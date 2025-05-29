#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDFレポート生成モジュール - パフォーマンス最適化版
新しい設定管理システムとパフォーマンス監視を完全統合
"""

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from decimal import Decimal
from datetime import datetime
import traceback
import os
from typing import Dict, List, Optional, Any
import logging

# 日本語フォント対応のため追加
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models import CaseData
from calculation.compensation_engine import CalculationResult
from utils import (
    get_error_handler, CompensationSystemError, ErrorCategory, ErrorSeverity, 
    FileIOError, ConfigurationError, monitor_performance, get_performance_monitor
)
from config.app_config import AppConfig


class PdfTemplateManager:
    """PDFテンプレート管理クラス"""
    
    def __init__(self, report_config, logger):
        self.report_config = report_config
        self.logger = logger
        self.templates = {}
        self._initialize_templates()
    
    @monitor_performance
    def _initialize_templates(self):
        """テンプレートを初期化"""
        try:
            self.templates = {
                'traffic_accident': self._create_traffic_accident_template(),
                'work_accident': self._create_work_accident_template(),
                'medical_malpractice': self._create_medical_malpractice_template()
            }
            self.logger.info(f"PDFテンプレート {len(self.templates)} 種類を初期化しました")
        except Exception as e:
            self.logger.error(f"PDFテンプレート初期化に失敗: {str(e)}")
            raise ConfigurationError(f"PDFテンプレート初期化エラー: {str(e)}")
    
    def _create_traffic_accident_template(self) -> Dict[str, Any]:
        """交通事故用PDFテンプレート"""
        return {
            'name': '交通事故損害賠償計算書',
            'sections': [
                {'id': 'header', 'title': '事故概要', 'items': ['accident_date', 'location', 'fault_ratio']},
                {'id': 'injury', 'title': '受傷情報', 'items': ['injury_details', 'treatment_period']},
                {'id': 'damages', 'title': '損害項目', 'items': ['medical_expenses', 'transportation', 'lost_income']},
                {'id': 'calculation', 'title': '慰謝料計算', 'items': ['pain_suffering', 'disability_compensation']},
                {'id': 'summary', 'title': '合計金額', 'items': ['total_amount', 'deductions']}
            ],
            'layout': {
                'margins': (20*mm, 20*mm, 20*mm, 20*mm),
                'font_sizes': {'title': 18, 'section': 14, 'content': 10},
                'colors': {'header': colors.lightblue, 'section': colors.lightgrey}
            }
        }
    
    def _create_work_accident_template(self) -> Dict[str, Any]:
        """労災事故用PDFテンプレート"""
        return {
            'name': '労災事故損害賠償計算書',
            'sections': [
                {'id': 'accident_info', 'title': '労災事故概要', 'items': ['accident_date', 'workplace', 'cause']},
                {'id': 'worker_info', 'title': '労働者情報', 'items': ['age', 'occupation', 'salary']},
                {'id': 'compensation', 'title': '労災補償', 'items': ['disability_grade', 'pension_amount']},
                {'id': 'additional', 'title': '追加補償', 'items': ['employer_liability', 'special_damages']},
                {'id': 'total', 'title': '総合計算', 'items': ['total_compensation', 'payment_schedule']}
            ],
            'layout': {
                'margins': (20*mm, 20*mm, 20*mm, 20*mm),
                'font_sizes': {'title': 18, 'section': 14, 'content': 10},
                'colors': {'header': colors.lightyellow, 'section': colors.lightgrey}
            }
        }
    
    def _create_medical_malpractice_template(self) -> Dict[str, Any]:
        """医療過誤用PDFテンプレート"""
        return {
            'name': '医療過誤損害賠償計算書',
            'sections': [
                {'id': 'medical_info', 'title': '医療事故概要', 'items': ['incident_date', 'medical_institution', 'treatment_details']},
                {'id': 'patient_info', 'title': '患者情報', 'items': ['age', 'condition_before', 'condition_after']},
                {'id': 'damages', 'title': '損害項目', 'items': ['medical_costs', 'future_care', 'lost_earnings']},
                {'id': 'evaluation', 'title': '損害評価', 'items': ['pain_suffering', 'life_impact']},
                {'id': 'conclusion', 'title': '損害額算定', 'items': ['total_damages', 'mitigation_factors']}
            ],
            'layout': {
                'margins': (20*mm, 20*mm, 20*mm, 20*mm),
                'font_sizes': {'title': 18, 'section': 14, 'content': 10},
                'colors': {'header': colors.lightcoral, 'section': colors.lightgrey}
            }
        }
    
    @monitor_performance
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """指定されたテンプレートを取得"""
        template = self.templates.get(template_name)
        if not template:
            self.logger.warning(f"テンプレート '{template_name}' が見つかりません。デフォルトテンプレートを使用します。")
            return self.templates.get('traffic_accident')  # デフォルト
        return template
    
    @monitor_performance
    def apply_template_data(self, template: Dict[str, Any], case_data: CaseData) -> Dict[str, Any]:
        """テンプレートにケースデータを適用"""
        try:
            # テンプレートデータマッピングを使用してプレースホルダーを置換
            mapping = self.report_config.template_data_mapping
            
            for section in template['sections']:
                for i, item in enumerate(section['items']):
                    if item in mapping:
                        # ケースデータから実際の値を取得して置換
                        actual_value = self._get_case_data_value(case_data, mapping[item])
                        section['items'][i] = actual_value or item
            
            return template
        except Exception as e:
            self.logger.error(f"テンプレートデータ適用エラー: {str(e)}")
            return template
    
    def _get_case_data_value(self, case_data: CaseData, field_path: str) -> Optional[str]:
        """ケースデータから指定されたフィールドの値を取得"""
        try:
            # ドット記法でネストされたフィールドにアクセス
            obj = case_data
            for field in field_path.split('.'):
                obj = getattr(obj, field, None)
                if obj is None:
                    return None
            return str(obj) if obj is not None else None
        except Exception:
            return None


class PdfReportGeneratorOptimized:
    """PDFレポート生成クラス - パフォーマンス最適化版"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.report_config = config.report
        self.styles = getSampleStyleSheet()
        self.error_handler = get_error_handler()
        self.performance_monitor = get_performance_monitor()
        self.logger = logging.getLogger(__name__)
        self.template_manager = PdfTemplateManager(self.report_config, self.logger)
        
        # パフォーマンス最適化のための設定
        self.batch_size = getattr(self.report_config, 'pdf_batch_size', 50)
        self.enable_cache = getattr(self.report_config, 'pdf_enable_cache', True)
        self.cache = {} if self.enable_cache else None
        
        self._register_fonts()
        self._initialize_styles()
        
        self.logger.info("最適化版PDFレポート生成システムを初期化しました")

    @monitor_performance
    def _register_fonts(self):
        """設定に基づいてフォントを登録する"""
        font_name_gothic = self.report_config.font_name_gothic
        font_path_gothic = self.report_config.font_path_gothic

        if not font_name_gothic or not font_path_gothic:
            self.error_handler.handle_exception(
                ConfigurationError(
                    "PDF生成に必要なゴシックフォント名またはパスが設定されていません。",
                    user_message="PDF設定でゴシックフォント名またはパスが指定されていません。設定を確認してください。",
                    severity=ErrorSeverity.HIGH,
                    context={"font_name": font_name_gothic, "font_path": font_path_gothic}
                )
            )
            self.logger.error("ゴシックフォントの設定が不完全なため、PDF生成に問題が発生する可能性があります。")
            return

        try:
            if os.path.exists(font_path_gothic):
                pdfmetrics.registerFont(TTFont(font_name_gothic, font_path_gothic))
                self.logger.info(f"フォント '{font_name_gothic}' を '{font_path_gothic}' から登録しました。")
            else:
                self.error_handler.handle_exception(
                    FileIOError(
                        f"指定されたフォントファイルが見つかりません: {font_path_gothic}",
                        user_message=f"PDF生成に必要なフォントファイル '{font_path_gothic}' が見つかりません。設定を確認してください。",
                        severity=ErrorSeverity.HIGH,
                        context={"font_name": font_name_gothic, "font_path": font_path_gothic}
                    )
                )
                self.logger.error(f"フォントファイル '{font_path_gothic}' が見つかりません。")
        except Exception as e:
            self.error_handler.handle_exception(
                FileIOError(
                    f"日本語フォント '{font_name_gothic}' の読み込みに失敗しました。'{font_path_gothic}' を確認してください。エラー: {e}",
                    user_message=f"PDF生成に必要な日本語フォント '{font_name_gothic}' が見つからないか、読み込めませんでした。PDF内の日本語が正しく表示されない可能性があります。フォントパス '{font_path_gothic}' を確認してください。",
                    severity=ErrorSeverity.MEDIUM,
                    context={"font_name": font_name_gothic, "font_path": font_path_gothic, "exception": str(e)}
                )
            )
            self.logger.warning(f"日本語フォント '{font_name_gothic}' の読み込みに失敗。PDFの日本語表示に問題が出る可能性があります。")

    @monitor_performance
    def _initialize_styles(self):
        """設定に基づいてカスタムスタイルを初期化"""
        font_name_gothic = self.report_config.font_name_gothic
        # フォントが正常に登録されたか確認し、されていなければデフォルトフォントを使用
        base_font = font_name_gothic if pdfmetrics.getFont(font_name_gothic, None) else 'Helvetica'
        
        if base_font == 'Helvetica' and font_name_gothic:
            self.logger.warning(f"指定されたフォント '{font_name_gothic}' が利用できないため、Helveticaにフォールバックします。")

        # 設定ファイルからフォントサイズを取得
        font_sizes = self.report_config.pdf_font_sizes
        
        try:
            self.styles.add(ParagraphStyle(
                name='MainTitle', 
                fontSize=font_sizes.get('title', 18),
                alignment=TA_CENTER, 
                spaceAfter=10*mm, 
                fontName=base_font, 
                leading=font_sizes.get('title', 18) + 4
            ))
            
            self.styles.add(ParagraphStyle(
                name='SubTitle', 
                fontSize=font_sizes.get('section', 14),
                alignment=TA_LEFT, 
                spaceAfter=5*mm, 
                spaceBefore=5*mm, 
                fontName=base_font, 
                leading=font_sizes.get('section', 14) + 4
            ))
            
            self.styles.add(ParagraphStyle(
                name='Normal_jp', 
                fontSize=font_sizes.get('content', 10),
                alignment=TA_LEFT, 
                spaceAfter=3*mm, 
                fontName=base_font, 
                leading=font_sizes.get('content', 10) + 2
            ))
            
            self.styles.add(ParagraphStyle(
                name='TableText', 
                fontSize=font_sizes.get('table', 9),
                alignment=TA_CENTER, 
                fontName=base_font,
                leading=font_sizes.get('table', 9) + 1
            ))
            
            self.logger.info("カスタムスタイルを初期化しました")
            
        except Exception as e:
            self.logger.error(f"スタイル初期化エラー: {str(e)}")
            # デフォルトスタイルにフォールバック
            self._initialize_default_styles(base_font)

    def _initialize_default_styles(self, base_font: str):
        """デフォルトスタイルで初期化"""
        self.styles.add(ParagraphStyle(name='MainTitle', fontSize=18, alignment=TA_CENTER, spaceAfter=10*mm, fontName=base_font, leading=22))
        self.styles.add(ParagraphStyle(name='SubTitle', fontSize=14, alignment=TA_LEFT, spaceAfter=5*mm, spaceBefore=5*mm, fontName=base_font, leading=18))
        self.styles.add(ParagraphStyle(name='Normal_jp', fontSize=10, alignment=TA_LEFT, spaceAfter=3*mm, fontName=base_font, leading=12))
        self.styles.add(ParagraphStyle(name='TableText', fontSize=9, alignment=TA_CENTER, fontName=base_font, leading=10))

    @monitor_performance
    def create_compensation_report(self, case_data: CaseData, results: Dict[str, CalculationResult], 
                                 template_type: str = 'traffic_accident', 
                                 filename: Optional[str] = None) -> str:
        """
        損害賠償計算書PDFを生成する - パフォーマンス最適化版
        
        Args:
            case_data: ケースデータ
            results: 計算結果
            template_type: テンプレートタイプ ('traffic_accident', 'work_accident', 'medical_malpractice')
            filename: 出力ファイル名（省略時は自動生成）
            
        Returns:
            str: 生成されたPDFファイルのパス
        """
        try:
            self.performance_monitor.start_timing('pdf_generation_total')
            
            # テンプレート取得と適用
            template = self.template_manager.get_template(template_type)
            if template:
                template = self.template_manager.apply_template_data(template, case_data)
            
            # 出力ファイル名の決定
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"compensation_report_{template_type}_{timestamp}.pdf"
            
            output_path = os.path.join(self.report_config.output_directory, filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # PDF文書作成
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=25*mm,
                bottomMargin=25*mm
            )
            
            # 文書の要素を構築
            story = []
            
            # ヘッダー部分
            story.extend(self._create_header_section(case_data, template))
            
            # メイン計算結果セクション
            story.extend(self._create_calculation_sections(case_data, results, template))
            
            # サマリーセクション
            story.extend(self._create_summary_section(results, template))
            
            # フッター情報
            story.extend(self._create_footer_section())
            
            # PDF生成
            self.performance_monitor.start_timing('pdf_build')
            doc.build(story)
            self.performance_monitor.end_timing('pdf_build')
            
            self.performance_monitor.end_timing('pdf_generation_total')
            
            self.logger.info(f"PDF レポート生成完了: {output_path}")
            
            # パフォーマンス統計をログ出力
            stats = self.performance_monitor.get_statistics()
            if 'pdf_generation_total' in stats:
                duration = stats['pdf_generation_total']['total_time']
                self.logger.info(f"PDF生成時間: {duration:.2f}秒")
            
            return output_path
            
        except Exception as e:
            self.performance_monitor.end_timing('pdf_generation_total')
            error_msg = f"PDF レポート生成中にエラーが発生しました: {str(e)}"
            self.error_handler.handle_exception(
                CompensationSystemError(
                    error_msg,
                    user_message="PDFレポートの生成に失敗しました。設定とデータを確認してください。",
                    severity=ErrorSeverity.HIGH,
                    context={
                        'case_data': str(case_data),
                        'template_type': template_type,
                        'filename': filename,
                        'exception': str(e),
                        'traceback': traceback.format_exc()
                    }
                )
            )
            self.logger.error(f"PDF生成エラー: {error_msg}")
            raise

    @monitor_performance
    def _create_header_section(self, case_data: CaseData, template: Optional[Dict[str, Any]]) -> List:
        """ヘッダーセクションを作成"""
        story = []
        
        # タイトル
        title = template['name'] if template else "損害賠償計算書"
        story.append(Paragraph(title, self.styles['MainTitle']))
        story.append(Spacer(1, 10*mm))
        
        # ロゴ挿入（設定されている場合）
        if hasattr(self.report_config, 'company_logo_path') and self.report_config.company_logo_path:
            logo_path = self.report_config.company_logo_path
            if os.path.exists(logo_path):
                try:
                    logo = Image(logo_path, width=50*mm, height=20*mm)
                    story.append(logo)
                    story.append(Spacer(1, 5*mm))
                except Exception as e:
                    self.logger.warning(f"ロゴ挿入エラー: {str(e)}")
        
        # 基本情報テーブル
        basic_info_data = [
            ['作成日時', datetime.now().strftime("%Y年%m月%d日 %H:%M")],
            ['事件番号', getattr(case_data, 'case_number', '未設定')],
            ['依頼者名', getattr(case_data, 'client_name', '未設定')],
            ['作成者', getattr(self.report_config, 'creator_name', '未設定')]
        ]
        
        basic_info_table = Table(basic_info_data, colWidths=[40*mm, 80*mm])
        basic_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self.report_config.font_name_gothic or 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        
        story.append(basic_info_table)
        story.append(Spacer(1, 10*mm))
        
        return story

    @monitor_performance
    def _create_calculation_sections(self, case_data: CaseData, results: Dict[str, CalculationResult], 
                                   template: Optional[Dict[str, Any]]) -> List:
        """計算結果セクションを作成"""
        story = []
        
        # バッチ処理でセクションを効率的に作成
        sections_to_process = []
        if template and 'sections' in template:
            sections_to_process = template['sections'][1:-1]  # ヘッダーとサマリーを除く
        
        if not sections_to_process:
            # デフォルトセクション
            sections_to_process = [
                {'id': 'main_calculation', 'title': '損害賠償計算結果', 'items': list(results.keys())}
            ]
        
        # バッチ処理で複数セクションを一度に処理
        for i in range(0, len(sections_to_process), self.batch_size):
            batch_sections = sections_to_process[i:i + self.batch_size]
            story.extend(self._process_sections_batch(batch_sections, results))
        
        return story

    def _process_sections_batch(self, sections: List[Dict[str, Any]], results: Dict[str, CalculationResult]) -> List:
        """セクションのバッチ処理"""
        story = []
        
        for section in sections:
            # セクションタイトル
            story.append(Paragraph(section['title'], self.styles['SubTitle']))
            story.append(Spacer(1, 5*mm))
            
            # セクション内容
            section_data = []
            for item in section.get('items', []):
                if item in results:
                    result = results[item]
                    formatted_amount = self._format_currency(result.amount)
                    section_data.append([
                        result.item_name or item,
                        formatted_amount,
                        result.calculation_method or '標準計算'
                    ])
            
            if section_data:
                # テーブルヘッダー
                section_data.insert(0, ['項目', '金額', '計算方法'])
                
                section_table = Table(section_data, colWidths=[60*mm, 40*mm, 60*mm])
                section_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (1, -1), 'RIGHT'),  # 金額は右寄せ
                    ('FONTNAME', (0, 0), (-1, -1), self.report_config.font_name_gothic or 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # ヘッダー背景
                ]))
                
                story.append(section_table)
                story.append(Spacer(1, 8*mm))
        
        return story

    @monitor_performance
    def _create_summary_section(self, results: Dict[str, CalculationResult], 
                              template: Optional[Dict[str, Any]]) -> List:
        """サマリーセクションを作成"""
        story = []
        
        story.append(Paragraph("計算結果サマリー", self.styles['SubTitle']))
        story.append(Spacer(1, 5*mm))
        
        # 合計金額計算
        total_amount = sum(result.amount for result in results.values() if result.amount > 0)
        deduction_amount = sum(abs(result.amount) for result in results.values() if result.amount < 0)
        net_amount = total_amount - deduction_amount
        
        summary_data = [
            ['項目', '金額'],
            ['損害賠償額合計', self._format_currency(total_amount)],
            ['控除額合計', self._format_currency(deduction_amount)],
            ['差引損害賠償額', self._format_currency(net_amount)]
        ]
        
        summary_table = Table(summary_data, colWidths=[80*mm, 50*mm])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), self.report_config.font_name_gothic or 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightyellow),  # 最終行を強調
            ('FONTSIZE', (0, -1), (-1, -1), 12),  # 最終行のフォントサイズを大きく
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 10*mm))
        
        return story

    def _create_footer_section(self) -> List:
        """フッターセクションを作成"""
        story = []
        
        # 注意事項
        notes = [
            "※ この計算書は概算です。実際の支払額は示談交渉や裁判の結果により異なる場合があります。",
            "※ 計算根拠については別途詳細資料をご参照ください。",
            "※ 法改正等により計算基準が変更される場合があります。"
        ]
        
        story.append(Paragraph("注意事項", self.styles['SubTitle']))
        for note in notes:
            story.append(Paragraph(note, self.styles['Normal_jp']))
        
        story.append(Spacer(1, 10*mm))
        
        # 作成者情報
        if hasattr(self.report_config, 'creator_name') and self.report_config.creator_name:
            creator_info = f"作成者: {self.report_config.creator_name}"
            if hasattr(self.report_config, 'organization_name') and self.report_config.organization_name:
                creator_info += f" ({self.report_config.organization_name})"
            story.append(Paragraph(creator_info, self.styles['Normal_jp']))
        
        return story

    def _format_currency(self, amount: Decimal) -> str:
        """通貨フォーマット"""
        return f"¥{amount:,.0f}"

    @monitor_performance
    def generate_batch_reports(self, case_list: List[Dict], template_type: str = 'traffic_accident') -> List[str]:
        """複数ケースのバッチレポート生成"""
        generated_files = []
        
        try:
            self.performance_monitor.start_timing('batch_pdf_generation')
            
            for i, case_info in enumerate(case_list):
                try:
                    case_data = case_info['case_data']
                    results = case_info['results']
                    filename = f"batch_report_{i+1:03d}_{template_type}.pdf"
                    
                    output_path = self.create_compensation_report(
                        case_data, results, template_type, filename
                    )
                    generated_files.append(output_path)
                    
                except Exception as e:
                    self.logger.error(f"バッチ処理 {i+1} でエラー: {str(e)}")
                    continue
            
            self.performance_monitor.end_timing('batch_pdf_generation')
            
            # バッチ処理統計
            stats = self.performance_monitor.get_statistics()
            if 'batch_pdf_generation' in stats:
                total_time = stats['batch_pdf_generation']['total_time']
                avg_time = total_time / len(case_list) if case_list else 0
                self.logger.info(f"バッチPDF生成完了: {len(generated_files)}件, 総時間: {total_time:.2f}秒, 平均: {avg_time:.2f}秒/件")
            
            return generated_files
            
        except Exception as e:
            self.performance_monitor.end_timing('batch_pdf_generation')
            self.logger.error(f"バッチPDF生成エラー: {str(e)}")
            raise
