"""
Advanced browser configuration and management inspired by crawl4ai.

This module provides comprehensive browser configuration options:
- BrowserConfig: Main browser configuration class
- GeolocationConfig: Geolocation settings
- ProxyConfig: Proxy configuration
- UserAgentConfig: User agent management
"""

import os
import json
import random
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class BrowserType(str, Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox" 
    WEBKIT = "webkit"


class DeviceType(str, Enum):
    """Device types for emulation."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


@dataclass
class GeolocationConfig:
    """Configuration for browser geolocation settings."""
    
    latitude: float
    longitude: float
    accuracy: float = 0.0
    
    @classmethod
    def from_dict(cls, geo_dict: Dict[str, Any]) -> "GeolocationConfig":
        """Create GeolocationConfig from dictionary."""
        return cls(
            latitude=geo_dict.get("latitude"),
            longitude=geo_dict.get("longitude"),
            accuracy=geo_dict.get("accuracy", 0.0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy
        }
    
    def clone(self, **kwargs) -> "GeolocationConfig":
        """Create a copy with updated values."""
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return GeolocationConfig.from_dict(config_dict)


@dataclass
class ProxyConfig:
    """Configuration for a single proxy."""
    
    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    ip: Optional[str] = None
    
    def __post_init__(self):
        """Extract IP from server if not provided."""
        if not self.ip:
            self.ip = self._extract_ip_from_server()
    
    def _extract_ip_from_server(self) -> Optional[str]:
        """Extract IP address from server URL."""
        try:
            if "://" in self.server:
                parts = self.server.split("://")[1].split(":")
                return parts[0]
            else:
                parts = self.server.split(":")
                return parts[0]
        except Exception:
            return None
    
    @classmethod
    def from_string(cls, proxy_str: str) -> "ProxyConfig":
        """Create ProxyConfig from string format 'ip:port:username:password'."""
        parts = proxy_str.split(":")
        if len(parts) == 4:  # ip:port:username:password
            ip, port, username, password = parts
            return cls(
                server=f"http://{ip}:{port}",
                username=username,
                password=password,
                ip=ip
            )
        elif len(parts) == 2:  # ip:port only
            ip, port = parts
            return cls(
                server=f"http://{ip}:{port}",
                ip=ip
            )
        else:
            raise ValueError(f"Invalid proxy string format: {proxy_str}")
    
    @classmethod
    def from_dict(cls, proxy_dict: Dict[str, Any]) -> "ProxyConfig":
        """Create ProxyConfig from dictionary."""
        return cls(
            server=proxy_dict.get("server"),
            username=proxy_dict.get("username"),
            password=proxy_dict.get("password"),
            ip=proxy_dict.get("ip")
        )
    
    @classmethod
    def from_env(cls, env_var: str = "PROXIES") -> List["ProxyConfig"]:
        """Load proxies from environment variable."""
        proxies = []
        try:
            proxy_list = os.getenv(env_var, "").split(",")
            for proxy in proxy_list:
                proxy = proxy.strip()
                if proxy:
                    proxies.append(cls.from_string(proxy))
        except Exception as e:
            logger.warning(f"Error loading proxies from env {env_var}: {str(e)}")
        
        return proxies
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "server": self.server,
            "username": self.username,
            "password": self.password,
            "ip": self.ip
        }


@dataclass 
class UserAgentConfig:
    """Configuration for user agent management."""
    
    user_agent: Optional[str] = None
    platform: Optional[str] = None
    device_type: DeviceType = DeviceType.DESKTOP
    randomize: bool = False
    
    # Common user agents for different platforms
    DESKTOP_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    
    MOBILE_USER_AGENTS = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ]
    
    TABLET_USER_AGENTS = [
        "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-T970) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    def get_user_agent(self) -> str:
        """Get user agent string based on configuration."""
        if self.user_agent:
            return self.user_agent
        
        if self.randomize:
            agents_list = self._get_agents_for_device_type()
            return random.choice(agents_list)
        else:
            # Return default for device type
            agents_list = self._get_agents_for_device_type()
            return agents_list[0] if agents_list else self.DESKTOP_USER_AGENTS[0]
    
    def _get_agents_for_device_type(self) -> List[str]:
        """Get user agent list for device type."""
        if self.device_type == DeviceType.MOBILE:
            return self.MOBILE_USER_AGENTS
        elif self.device_type == DeviceType.TABLET:
            return self.TABLET_USER_AGENTS
        else:
            return self.DESKTOP_USER_AGENTS


@dataclass
class BrowserConfig:
    """
    Comprehensive browser configuration for advanced web scraping.
    
    This class centralizes all browser-related parameters and settings
    for consistent configuration across different scraping scenarios.
    """
    
    # Basic browser settings
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    verbose: bool = False
    
    # Window and viewport settings
    viewport_width: int = 1920
    viewport_height: int = 1080
    window_width: Optional[int] = None
    window_height: Optional[int] = None
    device_scale_factor: float = 1.0
    
    # User agent and device emulation
    user_agent_config: Optional[UserAgentConfig] = None
    device_type: DeviceType = DeviceType.DESKTOP
    
    # Proxy and network settings
    proxy_config: Optional[ProxyConfig] = None
    ignore_https_errors: bool = True
    bypass_csp: bool = True
    
    # Geolocation settings  
    geolocation_config: Optional[GeolocationConfig] = None
    
    # Browser profile and persistence
    user_data_dir: Optional[str] = None
    use_persistent_context: bool = False
    profile_name: Optional[str] = None
    
    # Performance and resource settings
    javascript_enabled: bool = True
    images_enabled: bool = True
    css_enabled: bool = True
    plugins_enabled: bool = False
    webgl_enabled: bool = True
    
    # Security and privacy settings
    accept_downloads: bool = False
    permissions: List[str] = field(default_factory=list)
    locale: str = "en-US"
    timezone: Optional[str] = None
    
    # Browser launch arguments
    browser_args: List[str] = field(default_factory=list)
    chromium_sandbox: bool = True
    
    # Timeouts
    page_timeout: int = 30000  # milliseconds
    navigation_timeout: int = 30000  # milliseconds
    
    # Extra HTTP headers
    extra_headers: Dict[str, str] = field(default_factory=dict)
    
    # Cookie and session settings
    accept_cookies: bool = True
    cookie_file: Optional[str] = None
    
    # Screenshot and media settings
    full_page_screenshot: bool = False
    screenshot_quality: int = 80
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Set default user agent config if not provided
        if self.user_agent_config is None:
            self.user_agent_config = UserAgentConfig(device_type=self.device_type)
        
        # Set default browser arguments for security and performance
        if not self.browser_args:
            self.browser_args = self._get_default_browser_args()
        
        # Set window size if not specified
        if self.window_width is None:
            self.window_width = self.viewport_width
        if self.window_height is None:
            self.window_height = self.viewport_height
    
    def _get_default_browser_args(self) -> List[str]:
        """Get default browser arguments for security and performance."""
        args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
        ]
        
        if not self.chromium_sandbox:
            args.extend([
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ])
        
        if self.device_type == DeviceType.MOBILE:
            args.extend([
                "--enable-touch-events",
                "--enable-viewport"
            ])
        
        return args
    
    def get_launch_options(self) -> Dict[str, Any]:
        """Get browser launch options dictionary."""
        options = {
            "headless": self.headless,
            "args": self.browser_args,
            "ignore_https_errors": self.ignore_https_errors,
            "timeout": self.page_timeout
        }
        
        if self.user_data_dir:
            options["user_data_dir"] = self.user_data_dir
        
        if self.proxy_config:
            options["proxy"] = {
                "server": self.proxy_config.server
            }
            if self.proxy_config.username:
                options["proxy"]["username"] = self.proxy_config.username
            if self.proxy_config.password:
                options["proxy"]["password"] = self.proxy_config.password
        
        return options
    
    def get_context_options(self) -> Dict[str, Any]:
        """Get browser context options dictionary."""
        options = {
            "viewport": {
                "width": self.viewport_width,
                "height": self.viewport_height
            },
            "user_agent": self.user_agent_config.get_user_agent() if self.user_agent_config else None,
            "locale": self.locale,
            "timezone_id": self.timezone,
            "permissions": self.permissions,
            "extra_http_headers": self.extra_headers,
            "bypass_csp": self.bypass_csp,
            "javascript_enabled": self.javascript_enabled,
            "accept_downloads": self.accept_downloads
        }
        
        if self.geolocation_config:
            options["geolocation"] = self.geolocation_config.to_dict()
        
        # Remove None values
        return {k: v for k, v in options.items() if v is not None}
    
    def get_page_options(self) -> Dict[str, Any]:
        """Get page-specific options."""
        return {
            "timeout": self.navigation_timeout,
            "wait_until": "domcontentloaded"
        }
    
    def clone(self, **kwargs) -> "BrowserConfig":
        """Create a copy of this configuration with updated values."""
        # Create a copy of current config
        current_dict = self.to_dict()
        current_dict.update(kwargs)
        return BrowserConfig.from_dict(current_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "browser_type": self.browser_type.value,
            "headless": self.headless,
            "verbose": self.verbose,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "device_scale_factor": self.device_scale_factor,
            "user_agent_config": {
                "user_agent": self.user_agent_config.user_agent,
                "platform": self.user_agent_config.platform,
                "device_type": self.user_agent_config.device_type.value,
                "randomize": self.user_agent_config.randomize
            } if self.user_agent_config else None,
            "device_type": self.device_type.value,
            "proxy_config": self.proxy_config.to_dict() if self.proxy_config else None,
            "ignore_https_errors": self.ignore_https_errors,
            "bypass_csp": self.bypass_csp,
            "geolocation_config": self.geolocation_config.to_dict() if self.geolocation_config else None,
            "user_data_dir": self.user_data_dir,
            "use_persistent_context": self.use_persistent_context,
            "profile_name": self.profile_name,
            "javascript_enabled": self.javascript_enabled,
            "images_enabled": self.images_enabled,
            "css_enabled": self.css_enabled,
            "plugins_enabled": self.plugins_enabled,
            "webgl_enabled": self.webgl_enabled,
            "accept_downloads": self.accept_downloads,
            "permissions": self.permissions,
            "locale": self.locale,
            "timezone": self.timezone,
            "browser_args": self.browser_args,
            "chromium_sandbox": self.chromium_sandbox,
            "page_timeout": self.page_timeout,
            "navigation_timeout": self.navigation_timeout,
            "extra_headers": self.extra_headers,
            "accept_cookies": self.accept_cookies,
            "cookie_file": self.cookie_file,
            "full_page_screenshot": self.full_page_screenshot,
            "screenshot_quality": self.screenshot_quality
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "BrowserConfig":
        """Create BrowserConfig from dictionary."""
        # Handle nested configs
        user_agent_config = None
        if config_dict.get("user_agent_config"):
            ua_dict = config_dict["user_agent_config"]
            user_agent_config = UserAgentConfig(
                user_agent=ua_dict.get("user_agent"),
                platform=ua_dict.get("platform"),
                device_type=DeviceType(ua_dict.get("device_type", "desktop")),
                randomize=ua_dict.get("randomize", False)
            )
        
        proxy_config = None
        if config_dict.get("proxy_config"):
            proxy_config = ProxyConfig.from_dict(config_dict["proxy_config"])
        
        geolocation_config = None
        if config_dict.get("geolocation_config"):
            geolocation_config = GeolocationConfig.from_dict(config_dict["geolocation_config"])
        
        # Create config with processed nested objects
        processed_dict = config_dict.copy()
        processed_dict["browser_type"] = BrowserType(config_dict.get("browser_type", "chromium"))
        processed_dict["device_type"] = DeviceType(config_dict.get("device_type", "desktop"))
        processed_dict["user_agent_config"] = user_agent_config
        processed_dict["proxy_config"] = proxy_config
        processed_dict["geolocation_config"] = geolocation_config
        
        return cls(**{k: v for k, v in processed_dict.items() if v is not None})


# Predefined browser configurations for common use cases
def get_stealth_browser_config() -> BrowserConfig:
    """Get browser configuration optimized for stealth scraping."""
    return BrowserConfig(
        headless=True,
        user_agent_config=UserAgentConfig(randomize=True),
        ignore_https_errors=True,
        bypass_csp=True,
        chromium_sandbox=False,
        browser_args=[
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-plugins", 
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-ipc-flooding-protection",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ],
        extra_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    )


def get_mobile_browser_config() -> BrowserConfig:
    """Get browser configuration for mobile device emulation."""
    return BrowserConfig(
        device_type=DeviceType.MOBILE,
        viewport_width=414,
        viewport_height=896,
        device_scale_factor=3.0,
        user_agent_config=UserAgentConfig(
            device_type=DeviceType.MOBILE,
            randomize=False
        ),
        browser_args=[
            "--enable-touch-events",
            "--enable-viewport",
            "--disable-extensions",
            "--no-first-run"
        ]
    )


def get_high_performance_browser_config() -> BrowserConfig:
    """Get browser configuration optimized for performance."""
    return BrowserConfig(
        headless=True,
        images_enabled=False,  # Skip image loading
        css_enabled=False,     # Skip CSS loading
        plugins_enabled=False,
        webgl_enabled=False,
        javascript_enabled=True,  # Keep JS for dynamic content
        browser_args=[
            "--disable-extensions",
            "--disable-plugins",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows", 
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-sync",
            "--disable-background-networking",
            "--disable-background-mode",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-default-apps",
            "--no-first-run",
            "--no-default-browser-check"
        ]
    )


# Utility functions
def create_browser_config_from_env() -> BrowserConfig:
    """Create browser configuration from environment variables."""
    config = BrowserConfig()
    
    # Basic settings
    if os.getenv("BROWSER_HEADLESS"):
        config.headless = os.getenv("BROWSER_HEADLESS").lower() == "true"
    
    if os.getenv("BROWSER_TYPE"):
        config.browser_type = BrowserType(os.getenv("BROWSER_TYPE"))
    
    # Viewport settings
    if os.getenv("VIEWPORT_WIDTH"):
        config.viewport_width = int(os.getenv("VIEWPORT_WIDTH"))
    
    if os.getenv("VIEWPORT_HEIGHT"):
        config.viewport_height = int(os.getenv("VIEWPORT_HEIGHT"))
    
    # User agent
    if os.getenv("USER_AGENT"):
        config.user_agent_config = UserAgentConfig(user_agent=os.getenv("USER_AGENT"))
    
    # Proxy settings
    if os.getenv("PROXY_SERVER"):
        config.proxy_config = ProxyConfig(
            server=os.getenv("PROXY_SERVER"),
            username=os.getenv("PROXY_USERNAME"),
            password=os.getenv("PROXY_PASSWORD")
        )
    
    # Geolocation
    if os.getenv("GEO_LATITUDE") and os.getenv("GEO_LONGITUDE"):
        config.geolocation_config = GeolocationConfig(
            latitude=float(os.getenv("GEO_LATITUDE")),
            longitude=float(os.getenv("GEO_LONGITUDE"))
        )
    
    return config
