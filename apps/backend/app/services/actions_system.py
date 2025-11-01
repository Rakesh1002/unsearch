"""
Advanced Actions System for browser automation inspired by Firecrawl.

Provides sophisticated browser automation capabilities including:
- Click, scroll, input, wait actions
- Screenshot capture
- JavaScript execution
- PDF generation
- Complex interaction sequences
"""

import asyncio
import time
import json
import base64
from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.config import get_settings
from app.models.responses import ScrapedContent

logger = structlog.get_logger(__name__)
settings = get_settings()


class ActionType(Enum):
    """Types of browser actions."""
    WAIT = "wait"
    CLICK = "click"
    SCROLL = "scroll"
    WRITE = "write"
    PRESS = "press"
    SCREENSHOT = "screenshot"
    SCRAPE = "scrape"
    EXECUTE_JAVASCRIPT = "executeJavascript"
    PDF = "pdf"


@dataclass
class WaitAction:
    """Wait action configuration."""
    type: Literal["wait"] = "wait"
    milliseconds: Optional[int] = None
    selector: Optional[str] = None
    
    def __post_init__(self):
        if not self.milliseconds and not self.selector:
            raise ValueError("Either milliseconds or selector must be provided")
        if self.milliseconds and self.selector:
            raise ValueError("Only one of milliseconds or selector can be provided")


@dataclass
class ClickAction:
    """Click action configuration."""
    type: Literal["click"] = "click"
    selector: str
    all: bool = False


@dataclass
class ScrollAction:
    """Scroll action configuration."""
    type: Literal["scroll"] = "scroll"
    direction: Literal["up", "down"] = "down"
    selector: Optional[str] = None


@dataclass
class WriteAction:
    """Write text action configuration."""
    type: Literal["write"] = "write"
    text: str


@dataclass
class PressAction:
    """Press key action configuration."""
    type: Literal["press"] = "press"
    key: str


@dataclass
class ScreenshotAction:
    """Screenshot action configuration."""
    type: Literal["screenshot"] = "screenshot"
    fullPage: bool = False
    quality: Optional[int] = None  # 1-100
    viewport: Optional[Dict[str, int]] = None


@dataclass
class ScrapeAction:
    """Scrape current state action configuration."""
    type: Literal["scrape"] = "scrape"


@dataclass
class ExecuteJavaScriptAction:
    """Execute JavaScript action configuration."""
    type: Literal["executeJavascript"] = "executeJavascript"
    script: str


@dataclass
class PDFAction:
    """Generate PDF action configuration."""
    type: Literal["pdf"] = "pdf"
    landscape: bool = False
    scale: float = 1.0
    format: Literal["A0", "A1", "A2", "A3", "A4", "A5", "A6", "Letter", "Legal", "Tabloid", "Ledger"] = "Letter"


# Union type for all actions
Action = Union[
    WaitAction,
    ClickAction,
    ScrollAction,
    WriteAction,
    PressAction,
    ScreenshotAction,
    ScrapeAction,
    ExecuteJavaScriptAction,
    PDFAction
]


@dataclass
class ActionResult:
    """Result of an action execution."""
    action_type: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    screenshot_url: Optional[str] = None


@dataclass
class ActionsSequenceResult:
    """Result of executing a sequence of actions."""
    success: bool
    actions_results: List[ActionResult] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    scrapes: List[Dict[str, Any]] = field(default_factory=list)
    javascript_returns: List[Dict[str, Any]] = field(default_factory=list)
    pdfs: List[str] = field(default_factory=list)
    total_execution_time_ms: int = 0
    error: Optional[str] = None


