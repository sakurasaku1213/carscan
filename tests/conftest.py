#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弁護士基準損害賠償計算システム - 包括テストスイート
"""

import pytest
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

def pytest_collection_modifyitems(config, items):
    """テストアイテムの修正"""
    for item in items:
        # 統合テストディレクトリのテストに統合テストマーカーを追加
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # ユニットテストディレクトリのテストにユニットテストマーカーを追加
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

@pytest.fixture(scope="session")
def test_data_dir():
    """テストデータディレクトリ"""
    return Path(__file__).parent / "test_data"

@pytest.fixture(scope="session")
def temp_db_path(tmp_path_factory):
    """一時的なテストデータベースパス"""
    return tmp_path_factory.mktemp("test_db") / "test_compensation.db"

@pytest.fixture
def sample_case_data():
    """サンプル案件データ"""
    from models.case_data import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
    from datetime import datetime, date
    
    case_data = CaseData()
    case_data.case_number = "TEST-2024-001"
    case_data.created_date = datetime.now()
    case_data.status = "作成中"
    
    # 個人情報
    case_data.person_info.name = "テスト太郎"
    case_data.person_info.age = 35
    case_data.person_info.gender = "男性"
    case_data.person_info.address = "東京都渋谷区"
    case_data.person_info.phone = "03-1234-5678"
    
    # 事故情報
    case_data.accident_info.accident_date = date(2024, 1, 15)
    case_data.accident_info.accident_type = "交通事故"
    case_data.accident_info.location = "東京都新宿区"
    case_data.accident_info.weather = "晴れ"
    case_data.accident_info.description = "信号待ち中に後方から追突された"
    case_data.accident_info.fault_ratio = 0  # 被害者過失なし
    
    # 医療情報
    case_data.medical_info.injury_description = "頸椎捻挫"
    case_data.medical_info.treatment_period_start = date(2024, 1, 15)
    case_data.medical_info.treatment_period_end = date(2024, 3, 15)
    case_data.medical_info.treatment_days = 60
    case_data.medical_info.hospitalization_days = 0
    case_data.medical_info.hospital_name = "テスト病院"
    case_data.medical_info.doctor_name = "テスト医師"
    case_data.medical_info.disability_grade = None
    
    # 収入情報
    case_data.income_info.basic_annual_income = 5000000  # 500万円
    case_data.income_info.employment_type = "給与所得者"
    case_data.income_info.company_name = "テスト株式会社"
    case_data.income_info.position = "営業部主任"
    case_data.income_info.work_days_per_year = 250
    
    return case_data

@pytest.fixture
def mock_database_manager(temp_db_path):
    """モックデータベースマネージャー"""
    from database.db_manager import DatabaseManager
    return DatabaseManager(str(temp_db_path))

@pytest.fixture
def mock_config():
    """モック設定"""
    from config.app_config import AppConfig
    config = AppConfig()
    config.calculation.default_standard = "弁護士基準"
    config.calculation.precision_digits = 0
    config.calculation.rounding_method = "round"
    return config
