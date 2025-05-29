#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
パフォーマンス監視・最適化システム

機能:
- 処理時間の計測とプロファイリング
- メモリ使用量の監視
- データベースパフォーマンスの分析
- ボトルネックの特定と最適化提案
- リアルタイム監視ダッシュボード
"""

import time
import threading
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
import functools
import json
from pathlib import Path
import sqlite3
from collections import defaultdict, deque

@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""
    function_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    timestamp: datetime
    thread_id: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    result_size: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None

@dataclass
class SystemMetrics:
    """システム指標"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage: float
    active_threads: int
    database_connections: int = 0

class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self, max_history: int = 1000, sampling_interval: float = 1.0):
        self.max_history = max_history
        self.sampling_interval = sampling_interval
        self.logger = logging.getLogger(__name__)
        
        # メトリクス履歴
        self.performance_history: deque = deque(maxlen=max_history)
        self.system_history: deque = deque(maxlen=max_history)
        
        # 統計情報
        self.function_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_calls': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'error_count': 0,
            'last_called': None
        })
        
        # 監視フラグ
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # アラート設定
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'execution_time': 5.0,  # 秒
            'error_rate': 0.1  # 10%
        }
        
        # アラート履歴
        self.alerts: List[Dict[str, Any]] = []
        
        self.logger.info("パフォーマンス監視システムを初期化しました")
    
    def start_monitoring(self):
        """システム監視を開始"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitor_thread.start()
        self.logger.info("システム監視を開始しました")
    
    def stop_monitoring(self):
        """システム監視を停止"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        self.logger.info("システム監視を停止しました")
    
    def _monitor_system(self):
        """システムメトリクスの監視ループ"""
        while self.monitoring_active:
            try:
                metrics = self._collect_system_metrics()
                self.system_history.append(metrics)
                self._check_system_alerts(metrics)
                time.sleep(self.sampling_interval)
            except Exception as e:
                self.logger.error(f"システム監視エラー: {e}")
                time.sleep(self.sampling_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクスを収集"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_available=memory.available,
            disk_usage=disk.percent,
            active_threads=threading.active_count()
        )
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """システムアラートをチェック"""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'message': f'CPU使用率が高い: {metrics.cpu_percent:.1f}%',
                'value': metrics.cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })
        
        if metrics.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'message': f'メモリ使用率が高い: {metrics.memory_percent:.1f}%',
                'value': metrics.memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })
        
        for alert in alerts:
            alert['timestamp'] = datetime.now()
            self.alerts.append(alert)
            self.logger.warning(f"アラート: {alert['message']}")
    
    def start_timing(self, operation_name: str):
        """タイミング計測を開始"""
        # コンテキストマネージャーを使用する代わりに、シンプルなタイミング開始メソッドを提供
        if not hasattr(self, '_timing_data'):
            self._timing_data = {}
        self._timing_data[operation_name] = time.time()
        
    def end_timing(self, operation_name: str) -> float:
        """タイミング計測を終了し、経過時間を返す"""
        if not hasattr(self, '_timing_data') or operation_name not in self._timing_data:
            return 0.0
        elapsed = time.time() - self._timing_data[operation_name]
        del self._timing_data[operation_name]
        return elapsed
        
    def get_memory_usage(self) -> int:
        """現在のメモリ使用量を取得（バイト単位）"""
        return psutil.virtual_memory().used
    
    @contextmanager
    def measure_performance(self, function_name: str, parameters: Optional[Dict[str, Any]] = None):
        """パフォーマンス計測のコンテキストマネージャー"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        thread_id = threading.get_ident()
        
        success = True
        error_message = None
        result_size = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            metrics = PerformanceMetrics(
                function_name=function_name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=psutil.cpu_percent(),
                timestamp=datetime.now(),
                thread_id=thread_id,
                parameters=parameters or {},
                result_size=result_size,
                success=success,
                error_message=error_message
            )
            
            self._record_performance(metrics)
    
    def _record_performance(self, metrics: PerformanceMetrics):
        """パフォーマンス記録"""
        self.performance_history.append(metrics)
        self._update_function_stats(metrics)
        self._check_performance_alerts(metrics)
    
    def _update_function_stats(self, metrics: PerformanceMetrics):
        """関数統計を更新"""
        stats = self.function_stats[metrics.function_name]
        
        stats['total_calls'] += 1
        stats['total_time'] += metrics.execution_time
        stats['avg_time'] = stats['total_time'] / stats['total_calls']
        stats['min_time'] = min(stats['min_time'], metrics.execution_time)
        stats['max_time'] = max(stats['max_time'], metrics.execution_time)
        stats['last_called'] = metrics.timestamp
        
        if not metrics.success:
            stats['error_count'] += 1
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """パフォーマンスアラートをチェック"""
        alerts = []
        
        if metrics.execution_time > self.alert_thresholds['execution_time']:
            alerts.append({
                'type': 'slow_execution',
                'message': f'実行時間が長い: {metrics.function_name} ({metrics.execution_time:.2f}秒)',
                'function': metrics.function_name,
                'value': metrics.execution_time,
                'threshold': self.alert_thresholds['execution_time']
            })
        
        # エラー率のチェック
        stats = self.function_stats[metrics.function_name]
        if stats['total_calls'] >= 10:  # 最低10回の呼び出し後にチェック
            error_rate = stats['error_count'] / stats['total_calls']
            if error_rate > self.alert_thresholds['error_rate']:
                alerts.append({
                    'type': 'high_error_rate',
                    'message': f'エラー率が高い: {metrics.function_name} ({error_rate:.1%})',
                    'function': metrics.function_name,
                    'value': error_rate,
                    'threshold': self.alert_thresholds['error_rate']
                })
        
        for alert in alerts:
            alert['timestamp'] = datetime.now()
            self.alerts.append(alert)
            self.logger.warning(f"パフォーマンスアラート: {alert['message']}")

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """パフォーマンス要約を取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 指定時間内のメトリクスをフィルタ
        recent_performance = [m for m in self.performance_history if m.timestamp >= cutoff_time]
        recent_system = [m for m in self.system_history if m.timestamp >= cutoff_time]
        
        # 統計計算
        if recent_performance:
            avg_execution_time = sum(m.execution_time for m in recent_performance) / len(recent_performance)
            max_execution_time = max(m.execution_time for m in recent_performance)
            error_count = sum(1 for m in recent_performance if not m.success)
            error_rate = error_count / len(recent_performance) if recent_performance else 0
        else:
            avg_execution_time = max_execution_time = error_rate = 0
            error_count = 0
        
        if recent_system:
            avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system)
            avg_memory = sum(m.memory_percent for m in recent_system) / len(recent_system)
            max_cpu = max(m.cpu_percent for m in recent_system)
            max_memory = max(m.memory_percent for m in recent_system)
        else:
            avg_cpu = avg_memory = max_cpu = max_memory = 0
        
        # 最も遅い関数のトップ5
        slowest_functions = sorted(
            self.function_stats.items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )[:5]
        
        # 最も呼び出される関数のトップ5
        most_called_functions = sorted(
            self.function_stats.items(),
            key=lambda x: x[1]['total_calls'],
            reverse=True
        )[:5]
        
        return {
            'period_hours': hours,
            'total_function_calls': len(recent_performance),
            'performance': {
                'avg_execution_time': avg_execution_time,
                'max_execution_time': max_execution_time,
                'error_count': error_count,
                'error_rate': error_rate
            },
            'system': {
                'avg_cpu_percent': avg_cpu,
                'avg_memory_percent': avg_memory,
                'max_cpu_percent': max_cpu,
                'max_memory_percent': max_memory
            },
            'slowest_functions': [
                {
                    'name': name,
                    'avg_time': stats['avg_time'],
                    'total_calls': stats['total_calls']
                }
                for name, stats in slowest_functions
            ],
            'most_called_functions': [
                {
                    'name': name,
                    'total_calls': stats['total_calls'],
                    'avg_time': stats['avg_time']
                }
                for name, stats in most_called_functions
            ],
            'recent_alerts': self.alerts[-10:] if self.alerts else []
        }
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """最適化提案を生成"""
        suggestions = []
        
        # 遅い関数の特定
        for func_name, stats in self.function_stats.items():
            if stats['avg_time'] > 1.0:  # 1秒以上
                suggestions.append({
                    'type': 'slow_function',
                    'priority': 'high',
                    'message': f'{func_name} の実行時間が長い (平均 {stats["avg_time"]:.2f}秒)',
                    'suggestion': 'アルゴリズムの最適化、キャッシュの活用、または非同期処理の検討'
                })
        
        # エラー率の高い関数
        for func_name, stats in self.function_stats.items():
            if stats['total_calls'] >= 10:
                error_rate = stats['error_count'] / stats['total_calls']
                if error_rate > 0.05:  # 5%以上
                    suggestions.append({
                        'type': 'high_error_rate',
                        'priority': 'medium',
                        'message': f'{func_name} のエラー率が高い ({error_rate:.1%})',
                        'suggestion': 'エラーハンドリングの改善、入力値検証の強化'
                    })
        
        # システムリソース
        if self.system_history:
            recent_cpu = [m.cpu_percent for m in list(self.system_history)[-10:]]
            recent_memory = [m.memory_percent for m in list(self.system_history)[-10:]]
            
            avg_cpu = sum(recent_cpu) / len(recent_cpu)
            avg_memory = sum(recent_memory) / len(recent_memory)
            
            if avg_cpu > 70:
                suggestions.append({
                    'type': 'high_cpu',
                    'priority': 'medium',
                    'message': f'CPU使用率が高い (平均 {avg_cpu:.1f}%)',
                    'suggestion': 'CPU集約的な処理の並列化、または処理の分散'
                })
            
            if avg_memory > 80:
                suggestions.append({
                    'type': 'high_memory',
                    'priority': 'medium',
                    'message': f'メモリ使用率が高い (平均 {avg_memory:.1f}%)',
                    'suggestion': 'メモリリークの確認、大きなオブジェクトの最適化'
                })
        
        return suggestions
    
    def export_performance_report(self, filepath: str = "performance_report.json"):
        """パフォーマンスレポートをエクスポート"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_performance_summary(),
            'optimization_suggestions': self.get_optimization_suggestions(),
            'function_statistics': {
                name: {
                    **stats,
                    'last_called': stats['last_called'].isoformat() if stats['last_called'] else None
                }
                for name, stats in self.function_stats.items()
            },
            'alert_history': self.alerts,
            'monitoring_config': {
                'max_history': self.max_history,
                'sampling_interval': self.sampling_interval,
                'alert_thresholds': self.alert_thresholds
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"パフォーマンスレポートを保存しました: {filepath}")

# デコレータ
def monitor_performance(function_name: Optional[str] = None, 
                       track_parameters: bool = False):
    """パフォーマンス監視デコレータ"""
    def decorator(func):
        nonlocal function_name
        if function_name is None:
            function_name = f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            
            parameters = {}
            if track_parameters:
                # 安全にパラメータを記録（大きなオブジェクトは除外）
                try:
                    parameters = {
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                    # 小さな値のみ記録
                    for k, v in kwargs.items():
                        if isinstance(v, (str, int, float, bool)) and len(str(v)) < 100:
                            parameters[k] = v
                except:
                    pass
            
            with monitor.measure_performance(function_name, parameters):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

# グローバルパフォーマンス監視インスタンス
_global_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """グローバルパフォーマンス監視インスタンスを取得"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
        _global_performance_monitor.start_monitoring()
    return _global_performance_monitor

if __name__ == "__main__":
    # テスト用のコード
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    # テスト関数
    @monitor_performance("test_function", track_parameters=True)
    def test_slow_function(delay: float = 1.0):
        time.sleep(delay)
        return "完了"
    
    # テスト実行
    try:
        for i in range(5):
            result = test_slow_function(0.1 * i)
            print(f"実行 {i+1}: {result}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    
    # レポート生成
    time.sleep(2)  # システムメトリクス収集のため
    monitor.stop_monitoring()
    
    summary = monitor.get_performance_summary(hours=1)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    
    suggestions = monitor.get_optimization_suggestions()
    print("\n最適化提案:")
    for suggestion in suggestions:
        print(f"- {suggestion['message']}")
        print(f"  提案: {suggestion['suggestion']}")
    
    monitor.export_performance_report()
