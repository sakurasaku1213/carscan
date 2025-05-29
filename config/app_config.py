#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリケーション設定管理システム
設定の読み込み、保存、検証を統一的に管理
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import os
from enum import Enum # 追加
from utils.error_handler import ErrorHandler, ConfigurationError, get_error_handler # 変更

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@dataclass
class DatabaseConfig:
    """データベース設定"""
    db_path: str = "compensation_cases.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    auto_optimize: bool = True
    connection_timeout: float = 30.0
    # 設定ファイルから読み込まれる追加の属性
    file_path: str = "database/cases_v2.db"
    backup_dir: str = "database/backups"
    auto_backup_interval_hours: int = 24
    max_backup_files: int = 7
    connection_timeout_seconds: int = 30
    journal_mode: str = "WAL"
    enable_foreign_keys: bool = True
    
@dataclass
class UIConfig:
    """UI設定"""
    theme: str = "light"
    language: str = "ja"
    window_width: int = 1200
    window_height: int = 800
    font_size: int = 10
    enable_tooltips: bool = True
    auto_save_interval: int = 300  # 秒
    # 設定ファイルから読み込まれる追加の属性
    appearance_mode: str = "light"
    font_family: str = "Meiryo UI"
    default_window_width: int = 1200
    default_window_height: int = 800
    auto_calculate: bool = True
    export_path: str = "exports"
    template_dir: str = "templates/ui"
    recent_files_max: int = 10

@dataclass
class ReportConfig: # 新規追加
    """レポート生成設定"""
    default_output_directory: str = "reports/generated"
    excel_template_path: Optional[str] = "templates/excel/standard_report_template.xlsx"
    pdf_template_path: Optional[str] = "templates/pdf/standard_report_template.json" # PDFテンプレートはJSONで構造定義も可
    include_charts_in_excel: bool = True
    include_detailed_calculation_in_pdf: bool = False # PDFに詳細計算を含めるか（既存）
    company_logo_path: Optional[str] = "assets/company_logo.png"
    default_author: str = "弁護士法人〇〇法律事務所"
    font_name_gothic: str = "IPAexGothic" # PDF用日本語フォント
    font_path_gothic: str = "fonts/ipaexg.ttf" # PDF用日本語フォントパス

    # レポートに含める項目リスト (新規追加)
    excel_report_items: list[str] = field(default_factory=lambda: [
        "header", "case_summary", "basic_info", "medical_info", "income_info", 
        "calculation_summary_table", "detailed_calculation_table", "charts", "footer"
    ])
    pdf_report_items: list[str] = field(default_factory=lambda: [
        "logo", "header_title", "case_info_header", "basic_info_table", "medical_info_table", 
        "income_info_table", "calculation_results_table", "disclaimer_footer"
    ])
    # 詳細計算テーブルをPDFに含めるかは include_detailed_calculation_in_pdf で制御するため、
    # pdf_report_items からは "detailed_calculation_table" のような項目は除外しておくか、
    # pdf_generator側で include_detailed_calculation_in_pdf と pdf_report_items の両方を考慮する。
    # ここでは、pdf_report_items は大まかなセクションを示し、詳細表示フラグは別途参照する方針とする。

    # 複数テンプレート管理 (新規追加)
    excel_templates: Dict[str, str] = field(default_factory=lambda: {
        "traffic_accident": "templates/excel/traffic_accident_template.xlsx",
        "work_accident": "templates/excel/work_accident_template.xlsx", 
        "medical_malpractice": "templates/excel/medical_malpractice_template.xlsx",
        "default": "templates/excel/standard_report_template.xlsx"
    })
    pdf_templates: Dict[str, str] = field(default_factory=lambda: {
        "traffic_accident": "templates/pdf/traffic_accident_template.json",
        "work_accident": "templates/pdf/work_accident_template.json",
        "medical_malpractice": "templates/pdf/medical_malpractice_template.json", 
        "default": "templates/pdf/standard_report_template.json"
    })
    
    # テンプレートカスタマイズ設定
    enable_template_customization: bool = True
    auto_create_missing_templates: bool = True
    template_data_mapping: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "traffic_accident": {
            "title": "交通事故損害賠償計算書",
            "special_notes": "自賠責保険・任意保険との調整を考慮",
            "required_fields": "事故状況,過失割合,車両損害"
        },
        "work_accident": {
            "title": "労災事故損害賠償計算書", 
            "special_notes": "労災給付との調整・特別支給金の取扱い",
            "required_fields": "災害発生状況,労災認定,事業主責任"
        },
        "medical_malpractice": {
            "title": "医療過誤損害賠償計算書",
            "special_notes": "因果関係・過失の程度・寄与度減額を考慮",
            "required_fields": "医療行為,過誤内容,因果関係,鑑定結果"
        }
    })
    
    # 高度なレポートカスタマイズ
    excel_column_widths: Dict[str, float] = field(default_factory=lambda: {
        "A": 20.0, "B": 15.0, "C": 40.0, "D": 25.0, 
        "E": 15.0, "F": 15.0, "G": 15.0, "H": 15.0
    })
    excel_row_heights: Dict[str, float] = field(default_factory=lambda: {
        "header": 25.0, "subheader": 20.0, "data": 18.0, "footer": 15.0
    })
    excel_color_scheme: Dict[str, str] = field(default_factory=lambda: {
        "header_bg": "4472C4", "subheader_bg": "8DB4E2", 
        "amount_bg": "FFF2CC", "total_bg": "D5E8D4",
        "header_text": "FFFFFF", "body_text": "000000"
    })
    
    # PDF詳細設定
    pdf_page_margins: Dict[str, float] = field(default_factory=lambda: {
        "top": 72, "bottom": 72, "left": 72, "right": 72
    })
    pdf_font_sizes: Dict[str, int] = field(default_factory=lambda: {
        "title": 18, "header": 14, "subheader": 12, 
        "body": 10, "small": 8, "footer": 9
    })
    pdf_line_spacing: float = 1.2
    pdf_table_style: Dict[str, str] = field(default_factory=lambda: {
        "grid_color": "black", "header_bg": "lightgrey",
        "alt_row_bg": "whitesmoke", "border_width": "0.5"
    })