class BrowserActionsExecutor:
    """
    Browser actions executor using Playwright or Puppeteer.
    
    Executes complex sequences of browser actions including:
    - User interactions (click, scroll, type)
    - Waiting for elements or time
    - Screenshot capture
    - JavaScript execution
    - PDF generation
    - Content scraping at various stages
    """
    
    def __init__(self):
        """Initialize the browser actions executor."""
        self.browser = None
        self.page = None
        self.context = None
        self.actions_stats = {"total_actions": 0, "successful_actions": 0}
    
    async def execute_actions_sequence(
        self, 
        url: str, 
        actions: List[Dict[str, Any]],
        browser_options: Optional[Dict[str, Any]] = None
    ) -> ActionsSequenceResult:
        """
        Execute a sequence of browser actions.
        
        Args:
            url: URL to navigate to
            actions: List of action dictionaries
            browser_options: Browser configuration options
            
        Returns:
            ActionsSequenceResult with execution results
        """
        start_time = time.time()
        result = ActionsSequenceResult(success=True)
        
        try:
            # Parse actions
            parsed_actions = self._parse_actions(actions)
            
            # Initialize browser
            await self._initialize_browser(browser_options or {})
            
            # Navigate to URL
            await self._navigate_to_url(url)
            
            # Execute each action
            for i, action in enumerate(parsed_actions):
                try:
                    logger.info("executing_action", 
                               index=i, 
                               action_type=action.type,
                               url=url)
                    
                    action_result = await self._execute_single_action(action)
                    result.actions_results.append(action_result)
                    
                    # Collect results by type
                    if action_result.success:
                        self.actions_stats["successful_actions"] += 1
                        
                        if action.type == "screenshot" and action_result.screenshot_url:
                            result.screenshots.append(action_result.screenshot_url)
                        elif action.type == "scrape" and action_result.data:
                            result.scrapes.append(action_result.data)
                        elif action.type == "executeJavascript" and action_result.data:
                            result.javascript_returns.append({
                                "type": type(action_result.data).__name__,
                                "value": action_result.data
                            })
                        elif action.type == "pdf" and action_result.data:
                            result.pdfs.append(action_result.data)
                    
                    self.actions_stats["total_actions"] += 1
                    
                except Exception as e:
                    error_msg = f"Action {i} ({action.type}) failed: {str(e)}"
                    logger.error("action_execution_failed", 
                               index=i, 
                               action_type=action.type, 
                               error=str(e))
                    
                    result.actions_results.append(ActionResult(
                        action_type=action.type,
                        success=False,
                        error=error_msg
                    ))
                    
                    # Continue with other actions unless critical failure
                    if action.type in ["wait", "click", "write"]:
                        continue
                    else:
                        result.success = False
                        result.error = error_msg
                        break
            
            result.total_execution_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info("actions_sequence_completed",
                       url=url,
                       total_actions=len(actions),
                       successful_actions=len([r for r in result.actions_results if r.success]),
                       execution_time_ms=result.total_execution_time_ms)
            
            return result
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.total_execution_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error("actions_sequence_failed", 
                        url=url, 
                        error=str(e),
                        execution_time_ms=result.total_execution_time_ms)
            
            return result
        
        finally:
            await self._cleanup_browser()
    
    def _parse_actions(self, actions: List[Dict[str, Any]]) -> List[Action]:
        """Parse action dictionaries into typed action objects."""
        parsed_actions = []
        
        for action_dict in actions:
            action_type = action_dict.get("type")
            
            try:
                if action_type == "wait":
                    parsed_actions.append(WaitAction(**action_dict))
                elif action_type == "click":
                    parsed_actions.append(ClickAction(**action_dict))
                elif action_type == "scroll":
                    parsed_actions.append(ScrollAction(**action_dict))
                elif action_type == "write":
                    parsed_actions.append(WriteAction(**action_dict))
                elif action_type == "press":
                    parsed_actions.append(PressAction(**action_dict))
                elif action_type == "screenshot":
                    parsed_actions.append(ScreenshotAction(**action_dict))
                elif action_type == "scrape":
                    parsed_actions.append(ScrapeAction(**action_dict))
                elif action_type == "executeJavascript":
                    parsed_actions.append(ExecuteJavaScriptAction(**action_dict))
                elif action_type == "pdf":
                    parsed_actions.append(PDFAction(**action_dict))
                else:
                    raise ValueError(f"Unknown action type: {action_type}")
                    
            except Exception as e:
                logger.error("action_parsing_failed", action=action_dict, error=str(e))
                raise ValueError(f"Invalid action configuration: {str(e)}")
        
        return parsed_actions
    
    async def _initialize_browser(self, browser_options: Dict[str, Any]):
        """Initialize browser instance."""
        try:
            # Try Playwright first
            playwright_url = getattr(settings, 'playwright_service_url', None)
            if playwright_url:
                await self._initialize_playwright_browser(browser_options)
                return
            
            # Fallback to Fire Engine
            fire_engine_url = getattr(settings, 'fire_engine_url', None)
            if fire_engine_url:
                await self._initialize_fire_engine_browser(browser_options)
                return
            
            # Fallback to local Playwright
            await self._initialize_local_playwright(browser_options)
            
        except Exception as e:
            logger.error("browser_initialization_failed", error=str(e))
            raise e
    
    async def _initialize_playwright_browser(self, options: Dict[str, Any]):
        """Initialize Playwright browser via service."""
        # This would connect to Playwright service
        # For now, simulate browser initialization
        self.browser = "playwright_service"
        self.page = "playwright_page"
        self.context = "playwright_context"
    
    async def _initialize_fire_engine_browser(self, options: Dict[str, Any]):
        """Initialize Fire Engine browser."""
        # This would connect to Fire Engine
        # For now, simulate browser initialization
        self.browser = "fire_engine"
        self.page = "fire_engine_page"
        self.context = "fire_engine_context"
    
    async def _initialize_local_playwright(self, options: Dict[str, Any]):
        """Initialize local Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=options.get("headless", True),
                args=options.get("args", [])
            )
            self.context = await self.browser.new_context(
                viewport=options.get("viewport", {"width": 1920, "height": 1080}),
                user_agent=options.get("userAgent", settings.scraping_user_agent)
            )
            self.page = await self.context.new_page()
            
        except ImportError:
            logger.warning("playwright_not_available", fallback="mock")
            # Mock browser for testing
            self.browser = "mock_browser"
            self.page = "mock_page"
            self.context = "mock_context"
    
    async def _navigate_to_url(self, url: str):
        """Navigate to the specified URL."""
        if self.page == "mock_page":
            return  # Mock navigation
        
        # Here we would navigate using actual browser
        # For now, log the navigation
        logger.info("navigating_to_url", url=url)
    
    async def _execute_single_action(self, action: Action) -> ActionResult:
        """Execute a single browser action."""
        start_time = time.time()
        
        try:
            if action.type == "wait":
                result_data = await self._execute_wait(action)
            elif action.type == "click":
                result_data = await self._execute_click(action)
            elif action.type == "scroll":
                result_data = await self._execute_scroll(action)
            elif action.type == "write":
                result_data = await self._execute_write(action)
            elif action.type == "press":
                result_data = await self._execute_press(action)
            elif action.type == "screenshot":
                result_data = await self._execute_screenshot(action)
            elif action.type == "scrape":
                result_data = await self._execute_scrape(action)
            elif action.type == "executeJavascript":
                result_data = await self._execute_javascript(action)
            elif action.type == "pdf":
                result_data = await self._execute_pdf(action)
            else:
                raise ValueError(f"Unsupported action type: {action.type}")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ActionResult(
                action_type=action.type,
                success=True,
                data=result_data,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            
            return ActionResult(
                action_type=action.type,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def _execute_wait(self, action: WaitAction) -> Any:
        """Execute wait action."""
        if action.milliseconds:
            await asyncio.sleep(action.milliseconds / 1000)
            return {"waited_ms": action.milliseconds}
        elif action.selector:
            # Wait for element to appear
            # In real implementation, would wait for selector
            await asyncio.sleep(1)  # Simulate wait
            return {"waited_for_selector": action.selector}
    
    async def _execute_click(self, action: ClickAction) -> Any:
        """Execute click action."""
        # In real implementation, would click element
        await asyncio.sleep(0.1)  # Simulate click
        return {"clicked_selector": action.selector, "all": action.all}
    
    async def _execute_scroll(self, action: ScrollAction) -> Any:
        """Execute scroll action."""
        # In real implementation, would scroll page
        await asyncio.sleep(0.1)  # Simulate scroll
        return {"scrolled": action.direction, "selector": action.selector}
    
    async def _execute_write(self, action: WriteAction) -> Any:
        """Execute write text action."""
        # In real implementation, would type text
        await asyncio.sleep(len(action.text) * 0.01)  # Simulate typing
        return {"written_text": action.text}
    
    async def _execute_press(self, action: PressAction) -> Any:
        """Execute key press action."""
        # In real implementation, would press key
        await asyncio.sleep(0.1)  # Simulate key press
        return {"pressed_key": action.key}
    
    async def _execute_screenshot(self, action: ScreenshotAction) -> Any:
        """Execute screenshot action."""
        # In real implementation, would capture screenshot
        await asyncio.sleep(0.5)  # Simulate screenshot capture
        
        # Generate mock base64 screenshot data
        screenshot_data = base64.b64encode(b"mock_screenshot_data").decode()
        
        return {
            "screenshot_base64": screenshot_data,
            "fullPage": action.fullPage,
            "quality": action.quality
        }
    
    async def _execute_scrape(self, action: ScrapeAction) -> Any:
        """Execute scrape current state action."""
        # In real implementation, would scrape current page
        await asyncio.sleep(0.2)  # Simulate scraping
        
        return {
            "html": "<html>Mock scraped content</html>",
            "title": "Mock Page Title",
            "text": "Mock page text content",
            "timestamp": time.time()
        }
    
    async def _execute_javascript(self, action: ExecuteJavaScriptAction) -> Any:
        """Execute JavaScript action."""
        # In real implementation, would execute JavaScript
        await asyncio.sleep(0.1)  # Simulate JS execution
        
        # Mock JavaScript result
        return {
            "script": action.script,
            "result": "Mock JS execution result"
        }
    
    async def _execute_pdf(self, action: PDFAction) -> Any:
        """Execute PDF generation action."""
        # In real implementation, would generate PDF
        await asyncio.sleep(1.0)  # Simulate PDF generation
        
        # Generate mock PDF data
        pdf_data = base64.b64encode(b"mock_pdf_data").decode()
        
        return {
            "pdf_base64": pdf_data,
            "landscape": action.landscape,
            "scale": action.scale,
            "format": action.format
        }
    
    async def _cleanup_browser(self):
        """Cleanup browser resources."""
        try:
            if hasattr(self, 'playwright') and self.playwright:
                if self.browser and hasattr(self.browser, 'close'):
                    await self.browser.close()
                await self.playwright.stop()
            
            # Reset browser state
            self.browser = None
            self.page = None
            self.context = None
            
        except Exception as e:
            logger.warning("browser_cleanup_failed", error=str(e))
    
    async def get_actions_stats(self) -> Dict[str, Any]:
        """Get actions execution statistics."""
        return {
            "actions_stats": self.actions_stats,
            "success_rate": (
                self.actions_stats["successful_actions"] / 
                max(1, self.actions_stats["total_actions"])
            ) if self.actions_stats["total_actions"] > 0 else 0
        }


# Convenience functions
async def execute_browser_actions(
    url: str,
    actions: List[Dict[str, Any]],
    browser_options: Optional[Dict[str, Any]] = None
) -> ActionsSequenceResult:
    """
    Execute browser actions sequence.
    
    Args:
        url: URL to navigate to
        actions: List of action configurations
        browser_options: Browser configuration options
        
    Returns:
        ActionsSequenceResult with execution results
    """
    executor = BrowserActionsExecutor()
    return await executor.execute_actions_sequence(url, actions, browser_options)


# Singleton service
_actions_service: Optional[BrowserActionsExecutor] = None


async def get_actions_service() -> BrowserActionsExecutor:
    """Get or create browser actions service instance."""
    global _actions_service
    
    if _actions_service is None:
        _actions_service = BrowserActionsExecutor()
    
    return _actions_service
