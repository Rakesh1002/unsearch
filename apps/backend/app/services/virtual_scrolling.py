"""
Virtual scrolling support for infinite pages inspired by crawl4ai.

This module implements sophisticated virtual scrolling capabilities:
- Automatic infinite scroll detection and handling
- Smart waiting strategies for dynamic content
- Content extraction during scrolling
- Progress tracking and optimization
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable, Tuple
from urllib.parse import urlparse

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)


@dataclass
class VirtualScrollConfig:
    """Configuration for virtual scrolling behavior."""
    container_selector: Optional[str] = None
    scroll_count: int = 10
    scroll_by: str = "viewport_height"  # "viewport_height", "container_height", "pixels"
    scroll_pixels: int = 1000
    wait_after_scroll: float = 2.0
    wait_for_selector: Optional[str] = None
    scroll_timeout: float = 30.0
    check_content_changes: bool = True
    min_content_increase: int = 100  # Minimum chars to consider new content
    max_scroll_attempts: int = 50
    auto_detect_infinite_scroll: bool = True
    scroll_pause_detection: bool = True
    content_stabilization_time: float = 3.0


@dataclass
class ScrollState:
    """State tracking for virtual scrolling operations."""
    current_scroll: int = 0
    total_content_length: int = 0
    last_content_change: float = 0
    scroll_history: List[int] = None
    content_snapshots: List[str] = None
    stabilization_count: int = 0
    last_successful_scroll: int = 0
    is_infinite_scroll_detected: bool = False
    scroll_triggers: List[str] = None
    
    def __post_init__(self):
        if self.scroll_history is None:
            self.scroll_history = []
        if self.content_snapshots is None:
            self.content_snapshots = []
        if self.scroll_triggers is None:
            self.scroll_triggers = []


@dataclass
class VirtualScrollResult:
    """Result of virtual scrolling operation."""
    success: bool
    total_scrolls: int
    final_content: str
    content_blocks: List[Dict[str, Any]]
    scroll_metadata: Dict[str, Any]
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class VirtualScrollHandler:
    """
    Handler for virtual scrolling operations.
    
    This class manages the complex process of scrolling through infinite
    pages and extracting content as it loads dynamically.
    """
    
    def __init__(self, config: VirtualScrollConfig):
        """Initialize virtual scroll handler."""
        self.config = config
        
        # JavaScript snippets for scrolling operations
        self.scroll_js = {
            "viewport_height": """
                window.scrollBy(0, window.innerHeight);
                return window.pageYOffset;
            """,
            "container_height": """
                const container = document.querySelector(arguments[0]);
                if (container) {
                    container.scrollBy(0, container.clientHeight);
                    return container.scrollTop;
                }
                return -1;
            """,
            "pixels": """
                window.scrollBy(0, arguments[0]);
                return window.pageYOffset;
            """,
            "to_bottom": """
                window.scrollTo(0, document.body.scrollHeight);
                return window.pageYOffset;
            """,
            "get_scroll_position": """
                return {
                    scrollY: window.pageYOffset,
                    scrollHeight: document.body.scrollHeight,
                    clientHeight: window.innerHeight
                };
            """,
            "detect_infinite_scroll": """
                // Look for common infinite scroll indicators
                const indicators = [
                    '[data-testid*="feed"]',
                    '.infinite-scroll',
                    '[class*="infinite"]',
                    '[id*="infinite"]',
                    '.lazy-load',
                    '[data-lazy]',
                    '.loading-more',
                    '.load-more'
                ];
                
                for (let selector of indicators) {
                    if (document.querySelector(selector)) {
                        return {detected: true, selector: selector};
                    }
                }
                
                // Check for scroll event listeners
                const hasScrollListeners = window.getEventListeners && 
                    Object.keys(window.getEventListeners(window)).includes('scroll');
                
                return {
                    detected: hasScrollListeners || false,
                    selector: null,
                    hasScrollListeners: hasScrollListeners
                };
            """,
            "wait_for_content_load": """
                return new Promise((resolve) => {
                    let attempts = 0;
                    const maxAttempts = arguments[0] || 10;
                    const checkInterval = arguments[1] || 500;
                    
                    function checkForNewContent() {
                        attempts++;
                        
                        // Check if loading indicators are gone
                        const loadingElements = document.querySelectorAll(
                            '.loading, .spinner, [class*="load"], [aria-label*="load"]'
                        );
                        
                        const stillLoading = Array.from(loadingElements).some(el => 
                            el.offsetParent !== null && !el.hidden
                        );
                        
                        if (!stillLoading || attempts >= maxAttempts) {
                            resolve({
                                attempts: attempts,
                                stillLoading: stillLoading,
                                loadingElements: loadingElements.length
                            });
                        } else {
                            setTimeout(checkForNewContent, checkInterval);
                        }
                    }
                    
                    checkForNewContent();
                });
            """
        }
    
    async def perform_virtual_scroll(
        self,
        page_executor: Callable,  # Function to execute JS on the page
        content_extractor: Callable,  # Function to extract current page content
        url: str = "",
        **kwargs
    ) -> VirtualScrollResult:
        """
        Perform virtual scrolling with content extraction.
        
        Args:
            page_executor: Function to execute JavaScript on the page
            content_extractor: Function to extract content from current page state
            url: URL being scrolled (for logging)
            **kwargs: Additional parameters
            
        Returns:
            VirtualScrollResult with extracted content and metadata
        """
        start_time = time.time()
        state = ScrollState()
        content_blocks = []
        
        try:
            logger.info(
                "virtual_scroll_started",
                url=url,
                config=self.config.__dict__
            )
            
            # Auto-detect infinite scroll if enabled
            if self.config.auto_detect_infinite_scroll:
                detection_result = await self._detect_infinite_scroll(page_executor)
                state.is_infinite_scroll_detected = detection_result.get('detected', False)
                
                if state.is_infinite_scroll_detected:
                    logger.info("infinite_scroll_detected", url=url, detection=detection_result)
            
            # Initial content extraction
            initial_content = await content_extractor()
            if initial_content:
                state.total_content_length = len(initial_content)
                state.content_snapshots.append(initial_content[:500])  # Store first 500 chars
                content_blocks.append({
                    'scroll_position': 0,
                    'content': initial_content,
                    'timestamp': time.time(),
                    'content_length': len(initial_content)
                })
            
            # Perform scrolling iterations
            successful_scrolls = 0
            consecutive_no_change = 0
            
            for scroll_iteration in range(self.config.scroll_count):
                if scroll_iteration >= self.config.max_scroll_attempts:
                    logger.warning("max_scroll_attempts_reached", url=url)
                    break
                
                # Perform scroll action
                scroll_result = await self._perform_single_scroll(
                    page_executor, scroll_iteration
                )
                
                if not scroll_result['success']:
                    logger.warning(
                        "scroll_action_failed",
                        iteration=scroll_iteration,
                        url=url
                    )
                    continue
                
                state.current_scroll = scroll_iteration + 1
                state.scroll_history.append(scroll_result['position'])
                
                # Wait for content to load
                await self._wait_for_content_stabilization(page_executor)
                
                # Extract content after scroll
                new_content = await content_extractor()
                if new_content:
                    # Check if content actually changed
                    content_change = len(new_content) - state.total_content_length
                    
                    if content_change >= self.config.min_content_increase:
                        # Significant content change detected
                        state.total_content_length = len(new_content)
                        state.last_content_change = time.time()
                        state.content_snapshots.append(new_content[-500:])  # Store last 500 chars
                        consecutive_no_change = 0
                        successful_scrolls += 1
                        
                        content_blocks.append({
                            'scroll_position': scroll_iteration + 1,
                            'content': new_content,
                            'content_delta': content_change,
                            'timestamp': time.time(),
                            'content_length': len(new_content)
                        })
                        
                        state.last_successful_scroll = scroll_iteration
                        
                        logger.debug(
                            "scroll_content_updated",
                            iteration=scroll_iteration,
                            content_change=content_change,
                            url=url
                        )
                    else:
                        # No significant content change
                        consecutive_no_change += 1
                        
                        if consecutive_no_change >= 3:
                            logger.info(
                                "no_content_change_detected",
                                consecutive_attempts=consecutive_no_change,
                                url=url
                            )
                            break
                
                # Check if we've reached the bottom
                if await self._check_if_at_bottom(page_executor):
                    logger.info("reached_bottom_of_page", url=url)
                    break
                
                # Adaptive delay based on content loading
                await self._adaptive_wait(state, scroll_iteration)
            
            # Final content extraction
            final_content = await content_extractor()
            
            # Calculate performance metrics
            end_time = time.time()
            performance_metrics = {
                'total_time': end_time - start_time,
                'scrolls_performed': state.current_scroll,
                'successful_scrolls': successful_scrolls,
                'content_increase_ratio': state.total_content_length / max(1, len(initial_content or "")),
                'avg_scroll_time': (end_time - start_time) / max(1, state.current_scroll),
                'content_per_scroll': state.total_content_length / max(1, successful_scrolls),
                'stabilization_time': self.config.content_stabilization_time
            }
            
            # Prepare scroll metadata
            scroll_metadata = {
                'infinite_scroll_detected': state.is_infinite_scroll_detected,
                'total_scrolls': state.current_scroll,
                'successful_scrolls': successful_scrolls,
                'final_content_length': len(final_content) if final_content else 0,
                'content_snapshots_count': len(state.content_snapshots),
                'scroll_history': state.scroll_history,
                'config': self.config.__dict__
            }
            
            logger.info(
                "virtual_scroll_completed",
                url=url,
                total_scrolls=state.current_scroll,
                successful_scrolls=successful_scrolls,
                final_content_length=len(final_content) if final_content else 0
            )
            
            return VirtualScrollResult(
                success=True,
                total_scrolls=state.current_scroll,
                final_content=final_content or "",
                content_blocks=content_blocks,
                scroll_metadata=scroll_metadata,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error("virtual_scroll_failed", url=url, error=str(e))
            
            return VirtualScrollResult(
                success=False,
                total_scrolls=state.current_scroll,
                final_content="",
                content_blocks=content_blocks,
                scroll_metadata={'error': str(e)},
                error_message=str(e)
            )
    
    async def _detect_infinite_scroll(self, page_executor: Callable) -> Dict[str, Any]:
        """Detect if the page uses infinite scrolling."""
        try:
            result = await page_executor(self.scroll_js["detect_infinite_scroll"])
            return result if isinstance(result, dict) else {'detected': False}
        except Exception as e:
            logger.warning("infinite_scroll_detection_failed", error=str(e))
            return {'detected': False, 'error': str(e)}
    
    async def _perform_single_scroll(
        self, 
        page_executor: Callable, 
        iteration: int
    ) -> Dict[str, Any]:
        """Perform a single scroll action."""
        try:
            if self.config.scroll_by == "viewport_height":
                result = await page_executor(self.scroll_js["viewport_height"])
            elif self.config.scroll_by == "container_height":
                result = await page_executor(
                    self.scroll_js["container_height"],
                    self.config.container_selector or "body"
                )
            else:  # pixels
                result = await page_executor(
                    self.scroll_js["pixels"],
                    self.config.scroll_pixels
                )
            
            return {
                'success': True,
                'position': result if isinstance(result, (int, float)) else 0,
                'iteration': iteration
            }
            
        except Exception as e:
            logger.error("scroll_action_failed", iteration=iteration, error=str(e))
            return {'success': False, 'error': str(e), 'iteration': iteration}
    
    async def _wait_for_content_stabilization(self, page_executor: Callable):
        """Wait for content to stabilize after scrolling."""
        try:
            # Basic wait
            await asyncio.sleep(self.config.wait_after_scroll)
            
            # If specified, wait for specific selector
            if self.config.wait_for_selector:
                # Simple implementation - in production, you'd want more sophisticated waiting
                await asyncio.sleep(1.0)
            
            # Wait for loading indicators to disappear
            if self.config.scroll_pause_detection:
                await page_executor(
                    self.scroll_js["wait_for_content_load"],
                    10,  # max attempts
                    500  # check interval ms
                )
            
        except Exception as e:
            logger.warning("content_stabilization_wait_failed", error=str(e))
            # Continue with default wait
            await asyncio.sleep(self.config.wait_after_scroll)
    
    async def _check_if_at_bottom(self, page_executor: Callable) -> bool:
        """Check if we've reached the bottom of the page."""
        try:
            result = await page_executor(self.scroll_js["get_scroll_position"])
            
            if isinstance(result, dict):
                scroll_y = result.get('scrollY', 0)
                scroll_height = result.get('scrollHeight', 0)
                client_height = result.get('clientHeight', 0)
                
                # Check if we're within 100 pixels of the bottom
                return (scroll_y + client_height) >= (scroll_height - 100)
            
            return False
            
        except Exception as e:
            logger.warning("bottom_check_failed", error=str(e))
            return False
    
    async def _adaptive_wait(self, state: ScrollState, iteration: int):
        """Implement adaptive waiting based on scrolling patterns."""
        base_wait = self.config.wait_after_scroll
        
        # Increase wait time if we haven't seen content changes recently
        time_since_change = time.time() - state.last_content_change
        if time_since_change > 10.0:  # 10 seconds without change
            base_wait *= 1.5
        
        # Decrease wait time if we're getting consistent content updates
        if len(state.content_snapshots) > 3:
            recent_changes = len(set(state.content_snapshots[-3:]))
            if recent_changes >= 2:  # Recent content diversity
                base_wait *= 0.8
        
        # Increase wait time for later iterations (content might load slower)
        if iteration > 10:
            base_wait *= 1.2
        
        # Ensure reasonable bounds
        final_wait = max(0.5, min(10.0, base_wait))
        
        await asyncio.sleep(final_wait)


