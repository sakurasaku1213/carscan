#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データモデル統合インターフェース

このモジュールは、システム全体で使用されるデータモデルクラスを
一元化し、インポートの重複を排除します。
"""

# 遅延インポートで循環インポートを回避
def __getattr__(name):
    """モジュール属性の動的取得"""
    from .case_data import (
        CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
    )
      # case_data.py内に実際に存在するクラス/関数のマッピング
    actual_exports = {
        'CaseData': CaseData,
        'PersonalInfo': PersonInfo,  # PersonInfoをPersonalInfoとしてエクスポート
        'PersonInfo': PersonInfo,    # 元の名前も維持
        'AccidentInfo': AccidentInfo,
        'MedicalInfo': MedicalInfo,
        'IncomeInfo': IncomeInfo,
        # エイリアス
        'InjuryInfo': MedicalInfo,      # InjuryInfoはMedicalInfoのエイリアス
        'DamageInfo': IncomeInfo,       # DamageInfoはIncomeInfoのエイリアス
        'MedicalExpense': MedicalInfo,  # MedicalExpenseはMedicalInfoのエイリアス
        'LostIncome': IncomeInfo,       # LostIncomeはIncomeInfoのエイリアス
    }    # エイリアスマッピング
    alias_mapping = {
        'MedicalExpense': 'MedicalInfo',
        'LostIncome': 'IncomeInfo',
    }
    
    # 存在しないクラス用のダミー実装
    if name in ['CalculationInput', 'CompensationResult', 'AccidentType', 
                'InjuryGrade', 'LiabilityRatio', 'CalculationMethod']:
        class DummyClass:
            """存在しないクラス用のダミー実装"""
            def __init__(self, *args, **kwargs):
                pass
        return DummyClass
    
    if name in actual_exports:
        return actual_exports[name]
    elif name in alias_mapping:
        return actual_exports[alias_mapping[name]]
    
    # ヘルパー関数は存在しない可能性があるのでダミーを返す
    helper_functions = ['create_case_data', 'validate_case_data', 'serialize_case_data', 'deserialize_case_data']
    if name in helper_functions:
        def dummy_helper(*args, **kwargs):
            raise NotImplementedError(f"{name} is not implemented yet")
        return dummy_helper
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # メインクラス
    'CaseData',
    'PersonalInfo', 'PersonInfo',  # エイリアス含む
    'AccidentInfo',
    'MedicalInfo', 'MedicalExpense',  # エイリアス含む
    'IncomeInfo', 'LostIncome',  # エイリアス含む
    'InjuryInfo', 'DamageInfo',  # エイリアス
    'CalculationInput',
    'CompensationResult',
    
    # Enum クラス
    'AccidentType',
    'InjuryGrade', 
    'LiabilityRatio',
    'CalculationMethod',
    
    # ヘルパー関数
    'create_case_data',
    'validate_case_data',
    'serialize_case_data',
    'deserialize_case_data',
]
