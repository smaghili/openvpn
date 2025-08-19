import time
import threading
import psutil
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque
logger = logging.getLogger(__name__)
@dataclass
class PerformanceMetrics:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    database_connections: int
class PerformanceMonitor:
    def __init__(self, max_history: int = 1000, collection_interval: int = 5):
        self.max_history = max_history
        self.collection_interval = collection_interval
        self.metrics_history: deque[PerformanceMetrics] = deque(maxlen=max_history)
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self._last_disk_io = psutil.disk_io_counters()
        self._last_network_io = psutil.net_io_counters()
        self._last_collection_time = time.time()
    def start_monitoring(self) -> None:
        if self.is_monitoring:
            logger.warning("Performance monitoring is already running")
            return
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")
    def stop_monitoring(self) -> None:
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    def _monitor_loop(self) -> None:
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                with self.lock:
                    self.metrics_history.append(metrics)
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error collecting performance metrics: {e}")
                time.sleep(self.collection_interval)
    def _collect_metrics(self) -> PerformanceMetrics:
        current_time = time.time()
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        time_diff = current_time - self._last_collection_time
        disk_read_mb = (disk_io.read_bytes - self._last_disk_io.read_bytes) / (1024 * 1024 * time_diff) if time_diff > 0 else 0
        disk_write_mb = (disk_io.write_bytes - self._last_disk_io.write_bytes) / (1024 * 1024 * time_diff) if time_diff > 0 else 0
        network_sent_mb = (network_io.bytes_sent - self._last_network_io.bytes_sent) / (1024 * 1024 * time_diff) if time_diff > 0 else 0
        network_recv_mb = (network_io.bytes_recv - self._last_network_io.bytes_recv) / (1024 * 1024 * time_diff) if time_diff > 0 else 0
        self._last_disk_io = disk_io
        self._last_network_io = network_io
        self._last_collection_time = current_time
        return PerformanceMetrics(
            timestamp=current_time,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_connections=len(psutil.net_connections()),
            database_connections=0
        )
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        with self.lock:
            return self.metrics_history[-1] if self.metrics_history else None
    def get_metrics_history(self, minutes: int = 60) -> List[PerformanceMetrics]:
        cutoff_time = time.time() - (minutes * 60)
        with self.lock:
            return [
                metrics for metrics in self.metrics_history
                if metrics.timestamp >= cutoff_time
            ]
    def get_average_metrics(self, minutes: int = 5) -> Dict[str, float]:
        metrics = self.get_metrics_history(minutes)
        if not metrics:
            return {}
        return {
            "avg_cpu_percent": sum(m.cpu_percent for m in metrics) / len(metrics),
            "avg_memory_percent": sum(m.memory_percent for m in metrics) / len(metrics),
            "avg_memory_used_mb": sum(m.memory_used_mb for m in metrics) / len(metrics),
            "avg_disk_read_mb": sum(m.disk_io_read_mb for m in metrics) / len(metrics),
            "avg_disk_write_mb": sum(m.disk_io_write_mb for m in metrics) / len(metrics),
            "avg_network_sent_mb": sum(m.network_sent_mb for m in metrics) / len(metrics),
            "avg_network_recv_mb": sum(m.network_recv_mb for m in metrics) / len(metrics),
            "avg_active_connections": sum(m.active_connections for m in metrics) / len(metrics)
        }
    def get_performance_alerts(self) -> List[str]:
        alerts = []
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return alerts
        if current_metrics.cpu_percent > 80:
            alerts.append(f"High CPU usage: {current_metrics.cpu_percent:.1f}%")
        if current_metrics.memory_percent > 85:
            alerts.append(f"High memory usage: {current_metrics.memory_percent:.1f}%")
        if current_metrics.memory_used_mb > 800:
            alerts.append(f"High memory usage: {current_metrics.memory_used_mb:.1f}MB")
        if current_metrics.active_connections > 1000:
            alerts.append(f"High number of connections: {current_metrics.active_connections}")
        return alerts
    def get_performance_summary(self) -> Dict[str, Any]:
        current = self.get_current_metrics()
        avg_5min = self.get_average_metrics(5)
        avg_1hour = self.get_average_metrics(60)
        alerts = self.get_performance_alerts()
        return {
            "current": {
                "cpu_percent": current.cpu_percent if current else 0,
                "memory_percent": current.memory_percent if current else 0,
                "memory_used_mb": current.memory_used_mb if current else 0,
                "active_connections": current.active_connections if current else 0
            },
            "average_5min": avg_5min,
            "average_1hour": avg_1hour,
            "alerts": alerts,
            "monitoring_active": self.is_monitoring,
            "metrics_count": len(self.metrics_history)
        }
_performance_monitor = PerformanceMonitor()
def get_performance_monitor() -> PerformanceMonitor:
    return _performance_monitor