class PuppeteerVirtualScroller:
    """
    Virtual scroller that integrates with Puppeteer service.
    
    This class provides a bridge between the virtual scrolling logic
    and the Puppeteer-based browser automation.
    """
    
    def __init__(self, puppeteer_service_url: str):
        """Initialize Puppeteer virtual scroller."""
        self.service_url = puppeteer_service_url
        self.handler = None
    
    async def scroll_and_extract(
        self,
        url: str,
        config: VirtualScrollConfig,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> VirtualScrollResult:
        """
        Scroll page and extract content using Puppeteer service.
        
        Args:
            url: URL to scroll
            config: Virtual scrolling configuration
            headers: Optional HTTP headers
            **kwargs: Additional parameters
            
        Returns:
            VirtualScrollResult with extracted content
        """
        self.handler = VirtualScrollHandler(config)
        
        # Create page executor for Puppeteer
        async def page_executor(js_code: str, *args) -> Any:
            return await self._execute_js_on_puppeteer(url, js_code, args, headers)
        
        # Create content extractor for current page state
        async def content_extractor() -> str:
            return await self._extract_page_content(url, headers)
        
        return await self.handler.perform_virtual_scroll(
            page_executor=page_executor,
            content_extractor=content_extractor,
            url=url,
            **kwargs
        )
    
    async def _execute_js_on_puppeteer(
        self,
        url: str,
        js_code: str,
        args: Tuple,
        headers: Optional[Dict[str, str]]
    ) -> Any:
        """Execute JavaScript on Puppeteer service."""
        # This would integrate with your existing Puppeteer service
        # For now, this is a placeholder implementation
        import httpx
        
        async with httpx.AsyncClient() as client:
            payload = {
                'url': url,
                'javascript': js_code,
                'args': list(args) if args else [],
                'headers': headers or {},
                'waitUntil': 'networkidle0'
            }
            
            response = await client.post(
                f"{self.service_url}/execute-js",
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result')
            else:
                raise Exception(f"Puppeteer service error: {response.status_code}")
    
    async def _extract_page_content(
        self,
        url: str,
        headers: Optional[Dict[str, str]]
    ) -> str:
        """Extract current page content via Puppeteer service."""
        # This would integrate with your existing Puppeteer service
        import httpx
        
        async with httpx.AsyncClient() as client:
            payload = {
                'url': url,
                'headers': headers or {},
                'waitUntil': 'networkidle0'
            }
            
            response = await client.post(
                f"{self.service_url}/render",
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('html', '')
            else:
                return ''


# Convenience functions
def create_virtual_scroll_config(
    container_selector: Optional[str] = None,
    scroll_count: int = 10,
    wait_after_scroll: float = 2.0,
    auto_detect: bool = True
) -> VirtualScrollConfig:
    """Create virtual scroll configuration with common settings."""
    return VirtualScrollConfig(
        container_selector=container_selector,
        scroll_count=scroll_count,
        wait_after_scroll=wait_after_scroll,
        auto_detect_infinite_scroll=auto_detect,
        check_content_changes=True,
        scroll_pause_detection=True
    )


async def scroll_infinite_page(
    url: str,
    puppeteer_service_url: str,
    scroll_count: int = 10,
    wait_time: float = 2.0,
    container_selector: Optional[str] = None
) -> VirtualScrollResult:
    """
    Convenience function to scroll an infinite page.
    
    Args:
        url: URL to scroll
        puppeteer_service_url: Puppeteer service endpoint
        scroll_count: Number of scrolls to perform
        wait_time: Time to wait after each scroll
        container_selector: Optional container selector
        
    Returns:
        VirtualScrollResult with extracted content
    """
    config = VirtualScrollConfig(
        container_selector=container_selector,
        scroll_count=scroll_count,
        wait_after_scroll=wait_time,
        auto_detect_infinite_scroll=True
    )
    
    scroller = PuppeteerVirtualScroller(puppeteer_service_url)
    return await scroller.scroll_and_extract(url, config)
