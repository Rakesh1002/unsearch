"""
Advanced proxy rotation strategies for distributed web scraping.

This module provides sophisticated proxy management:
- Multiple rotation strategies (Round Robin, Random, Health-based)
- Proxy health monitoring and failover
- Automatic proxy validation and testing
- Performance-based proxy selection
- Geographic proxy distribution
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

import httpx
import structlog

from app.services.browser_config import ProxyConfig

logger = structlog.get_logger(__name__)


class ProxyStatus(str, Enum):
    """Proxy status enumeration."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    SLOW = "slow"
    UNHEALTHY = "unhealthy"
    BLOCKED = "blocked"
    DISABLED = "disabled"


@dataclass
class ProxyMetrics:
    """Metrics for proxy performance tracking."""
    proxy_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_used: Optional[float] = None
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    consecutive_failures: int = 0
    status: ProxyStatus = ProxyStatus.UNKNOWN
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 100.0 - self.success_rate
    
    def update_success(self, response_time: float):
        """Update metrics for successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_used = time.time()
        self.last_success = time.time()
        
        # Update average response time
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.avg_response_time = (alpha * response_time) + ((1 - alpha) * self.avg_response_time)
        
        # Update status based on response time
        if response_time < 2.0:
            self.status = ProxyStatus.HEALTHY
        elif response_time < 5.0:
            self.status = ProxyStatus.SLOW
        else:
            self.status = ProxyStatus.UNHEALTHY
    
    def update_failure(self, error_type: str = "unknown"):
        """Update metrics for failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_used = time.time()
        self.last_failure = time.time()
        
        # Update status based on failure pattern
        if self.consecutive_failures >= 5:
            if "blocked" in error_type.lower() or "forbidden" in error_type.lower():
                self.status = ProxyStatus.BLOCKED
            else:
                self.status = ProxyStatus.UNHEALTHY
        elif self.failure_rate > 70:
            self.status = ProxyStatus.UNHEALTHY


@dataclass
class ProxyInfo:
    """Enhanced proxy information with metrics."""
    config: ProxyConfig
    metrics: ProxyMetrics = field(init=False)
    region: Optional[str] = None
    isp: Optional[str] = None
    speed_tier: Optional[str] = None  # "fast", "medium", "slow"
    
    def __post_init__(self):
        self.metrics = ProxyMetrics(proxy_id=self._generate_id())
    
    def _generate_id(self) -> str:
        """Generate unique ID for proxy."""
        return f"{self.config.ip}:{urlparse(self.config.server).port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is healthy enough to use."""
        return self.metrics.status in [ProxyStatus.HEALTHY, ProxyStatus.SLOW, ProxyStatus.UNKNOWN]
    
    @property
    def priority_score(self) -> float:
        """Calculate priority score for proxy selection."""
        base_score = 1.0
        
        # Success rate factor
        success_factor = self.metrics.success_rate / 100.0
        
        # Response time factor (lower is better)
        if self.metrics.avg_response_time > 0:
            time_factor = max(0.1, 1.0 - (self.metrics.avg_response_time / 10.0))
        else:
            time_factor = 1.0
        
        # Consecutive failures penalty
        failure_penalty = max(0.1, 1.0 - (self.metrics.consecutive_failures * 0.2))
        
        # Status factor
        status_factors = {
            ProxyStatus.HEALTHY: 1.0,
            ProxyStatus.SLOW: 0.7,
            ProxyStatus.UNKNOWN: 0.8,
            ProxyStatus.UNHEALTHY: 0.2,
            ProxyStatus.BLOCKED: 0.1,
            ProxyStatus.DISABLED: 0.0
        }
        status_factor = status_factors.get(self.metrics.status, 0.5)
        
        return base_score * success_factor * time_factor * failure_penalty * status_factor


