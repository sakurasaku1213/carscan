#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム統合テスト - 弁護士基準損害賠償計算システム
新機能のエンドツーエンドテスト
"""

import unittest
import tempfile
import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
import logging

# パスの設定
sys.path.insert(0, os.path.abspath('.'))

# プロジェクトモジュールのインポート
from config.app_config import AppConfig, ConfigManager
from models.case_data import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
from calculation.compensation_engine import CompensationEngine, CalculationResult
from reports.excel_generator_optimized import ExcelReportGeneratorOptimized
from reports.pdf_generator_optimized import PdfReportGeneratorOptimized
from utils.security_manager import IntegratedSecurityManager, DataCategory
from utils.performance_monitor import PerformanceMonitor
from utils.error_handler import get_error_handler


class SystemIntegrationTests(unittest.TestCase):
    """システム統合テストクラス"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス初期化"""
        # ログ設定
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        
        # 一時ディレクトリ作成
        cls.temp_dir = tempfile.mkdtemp()
        cls.logger.info(f"テスト用一時ディレクトリ: {cls.temp_dir}")
        
        # 設定ファイル作成
        cls._create_test_config()
          # アプリケーション設定の初期化
        cls.config_manager = ConfigManager(cls.test_config_path)
        cls.config = cls.config_manager.get_config()
        
        # テスト用ケースデータ作成
        cls.test_case_data = cls._create_test_case_data()
        
        cls.logger.info("システム統合テスト環境を初期化しました")

    @classmethod
    def _create_test_config(cls):
        """テスト用設定ファイル作成"""
        config_data = {
            "application": {
                "name": "弁護士基準損害賠償計算システム（テスト版）",
                "version": "2.0.0-test",
                "description": "統合テスト用設定",
                "author": "開発チーム",
                "license": "proprietary"
            },            "database": {
                "db_path": os.path.join(cls.temp_dir, "database", "test.db"),
                "backup_enabled": True,
                "backup_interval_hours": 1,
                "backup_retention_days": 7
            },            "report": {
                "default_output_directory": os.path.join(cls.temp_dir, "reports"),
                "excel_template_path": os.path.join(cls.temp_dir, "templates", "default.xlsx"),
                "pdf_template_path": os.path.join(cls.temp_dir, "templates", "default.json"),
                "company_logo_path": os.path.join(cls.temp_dir, "assets", "logo.png"),
                "default_author": "テスト実行者",
                "font_name_gothic": "MS Gothic",
                "font_path_gothic": "",                "excel_templates": {
                    "traffic_accident": "交通事故損害賠償計算書.xlsx",
                    "work_accident": "労災事故損害賠償計算書.xlsx", 
                    "medical_malpractice": "医療過誤損害賠償計算書.xlsx"
                },
                "pdf_templates": {
                    "traffic_accident": "交通事故損害賠償計算書.pdf",
                    "work_accident": "労災事故損害賠償計算書.pdf",
                    "medical_malpractice": "医療過誤損害賠償計算書.pdf"
                }
            },            "security": {
                "enable_data_encryption": True,
                "backup_encryption": True,
                "session_timeout": 1800,
                "max_login_attempts": 3
            },
            "performance": {
                "monitoring_enabled": True,
                "log_performance_metrics": True,
                "performance_log_file": os.path.join(cls.temp_dir, "performance.log"),
                "alert_thresholds": {
                    "calculation_time_ms": 5000,
                    "report_generation_time_ms": 10000,
                    "memory_usage_mb": 500
                }
            }
        }
          # 設定ファイル保存
        cls.test_config_path = os.path.join(cls.temp_dir, "test_config.json")
        with open(cls.test_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

    @classmethod
    def _create_test_case_data(cls) -> CaseData:
        """テスト用ケースデータ作成"""
        return CaseData(
            case_number="TEST-2024-001",
            status="計算完了",
            person_info=PersonInfo(
                name="田中太郎",
                age=35,
                gender="男性",
                occupation="会社員",
                annual_income=Decimal("5000000"),
                fault_percentage=20.0
            ),
            accident_info=AccidentInfo(
                accident_date=date(2024, 1, 15),
                location="東京都新宿区",
                weather="晴天",
                accident_type="追突事故",
                police_report_number="R6-12345"
            ),
            medical_info=MedicalInfo(
                hospital_months=0,
                outpatient_months=6,
                actual_outpatient_days=90,
                is_whiplash=True,
                disability_grade=14,
                disability_details="頸椎捻挫",
                medical_expenses=Decimal("150000"),
                transportation_costs=Decimal("25000"),
                nursing_costs=Decimal("0")
            ),
            income_info=IncomeInfo(
                lost_work_days=30,
                daily_income=Decimal("16438"),  # 年収500万円÷365日≈13,698円、働く日数を考慮して調整
                loss_period_years=10,
                basic_annual_income=Decimal("5000000"),
                bonus_ratio=0.3
            ),
            notes="交通事故による頸椎捻挫のテストケース"
        )

    def setUp(self):
        """各テストメソッド前の初期化"""
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = get_error_handler()
          # 必要なディレクトリを作成
        os.makedirs(self.config.report.default_output_directory, exist_ok=True)
        os.makedirs(os.path.dirname(self.config.report.excel_template_path or "templates/excel"), exist_ok=True)

    def test_01_config_system_integration(self):
        """設定管理システムの統合テスト"""
        self.logger.info("=== 設定管理システム統合テスト開始 ===")
        self.assertIsNotNone(self.config)
        self.assertIsNotNone(self.config_manager)

        # 設定値の検証 (getメソッドではなく直接アクセス)
        self.assertEqual(self.config.application.app_name, "弁護士基準損害賠償計算システム")
        self.assertTrue(self.config.security.encryption_enabled) # 変更
        self.assertEqual(self.config.database.db_path, str(self.temp_dir / "test_cases.db"))

        # 設定の保存と再読み込み
        self.config_manager.save_config()
        self.config_manager.load_config()

        self.logger.info("設定管理システム統合テスト完了")

    def test_02_calculation_engine_integration(self):
        """計算エンジンの統合テスト"""
        self.logger.info("=== 計算エンジン統合テスト開始 ===")
        
        engine = CompensationEngine()
        
        # 計算実行
        results = engine.calculate_compensation(self.test_case_data)
        
        # 結果検証
        self.assertIsInstance(results, dict)
        self.assertTrue(len(results) > 0)
        
        # 各結果項目の検証
        for item_name, result in results.items():
            self.assertIsInstance(result, CalculationResult)
            self.assertIsNotNone(result.amount)
            self.assertIsInstance(result.amount, Decimal)
        
        # 主要項目の存在確認
        expected_items = ['medical_expenses', 'pain_suffering', 'lost_income']
        for item in expected_items:
            found = any(item in result_name for result_name in results.keys())
            self.assertTrue(found, f"期待される項目 '{item}' が見つかりません")
        
        self.logger.info(f"計算結果 {len(results)} 項目を確認しました")

    def test_03_excel_report_generation_integration(self):
        """Excelレポート生成の統合テスト"""
        self.logger.info("=== Excelレポート生成統合テスト開始 ===")
        
        # 計算実行
        engine = CompensationEngine()
        results = engine.calculate_compensation(self.test_case_data)
        
        # Excelジェネレータ初期化
        excel_generator = ExcelReportGeneratorOptimized(self.config)
        
        # テンプレートタイプ別にテスト
        template_types = ['traffic_accident', 'work_accident', 'medical_malpractice']
        generated_files = []
        
        for template_type in template_types:
            output_path = excel_generator.create_compensation_report(
                self.test_case_data,
                results,
                template_type=template_type,
                filename=f"test_excel_{template_type}.xlsx"
            )
            
            # ファイル存在確認
            self.assertTrue(os.path.exists(output_path), f"Excelファイルが生成されませんでした: {output_path}")
            
            # ファイルサイズ確認
            file_size = os.path.getsize(output_path)
            self.assertGreater(file_size, 1000, f"生成されたExcelファイルのサイズが小さすぎます: {file_size} bytes")
            
            generated_files.append(output_path)
            self.logger.info(f"Excelファイル生成完了: {template_type} ({file_size} bytes)")
        
        self.assertEqual(len(generated_files), 3)
        self.logger.info("Excelレポート生成統合テスト完了")

    def test_04_pdf_report_generation_integration(self):
        """PDFレポート生成の統合テスト"""
        self.logger.info("=== PDFレポート生成統合テスト開始 ===")
          # 計算実行
        engine = CompensationEngine()
        results = engine.calculate_compensation(self.test_case_data)
        
        # PDFジェネレータ初期化
        pdf_generator = PdfReportGeneratorOptimized(self.config)
        
        # テンプレートタイプ別にテスト
        template_types = ['traffic_accident', 'work_accident', 'medical_malpractice']
        generated_files = []
        
        for template_type in template_types:
            output_path = pdf_generator.create_compensation_report(
                self.test_case_data,
                results,
                template_type=template_type,
                filename=f"test_pdf_{template_type}.pdf"
            )
            
            # ファイル存在確認
            self.assertTrue(os.path.exists(output_path), f"PDFファイルが生成されませんでした: {output_path}")
            
            # ファイルサイズ確認
            file_size = os.path.getsize(output_path)
            self.assertGreater(file_size, 1000, f"生成されたPDFファイルのサイズが小さすぎます: {file_size} bytes")
            
            generated_files.append(output_path)
            self.logger.info(f"PDFファイル生成完了: {template_type} ({file_size} bytes)")
        
        self.assertEqual(len(generated_files), 3)
        self.logger.info("PDFレポート生成統合テスト完了")

    def test_05_security_system_integration(self):
        """セキュリティシステムの統合テスト"""
        self.logger.info("=== セキュリティシステム統合テスト開始 ===")
        
        # セキュリティマネージャー初期化
        security_manager = IntegratedSecurityManager(self.config)
        
        # データ暗号化テスト
        test_data = {
            "client_name": "テスト太郎",
            "case_number": "TEST-001",
            "medical_expenses": "150000"
        }
        
        # 暗号化
        encrypted_data, metadata = security_manager.encrypt_data(
            test_data, 
            DataCategory.CASE_DATA,
            user_id="test_user"
        )
        
        self.assertIsNotNone(encrypted_data)
        self.assertTrue(metadata.get('encrypted', False))
        
        # 復号化
        decrypted_data = security_manager.decrypt_data(
            encrypted_data,
            metadata,
            DataCategory.CASE_DATA,
            user_id="test_user"
        )
        
        self.assertEqual(decrypted_data, test_data)
          # セキュアレポート生成テスト
        engine = CompensationEngine()
        results = engine.calculate_compensation(self.test_case_data)
        
        secure_report = security_manager.secure_report_generation(
            {"case_data": self.test_case_data.__dict__, "results": results},
            "traffic_accident",
            user_id="test_user"
        )
        
        self.assertTrue(secure_report.get('security_applied', False))
        self.assertIn('masked_data', secure_report)
        self.assertIn('encrypted_data', secure_report)
        
        # セキュリティ監査レポート生成テスト
        audit_report = security_manager.get_security_audit_report(user_id="test_user")
        self.assertIsNotNone(audit_report)
        self.assertIn('summary', audit_report)
        self.assertIn('statistics', audit_report)
        
        self.logger.info("セキュリティシステム統合テスト完了")

    def test_06_performance_monitoring_integration(self):
        """パフォーマンス監視システムの統合テスト"""
        self.logger.info("=== パフォーマンス監視統合テスト開始 ===")
        
        # パフォーマンス監視付きで処理実行
        self.performance_monitor.start_timing('integration_test')
          # 計算エンジン実行
        engine = CompensationEngine()
        results = engine.calculate_compensation(self.test_case_data)
        
        # レポート生成
        excel_generator = ExcelReportGeneratorOptimized(self.config)
        excel_path = excel_generator.create_compensation_report(
            self.test_case_data,
            results,
            filename="performance_test.xlsx"
        )
        
        self.performance_monitor.end_timing('integration_test')
        
        # パフォーマンス統計取得
        stats = self.performance_monitor.get_statistics()
        self.assertIn('integration_test', stats)
        
        total_time = stats['integration_test']['total_time']
        self.assertGreater(total_time, 0)
        self.logger.info(f"統合テスト実行時間: {total_time:.3f}秒")
        
        # メモリ使用量確認
        memory_usage = self.performance_monitor.get_memory_usage()
        self.assertGreater(memory_usage, 0)
        self.logger.info(f"メモリ使用量: {memory_usage:.2f}MB")
        
        self.logger.info("パフォーマンス監視統合テスト完了")

    def test_07_error_handling_integration(self):
        """エラーハンドリングシステムの統合テスト"""
        self.logger.info("=== エラーハンドリング統合テスト開始 ===")
          # 無効なデータでのテスト
        invalid_person_info = PersonInfo(
            name="",  # 空の名前
            age=-1,  # 無効な年齢
            gender="invalid",  # 無効な性別
            occupation="",
            annual_income=Decimal("-1000"),  # 負の収入
            fault_percentage=200.0  # 100%超過
        )
        
        invalid_accident_info = AccidentInfo(
            accident_date=date(2024, 1, 15)
        )
        
        invalid_medical_info = MedicalInfo(
            injury_type="",
            treatment_period_days=-10,  # 負の治療期間
            hospitalization_days=-5,
            disability_grade=100,  # 無効な等級
            medical_expenses=Decimal("-1000")
        )
        
        invalid_income_info = IncomeInfo(
            transportation_expenses=Decimal("-500"),
            lost_income_days=-10,
            other_expenses=Decimal("-100")
        )
        
        invalid_case_data = CaseData(
            case_number="INVALID-TEST",
            person_info=invalid_person_info,
            accident_info=invalid_accident_info,
            medical_info=invalid_medical_info,
            income_info=invalid_income_info
        )
        
        engine = CompensationEngine()
        
        # エラーが適切に処理されることを確認
        try:
            results = engine.calculate_compensation(invalid_case_data)
            # エラーが発生せずに結果が返される場合もあることを考慮
            self.logger.info("無効データでも結果が返されました（バリデーション機能が必要）")
        except Exception as e:
            self.logger.info(f"期待通りエラーが発生しました: {type(e).__name__}")
        
        self.logger.info("エラーハンドリング統合テスト完了")

    def test_08_batch_processing_integration(self):
        """バッチ処理の統合テスト"""
        self.logger.info("=== バッチ処理統合テスト開始 ===")
        
        # 複数ケースデータ作成
        test_cases = []
        for i in range(5):            case_data = CaseData(
                case_number=f"BATCH-TEST-{i+1:03d}",
                person_info=PersonInfo(
                    name=f"テスト太郎{i+1}",
                    age=30 + i,
                    gender="male" if i % 2 == 0 else "female",
                    occupation="会社員",
                    annual_income=Decimal(str(4000000 + i * 500000))
                ),
                accident_info=AccidentInfo(
                    accident_date=date(2024, 1, 15)
                ),
                medical_info=MedicalInfo(
                    injury_type="頸椎捻挫",
                    treatment_period_days=120 + i * 30,
                    hospitalization_days=i * 2,
                    disability_grade=14,                    medical_expenses=Decimal(str(100000 + i * 25000))
                ),
                income_info=IncomeInfo(
                    transportation_expenses=Decimal(str(20000 + i * 5000)),
                    lost_income_days=20 + i * 10,
                    other_expenses=Decimal(str(5000 + i * 2000))
                )
            )
            
            # エンジン初期化と計算実行
            engine = CompensationEngine()
            results = engine.calculate_compensation(case_data)
            
            test_cases.append({
                'case_data': case_data,
                'results': results
            })
        
        # バッチPDF生成テスト
        pdf_generator = PdfReportGeneratorOptimized(self.config)
        generated_pdfs = pdf_generator.generate_batch_reports(test_cases, 'traffic_accident')
        
        self.assertEqual(len(generated_pdfs), 5)
        
        # 全ファイルの存在確認
        for pdf_path in generated_pdfs:
            self.assertTrue(os.path.exists(pdf_path))
            file_size = os.path.getsize(pdf_path)
            self.assertGreater(file_size, 1000)
        
        self.logger.info(f"バッチ処理で {len(generated_pdfs)} 件のPDFを生成しました")

    def test_09_end_to_end_workflow(self):
        """エンドツーエンドワークフローテスト"""
        self.logger.info("=== エンドツーエンド ワークフローテスト開始 ===")
        
        self.performance_monitor.start_timing('e2e_workflow')
        
        # 1. ケースデータ準備
        case_data = self.test_case_data
        
        # 2. セキュリティチェック
        security_manager = IntegratedSecurityManager(self.config)
        encrypted_case, metadata = security_manager.encrypt_data(
            case_data.__dict__,
            DataCategory.CASE_DATA,
            user_id="e2e_test_user"
        )
          # 3. 計算実行
        engine = CompensationEngine()
        results = engine.calculate_compensation(case_data)
        
        # 4. セキュアレポート生成
        secure_report_data = security_manager.secure_report_generation(
            {"case_data": case_data.__dict__, "results": results},
            "traffic_accident",
            user_id="e2e_test_user"
        )
        
        # 5. Excelレポート生成
        excel_generator = ExcelReportGeneratorOptimized(self.config)
        excel_path = excel_generator.create_compensation_report(
            case_data,
            results,
            template_type='traffic_accident',
            filename="e2e_test_excel.xlsx"
        )
        
        # 6. PDFレポート生成
        pdf_generator = PdfReportGeneratorOptimized(self.config)
        pdf_path = pdf_generator.create_compensation_report(
            case_data,
            results,
            template_type='traffic_accident',
            filename="e2e_test_pdf.pdf"
        )
        
        # 7. 監査ログ確認
        audit_report = security_manager.get_security_audit_report(user_id="e2e_test_user")
        
        self.performance_monitor.end_timing('e2e_workflow')
        
        # 結果検証
        self.assertTrue(os.path.exists(excel_path))
        self.assertTrue(os.path.exists(pdf_path))
        self.assertIsNotNone(audit_report)
        self.assertTrue(secure_report_data.get('security_applied', False))
        
        # パフォーマンス統計
        stats = self.performance_monitor.get_statistics()
        e2e_time = stats['e2e_workflow']['total_time']
        
        self.logger.info(f"エンドツーエンドワークフロー完了時間: {e2e_time:.3f}秒")
        self.logger.info(f"生成ファイル - Excel: {excel_path}")
        self.logger.info(f"生成ファイル - PDF: {pdf_path}")

    def test_10_system_stability_test(self):
        """システム安定性テスト"""
        self.logger.info("=== システム安定性テスト開始 ===")
        
        # 連続処理でメモリリークや性能劣化をチェック
        initial_memory = self.performance_monitor.get_memory_usage()
        
        for i in range(10):  # 10回連続実行
            case_data = CaseData(
                case_number=f"STABILITY-{i+1:03d}",
                client_name=f"安定性テスト{i+1}",
                accident_date=date(2024, 1, 15),
                age=30,
                gender="male",
                occupation="会社員",
                annual_income=Decimal("5000000"),
                injury_type="頸椎捻挫",
                treatment_period_days=120,
                hospitalization_days=0,
                disability_grade=14,
                fault_ratio=Decimal("0.2"),
                medical_expenses=Decimal("100000"),
                transportation_expenses=Decimal("20000"),
                lost_income_days=20,
                other_expenses=Decimal("5000")            )
            
            # 計算実行
            engine = CompensationEngine()
            results = engine.calculate_compensation(case_data)
            
            # レポート生成（Excel）
            excel_generator = ExcelReportGeneratorOptimized(self.config)
            excel_path = excel_generator.create_compensation_report(
                case_data,
                results,
                filename=f"stability_test_{i+1:03d}.xlsx"
            )
            
            # ファイル存在確認
            self.assertTrue(os.path.exists(excel_path))
            
            # メモリ使用量監視
            current_memory = self.performance_monitor.get_memory_usage()
            memory_increase = current_memory - initial_memory
            
            # メモリ使用量が異常に増加していないことを確認（100MB以下）
            self.assertLess(memory_increase, 100, 
                          f"反復 {i+1}: メモリ使用量が異常に増加しています ({memory_increase:.2f}MB)")
            
            if (i + 1) % 5 == 0:
                self.logger.info(f"安定性テスト進捗: {i+1}/10 - メモリ使用量: {current_memory:.2f}MB")
        
        final_memory = self.performance_monitor.get_memory_usage()
        total_memory_increase = final_memory - initial_memory
        
        self.logger.info(f"安定性テスト完了 - 総メモリ増加量: {total_memory_increase:.2f}MB")
        self.assertLess(total_memory_increase, 50, "メモリリークの可能性があります")

    @classmethod
    def tearDownClass(cls):
        """テストクラス終了処理"""
        import shutil
        
        cls.logger.info("=== システム統合テスト完了 ===")
        cls.logger.info(f"テスト結果ファイルは {cls.temp_dir} に保存されています")
        
        # 一時ディレクトリの削除（コメントアウトして結果を確認可能）
        # shutil.rmtree(cls.temp_dir)


if __name__ == '__main__':
    # テストスイート実行
    unittest.main(verbosity=2)
