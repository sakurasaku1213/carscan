#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一エラーハンドリングシステム

機能:
- 例外の分類と統一的な処理
- ユーザーフレンドリーなエラーメッセージ
- 詳細なログ記録
- 自動復旧機能
- エラー統計と分析
"""

import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type, Union, List
from enum import Enum
from dataclasses import dataclass, field
import json
from pathlib import Path
import functools

class ErrorSeverity(Enum):
    """エラーの重要度"""
    LOW = "low"           # 軽微（警告レベル）
    MEDIUM = "medium"     # 中程度（エラーレベル）
    HIGH = "high"         # 重大（クリティカルレベル）
    CRITICAL = "critical" # 致命的（システム停止）

class ErrorCategory(Enum):
    """エラーカテゴリ"""
    INPUT_VALIDATION = "input_validation"
    DATABASE = "database"
    CALCULATION = "calculation"
    FILE_IO = "file_io"
    NETWORK = "network"
    SYSTEM = "system"
    UI = "ui"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    UNKNOWN = "unknown"

@dataclass
class ErrorInfo:
    """エラー情報"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_suggestion: Optional[str] = None
    error_code: Optional[str] = None

class CompensationSystemError(Exception):
    """損害賠償システムのベース例外クラス"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 user_message: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 recovery_suggestion: Optional[str] = None,
                 error_code: Optional[str] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.user_message = user_message or message
        self.context = context or {}
        self.recovery_suggestion = recovery_suggestion
        self.error_code = error_code

# 具体的な例外クラス
class ValidationError(CompensationSystemError):
    """入力値検証エラー"""
    def __init__(self, message: str, field_name: Optional[str] = None, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.INPUT_VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        if field_name:
            self.context["field_name"] = field_name

class DatabaseError(CompensationSystemError):
    """データベース操作エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )

