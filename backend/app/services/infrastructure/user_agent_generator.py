"""
Advanced user agent generation system with multiple strategies and client hints.

This module provides sophisticated user agent management:
- Multiple generation strategies (Valid, Online, Custom)
- Automatic client hints generation (Sec-CH-UA)
- Browser fingerprinting avoidance
- Platform and browser specific agents
- Performance optimization with caching
"""

import random
import re
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class UserAgentProfile:
    """Profile for user agent generation."""
    browser: str
    version: str
    platform: str
    os: str
    engine: str
    full_agent: str
    client_hints: str
    popularity_score: float = 0.0
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {
            'browser': self.browser,
            'version': self.version,
            'platform': self.platform,
            'os': self.os,
            'engine': self.engine,
            'user_agent': self.full_agent,
            'client_hints': self.client_hints
        }


class UAGenerator(ABC):
    """Abstract base class for user agent generators."""
    
    @abstractmethod
    def generate(self, 
                browsers: Optional[List[str]] = None,
                os: Optional[Union[str, List[str]]] = None,
                min_version: float = 0.0,
                platforms: Optional[Union[str, List[str]]] = None,
                pct_threshold: Optional[float] = None,
                fallback: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36") -> Union[str, UserAgentProfile]:
        """Generate user agent string or profile."""
        pass
    
    @staticmethod
    def generate_client_hints(user_agent: str) -> str:
        """Generate Sec-CH-UA header value based on user agent string."""
        def _parse_user_agent(user_agent: str) -> Dict[str, str]:
            """Parse a user agent string to extract browser and version information."""
            browsers = {
                "chrome": r"Chrome/(\d+)",
                "edge": r"Edg/(\d+)", 
                "safari": r"Version/(\d+)",
                "firefox": r"Firefox/(\d+)",
            }
            
            result = {}
            for browser, pattern in browsers.items():
                match = re.search(pattern, user_agent)
                if match:
                    result[browser] = match.group(1)
            
            return result
        
        browsers = _parse_user_agent(user_agent)
        
        # Client hints components
        hints = []
        
        # Handle different browser combinations
        if "chrome" in browsers:
            hints.append(f'"Chromium";v="{browsers["chrome"]}"')
            hints.append('"Not_A Brand";v="8"')
            
            if "edge" in browsers:
                hints.append(f'"Microsoft Edge";v="{browsers["edge"]}"')
            else:
                hints.append(f'"Google Chrome";v="{browsers["chrome"]}"')
        
        elif "firefox" in browsers:
            # Firefox doesn't typically send Sec-CH-UA
            return '""'
        
        elif "safari" in browsers:
            # Safari's format for client hints
            hints.append(f'"Safari";v="{browsers["safari"]}"')
            hints.append('"Not_A Brand";v="8"')
        
        return ", ".join(hints)
    
    @staticmethod
    def parse_user_agent_details(user_agent: str) -> UserAgentProfile:
        """Parse user agent string into detailed profile."""
        # Default values
        browser = "Unknown"
        version = "0.0"
        platform = "Unknown"
        os = "Unknown"
        engine = "Unknown"
        
        # Browser detection patterns
        browser_patterns = {
            'Chrome': r'Chrome/(\d+\.\d+)',
            'Firefox': r'Firefox/(\d+\.\d+)',
            'Safari': r'Version/(\d+\.\d+).*Safari',
            'Edge': r'Edg/(\d+\.\d+)',
            'Opera': r'OPR/(\d+\.\d+)',
            'Internet Explorer': r'MSIE (\d+\.\d+)',
        }
        
        # OS detection patterns
        os_patterns = {
            'Windows': r'Windows NT (\d+\.\d+)',
            'Mac OS': r'Mac OS X (\d+[_\d]*)',
            'Linux': r'Linux',
            'Android': r'Android (\d+\.\d+)',
            'iOS': r'iPhone OS (\d+[_\d]*)',
        }
        
        # Platform detection patterns
        platform_patterns = {
            'Desktop': r'(Windows|Mac OS X|Linux)',
            'Mobile': r'(Android|iPhone|iPad)',
            'Tablet': r'(iPad|Android.*Tablet)',
        }
        
        # Engine detection patterns
        engine_patterns = {
            'WebKit': r'WebKit/(\d+\.\d+)',
            'Gecko': r'Gecko/(\d+)',
            'Blink': r'Chrome.*WebKit',  # Chrome uses Blink (fork of WebKit)
            'EdgeHTML': r'Edge/(\d+\.\d+)',
        }
        
        # Detect browser
        for browser_name, pattern in browser_patterns.items():
            match = re.search(pattern, user_agent)
            if match:
                browser = browser_name
                version = match.group(1)
                break
        
        # Detect OS
        for os_name, pattern in os_patterns.items():
            if re.search(pattern, user_agent):
                os = os_name
                break
        
        # Detect platform
        for platform_name, pattern in platform_patterns.items():
            if re.search(pattern, user_agent):
                platform = platform_name
                break
        
        # Detect engine
        for engine_name, pattern in engine_patterns.items():
            if re.search(pattern, user_agent):
                engine = engine_name
                break
        
        # Generate client hints
        client_hints = UAGenerator.generate_client_hints(user_agent)
        
        return UserAgentProfile(
            browser=browser,
            version=version,
            platform=platform,
            os=os,
            engine=engine,
            full_agent=user_agent,
            client_hints=client_hints
        )


class ValidUAGenerator(UAGenerator):
    """User agent generator using fake-useragent library with validation."""
    
    def __init__(self):
        """Initialize with fallback agents if fake-useragent is not available."""
        self._fallback_agents = [
            # Chrome agents
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Firefox agents
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
            
            # Edge agents
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            
            # Safari agents
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]
        
        # Try to import fake-useragent
        try:
            from fake_useragent import UserAgent
            self.ua = UserAgent()
            self._has_fake_ua = True
        except ImportError:
            logger.warning("fake-useragent not available, using fallback agents")
            self.ua = None
            self._has_fake_ua = False
    
    def generate(self,
                browsers: Optional[List[str]] = None,
                os: Optional[Union[str, List[str]]] = None,
                min_version: float = 0.0,
                platforms: Optional[Union[str, List[str]]] = None,
                pct_threshold: Optional[float] = None,
                fallback: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36") -> str:
        """Generate user agent string using fake-useragent or fallbacks."""
        
        if self._has_fake_ua and self.ua:
            try:
                # Use fake-useragent with specified parameters
                if browsers:
                    # Try to get specific browser
                    browser_name = random.choice(browsers).lower()
                    if hasattr(self.ua, browser_name):
                        return getattr(self.ua, browser_name)
                
                # Get random user agent
                return self.ua.random
                
            except Exception as e:
                logger.warning(f"fake-useragent failed: {str(e)}, using fallback")
        
        # Filter fallback agents by criteria
        suitable_agents = self._fallback_agents
        
        if browsers:
            browser_filters = [b.lower() for b in browsers]
            suitable_agents = [
                agent for agent in suitable_agents
                if any(browser in agent.lower() for browser in browser_filters)
            ]
        
        if os:
            os_list = [os] if isinstance(os, str) else os
            os_filters = [o.lower() for o in os_list]
            suitable_agents = [
                agent for agent in suitable_agents
                if any(os_name in agent.lower() for os_name in os_filters)
            ]
        
        # Return random suitable agent or fallback
        if suitable_agents:
            return random.choice(suitable_agents)
        else:
            return fallback


class OnlineUAGenerator(UAGenerator):
    """User agent generator that fetches fresh agents from online sources."""
    
    def __init__(self, cache_file: Optional[str] = None, cache_duration: int = 24):
        """
        Initialize online UA generator.
        
        Args:
            cache_file: Path to cache file for offline usage
            cache_duration: Cache duration in hours
        """
        self.cache_file = cache_file
        self.cache_duration = cache_duration
        self.agents: List[str] = []
        self.last_fetch: Optional[datetime] = None
        
        # Load cached agents if available
        self._load_cache()
    
    def _load_cache(self):
        """Load cached user agents from file."""
        if not self.cache_file or not Path(self.cache_file).exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.agents = data.get('agents', [])
                last_fetch_str = data.get('last_fetch')
                if last_fetch_str:
                    self.last_fetch = datetime.fromisoformat(last_fetch_str)
        except Exception as e:
            logger.warning(f"Failed to load cached user agents: {str(e)}")
    
    def _save_cache(self):
        """Save user agents to cache file."""
        if not self.cache_file:
            return
        
        try:
            Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'agents': self.agents,
                'last_fetch': self.last_fetch.isoformat() if self.last_fetch else None
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save user agents cache: {str(e)}")
    
    def _needs_refresh(self) -> bool:
        """Check if cache needs refresh."""
        if not self.agents or not self.last_fetch:
            return True
        
        age = datetime.now() - self.last_fetch
        return age > timedelta(hours=self.cache_duration)
    
    def _fetch_agents(self):
        """Fetch user agents from online sources."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("requests and beautifulsoup4 required for online UA generation")
            return
        
        # Try multiple sources
        sources = [
            {
                'url': 'https://www.useragents.me/',
                'selector': '.ua'
            },
            {
                'url': 'https://developers.whatismybrowser.com/useragents/explore/',
                'selector': '.useragent'
            }
        ]
        
        new_agents = []
        
        for source in sources:
            try:
                response = requests.get(
                    source['url'],
                    timeout=10,
                    headers={'Accept': 'text/html,application/xhtml+xml'}
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                elements = soup.select(source['selector'])
                
                for element in elements[:50]:  # Limit to 50 per source
                    agent_text = element.get_text().strip()
                    if agent_text and len(agent_text) > 50:  # Basic validation
                        new_agents.append(agent_text)
                
                if new_agents:
                    logger.info(f"Fetched {len(new_agents)} user agents from {source['url']}")
                    break  # Use first successful source
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {source['url']}: {str(e)}")
                continue
        
        if new_agents:
            self.agents = new_agents
            self.last_fetch = datetime.now()
            self._save_cache()
        else:
            logger.warning("Failed to fetch user agents from all sources")
    
    def generate(self,
                browsers: Optional[List[str]] = None,
                os: Optional[Union[str, List[str]]] = None,
                min_version: float = 0.0,
                platforms: Optional[Union[str, List[str]]] = None,
                pct_threshold: Optional[float] = None,
                fallback: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36") -> str:
        """Generate user agent from online sources."""
        
        # Refresh cache if needed
        if self._needs_refresh():
            self._fetch_agents()
        
        if not self.agents:
            return fallback
        
        # Filter agents by criteria
        suitable_agents = self.agents
        
        if browsers:
            browser_filters = [b.lower() for b in browsers]
            suitable_agents = [
                agent for agent in suitable_agents
                if any(browser in agent.lower() for browser in browser_filters)
            ]
        
        if os:
            os_list = [os] if isinstance(os, str) else os
            os_filters = [o.lower() for o in os_list]
            suitable_agents = [
                agent for agent in suitable_agents
                if any(os_name in agent.lower() for os_name in os_filters)
            ]
        
        # Return random suitable agent
        if suitable_agents:
            return random.choice(suitable_agents)
        else:
            return random.choice(self.agents) if self.agents else fallback


class CustomUAGenerator(UAGenerator):
    """Custom user agent generator with predefined patterns."""
    
    def __init__(self, custom_agents: List[str] = None):
        """
        Initialize with custom agent list.
        
        Args:
            custom_agents: List of custom user agent strings
        """
        self.custom_agents = custom_agents or []
        
        # Add some high-quality default agents if none provided
        if not self.custom_agents:
            self.custom_agents = [
                # Latest Chrome versions
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                
                # Latest Firefox versions
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
                
                # Mobile agents
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            ]
    
    def add_agent(self, agent: str):
        """Add custom user agent."""
        if agent not in self.custom_agents:
            self.custom_agents.append(agent)
    
    def remove_agent(self, agent: str):
        """Remove custom user agent."""
        if agent in self.custom_agents:
            self.custom_agents.remove(agent)
    
    def generate(self,
                browsers: Optional[List[str]] = None,
                os: Optional[Union[str, List[str]]] = None,
                min_version: float = 0.0,
                platforms: Optional[Union[str, List[str]]] = None,
                pct_threshold: Optional[float] = None,
                fallback: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36") -> str:
        """Generate user agent from custom list."""
        
        if not self.custom_agents:
            return fallback
        
        # Filter agents by criteria
        suitable_agents = self.custom_agents
        
        if browsers:
            browser_filters = [b.lower() for b in browsers]
            suitable_agents = [
                agent for agent in suitable_agents
                if any(browser in agent.lower() for browser in browser_filters)
            ]
        
        if os:
            os_list = [os] if isinstance(os, str) else os
            os_filters = [o.lower() for o in os_list]
            suitable_agents = [
                agent for agent in suitable_agents
                if any(os_name in agent.lower() for os_name in os_filters)
            ]
        
        # Return random suitable agent
        return random.choice(suitable_agents) if suitable_agents else fallback


class UserAgentManager:
    """
    Comprehensive user agent management system.
    
    Provides multiple generation strategies and advanced features.
    """
    
    def __init__(self, 
                 default_strategy: str = "valid",
                 cache_dir: Optional[str] = None):
        """
        Initialize user agent manager.
        
        Args:
            default_strategy: Default generation strategy
            cache_dir: Directory for caching online agents
        """
        self.default_strategy = default_strategy
        self.cache_dir = cache_dir
        
        # Initialize generators
        self.generators = {
            'valid': ValidUAGenerator(),
            'online': OnlineUAGenerator(
                cache_file=f"{cache_dir}/online_agents.json" if cache_dir else None
            ),
            'custom': CustomUAGenerator()
        }
        
        # Usage statistics
        self.usage_stats = {strategy: 0 for strategy in self.generators.keys()}
    
    def generate(self, 
                strategy: Optional[str] = None,
                return_profile: bool = False,
                **kwargs) -> Union[str, UserAgentProfile]:
        """
        Generate user agent using specified strategy.
        
        Args:
            strategy: Generation strategy to use
            return_profile: Whether to return detailed profile
            **kwargs: Additional parameters for generation
            
        Returns:
            User agent string or profile
        """
        strategy = strategy or self.default_strategy
        
        if strategy not in self.generators:
            logger.warning(f"Unknown strategy '{strategy}', using default")
            strategy = self.default_strategy
        
        # Generate user agent
        generator = self.generators[strategy]
        user_agent = generator.generate(**kwargs)
        
        # Update usage statistics
        self.usage_stats[strategy] += 1
        
        # Return profile if requested
        if return_profile:
            return UAGenerator.parse_user_agent_details(user_agent)
        else:
            return user_agent
    
    def add_custom_agent(self, agent: str):
        """Add custom user agent to custom generator."""
        custom_gen = self.generators['custom']
        if isinstance(custom_gen, CustomUAGenerator):
            custom_gen.add_agent(agent)
    
    def get_random_profile(self, **kwargs) -> UserAgentProfile:
        """Get random user agent profile with all details."""
        return self.generate(return_profile=True, **kwargs)
    
    def get_mobile_agent(self, **kwargs) -> str:
        """Get mobile-specific user agent."""
        kwargs['platforms'] = ['mobile']
        return self.generate(**kwargs)
    
    def get_desktop_agent(self, **kwargs) -> str:
        """Get desktop-specific user agent."""
        kwargs['platforms'] = ['desktop']
        return self.generate(**kwargs)
    
    def get_chrome_agent(self, **kwargs) -> str:
        """Get Chrome-specific user agent."""
        kwargs['browsers'] = ['Chrome']
        return self.generate(**kwargs)
    
    def get_firefox_agent(self, **kwargs) -> str:
        """Get Firefox-specific user agent."""
        kwargs['browsers'] = ['Firefox']
        return self.generate(**kwargs)
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics for different strategies."""
        return self.usage_stats.copy()
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.usage_stats = {strategy: 0 for strategy in self.generators.keys()}


# Singleton instance
_ua_manager: Optional[UserAgentManager] = None


def get_user_agent_manager(**kwargs) -> UserAgentManager:
    """Get singleton user agent manager."""
    global _ua_manager
    if _ua_manager is None:
        _ua_manager = UserAgentManager(**kwargs)
    return _ua_manager


# Convenience functions
def generate_user_agent(strategy: str = "valid", **kwargs) -> str:
    """Generate user agent using specified strategy."""
    manager = get_user_agent_manager()
    return manager.generate(strategy=strategy, **kwargs)


def get_random_user_agent(**kwargs) -> str:
    """Get random user agent with optional filtering."""
    manager = get_user_agent_manager()
    return manager.generate(**kwargs)


def get_user_agent_with_hints(strategy: str = "valid", **kwargs) -> Tuple[str, str]:
    """Get user agent string with client hints."""
    manager = get_user_agent_manager()
    profile = manager.generate(strategy=strategy, return_profile=True, **kwargs)
    return profile.full_agent, profile.client_hints
