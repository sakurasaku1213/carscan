#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースマネージャーのユニットテスト
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, date
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database.db_manager import DatabaseManager
from models.case_data import CaseData

class TestDatabaseManager:
    """DatabaseManagerクラスのテスト"""
    
    def test_init_database(self, temp_db_path):
        """データベース初期化のテスト"""
        db_manager = DatabaseManager(str(temp_db_path))
        
        # データベースファイルが作成されることを確認
        assert temp_db_path.exists()
        
        # テーブルが作成されることを確認
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'cases', 'calculation_history', 'backup_records', 
                'settings', 'case_templates'
            ]
            for table in expected_tables:
                assert table in tables
    
    def test_save_and_load_case(self, mock_database_manager, sample_case_data):
        """案件の保存と読み込みのテスト"""
        # 案件を保存
        success = mock_database_manager.save_case(sample_case_data)
        assert success
        
        # 案件を読み込み
        loaded_case = mock_database_manager.load_case(sample_case_data.case_number)
        assert loaded_case is not None
        assert loaded_case.case_number == sample_case_data.case_number
        assert loaded_case.person_info.name == sample_case_data.person_info.name
        assert loaded_case.accident_info.accident_type == sample_case_data.accident_info.accident_type
    
    def test_save_case_validation(self, mock_database_manager):
        """案件保存時のバリデーションテスト"""
        # 無効なケースデータ
        invalid_case = CaseData()
        invalid_case.case_number = ""  # 空の案件番号
        
        success = mock_database_manager.save_case(invalid_case)
        assert not success
        
        # Noneの場合
        success = mock_database_manager.save_case(None)
        assert not success
    
    def test_load_nonexistent_case(self, mock_database_manager):
        """存在しない案件の読み込みテスト"""
        result = mock_database_manager.load_case("NONEXISTENT-CASE")
        assert result is None
    
    def test_search_cases(self, mock_database_manager, sample_case_data):
        """案件検索のテスト"""
        # テストデータを保存
        mock_database_manager.save_case(sample_case_data)
        
        # 案件番号で検索
        results = mock_database_manager.search_cases(
            case_number_pattern="TEST-2024"
        )
        assert len(results) >= 1
        assert any(r['case_number'] == sample_case_data.case_number for r in results)
        
        # 依頼者名で検索
        results = mock_database_manager.search_cases(
            client_name_pattern="テスト太郎"
        )
        assert len(results) >= 1
    
    def test_delete_case(self, mock_database_manager, sample_case_data):
        """案件削除（アーカイブ）のテスト"""
        # 案件を保存
        mock_database_manager.save_case(sample_case_data)
        
        # 削除（アーカイブ）
        success = mock_database_manager.delete_case(sample_case_data.case_number)
        assert success
        
        # アーカイブ後は読み込めないことを確認
        loaded_case = mock_database_manager.load_case(sample_case_data.case_number)
        assert loaded_case is None
    
    def test_get_statistics(self, mock_database_manager, sample_case_data):
        """統計情報取得のテスト"""
        # テストデータを保存
        mock_database_manager.save_case(sample_case_data)
        
        stats = mock_database_manager.get_statistics()
        assert 'total_cases' in stats
        assert 'status_counts' in stats
        assert stats['total_cases'] >= 1
    
    def test_template_operations(self, mock_database_manager, sample_case_data):
        """テンプレート操作のテスト"""
        template_name = "テストテンプレート"
        
        # テンプレートを保存
        template_id = mock_database_manager.save_template(template_name, sample_case_data)
        assert template_id is not None
        
        # テンプレートを読み込み
        loaded_template = mock_database_manager.load_template(template_id)
        assert loaded_template is not None
        assert loaded_template.person_info.name == sample_case_data.person_info.name
        
        # テンプレート一覧を取得
        templates = mock_database_manager.get_all_templates_summary()
        assert len(templates) >= 1
        
        # 名前でテンプレートを検索
        found_template = mock_database_manager.get_template_by_name(template_name)
        assert found_template is not None
        
        # テンプレートを削除
        success = mock_database_manager.delete_template(template_id)
        assert success
    
    def test_backup_operations(self, mock_database_manager, tmp_path):
        """バックアップ操作のテスト"""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        
        success = mock_database_manager.create_backup(str(backup_dir))
        assert success
        
        # バックアップファイルが作成されることを確認
        backup_files = list(backup_dir.glob("*.db"))
        assert len(backup_files) >= 1
    
    def test_database_optimization(self, mock_database_manager):
        """データベース最適化のテスト"""
        success = mock_database_manager.optimize_database()
        assert success
    
    def test_database_info(self, mock_database_manager):
        """データベース情報取得のテスト"""
        info = mock_database_manager.get_database_info()
        assert 'file_size' in info
        assert 'sqlite_version' in info
        assert 'tables' in info
        assert 'table_counts' in info
    
    def test_health_check(self, mock_database_manager):
        """ヘルスチェックのテスト"""
        health = mock_database_manager.health_check()
        assert 'status' in health
        assert 'issues' in health
        assert 'recommendations' in health
        assert health['status'] in ['healthy', 'warning', 'error']
    
    def test_connection_error_handling(self):
        """接続エラーハンドリングのテスト"""
        # 無効なパスでデータベースマネージャーを作成
        with pytest.raises(Exception):
            db_manager = DatabaseManager("/invalid/path/database.db")
            with db_manager.get_connection() as conn:
                pass
    
    def test_json_serialization_error_handling(self, mock_database_manager):
        """JSON変換エラーハンドリングのテスト"""
        # 不正なデータを含むケースデータ
        invalid_case = CaseData()
        invalid_case.case_number = "INVALID-JSON-TEST"
        
        # カスタムフィールドに変換不可能なオブジェクトを設定
        class UnserializableObject:
            def __str__(self):
                raise Exception("Serialization error")
        
        invalid_case.custom_fields = {"bad_object": UnserializableObject()}
        
        # エラーハンドリングが機能することを確認
        success = mock_database_manager.save_case(invalid_case)
        # safe_json_dumpsが空辞書で代替するため成功する
        assert success
    
    @pytest.mark.slow
    def test_batch_operations(self, mock_database_manager):
        """バッチ操作のテスト"""
        # 複数のケースデータを作成
        cases = []
        for i in range(10):
            case = CaseData()
            case.case_number = f"BATCH-TEST-{i:03d}"
            case.person_info.name = f"テスト{i}号"
            cases.append(case)
        
        # バッチ保存
        results = mock_database_manager.batch_save_cases(cases)
        assert results['success_count'] == 10
        assert results['failed_count'] == 0
        
        # 保存されたことを確認
        for case in cases:
            loaded = mock_database_manager.load_case(case.case_number)
            assert loaded is not None
