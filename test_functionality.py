#!/usr/bin/env python
"""弁護士報酬計算システムの基本機能テスト"""

import sys
import os
import json
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_operations():
    """データベース操作のテスト"""
    print("🧪 データベース操作テストを開始...")
    try:
        from database.db_manager import DatabaseManager
        from config import get_config
          # 設定をロード
        config = get_config()
        
        # データベースマネージャーを初期化
        db_path = config.database.db_path
        db_manager = DatabaseManager(db_path)
        
        print("✅ データベースマネージャーの初期化に成功")
        
        # テストケースデータをCaseDataオブジェクトとして作成
        from models import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
        
        test_case = CaseData(
            case_number='TEST-001',
            person_info=PersonInfo(
                name='田中太郎',
                age=35,
                gender='男性',
                occupation='会社員'
            ),
            accident_info=AccidentInfo(
                accident_type='交通事故',
                location='東京都渋谷区'
            ),
            medical_info=MedicalInfo(
                hospital_months=6,
                disability_grade=12
            ),            income_info=IncomeInfo(
                basic_annual_income=5000000,
                lost_work_days=60
            ),
            notes='テストケースです'
        )
          # ケースを保存
        print("📝 テストケースを保存中...")
        success = db_manager.save_case(test_case)
        if success:
            print("✅ ケース保存成功")
            # 作成されたケースを番号で検索してIDを取得
            search_results = db_manager.search_cases(case_number_pattern='TEST-001')
            if search_results:
                case_id = search_results[0]['id']  # 最初の結果のIDを取得
            else:
                print("❌ 作成されたケースのIDが見つかりません")
                return False
        else:
            print("❌ ケース保存に失敗")
            return False        # ケースを取得
        print("📖 ケースを取得中...")
        retrieved_case = db_manager.load_case_by_id(case_id)
        if retrieved_case:
            print(f"✅ ケース取得成功: {retrieved_case.get('case_number', 'N/A')}")
            print(f"   作成日: {retrieved_case.get('created_date', 'N/A')}")
        else:
            print("❌ ケース取得に失敗")
            return False
          # 全ケース一覧を取得
        print("📋 全ケース一覧を取得中...")
        all_cases = db_manager.search_cases()
        print(f"✅ 全ケース取得成功: {len(all_cases)}件")        # ケースを更新
        print("✏️ ケースを更新中...")
        # ケースを読み込み
        case_to_update = db_manager.load_case('TEST-001')
        if case_to_update:
            case_to_update.notes = 'テストケース - 更新済み'
            success = db_manager.save_case(case_to_update)
            if success:
                print("✅ ケース更新成功")
            else:
                print("❌ ケース更新に失敗")
                return False
        else:
            print("❌ 更新対象のケースが見つかりません")
            return False
        
        print("\n🎉 全てのデータベース操作テストが成功しました！")
        return True
        
    except Exception as e:
        print(f"❌ データベース操作テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calculation_engine():
    """計算エンジンのテスト"""
    print("\n🧮 計算エンジンテストを開始...")
    
    try:
        from calculation.compensation_engine import CompensationEngine
        calculator = CompensationEngine()
        print("✅ 計算エンジンの初期化に成功")
          # テスト用のCaseDataオブジェクトを作成
        from models import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
        
        test_case_data = CaseData(
            case_number="TEST-001",            person_info=PersonInfo(
                name="テスト太郎",
                age=35,
                gender="男性",
                occupation="会社員"
            ),accident_info=AccidentInfo(
                accident_type="交通事故",
                accident_date=None,
                location="テスト場所"
            ),            medical_info=MedicalInfo(
                hospital_months=1,
                outpatient_months=2,
                disability_grade=14
            ),            income_info=IncomeInfo(
                basic_annual_income=5000000,
                lost_work_days=30
            )
        )
        
        print("⚖️ 弁護士基準での計算を実行中...")
        results = calculator.calculate_all(test_case_data)
        
        if results:
            print("✅ 弁護士基準計算成功:")
            print(f"   慰謝料: ¥{results.get('solatium', 0):,}")
            print(f"   休業損害: ¥{results.get('income_loss', 0):,}")
            print(f"   合計: ¥{results.get('total', 0):,}")
        else:
            print("❌ 弁護士基準計算に失敗")
            return False
        
        print("\n🎉 計算エンジンテストが成功しました！")
        return True
        
    except Exception as e:
        print(f"❌ 計算エンジンテスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト関数"""
    print("🚀 弁護士報酬計算システム 機能テスト開始")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # データベース操作テスト
    if test_database_operations():
        success_count += 1
    
    # 計算エンジンテスト
    if test_calculation_engine():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 テスト結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("🎉 全てのテストが成功しました！システムは正常に動作しています。")
    else:
        print("⚠️ 一部のテストが失敗しました。ログを確認してください。")
    
    return success_count == total_tests

if __name__ == "__main__":
    main()
