#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シンプルな統合テスト
基本機能の動作確認
"""

import unittest
import tempfile
import os
import sys
from datetime import date
from decimal import Decimal
import time  # 追加

# パスの設定
sys.path.insert(0, os.path.abspath('.'))

# 必要なモジュールのインポート
from config.app_config import AppConfig, ConfigManager
from models.case_data import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
from calculation.compensation_engine import CompensationEngine

class SimpleIntegrationTest(unittest.TestCase):
    """シンプルな統合テスト"""
    
    def setUp(self):
        """テスト初期化"""
        self.config = AppConfig()
        self.engine = CompensationEngine()
        
        # テストケースデータ作成
        self.test_case = CaseData(
            case_number="SIMPLE-TEST-001",
            person_info=PersonInfo(
                name="テスト太郎",
                age=35,
                gender="男性",
                occupation="会社員",
                annual_income=Decimal("5000000")
            ),
            accident_info=AccidentInfo(
                accident_date=date(2024, 1, 15),
                location="東京都",
                accident_type="追突事故"
            ),
            medical_info=MedicalInfo(
                hospital_months=0,
                outpatient_months=6,
                actual_outpatient_days=90,
                is_whiplash=True,
                disability_grade=14,
                medical_expenses=Decimal("150000"),
                transportation_costs=Decimal("25000")
            ),
            income_info=IncomeInfo(
                lost_work_days=30,
                daily_income=Decimal("16438"),
                loss_period_years=10,
                basic_annual_income=Decimal("5000000")
            )
        )
    
    def test_configuration_basic(self):
        """基本設定テスト"""
        self.assertIsNotNone(self.config)
        self.assertIsInstance(self.config.version, str)
        self.assertIsInstance(self.config.app_name, str)
    
    def test_calculation_engine_basic(self):
        """計算エンジン基本テスト"""
        self.assertIsNotNone(self.engine)
        
        # 入通院慰謝料計算
        result = self.engine.calculate_hospitalization_compensation(self.test_case.medical_info)
        self.assertIsNotNone(result)
        self.assertGreater(result.amount, 0)
        self.assertEqual(result.item_name, "入通院慰謝料")
        
        # 後遺障害慰謝料計算
        result2 = self.engine.calculate_disability_compensation(self.test_case.medical_info)
        self.assertIsNotNone(result2)
        self.assertGreater(result2.amount, 0)
        self.assertEqual(result2.item_name, "後遺障害慰謝料")
        
        # 休業損害計算
        result3 = self.engine.calculate_lost_income(self.test_case.income_info)
        self.assertIsNotNone(result3)
        self.assertGreater(result3.amount, 0)
        self.assertEqual(result3.item_name, "休業損害")
    
    def test_case_data_serialization(self):
        """ケースデータのシリアライゼーションテスト"""
        # 辞書変換
        case_dict = self.test_case.to_dict()
        self.assertIsInstance(case_dict, dict)
        self.assertEqual(case_dict['case_number'], "SIMPLE-TEST-001")
        
        # 辞書から復元
        restored_case = CaseData.from_dict(case_dict)
        self.assertEqual(restored_case.case_number, self.test_case.case_number)
        self.assertEqual(restored_case.person_info.name, self.test_case.person_info.name)
    
    def test_end_to_end_calculation(self):
        """エンドツーエンド計算テスト"""
        # すべての損害項目を計算
        results = []
        
        # 入通院慰謝料
        result1 = self.engine.calculate_hospitalization_compensation(self.test_case.medical_info)
        results.append(result1)
        
        # 後遺障害慰謝料
        result2 = self.engine.calculate_disability_compensation(self.test_case.medical_info)
        results.append(result2)
        
        # 休業損害
        result3 = self.engine.calculate_lost_income(self.test_case.income_info)
        results.append(result3)
        
        # 逸失利益
        result4 = self.engine.calculate_future_income_loss(
            self.test_case.person_info, 
            self.test_case.medical_info, 
            self.test_case.income_info
        )
        results.append(result4)
        
        # 治療費
        result5 = self.engine.calculate_medical_expenses(self.test_case.medical_info)
        results.append(result5)
        
        # すべての結果が取得できていることを確認
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.item_name)
            self.assertIsNotNone(result.amount)
            self.assertIsNotNone(result.calculation_details)
        
        # 合計金額計算
        total_amount = sum(result.amount for result in results)
        self.assertGreater(total_amount, 0)
        
        print(f"\n=== 計算結果サマリー ===")
        for result in results:
            print(f"{result.item_name}: {result.amount:,}円")
        print(f"合計: {total_amount:,}円")
        print("===================")
    
    def test_performance_monitor_basic(self):
        """パフォーマンス監視基本テスト"""
        from utils.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 基本メソッドが動作するかテスト
        monitor.start_timing('test_operation')
        time.sleep(0.1)  # 短時間待機
        elapsed = monitor.end_timing('test_operation')
        
        self.assertGreater(elapsed, 0.05)  # 最低0.05秒は経過しているはず
        
        # メモリ使用量取得テスト
        memory_usage = monitor.get_memory_usage()
        self.assertIsInstance(memory_usage, int)
        self.assertGreater(memory_usage, 0)
        
        print(f"基本パフォーマンス監視テスト完了: {elapsed:.3f}秒, メモリ:{memory_usage:,}バイト")

    def test_security_config_access(self):
        """セキュリティ設定アクセステスト"""
        config = AppConfig()
        
        # 直接属性アクセスが動作するかテスト
        self.assertIsInstance(config.security.encryption_enabled, bool)
        self.assertIsInstance(config.security.data_retention_days, int)
        self.assertIsInstance(config.security.audit_logging_enabled, bool)
        
        print("セキュリティ設定アクセステスト完了")

if __name__ == '__main__':
    unittest.main(verbosity=2)
