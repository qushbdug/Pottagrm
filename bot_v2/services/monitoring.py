"""
Enhanced Monitoring Service for Yemen Net Bot v2
Implements comprehensive metrics collection, health checks, and alerting
"""

import time
import asyncio
import logging
import threading
import psutil
import os
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from ..core.exceptions import BotException
from ..core.config import config

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: Union[int, float, str]
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class Metric:
    """Metric definition and data"""
    name: str
    description: str
    unit: str
    type: str  # counter, gauge, histogram
    data: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class Alert:
    """Alert definition"""
    name: str
    condition: str
    threshold: Union[int, float]
    severity: str  # info, warning, error, critical
    message: str
    enabled: bool = True
    last_triggered: Optional[float] = None
    cooldown: int = 300  # seconds

@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    check_func: Callable
    interval: int  # seconds
    timeout: int = 30
    last_check: Optional[float] = None
    last_status: str = "unknown"
    last_error: Optional[str] = None

class MonitoringService:
    """Enhanced monitoring service with metrics, health checks, and alerts"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger('MonitoringService')
        
        # Metrics storage
        self.metrics: Dict[str, Metric] = {}
        self.custom_metrics: Dict[str, Any] = {}
        
        # Alerts
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_status: Dict[str, str] = {}
        
        # System monitoring
        self.system_metrics = {
            'cpu_usage': deque(maxlen=100),
            'memory_usage': deque(maxlen=100),
            'disk_usage': deque(maxlen=100),
            'network_io': deque(maxlen=100),
            'process_count': deque(maxlen=100)
        }
        
        # Performance tracking
        self.performance_metrics = {
            'response_times': deque(maxlen=1000),
            'error_rates': deque(maxlen=1000),
            'request_counts': deque(maxlen=1000),
            'cache_hit_rates': deque(maxlen=1000)
        }
        
        # Threading
        self.lock = threading.RLock()
        self.running = False
        
        # Initialize default metrics and alerts
        self._initialize_defaults()
        
        # Start monitoring
        self.start()
    
    def _initialize_defaults(self):
        """Initialize default metrics and alerts"""
        # System metrics
        self.add_metric('system_cpu_usage', 'CPU usage percentage', '%', 'gauge')
        self.add_metric('system_memory_usage', 'Memory usage percentage', '%', 'gauge')
        self.add_metric('system_disk_usage', 'Disk usage percentage', '%', 'gauge')
        self.add_metric('system_network_io', 'Network I/O bytes per second', 'B/s', 'gauge')
        self.add_metric('system_process_count', 'Number of running processes', 'count', 'gauge')
        
        # Bot metrics
        self.add_metric('bot_messages_processed', 'Total messages processed', 'count', 'counter')
        self.add_metric('bot_commands_executed', 'Total commands executed', 'count', 'counter')
        self.add_metric('bot_errors', 'Total errors encountered', 'count', 'counter')
        self.add_metric('bot_response_time', 'Bot response time', 'ms', 'histogram')
        self.add_metric('bot_active_users', 'Number of active users', 'count', 'gauge')
        
        # Database metrics
        self.add_metric('db_queries_executed', 'Total database queries', 'count', 'counter')
        self.add_metric('db_query_time', 'Database query execution time', 'ms', 'histogram')
        self.add_metric('db_connections_active', 'Active database connections', 'count', 'gauge')
        self.add_metric('db_errors', 'Database errors', 'count', 'counter')
        
        # Cache metrics
        self.add_metric('cache_hits', 'Cache hit count', 'count', 'counter')
        self.add_metric('cache_misses', 'Cache miss count', 'count', 'counter')
        self.add_metric('cache_size', 'Current cache size', 'MB', 'gauge')
        self.add_metric('cache_evictions', 'Cache evictions', 'count', 'counter')
        
        # Default alerts
        self.add_alert(
            'high_cpu_usage',
            'system_cpu_usage > 80',
            80.0,
            'warning',
            'CPU usage is high: {value}%'
        )
        
        self.add_alert(
            'high_memory_usage',
            'system_memory_usage > 85',
            85.0,
            'warning',
            'Memory usage is high: {value}%'
        )
        
        self.add_alert(
            'high_disk_usage',
            'system_disk_usage > 90',
            90.0,
            'error',
            'Disk usage is critical: {value}%'
        )
        
        self.add_alert(
            'high_error_rate',
            'bot_errors > 100',
            100,
            'error',
            'High error rate detected: {value} errors'
        )
        
        self.add_alert(
            'slow_response_time',
            'bot_response_time > 5000',
            5000,
            'warning',
            'Slow response time: {value}ms'
        )
        
        # Default health checks
        self.add_health_check('database_connection', self._check_database_health, 60)
        self.add_health_check('cache_health', self._check_cache_health, 120)
        self.add_health_check('bot_responsiveness', self._check_bot_responsiveness, 30)
    
    def add_metric(self, name: str, description: str, unit: str, metric_type: str, labels: Dict[str, str] = None):
        """Add a new metric"""
        with self.lock:
            self.metrics[name] = Metric(
                name=name,
                description=description,
                unit=unit,
                type=metric_type,
                labels=labels or {}
            )
            self.logger.debug(f"Added metric: {name}")
    
    def record_metric(self, name: str, value: Union[int, float, str], labels: Dict[str, str] = None):
        """Record a metric value"""
        try:
            with self.lock:
                if name in self.metrics:
                    metric = self.metrics[name]
                    point = MetricPoint(
                        timestamp=time.time(),
                        value=value,
                        labels=labels or {}
                    )
                    metric.data.append(point)
                    
                    # Update custom metrics for quick access
                    self.custom_metrics[name] = value
                    
                    # Check alerts
                    self._check_alerts(name, value)
                    
                    self.logger.debug(f"Recorded metric {name}: {value}")
                else:
                    self.logger.warning(f"Unknown metric: {name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to record metric {name}: {e}")
    
    def increment_metric(self, name: str, increment: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        try:
            current_value = self.custom_metrics.get(name, 0)
            new_value = current_value + increment
            self.record_metric(name, new_value, labels)
        except Exception as e:
            self.logger.error(f"Failed to increment metric {name}: {e}")
    
    def add_alert(self, name: str, condition: str, threshold: Union[int, float], 
                  severity: str, message: str, cooldown: int = 300):
        """Add a new alert"""
        with self.lock:
            self.alerts[name] = Alert(
                name=name,
                condition=condition,
                threshold=threshold,
                severity=severity,
                message=message,
                cooldown=cooldown
            )
            self.logger.debug(f"Added alert: {name}")
    
    def add_health_check(self, name: str, check_func: Callable, interval: int, timeout: int = 30):
        """Add a new health check"""
        with self.lock:
            self.health_checks[name] = HealthCheck(
                name=name,
                check_func=check_func,
                interval=interval,
                timeout=timeout
            )
            self.logger.debug(f"Added health check: {name}")
    
    def _check_alerts(self, metric_name: str, value: Union[int, float, str]):
        """Check if any alerts should be triggered"""
        current_time = time.time()
        
        for alert_name, alert in self.alerts.items():
            if not alert.enabled:
                continue
            
            # Check cooldown
            if (alert.last_triggered and 
                current_time - alert.last_triggered < alert.cooldown):
                continue
            
            # Check condition
            if self._evaluate_alert_condition(alert.condition, metric_name, value):
                self._trigger_alert(alert, value)
    
    def _evaluate_alert_condition(self, condition: str, metric_name: str, value: Union[int, float, str]) -> bool:
        """Evaluate alert condition"""
        try:
            # Simple condition evaluation
            if '>' in condition:
                metric, threshold = condition.split('>')
                metric = metric.strip()
                threshold = float(threshold.strip())
                return metric == metric_name and float(value) > threshold
            elif '<' in condition:
                metric, threshold = condition.split('<')
                metric = metric.strip()
                threshold = float(threshold.strip())
                return metric == metric_name and float(value) < threshold
            elif '==' in condition:
                metric, threshold = condition.split('==')
                metric = metric.strip()
                threshold = threshold.strip().strip('"\'')
                return metric == metric_name and str(value) == threshold
            else:
                return False
        except Exception as e:
            self.logger.error(f"Failed to evaluate alert condition '{condition}': {e}")
            return False
    
    def _trigger_alert(self, alert: Alert, value: Union[int, float, str]):
        """Trigger an alert"""
        try:
            current_time = time.time()
            alert.last_triggered = current_time
            
            # Format message
            message = alert.message.format(value=value)
            
            # Create alert record
            alert_record = {
                'name': alert.name,
                'severity': alert.severity,
                'message': message,
                'value': value,
                'timestamp': current_time,
                'formatted_time': datetime.fromtimestamp(current_time).isoformat()
            }
            
            # Add to history
            self.alert_history.append(alert_record)
            
            # Log alert
            log_level = getattr(logging, alert.severity.upper(), logging.INFO)
            self.logger.log(log_level, f"ALERT [{alert.severity.upper()}]: {message}")
            
            # Send notification if configured
            self._send_alert_notification(alert_record)
            
        except Exception as e:
            self.logger.error(f"Failed to trigger alert {alert.name}: {e}")
    
    def _send_alert_notification(self, alert_record: Dict[str, Any]):
        """Send alert notification"""
        try:
            # This could be extended to send notifications via:
            # - Telegram messages
            # - Email
            # - Webhooks
            # - Slack/Discord
            # - SMS
            
            if self.config.ENABLE_NOTIFICATIONS:
                # For now, just log the alert
                self.logger.info(f"Alert notification: {alert_record['message']}")
                
        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {e}")
    
    def _check_database_health(self) -> str:
        """Check database health"""
        try:
            # Import here to avoid circular imports
            from .database_manager import db_manager
            
            # Check database connection
            stats = db_manager.get_database_stats()
            if not stats:
                return "error"
            
            # Check if database is responsive
            if 'table_stats' in stats and stats['table_stats']:
                return "healthy"
            else:
                return "warning"
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return "error"
    
    def _check_cache_health(self) -> str:
        """Check cache health"""
        try:
            # Import here to avoid circular imports
            from .cache_manager import cache_manager
            
            stats = cache_manager.get_stats()
            if not stats:
                return "error"
            
            # Check cache hit rate
            hit_rate = stats.get('hit_rate', 0)
            if hit_rate < 50:
                return "warning"
            elif hit_rate < 20:
                return "error"
            else:
                return "healthy"
                
        except Exception as e:
            self.logger.error(f"Cache health check failed: {e}")
            return "error"
    
    def _check_bot_responsiveness(self) -> str:
        """Check bot responsiveness"""
        try:
            # Check if bot is responding to commands
            # This is a simplified check - in practice, you might want to
            # send a test message and measure response time
            
            # For now, check if we have recent activity
            recent_activity = self.custom_metrics.get('bot_messages_processed', 0)
            if recent_activity > 0:
                return "healthy"
            else:
                return "warning"
                
        except Exception as e:
            self.logger.error(f"Bot responsiveness check failed: {e}")
            return "error"
    
    def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric('system_cpu_usage', cpu_percent)
            self.system_metrics['cpu_usage'].append(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.record_metric('system_memory_usage', memory_percent)
            self.system_metrics['memory_usage'].append(memory_percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric('system_disk_usage', disk_percent)
            self.system_metrics['disk_usage'].append(disk_percent)
            
            # Network I/O
            network = psutil.net_io_counters()
            network_bytes = network.bytes_sent + network.bytes_recv
            self.record_metric('system_network_io', network_bytes)
            self.system_metrics['network_io'].append(network_bytes)
            
            # Process count
            process_count = len(psutil.pids())
            self.record_metric('system_process_count', process_count)
            self.system_metrics['process_count'].append(process_count)
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def _run_health_checks(self):
        """Run all health checks"""
        current_time = time.time()
        
        for check_name, health_check in self.health_checks.items():
            try:
                # Check if it's time to run this health check
                if (health_check.last_check is None or 
                    current_time - health_check.last_check >= health_check.interval):
                    
                    # Run health check
                    start_time = time.time()
                    status = health_check.check_func()
                    check_time = (time.time() - start_time) * 1000
                    
                    # Update health check status
                    health_check.last_check = current_time
                    health_check.last_status = status
                    
                    # Record health check metric
                    self.record_metric(f'health_check_{check_name}', 1 if status == 'healthy' else 0)
                    self.record_metric(f'health_check_{check_name}_time', check_time)
                    
                    # Update overall health status
                    self.health_status[check_name] = status
                    
                    self.logger.debug(f"Health check {check_name}: {status} ({check_time:.2f}ms)")
                    
            except Exception as e:
                health_check.last_error = str(e)
                health_check.last_status = 'error'
                self.health_status[check_name] = 'error'
                self.logger.error(f"Health check {check_name} failed: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Run health checks
                self._run_health_checks()
                
                # Sleep for monitoring interval
                time.sleep(self.config.MONITORING_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(10)  # Wait before retrying
    
    def start(self):
        """Start monitoring service"""
        if not self.running:
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            self.logger.info("Monitoring service started")
    
    def stop(self):
        """Stop monitoring service"""
        self.running = False
        if hasattr(self, 'monitoring_thread'):
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Monitoring service stopped")
    
    def get_metrics(self, metric_names: List[str] = None) -> Dict[str, Any]:
        """Get metrics data"""
        with self.lock:
            if metric_names:
                return {name: self.metrics.get(name) for name in metric_names if name in self.metrics}
            else:
                return self.metrics.copy()
    
    def get_metric_value(self, name: str) -> Optional[Union[int, float, str]]:
        """Get current value of a metric"""
        return self.custom_metrics.get(name)
    
    def get_alerts(self, severity: str = None) -> List[Dict[str, Any]]:
        """Get alert history"""
        with self.lock:
            if severity:
                return [alert for alert in self.alert_history if alert['severity'] == severity]
            else:
                return list(self.alert_history)
    
    def get_health_status(self) -> Dict[str, str]:
        """Get overall health status"""
        with self.lock:
            return self.health_status.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get current system metrics
            current_metrics = {}
            for metric_name in self.system_metrics:
                if self.system_metrics[metric_name]:
                    current_metrics[metric_name] = self.system_metrics[metric_name][-1]
            
            # Get performance metrics
            performance_summary = {}
            for metric_name, data in self.performance_metrics.items():
                if data:
                    values = list(data)
                    performance_summary[metric_name] = {
                        'current': values[-1] if values else 0,
                        'average': sum(values) / len(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0
                    }
            
            return {
                'timestamp': time.time(),
                'formatted_time': datetime.now().isoformat(),
                'system_metrics': current_metrics,
                'performance_metrics': performance_summary,
                'health_status': self.get_health_status(),
                'alerts': {
                    'total': len(self.alert_history),
                    'recent': len([a for a in self.alert_history if time.time() - a['timestamp'] < 3600])
                },
                'metrics_summary': {
                    'total_metrics': len(self.metrics),
                    'total_alerts': len(self.alerts),
                    'total_health_checks': len(self.health_checks)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {}
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format"""
        try:
            if format.lower() == 'json':
                return json.dumps(self.get_system_status(), indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return ""

# Global monitoring service instance
monitoring_service = MonitoringService()