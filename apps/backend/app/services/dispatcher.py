"""
Advanced dispatcher system for managing concurrent crawling operations.

This module provides sophisticated dispatchers for controlling:
- Concurrent request management  
- Rate limiting and throttling
- Memory-aware resource allocation
- Adaptive performance optimization
"""

import asyncio
import time
import psutil
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict, deque

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DispatchStats:
    """Statistics for dispatcher operations."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    avg_response_time: float = 0.0
    peak_memory_usage: float = 0.0
    current_active: int = 0
    
    def update_response_time(self, response_time: float):
        """Update average response time with new measurement."""
        if self.successful_requests == 0:
            self.avg_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.avg_response_time = (alpha * response_time) + ((1 - alpha) * self.avg_response_time)


@dataclass
class TaskResult:
    """Result of a dispatched task."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    memory_usage: float = 0.0
    
    @property
    def duration(self) -> float:
        """Get task duration in seconds."""
        return self.end_time - self.start_time if self.end_time > self.start_time else 0.0


class BaseDispatcher(ABC):
    """Abstract base class for all dispatchers."""
    
    def __init__(self, max_concurrent: int = 10, **kwargs):
        """
        Initialize base dispatcher.
        
        Args:
            max_concurrent: Maximum concurrent operations
            **kwargs: Additional configuration options
        """
        self.max_concurrent = max_concurrent
        self.stats = DispatchStats()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.verbose = kwargs.get('verbose', False)
    
    @abstractmethod
    async def dispatch(
        self,
        tasks: List[Callable[..., Awaitable[Any]]],
        *args,
        **kwargs
    ) -> List[TaskResult]:
        """
        Dispatch tasks for execution.
        
        Args:
            tasks: List of async callables to execute
            *args: Arguments to pass to each task
            **kwargs: Keyword arguments to pass to each task
            
        Returns:
            List of TaskResult objects
        """
        pass
    
    async def cleanup(self):
        """Cleanup dispatcher resources."""
        # Cancel any remaining active tasks
        for task in self.active_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish cancellation
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        self.active_tasks.clear()


class SemaphoreDispatcher(BaseDispatcher):
    """
    Simple semaphore-based dispatcher for basic concurrency control.
    
    Uses asyncio.Semaphore to limit concurrent operations without
    sophisticated rate limiting or memory management.
    """
    
    def __init__(self, max_concurrent: int = 10, **kwargs):
        """Initialize semaphore dispatcher."""
        super().__init__(max_concurrent, **kwargs)
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def dispatch(
        self,
        tasks: List[Callable[..., Awaitable[Any]]],
        *args,
        **kwargs
    ) -> List[TaskResult]:
        """Dispatch tasks with semaphore-based concurrency control."""
        if not tasks:
            return []
        
        # Create task wrappers
        wrapped_tasks = []
        for i, task in enumerate(tasks):
            task_id = f"task_{i}_{int(time.time() * 1000)}"
            wrapped_task = self._wrap_task(task, task_id, *args, **kwargs)
            wrapped_tasks.append(wrapped_task)
        
        # Execute all tasks
        results = await asyncio.gather(*wrapped_tasks, return_exceptions=True)
        
        # Process results
        task_results = []
        for result in results:
            if isinstance(result, TaskResult):
                task_results.append(result)
            elif isinstance(result, Exception):
                task_results.append(TaskResult(
                    task_id=f"error_{int(time.time())}",
                    success=False,
                    error=str(result)
                ))
            else:
                task_results.append(TaskResult(
                    task_id=f"unknown_{int(time.time())}",
                    success=True,
                    result=result
                ))
        
        return task_results
    
    async def _wrap_task(
        self,
        task: Callable[..., Awaitable[Any]],
        task_id: str,
        *args,
        **kwargs
    ) -> TaskResult:
        """Wrap task with semaphore and monitoring."""
        async with self.semaphore:
            start_time = time.time()
            start_memory = psutil.virtual_memory().used
            
            self.stats.current_active += 1
            self.stats.total_requests += 1
            
            try:
                result = await task(*args, **kwargs)
                
                end_time = time.time()
                end_memory = psutil.virtual_memory().used
                memory_usage = end_memory - start_memory
                
                self.stats.successful_requests += 1
                self.stats.update_response_time(end_time - start_time)
                self.stats.peak_memory_usage = max(
                    self.stats.peak_memory_usage, 
                    memory_usage
                )
                
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    memory_usage=memory_usage
                )
                
            except Exception as e:
                end_time = time.time()
                self.stats.failed_requests += 1
                
                logger.error(f"Task {task_id} failed: {str(e)}")
                
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    start_time=start_time,
                    end_time=end_time
                )
            
            finally:
                self.stats.current_active -= 1