class CalculationError(CompensationSystemError):
    """計算処理エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.CALCULATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class ConfigurationError(CompensationSystemError):
    """設定エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class SecurityError(CompensationSystemError):
    """セキュリティエラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class FileIOError(CompensationSystemError):
    """ファイルI/Oエラー"""
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.FILE_IO,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        if file_path:
            self.context["file_path"] = file_path

class ErrorHandler:
    """統一エラーハンドリングシステム"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.error_stats: Dict[str, int] = {}
        self.error_history: List[ErrorInfo] = []
        self.recovery_handlers: Dict[ErrorCategory, Callable] = {}
        
        # エラーログファイルの設定
        if log_file:
            self.setup_error_logging(log_file)
        
        # デフォルトの復旧ハンドラーを設定
        self.setup_default_recovery_handlers()
    
    def setup_error_logging(self, log_file: str):
        """エラーログの設定"""
        error_handler = logging.FileHandler(log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def setup_default_recovery_handlers(self):
        """デフォルトの復旧ハンドラーを設定"""
        self.recovery_handlers[ErrorCategory.INPUT_VALIDATION] = self._handle_validation_error
        self.recovery_handlers[ErrorCategory.DATABASE] = self._handle_database_error
        self.recovery_handlers[ErrorCategory.CALCULATION] = self._handle_calculation_error
        self.recovery_handlers[ErrorCategory.FILE_IO] = self._handle_file_error
    
    def handle_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """例外を処理してErrorInfoを生成"""
        context = context or {}
        
        # CompensationSystemError の場合
        if isinstance(exception, CompensationSystemError):
            error_info = ErrorInfo(
                category=exception.category,
                severity=exception.severity,
                message=str(exception),
                user_message=exception.user_message,
                exception_type=type(exception).__name__,
                stack_trace=traceback.format_exc(),
                context={**exception.context, **context},
                recovery_suggestion=exception.recovery_suggestion,
                error_code=exception.error_code
            )
        else:
            # 標準例外の場合、カテゴリを推測
            category = self._categorize_exception(exception)
            severity = self._determine_severity(exception)
            
            error_info = ErrorInfo(
                category=category,
                severity=severity,
                message=str(exception),
                user_message=self._create_user_friendly_message(exception),
                exception_type=type(exception).__name__,
                stack_trace=traceback.format_exc(),
                context=context,
                recovery_suggestion=self._get_recovery_suggestion(category)
            )
        
        # ログ記録と統計更新
        self._log_error(error_info)
        self._update_statistics(error_info)
        self.error_history.append(error_info)
        
        # 復旧の試行
        self._attempt_recovery(error_info)
        
        return error_info
    
    def _categorize_exception(self, exception: Exception) -> ErrorCategory:
        """例外の種類からカテゴリを推測"""
        exception_type = type(exception).__name__
        
        mapping = {
            'ValueError': ErrorCategory.INPUT_VALIDATION,
            'TypeError': ErrorCategory.INPUT_VALIDATION,
            'sqlite3.Error': ErrorCategory.DATABASE,
            'FileNotFoundError': ErrorCategory.FILE_IO,
            'PermissionError': ErrorCategory.FILE_IO,
            'IOError': ErrorCategory.FILE_IO,
            'OSError': ErrorCategory.SYSTEM,
            'MemoryError': ErrorCategory.SYSTEM,
            'ConnectionError': ErrorCategory.NETWORK,
            'TimeoutError': ErrorCategory.NETWORK,
            'ZeroDivisionError': ErrorCategory.CALCULATION,
            'OverflowError': ErrorCategory.CALCULATION,
        }
        
        return mapping.get(exception_type, ErrorCategory.UNKNOWN)
    
    def _determine_severity(self, exception: Exception) -> ErrorSeverity:
        """例外の重要度を判定"""
        critical_exceptions = ['MemoryError', 'SystemExit', 'KeyboardInterrupt']
        high_exceptions = ['FileNotFoundError', 'PermissionError', 'ZeroDivisionError']
        
        exception_type = type(exception).__name__
        
        if exception_type in critical_exceptions:
            return ErrorSeverity.CRITICAL
        elif exception_type in high_exceptions:
            return ErrorSeverity.HIGH
        elif exception_type in ['ValueError', 'TypeError']:
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM
    
    def _create_user_friendly_message(self, exception: Exception) -> str:
        """ユーザーフレンドリーなエラーメッセージを生成"""
        exception_type = type(exception).__name__
        
        messages = {
            'ValueError': '入力された値が無効です。正しい形式で入力してください。',
            'TypeError': 'データの型が正しくありません。入力内容を確認してください。',
            'FileNotFoundError': '指定されたファイルが見つかりません。',
            'PermissionError': 'ファイルへのアクセス権限がありません。',
            'ZeroDivisionError': '計算でゼロ除算が発生しました。入力値を確認してください。',
            'MemoryError': 'メモリ不足です。他のアプリケーションを終了してください。',
            'ConnectionError': 'ネットワーク接続に問題があります。',
        }
        
        return messages.get(exception_type, 
                          f'予期しないエラーが発生しました: {str(exception)}')
    
    def _get_recovery_suggestion(self, category: ErrorCategory) -> str:
        """復旧提案を生成"""
        suggestions = {
            ErrorCategory.INPUT_VALIDATION: '入力内容を確認し、正しい形式で再入力してください。',
            ErrorCategory.DATABASE: 'データベースファイルの確認またはアプリケーションの再起動を試してください。',
            ErrorCategory.CALCULATION: '入力された数値に問題がないか確認してください。',
            ErrorCategory.FILE_IO: 'ファイルの存在とアクセス権限を確認してください。',
            ErrorCategory.NETWORK: 'ネットワーク接続を確認してください。',
            ErrorCategory.SYSTEM: 'システムリソースを確認し、必要に応じて再起動してください。',
            ErrorCategory.CONFIGURATION: '設定ファイルを確認または初期化してください。',
        }
        
        return suggestions.get(category, 'アプリケーションを再起動してください。')
    
    def _log_error(self, error_info: ErrorInfo):
        """エラーをログに記録"""
        log_message = (
            f"[{error_info.category.value}] {error_info.message} "
            f"(重要度: {error_info.severity.value})"
        )
        
        if error_info.context:
            log_message += f" | Context: {json.dumps(error_info.context, ensure_ascii=False)}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # スタックトレースも記録
        if error_info.stack_trace:
            self.logger.debug(f"Stack trace: {error_info.stack_trace}")
    
    def _update_statistics(self, error_info: ErrorInfo):
        """エラー統計を更新"""
        key = f"{error_info.category.value}_{error_info.severity.value}"
        self.error_stats[key] = self.error_stats.get(key, 0) + 1
    
    def _attempt_recovery(self, error_info: ErrorInfo):
        """復旧を試行"""
        recovery_handler = self.recovery_handlers.get(error_info.category)
        if recovery_handler:
            try:
                recovery_handler(error_info)
            except Exception as e:
                self.logger.error(f"復旧処理中にエラー: {e}")
    
    # 復旧ハンドラー
    def _handle_validation_error(self, error_info: ErrorInfo):
        """入力検証エラーの復旧"""
        self.logger.info("入力検証エラー - ユーザーに再入力を促します")
    
    def _handle_database_error(self, error_info: ErrorInfo):
        """データベースエラーの復旧"""
        self.logger.info("データベースエラー - 接続の再試行を検討")
    
    def _handle_calculation_error(self, error_info: ErrorInfo):
        """計算エラーの復旧"""
        self.logger.info("計算エラー - デフォルト値での計算を検討")
    
    def _handle_file_error(self, error_info: ErrorInfo):
        """ファイルエラーの復旧"""
        self.logger.info("ファイルエラー - 代替ファイルまたはデフォルト設定を検討")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        return {
            "total_errors": len(self.error_history),
            "by_category": self.error_stats,
            "recent_errors": [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "message": error.message
                }
                for error in self.error_history[-10:]  # 最新10件
            ]
        }
    
    def export_error_report(self, filepath: str = "error_report.json"):
        """エラーレポートをエクスポート"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "statistics": self.get_error_statistics(),
            "all_errors": [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "message": error.message,
                    "user_message": error.user_message,
                    "exception_type": error.exception_type,
                    "context": error.context,
                    "recovery_suggestion": error.recovery_suggestion,
                    "error_code": error.error_code
                }
                for error in self.error_history
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

# デコレータ関数
def error_handler(category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 user_message: Optional[str] = None,
                 recovery_suggestion: Optional[str] = None):
    """エラーハンドリングデコレータ"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # グローバルエラーハンドラーがあれば使用
                if hasattr(func, '_error_handler'):
                    error_info = func._error_handler.handle_exception(e)
                    if severity == ErrorSeverity.CRITICAL:
                        raise
                    return None
                else:
                    # 独自例外として再発生
                    raise CompensationSystemError(
                        str(e),
                        category=category,
                        severity=severity,
                        user_message=user_message,
                        recovery_suggestion=recovery_suggestion
                    )
        return wrapper
    return decorator

# グローバルエラーハンドラーのインスタンス
_global_error_handler = None

def get_error_handler() -> ErrorHandler:
    """グローバルエラーハンドラーを取得"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler("errors.log")
    return _global_error_handler

def handle_critical_error(exception: Exception):
    """致命的エラーの処理"""
    error_handler = get_error_handler()
    error_info = error_handler.handle_exception(exception)
    
    # 緊急時の処理
    if error_info.severity == ErrorSeverity.CRITICAL:
        print(f"致命的エラー: {error_info.user_message}")
        print("アプリケーションを安全に終了します...")
        sys.exit(1)

if __name__ == "__main__":
    # テスト用のコード
    handler = ErrorHandler()
    
    try:
        raise ValueError("テスト用のエラー")
    except Exception as e:
        error_info = handler.handle_exception(e, {"test_context": "例外テスト"})
        print(f"エラー処理完了: {error_info.user_message}")
    
    print("エラー統計:", handler.get_error_statistics())
