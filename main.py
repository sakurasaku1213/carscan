#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弁護士基準損害賠償計算システム - メインエントリーポイント

統合された起動システム:
- 依存関係の自動チェック・インストール
- 設定システムの初期化
- パフォーマンス監視の開始
- セキュリティシステムの起動
- エラーハンドリングの設定
- UIアプリケーションの起動
"""

import sys
import os
import logging
import traceback
import webbrowser
from pathlib import Path

# プロジェクトのルートディレクトリをsys.pathに追加
# main.py が e:\\ にあるため、PROJECT_ROOT は e:\\ になる
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# デバッグ用に現在のsys.pathを出力 (本番ではコメントアウトまたは削除推奨)
# print(f"DEBUG: sys.path after adding PROJECT_ROOT: {sys.path}")

# グローバル変数
from typing import Optional, Dict, Any, List
import argparse
from datetime import datetime

# 設定とユーティリティのインポート - 直接インポート使用
try:
    from config.app_config import (
        ConfigManager, get_config_manager, AppConfig, ConfigurationError
    )
    from utils.error_handler import (
        ErrorHandler, get_error_handler, handle_critical_error, 
        CompensationSystemError, ErrorCategory, ErrorSeverity
    )
    from utils.performance_monitor import (
        PerformanceMonitor, get_performance_monitor
    )
    from utils.security_manager import (
        IntegratedSecurityManager, get_security_manager, DataCategory
    )
    from dependency_manager import DependencyManager, quick_setup
except ImportError as e:
    print(f"❌ 重要なモジュールのインポートに失敗しました: {e}")
    print("dependency_manager.py を実行して依存関係をインストールしてください。")
    sys.exit(1)

class CompensationSystemLauncher:
    """統合システム起動クラス"""
    
    def __init__(self, args: Optional[argparse.Namespace] = None):
        self.args = args or argparse.Namespace()
        self.setup_complete = False
        self.components_initialized = False
        self.config_manager: Optional[ConfigManager] = None # 型ヒント追加
        self.error_handler: Optional[ErrorHandler] = None # 型ヒント追加
        self.performance_monitor: Optional[PerformanceMonitor] = None # 型ヒント追加
        self.security_manager: Optional[IntegratedSecurityManager] = None # 型ヒント追加 SecureDataManager を IntegratedSecurityManager に変更
        self.logger = logging.getLogger(__name__) # ロガーの初期化
        self.app_config: Optional[AppConfig] = None # AppConfig を保持するフィールド
          # 基本ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('system_startup.log', encoding='utf-8')
            ]
        )
        
        self.logger.info("弁護士基準損害賠償計算システムを起動中...")
    
    def check_system_requirements(self) -> bool:
        """システム要件をチェック"""
        try:
            self.logger.info("🔍 システム要件をチェック中...")
            
            # プロジェクトルートパスを定義
            project_root_path = Path(__file__).resolve().parent
            
            # Python バージョンチェック
            if sys.version_info < (3, 8):
                self.logger.error(f"Python 3.8以上が必要です (現在: {sys.version})")
                return False
            
            # 必要なディレクトリの作成
            required_dirs = [
                'config', 'database', 'logs', 'reports', 'exports', 'temp'
            ]
            
            for dir_name in required_dirs:
                dir_path = project_root_path / dir_name
                dir_path.mkdir(exist_ok=True)
                self.logger.debug(f"ディレクトリを確認/作成: {dir_path}")
            
            self.logger.info("✅ システム要件チェック完了")
            return True
        except OSError as e:
            # ディレクトリ作成失敗など
            sys_err = CompensationSystemError(
                message=f"システム要件チェック中にOSエラーが発生しました: {e}",
                user_message="システムの初期セットアップ中に問題が発生しました。権限などを確認してください。",
                category="system", # ErrorCategory.SYSTEM に対応する文字列
                severity="critical" # ErrorSeverity.CRITICAL に対応する文字列
            )
            # この段階では error_handler が初期化されていない可能性があるため、直接ログに出力
            self.logger.critical(sys_err.message, exc_info=True)
            print(f"致命的なシステムエラー: {sys_err.user_message}", file=sys.stderr)
            return False
        except Exception as e:
            self.logger.critical(f"システム要件チェック中に予期せぬエラー: {e}", exc_info=True)
            print(f"致命的なシステムエラーが発生しました。詳細は system_startup.log を確認してください。", file=sys.stderr)
            return False
    
    def setup_dependencies(self) -> bool:
        """依存関係をセットアップ"""
        if hasattr(self.args, 'skip_deps') and self.args.skip_deps:
            self.logger.info("⏭️  依存関係チェックをスキップします")
            return True        
        self.logger.info("📦 依存関係をチェック中...")
        
        try:
            dm = DependencyManager("requirements.txt") # requirements.txtのパスを渡す
            dm.install_missing_packages()
            self.logger.info("✅ 依存関係チェック完了")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 依存関係チェックエラー: {e}", exc_info=True)
            # ここでも error_handler はまだ使えない
            print(f"依存関係の処理中にエラーが発生しました。詳細はログを確認してください。", file=sys.stderr)
            return False
    
    def initialize_configuration(self) -> bool:
        """設定システムを初期化"""
        self.logger.info("⚙️ 設定システムを初期化中...")
        
        try:
            self.config_manager = get_config_manager()
            # コマンドライン引数で設定ファイルが指定されていればそれを使用
            config_path_arg = getattr(self.args, 'config_file', None)
            if config_path_arg:
                config_file_path = Path(config_path_arg)
                if not config_file_path.is_file():
                    self.logger.warning(f"指定された設定ファイルが見つかりません: {config_file_path}")
                    # エラーを発生させるか、デフォルトに進むか選択できます                    # ここでは警告を出し、デフォルトのロードに進みます                    app_config = self.config_manager.get_config()
                else:                    app_config = self.config_manager.get_config()
            else:
                app_config = self.config_manager.get_config()            
            self.app_config = app_config # app_config をインスタンス変数に保存
            self.logger.info("設定をロードしました")
            
            # 設定の妥当性チェック
            if not self.config_manager.validate_config():
                self.logger.error("設定の妥当性チェックに失敗しました")
                return False
              # ログレベルを設定から更新
            log_level = getattr(logging, self.app_config.logging.level.upper())
            logging.getLogger().setLevel(log_level)
            
            self.logger.info("✅ 設定システム初期化完了")
            return True
            
        except ConfigurationError as e: # 設定システム固有のエラー
            self.logger.error(f"❌ 設定システム初期化エラー: {e.message}", exc_info=True)
            print(f"設定エラー: {e.user_message} 設定ファイルを確認してください。", file=sys.stderr)
            return False
        except Exception as e:
            self.logger.error(f"❌ 設定システム初期化中に予期せぬエラー: {e}", exc_info=True)
            print(f"設定システムの初期化に失敗しました。詳細はログを確認してください。", file=sys.stderr)
            return False
    
    def initialize_error_handling(self) -> bool:
        """エラーハンドリングシステムを初期化"""
        self.logger.info("🛡️ エラーハンドリングシステムを初期化中...")
        
        try:
            self.logger.info("エラーハンドリングシステムを初期化しています...")
            # get_error_handlerは引数を取らないため、修正
            self.error_handler = get_error_handler()
            # 必要であれば、app_configをエラーハンドラーに別途設定するメソッドをErrorHandlerクラスに追加検討
            # self.error_handler.set_config(self.app_config) 
            self.logger.info("エラーハンドリングシステムが正常に初期化されました。")
            
            # グローバル例外ハンドラーを設定
            def global_exception_handler(exc_type, exc_value, exc_traceback):
                if issubclass(exc_type, KeyboardInterrupt):
                    sys.__excepthook__(exc_type, exc_value, exc_traceback)
                    return
                
                self.logger.critical("未捕捉の例外が発生しました", 
                                   exc_info=(exc_type, exc_value, exc_traceback))
                self.error_handler.handle_exception(exc_value)
            
            sys.excepthook = global_exception_handler
            
            self.logger.info("✅ エラーハンドリングシステム初期化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ エラーハンドリングシステム初期化エラー: {e}", exc_info=True)
            # このエラーはグローバルハンドラでは捕捉されないため、直接出力
            print(f"エラーハンドリングシステムの初期化に失敗しました。詳細はログを確認してください。", file=sys.stderr)
            return False
    
    def initialize_performance_monitoring(self) -> bool:
        """パフォーマンス監視システムを初期化"""
        if hasattr(self.args, 'no_monitoring') and self.args.no_monitoring:
            self.logger.info("⏭️  パフォーマンス監視をスキップします")
            return True
        
        self.logger.info("📊 パフォーマンス監視システムを初期化中...")
        
        try:
            self.performance_monitor = get_performance_monitor()

            if self.app_config and self.app_config.performance_monitoring.monitoring_enabled:
                # PerformanceMonitorインスタンスに設定を適用する必要がある場合、ここで行う
                # 例: self.performance_monitor.configure(self.app_config.performance_monitoring, self.error_handler)
                # 現状のPerformanceMonitorの実装では、start_monitoringを呼び出すのみ
                self.performance_monitor.start_monitoring() # start_session から start_monitoring に変更
                self.logger.info("パフォーマンス監視システムが正常に初期化され、監視が開始されました。")
            else:
                # self.performance_monitor は get_performance_monitor() で取得済みなので、None に再代入しない
                # 必要であれば、監視を明示的に停止するメソッドを呼び出す
                # self.performance_monitor.stop_monitoring() 
                self.logger.info("パフォーマンス監視は設定で無効化されているか、設定が存在しません。")

            self.logger.info("✅ パフォーマンス監視システム初期化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ パフォーマンス監視システム初期化エラー: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, {"component": "PerformanceMonitor"})
            else:
                print(f"パフォーマンス監視システムの初期化エラー: {e}", file=sys.stderr)
            return False

    def initialize_security(self) -> bool:
        """セキュリティシステムを初期化"""
        if hasattr(self.args, 'no_security') and self.args.no_security:
            self.logger.info("⏭️  セキュリティシステムをスキップします")
            return True
        
        self.logger.info("🔒 セキュリティシステムを初期化中...")
        
        try:
            if not self.error_handler or not self.app_config:
                self.logger.error("セキュリティシステムの初期化に必要なコンポーネント（エラーハンドラまたは設定）がありません。")
                # 依存コンポーネントがない場合は、セキュリティマネージャを初期化しないか、
                # 限定的な機能で初期化するなどのフォールバック処理を検討
                self.security_manager = None 
                return False

            # IntegratedSecurityManager のインスタンスを取得または生成
            # get_security_manager は引数を取らない想定
            self.security_manager = get_security_manager()

            # IntegratedSecurityManager に設定とエラーハンドラを渡す
            # (IntegratedSecurityManager側に、これらのコンポーネントを受け取るメソッドが必要)
            if hasattr(self.security_manager, 'configure'):
                self.security_manager.configure(self.app_config.security, self.error_handler)
            else:
                self.logger.warning("SecurityManagerにconfigureメソッドが存在しません。設定の適用をスキップします。")

            # 必要に応じて、セキュリティ機能の有効化などを行う
            if self.app_config.security.encryption_enabled:
                if hasattr(self.security_manager, 'enable_encryption'):
                    self.security_manager.enable_encryption()
                    self.logger.info("データ暗号化が有効化されました。")
                else:
                    self.logger.warning("SecurityManagerにenable_encryptionメソッドが存在しません。")
            
            self.logger.info("セキュリティシステムが正常に初期化されました。")
            return True

        except Exception as e:
            self.logger.error(f"セキュリティシステムの初期化中にエラーが発生しました: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_error(
                    message=f"セキュリティシステム初期化エラー: {e}",
                    category=ErrorCategory.SECURITY,
                    severity=ErrorSeverity.HIGH, # セキュリティ関連は重要度を高めに設定
                    context={"component": "SecurityManager"}
                )
            self.security_manager = None # 初期化失敗時は無効化
            return False
            # セキュリティシステムの初期化失敗は致命的である可能性が高いため、再スローを検討
            # raise

    def launch_application(self) -> bool:
        """アプリケーションを起動"""
        self.logger.info("🚀 メインアプリケーションを起動中...")
        
        try:
            # UIモジュールのインポート（遅延インポート）
            try:
                from ui.modern_calculator_ui import ModernCompensationCalculator
            except ImportError as e:
                self.logger.error(f"UIモジュールのインポートに失敗: {e}")
                if self.error_handler:
                    self.error_handler.handle_exception(e, {"component": "UI_Loader", "message": "UIモジュールのロードに失敗しました。"})
                else:
                    print(f"UIモジュールのインポートエラー: {e}. 依存関係を確認してください。", file=sys.stderr)
                return False
            
            # アプリケーションの作成と起動
            app = ModernCompensationCalculator()
            
            self.logger.info("✅ アプリケーションを起動しました")
            self.logger.info("📱 UIが表示されるまでお待ちください...")
            
            # メインループの開始
            app.run()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ アプリケーション起動エラー: {e}", exc_info=True)
            if self.error_handler: # error_handler が初期化されていれば使用
                self.error_handler.handle_exception(e, {"component": "ApplicationLaunch"})
            else: # そうでなければ標準エラーに出力
                print(f"アプリケーションの起動に失敗しました: {e}", file=sys.stderr)
            return False
    
    def cleanup(self):
        """システムクリーンアップ"""
        self.logger.info("🧹 システムクリーンアップを実行中...")
        
        try:
            # パフォーマンス監視の停止
            if self.performance_monitor: # 属性存在チェックを追加
                self.performance_monitor.stop_monitoring()
                self.performance_monitor.export_performance_report("logs/performance_report.json")
            
            # エラーレポートの出力
            if self.error_handler: # 属性存在チェックを追加
                self.error_handler.export_error_report("logs/error_report.json")
              # セキュリティレポートの出力
            if self.security_manager:
                # IntegratedSecurityManagerの実際のメソッドを使用するか、実装がない場合はスキップ
                if hasattr(self.security_manager, 'get_security_summary'):
                    summary = self.security_manager.get_security_summary()
                    import json
                    with open("logs/security_summary.json", 'w', encoding='utf-8') as f:
                        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
                else:
                    self.logger.info("セキュリティサマリー機能は実装されていません。スキップします。")
            
            self.logger.info("✅ クリーンアップ完了")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}", exc_info=True)
            # クリーンアップ中のエラーはログに記録するのみ
    
    def run(self) -> int:
        """メイン実行関数"""
        try:
            self.logger.info(f"{'='*60}")
            self.logger.info("弁護士基準損害賠償計算システム v2.0")
            self.logger.info(f"起動時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"{'='*60}")
              # 1. システム要件チェック
            if not self.check_system_requirements():
                return 1
            
            # 2. 設定システム初期化
            if not self.initialize_configuration():
                return 1
            
            # 3. 依存関係セットアップ
            if not self.setup_dependencies():
                return 1
            
            # 4. エラーハンドリング初期化
            if not self.initialize_error_handling():
                return 1
            
            # 5. パフォーマンス監視初期化
            if not self.initialize_performance_monitoring():
                return 1
            
            # 6. セキュリティシステム初期化
            if not self.initialize_security():
                return 1
            
            self.components_initialized = True
            self.logger.info("🎉 すべてのシステムコンポーネントの初期化が完了しました")
            
            # 7. アプリケーション起動
            if not self.launch_application():
                return 1
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("ユーザーによって中断されました")
            return 0
        except CompensationSystemError as e: # アプリケーション固有の制御されたエラー
            self.logger.critical(f"システムエラーが発生しました: {e.message} (カテゴリ: {e.category}, 重要度: {e.severity})", exc_info=True)
            if self.error_handler: # error_handler が利用可能なら詳細を記録
                self.error_handler.handle_exception(e)
            else:
                print(f"システムエラー: {e.user_message}", file=sys.stderr)
            return 1
        except Exception as e: # その他の予期せぬ致命的エラー
            self.logger.critical(f"予期せぬ致命的エラーが発生しました: {e}", exc_info=True)
            if self.error_handler: # error_handler が利用可能なら使用
                handle_critical_error(e) # error_handler 内部で処理
            else: # そうでなければ基本的なメッセージを出力
                print(f"致命的なエラーが発生しました。アプリケーションを終了します。詳細はログを確認してください。", file=sys.stderr)
            return 1
        finally:
            if self.components_initialized:
                self.cleanup()
            else:
                self.logger.info("コンポーネントが完全に初期化される前に終了します。部分的なクリーンアップを試みます。")
                # 限定的なクリーンアップ (error_handler があればレポート出力など)
                if self.error_handler:
                    try:
                        self.error_handler.export_error_report("logs/error_report_partial_init.json")
                    except Exception as report_e:
                        self.logger.error(f"部分的クリーンアップ中のエラーレポート出力失敗: {report_e}")

    def _initialize_components(self):
        """主要コンポーネントの初期化"""
        if not self.app_config:
            self.logger.error("アプリケーション設定がロードされていません。コンポーネントを初期化できません。")
            raise ConfigurationError("アプリケーション設定がロードされていません。")
        
        self.error_handler = get_error_handler(self.app_config)  # app_config を渡す
        self.performance_monitor = get_performance_monitor(self.app_config) # app_config を渡す
        self.security_manager = get_security_manager(self.app_config) # app_config を渡す
        
        # ログレベルの設定 (app_config から取得)
        log_level_str = getattr(self.app_config.logging, 'level', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logging.basicConfig(level=log_level, format=getattr(self.app_config.logging, 'format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        self.logger.info("主要コンポーネントを初期化しました")
        self.components_initialized = True
    
    def _setup_logging(self):
        """ロギング設定"""
        if not self.app_config:
            # app_config がまだロードされていない場合、基本的なロギングを設定
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.logger = logging.getLogger(__name__)
            self.logger.warning("app_configが未ロードのため、デフォルトのロギング設定を使用します。")
            return
        
        log_config = self.app_config.logging
        log_level_str = getattr(log_config, 'level', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        log_format = getattr(log_config, 'format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = getattr(log_config, 'file', None)
        
        handlers: List[logging.Handler] = [logging.StreamHandler()] # logging.List ではなく List を使用
        
        if log_file:
            try:
                # ディレクトリが存在しない場合は作成
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
            except Exception as e:
                self.logger.error(f"ログファイルハンドラの作成に失敗しました: {log_file}, エラー: {e}")

    def _perform_dependency_check(self):
        """依存関係のチェックとインストール"""
        self.logger.info("依存関係のチェックを開始します...")
        try:
            dm = DependencyManager(self.app_config) # AppConfig を渡して初期化
            dm.check_and_install_dependencies()
            self.logger.info("依存関係のチェックとインストールが完了しました。")
        except Exception as e:
            self.logger.error(f"依存関係の処理中にエラーが発生しました: {e}", exc_info=True)
            # 依存関係のエラーはクリティカルな場合がある
            # ここでユーザーに通知し、終了するかどうかを検討
            print(f"⚠️ 依存関係の処理中にエラー: {e}")
            # sys.exit(1) # 必要に応じて終了
    
    def _initialize_error_handling(self):
        """エラーハンドリングシステムの初期化"""
        if not self.app_config:
            self.logger.error("エラーハンドリング初期化の前にアプリケーション設定がロードされていません。")
            # デフォルト設定で ErrorHandler を初期化するか、エラーとする
            # ここでは、基本的なエラーハンドラを設定
            self.error_handler = ErrorHandler(AppConfig()) # デフォルトのAppConfigで初期化
            logging.basicConfig(level=logging.INFO) # 基本的なロギング
            self.logger = logging.getLogger(__name__)
            self.logger.warning("AppConfigが未ロードのため、デフォルトのエラーハンドリング設定を使用します。")
        else:
            self.error_handler = get_error_handler(self.app_config)
        
        # グローバルな例外フックの設定
        # sys.excepthook = self.error_handler.handle_exception # ここで設定すると、以降のすべての未処理例外を補足
        # ただし、これが早すぎると、他の初期化処理中のエラーも補足してしまう可能性がある
        # main 関数の最後や、アプリケーション実行直前に設定するのが一般的
        self.logger.info("エラーハンドリングシステムを初期化しました")
    
    def _launch_application(self):
        """アプリケーションの起動"""
        if not self.components_initialized:
            self.logger.error("コンポーネントが初期化されていないため、アプリケーションを起動できません。")
            return
        
        self.logger.info("アプリケーションの起動準備ができました。")
        # ここで実際のアプリケーション（例：UI）を起動します。
        # 例: from ui.main_window import launch_ui; launch_ui(self.app_config)
        try:
            # UIのインポートと起動
            # from ui.modern_calculator_ui import launch_ui # modern_calculator_ui があると仮定
            # launch_ui(self.app_config, self.security_manager, self.performance_monitor)
            self.logger.info("アプリケーション（UI）を起動します...")
            print("仮のアプリケーション実行ポイント。実際のUIや処理をここに実装します。")
            
            # 簡単なテスト実行
            if self.args.run_simple_test:
                self.logger.info("簡易テストを実行します...")
                self._run_simple_test()
            else:
                self.logger.info("通常のアプリケーションフローを実行します。 (現在はプレースホルダー)")
                # ここにメインのアプリケーションロジックを配置
                # 例: self._start_main_application_loop()
        
        except ImportError as e:
            self.logger.error(f"UIモジュールのインポートに失敗しました: {e}", exc_info=True)
            self.error_handler.handle_error(e, "UIの起動に失敗しました", ErrorSeverity.CRITICAL)
        except Exception as e:
            self.logger.error(f"アプリケーションの起動中に予期せぬエラーが発生しました: {e}", exc_info=True)
            self.error_handler.handle_error(e, "アプリケーションの起動エラー", ErrorSeverity.CRITICAL)
    
    def _run_simple_test(self):
        """設定と主要コンポーネントの動作を確認する簡単なテスト"""
        if not self.app_config or not self.security_manager or not self.performance_monitor or not self.error_handler:
            self.logger.error("簡易テストの実行に必要なコンポーネントが初期化されていません。")
            return
        
        self.logger.info("--- 簡易テスト開始 ---")
        try:
            # 1. 設定値の読み取りテスト
            self.logger.info(f"アプリケーション名 (設定より): {self.app_config.application.name}")
            self.logger.info(f"デフォルトのExcelテンプレート (設定より): {self.app_config.reporting.excel.default_template}")
            
            # 2. パフォーマンスモニターのテスト
            self.performance_monitor.start_timing("simple_test_task")
            # 何か処理を行う (例: time.sleep(0.1))
            import time
            time.sleep(0.1)
            self.performance_monitor.end_timing("simple_test_task")
            self.logger.info(f"パフォーマンスモニターテスト: simple_test_task の実行時間記録完了")
            self.logger.info(f"現在のメモリ使用量: {self.performance_monitor.get_memory_usage()} MB")
            
            # 3. セキュリティマネージャーのテスト (簡単な暗号化・復号化)
            if self.app_config.security.encryption_enabled:
                original_data = "これは秘密のテストデータです。"
                self.logger.info(f"元のデータ: {original_data}")
                encrypted_data = self.security_manager.encrypt_data(original_data, DataCategory.CASE_DATA)
                self.logger.info(f"暗号化されたデータ: {encrypted_data[:30]}...") # 長すぎる場合は一部表示
                decrypted_data = self.security_manager.decrypt_data(encrypted_data, DataCategory.CASE_DATA)
                self.logger.info(f"復号化されたデータ: {decrypted_data}")
                if original_data == decrypted_data:
                    self.logger.info("暗号化・復号化テスト成功！")
                else:
                    self.logger.error("暗号化・復号化テスト失敗！")
            else:
                self.logger.info("暗号化が無効なため、セキュリティマネージャーの暗号化テストはスキップされました。")
            
            # 4. エラーハンドリングのテスト (意図的な軽微なエラー)
            try:
                raise ValueError("これはテスト用の軽微なエラーです。")
            except ValueError as ve:
                self.error_handler.handle_error(ve, "テストエラーハンドリング", ErrorSeverity.WARNING)
            self.logger.info("エラーハンドリングテスト (軽微なエラーの処理) 完了")
            
            self.logger.info("--- 簡易テスト終了 ---")
        except Exception as e:
            self.logger.error(f"簡易テスト中にエラーが発生しました: {e}", exc_info=True)
            self.error_handler.handle_error(e, "簡易テストの実行失敗", ErrorSeverity.ERROR)
  

def create_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="弁護士基準損害賠償計算システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py                    # 通常起動
  python main.py --dev-mode         # 開発者モード
  python main.py --auto-install     # 自動依存関係インストール
  python main.py --no-monitoring    # 監視なしで起動
  python main.py --skip-deps        # 依存関係チェックスキップ
        """
    )
    
    parser.add_argument('--dev-mode', action='store_true',
                       help='開発者モードで起動（デバッグ機能有効）')
    parser.add_argument('--auto-install', action='store_true',
                       help='不足している依存関係を自動インストール')
    parser.add_argument('--skip-deps', action='store_true',
                       help='依存関係チェックをスキップ')
    parser.add_argument('--no-monitoring', action='store_true',
                       help='パフォーマンス監視を無効化')
    parser.add_argument('--no-security', action='store_true',
                       help='セキュリティシステムを無効化')
    parser.add_argument('--config-file', type=str,
                       help='設定ファイルのパスを指定')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='ログレベルを指定')
    parser.add_argument('--version', action='version', version='%(prog)s 2.0')
    
    return parser

def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # ランチャーを作成して実行
    launcher = CompensationSystemLauncher(args)
    exit_code = launcher.run()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
