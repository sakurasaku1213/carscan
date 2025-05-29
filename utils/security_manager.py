#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
セキュリティ・データ保護システム - 統合版

機能:
- データ暗号化・復号化
- アクセス制御とユーザー認証
- 機密データの安全な保存
- 監査ログの記録
- データ完整性の検証
- セキュリティアラート
- レポート生成時のデータ保護
- 設定管理システムとの統合
"""

import hashlib
import hmac
import secrets
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import sqlite3
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# プロジェクト内モジュールのインポート
from config.app_config import AppConfig
from utils.performance_monitor import monitor_performance, get_performance_monitor
from utils.error_handler import get_error_handler, SecurityError, ErrorSeverity

class SecurityLevel(Enum):
    """セキュリティレベル"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class AccessType(Enum):
    """アクセス種別"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class DataCategory(Enum):
    """データカテゴリ"""
    CASE_DATA = "case_data"
    CALCULATION_RESULT = "calculation_result"
    REPORT_OUTPUT = "report_output"
    USER_DATA = "user_data"
    SYSTEM_CONFIG = "system_config"

@dataclass
class SecurityEvent:
    """セキュリティイベント"""
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    resource: str
    action: str
    security_level: SecurityLevel
    result: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DataProtectionPolicy:
    """データ保護ポリシー"""
    data_category: DataCategory
    security_level: SecurityLevel
    encryption_required: bool
    access_control_required: bool
    audit_logging_required: bool
    retention_days: Optional[int] = None
    anonymization_required: bool = False

class IntegratedSecurityManager:
    """統合セキュリティマネージャー"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.error_handler = get_error_handler()
        self.performance_monitor = get_performance_monitor()
        self.logger = logging.getLogger(__name__)
        
        # セキュリティ設定の初期化
        self.security_config = getattr(config, 'security', None)
        if not self.security_config:
            self.logger.warning("セキュリティ設定が見つかりません。デフォルト設定を使用します。")
            self._initialize_default_security_config()
        
        # 暗号化キーの初期化
        self._encryption_key = None
        self._salt = None
        
        # データ保護ポリシーの初期化
        self.data_policies = self._initialize_data_policies()
        
        # 監査ログデータベースの初期化
        self._init_audit_database()
        
        # セキュリティイベントキューの初期化
        self.security_events: List[SecurityEvent] = []
        
        self.logger.info("統合セキュリティマネージャーを初期化しました")

    def _initialize_default_security_config(self):
        """デフォルトセキュリティ設定の初期化"""
        self.security_config = {
            'encryption_enabled': True,
            'audit_logging_enabled': True,
            'access_control_enabled': True,
            'password_policy': {
                'min_length': 8,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_symbols': True
            },
            'session_timeout_minutes': 30,
            'max_failed_attempts': 5,
            'data_retention_days': 365
        }

    def _initialize_data_policies(self) -> Dict[DataCategory, DataProtectionPolicy]:
        """データ保護ポリシーの初期化"""
        return {
            DataCategory.CASE_DATA: DataProtectionPolicy(
                data_category=DataCategory.CASE_DATA,
                security_level=SecurityLevel.CONFIDENTIAL,
                encryption_required=True,
                access_control_required=True,
                audit_logging_required=True,
                retention_days=self.security_config.data_retention_days,
                anonymization_required=False
            ),            DataCategory.CALCULATION_RESULT: DataProtectionPolicy(
                data_category=DataCategory.CALCULATION_RESULT,
                security_level=SecurityLevel.CONFIDENTIAL,
                encryption_required=True,
                access_control_required=True,
                audit_logging_required=True,
                retention_days=self.security_config.data_retention_days
            ),            DataCategory.REPORT_OUTPUT: DataProtectionPolicy(
                data_category=DataCategory.REPORT_OUTPUT,
                security_level=SecurityLevel.INTERNAL,
                encryption_required=False,
                access_control_required=True,
                audit_logging_required=True,
                retention_days=self.security_config.data_retention_days
            ),
            DataCategory.USER_DATA: DataProtectionPolicy(
                data_category=DataCategory.USER_DATA,
                security_level=SecurityLevel.RESTRICTED,
                encryption_required=True,
                access_control_required=True,
                audit_logging_required=True,
                anonymization_required=True
            ),
            DataCategory.SYSTEM_CONFIG: DataProtectionPolicy(
                data_category=DataCategory.SYSTEM_CONFIG,
                security_level=SecurityLevel.RESTRICTED,
                encryption_required=True,
                access_control_required=True,
                audit_logging_required=True
            )
        }

    @monitor_performance
    def _init_audit_database(self):
        """監査ログデータベースの初期化"""
        try:
            # データベースファイルのパス
            db_dir = getattr(self.config, 'database_directory', './database')
            os.makedirs(db_dir, exist_ok=True)
            self.audit_db_path = os.path.join(db_dir, 'security_audit.db')
            
            # データベース接続とテーブル作成
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        event_type TEXT NOT NULL,
                        user_id TEXT,
                        resource TEXT NOT NULL,
                        action TEXT NOT NULL,
                        security_level TEXT NOT NULL,
                        result TEXT NOT NULL,
                        details TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_security_events_timestamp 
                    ON security_events(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_security_events_user 
                    ON security_events(user_id)
                ''')
                
                conn.commit()
                
            self.logger.info(f"監査ログデータベースを初期化しました: {self.audit_db_path}")
            
        except Exception as e:
            self.logger.error(f"監査ログデータベース初期化エラー: {str(e)}")
            self.error_handler.handle_exception(
                SecurityError(
                    f"監査ログデータベースの初期化に失敗しました: {str(e)}",
                    user_message="セキュリティシステムの初期化に失敗しました。",
                    severity=ErrorSeverity.HIGH,
                    context={'error': str(e)}
                )
            )

    @monitor_performance
    def get_encryption_key(self, password: Optional[str] = None) -> bytes:
        """暗号化キーを取得"""
        if self._encryption_key is None:
            if password is None:
                # 環境変数から暗号化パスワードを取得
                password = os.environ.get('COMPENSATION_SYSTEM_ENCRYPTION_KEY')
                if not password:
                    # デフォルトパスワードを使用（実運用では推奨されません）
                    password = "default_compensation_system_key_2024"
                    self.logger.warning("デフォルト暗号化キーを使用しています。実運用では環境変数を設定してください。")
            
            # ソルト生成
            if self._salt is None:
                self._salt = secrets.token_bytes(32)
            
            # PBKDF2を使用してキー導出
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self._encryption_key = key
            
        return self._encryption_key

    @monitor_performance
    def encrypt_data(self, data: Union[str, bytes, Dict[str, Any]], 
                    data_category: DataCategory,
                    user_id: Optional[str] = None) -> Tuple[bytes, Dict[str, Any]]:
        """データの暗号化"""
        try:
            # データ保護ポリシーの確認
            policy = self.data_policies.get(data_category)
            if not policy or not policy.encryption_required:
                # 暗号化が不要な場合は元データを返す
                if isinstance(data, dict):
                    data = json.dumps(data, ensure_ascii=False)
                if isinstance(data, str):
                    data = data.encode('utf-8')
                return data, {'encrypted': False}
            
            # データを文字列に変換
            if isinstance(data, dict):
                data_str = json.dumps(data, ensure_ascii=False)
            elif isinstance(data, bytes):
                data_str = data.decode('utf-8')
            else:
                data_str = str(data)
            
            # 暗号化実行
            fernet = Fernet(self.get_encryption_key())
            encrypted_data = fernet.encrypt(data_str.encode('utf-8'))
            
            # メタデータ作成
            metadata = {
                'encrypted': True,
                'encryption_algorithm': 'Fernet',
                'data_category': data_category.value,
                'encrypted_at': datetime.now().isoformat(),
                'encrypted_by': user_id
            }
            
            # セキュリティイベント記録
            self._log_security_event(
                event_type='data_encryption',
                user_id=user_id,
                resource=f"{data_category.value}",
                action='encrypt',
                security_level=policy.security_level,
                result='success',
                details={'data_size': len(data_str)}
            )
            
            self.logger.debug(f"データ暗号化完了: {data_category.value}")
            return encrypted_data, metadata
            
        except Exception as e:
            self.logger.error(f"データ暗号化エラー: {str(e)}")
            self.error_handler.handle_exception(
                SecurityError(
                    f"データ暗号化に失敗しました: {str(e)}",
                    user_message="データの暗号化処理に失敗しました。",
                    severity=ErrorSeverity.HIGH,
                    context={'data_category': data_category.value, 'error': str(e)}
                )
            )
            raise

    @monitor_performance
    def decrypt_data(self, encrypted_data: bytes, metadata: Dict[str, Any],
                    data_category: DataCategory,
                    user_id: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        """データの復号化"""
        try:
            # 暗号化されていないデータの場合
            if not metadata.get('encrypted', False):
                return encrypted_data.decode('utf-8') if isinstance(encrypted_data, bytes) else encrypted_data
            
            # データ保護ポリシーの確認
            policy = self.data_policies.get(data_category)
            if policy and policy.access_control_required:
                # アクセス制御チェック（実装に応じて拡張）
                if not self._check_access_permission(user_id, data_category, AccessType.READ):
                    raise SecurityError("データアクセス権限がありません")
            
            # 復号化実行
            fernet = Fernet(self.get_encryption_key())
            decrypted_data = fernet.decrypt(encrypted_data)
            data_str = decrypted_data.decode('utf-8')
            
            # JSONデータの場合は辞書に変換
            try:
                data_dict = json.loads(data_str)
                result = data_dict
            except json.JSONDecodeError:
                result = data_str
            
            # セキュリティイベント記録
            self._log_security_event(
                event_type='data_decryption',
                user_id=user_id,
                resource=f"{data_category.value}",
                action='decrypt',
                security_level=policy.security_level if policy else SecurityLevel.INTERNAL,
                result='success',
                details={'data_size': len(data_str)}
            )
            
            self.logger.debug(f"データ復号化完了: {data_category.value}")
            return result
            
        except Exception as e:
            self.logger.error(f"データ復号化エラー: {str(e)}")
            self.error_handler.handle_exception(
                SecurityError(
                    f"データ復号化に失敗しました: {str(e)}",
                    user_message="データの復号化処理に失敗しました。",
                    severity=ErrorSeverity.HIGH,
                    context={'data_category': data_category.value, 'error': str(e)}
                )
            )
            raise

    def _check_access_permission(self, user_id: Optional[str], 
                               data_category: DataCategory, 
                               access_type: AccessType) -> bool:
        """アクセス権限チェック"""
        # 基本的なアクセス制御ロジック
        # 実際の実装では、ユーザーロール、権限マトリックス等を参照
        
        if not user_id:
            # 匿名ユーザーはPUBLICデータのREADのみ許可
            policy = self.data_policies.get(data_category)
            return (policy and 
                   policy.security_level == SecurityLevel.PUBLIC and 
                   access_type == AccessType.READ)
        
        # 認証済みユーザーの場合は基本的にアクセスを許可
        # 実際の実装では詳細な権限チェックを実装
        return True

    @monitor_performance
    def secure_report_generation(self, report_data: Dict[str, Any], 
                               report_type: str,
                               user_id: Optional[str] = None) -> Dict[str, Any]:
        """セキュアなレポート生成"""
        try:
            self.logger.info(f"セキュアレポート生成開始: {report_type}")
            
            # レポートデータの暗号化
            encrypted_data, metadata = self.encrypt_data(
                report_data, 
                DataCategory.REPORT_OUTPUT, 
                user_id
            )
            
            # レポート生成時の個人情報マスキング
            masked_data = self._apply_data_masking(report_data, user_id)
            
            # アクセスログの記録
            self._log_security_event(
                event_type='report_generation',
                user_id=user_id,
                resource=f"report_{report_type}",
                action='generate',
                security_level=SecurityLevel.INTERNAL,
                result='success',
                details={
                    'report_type': report_type,
                    'data_categories': list(report_data.keys()),
                    'masked_fields': list(masked_data.get('masked_fields', []))
                }
            )
            
            return {
                'original_data': report_data,
                'masked_data': masked_data,
                'encrypted_data': encrypted_data,
                'metadata': metadata,
                'security_applied': True
            }
            
        except Exception as e:
            self.logger.error(f"セキュアレポート生成エラー: {str(e)}")
            self.error_handler.handle_exception(
                SecurityError(
                    f"セキュアレポート生成に失敗しました: {str(e)}",
                    user_message="セキュリティ機能を適用したレポート生成に失敗しました。",
                    severity=ErrorSeverity.HIGH,
                    context={'report_type': report_type, 'error': str(e)}
                )
            )
            raise

    def _apply_data_masking(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """データマスキングの適用"""
        masked_data = data.copy()
        masked_fields = []
        
        # 個人情報フィールドのマスキング
        sensitive_fields = [
            'client_name', 'name', 'personal_id', 'address', 'phone', 'email',
            'bank_account', 'credit_card', 'social_security'
        ]
        
        def mask_value(value: str) -> str:
            if len(value) <= 4:
                return '*' * len(value)
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
        
        def mask_recursive(obj: Any, path: str = '') -> Any:
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.lower() in sensitive_fields:
                        if isinstance(value, str) and value:
                            result[key] = mask_value(value)
                            masked_fields.append(current_path)
                        else:
                            result[key] = value
                    else:
                        result[key] = mask_recursive(value, current_path)
                return result
            elif isinstance(obj, list):
                return [mask_recursive(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            else:
                return obj
        
        masked_data = mask_recursive(masked_data)
        
        return {
            'data': masked_data,
            'masked_fields': masked_fields,
            'masking_applied_at': datetime.now().isoformat(),
            'masked_by': user_id
        }

    def _log_security_event(self, event_type: str, user_id: Optional[str], 
                          resource: str, action: str, security_level: SecurityLevel,
                          result: str, details: Optional[Dict[str, Any]] = None):
        """セキュリティイベントのログ記録"""
        if not self.security_config.audit_logging_enabled:
            return
        
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            security_level=security_level,
            result=result,
            details=details or {}
        )
        
        # メモリキューに追加
        self.security_events.append(event)
        
        # データベースに記録
        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO security_events 
                    (timestamp, event_type, user_id, resource, action, security_level, result, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.timestamp,
                    event.event_type,
                    event.user_id,
                    event.resource,
                    event.action,
                    event.security_level.value,
                    event.result,
                    json.dumps(event.details, ensure_ascii=False)
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"セキュリティイベント記録エラー: {str(e)}")

    @monitor_performance
    def get_security_audit_report(self, start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                user_id: Optional[str] = None) -> Dict[str, Any]:
        """セキュリティ監査レポートの生成"""
        try:
            # デフォルトの期間設定（過去30日）
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()
                
                # 基本統計の取得
                query = '''
                    SELECT 
                        event_type,
                        security_level,
                        result,
                        COUNT(*) as count
                    FROM security_events 
                    WHERE timestamp BETWEEN ? AND ?
                '''
                params = [start_date, end_date]
                
                if user_id:
                    query += ' AND user_id = ?'
                    params.append(user_id)
                
                query += ' GROUP BY event_type, security_level, result ORDER BY count DESC'
                
                cursor.execute(query, params)
                statistics = cursor.fetchall()
                
                # 詳細イベントの取得（最新100件）
                detail_query = '''
                    SELECT timestamp, event_type, user_id, resource, action, 
                           security_level, result, details
                    FROM security_events 
                    WHERE timestamp BETWEEN ? AND ?
                '''
                detail_params = [start_date, end_date]
                
                if user_id:
                    detail_query += ' AND user_id = ?'
                    detail_params.append(user_id)
                
                detail_query += ' ORDER BY timestamp DESC LIMIT 100'
                
                cursor.execute(detail_query, detail_params)
                events = cursor.fetchall()
            
            # レポート作成
            report = {
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': {
                    'total_events': len(events),
                    'unique_users': len(set(event[2] for event in events if event[2])),
                    'security_levels': {}
                },
                'statistics': [
                    {
                        'event_type': stat[0],
                        'security_level': stat[1],
                        'result': stat[2],
                        'count': stat[3]
                    }
                    for stat in statistics
                ],
                'recent_events': [
                    {
                        'timestamp': event[0],
                        'event_type': event[1],
                        'user_id': event[2],
                        'resource': event[3],
                        'action': event[4],
                        'security_level': event[5],
                        'result': event[6],
                        'details': json.loads(event[7]) if event[7] else {}
                    }
                    for event in events
                ],
                'generated_at': datetime.now().isoformat(),
                'generated_by': user_id
            }
            
            # セキュリティレベル別統計
            for stat in statistics:
                level = stat[1]
                if level not in report['summary']['security_levels']:
                    report['summary']['security_levels'][level] = 0
                report['summary']['security_levels'][level] += stat[3]
            
            self.logger.info(f"セキュリティ監査レポート生成完了: {len(events)}件のイベント")
            return report
            
        except Exception as e:
            self.logger.error(f"セキュリティ監査レポート生成エラー: {str(e)}")
            self.error_handler.handle_exception(
                SecurityError(
                    f"セキュリティ監査レポート生成に失敗しました: {str(e)}",
                    user_message="セキュリティ監査レポートの生成に失敗しました。",
                    severity=ErrorSeverity.MEDIUM,
                    context={'error': str(e)}
                )
            )
            raise

# グローバルシングルトンインスタンス
_security_manager_instance: Optional[IntegratedSecurityManager] = None

def get_security_manager(app_config: Optional[AppConfig] = None) -> IntegratedSecurityManager:
    """
    セキュリティマネージャーのシングルトンインスタンスを取得
    
    Args:
        app_config: アプリケーション設定（初回のみ使用）
        
    Returns:
        IntegratedSecurityManagerのインスタンス
    """
    global _security_manager_instance
    
    if _security_manager_instance is None:
        if app_config is None:
            # デフォルト設定でAppConfigを作成
            try:
                app_config = AppConfig()
            except Exception as e:
                # 最小限の設定で作成
                from types import SimpleNamespace
                app_config = SimpleNamespace()
                app_config.database_path = "data/security.db"
                app_config.encryption_key_file = "config/encryption.key"
                app_config.log_level = "INFO"
                app_config.max_failed_attempts = 3
                app_config.session_timeout_minutes = 30
        
        _security_manager_instance = IntegratedSecurityManager(app_config)
    
    return _security_manager_instance

def reset_security_manager():
    """
    セキュリティマネージャーのインスタンスをリセット（主にテスト用）
    """
    global _security_manager_instance
    _security_manager_instance = None