class RateLimiter:
    """
    Advanced rate limiter with multiple strategies.
    
    Supports:
    - Token bucket algorithm
    - Sliding window rate limiting
    - Per-domain rate limiting
    - Adaptive rate adjustment
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        time_window: float = 60.0,  # seconds
        burst_size: Optional[int] = None,
        per_domain: bool = False
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
            burst_size: Maximum burst size (defaults to max_requests)
            per_domain: Whether to apply rate limiting per domain
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.burst_size = burst_size or max_requests
        self.per_domain = per_domain
        
        # Token bucket state
        self.tokens = self.burst_size
        self.last_refill = time.time()
        
        # Per-domain limiters
        self.domain_limiters: Dict[str, 'RateLimiter'] = {}
        
        # Request history for sliding window
        self.request_history = deque()
        
        self.lock = asyncio.Lock()
    
    async def acquire(self, domain: Optional[str] = None) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            domain: Domain for per-domain limiting
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self.lock:
            current_time = time.time()
            
            # Per-domain rate limiting
            if self.per_domain and domain:
                if domain not in self.domain_limiters:
                    self.domain_limiters[domain] = RateLimiter(
                        max_requests=self.max_requests,
                        time_window=self.time_window,
                        burst_size=self.burst_size,
                        per_domain=False  # Avoid infinite recursion
                    )
                return await self.domain_limiters[domain].acquire()
            
            # Refill tokens based on elapsed time
            self._refill_tokens(current_time)
            
            # Check if we have tokens available
            if self.tokens >= 1:
                self.tokens -= 1
                self.request_history.append(current_time)
                return True
            
            return False
    
    def _refill_tokens(self, current_time: float):
        """Refill token bucket based on elapsed time."""
        elapsed = current_time - self.last_refill
        
        if elapsed > 0:
            # Calculate tokens to add
            refill_rate = self.max_requests / self.time_window
            new_tokens = elapsed * refill_rate
            
            # Add tokens up to burst size
            self.tokens = min(self.burst_size, self.tokens + new_tokens)
            self.last_refill = current_time
    
    def get_wait_time(self) -> float:
        """Get estimated wait time before next request can be made."""
        if self.tokens >= 1:
            return 0.0
        
        # Calculate time needed for one token
        refill_rate = self.max_requests / self.time_window
        return 1.0 / refill_rate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        current_time = time.time()
        
        # Clean old requests from history
        cutoff_time = current_time - self.time_window
        while self.request_history and self.request_history[0] < cutoff_time:
            self.request_history.popleft()
        
        return {
            "current_tokens": self.tokens,
            "max_tokens": self.burst_size,
            "requests_in_window": len(self.request_history),
            "max_requests_per_window": self.max_requests,
            "time_window": self.time_window,
            "estimated_wait_time": self.get_wait_time()
        }


class MemoryAdaptiveDispatcher(BaseDispatcher):
    """
    Memory-aware dispatcher that adapts concurrency based on system resources.
    
    This dispatcher monitors system memory usage and automatically adjusts
    the number of concurrent operations to prevent resource exhaustion.
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        memory_threshold: float = 80.0,  # Percentage
        rate_limiter: Optional[RateLimiter] = None,
        **kwargs
    ):
        """
        Initialize memory-adaptive dispatcher.
        
        Args:
            max_concurrent: Maximum concurrent operations
            memory_threshold: Memory usage threshold percentage (0-100)
            rate_limiter: Optional rate limiter instance
        """
        super().__init__(max_concurrent, **kwargs)
        self.memory_threshold = memory_threshold
        self.rate_limiter = rate_limiter or RateLimiter()
        
        # Adaptive parameters
        self.current_max_concurrent = max_concurrent
        self.adaptation_history = deque(maxlen=10)
        self.last_adaptation = time.time()
        
        # Performance tracking
        self.performance_window = deque(maxlen=100)
        
        # Create semaphore
        self.semaphore = asyncio.Semaphore(self.current_max_concurrent)
    
    async def dispatch(
        self,
        tasks: List[Callable[..., Awaitable[Any]]],
        *args,
        **kwargs
    ) -> List[TaskResult]:
        """Dispatch tasks with memory-adaptive concurrency control."""
        if not tasks:
            return []
        
        # Adapt concurrency based on current conditions
        await self._adapt_concurrency()
        
        # Create task wrappers with rate limiting
        wrapped_tasks = []
        for i, task in enumerate(tasks):
            task_id = f"task_{i}_{int(time.time() * 1000)}"
            wrapped_task = self._wrap_task_with_rate_limiting(
                task, task_id, *args, **kwargs
            )
            wrapped_tasks.append(wrapped_task)
        
        # Execute all tasks
        results = await asyncio.gather(*wrapped_tasks, return_exceptions=True)
        
        # Process and return results
        return self._process_results(results)
    
    async def _adapt_concurrency(self):
        """Adapt concurrency level based on system conditions."""
        current_time = time.time()
        
        # Only adapt periodically to avoid thrashing
        if current_time - self.last_adaptation < 5.0:  # 5 second cooldown
            return
        
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=0.1)
        
        # Calculate performance score
        performance_score = self._calculate_performance_score()
        
        # Determine adaptation direction
        should_increase = (
            memory_usage < self.memory_threshold * 0.7 and
            cpu_usage < 70.0 and
            performance_score > 0.8 and
            self.current_max_concurrent < self.max_concurrent
        )
        
        should_decrease = (
            memory_usage > self.memory_threshold or
            cpu_usage > 90.0 or
            performance_score < 0.5
        )
        
        old_limit = self.current_max_concurrent
        
        if should_increase:
            self.current_max_concurrent = min(
                self.max_concurrent,
                int(self.current_max_concurrent * 1.2)
            )
        elif should_decrease:
            self.current_max_concurrent = max(
                1,
                int(self.current_max_concurrent * 0.8)
            )
        
        # Update semaphore if limit changed
        if self.current_max_concurrent != old_limit:
            self.semaphore = asyncio.Semaphore(self.current_max_concurrent)
            
            self.adaptation_history.append({
                'timestamp': current_time,
                'old_limit': old_limit,
                'new_limit': self.current_max_concurrent,
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage,
                'performance_score': performance_score
            })
            
            if self.verbose:
                logger.info(
                    f"Adapted concurrency: {old_limit} -> {self.current_max_concurrent} "
                    f"(mem: {memory_usage:.1f}%, cpu: {cpu_usage:.1f}%, perf: {performance_score:.2f})"
                )
        
        self.last_adaptation = current_time
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-1)."""
        if not self.performance_window:
            return 1.0
        
        # Calculate success rate
        successful_tasks = sum(1 for p in self.performance_window if p['success'])
        success_rate = successful_tasks / len(self.performance_window)
        
        # Calculate average response time score (lower is better)
        avg_response_time = sum(p['response_time'] for p in self.performance_window) / len(self.performance_window)
        response_time_score = max(0.0, 1.0 - (avg_response_time / 30.0))  # 30s baseline
        
        # Calculate memory efficiency score
        if self.stats.peak_memory_usage > 0:
            memory_score = max(0.0, 1.0 - (self.stats.peak_memory_usage / (1024 * 1024 * 1024)))  # 1GB baseline
        else:
            memory_score = 1.0
        
        # Weighted combination
        return (success_rate * 0.5) + (response_time_score * 0.3) + (memory_score * 0.2)
    
    async def _wrap_task_with_rate_limiting(
        self,
        task: Callable[..., Awaitable[Any]],
        task_id: str,
        *args,
        **kwargs
    ) -> TaskResult:
        """Wrap task with both semaphore and rate limiting."""
        # Rate limiting check
        domain = kwargs.get('domain') or kwargs.get('url', '').split('//')[-1].split('/')[0] if kwargs.get('url') else None
        
        while not await self.rate_limiter.acquire(domain):
            wait_time = self.rate_limiter.get_wait_time()
            await asyncio.sleep(max(0.1, wait_time))
            self.stats.rate_limited_requests += 1
        
        # Semaphore-based execution
        async with self.semaphore:
            start_time = time.time()
            start_memory = psutil.virtual_memory().used
            
            self.stats.current_active += 1
            self.stats.total_requests += 1
            
            try:
                result = await task(*args, **kwargs)
                
                end_time = time.time()
                end_memory = psutil.virtual_memory().used
                memory_usage = end_memory - start_memory
                response_time = end_time - start_time
                
                self.stats.successful_requests += 1
                self.stats.update_response_time(response_time)
                self.stats.peak_memory_usage = max(
                    self.stats.peak_memory_usage,
                    memory_usage
                )
                
                # Track performance
                self.performance_window.append({
                    'success': True,
                    'response_time': response_time,
                    'memory_usage': memory_usage
                })
                
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    memory_usage=memory_usage
                )
                
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                
                self.stats.failed_requests += 1
                
                # Track performance
                self.performance_window.append({
                    'success': False,
                    'response_time': response_time,
                    'memory_usage': 0
                })
                
                logger.error(f"Task {task_id} failed: {str(e)}")
                
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    start_time=start_time,
                    end_time=end_time
                )
            
            finally:
                self.stats.current_active -= 1
    
    def _process_results(self, results: List[Any]) -> List[TaskResult]:
        """Process raw results into TaskResult objects."""
        task_results = []
        
        for result in results:
            if isinstance(result, TaskResult):
                task_results.append(result)
            elif isinstance(result, Exception):
                task_results.append(TaskResult(
                    task_id=f"error_{int(time.time())}",
                    success=False,
                    error=str(result)
                ))
            else:
                task_results.append(TaskResult(
                    task_id=f"success_{int(time.time())}",
                    success=True,
                    result=result
                ))
        
        return task_results
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        rate_limiter_stats = self.rate_limiter.get_stats()
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent()
        
        return {
            "dispatcher_stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "rate_limited_requests": self.stats.rate_limited_requests,
                "success_rate": self.stats.successful_requests / max(1, self.stats.total_requests),
                "avg_response_time": self.stats.avg_response_time,
                "current_active": self.stats.current_active
            },
            "resource_usage": {
                "memory_percent": memory_usage,
                "cpu_percent": cpu_usage,
                "peak_memory_usage_bytes": self.stats.peak_memory_usage
            },
            "concurrency": {
                "max_concurrent": self.max_concurrent,
                "current_max_concurrent": self.current_max_concurrent,
                "adaptation_count": len(self.adaptation_history)
            },
            "rate_limiting": rate_limiter_stats,
            "performance_score": self._calculate_performance_score()
        }


# Factory functions
def create_dispatcher(
    dispatcher_type: str = "memory_adaptive",
    max_concurrent: int = 10,
    **kwargs
) -> BaseDispatcher:
    """
    Factory function to create dispatchers.
    
    Args:
        dispatcher_type: Type of dispatcher ("semaphore", "memory_adaptive")
        max_concurrent: Maximum concurrent operations
        **kwargs: Additional configuration
        
    Returns:
        Configured dispatcher instance
    """
    dispatchers = {
        "semaphore": SemaphoreDispatcher,
        "memory_adaptive": MemoryAdaptiveDispatcher
    }
    
    if dispatcher_type not in dispatchers:
        raise ValueError(f"Unknown dispatcher type: {dispatcher_type}. Available: {list(dispatchers.keys())}")
    
    dispatcher_class = dispatchers[dispatcher_type]
    return dispatcher_class(max_concurrent=max_concurrent, **kwargs)


def create_rate_limiter(
    max_requests: int = 100,
    time_window: float = 60.0,
    per_domain: bool = True
) -> RateLimiter:
    """Create a rate limiter with common settings."""
    return RateLimiter(
        max_requests=max_requests,
        time_window=time_window,
        per_domain=per_domain
    )
