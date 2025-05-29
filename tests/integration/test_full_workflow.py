#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリケーション全体の統合テスト
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, date
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database.db_manager import DatabaseManager
from calculation.compensation_engine import CompensationEngine
from config.app_config import ConfigManager, AppConfig
from models.case_data import CaseData

class TestIntegration:
    """統合テストクラス"""
    
    def test_end_to_end_case_processing(self, sample_case_data, tmp_path):
        """エンドツーエンドの案件処理テスト"""
        # 一時的なデータベースファイル
        db_path = tmp_path / "test_integration.db"
        
        # データベースマネージャーを初期化
        db_manager = DatabaseManager(str(db_path))
        
        # 計算エンジンを初期化
        calc_engine = CompensationEngine()
        
        # 1. 案件データを保存
        save_success = db_manager.save_case(sample_case_data)
        assert save_success, "案件データの保存に失敗"
        
        # 2. 保存した案件データを読み込み
        loaded_case = db_manager.load_case(sample_case_data.case_number)
        assert loaded_case is not None, "案件データの読み込みに失敗"
        assert loaded_case.case_number == sample_case_data.case_number
        
        # 3. 読み込んだデータで損害賠償を計算
        calc_result = calc_engine.calculate_compensation(loaded_case)
        assert calc_result is not None, "損害賠償計算に失敗"
        assert 'total_compensation' in calc_result
        assert calc_result['total_compensation'] > 0
        
        # 4. 計算結果を案件データに保存
        loaded_case.calculation_results = calc_result
        update_success = db_manager.save_case(loaded_case)
        assert update_success, "計算結果の保存に失敗"
        
        # 5. 計算結果を含めて再度読み込み
        final_case = db_manager.load_case(sample_case_data.case_number)
        assert final_case is not None
        assert 'total_compensation' in final_case.calculation_results
        assert final_case.calculation_results['total_compensation'] > 0
    
    def test_config_and_calculation_integration(self, sample_case_data, tmp_path):
        """設定管理と計算の統合テスト"""
        # 一時的な設定ファイル
        config_path = tmp_path / "test_config.json"
        
        # 設定マネージャーを初期化
        config_manager = ConfigManager(str(config_path))
        config = config_manager.get_config()
        
        # 計算設定を変更
        config.calculation.default_standard = "弁護士基準"
        config.calculation.precision_digits = 0
        config.calculation.rounding_method = "round"
        config_manager.save_config()
        
        # 計算エンジンで設定を使用
        calc_engine = CompensationEngine()
        
        # 設定に基づいて計算
        result = calc_engine.calculate_compensation(
            sample_case_data, 
            config.calculation.default_standard
        )
        
        assert result is not None
        assert isinstance(result['total_compensation'], int)  # 精度0で整数
    
    def test_template_workflow(self, sample_case_data, tmp_path):
        """テンプレート機能のワークフローテスト"""
        db_path = tmp_path / "test_template.db"
        db_manager = DatabaseManager(str(db_path))
        
        template_name = "交通事故標準テンプレート"
        
        # 1. 案件データをテンプレートとして保存
        template_id = db_manager.save_template(template_name, sample_case_data)
        assert template_id is not None
        
        # 2. テンプレート一覧を取得
        templates = db_manager.get_all_templates_summary()
        assert len(templates) >= 1
        assert any(t[1] == template_name for t in templates)
        
        # 3. テンプレートを読み込んで新しい案件を作成
        template_case = db_manager.load_template(template_id)
        assert template_case is not None
        
        # 新しい案件番号を設定
        template_case.case_number = "TEMPLATE-BASED-001"
        template_case.person_info.name = "テンプレート太郎"
        
        # 4. テンプレートベースの案件を保存
        save_success = db_manager.save_case(template_case)
        assert save_success
        
        # 5. 保存した案件を確認
        saved_case = db_manager.load_case("TEMPLATE-BASED-001")
        assert saved_case is not None
        assert saved_case.person_info.name == "テンプレート太郎"
        
        # テンプレートの他の情報は保持されていることを確認
        assert saved_case.accident_info.accident_type == sample_case_data.accident_info.accident_type
    
    def test_search_and_calculation_workflow(self, tmp_path):
        """検索と計算の統合ワークフロー"""
        db_path = tmp_path / "test_search.db"
        db_manager = DatabaseManager(str(db_path))
        calc_engine = CompensationEngine()
        
        # 複数の案件データを作成
        cases = []
        for i in range(5):
            case = CaseData()
            case.case_number = f"SEARCH-TEST-{i:03d}"
            case.person_info.name = f"検索テスト{i}号"
            case.person_info.age = 30 + i
            case.accident_info.accident_type = "交通事故"
            case.income_info.basic_annual_income = 3000000 + (i * 500000)
            cases.append(case)
        
        # 案件を保存
        for case in cases:
            db_manager.save_case(case)
        
        # 案件を検索
        search_results = db_manager.search_cases(
            case_number_pattern="SEARCH-TEST"
        )
        assert len(search_results) == 5
        
        # 検索結果の各案件で計算を実行
        for result in search_results:
            case_number = result['case_number']
            case_data = db_manager.load_case(case_number)
            assert case_data is not None
            
            # 損害賠償計算
            compensation = calc_engine.calculate_compensation(case_data)
            assert compensation is not None
            assert compensation['total_compensation'] > 0
            
            # 計算結果を保存
            case_data.calculation_results = compensation
            db_manager.save_case(case_data)
        
        # 統計情報を確認
        stats = db_manager.get_statistics()
        assert stats['total_cases'] == 5
        assert '作成中' in stats['status_counts']
    
    def test_backup_and_restore_workflow(self, sample_case_data, tmp_path):
        """バックアップと復元のワークフロー"""
        original_db_path = tmp_path / "original.db"
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        
        # 元のデータベースに案件を保存
        original_db = DatabaseManager(str(original_db_path))
        original_db.save_case(sample_case_data)
        
        # バックアップを作成
        backup_success = original_db.create_backup(str(backup_dir))
        assert backup_success
        
        # バックアップファイルが作成されたことを確認
        backup_files = list(backup_dir.glob("*.db"))
        assert len(backup_files) >= 1
        
        # バックアップファイルから復元
        backup_file = backup_files[0]
        restored_db = DatabaseManager(str(backup_file))
        
        # 復元されたデータを確認
        restored_case = restored_db.load_case(sample_case_data.case_number)
        assert restored_case is not None
        assert restored_case.case_number == sample_case_data.case_number
        assert restored_case.person_info.name == sample_case_data.person_info.name
    
    def test_error_handling_integration(self, tmp_path):
        """エラーハンドリングの統合テスト"""
        db_path = tmp_path / "error_test.db"
        db_manager = DatabaseManager(str(db_path))
        calc_engine = CompensationEngine()
        
        # 不正なデータでのテスト
        invalid_case = CaseData()
        invalid_case.case_number = "ERROR-TEST"
        # 必要なデータを意図的に設定しない
        
        # データベース操作は成功する（デフォルト値で処理）
        save_result = db_manager.save_case(invalid_case)
        assert save_result  # 最低限のデータで保存可能
        
        # 計算は適切にエラーハンドリングされる
        calc_result = calc_engine.calculate_compensation(invalid_case)
        assert isinstance(calc_result, dict)  # エラーでも辞書を返す
    
    def test_multi_standard_calculation_comparison(self, sample_case_data, tmp_path):
        """複数基準での計算比較テスト"""
        db_path = tmp_path / "multi_standard.db"
        db_manager = DatabaseManager(str(db_path))
        calc_engine = CompensationEngine()
        
        # 案件を保存
        db_manager.save_case(sample_case_data)
        
        # 3つの基準で計算
        standards = ["自賠責基準", "任意保険基準", "弁護士基準"]
        results = {}
        
        for standard in standards:
            result = calc_engine.calculate_compensation(sample_case_data, standard)
            results[standard] = result
            
            # 計算結果を案件データに保存（基準別）
            case_copy = db_manager.load_case(sample_case_data.case_number)
            case_copy.calculation_results[f'{standard}_result'] = result
            db_manager.save_case(case_copy)
        
        # 基準の順序確認（弁護士基準が最高額）
        jibaiseki = results["自賠責基準"]['total_compensation']
        ninihoken = results["任意保険基準"]['total_compensation']
        bengoshi = results["弁護士基準"]['total_compensation']
        
        assert bengoshi >= ninihoken >= jibaiseki
        
        # 保存された結果を確認
        final_case = db_manager.load_case(sample_case_data.case_number)
        assert '弁護士基準_result' in final_case.calculation_results
        assert '自賠責基準_result' in final_case.calculation_results
    
    def test_performance_benchmark(self, tmp_path):
        """パフォーマンスベンチマークテスト"""
        import time
        
        db_path = tmp_path / "performance.db"
        db_manager = DatabaseManager(str(db_path))
        calc_engine = CompensationEngine()
        
        # 100件の案件データを作成・保存・計算
        start_time = time.time()
        
        cases_count = 100
        for i in range(cases_count):
            case = CaseData()
            case.case_number = f"PERF-{i:04d}"
            case.person_info.name = f"パフォーマンステスト{i}"
            case.person_info.age = 20 + (i % 50)
            case.income_info.basic_annual_income = 3000000 + (i * 10000)
            case.accident_info.accident_type = "交通事故"
            case.medical_info.treatment_days = 30 + (i % 100)
            
            # 保存
            db_manager.save_case(case)
            
            # 計算
            result = calc_engine.calculate_compensation(case)
            case.calculation_results = result
            db_manager.save_case(case)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # パフォーマンス要件：100件を60秒以内で処理
        assert total_time < 60, f"処理時間が長すぎます: {total_time:.2f}秒"
        
        # 平均処理時間をログ出力
        avg_time = total_time / cases_count
        print(f"平均処理時間: {avg_time:.3f}秒/件 (総処理時間: {total_time:.2f}秒)")
        
        # データベース統計確認
        stats = db_manager.get_statistics()
        assert stats['total_cases'] == cases_count