@dataclass
class CalculationConfig:
    """計算設定"""
    default_standard: str = "弁護士基準"
    enable_auto_calculation: bool = True
    precision_digits: int = 0
    rounding_method: str = "round"  # round, floor, ceil
    validation_enabled: bool = True
    # 設定ファイルから読み込まれる追加の属性
    default_interest_rate_pa: float = 3.0
    leibniz_coefficients_file: str = "config/leibniz_coefficients.json"
    lawyer_fee_calculation_standard: str = "old_standard"
    enable_detailed_calculation_log: bool = False

@dataclass
class LoggingConfig:
    """ログ設定"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "logs/app.log"  # 通常のアプリケーションログ
    error_log_file_path: Optional[str] = "logs/error.log" # エラー専用ログファイルを追加
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    console_enabled: bool = True
    # 設定ファイルから読み込まれる追加の属性
    file_enabled: bool = True

@dataclass
class SecurityConfig:
    """セキュリティ設定"""
    enable_data_encryption: bool = False
    encryption_enabled: bool = False  # テスト互換性のため
    backup_encryption: bool = False
    session_timeout: int = 3600  # 秒
    max_login_attempts: int = 3
    data_retention_days: int = 365  # セキュリティマネージャー互換性のため
    anonymization_threshold_days: int = 730
    audit_logging_enabled: bool = True  # セキュリティマネージャー互換性のため
    # 設定ファイルから読み込まれる追加の属性
    master_key_env_var: str = "COMP_SYS_MASTER_KEY"
    secure_db_path: str = "database/secure_storage.db"
    audit_log_file: str = "logs/security_audit.log"
    password_policy: Dict[str, Any] = field(default_factory=lambda: {
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digit": True,
        "require_special_char": True
    })
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

# 新規追加: エラーハンドリング設定
class ErrorSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class ErrorHandlerConfig:
    log_file: Optional[str] = "logs/critical_system_errors.log" # より重大なエラーのログファイル
    default_severity: ErrorSeverity = ErrorSeverity.MEDIUM
    report_dir: str = "reports/error_details"
    enable_recovery_suggestions: bool = True
    max_history_items: int = 200

@dataclass
class PerformanceConfig:
    """パフォーマンス設定"""
    monitoring_enabled: bool = True
    log_performance_metrics: bool = True
    performance_log_file: Optional[str] = "logs/performance.log"
    alert_thresholds: Dict[str, int] = field(default_factory=lambda: {
        "calculation_time_ms": 5000,
        "report_generation_time_ms": 10000,
        "memory_usage_mb": 500
    })

@dataclass
class ApplicationConfig:
    """アプリケーション基本設定"""
    name: str = "弁護士基準損害賠償計算システム"
    version: str = "1.0.0"
    description: str = "弁護士基準に基づく損害賠償額を計算するシステム"
    author: str = "Your Name/Organization"
    license: str = "MIT"

@dataclass
class AppConfig:
    """アプリケーション全体設定"""
    version: str = "1.0.0"
    app_name: str = "弁護士基準損害賠償計算システム"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    calculation: CalculationConfig = field(default_factory=CalculationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    error_handling: ErrorHandlerConfig = field(default_factory=ErrorHandlerConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    performance_monitoring: PerformanceConfig = field(default_factory=PerformanceConfig) # 'performance' を 'performance_monitoring' に変更
    
    custom_settings: Dict[str, Any] = field(default_factory=dict)

class ConfigManager:
    _instance = None
    _config: Optional[AppConfig] = None
    _config_file_path: Optional[Path] = None
    _error_handler: ErrorHandler # 追加
    logger: logging.Logger # loggerを追加

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file_path: Optional[Union[str, Path]] = None):
        if not hasattr(self, '_initialized'):  # Prevent re-initialization
            # 最初にloggerを初期化
            self.logger = logging.getLogger(__name__)
            # エラーハンドラーは後で初期化（循環参照を避けるため）
            self._error_handler = None
            if config_file_path:
                self._config_file_path = Path(config_file_path)
            else:
                self._config_file_path = Path("config/app_config.json")
            self._load_config()
            # 設定読み込み後にエラーハンドラーを初期化
            try:
                self._error_handler = get_error_handler()
            except Exception as e:
                self.logger.warning(f"エラーハンドラーの初期化に失敗: {e}")
            self._initialized = True

    def _create_default_config(self) -> AppConfig:
        """デフォルト設定を作成"""
        return AppConfig()

    def _load_config(self):
        if self._config_file_path and self._config_file_path.exists():
            try:
                with open(self._config_file_path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                
                # バージョンチェックと移行処理
                config_dict = self._migrate_config_if_needed(config_dict)
                
                # 設定オブジェクトを作成
                self._config = self._dict_to_config(config_dict)
                self.logger.info(f"設定ファイルを読み込みました: {self._config_file_path}")
            except FileNotFoundError:
                if self._error_handler:
                    self._error_handler.handle_exception(
                        ConfigurationError(f"設定ファイルが見つかりません: {self._config_file_path}",
                                           user_message="設定ファイルが見つかりませんでした。デフォルト設定で起動します。")
                    )
                else:
                    self.logger.warning(f"設定ファイルが見つかりません: {self._config_file_path}")
                self._config = self._create_default_config()
            except json.JSONDecodeError as e:
                if self._error_handler:
                    self._error_handler.handle_exception(
                        ConfigurationError(f"設定ファイルの解析に失敗しました: {self._config_file_path}. Error: {e}",
                                           user_message="設定ファイルの形式が正しくありません。デフォルト設定で起動します。")
                    )
                else:
                    self.logger.error(f"設定ファイルの解析に失敗: {e}")
                self._config = self._create_default_config()
            except Exception as e: # その他の予期せぬエラー
                if self._error_handler:
                    self._error_handler.handle_exception(
                        ConfigurationError(f"設定ファイルの読み込み中に予期せぬエラーが発生しました: {e}",
                                           user_message="設定の読み込みに失敗しました。デフォルト設定で起動します。")
                    )
                else:
                    if self.logger:
                        self.logger.error(f"設定ファイル読み込み中にエラー: {e}")
                
                self._config = self._create_default_config()

        else:
            # デフォルト設定で初期化
            self._config = AppConfig()
            self.save_config()
            logging.info("デフォルト設定で初期化しました")
            
    def save_config(self, file_path: Optional[Union[str, Path]] = None):
        """設定ファイルを保存"""
        try:
            if self._config is None:
                self._config = AppConfig()
            
            # 更新日時を設定
            self._config.last_updated = datetime.now().isoformat()
            
            # 設定を辞書に変換
            config_dict = asdict(self._config)
            
            # JSONファイルに保存
            save_path = Path(file_path) if file_path else self._config_file_path
            if not save_path:
                self._error_handler.handle_exception(
                    ConfigurationError("設定ファイルの保存パスが指定されていません。",
                                       user_message="設定ファイルの保存先が不明です。")
                )
                return

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logging.info(f"設定ファイルを保存しました: {self._config_file_path}")
            
        except IOError as e:
            self._error_handler.handle_exception(
                ConfigurationError(f"設定ファイルの書き込みに失敗しました: {save_path}. Error: {e}",
                                   user_message=f"設定ファイル '{save_path.name}' の保存に失敗しました。")
            )
        except Exception as e: # その他の予期せぬエラー
            self._error_handler.handle_exception(
                ConfigurationError(f"設定ファイルの保存中に予期せぬエラーが発生しました: {e}",
                                   user_message="設定の保存中にエラーが発生しました。")
            )

    def get_config(self) -> AppConfig:
        """現在の設定を取得"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def update_config(self, **kwargs) -> bool:
        """設定を更新"""
        try:
            if self._config is None:
                self._load_config()
            
            # ネストした設定の更新
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    if isinstance(value, dict):
                        # セクション設定の更新
                        section = getattr(self._config, key)
                        for sub_key, sub_value in value.items():
                            if hasattr(section, sub_key):
                                setattr(section, sub_key, sub_value)
                    else:
                        setattr(self._config, key, value)
                else:
                    # カスタム設定に追加
                    self._config.custom_settings[key] = value
            
            return self.save_config()
            
        except Exception as e:
            logging.error(f"設定更新エラー: {e}")
            return False
    
    def get_setting(self, key: str, section: str = None, default=None) -> Any:
        """特定の設定値を取得"""
        try:
            if self._config is None:
                self._load_config()
            
            if section:
                section_obj = getattr(self._config, section, None)
                if section_obj:
                    return getattr(section_obj, key, default)
            else:
                return getattr(self._config, key, default)
                
        except Exception as e:
            logging.error(f"設定取得エラー: {e}")
        
        return default
    
    def set_setting(self, key: str, value: Any, section: str = None) -> bool:
        """特定の設定値を設定"""
        try:
            if self._config is None:
                self._load_config()
            
            if section:
                section_obj = getattr(self._config, section, None)
                if section_obj and hasattr(section_obj, key):
                    setattr(section_obj, key, value)
                    return self.save_config()
            else:
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                    return self.save_config()
                else:
                    self._config.custom_settings[key] = value
                    return self.save_config()
                    
        except Exception as e:
            logging.error(f"設定設定エラー: {e}")
        
        return False
    
    def reset_to_defaults(self, section: str = None) -> bool:
        """設定をデフォルトにリセット"""
        try:
            if section:
                # 特定セクションのみリセット
                if hasattr(AppConfig, section):
                    default_section = getattr(AppConfig(), section)
                    setattr(self._config, section, default_section)
            else:
                # 全設定をリセット
                self._config = AppConfig()
            
            return self.save_config()
            
        except Exception as e:
            logging.error(f"設定リセットエラー: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """設定の妥当性を検証"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if self._config is None:
                self._load_config()
            
            # データベース設定の検証
            if self._config.database.backup_interval_hours < 1:
                validation_result['errors'].append("バックアップ間隔は1時間以上である必要があります")
                validation_result['valid'] = False
            
            if self._config.database.backup_retention_days < 1:
                validation_result['errors'].append("バックアップ保持期間は1日以上である必要があります")
                validation_result['valid'] = False
            
            # UI設定の検証
            if self._config.ui.window_width < 800:
                validation_result['warnings'].append("ウィンドウ幅が小さすぎる可能性があります")
            
            if self._config.ui.window_height < 600:
                validation_result['warnings'].append("ウィンドウ高さが小さすぎる可能性があります")
            
            # 計算設定の検証
            if self._config.calculation.precision_digits < 0:
                validation_result['errors'].append("精度桁数は0以上である必要があります")
                validation_result['valid'] = False
            
            # ログ設定の検証
            log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if self._config.logging.level not in log_levels:
                validation_result['errors'].append(f"ログレベルは{log_levels}のいずれかである必要があります")
                validation_result['valid'] = False
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"設定検証エラー: {str(e)}")
        
        return validation_result
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """辞書から設定オブジェクトを作成"""
        try:
            # 各セクションを安全に作成
            application_config = ApplicationConfig(**config_dict.get('application', {}))
            database_config = DatabaseConfig(**config_dict.get('database', {}))
            ui_config = UIConfig(**config_dict.get('ui', {}))
            calculation_config = CalculationConfig(**config_dict.get('calculation', {}))
            logging_config = LoggingConfig(**config_dict.get('logging', {}))
            security_config = SecurityConfig(**config_dict.get('security', {}))
            error_handling_config = ErrorHandlerConfig(**config_dict.get('error_handling', {}))
            report_config = ReportConfig(**config_dict.get('report', {}))
            # 'performance' キーを 'performance_monitoring' に変更して読み込む
            performance_config = PerformanceConfig(**config_dict.get('performance_monitoring', config_dict.get('performance', {})))


            return AppConfig(
                version=config_dict.get('version', '1.0.0'),
                app_name=config_dict.get('app_name', '弁護士基準損害賠償計算システム'),
                last_updated=config_dict.get('last_updated', datetime.now().isoformat()),
                application=application_config,
                database=database_config,
                ui=ui_config,
                calculation=calculation_config,
                logging=logging_config,
                security=security_config,
                error_handling=error_handling_config,
                report=report_config,
                performance_monitoring=performance_config, # 'performance' を 'performance_monitoring' に変更
                custom_settings=config_dict.get('custom_settings', {})
            )
        except Exception as e:
            self.logger.error(f"設定オブジェクト作成エラー: {e}") # Changed to self.logger
            # Return a default AppConfig instance, which will use default factories
            return AppConfig()
    
    def _migrate_config_if_needed(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """設定のバージョン移行処理"""
        current_version = config_dict.get('version', '0.0.0')
        
        # バージョン固有の移行処理をここに追加
        if current_version < '1.0.0':
            # 1.0.0への移行処理
            logging.info(f"設定を{current_version}から1.0.0に移行します")
            config_dict['version'] = '1.0.0'
        
        return config_dict
    
    def export_config(self, export_path: str) -> bool:
        """設定をエクスポート"""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self._config is None:
                self._load_config()
            
            config_dict = asdict(self._config)
            config_dict['export_date'] = datetime.now().isoformat()
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logging.info(f"設定をエクスポートしました: {export_path}")
            return True
            
        except Exception as e:
            logging.error(f"設定エクスポートエラー: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """設定をインポート"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logging.error(f"インポートファイルが見つかりません: {import_path}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # バージョンチェックと移行
            config_dict = self._migrate_config_if_needed(config_dict)
            
            # 設定を更新
            self._config = self._dict_to_config(config_dict)
            
            # 保存
            if self.save_config():
                logging.info(f"設定をインポートしました: {import_path}")
                return True
            else:
                return False
                
        except Exception as e:
            logging.error(f"設定インポートエラー: {e}")
            return False

# グローバル設定管理インスタンス
_config_manager = None

def get_config_manager() -> ConfigManager:
    """設定管理インスタンスを取得（シングルトンパターン）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> AppConfig:
    """現在の設定を取得（便利関数）"""
    return get_config_manager().get_config()

def save_config() -> bool:
    """設定を保存（便利関数）"""
    return get_config_manager().save_config()
