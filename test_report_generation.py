#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弁護士損害賠償計算システム - 報告書生成機能テスト
Excel/PDF報告書生成とパフォーマンス最適化のテスト
"""

import os
import sys
import time
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from models import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
from calculation.compensation_engine import CompensationEngine
from config import get_config

# レポート生成機能の動的インポート
try:
    from reports.excel_generator import ExcelReportGeneratorOptimized as ExcelReportGenerator
    # 最適化版をメインとして使用
    ExcelReportGeneratorOptimized = ExcelReportGenerator
except ImportError as e:
    print(f"Excel生成器のインポートエラー: {e}")
    ExcelReportGenerator = None
    ExcelReportGeneratorOptimized = None

try:
    from reports.pdf_generator import PdfReportGeneratorOptimized as PdfReportGenerator
    # 最適化版をメインとして使用
    PdfReportGeneratorOptimized = PdfReportGenerator
except ImportError as e:
    print(f"PDF生成器のインポートエラー: {e}")
    PdfReportGenerator = None
    PdfReportGeneratorOptimized = None

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
        family_structure="妻・子2人",
        special_circumstances=""
    )
    
    accident_info = AccidentInfo(
        accident_date=date(2024, 6, 15),
        accident_type="交通事故",
        location="東京都渋谷区",
        weather_conditions="晴れ",
        fault_ratio=Decimal("20.0"),
        description="信号待ち中の追突事故"
    )
    
    medical_info = MedicalInfo(
        initial_diagnosis="頸椎捻挫、腰椎捻挫",
        treatment_period_days=180,
        hospitalization_days=0,
        outpatient_days=60,
        medical_expenses=Decimal("450000"),
        future_medical_expenses=Decimal("0"),
        disability_grade=14,
        symptoms="頸部痛、腰痛、右肩関節可動域制限"
    )
    
    income_info = IncomeInfo(
        annual_income=Decimal("6000000"),
        daily_income=Decimal("16438"),
        loss_period_days=45,
        occupation_type="給与所得者",
        income_proof="源泉徴収票",
        future_income_impact=Decimal("0")
    )
    
    case_data = CaseData(
        case_number="TEST-2024-001",
        client_name="田中太郎",
        case_type="交通事故",
        created_date=datetime.now(),
        person_info=person_info,
        accident_info=accident_info,
        medical_info=medical_info,
        income_info=income_info,
        notes="報告書生成テスト用データ"
    )
    
    return case_data

def test_calculation_results(case_data):
    """計算結果のテスト"""
    logger.info("=== 計算結果テスト開始 ===")
    
    engine = CompensationEngine()
    start_time = time.time()
    results = engine.calculate_compensation(case_data)
    calc_time = time.time() - start_time
    
    logger.info(f"計算処理時間: {calc_time:.3f}秒")
    logger.info(f"治療費: {results.medical_expenses:,}円")
    logger.info(f"休業損害: {results.lost_income:,}円")
    logger.info(f"慰謝料: {results.pain_suffering:,}円")
    logger.info(f"後遺障害慰謝料: {results.disability_compensation:,}円")
    logger.info(f"総損害額: {results.total_damage:,}円")
    logger.info(f"過失相殺後: {results.final_compensation:,}円")
    
    return results

def test_excel_generation(case_data, results, config):
    """Excel報告書生成テスト"""
    logger.info("=== Excel報告書生成テスト開始 ===")
    
    # 出力ディレクトリ作成
    output_dir = Path("reports/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    test_results = {}
    
    # 標準版テスト
    if ExcelReportGenerator:
        try:
            logger.info("標準版Excel生成器テスト開始")
            generator = ExcelReportGenerator(case_data, results)
            output_path = output_dir / "test_standard_excel.xlsx"
            
            start_time = time.time()
            success = generator.generate_report(str(output_path))
            generation_time = time.time() - start_time
            
            if success and output_path.exists():
                file_size = output_path.stat().st_size
                test_results['standard_excel'] = {
                    'success': True,
                    'time': generation_time,
                    'file_size': file_size,
                    'path': str(output_path)
                }
                logger.info(f"標準版Excel生成成功: {generation_time:.3f}秒, {file_size:,}bytes")
            else:
                test_results['standard_excel'] = {'success': False, 'error': 'ファイル生成失敗'}
                logger.error("標準版Excel生成失敗")
                
        except Exception as e:
            test_results['standard_excel'] = {'success': False, 'error': str(e)}
            logger.error(f"標準版Excel生成エラー: {e}")
    
    # 最適化版テスト
    if ExcelReportGeneratorOptimized:
        try:
            logger.info("最適化版Excel生成器テスト開始")
            generator_opt = ExcelReportGeneratorOptimized(config)
            
            start_time = time.time()
            output_path = generator_opt.create_compensation_report(
                case_data,
                results,
                template_type='traffic_accident',
                filename='test_optimized_excel.xlsx'
            )
            generation_time = time.time() - start_time
            
            if output_path and Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                test_results['optimized_excel'] = {
                    'success': True,
                    'time': generation_time,
                    'file_size': file_size,
                    'path': output_path
                }
                logger.info(f"最適化版Excel生成成功: {generation_time:.3f}秒, {file_size:,}bytes")
            else:
                test_results['optimized_excel'] = {'success': False, 'error': 'ファイル生成失敗'}
                logger.error("最適化版Excel生成失敗")
                
        except Exception as e:
            test_results['optimized_excel'] = {'success': False, 'error': str(e)}
            logger.error(f"最適化版Excel生成エラー: {e}")
    
    return test_results

def test_pdf_generation(case_data, results, config):
    """PDF報告書生成テスト"""
    logger.info("=== PDF報告書生成テスト開始 ===")
    
    # 出力ディレクトリ作成
    output_dir = Path("reports/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    test_results = {}
    
    # 標準版テスト
    if PdfReportGenerator:
        try:
            logger.info("標準版PDF生成器テスト開始")
            generator = PdfReportGenerator(case_data, results)
            output_path = output_dir / "test_standard_pdf.pdf"
            
            start_time = time.time()
            success = generator.generate_report(str(output_path))
            generation_time = time.time() - start_time
            
            if success and output_path.exists():
                file_size = output_path.stat().st_size
                test_results['standard_pdf'] = {
                    'success': True,
                    'time': generation_time,
                    'file_size': file_size,
                    'path': str(output_path)
                }
                logger.info(f"標準版PDF生成成功: {generation_time:.3f}秒, {file_size:,}bytes")
            else:
                test_results['standard_pdf'] = {'success': False, 'error': 'ファイル生成失敗'}
                logger.error("標準版PDF生成失敗")
                
        except Exception as e:
            test_results['standard_pdf'] = {'success': False, 'error': str(e)}
            logger.error(f"標準版PDF生成エラー: {e}")
    
    # 最適化版テスト
    if PdfReportGeneratorOptimized:
        try:
            logger.info("最適化版PDF生成器テスト開始")
            generator_opt = PdfReportGeneratorOptimized(config)
            
            start_time = time.time()
            output_path = generator_opt.create_compensation_report(
                case_data,
                results,
                template_type='traffic_accident',
                filename='test_optimized_pdf.pdf'
            )
            generation_time = time.time() - start_time
            
            if output_path and Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                test_results['optimized_pdf'] = {
                    'success': True,
                    'time': generation_time,
                    'file_size': file_size,
                    'path': output_path
                }
                logger.info(f"最適化版PDF生成成功: {generation_time:.3f}秒, {file_size:,}bytes")
            else:
                test_results['optimized_pdf'] = {'success': False, 'error': 'ファイル生成失敗'}
                logger.error("最適化版PDF生成失敗")
                
        except Exception as e:
            test_results['optimized_pdf'] = {'success': False, 'error': str(e)}
            logger.error(f"最適化版PDF生成エラー: {e}")
    
    return test_results

def test_template_types(case_data, results, config):
    """異なるテンプレートタイプのテスト"""
    logger.info("=== テンプレートタイプテスト開始 ===")
    
    template_types = ['traffic_accident', 'work_accident', 'medical_malpractice']
    template_results = {}
    
    # 最適化版Excelでテンプレートタイプをテスト
    if ExcelReportGeneratorOptimized:
        generator_opt = ExcelReportGeneratorOptimized(config)
        
        for template_type in template_types:
            try:
                logger.info(f"テンプレートタイプ '{template_type}' テスト開始")
                start_time = time.time()
                
                output_path = generator_opt.create_compensation_report(
                    case_data,
                    results,
                    template_type=template_type,
                    filename=f'test_template_{template_type}.xlsx'
                )
                
                generation_time = time.time() - start_time
                
                if output_path and Path(output_path).exists():
                    file_size = Path(output_path).stat().st_size
                    template_results[template_type] = {
                        'success': True,
                        'time': generation_time,
                        'file_size': file_size,
                        'path': output_path
                    }
                    logger.info(f"テンプレート '{template_type}' 生成成功: {generation_time:.3f}秒")
                else:
                    template_results[template_type] = {'success': False, 'error': 'ファイル生成失敗'}
                    
            except Exception as e:
                template_results[template_type] = {'success': False, 'error': str(e)}
                logger.error(f"テンプレート '{template_type}' 生成エラー: {e}")
    
    return template_results

def performance_comparison(excel_results, pdf_results):
    """パフォーマンス比較"""
    logger.info("=== パフォーマンス比較結果 ===")
    
    # Excel比較
    if 'standard_excel' in excel_results and 'optimized_excel' in excel_results:
        std_excel = excel_results['standard_excel']
        opt_excel = excel_results['optimized_excel']
        
        if std_excel.get('success') and opt_excel.get('success'):
            time_improvement = ((std_excel['time'] - opt_excel['time']) / std_excel['time']) * 100
            size_diff = opt_excel['file_size'] - std_excel['file_size']
            
            logger.info(f"Excel生成時間改善: {time_improvement:.1f}%")
            logger.info(f"標準版: {std_excel['time']:.3f}秒, 最適化版: {opt_excel['time']:.3f}秒")
            logger.info(f"ファイルサイズ差: {size_diff:+,}bytes")
    
    # PDF比較
    if 'standard_pdf' in pdf_results and 'optimized_pdf' in pdf_results:
        std_pdf = pdf_results['standard_pdf']
        opt_pdf = pdf_results['optimized_pdf']
        
        if std_pdf.get('success') and opt_pdf.get('success'):
            time_improvement = ((std_pdf['time'] - opt_pdf['time']) / std_pdf['time']) * 100
            size_diff = opt_pdf['file_size'] - std_pdf['file_size']
            
            logger.info(f"PDF生成時間改善: {time_improvement:.1f}%")
            logger.info(f"標準版: {std_pdf['time']:.3f}秒, 最適化版: {opt_pdf['time']:.3f}秒")
            logger.info(f"ファイルサイズ差: {size_diff:+,}bytes")

def print_summary(excel_results, pdf_results, template_results):
    """テスト結果サマリー"""
    logger.info("=== テスト結果サマリー ===")
    
    total_tests = 0
    passed_tests = 0
    
    # Excelテスト
    for test_name, result in excel_results.items():
        total_tests += 1
        if result.get('success'):
            passed_tests += 1
            logger.info(f"✅ {test_name}: 成功")
        else:
            logger.error(f"❌ {test_name}: 失敗 - {result.get('error', '不明なエラー')}")
    
    # PDFテスト
    for test_name, result in pdf_results.items():
        total_tests += 1
        if result.get('success'):
            passed_tests += 1
            logger.info(f"✅ {test_name}: 成功")
        else:
            logger.error(f"❌ {test_name}: 失敗 - {result.get('error', '不明なエラー')}")
    
    # テンプレートテスト
    for template_type, result in template_results.items():
        total_tests += 1
        if result.get('success'):
            passed_tests += 1
            logger.info(f"✅ テンプレート_{template_type}: 成功")
        else:
            logger.error(f"❌ テンプレート_{template_type}: 失敗 - {result.get('error', '不明なエラー')}")
    
    logger.info(f"総テスト数: {total_tests}, 成功: {passed_tests}, 失敗: {total_tests - passed_tests}")
    logger.info(f"成功率: {(passed_tests / total_tests * 100):.1f}%")

def main():
    """メイン実行関数"""
    logger.info("弁護士損害賠償計算システム - 報告書生成機能テスト開始")
    
    try:        # 設定読み込み
        config = get_config()
        
        # テストデータ作成
        case_data = create_test_case_data()
        
        # 計算実行
        results = test_calculation_results(case_data)
        
        # Excel報告書生成テスト
        excel_results = test_excel_generation(case_data, results, config)
        
        # PDF報告書生成テスト
        pdf_results = test_pdf_generation(case_data, results, config)
        
        # テンプレートタイプテスト
        template_results = test_template_types(case_data, results, config)
        
        # パフォーマンス比較
        performance_comparison(excel_results, pdf_results)
        
        # 結果サマリー
        print_summary(excel_results, pdf_results, template_results)
        
        logger.info("報告書生成機能テスト完了")
        
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()
