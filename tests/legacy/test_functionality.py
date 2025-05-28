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
        from config.app_config import get_config
        
        # 設定をロード
        config = get_config()
        
        # データベースマネージャーを初期化
        db_manager = DatabaseManager(config)
        
        print("✅ データベースマネージャーの初期化に成功")
        
        # テストケースデータ
        test_case = {
            'case_number': 'TEST-001',
            'case_name': '交通事故損害賠償請求事件',
            'client_name': '田中太郎',
            'person_info': json.dumps({
                'name': '田中太郎',
                'age': 35,
                'gender': '男性',
                'occupation': '会社員'
            }),
            'accident_info': json.dumps({
                'date': '2025-01-15',
                'type': '交通事故',
                'location': '東京都渋谷区',
                'severity': '重傷'
            }),
            'medical_info': json.dumps({
                'hospital': '○○病院',
                'treatment_period': '6ヶ月',
                'disability_grade': '12級'
            }),
            'income_info': json.dumps({
                'annual_income': 5000000,
                'employment_type': '正社員'
            }),
            'notes': 'テストケースです'
        }
        
        # ケースを保存
        print("📝 テストケースを保存中...")
        case_id = db_manager.save_case(test_case)
        print(f"✅ ケース保存成功 (ID: {case_id})")
        
        # ケースを取得
        print("📖 ケースを取得中...")
        retrieved_case = db_manager.get_case(case_id)
        if retrieved_case:
            print(f"✅ ケース取得成功: {retrieved_case['case_name']}")
            print(f"   クライアント: {retrieved_case['client_name']}")
            print(f"   作成日: {retrieved_case['created_date']}")
        else:
            print("❌ ケース取得に失敗")
            return False
        
        # 全ケース一覧を取得
        print("📋 全ケース一覧を取得中...")
        all_cases = db_manager.get_all_cases()
        print(f"✅ 全ケース取得成功: {len(all_cases)}件")
        
        # ケースを更新
        print("✏️ ケースを更新中...")
        updated_data = test_case.copy()
        updated_data['notes'] = 'テストケース - 更新済み'
        success = db_manager.update_case(case_id, updated_data)
        if success:
            print("✅ ケース更新成功")
        else:
            print("❌ ケース更新に失敗")
            return False
        
        # 計算履歴を保存
        print("📊 計算履歴を保存中...")
        calculation_data = {
            'case_id': case_id,
            'calculation_type': '弁護士基準',
            'input_data': json.dumps({
                'injury_grade': 12,
                'treatment_days': 180,
                'income_loss': 1000000
            }),
            'results': json.dumps({
                'solatium': 2900000,
                'income_loss': 1000000,
                'total': 3900000
            }),
            'notes': 'テスト計算'
        }
        
        history_id = db_manager.save_calculation_history(calculation_data)
        print(f"✅ 計算履歴保存成功 (ID: {history_id})")
        
        # 計算履歴を取得
        print("📈 計算履歴を取得中...")
        history = db_manager.get_calculation_history(case_id)
        print(f"✅ 計算履歴取得成功: {len(history)}件")
        
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
        from calculation.compensation_engine import CompensationCalculator
        
        calculator = CompensationCalculator()
        print("✅ 計算エンジンの初期化に成功")
        
        # テスト計算データ
        test_data = {
            'injury_grade': 12,
            'age': 35,
            'gender': '男性',
            'treatment_days': 180,
            'hospitalization_days': 30,
            'annual_income': 5000000,
            'lost_income_days': 60
        }
        
        print("⚖️ 弁護士基準での計算を実行中...")
        results = calculator.calculate_lawyer_standard(test_data)
        
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
