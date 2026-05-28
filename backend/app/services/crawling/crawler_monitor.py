"""
Advanced crawler monitoring system with real-time status tracking and metrics.

This module provides comprehensive monitoring capabilities:
- Real-time crawling status and progress tracking
- Performance metrics collection
- Resource usage monitoring
- Terminal UI for live monitoring
- Event logging and statistics
- Configurable alerts and thresholds
"""

import time
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque, defaultdict

import psutil
import structlog

logger = structlog.get_logger(__name__)


class CrawlStatus(str, Enum):
    """Crawling status enumeration."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TaskMetrics:
    """Metrics for individual crawler tasks."""
    task_id: str
    url: str
    status: CrawlStatus
    start_time: float
    end_time: Optional[float] = None
    response_time: Optional[float] = None
    status_code: Optional[int] = None
    content_length: int = 0
    error: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Get task duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status in [CrawlStatus.COMPLETED, CrawlStatus.ERROR]


@dataclass
class SystemMetrics:
    """System resource metrics."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    active_connections: int = 0
    
    @classmethod
    def current(cls) -> "SystemMetrics":
        """Get current system metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        
        return cls(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            disk_io_read_mb=disk_io.read_bytes / 1024 / 1024 if disk_io else 0,
            disk_io_write_mb=disk_io.write_bytes / 1024 / 1024 if disk_io else 0,
            network_io_sent_mb=network_io.bytes_sent / 1024 / 1024 if network_io else 0,
            network_io_recv_mb=network_io.bytes_recv / 1024 / 1024 if network_io else 0
        )


@dataclass
class CrawlerStats:
    """Comprehensive crawler statistics."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Task counters
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_tasks: int = 0
    
    # Performance metrics
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    total_bytes_downloaded: int = 0
    
    # Status code distribution
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Error tracking
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Rate metrics
    current_rate: float = 0.0  # requests per second
    peak_rate: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def duration(self) -> float:
        """Get total crawling duration."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def throughput(self) -> float:
        """Calculate overall throughput (requests per second)."""
        duration = self.duration
        if duration > 0:
            return self.total_tasks / duration
        return 0.0


class CrawlerMonitor:
    """
    Advanced crawler monitoring system.
    
    Provides real-time monitoring, metrics collection, and performance tracking
    for web crawling operations.
    """
    
    def __init__(self,
                 update_interval: float = 1.0,
                 max_history_size: int = 1000,
                 enable_terminal_ui: bool = False):
        """
        Initialize crawler monitor.
        
        Args:
            update_interval: Update interval for metrics collection
            max_history_size: Maximum number of metrics to keep in history
            enable_terminal_ui: Whether to enable terminal UI
        """
        self.update_interval = update_interval
        self.max_history_size = max_history_size
        self.enable_terminal_ui = enable_terminal_ui
        
        # Monitoring state
        self.is_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self.stats = CrawlerStats()
        self.active_tasks: Dict[str, TaskMetrics] = {}
        self.completed_tasks: deque = deque(maxlen=max_history_size)
        
        # System metrics history
        self.system_metrics_history: deque = deque(maxlen=max_history_size)
        
        # Rate tracking
        self._rate_window = deque(maxlen=60)  # 1 minute window
        
        # Event callbacks
        self._event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Terminal UI
        self._terminal_ui = None
        if enable_terminal_ui:
            try:
                self._terminal_ui = TerminalUI()
            except ImportError:
                logger.warning("Terminal UI dependencies not available")
    
    def start(self):
        """Start the monitoring system."""
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        # Start terminal UI if enabled
        if self._terminal_ui:
            self._terminal_ui.start(self)
        
        logger.info("Crawler monitor started")
        self._trigger_event('monitor_started', {})
    
    def stop(self):
        """Stop the monitoring system."""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        # Stop terminal UI
        if self._terminal_ui:
            self._terminal_ui.stop()
        
        # Wait for monitor thread
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        # Mark stats end time
        self.stats.end_time = time.time()
        
        logger.info("Crawler monitor stopped")
        self._trigger_event('monitor_stopped', {'stats': self.stats})
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Update system metrics
                system_metrics = SystemMetrics.current()
                system_metrics.active_connections = len(self.active_tasks)
                self.system_metrics_history.append(system_metrics)
                
                # Update rate metrics
                self._update_rate_metrics()
                
                # Check for alerts
                self._check_alerts(system_metrics)
                
                # Sleep until next update
                self._stop_event.wait(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")
                time.sleep(self.update_interval)
    
    def _update_rate_metrics(self):
        """Update rate-based metrics."""
        current_time = time.time()
        current_active = len(self.active_tasks)
        
        # Add current measurement to rate window
        self._rate_window.append((current_time, current_active))
        
        # Calculate current rate (requests per second over last 10 seconds)
        ten_seconds_ago = current_time - 10.0
        recent_measurements = [(t, count) for t, count in self._rate_window if t > ten_seconds_ago]
        
        if len(recent_measurements) >= 2:
            # Calculate rate based on change in active tasks
            start_time, start_count = recent_measurements[0]
            end_time, end_count = recent_measurements[-1]
            
            time_diff = end_time - start_time
            if time_diff > 0:
                # This is a simplified rate calculation
                completed_in_window = max(0, self.stats.completed_tasks - getattr(self, '_last_completed_count', 0))
                self.stats.current_rate = completed_in_window / time_diff
                
                # Update peak rate
                if self.stats.current_rate > self.stats.peak_rate:
                    self.stats.peak_rate = self.stats.current_rate
        
        # Store count for next calculation
        self._last_completed_count = self.stats.completed_tasks
    
    def _check_alerts(self, system_metrics: SystemMetrics):
        """Check for alert conditions."""
        alerts = []
        
        # High CPU usage
        if system_metrics.cpu_percent > 90:
            alerts.append({
                'type': 'high_cpu',
                'message': f'High CPU usage: {system_metrics.cpu_percent:.1f}%',
                'severity': 'warning'
            })
        
        # High memory usage
        if system_metrics.memory_percent > 85:
            alerts.append({
                'type': 'high_memory',
                'message': f'High memory usage: {system_metrics.memory_percent:.1f}%',
                'severity': 'warning'
            })
        
        # Low success rate
        if self.stats.total_tasks > 10 and self.stats.success_rate < 50:
            alerts.append({
                'type': 'low_success_rate',
                'message': f'Low success rate: {self.stats.success_rate:.1f}%',
                'severity': 'error'
            })
        
        # Trigger alert events
        for alert in alerts:
            self._trigger_event('alert', alert)
    
    def task_started(self, task_id: str, url: str):
        """Record task start."""
        task_metrics = TaskMetrics(
            task_id=task_id,
            url=url,
            status=CrawlStatus.STARTING,
            start_time=time.time()
        )
        
        self.active_tasks[task_id] = task_metrics
        self.stats.total_tasks += 1
        self.stats.active_tasks = len(self.active_tasks)
        
        self._trigger_event('task_started', {'task_id': task_id, 'url': url})
    
    def task_completed(self, 
                      task_id: str, 
                      status_code: Optional[int] = None,
                      content_length: int = 0,
                      response_time: Optional[float] = None):
        """Record task completion."""
        task_metrics = self.active_tasks.get(task_id)
        if not task_metrics:
            return
        
        # Update task metrics
        task_metrics.end_time = time.time()
        task_metrics.status = CrawlStatus.COMPLETED
        task_metrics.status_code = status_code
        task_metrics.content_length = content_length
        task_metrics.response_time = response_time or task_metrics.duration
        
        # Update statistics
        self.stats.completed_tasks += 1
        self.stats.active_tasks = len(self.active_tasks) - 1
        self.stats.total_bytes_downloaded += content_length
        
        if status_code:
            self.stats.status_codes[status_code] += 1
        
        if task_metrics.response_time:
            # Update response time statistics
            rt = task_metrics.response_time
            self.stats.min_response_time = min(self.stats.min_response_time, rt)
            self.stats.max_response_time = max(self.stats.max_response_time, rt)
            
            # Update average response time
            total_completed = self.stats.completed_tasks
            if total_completed > 1:
                self.stats.avg_response_time = (
                    (self.stats.avg_response_time * (total_completed - 1) + rt) / total_completed
                )
            else:
                self.stats.avg_response_time = rt
        
        # Move to completed tasks
        self.completed_tasks.append(task_metrics)
        del self.active_tasks[task_id]
        
        self._trigger_event('task_completed', {
            'task_id': task_id, 
            'status_code': status_code,
            'response_time': task_metrics.response_time
        })
    
    def task_failed(self, task_id: str, error: str):
        """Record task failure."""
        task_metrics = self.active_tasks.get(task_id)
        if not task_metrics:
            return
        
        # Update task metrics
        task_metrics.end_time = time.time()
        task_metrics.status = CrawlStatus.ERROR
        task_metrics.error = error
        
        # Update statistics
        self.stats.failed_tasks += 1
        self.stats.active_tasks = len(self.active_tasks) - 1
        self.stats.errors[error] += 1
        
        # Move to completed tasks
        self.completed_tasks.append(task_metrics)
        del self.active_tasks[task_id]
        
        self._trigger_event('task_failed', {'task_id': task_id, 'error': error})
    
    def on_event(self, event_type: str, callback: Callable):
        """Register event callback."""
        self._event_callbacks[event_type].append(callback)
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger event callbacks."""
        for callback in self._event_callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback for {event_type}: {str(e)}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current monitoring metrics."""
        current_system = self.system_metrics_history[-1] if self.system_metrics_history else None
        
        return {
            'timestamp': time.time(),
            'status': CrawlStatus.RUNNING if self.is_running else CrawlStatus.IDLE,
            'stats': {
                'total_tasks': self.stats.total_tasks,
                'completed_tasks': self.stats.completed_tasks,
                'failed_tasks': self.stats.failed_tasks,
                'active_tasks': self.stats.active_tasks,
                'success_rate': self.stats.success_rate,
                'avg_response_time': self.stats.avg_response_time,
                'current_rate': self.stats.current_rate,
                'peak_rate': self.stats.peak_rate,
                'total_bytes': self.stats.total_bytes_downloaded,
                'duration': self.stats.duration
            },
            'system': {
                'cpu_percent': current_system.cpu_percent if current_system else 0,
                'memory_percent': current_system.memory_percent if current_system else 0,
                'memory_used_mb': current_system.memory_used_mb if current_system else 0,
                'active_connections': current_system.active_connections if current_system else 0
            },
            'top_errors': dict(list(self.stats.errors.items())[:5]),
            'status_codes': dict(self.stats.status_codes)
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        metrics = self.get_current_metrics()
        
        # Calculate additional performance indicators
        report = {
            'summary': {
                'total_duration': self.stats.duration,
                'total_tasks': self.stats.total_tasks,
                'success_rate': self.stats.success_rate,
                'throughput': self.stats.throughput,
                'total_data': self.stats.total_bytes_downloaded
            },
            'performance': {
                'avg_response_time': self.stats.avg_response_time,
                'min_response_time': self.stats.min_response_time if self.stats.min_response_time != float('inf') else 0,
                'max_response_time': self.stats.max_response_time,
                'current_rate': self.stats.current_rate,
                'peak_rate': self.stats.peak_rate
            },
            'system_usage': metrics['system'],
            'errors': dict(self.stats.errors),
            'status_codes': dict(self.stats.status_codes),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        # Success rate recommendations
        if self.stats.total_tasks > 10:
            if self.stats.success_rate < 70:
                recommendations.append("Low success rate detected. Check network connectivity and target server stability.")
            elif self.stats.success_rate < 90:
                recommendations.append("Consider implementing retry logic for failed requests.")
        
        # Response time recommendations
        if self.stats.avg_response_time > 5.0:
            recommendations.append("High average response time. Consider reducing concurrent requests or increasing timeout.")
        
        # System resource recommendations
        current_system = self.system_metrics_history[-1] if self.system_metrics_history else None
        if current_system:
            if current_system.cpu_percent > 80:
                recommendations.append("High CPU usage. Consider reducing concurrency or optimizing processing logic.")
            
            if current_system.memory_percent > 80:
                recommendations.append("High memory usage. Consider implementing content streaming or reducing cache sizes.")
        
        # Error pattern recommendations
        common_errors = sorted(self.stats.errors.items(), key=lambda x: x[1], reverse=True)[:3]
        for error, count in common_errors:
            if count > self.stats.total_tasks * 0.1:  # More than 10% of tasks
                recommendations.append(f"Frequent error '{error}' ({count} occurrences). Investigate root cause.")
        
        return recommendations


# Simplified Terminal UI stub (full implementation would require rich/curses)
class TerminalUI:
    """Simplified terminal UI for monitoring (stub implementation)."""
    
    def __init__(self):
        self.is_running = False
        self.monitor = None
    
    def start(self, monitor: CrawlerMonitor):
        """Start terminal UI."""
        self.monitor = monitor
        self.is_running = True
        logger.info("Terminal UI started (simplified mode)")
    
    def stop(self):
        """Stop terminal UI."""
        self.is_running = False
        logger.info("Terminal UI stopped")


# Factory functions
def create_crawler_monitor(
    update_interval: float = 1.0,
    max_history_size: int = 1000,
    enable_terminal_ui: bool = False
) -> CrawlerMonitor:
    """Create a crawler monitor instance."""
    return CrawlerMonitor(
        update_interval=update_interval,
        max_history_size=max_history_size,
        enable_terminal_ui=enable_terminal_ui
    )


# Singleton instance for global monitoring
_global_monitor: Optional[CrawlerMonitor] = None


def get_global_monitor() -> CrawlerMonitor:
    """Get global crawler monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = create_crawler_monitor()
    return _global_monitor


def start_global_monitoring():
    """Start global monitoring."""
    monitor = get_global_monitor()
    monitor.start()


def stop_global_monitoring():
    """Stop global monitoring."""
    monitor = get_global_monitor()
    monitor.stop()
