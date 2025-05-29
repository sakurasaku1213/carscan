#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
計算エンジンのユニットテスト
"""

import pytest
from decimal import Decimal
from datetime import date
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from calculation.compensation_engine import CompensationEngine
from models.case_data import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo

class TestCompensationEngine:
    """CompensationEngineクラスのテスト"""
    
    def test_init(self):
        """初期化のテスト"""
        engine = CompensationEngine()
        assert engine is not None
        assert hasattr(engine, 'logger')
    
    def test_calculate_daily_income_salary_worker(self):
        """給与所得者の日額収入計算テスト"""
        engine = CompensationEngine()
        
        # テストケース1: 年収500万円、年間勤務日数250日
        daily_income = engine._calculate_daily_income(5000000, "給与所得者", 250)
        expected = 5000000 / 250  # 20,000円
        assert daily_income == expected
        
        # テストケース2: 年収0円の場合
        daily_income = engine._calculate_daily_income(0, "給与所得者", 250)
        assert daily_income == 0
    
    def test_calculate_daily_income_self_employed(self):
        """自営業者の日額収入計算テスト"""
        engine = CompensationEngine()
        
        # 自営業者の場合は年間365日で計算
        daily_income = engine._calculate_daily_income(3650000, "自営業", 300)
        expected = 3650000 / 365  # 10,000円
        assert daily_income == expected
    
    def test_calculate_daily_income_invalid_params(self):
        """無効なパラメータでの日額収入計算テスト"""
        engine = CompensationEngine()
        
        # 負の年収
        with pytest.raises(ValueError):
            engine._calculate_daily_income(-1000000, "給与所得者", 250)
        
        # ゼロまたは負の勤務日数
        with pytest.raises(ValueError):
            engine._calculate_daily_income(5000000, "給与所得者", 0)
        
        with pytest.raises(ValueError):
            engine._calculate_daily_income(5000000, "給与所得者", -10)
    
    def test_calculate_pain_and_suffering_minor_injury(self):
        """軽傷の慰謝料計算テスト"""
        engine = CompensationEngine()
        
        # 軽傷（14級程度）: 治療期間2ヶ月、通院日数30日
        compensation = engine._calculate_pain_and_suffering_compensation(
            treatment_days=30,
            hospitalization_days=0,
            treatment_period_months=2,
            disability_grade=14
        )
        
        # 軽傷の場合は基本的に治療期間と通院日数に基づく
        assert compensation > 0
        assert isinstance(compensation, (int, float))
    
    def test_calculate_pain_and_suffering_severe_injury(self):
        """重傷の慰謝料計算テスト"""
        engine = CompensationEngine()
        
        # 重傷（3級程度）: 治療期間12ヶ月、入院30日、通院100日
        compensation = engine._calculate_pain_and_suffering_compensation(
            treatment_days=130,
            hospitalization_days=30,
            treatment_period_months=12,
            disability_grade=3
        )
        
        # 重傷の場合は高額になる
        assert compensation > 1000000  # 100万円以上
        assert isinstance(compensation, (int, float))
    
    def test_calculate_pain_and_suffering_death_case(self):
        """死亡事故の慰謝料計算テスト"""
        engine = CompensationEngine()
        
        # 死亡事故の場合
        compensation = engine._calculate_pain_and_suffering_compensation(
            treatment_days=0,
            hospitalization_days=0,
            treatment_period_months=0,
            disability_grade=None,
            is_death=True,
            family_structure="一家の支柱"
        )
        
        # 死亡事故は高額慰謝料
        assert compensation >= 2800000  # 2800万円以上（一家の支柱）
    
    def test_calculate_lost_income_temporary(self):
        """一時的な休業損害計算テスト"""
        engine = CompensationEngine()
        
        daily_income = 20000  # 日額2万円
        days_off = 60  # 60日休業
        
        lost_income = engine._calculate_lost_income(
            daily_income=daily_income,
            rest_days=days_off,
            disability_grade=None
        )
        
        expected = daily_income * days_off  # 120万円
        assert lost_income == expected
    
    def test_calculate_lost_income_permanent_disability(self):
        """後遺障害による逸失利益計算テスト"""
        engine = CompensationEngine()
        
        annual_income = 5000000  # 年収500万円
        age = 35  # 35歳
        disability_grade = 7  # 7級
        
        lost_income = engine._calculate_lost_income(
            annual_income=annual_income,
            age=age,
            disability_grade=disability_grade
        )
        
        # 後遺障害の逸失利益は高額になる
        assert lost_income > annual_income  # 年収を超える
        assert isinstance(lost_income, (int, float))
    
    def test_calculate_medical_expenses(self):
        """治療費計算テスト"""
        engine = CompensationEngine()
        
        expenses = {
            "診療費": 500000,
            "薬代": 50000,
            "交通費": 30000,
            "その他": 20000
        }
        
        total = engine._calculate_medical_expenses(expenses)
        expected = sum(expenses.values())  # 60万円
        assert total == expected
    
    def test_calculate_comprehensive_compensation(self, sample_case_data):
        """総合的な損害賠償計算テスト"""
        engine = CompensationEngine()
        
        result = engine.calculate_compensation(sample_case_data)
        
        # 結果が適切な形式で返されることを確認
        assert isinstance(result, dict)
        assert 'total_compensation' in result
        assert 'pain_and_suffering' in result
        assert 'lost_income' in result
        assert 'medical_expenses' in result
        assert 'other_expenses' in result
        assert 'breakdown' in result
        
        # 金額が正の値であることを確認
        assert result['total_compensation'] > 0
        assert result['pain_and_suffering'] >= 0
        assert result['lost_income'] >= 0
        assert result['medical_expenses'] >= 0
    
    def test_calculate_with_fault_ratio(self, sample_case_data):
        """過失相殺ありの計算テスト"""
        engine = CompensationEngine()
        
        # 過失割合30%を設定
        sample_case_data.accident_info.fault_ratio = 30
        
        result = engine.calculate_compensation(sample_case_data)
        
        # 過失相殺後の金額が計算されることを確認
        assert 'fault_ratio' in result
        assert result['fault_ratio'] == 30
        assert 'compensation_after_fault' in result
        assert result['compensation_after_fault'] < result['total_compensation']
    
    def test_calculate_with_invalid_data(self):
        """無効なデータでの計算テスト"""
        engine = CompensationEngine()
        
        # Noneデータ
        result = engine.calculate_compensation(None)
        assert result is None or result == {}
        
        # 不完全なデータ
        incomplete_case = CaseData()
        incomplete_case.case_number = "INCOMPLETE"
        
        result = engine.calculate_compensation(incomplete_case)
        # エラーハンドリングが機能することを確認
        assert isinstance(result, dict)
    
    def test_insurance_standards_calculation(self, sample_case_data):
        """各基準（自賠責・任意保険・弁護士）での計算テスト"""
        engine = CompensationEngine()
        
        standards = ["自賠責基準", "任意保険基準", "弁護士基準"]
        results = {}
        
        for standard in standards:
            result = engine.calculate_compensation(sample_case_data, standard)
            results[standard] = result['total_compensation']
        
        # 弁護士基準が最も高額であることを確認
        assert results["弁護士基準"] >= results["任意保険基準"]
        assert results["任意保険基準"] >= results["自賠責基準"]
    
    def test_rounding_behavior(self):
        """端数処理のテスト"""
        engine = CompensationEngine()
        
        # 端数のある金額
        amount = 1234567.89
        
        # 四捨五入
        rounded = engine._round_amount(amount, method="round")
        assert rounded == 1234568
        
        # 切り捨て
        floored = engine._round_amount(amount, method="floor")
        assert floored == 1234567
        
        # 切り上げ
        ceiled = engine._round_amount(amount, method="ceil")
        assert ceiled == 1234568
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        engine = CompensationEngine()
        
        # 高齢者のケース（67歳以上）
        elderly_case = CaseData()
        elderly_case.person_info.age = 70
        elderly_case.income_info.basic_annual_income = 3000000
        
        # 最低賃金レベルのケース
        low_income_case = CaseData()
        low_income_case.income_info.basic_annual_income = 1500000  # 150万円
        
        # 高収入のケース
        high_income_case = CaseData()
        high_income_case.income_info.basic_annual_income = 20000000  # 2000万円
        
        # それぞれが適切に処理されることを確認
        for case in [elderly_case, low_income_case, high_income_case]:
            result = engine.calculate_compensation(case)
            assert isinstance(result, dict)
            assert result.get('total_compensation', 0) >= 0
    
    @pytest.mark.parametrize("disability_grade,expected_ratio", [
        (1, 100),  # 1級：100%
        (7, 56),   # 7級：56%
        (14, 5),   # 14級：5%
    ])
    def test_disability_labor_capacity_ratio(self, disability_grade, expected_ratio):
        """後遺障害の労働能力喪失率テスト"""
        engine = CompensationEngine()
        
        ratio = engine._get_labor_capacity_loss_ratio(disability_grade)
        assert ratio == expected_ratio
    
    def test_calculation_consistency(self, sample_case_data):
        """計算結果の一貫性テスト"""
        engine = CompensationEngine()
        
        # 同じデータで複数回計算
        result1 = engine.calculate_compensation(sample_case_data)
        result2 = engine.calculate_compensation(sample_case_data)
        
        # 結果が一貫していることを確認
        assert result1['total_compensation'] == result2['total_compensation']
        assert result1['pain_and_suffering'] == result2['pain_and_suffering']
        assert result1['lost_income'] == result2['lost_income']
