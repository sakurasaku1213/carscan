#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弁護士損害賠償計算システム - 簡易報告書生成テスト
基本的な計算機能と出力テスト
"""

import os
import sys
import time
import logging
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from models.case_data import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
from calculation.compensation_engine import CompensationEngine
from config.app_config import get_config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

def create_test_case_data():
    """テスト用のケースデータを作成"""
    person_info = PersonInfo(
        name="田中太郎",
        age=35,
        gender="男性",
        occupation="会社員",
        annual_income=Decimal("6000000"),
        fault_percentage=20.0
    )
    
    accident_info = AccidentInfo(
        accident_date=date(2024, 6, 15),
        accident_type="交通事故",
        location="東京都渋谷区",
        weather="晴れ",
        road_condition="乾燥",
        police_report_number="R06-001234"
    )
    
    medical_info = MedicalInfo(
        hospital_months=0,
        outpatient_months=6,
        actual_outpatient_days=60,
        is_whiplash=True,
        disability_grade=14,
        disability_details="頸部痛、腰痛、右肩関節可動域制限",
        medical_expenses=Decimal("450000"),
        transportation_costs=Decimal("25000"),
        nursing_costs=Decimal("0")
    )
    
    income_info = IncomeInfo(
        lost_work_days=45,
        daily_income=Decimal("16438"),
        loss_period_years=0,
        retirement_age=67,
        basic_annual_income=Decimal("6000000"),        bonus_ratio=0.3
    )
    
    case_data = CaseData()
    case_data.case_number = "TEST-2024-002"
    case_data.status = "計算完了"
    case_data.person_info = person_info
    case_data.accident_info = accident_info
    case_data.medical_info = medical_info
    case_data.income_info = income_info
    case_data.notes = "簡易報告書生成テスト用データ"
    
    return case_data

def test_calculation_engine(case_data):
    """計算エンジンのテスト"""
    logger.info("=== 計算エンジンテスト開始 ===")
    
    engine = CompensationEngine()
    start_time = time.time()
    
    try:
        results = engine.calculate_all(case_data)
        calc_time = time.time() - start_time
        
        logger.info(f"✅ 計算処理時間: {calc_time:.3f}秒")
        
        if isinstance(results, dict):
            total_amount = Decimal('0')
            for item_name, result in results.items():
                if result and hasattr(result, 'amount'):
                    amount = result.amount
                    logger.info(f"{item_name}: ¥{amount:,}")
                    if item_name != 'summary':  # summaryは最終合計なので重複計算を避ける
                        total_amount += amount
                        
            # サマリー情報を表示
            if 'summary' in results and results['summary']:
                logger.info("=== 計算結果サマリー ===")
                logger.info(results['summary'].calculation_details)
            
            return results, True
        else:
            logger.error("❌ 計算結果の形式が不正です")
            return None, False
            
    except Exception as e:
        logger.error(f"❌ 計算エンジンエラー: {e}")
        return None, False

def create_simple_text_report(case_data, results, output_path):
    """簡易テキスト報告書の作成"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("損害賠償計算書（簡易版）\n")
            f.write("=" * 60 + "\n\n")
              # 基本情報
            f.write("【基本情報】\n")
            f.write(f"案件番号: {case_data.case_number}\n")
            f.write(f"依頼者名: {case_data.person_info.name}\n")
            f.write(f"事故種類: {case_data.accident_info.accident_type}\n")
            f.write(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
              # 人的情報
            f.write("【人的情報】\n")
            f.write(f"氏名: {case_data.person_info.name}\n")
            f.write(f"年齢: {case_data.person_info.age}歳\n")
            f.write(f"性別: {case_data.person_info.gender}\n")
            f.write(f"職業: {case_data.person_info.occupation}\n")
            f.write(f"年収: {case_data.person_info.annual_income:,}円\n")
            f.write(f"過失割合: {case_data.person_info.fault_percentage}%\n\n")
            
            # 事故情報
            f.write("【事故情報】\n")
            f.write(f"事故日: {case_data.accident_info.accident_date}\n")
            f.write(f"事故場所: {case_data.accident_info.location}\n")
            f.write(f"天候: {case_data.accident_info.weather}\n")
            f.write(f"路面状況: {case_data.accident_info.road_condition}\n")
            f.write(f"事故種類: {case_data.accident_info.accident_type}\n")
            f.write(f"警察番号: {case_data.accident_info.police_report_number}\n\n")
            
            # 医療情報
            f.write("【医療情報】\n")
            f.write(f"入院期間: {case_data.medical_info.hospital_months}ヶ月\n")
            f.write(f"通院期間: {case_data.medical_info.outpatient_months}ヶ月\n")
            f.write(f"実通院日数: {case_data.medical_info.actual_outpatient_days}日\n")
            f.write(f"むち打ち症: {'あり' if case_data.medical_info.is_whiplash else 'なし'}\n")
            f.write(f"治療費: {case_data.medical_info.medical_expenses:,}円\n")
            f.write(f"交通費: {case_data.medical_info.transportation_costs:,}円\n")
            f.write(f"看護費: {case_data.medical_info.nursing_costs:,}円\n")
            f.write(f"後遺障害等級: {case_data.medical_info.disability_grade}級\n")
            f.write(f"後遺障害詳細: {case_data.medical_info.disability_details}\n\n")
            
            # 収入情報
            f.write("【収入情報】\n")
            f.write(f"基本年収: {case_data.income_info.basic_annual_income:,}円\n")
            f.write(f"日額: {case_data.income_info.daily_income:,}円\n")
            f.write(f"休業日数: {case_data.income_info.lost_work_days}日\n")
            f.write(f"退職年齢: {case_data.income_info.retirement_age}歳\n")
            f.write(f"ボーナス比率: {case_data.income_info.bonus_ratio:.1%}\n\n")
              # 計算結果
            f.write("【計算結果】\n")
            f.write("-" * 40 + "\n")
            
            # 結果がDictionary形式の場合
            if isinstance(results, dict):
                for item_name, result in results.items():
                    if result and hasattr(result, 'amount') and item_name != 'summary':
                        f.write(f"{item_name}: {result.amount:>15,}円\n")
                
                # サマリー情報
                if 'summary' in results and results['summary']:
                    f.write("-" * 40 + "\n")
                    f.write("【総合計】\n")
                    f.write(f"最終支払見込額: {results['summary'].amount:>12,}円\n")
                    f.write("\n【計算詳細】\n")
                    f.write(results['summary'].calculation_details)
            else:
                f.write("計算結果の取得に失敗しました\n")
            
            f.write("=" * 60 + "\n")
            
        return True
        
    except Exception as e:
        logger.error(f"テキスト報告書作成エラー: {e}")
        return False

def test_report_generation(case_data, results):
    """報告書生成テスト"""
    logger.info("=== 報告書生成テスト開始 ===")
    
    # 出力ディレクトリ作成
    output_dir = Path("reports/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    test_results = []
    
    # テキスト報告書生成テスト
    text_output_path = output_dir / "simple_report.txt"
    start_time = time.time()
    success = create_simple_text_report(case_data, results, text_output_path)
    generation_time = time.time() - start_time
    
    if success and text_output_path.exists():
        file_size = text_output_path.stat().st_size
        test_results.append({
            'type': 'テキスト報告書',
            'success': True,
            'time': generation_time,
            'file_size': file_size,
            'path': str(text_output_path)
        })
        logger.info(f"✅ テキスト報告書生成成功: {generation_time:.3f}秒, {file_size:,}bytes")
    else:
        test_results.append({
            'type': 'テキスト報告書',
            'success': False,
            'error': 'ファイル生成失敗'
        })
        logger.error("❌ テキスト報告書生成失敗")
    
    return test_results

def test_performance_scenarios(case_data):
    """パフォーマンステスト（複数シナリオ）"""
    logger.info("=== パフォーマンステスト開始 ===")
    
    engine = CompensationEngine()
    scenarios = []
      # シナリオ1: 軽微な事故
    scenario1 = case_data
    scenario1.medical_info.disability_grade = 0
    scenario1.medical_info.outpatient_months = 1    # シナリオ2: 重篤な事故
    scenario2_medical = MedicalInfo(
        hospital_months=4,
        outpatient_months=12,
        actual_outpatient_days=245,
        is_whiplash=False,
        disability_grade=1,
        disability_details="高次脳機能障害、四肢麻痺",
        medical_expenses=Decimal("2500000"),
        transportation_costs=Decimal("100000"),
        nursing_costs=Decimal("500000")
    )
    scenario2 = CaseData()
    scenario2.case_number = "PERF-2024-002"
    scenario2.status = "計算完了"
    scenario2.person_info = case_data.person_info
    scenario2.accident_info = case_data.accident_info
    scenario2.medical_info = scenario2_medical
    scenario2.income_info = case_data.income_info
    scenario2.notes = "重篤事故パフォーマンステスト"
    
    scenarios = [
        ("軽微事故", scenario1),
        ("重篤事故", scenario2)    ]
    
    performance_results = []
    
    for scenario_name, scenario_data in scenarios:
        logger.info(f"シナリオ '{scenario_name}' テスト開始")
        
        start_time = time.time()
        try:
            results = engine.calculate_all(scenario_data)
            calc_time = time.time() - start_time
            
            # 最終金額の取得
            final_amount = results['summary'].amount if 'summary' in results and results['summary'] else Decimal('0')
            
            performance_results.append({
                'scenario': scenario_name,
                'success': True,
                'time': calc_time,
                'final_compensation': final_amount
            })
            
            logger.info(f"✅ {scenario_name}: {calc_time:.3f}秒, 最終支払見込額: {final_amount:,}円")
            
        except Exception as e:
            performance_results.append({
                'scenario': scenario_name,
                'success': False,
                'error': str(e)
            })
            logger.error(f"❌ {scenario_name}: {e}")
    
    return performance_results

def print_test_summary(calc_success, report_results, performance_results):
    """テスト結果サマリー"""
    logger.info("=== テスト結果サマリー ===")
    
    total_tests = 1  # 計算エンジンテスト
    passed_tests = 0
    
    # 計算エンジンテスト
    if calc_success:
        passed_tests += 1
        logger.info("✅ 計算エンジンテスト: 成功")
    else:
        logger.error("❌ 計算エンジンテスト: 失敗")
    
    # 報告書生成テスト
    for result in report_results:
        total_tests += 1
        if result.get('success'):
            passed_tests += 1
            logger.info(f"✅ {result['type']}: 成功")
        else:
            logger.error(f"❌ {result['type']}: 失敗")
    
    # パフォーマンステスト
    for result in performance_results:
        total_tests += 1
        if result.get('success'):
            passed_tests += 1
            logger.info(f"✅ パフォーマンス_{result['scenario']}: 成功")
        else:
            logger.error(f"❌ パフォーマンス_{result['scenario']}: 失敗")
    
    logger.info(f"総テスト数: {total_tests}, 成功: {passed_tests}, 失敗: {total_tests - passed_tests}")
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    logger.info(f"成功率: {success_rate:.1f}%")
    
    return success_rate

def main():
    """メイン実行関数"""
    logger.info("弁護士損害賠償計算システム - 簡易報告書生成テスト開始")
    
    try:
        # 設定読み込み
        config = get_config()
        logger.info(f"設定読み込み完了: {config.app_name} v{config.version}")
        
        # テストデータ作成
        case_data = create_test_case_data()
        logger.info("テストデータ作成完了")
        
        # 計算エンジンテスト
        results, calc_success = test_calculation_engine(case_data)
        
        if not calc_success:
            logger.error("計算エンジンテストが失敗したため、テストを終了します")
            return
        
        # 報告書生成テスト
        report_results = test_report_generation(case_data, results)
        
        # パフォーマンステスト
        performance_results = test_performance_scenarios(case_data)
        
        # 結果サマリー
        success_rate = print_test_summary(calc_success, report_results, performance_results)
        
        if success_rate >= 80:
            logger.info("🎉 テスト全体: 成功")
        else:
            logger.warning("⚠️ テスト全体: 部分的成功")
        
        logger.info("簡易報告書生成テスト完了")
        
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()
