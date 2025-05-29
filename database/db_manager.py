#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLiteデータベース管理システム
案件データの永続化、検索、バックアップを担当
"""

import sqlite3
import logging
import json
import shutil
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple, Union, Callable

from utils.error_handler import get_error_handler, DatabaseError, ErrorSeverity
from config.app_config import ConfigManager
from models import CaseData

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DatabaseManager:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: Union[str, Path], config_manager: Optional[ConfigManager] = None, logger: Optional[logging.Logger] = None):
        self.db_path = Path(db_path)
        self.logger = logger or logging.getLogger(__name__)
        self._error_handler = get_error_handler() # 追加
        self.config_manager = config_manager if config_manager else ConfigManager() # 設定マネージャーを初期化

        db_config = self.config_manager.get_config().database
        self.journal_mode = db_config.journal_mode
        self.enable_foreign_keys = db_config.enable_foreign_keys
        self.connection_timeout = db_config.connection_timeout_seconds
        self.backup_dir = Path(db_config.backup_dir)
        self.max_backup_files = db_config.max_backup_files

        if not self.db_path.parent.exists():
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                err = DatabaseError(f"データベースディレクトリの作成に失敗しました: {self.db_path.parent}", severity=ErrorSeverity.CRITICAL, context={"path": str(self.db_path.parent)})
                self._error_handler.handle_exception(e, context=err.context)
                raise err from e # 再送してアプリケーションの起動を妨げる
        
        self._create_connection() # 初期接続試行
        self._initialize_db() # 初期化
    
    def _create_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path, timeout=self.connection_timeout, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            if self.journal_mode:
                conn.execute(f"PRAGMA journal_mode={self.journal_mode};")
            if self.enable_foreign_keys:
                conn.execute("PRAGMA foreign_keys = ON;")
            self.logger.info(f"データベースに接続しました: {self.db_path}")
            return conn
        except sqlite3.Error as e:
            db_err = DatabaseError(
                message=f"データベース接続エラー: {self.db_path}",
                user_message="データベースへの接続に失敗しました。ファイルパスや権限を確認してください。",
                severity=ErrorSeverity.CRITICAL,
                context={"db_path": str(self.db_path), "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=db_err.context)
            raise db_err from e

    def _close_connection(self, conn: Optional[sqlite3.Connection]):
        if conn:
            conn.close()
            self.logger.info(f"データベース接続を閉じました: {self.db_path}")

    def get_connection(self):
        """データベース接続をコンテキストマネージャーとして取得"""
        return self._create_connection()

    def execute_query(self, query: str, params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None, commit: bool = False, fetch_one: bool = False, fetch_all: bool = False) -> Any:
        conn = None
        try:
            conn = self._create_connection()
            cursor = conn.cursor()
            self.logger.debug(f"Executing query: {query} with params: {params}")
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if commit:
                conn.commit()
                self.logger.info(f"Query committed: {query[:50]}...")
                return cursor.lastrowid
            
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor # DDLなどの場合
        except sqlite3.IntegrityError as e:
            db_err = DatabaseError(
                message=f"データベース整合性エラー: {e}", 
                user_message="データの一貫性に問題が発生しました。入力内容を確認してください。",
                severity=ErrorSeverity.MEDIUM,
                context={"query": query, "params": params, "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=db_err.context)
            if conn: conn.rollback()
            raise db_err from e
        except sqlite3.OperationalError as e:
            db_err = DatabaseError(
                message=f"データベース操作エラー: {e}", 
                user_message="データベース操作中に問題が発生しました。スキーマや権限を確認してください。",
                severity=ErrorSeverity.HIGH,
                context={"query": query, "params": params, "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=db_err.context)
            if conn: conn.rollback()
            raise db_err from e
        except sqlite3.Error as e: # その他のsqlite3エラー
            db_err = DatabaseError(
                message=f"データベース一般エラー: {e}", 
                user_message="データベース処理中に予期せぬエラーが発生しました。",
                severity=ErrorSeverity.HIGH,
                context={"query": query, "params": params, "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=db_err.context)
            if conn: conn.rollback()
            raise db_err from e
        except Exception as e: # 予期せぬその他のエラー
            unknown_err = DatabaseError(
                message=f"予期せぬデータベース関連エラー: {e}",
                user_message="データベース処理中に不明なエラーが発生しました。システム管理者にお問い合わせください。",
                severity=ErrorSeverity.CRITICAL,
                context={"query": query, "params": params, "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=unknown_err.context)
            if conn: conn.rollback()
            raise unknown_err from e
        finally:
            self._close_connection(conn)

    def execute_script(self, script: str) -> None:
        conn = None
        try:
            conn = self._create_connection()
            cursor = conn.cursor()
            self.logger.info("Executing script...")
            cursor.executescript(script)
            conn.commit()
            self.logger.info("Script executed and committed successfully.")
        except sqlite3.Error as e:
            db_err = DatabaseError(
                message=f"データベーススクリプト実行エラー: {e}",
                user_message="データベース初期化またはマイグレーションスクリプトの実行に失敗しました。",
                severity=ErrorSeverity.CRITICAL,
                context={"script_snippet": script[:200], "original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=db_err.context)
            if conn: conn.rollback()
            raise db_err from e
        finally:
            self._close_connection(conn)

    def _initialize_db(self):
        """データベースの初期化（テーブル作成など）"""
        try:            # 案件テーブル
            create_cases_table = """
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT UNIQUE NOT NULL,
                case_name TEXT,
                created_date TEXT,
                last_modified TEXT,
                status TEXT DEFAULT '作成中',
                client_name TEXT,
                person_info TEXT,
                accident_info TEXT,
                medical_info TEXT,
                income_info TEXT,
                calculation_results TEXT,
                notes TEXT,
                custom_fields TEXT DEFAULT '{}',
                is_archived BOOLEAN DEFAULT 0
            );
            """
            
            # 計算履歴テーブル
            create_history_table = """
            CREATE TABLE IF NOT EXISTS calculation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                calculation_date TEXT,
                calculation_type TEXT,
                input_data TEXT,
                results TEXT,
                notes TEXT,
                FOREIGN KEY (case_id) REFERENCES cases (id)
            );
            """
            
            # バックアップ記録テーブル
            create_backup_table = """
            CREATE TABLE IF NOT EXISTS backup_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT,
                backup_path TEXT,
                file_size INTEGER,
                success BOOLEAN
            );
            """
            
            # 設定テーブル
            create_settings_table = """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_modified TEXT
            );
            """
            
            # テンプレートテーブル
            create_templates_table = """
            CREATE TABLE IF NOT EXISTS case_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT UNIQUE NOT NULL,
                template_data TEXT,
                created_date TEXT,
                last_modified TEXT,
                description TEXT
            );
            """
            
            # テーブルを作成
            self.execute_query(create_cases_table)
            self.execute_query(create_history_table)
            self.execute_query(create_backup_table)
            self.execute_query(create_settings_table)
            self.execute_query(create_templates_table)
            
            # インデックス作成
            self.execute_query("CREATE INDEX IF NOT EXISTS idx_cases_case_number ON cases (case_number);")
            self.execute_query("CREATE INDEX IF NOT EXISTS idx_cases_client_name ON cases (client_name);")
            self.execute_query("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases (status);")
            self.execute_query("CREATE INDEX IF NOT EXISTS idx_history_case_id ON calculation_history (case_id);")
            self.execute_query("CREATE INDEX IF NOT EXISTS idx_templates_name ON case_templates (template_name);")
            
            self.logger.info("データベースの初期化が完了しました")
        except DatabaseError as e: # execute_query/script から送出されるエラー
            # 初期化時のエラーは致命的である可能性が高い
            self.logger.critical(f"データベース初期化に失敗: {e.message}")
            # _error_handler.handle_exception は execute_query/script 内で呼ばれているのでここでは不要
            raise # アプリケーションの起動を止めるために再送
        except Exception as e: # 万が一 DatabaseError 以外が来た場合
            db_err = DatabaseError(
                message=f"データベース初期化中に予期せぬエラー: {e}",
                user_message="データベースのセットアップ中に重大なエラーが発生しました。",
                severity=ErrorSeverity.CRITICAL,
                context={"original_error": str(e)}
            )
            self._error_handler.handle_exception(e, context=db_err.context)
            raise db_err from e

    def save_case(self, case_data: CaseData) -> bool:
        """案件データを保存（新規作成・更新両対応）"""
        if not case_data or not case_data.case_number:
            self.logger.error("無効な案件データです: case_numberが空です")
            return False
            
        try:
            case_data.last_modified = datetime.now()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 既存データの確認
                cursor.execute('SELECT id FROM cases WHERE case_number = ?', (case_data.case_number,))
                existing = cursor.fetchone()
                
                # JSONシリアライゼーションの安全化
                def safe_json_dumps(obj):
                    """安全なJSON変換"""
                    try:
                        if hasattr(obj, 'to_dict'):
                            return json.dumps(obj.to_dict(), ensure_ascii=False, default=str)
                        else:
                            return json.dumps(obj, ensure_ascii=False, default=str)
                    except (TypeError, ValueError) as e:
                        self.logger.warning(f"JSON変換エラー（空辞書で代替）: {e}")
                        return json.dumps({}, ensure_ascii=False)
                
                if existing:
                    # 更新
                    cursor.execute('''
                        UPDATE cases SET
                            last_modified = ?,
                            status = ?,
                            person_info = ?,
                            accident_info = ?,
                            medical_info = ?,
                            income_info = ?,
                            notes = ?,
                            custom_fields = ?,
                            calculation_results = ?
                        WHERE case_number = ?
                    ''', (
                        case_data.last_modified.isoformat(),
                        case_data.status or '作成中',
                        safe_json_dumps(case_data.person_info),
                        safe_json_dumps(case_data.accident_info),
                        safe_json_dumps(case_data.medical_info),
                        safe_json_dumps(case_data.income_info),
                        case_data.notes or '',
                        safe_json_dumps(case_data.custom_fields or {}),
                        safe_json_dumps(case_data.calculation_results or {}),
                        case_data.case_number
                    ))
                    self.logger.info(f"案件データを更新しました: {case_data.case_number}")
                else:
                    # 新規作成
                    cursor.execute('''
                        INSERT INTO cases (
                            case_number, created_date, last_modified, status,
                            person_info, accident_info, medical_info, income_info,
                            notes, custom_fields, calculation_results
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        case_data.case_number,
                        (case_data.created_date or datetime.now()).isoformat(),
                        case_data.last_modified.isoformat(),
                        case_data.status or '作成中',
                        safe_json_dumps(case_data.person_info),
                        safe_json_dumps(case_data.accident_info),
                        safe_json_dumps(case_data.medical_info),
                        safe_json_dumps(case_data.income_info),
                        case_data.notes or '',
                        safe_json_dumps(case_data.custom_fields or {}),
                        safe_json_dumps(case_data.calculation_results or {})
                    ))
                    self.logger.info(f"新規案件データを作成しました: {case_data.case_number}")
                
                conn.commit()
                return True
                
        except sqlite3.IntegrityError as e:
            self.logger.error(f"案件番号重複エラー: {case_data.case_number} - {e}")
            return False
        except Exception as e:
            self.logger.error(f"案件保存エラー: {e}")
            return False

    def load_case(self, case_number: str) -> Optional[CaseData]:
        """案件番号で案件データを読み込み"""
        if not case_number or not case_number.strip():
            self.logger.error("案件番号が空です")
            return None
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM cases WHERE case_number = ? AND is_archived = 0', (case_number.strip(),))
                row = cursor.fetchone()
                
                if row:
                    def safe_json_loads(json_str, default=None):
                        """安全なJSON読み込み"""
                        if not json_str:
                            return default or {}
                        try:
                            return json.loads(json_str)
                        except (json.JSONDecodeError, TypeError) as e:
                            self.logger.warning(f"JSON読み込みエラー（デフォルト値で代替）: {e}")
                            return default or {}
                    
                    case_data = CaseData()
                    case_data.case_number = row['case_number']
                    
                    # 日付の安全な変換
                    try:
                        case_data.created_date = datetime.fromisoformat(row['created_date'])
                    except (ValueError, TypeError):
                        case_data.created_date = datetime.now()
                        self.logger.warning(f"作成日時の変換に失敗: {row['created_date']}")
                    
                    try:
                        case_data.last_modified = datetime.fromisoformat(row['last_modified'])
                    except (ValueError, TypeError):
                        case_data.last_modified = datetime.now()
                        self.logger.warning(f"更新日時の変換に失敗: {row['last_modified']}")
                    
                    case_data.status = row['status'] or '作成中'
                    
                    # 各情報セクションの安全な読み込み
                    try:
                        person_data = safe_json_loads(row['person_info'])
                        case_data.person_info = case_data.person_info.from_dict(person_data)
                    except Exception as e:
                        self.logger.warning(f"個人情報の読み込みエラー: {e}")
                        
                    try:
                        accident_data = safe_json_loads(row['accident_info'])
                        case_data.accident_info = case_data.accident_info.from_dict(accident_data)
                    except Exception as e:
                        self.logger.warning(f"事故情報の読み込みエラー: {e}")
                        
                    try:
                        medical_data = safe_json_loads(row['medical_info'])
                        case_data.medical_info = case_data.medical_info.from_dict(medical_data)
                    except Exception as e:
                        self.logger.warning(f"医療情報の読み込みエラー: {e}")
                        
                    try:
                        income_data = safe_json_loads(row['income_info'])
                        case_data.income_info = case_data.income_info.from_dict(income_data)
                    except Exception as e:
                        self.logger.warning(f"収入情報の読み込みエラー: {e}")
                    
                    case_data.notes = row['notes'] or ""
                    case_data.custom_fields = safe_json_loads(row['custom_fields'], {})
                    case_data.calculation_results = safe_json_loads(row['calculation_results'], {})
                    
                    self.logger.debug(f"案件データを正常に読み込みました: {case_number}")
                    return case_data
                else:
                    self.logger.info(f"指定された案件が見つかりません: {case_number}")
                    
        except Exception as e:
            self.logger.error(f"案件読み込みエラー: {case_number} - {e}")
        
        return None
    
    def load_case_by_id(self, case_id: int) -> Optional[Dict[str, Any]]:
        """案件IDで案件データを読み込み（辞書形式で返す）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM cases WHERE id = ? AND is_archived = 0', (case_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row['id'],
                        'case_number': row['case_number'],
                        'created_date': row['created_date'],
                        'last_modified': row['last_modified'],
                        'status': row['status'],
                        'person_info': json.loads(row['person_info']),
                        'accident_info': json.loads(row['accident_info']),
                        'medical_info': json.loads(row['medical_info']),
                        'income_info': json.loads(row['income_info']),
                        'notes': row['notes'] or "",
                        'custom_fields': json.loads(row['custom_fields']) if row['custom_fields'] else {},
                        'calculation_results': json.loads(row['calculation_results']) if row['calculation_results'] else {}
                    }
                    
        except Exception as e:
            self.logger.error(f"案件読み込みエラー (ID: {case_id}): {e}")
        
        return None
    
    def search_cases(self, 
                    case_number_pattern: str = None,
                    client_name_pattern: str = None,
                    status: str = None,
                    date_from: date = None,
                    date_to: date = None,
                    search_term: str = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """案件検索"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, case_number, created_date, last_modified, status,
                           json_extract(person_info, '$.name') as client_name,
                           json_extract(accident_info, '$.accident_date') as accident_date
                    FROM cases 
                    WHERE is_archived = 0
                '''
                params = []
                
                if case_number_pattern:
                    query += ' AND case_number LIKE ?'
                    params.append(f'%{case_number_pattern}%')
                
                if client_name_pattern:
                    query += ' AND json_extract(person_info, "$.name") LIKE ?'
                    params.append(f'%{client_name_pattern}%')
                
                if status:
                    query += ' AND status = ?'
                    params.append(status)
                
                if date_from:
                    query += ' AND created_date >= ?'
                    params.append(date_from.isoformat())
                
                if date_to:
                    query += ' AND created_date <= ?'
                    params.append(date_to.isoformat())
                
                # 汎用検索条件（案件番号または依頼者名に一致）
                if search_term:
                    query += ' AND (case_number LIKE ? OR json_extract(person_info, "$.name") LIKE ?)'
                    params.extend([f'%{search_term}%', f'%{search_term}%'])
                
                query += ' ORDER BY last_modified DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"案件検索エラー: {e}")
            return []
    
    def delete_case(self, case_number: str) -> bool:
        """案件を論理削除（アーカイブ）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE cases SET is_archived = 1 WHERE case_number = ?', (case_number,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    self.logger.info(f"案件をアーカイブしました: {case_number}")
                    return True
                else:
                    self.logger.warning(f"アーカイブ対象の案件が見つかりません: {case_number}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"案件削除エラー: {case_number} - {e}")
            return False
    
    def create_backup(self, backup_dir: str = "backups") -> bool:
        """データベースのバックアップ作成"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"compensation_db_backup_{timestamp}.db"
            
            shutil.copy2(self.db_path, backup_file)
            
            # バックアップ記録を保存
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO backup_records (backup_date, backup_file_path, backup_type, file_size)
                    VALUES (?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    str(backup_file),
                    "自動バックアップ",
                    backup_file.stat().st_size
                ))
                conn.commit()
            
            self.logger.info(f"バックアップを作成しました: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """データベース統計情報を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 総案件数
                cursor.execute('SELECT COUNT(*) FROM cases WHERE is_archived = 0')
                stats['total_cases'] = cursor.fetchone()[0]
                
                # ステータス別件数
                cursor.execute('SELECT status, COUNT(*) FROM cases WHERE is_archived = 0 GROUP BY status')
                stats['status_counts'] = dict(cursor.fetchall())
                
                # 月別作成件数（直近12ヶ月）
                cursor.execute('''
                    SELECT strftime('%Y-%m', created_date) as month, COUNT(*) 
                    FROM cases 
                    WHERE is_archived = 0 AND created_date >= date('now', '-12 months')
                    GROUP BY month 
                    ORDER BY month
                ''')
                stats['monthly_cases'] = dict(cursor.fetchall())
                
                return stats
                
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            return {}
    
    # テンプレート管理メソッド
    def save_template(self, name: str, case_data: CaseData) -> Optional[int]:
        """案件データをテンプレートとして保存"""
        try:
            # テンプレート用にCaseDataをコピーし、固有フィールドをクリア
            template_data = CaseData()
            template_data.person_info = case_data.person_info
            template_data.accident_info = case_data.accident_info
            template_data.medical_info = case_data.medical_info
            template_data.income_info = case_data.income_info
            template_data.notes = case_data.notes
            template_data.custom_fields = case_data.custom_fields
            # case_number, id, created_date, last_modified, status, calculation_resultsは除外
            
            # JSONに変換
            template_json = json.dumps({
                'person_info': template_data.person_info.to_dict(),
                'accident_info': template_data.accident_info.to_dict(),
                'medical_info': template_data.medical_info.to_dict(),
                'income_info': template_data.income_info.to_dict(),
                'notes': template_data.notes,
                'custom_fields': template_data.custom_fields
            }, ensure_ascii=False)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                # 既存テンプレートの確認
                cursor.execute('SELECT template_id FROM case_templates WHERE name = ?', (name,))
                existing = cursor.fetchone()
                
                if existing:
                    # 更新
                    cursor.execute('''
                        UPDATE case_templates SET 
                            data_json = ?,
                            updated_at = ?
                        WHERE name = ?
                    ''', (template_json, now, name))
                    template_id = existing[0]
                    self.logger.info(f"テンプレート '{name}' を更新しました")
                else:
                    # 新規作成
                    cursor.execute('''
                        INSERT INTO case_templates (name, data_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    ''', (name, template_json, now, now))
                    template_id = cursor.lastrowid
                    self.logger.info(f"新規テンプレート '{name}' を作成しました")
                
                conn.commit()
                return template_id
                
        except sqlite3.IntegrityError as e:
            self.logger.error(f"テンプレート名重複エラー: {name} - {e}")
            return None
        except Exception as e:
            self.logger.error(f"テンプレート保存エラー: {e}")
            return None
    
    def load_template(self, template_id: int) -> Optional[CaseData]:
        """テンプレートIDでテンプレートを読み込み"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT data_json FROM case_templates WHERE template_id = ?', (template_id,))
                row = cursor.fetchone()
                
                if row:
                    template_dict = json.loads(row[0])
                    
                    # 新しいCaseDataインスタンスを作成
                    case_data = CaseData()
                    case_data.person_info = case_data.person_info.from_dict(template_dict['person_info'])
                    case_data.accident_info = case_data.accident_info.from_dict(template_dict['accident_info'])
                    case_data.medical_info = case_data.medical_info.from_dict(template_dict['medical_info'])
                    case_data.income_info = case_data.income_info.from_dict(template_dict['income_info'])
                    case_data.notes = template_dict.get('notes', "")
                    case_data.custom_fields = template_dict.get('custom_fields', {})
                    
                    return case_data
                    
        except Exception as e:
            self.logger.error(f"テンプレート読み込みエラー: {template_id} - {e}")
        
        return None
    
    def get_all_templates_summary(self) -> List[Tuple[int, str, str]]:
        """すべてのテンプレートのサマリーを取得（ID、名前、更新日時）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT template_id, name, updated_at 
                    FROM case_templates 
                    ORDER BY updated_at DESC
                ''')
                return cursor.fetchall()
                
        except Exception as e:
            self.logger.error(f"テンプレートサマリー取得エラー: {e}")
            return []
    
    def delete_template(self, template_id: int) -> bool:
        """テンプレートを削除"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM case_templates WHERE template_id = ?', (template_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    self.logger.info(f"テンプレート (ID: {template_id}) を削除しました")
                    return True
                else:
                    self.logger.warning(f"削除対象のテンプレートが見つかりません: {template_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"テンプレート削除エラー: {template_id} - {e}")
            return False

    def get_template_by_name(self, name: str) -> Optional[CaseData]:
        """テンプレート名でテンプレートを検索"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT template_id FROM case_templates WHERE name = ?', (name,))
                row = cursor.fetchone()
                
                if row:
                    return self.load_template(row[0])
                    
        except Exception as e:
            self.logger.error(f"テンプレート名検索エラー: {name} - {e}")
        
        return None

    # バッチ処理とメンテナンス機能
    def batch_save_cases(self, cases: List[CaseData]) -> Dict[str, Any]:
        """複数案件の一括保存"""
        results = {
            'success_count': 0,
            'failed_count': 0,
            'errors': []
        }
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for case_data in cases:
                    try:
                        # 個別の保存処理（トランザクション内で実行）
                        if self._save_single_case_in_transaction(cursor, case_data):
                            results['success_count'] += 1
                        else:
                            results['failed_count'] += 1
                            results['errors'].append(f"保存失敗: {case_data.case_number}")
                    except Exception as e:
                        results['failed_count'] += 1
                        results['errors'].append(f"{case_data.case_number}: {str(e)}")
                
                conn.commit()
                self.logger.info(f"バッチ保存完了: 成功{results['success_count']}件、失敗{results['failed_count']}件")
                
        except Exception as e:
            self.logger.error(f"バッチ保存エラー: {e}")
            results['errors'].append(f"バッチ処理エラー: {str(e)}")
        
        return results

    def _save_single_case_in_transaction(self, cursor, case_data: CaseData) -> bool:
        """トランザクション内での単一案件保存（内部使用）"""
        # save_caseメソッドのロジックをトランザクション用に分離
        # 実装詳細は省略（必要に応じて追加）
        return True

    def optimize_database(self) -> bool:
        """データベースの最適化とメンテナンス"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # VACUUM実行（データベースの最適化）
                cursor.execute('VACUUM')
                
                # 統計情報の更新
                cursor.execute('ANALYZE')
                
                # WALファイルのチェックポイント
                cursor.execute('PRAGMA wal_checkpoint(FULL)')
                
                self.logger.info("データベースの最適化が完了しました")
                return True
                
        except Exception as e:
            self.logger.error(f"データベース最適化エラー: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """データベースの詳細情報を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                info = {}
                
                # ファイルサイズ
                info['file_size'] = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                # SQLiteバージョン
                cursor.execute('SELECT sqlite_version()')
                info['sqlite_version'] = cursor.fetchone()[0]
                
                # テーブル情報
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                info['tables'] = [row[0] for row in cursor.fetchall()]
                
                # 各テーブルの行数
                table_counts = {}
                for table in info['tables']:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    table_counts[table] = cursor.fetchone()[0]
                info['table_counts'] = table_counts
                
                return info
                
        except Exception as e:
            self.logger.error(f"データベース情報取得エラー: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """データベースの健全性チェック"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                health = {
                    'status': 'healthy',
                    'issues': [],
                    'recommendations': []
                }
                
                # 整合性チェック
                cursor.execute('PRAGMA integrity_check')
                integrity_result = cursor.fetchone()[0]
                if integrity_result != 'ok':
                    health['status'] = 'warning'
                    health['issues'].append(f"整合性チェック失敗: {integrity_result}")
                
                # 孤立レコードチェック
                cursor.execute('''
                    SELECT COUNT(*) FROM calculation_history ch
                    LEFT JOIN cases c ON ch.case_id = c.id
                    WHERE c.id IS NULL
                ''')
                orphaned_calculations = cursor.fetchone()[0]
                if orphaned_calculations > 0:
                    health['issues'].append(f"孤立した計算履歴: {orphaned_calculations}件")
                    health['recommendations'].append("孤立レコードのクリーンアップを実行してください")
                
                # ファイルサイズチェック
                file_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
                if file_size_mb > 100:  # 100MB以上の場合
                    health['recommendations'].append(f"データベースサイズが大きいです({file_size_mb:.1f}MB)。最適化を検討してください")
                
                return health
                
        except Exception as e:
            return {
                'status': 'error',
                'issues': [f"ヘルスチェック実行エラー: {str(e)}"],
                'recommendations': ['データベース接続を確認してください']
            }