class ProxyRotationStrategy(ABC):
    """Abstract base class for proxy rotation strategies."""
    
    def __init__(self, proxies: List[ProxyConfig]):
        """Initialize strategy with proxy list."""
        self.proxy_infos: List[ProxyInfo] = [ProxyInfo(config=p) for p in proxies]
        self.disabled_proxies: Set[str] = set()
        
        # Health checking
        self.health_check_interval = 300  # 5 minutes
        self.last_health_check = 0
        self.health_check_url = "http://httpbin.org/ip"
        self.health_check_timeout = 10.0
    
    @abstractmethod
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy according to strategy."""
        pass
    
    async def add_proxies(self, proxies: List[ProxyConfig]):
        """Add new proxies to the rotation."""
        new_proxy_infos = [ProxyInfo(config=p) for p in proxies]
        self.proxy_infos.extend(new_proxy_infos)
        logger.info(f"Added {len(proxies)} proxies to rotation")
    
    def remove_proxy(self, proxy_id: str):
        """Remove proxy from rotation."""
        self.proxy_infos = [p for p in self.proxy_infos if p.metrics.proxy_id != proxy_id]
        self.disabled_proxies.discard(proxy_id)
        logger.info(f"Removed proxy {proxy_id} from rotation")
    
    def disable_proxy(self, proxy_id: str):
        """Temporarily disable a proxy."""
        self.disabled_proxies.add(proxy_id)
        for proxy_info in self.proxy_infos:
            if proxy_info.metrics.proxy_id == proxy_id:
                proxy_info.metrics.status = ProxyStatus.DISABLED
        logger.warning(f"Disabled proxy {proxy_id}")
    
    def enable_proxy(self, proxy_id: str):
        """Re-enable a disabled proxy."""
        self.disabled_proxies.discard(proxy_id)
        for proxy_info in self.proxy_infos:
            if proxy_info.metrics.proxy_id == proxy_id:
                if proxy_info.metrics.status == ProxyStatus.DISABLED:
                    proxy_info.metrics.status = ProxyStatus.UNKNOWN
        logger.info(f"Enabled proxy {proxy_id}")
    
    def record_success(self, proxy: ProxyConfig, response_time: float):
        """Record successful proxy usage."""
        proxy_id = f"{proxy.ip}:{urlparse(proxy.server).port}"
        
        for proxy_info in self.proxy_infos:
            if proxy_info.metrics.proxy_id == proxy_id:
                proxy_info.metrics.update_success(response_time)
                break
    
    def record_failure(self, proxy: ProxyConfig, error_type: str = "unknown"):
        """Record failed proxy usage."""
        proxy_id = f"{proxy.ip}:{urlparse(proxy.server).port}"
        
        for proxy_info in self.proxy_infos:
            if proxy_info.metrics.proxy_id == proxy_id:
                proxy_info.metrics.update_failure(error_type)
                
                # Auto-disable if too many consecutive failures
                if proxy_info.metrics.consecutive_failures >= 10:
                    self.disable_proxy(proxy_id)
                break
    
    async def health_check_proxies(self):
        """Perform health check on all proxies."""
        current_time = time.time()
        
        if current_time - self.last_health_check < self.health_check_interval:
            return
        
        logger.info("Starting proxy health check")
        
        async def check_proxy(proxy_info: ProxyInfo) -> None:
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_info.config.server, "https://": proxy_info.config.server},
                    timeout=self.health_check_timeout
                ) as client:
                    start_time = time.time()
                    response = await client.get(self.health_check_url)
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        proxy_info.metrics.update_success(response_time)
                    else:
                        proxy_info.metrics.update_failure(f"status_{response.status_code}")
            
            except Exception as e:
                proxy_info.metrics.update_failure(str(e))
        
        # Check all proxies concurrently
        tasks = [check_proxy(proxy_info) for proxy_info in self.proxy_infos]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.last_health_check = current_time
        
        # Log health check results
        healthy_count = sum(1 for p in self.proxy_infos if p.is_healthy)
        logger.info(f"Proxy health check completed: {healthy_count}/{len(self.proxy_infos)} proxies healthy")
    
    def get_available_proxies(self) -> List[ProxyInfo]:
        """Get list of available (healthy and enabled) proxies."""
        available = []
        for proxy_info in self.proxy_infos:
            if (proxy_info.metrics.proxy_id not in self.disabled_proxies and 
                proxy_info.is_healthy):
                available.append(proxy_info)
        return available
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get comprehensive proxy statistics."""
        total_proxies = len(self.proxy_infos)
        available_proxies = len(self.get_available_proxies())
        disabled_proxies = len(self.disabled_proxies)
        
        status_counts = {}
        for status in ProxyStatus:
            status_counts[status.value] = sum(1 for p in self.proxy_infos if p.metrics.status == status)
        
        # Calculate aggregate metrics
        total_requests = sum(p.metrics.total_requests for p in self.proxy_infos)
        total_successes = sum(p.metrics.successful_requests for p in self.proxy_infos)
        avg_success_rate = (total_successes / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_time = sum(p.metrics.avg_response_time for p in self.proxy_infos if p.metrics.avg_response_time > 0)
        if avg_response_time > 0:
            active_proxies = sum(1 for p in self.proxy_infos if p.metrics.avg_response_time > 0)
            avg_response_time = avg_response_time / active_proxies if active_proxies > 0 else 0
        
        return {
            'total_proxies': total_proxies,
            'available_proxies': available_proxies,
            'disabled_proxies': disabled_proxies,
            'status_distribution': status_counts,
            'aggregate_metrics': {
                'total_requests': total_requests,
                'success_rate': avg_success_rate,
                'avg_response_time': avg_response_time
            },
            'top_performers': [
                {
                    'proxy_id': p.metrics.proxy_id,
                    'success_rate': p.metrics.success_rate,
                    'avg_response_time': p.metrics.avg_response_time,
                    'priority_score': p.priority_score
                }
                for p in sorted(self.proxy_infos, key=lambda x: x.priority_score, reverse=True)[:5]
            ]
        }


class RoundRobinProxyStrategy(ProxyRotationStrategy):
    """Round-robin proxy rotation strategy."""
    
    def __init__(self, proxies: List[ProxyConfig]):
        """Initialize round-robin strategy."""
        super().__init__(proxies)
        self.current_index = 0
    
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy using round-robin selection."""
        # Perform health check if needed
        await self.health_check_proxies()
        
        available_proxies = self.get_available_proxies()
        if not available_proxies:
            logger.warning("No available proxies for round-robin selection")
            return None
        
        # Select proxy using round-robin
        proxy_info = available_proxies[self.current_index % len(available_proxies)]
        self.current_index += 1
        
        return proxy_info.config


class RandomProxyStrategy(ProxyRotationStrategy):
    """Random proxy rotation strategy."""
    
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy using random selection."""
        # Perform health check if needed
        await self.health_check_proxies()
        
        available_proxies = self.get_available_proxies()
        if not available_proxies:
            logger.warning("No available proxies for random selection")
            return None
        
        # Select random proxy
        proxy_info = random.choice(available_proxies)
        return proxy_info.config


class WeightedProxyStrategy(ProxyRotationStrategy):
    """Weighted proxy rotation based on performance metrics."""
    
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy using weighted selection based on performance."""
        # Perform health check if needed
        await self.health_check_proxies()
        
        available_proxies = self.get_available_proxies()
        if not available_proxies:
            logger.warning("No available proxies for weighted selection")
            return None
        
        # Calculate weights based on priority scores
        weights = [max(0.1, proxy_info.priority_score) for proxy_info in available_proxies]
        total_weight = sum(weights)
        
        if total_weight == 0:
            # Fallback to random selection
            proxy_info = random.choice(available_proxies)
        else:
            # Weighted random selection
            r = random.uniform(0, total_weight)
            cumulative_weight = 0
            proxy_info = available_proxies[0]  # Default fallback
            
            for i, weight in enumerate(weights):
                cumulative_weight += weight
                if r <= cumulative_weight:
                    proxy_info = available_proxies[i]
                    break
        
        return proxy_info.config


class GeographicProxyStrategy(ProxyRotationStrategy):
    """Geographic-based proxy rotation strategy."""
    
    def __init__(self, proxies: List[ProxyConfig], preferred_regions: List[str] = None):
        """
        Initialize geographic strategy.
        
        Args:
            proxies: List of proxy configurations
            preferred_regions: Preferred regions for proxy selection
        """
        super().__init__(proxies)
        self.preferred_regions = preferred_regions or []
        
        # Set regions for proxies (in real implementation, would use IP geolocation)
        self._assign_regions()
    
    def _assign_regions(self):
        """Assign regions to proxies (mock implementation)."""
        mock_regions = ["us-east", "us-west", "eu-west", "ap-southeast"]
        
        for proxy_info in self.proxy_infos:
            # In real implementation, would use IP geolocation service
            proxy_info.region = random.choice(mock_regions)
    
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy with geographic preference."""
        # Perform health check if needed
        await self.health_check_proxies()
        
        available_proxies = self.get_available_proxies()
        if not available_proxies:
            logger.warning("No available proxies for geographic selection")
            return None
        
        # Filter by preferred regions if specified
        if self.preferred_regions:
            preferred_proxies = [
                p for p in available_proxies 
                if p.region in self.preferred_regions
            ]
            if preferred_proxies:
                available_proxies = preferred_proxies
        
        # Use weighted selection within geographic constraints
        weights = [max(0.1, proxy_info.priority_score) for proxy_info in available_proxies]
        total_weight = sum(weights)
        
        if total_weight == 0:
            proxy_info = random.choice(available_proxies)
        else:
            r = random.uniform(0, total_weight)
            cumulative_weight = 0
            proxy_info = available_proxies[0]
            
            for i, weight in enumerate(weights):
                cumulative_weight += weight
                if r <= cumulative_weight:
                    proxy_info = available_proxies[i]
                    break
        
        return proxy_info.config


# Factory function
def create_proxy_strategy(
    strategy_type: str,
    proxies: List[ProxyConfig],
    config: Dict[str, Any] = None
) -> ProxyRotationStrategy:
    """
    Create proxy rotation strategy.
    
    Args:
        strategy_type: Type of strategy ("round_robin", "random", "weighted", "geographic")
        proxies: List of proxy configurations
        config: Additional strategy configuration
        
    Returns:
        Configured proxy rotation strategy
    """
    config = config or {}
    
    strategies = {
        "round_robin": RoundRobinProxyStrategy,
        "random": RandomProxyStrategy,
        "weighted": WeightedProxyStrategy,
        "geographic": GeographicProxyStrategy
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy type: {strategy_type}. Available: {list(strategies.keys())}")
    
    strategy_class = strategies[strategy_type]
    
    # Handle special configuration for geographic strategy
    if strategy_type == "geographic":
        preferred_regions = config.get("preferred_regions", [])
        return strategy_class(proxies, preferred_regions)
    else:
        return strategy_class(proxies)


# Convenience functions
def create_proxy_list_from_strings(proxy_strings: List[str]) -> List[ProxyConfig]:
    """Create ProxyConfig list from string representations."""
    proxies = []
    for proxy_str in proxy_strings:
        try:
            proxy_config = ProxyConfig.from_string(proxy_str)
            proxies.append(proxy_config)
        except Exception as e:
            logger.warning(f"Invalid proxy string '{proxy_str}': {str(e)}")
    
    return proxies


async def test_proxy_rotation(
    strategy: ProxyRotationStrategy,
    num_requests: int = 10
) -> Dict[str, Any]:
    """Test proxy rotation strategy with multiple requests."""
    results = {
        'total_requests': num_requests,
        'proxy_usage': {},
        'errors': []
    }
    
    for i in range(num_requests):
        try:
            proxy = await strategy.get_next_proxy()
            if proxy:
                proxy_id = f"{proxy.ip}:{urlparse(proxy.server).port}"
                results['proxy_usage'][proxy_id] = results['proxy_usage'].get(proxy_id, 0) + 1
            else:
                results['errors'].append(f"Request {i}: No proxy available")
        except Exception as e:
            results['errors'].append(f"Request {i}: {str(e)}")
    
    return results
