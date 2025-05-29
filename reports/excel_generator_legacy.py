#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel・帳票出力エンジン
プロフェッショナルな書類作成機能

改善点:
- 設定システムとの統合
- エラーハンドリングの強化
- パフォーマンス最適化
- テンプレート機能の充実
- データ検証の強化
"""

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference, LineChart, PieChart
from openpyxl.drawing.image import Image
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
import os
import logging
import json
from pathlib import Path
from dataclasses import asdict

from models.case_data import CaseData
from calculation.compensation_engine import CalculationResult
from config.app_config import AppConfig, ReportConfig, get_config_manager
from utils.error_handler import ErrorHandler, get_error_handler, CompensationSystemError, ErrorCategory, ErrorSeverity, FileIOError, ConfigurationError
from utils.performance_monitor import monitor_performance, get_performance_monitor

class ExcelReportGenerator:
    """Excel帳票生成クラス - 統合設定システム対応版"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        self.report_config = self.config.report # report_config を追加
        self.logger = logging.getLogger(__name__)
        self.error_handler = get_error_handler() # 追加
          # テンプレートディレクトリの設定
        try:
            # report_config からExcelテンプレートのパスを取得するように変更
            if self.report_config.excel_template_path:
                excel_template_file = Path(self.report_config.excel_template_path)
                self.template_dir = excel_template_file.parent
            else:
                # フォールバックとしてUI設定のexport_pathを使用
                self.template_dir = Path(self.config.ui.export_path) / "templates/excel"
            self.template_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.error_handler.handle_exception(
                FileIOError(f"テンプレートディレクトリの作成に失敗しました: {self.template_dir}, {e}",
                            user_message="レポートテンプレート用ディレクトリの準備中にエラーが発生しました。",
                            context={"path": str(self.template_dir)})
            )
            # 致命的なエラーの場合、ここで処理を中断するか、デフォルトパスを使うなどのフォールバックが必要
            # ここでは、エラーハンドラに任せ、処理は続行するが、テンプレート機能は使えない可能性を示唆
            self.template_dir = Path(".") / "templates"  # フォールバックパス
            self.logger.warning(f"テンプレートディレクトリの作成に失敗したため、カレントディレクトリ ({self.template_dir}) を使用します。")
        
        self.setup_styles()
        # self.setup_templates() # setup_templates は TemplateManager に移譲するので削除またはコメントアウト
        self.logger.info("Excel帳票生成システムを初期化しました")
    
    def _initialize_styles(self):
        """Excelスタイル設定の初期化（設定ファイルから読み込み）"""
        try:
            # カラースキーム
            colors = self.report_config.excel_color_scheme
            default_font = self.config.ui.font_family
            
            # フォント設定
            self.fonts = {
                'title': Font(name=default_font, size=18, bold=True, color=colors.get('header_text', 'FFFFFF')),
                'header': Font(name=default_font, size=14, bold=True, color=colors.get('header_text', 'FFFFFF')),
                'subtitle': Font(name=default_font, size=12, bold=True, color=colors.get('body_text', '000000')),
                'body': Font(name=default_font, size=10, color=colors.get('body_text', '000000')),
                'number': Font(name=default_font, size=10, color=colors.get('body_text', '000000')),
                'small': Font(name=default_font, size=8, color=colors.get('body_text', '000000')),
                'money': Font(name=default_font, size=12, bold=True, color='C55A5A'),
                'important': Font(name=default_font, size=11, bold=True, color='E74C3C')
            }
            
            # 塗りつぶし設定
            self.fills = {
                'header': PatternFill(start_color=colors.get('header_bg', '4472C4'), 
                                    end_color=colors.get('header_bg', '4472C4'), 
                                    fill_type='solid'),
                'subheader': PatternFill(start_color=colors.get('subheader_bg', '8DB4E2'), 
                                       end_color=colors.get('subheader_bg', '8DB4E2'), 
                                       fill_type='solid'),
                'amount': PatternFill(start_color=colors.get('amount_bg', 'FFF2CC'), 
                                    end_color=colors.get('amount_bg', 'FFF2CC'), 
                                    fill_type='solid'),
                'total': PatternFill(start_color=colors.get('total_bg', 'D5E8D4'), 
                                   end_color=colors.get('total_bg', 'D5E8D4'), 
                                   fill_type='solid')
            }
            
            # 罫線設定
            self.borders = {
                'thin_all': Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin')),
                'medium_all': Border(left=Side(style='medium'), right=Side(style='medium'),
                                   top=Side(style='medium'), bottom=Side(style='medium')),
                'thick_bottom': Border(bottom=Side(style='thick'))
            }
            
            # 配置設定
            self.alignments = {
                'left': Alignment(horizontal='left', vertical='center'),
                'center': Alignment(horizontal='center', vertical='center'),
                'right': Alignment(horizontal='right', vertical='center'),
                'center_wrap': Alignment(horizontal='center', vertical='center', wrap_text=True)
            }
            
            # 列幅と行高設定
            self.column_widths = self.report_config.excel_column_widths
            self.row_heights = self.report_config.excel_row_heights
            
            self.logger.debug("Excelスタイル設定を初期化しました")
        except Exception as e:
            self.error_handler.handle_exception(
                ConfigurationError(f"Excelスタイル設定の初期化に失敗しました: {e}",
                                   user_message="Excelレポートのスタイル設定の読み込みに失敗しました。",
                                   context={"error_details": str(e)})
            )
            # フォールバック: デフォルトスタイルを設定
            self._set_default_styles()
    
    def _set_default_styles(self):
        """デフォルトスタイルの設定（フォールバック用）"""
        default_font = self.config.ui.font_family
        
        # フォント
        self.fonts = {
            'title': Font(name=default_font, size=16, bold=True, color='1F4E79'),
            'subtitle': Font(name=default_font, size=14, bold=True, color='2E75B6'),
            'header': Font(name=default_font, size=12, bold=True, color='FFFFFF'),
            'body': Font(name=default_font, size=11),
            'small': Font(name=default_font, size=10, color='666666'),
            'number': Font(name=default_font, size=11, bold=True),
            'money': Font(name=default_font, size=12, bold=True, color='C55A5A'),
            'important': Font(name=default_font, size=11, bold=True, color='E74C3C')
        }
        
        # 罫線
        self.borders = {
            'thin_all': Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            ),
            'thick_bottom': Border(bottom=Side(style='thick')),
            'medium_all': Border(
                left=Side(style='medium'), right=Side(style='medium'),
                top=Side(style='medium'), bottom=Side(style='medium')
            )
        }
        
        # 塗りつぶし
        self.fills = {
            'header': PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid'),
            'subheader': PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid'),
            'total': PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid'),
            'amount': PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
        }
        
        # 配置
        self.alignments = {
            'center': Alignment(horizontal='center', vertical='center'),
            'left': Alignment(horizontal='left', vertical='center'),
            'right': Alignment(horizontal='right', vertical='center'),
            'center_wrap': Alignment(horizontal='center', vertical='center', wrap_text=True)
        }
        
        # デフォルト列幅・行高
        self.column_widths = {"A": 20.0, "B": 15.0, "C": 40.0, "D": 25.0}
        self.row_heights = {"header": 25.0, "subheader": 20.0, "data": 18.0, "footer": 15.0}
      def create_compensation_report(self, case_data: CaseData, results: Dict[str, CalculationResult], 
                                 output_filename: str, template_type: str = "default") -> bool:
        """損害賠償計算書の作成 - テンプレート選択対応"""
        try:
            self.logger.info(f"損害賠償計算書の作成を開始します: {output_filename}")
            
            # テンプレートが指定されている場合は適用、そうでなければ新規作成
            if self.report_config.enable_template_customization and template_type != "none":
                wb = self.template_manager.apply_template(template_type, case_data)
                if wb is None:
                    # テンプレート適用に失敗した場合は新規作成
                    self.logger.warning(f"テンプレート '{template_type}' の適用に失敗したため、新規作成します")
                    wb = openpyxl.Workbook()
            else:
                wb = openpyxl.Workbook()
            
            # メインシートの作成
            ws = wb.active
            ws.title = "損害賠償計算書"
            
            # 設定から表示項目を取得
            report_items = self.report_config.excel_report_items
            
            # シート作成
            self._create_calculation_sheet(ws, case_data, results, report_items)
            
            # 追加シート作成（設定により制御）
            if "detailed_calculation_table" in report_items:
                self._create_detail_sheet(wb, case_data, results)
            
            if "charts" in report_items and self.report_config.include_charts_in_excel:
                self._create_chart_sheet(wb, results)
            
            if "reference_materials" in report_items:
                self._create_reference_sheet(wb, case_data)
            
            # 列幅の調整（設定から読み込み）
            self._apply_column_settings(ws)
            
            # ファイル保存
            output_path = self.output_dir / output_filename
            if not output_filename.endswith('.xlsx'):
                output_path = output_path.with_suffix('.xlsx')
            
            # 会社ロゴの挿入（設定されている場合）
            if self.report_config.company_logo_path and "logo" in report_items:
                self._insert_company_logo(ws)
            
            # Excelファイルのプロパティ設定
            self._set_excel_properties(wb, case_data)
            
            wb.save(output_path)
            self.logger.info(f"Excel帳票を正常に作成しました: {output_path}")
            return True
            
        except Exception as e:
            self.error_handler.handle_exception(
                FileIOError(f"Excel帳票の作成に失敗しました: {e}",
                            user_message="Excel損害賠償計算書の作成中にエラーが発生しました。",
                            context={"filename": output_filename, "template_type": template_type})
            )
            return False
        try:
            # 出力パスを report_config から取得
            output_dir = Path(self.report_config.default_output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename # 完全な出力パスを作成

            # 含める項目のリストを取得
            report_items = self.report_config.excel_report_items or []
            self.logger.info(f"Excel レポート生成項目: {report_items}")

            # テンプレートを使用するかどうか
            wb = None
            if self.report_config.excel_template_path and Path(self.report_config.excel_template_path).exists():
                try:
                    wb = openpyxl.load_workbook(self.report_config.excel_template_path)
                    self.logger.info(f"Excelテンプレートを読み込みました: {self.report_config.excel_template_path}")
                    # テンプレートを使用する場合、既存のシートをクリアするか、特定のシートに書き込むかなどの処理が必要
                    # ここでは、最初のシートをアクティブにして使用する想定（要件に応じて変更）
                    if wb.sheetnames:
                        ws_calc = wb.active # 既存のシートを使用
                        ws_calc.title = "損害賠償計算書" # 必要に応じてタイトル変更
                        # 既存の内容をクリアするなどの処理が必要な場合がある
                        # for row in ws_calc.iter_rows():
                        #     for cell in row:
                        #         cell.value = None
                    else:
                        ws_calc = wb.create_sheet("損害賠償計算書") # シートがない場合は作成

                    # 会社ロゴの挿入 (設定されていれば) - "logo" または "header" 項目が含まれている場合
                    if ("header" in report_items or "logo" in report_items) and \
                       self.report_config.company_logo_path and Path(self.report_config.company_logo_path).exists():
                        try:
                            img = Image(self.report_config.company_logo_path)
                            # ロゴのサイズや位置を調整 (例: A1セルに配置)
                            img.height = 50 # 高さを調整
                            img.width = 150 # 幅を調整
                            ws_calc.add_image(img, 'A1') # 位置を調整
                            self.logger.info(f"会社ロゴを挿入しました: {self.report_config.company_logo_path}")
                        except Exception as img_e:
                            self.error_handler.handle_exception(
                                FileIOError(f"会社ロゴの挿入に失敗しました: {img_e}",
                                            user_message="レポートへの会社ロゴの挿入中にエラーが発生しました。",
                                            context={"logo_path": self.report_config.company_logo_path, "details": str(img_e)})
                            )

                except Exception as template_e:
                    self.error_handler.handle_exception(
                        FileIOError(f"Excelテンプレートの読み込みに失敗しました: {template_e}",
                                    user_message="Excelレポートテンプレートの読み込み中にエラーが発生しました。標準フォーマットで作成します。",
                                    context={"template_path": self.report_config.excel_template_path, "details": str(template_e)})
                    )
                    wb = None # テンプレート読み込み失敗時は新規作成
            
            if wb is None: # テンプレートを使用しない、または読み込み失敗の場合
                wb = openpyxl.Workbook()
            
            # 設定に基づいてシートを生成
            # メインの計算書シート (header, case_summary, basic_info, medical_info, income_info, calculation_summary_table を含む)
            main_sheet_items = ["header", "case_summary", "basic_info", "medical_info", "income_info", "calculation_summary_table"]
            if any(item in report_items for item in main_sheet_items):
                self._create_calculation_sheet(wb, case_data, results, report_items)
            
            # 詳細計算シート (detailed_calculation_table を含む)
            if "detailed_calculation_table" in report_items:
                self._create_detail_sheet(wb, case_data, results)
            
            # グラフシート (charts を含み、設定でも有効)
            if "charts" in report_items and self.report_config.include_charts_in_excel:
                self._create_chart_sheet(wb, results)
            
            # 付属資料シート (footer や reference を含む)
            if "footer" in report_items or "reference" in report_items:
                self._create_reference_sheet(wb, case_data)
            
            # 不要なデフォルトシートを削除 (テンプレート未使用時のみ、またはテンプレート構造に応じて調整)
            if not self.report_config.excel_template_path or not Path(self.report_config.excel_template_path).exists():
                if 'Sheet' in wb.sheetnames and len(wb.sheetnames) > 1: # 他にシートがあればデフォルトシートを削除
                    if wb['Sheet'] is not wb.active: # アクティブシートでなければ削除
                         wb.remove(wb['Sheet'])

            # 作成者情報をプロパティに設定
            wb.properties.creator = self.report_config.default_author
            wb.properties.lastModifiedBy = self.report_config.default_author
            wb.properties.title = f"損害賠償計算書 - {case_data.case_number or '新規案件'}"
            wb.properties.subject = "損害賠償計算"
            
            wb.save(output_path) # 修正された出力パスを使用
            self.logger.info(f"Excelレポートが正常に出力されました: {output_path}") # 修正
            return True
            
        except openpyxl.utils.exceptions.IllegalCharacterError as e: # 追加
            self.error_handler.handle_exception( # 追加
                FileIOError(f"Excel出力エラー: 不正な文字が含まれています。 {e}", # 追加
                            user_message="レポート生成中にエラーが発生しました。ファイル名やデータに不正な文字が含まれている可能性があります。", # 追加
                            context={"output_path": output_path, "details": str(e)}), # 追加
                # severity=ErrorSeverity.HIGH
            ) # 追加
            return False # 追加
        except Exception as e:
            # print(f\"Excel出力エラー: {e}\") # 既存のprintは削除またはloggerに置き換え
            self.error_handler.handle_exception( # 修正
                CompensationSystemError(f"Excelレポート生成中に予期せぬエラーが発生しました: {e}", # 修正
                                        category=ErrorCategory.FILE_IO, # 修正
                                        severity=ErrorSeverity.HIGH, # 修正
                                        user_message="レポート生成中に予期しないエラーが発生しました。システム管理者にお問い合わせください。", # 修正
                                        context={"output_path": output_path, "exception_details": str(e)}), # 修正
            ) # 修正
            return False
    
    def _create_calculation_sheet(self, wb: openpyxl.Workbook, case_data: CaseData, 
                                results: Dict[str, CalculationResult], report_items: List[str] = None):
        """計算書シートの作成 - カスタマイズ可能な項目設定対応"""
        ws = wb.active
        ws.title = "損害賠償計算書"
        
        if report_items is None:
            report_items = []  # デフォルトは空リスト（すべて表示）
        
        current_row = 1
        
        # ヘッダー部分 (header項目に含まれる場合)
        if "header" in report_items or not report_items:  # 項目指定なしの場合もヘッダーは表示
            current_row = self._create_header(ws, case_data, current_row)
            current_row += 2  # スペース
        
        # 案件情報 (case_summary, basic_info, medical_info, income_info に対応)
        sections_to_create = []
        if "case_summary" in report_items or "basic_info" in report_items:
            sections_to_create.append("basic_info")
        if "medical_info" in report_items:
            sections_to_create.append("medical_info")
        if "income_info" in report_items:
            sections_to_create.append("income_info")
        
        # 項目指定なしの場合はすべてのセクションを作成
        if not report_items:
            sections_to_create = ["basic_info", "medical_info", "income_info"]
        
        for section in sections_to_create:
            current_row = self._create_case_info_section(ws, case_data, section, current_row)
            current_row += 2  # セクション間のスペース
        
        # 計算結果 (calculation_summary_table に対応)
        if "calculation_summary_table" in report_items or not report_items:
            current_row = self._create_calculation_results(ws, results, current_row)
            current_row += 2
        
        # フッター (footer項目に含まれる場合)
        if "footer" in report_items or not report_items:
            self._create_footer(ws, current_row)
        
        # 列幅調整
        self._adjust_column_widths(ws)
    
    def _create_header(self, ws, case_data: CaseData, start_row: int = 1) -> int:
        """ヘッダー部分の作成 - 開始行を指定可能"""
        row = start_row
        
        # タイトル
        # ws['A1'] = "損害賠償計算書" # ロゴを挿入する場合、この行は調整または削除
        # ws['A1'].font = self.fonts['title']
        # ws['A1'].alignment = self.alignments['center']
        # ws.merge_cells('A1:H1')
        # ロゴを挿入する場合、タイトルは別の位置に配置するか、ロゴと共存させる
        # 例：ロゴがA1-C2あたりにあるとして、タイトルをD1に配置
        title_cell = f'D{row}' # ロゴの配置によって調整
        if not (self.report_config.company_logo_path and Path(self.report_config.company_logo_path).exists()):
            # ロゴがない場合は従来通りA1にタイトル
            title_cell = f'A{row}'
            ws[title_cell] = "損害賠償計算書"
            ws[title_cell].font = self.fonts['title']
            ws[title_cell].alignment = self.alignments['center']
            ws.merge_cells(f'{title_cell}:{get_column_letter(ws.max_column)}{row}') #最終列まで結合
        else:
            # ロゴがある場合は、ロゴの隣などにタイトルを配置
            # この例では、ロゴがA1にあると仮定し、タイトルをC1あたりから開始
            # 実際のロゴサイズや配置に応じて調整が必要
            ws.merge_cells(f'C{row}:H{row}') # ロゴの右側のセルを結合してタイトル領域に
            title_cell_obj = ws[f'C{row}']
            title_cell_obj.value = "損害賠償計算書"
            title_cell_obj.font = self.fonts['title']
            title_cell_obj.alignment = self.alignments['center']

        row += 1

        # 作成日
        ws[f'G{row}'] = "作成日:"
        ws[f'H{row}'] = datetime.now().strftime("%Y年%m月%d日")
        ws[f'G{row}'].font = self.fonts['body']
        ws[f'H{row}'].font = self.fonts['body']
        ws[f'G{row}'].alignment = self.alignments['right']
        ws[f'H{row}'].alignment = self.alignments['right']
        
        row += 1
        
        # 案件番号
        ws[f'A{row}'] = f"案件番号: {case_data.case_number}"
        ws[f'A{row}'].font = self.fonts['subtitle']
        ws.merge_cells(f'A{row}:D{row}')
        
        # 依頼者名
        ws[f'E{row}'] = f"依頼者: {case_data.person_info.name} 様"
        ws[f'E{row}'].font = self.fonts['subtitle']
        ws.merge_cells(f'E{row}:H{row}')
        
        # 罫線
        for header_row in range(start_row, row + 1):
            for col in range(1, 9):
                cell = ws.cell(row=header_row, column=col)
                cell.border = self.borders['thin_all']
        
        return row
    
    def _create_case_info_section(self, ws, case_data: CaseData, section_type: str, start_row: int) -> int:
        """案件情報セクションの作成 - セクション別対応"""
        row = start_row
        
        if section_type == "basic_info":
            # セクションタイトル
            ws[f'A{row}'] = "【基本情報】"
            ws[f'A{row}'].font = self.fonts['header']
            ws[f'A{row}'].fill = self.fills['subheader']
            ws.merge_cells(f'A{row}:H{row}')
            row += 1
            
            # 基本情報テーブル
            info_data = [
                ("事故発生日", case_data.accident_info.accident_date.strftime("%Y年%m月%d日") if case_data.accident_info.accident_date else "未入力"),
                ("被害者年齢", f"{case_data.person_info.age}歳"),
                ("職業", case_data.person_info.occupation),
                ("性別", case_data.person_info.gender),
                ("過失割合", f"{case_data.person_info.fault_percentage}%"),
                ("年収", f"{case_data.person_info.annual_income:,}円"),
            ]
            row = self._create_info_table(ws, info_data, row)
            
        elif section_type == "medical_info":
            # セクションタイトル
            ws[f'A{row}'] = "【医療情報】"
            ws[f'A{row}'].font = self.fonts['header']
            ws[f'A{row}'].fill = self.fills['subheader']
            ws.merge_cells(f'A{row}:H{row}')
            row += 1
            
            # 医療情報テーブル
            med_info = case_data.medical_info
            info_data = [
                ("症状固定日", case_data.accident_info.symptom_fixed_date.strftime("%Y年%m月%d日") if case_data.accident_info.symptom_fixed_date else "未入力"),
                ("入院期間", f"{med_info.hospital_months}ヶ月" if med_info.hospital_months else "なし"),
                ("通院期間", f"{med_info.outpatient_months}ヶ月" if med_info.outpatient_months else "なし"),
                ("実通院日数", f"{med_info.actual_outpatient_days}日" if med_info.actual_outpatient_days else "なし"),
                ("むちうち等", "該当" if med_info.is_whiplash else "非該当"),
                ("後遺障害等級", f"第{med_info.disability_grade}級" if med_info.disability_grade and med_info.disability_grade > 0 else "なし"),
            ]
            row = self._create_info_table(ws, info_data, row)
            
            # 後遺障害詳細（別行）
            if med_info.disability_details:
                ws[f'A{row}'] = "後遺障害詳細"
                ws[f'B{row}'] = med_info.disability_details
                ws[f'A{row}'].font = self.fonts['body']
                ws[f'B{row}'].font = self.fonts['body']
                ws[f'A{row}'].fill = self.fills['subheader']
                ws.merge_cells(f'B{row}:H{row}')
                
                # 罫線
                for col in range(1, 9):
                    ws.cell(row=row, column=col).border = self.borders['thin_all']
                row += 1
            
        elif section_type == "income_info":
            # セクションタイトル
            ws[f'A{row}'] = "【収入・損害情報】"
            ws[f'A{row}'].font = self.fonts['header']
            ws[f'A{row}'].fill = self.fills['subheader']
            ws.merge_cells(f'A{row}:H{row}')
            row += 1
            
            # 収入情報テーブル
            inc_info = case_data.income_info
            info_data = [
                ("休業日数", f"{inc_info.lost_work_days}日" if inc_info.lost_work_days else "なし"),
                ("日額基礎収入", f"{inc_info.daily_income:,}円" if inc_info.daily_income else "未設定"),
                ("基礎年収（逸失利益用）", f"{inc_info.base_annual_income:,}円" if inc_info.base_annual_income else "未設定"),
                ("労働能力喪失期間", f"{inc_info.loss_period_years}年" if inc_info.loss_period_years else "未設定"),
                ("就労可能年数上限", f"{case_data.person_info.retirement_age}歳" if case_data.person_info.retirement_age else "未設定"),
            ]
            row = self._create_info_table(ws, info_data, row)
        
        return row
    
    def _create_info_table(self, ws, info_data: List[tuple], start_row: int) -> int:
        """情報テーブルの作成（共通処理）"""
        row = start_row
        
        for i, (label, value) in enumerate(info_data):
            col_offset = (i % 2) * 4  # 2列レイアウト
            if i % 2 == 0:
                row += 1
            
            ws.cell(row=row, column=1 + col_offset, value=label)
            ws.cell(row=row, column=2 + col_offset, value=value)
            
            # スタイル適用
            ws.cell(row=row, column=1 + col_offset).font = self.fonts['body']
            ws.cell(row=row, column=2 + col_offset).font = self.fonts['body']
            ws.cell(row=row, column=1 + col_offset).fill = self.fills['subheader']
            
            # 罫線
            for col in range(1 + col_offset, 3 + col_offset):
                ws.cell(row=row, column=col).border = self.borders['thin_all']
        
        return row + 1  # 次の行を返す

    def _create_calculation_results(self, ws, results: Dict[str, CalculationResult], start_row: int) -> int:
        """計算結果部分の作成 - 現在行を受け取り、次の行を返す"""
        row = start_row
        
        # セクションタイトル
        ws[f'A{row}'] = "【損害賠償額計算結果】"
        ws[f'A{row}'].font = self.fonts['header']
        ws[f'A{row}'].fill = self.fills['subheader']
        ws.merge_cells(f'A{row}:H{row}')
        row += 1
        
        # テーブルヘッダー
        headers = ["損害項目", "金額", "計算根拠", "法的根拠"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = self.fonts['header']
            cell.fill = self.fills['header']
            cell.font = Font(name='Meiryo UI', size=12, bold=True, color='FFFFFF')
            cell.alignment = self.alignments['center']
            cell.border = self.borders['thin_all']
        
        # 列幅設定
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 40
        ws.column_dimensions['D'].width = 25
        
        row += 1
        
        # 各損害項目
        total_amount = Decimal('0')
        for key, result in results.items():
            if key == 'summary':  # 合計は最後に表示
                continue
                
            ws.cell(row=row, column=1, value=result.item_name)
            ws.cell(row=row, column=2, value=f"¥{result.amount:,}")
            ws.cell(row=row, column=3, value=result.calculation_details)
            ws.cell(row=row, column=4, value=result.legal_basis)
            
            # スタイル適用
            ws.cell(row=row, column=1).font = self.fonts['body']
            ws.cell(row=row, column=2).font = self.fonts['number']
            ws.cell(row=row, column=2).alignment = self.alignments['right']
            ws.cell(row=row, column=3).font = self.fonts['small']
            ws.cell(row=row, column=3).alignment = self.alignments['left']
            ws.cell(row=row, column=4).font = self.fonts['small']
            
            # 金額セルの背景色
            if result.amount > 0:
                ws.cell(row=row, column=2).fill = self.fills['amount']
            
            # 罫線
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = self.borders['thin_all']
            
            total_amount += result.amount
            row += 1
        
        # 合計行
        if 'summary' in results:
            summary = results['summary']
            ws.cell(row=row, column=1, value="【総合計】")
            ws.cell(row=row, column=2, value=f"¥{summary.amount:,}")
            
            # 合計行のスタイル
            ws.cell(row=row, column=1).font = self.fonts['header']
            ws.cell(row=row, column=2).font = Font(name='Meiryo UI', size=14, bold=True)
            ws.cell(row=row, column=2).alignment = self.alignments['right']
            
            for col in range(1, 3):
                ws.cell(row=row, column=col).fill = self.fills['total']
                ws.cell(row=row, column=col).border = self.borders['medium_all']
            row += 1
        
        return row

    def _create_detail_sheet(self, wb: openpyxl.Workbook, case_data: CaseData, 
                           results: Dict[str, CalculationResult]):
        """詳細シートの作成"""
        ws = wb.create_sheet("計算詳細")
        
        row = 1
        
        # 各項目の詳細計算
        for key, result in results.items():
            if key == 'summary':
                continue
            
            # 項目タイトル
            ws.cell(row=row, column=1, value=f"【{result.item_name}】")
            ws.cell(row=row, column=1).font = self.fonts['subtitle']
            ws.merge_cells(f'A{row}:E{row}')
            row += 1
            
            # 計算詳細
            details_lines = result.calculation_details.split('\n')
            for line in details_lines:
                if line.strip():
                    ws.cell(row=row, column=1, value=line)
                    ws.cell(row=row, column=1).font = self.fonts['body']
                    row += 1
            
            # 法的根拠
            if result.legal_basis:
                ws.cell(row=row, column=1, value=f"法的根拠: {result.legal_basis}")
                ws.cell(row=row, column=1).font = self.fonts['small']
                row += 1
            
            # 注意事項
            if result.notes:
                ws.cell(row=row, column=1, value=f"注意: {result.notes}")
                ws.cell(row=row, column=1).font = self.fonts['small']
                row += 1
            
            row += 2  # 項目間のスペース
    
    def _create_chart_sheet(self, wb: openpyxl.Workbook, results: Dict[str, CalculationResult]):
        """グラフシートの作成"""
        ws = wb.create_sheet("グラフ")
        
        # データ準備
        row = 2
        ws.cell(row=1, column=1, value="損害項目")
        ws.cell(row=1, column=2, value="金額")
        
        chart_data = []
        for key, result in results.items():
            if key == 'summary' or result.amount == 0:
                continue
            
            ws.cell(row=row, column=1, value=result.item_name)
            ws.cell(row=row, column=2, value=float(result.amount))
            chart_data.append((result.item_name, float(result.amount)))
            row += 1
        
        # 棒グラフ作成
        if chart_data:
            chart = BarChart()
            chart.title = "損害項目別金額"
            chart.x_axis.title = "損害項目"
            chart.y_axis.title = "金額（円）"
            
            data = Reference(ws, min_col=2, min_row=1, max_row=row-1)
            categories = Reference(ws, min_col=1, min_row=2, max_row=row-1)
            
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(categories)
            
            ws.add_chart(chart, "D2")
    
    def _create_reference_sheet(self, wb: openpyxl.Workbook, case_data: CaseData):
        """付属資料シートの作成"""
        ws = wb.create_sheet("付属資料")
        
        # 弁護士基準の説明
        explanations = [
            "【弁護士基準（裁判基準）について】",
            "",
            "弁護士基準とは、過去の裁判例に基づいて定められた損害賠償の算定基準です。",
            "一般的に自賠責基準や任意保険基準よりも高額になる傾向があります。",
            "",
            "【計算に使用した基準】",
            "・入通院慰謝料: 赤い本2023年版 別表I/II",
            "・後遺障害慰謝料: 赤い本2023年版",
            "・ライプニッツ係数: 法定利率3%（令和2年4月1日以降）",
            "",
            "【注意事項】",
            "・本計算書は弁護士基準に基づく概算額です",
            "・実際の示談交渉や裁判では個別事情により変動する可能性があります",
            "・最新の法改正や判例により基準が変更される場合があります"
        ]
          for i, text in enumerate(explanations, 1):
            ws.cell(row=i, column=1, value=text)
            if text.startswith("【") and text.endswith("】"):
                ws.cell(row=i, column=1).font = self.fonts['header']
            else:
                ws.cell(row=i, column=1).font = self.fonts['body']
    
    def _create_footer(self, ws, start_row: int) -> int:
        """フッター部分の作成 - 現在行ベースで更新"""
        row = start_row
        
        # 作成者情報
        ws[f'A{row}'] = f"作成者: {self.report_config.default_author}"
        ws[f'A{row}'].font = self.fonts['small']
        row += 1
        
        # 作成日時
        ws[f'A{row}'] = f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}"
        ws[f'A{row}'].font = self.fonts['small']
        row += 1
        
        # 免責事項
        disclaimer = "※ この計算書は弁護士基準に基づく概算であり、実際の示談や裁判では個別事情により変動する可能性があります。"
        ws[f'A{row}'] = disclaimer
        ws[f'A{row}'].font = self.fonts['small']
        ws[f'A{row}'].alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        ws.merge_cells(f'A{row}:H{row}')
        ws.row_dimensions[row].height = 30  # 高さを調整
        row += 1
        
        return row
    
    def _adjust_column_widths(self, ws):
        """列幅の自動調整"""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if cell.value is not None: # Noneの場合を考慮
                        # datetimeやdateオブジェクトは文字列長計算前にstr()で変換
                        if isinstance(cell.value, (datetime, date)):
                            value_str = str(cell.value.strftime("%Y/%m/%d %H:%M:%S") if isinstance(cell.value, datetime) else cell.value.strftime("%Y/%m/%d"))
                        else:
                            value_str = str(cell.value)
                        
                        if len(value_str) > max_length:
                            max_length = len(value_str)
                except Exception as e: # より具体的な例外処理が望ましい
                    self.logger.warning(f"列幅調整中にエラーが発生しました (セル: {cell.coordinate}): {e}")
                    pass
            
            adjusted_width = min(max_length + 2, 50)  # 最大50文字
            ws.column_dimensions[column_letter].width = adjusted_width

    def _apply_column_settings(self, ws):
        """列幅と行高の設定適用"""
        try:
            # 列幅設定
            for col_letter, width in self.column_widths.items():
                ws.column_dimensions[col_letter].width = width
            
            # 行高設定（ヘッダー行など特定の行に適用）
            if hasattr(ws, 'row_dimensions'):
                # 最初の数行にヘッダー用の高さを適用
                for row_num in range(1, 6):  # 最初の5行
                    if row_num <= ws.max_row:
                        ws.row_dimensions[row_num].height = self.row_heights.get('header', 25.0)
                        
        except Exception as e:
            self.logger.warning(f"列幅・行高の設定適用に失敗しました: {e}")
    
    def _insert_company_logo(self, ws):
        """会社ロゴの挿入"""
        try:
            if self.report_config.company_logo_path:
                logo_path = Path(self.report_config.company_logo_path)
                if logo_path.exists():
                    from openpyxl.drawing import Image
                    img = Image(str(logo_path))
                    img.height = 60  # 高さ60ピクセル
                    img.width = 120  # 幅120ピクセル
                    ws.add_image(img, 'H1')  # 右上に配置
                    self.logger.debug("会社ロゴを挿入しました")
        except Exception as e:
            self.logger.warning(f"会社ロゴの挿入に失敗しました: {e}")
    
    def _set_excel_properties(self, wb: openpyxl.Workbook, case_data: CaseData):
        """Excelファイルのプロパティ設定"""
        try:
            props = wb.properties
            props.title = f"損害賠償計算書 - {case_data.case_number or '事件番号未設定'}"
            props.subject = "弁護士基準損害賠償計算"
            props.creator = self.report_config.default_author
            props.description = f"被害者: {case_data.victim_name or '氏名未設定'}"
            props.keywords = "損害賠償,弁護士基準,計算書"
            props.lastModifiedBy = self.report_config.default_author
            
            from datetime import datetime
            props.created = datetime.now()
            props.modified = datetime.now()
            
            self.logger.debug("Excelファイルプロパティを設定しました")
        except Exception as e:
            self.logger.warning(f"Excelファイルプロパティの設定に失敗しました: {e}")

class TemplateManager:
    """Excelテンプレート管理クラス"""
    
    def __init__(self, report_config: ReportConfig, error_handler: ErrorHandler):
        self.report_config = report_config
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        try:
            # 複数テンプレート管理対応
            if self.report_config.excel_templates:
                # デフォルトテンプレートのパスからディレクトリを取得
                default_template_path = self.report_config.excel_templates.get("default")
                if default_template_path:
                    self.template_dir = Path(default_template_path).parent
                else:
                    self.template_dir = Path("templates/excel")
            else:
                # 従来の単一テンプレートパス対応
                if self.report_config.excel_template_path:
                    excel_template_file = Path(self.report_config.excel_template_path)
                    self.template_dir = excel_template_file.parent
                else:
                    self.template_dir = Path("templates/excel")
            
            self.template_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"TemplateManager: テンプレートディレクトリを設定: {self.template_dir}")
        except OSError as e:
            self.error_handler.handle_exception(
                FileIOError(f"テンプレートディレクトリの作成/アクセスに失敗しました: {self.template_dir}, {e}",
                            user_message="テンプレート用ディレクトリの準備中にエラーが発生しました。",
                            context={"path": str(self.template_dir)})
            )
            self.template_dir = Path("./templates")  # フォールバック
            self.template_dir.mkdir(parents=True, exist_ok=True)
            self.logger.warning(f"テンプレートディレクトリの作成に失敗したため、フォールバックディレクトリ ({self.template_dir}) を使用します。")
    
    def create_standard_templates(self):
        """標準テンプレートの作成"""
        try: # 追加
            # 交通事故テンプレート
            self._create_traffic_accident_template()
            
            # 労災事故テンプレート
            self._create_work_accident_template()
            
            # 医療過誤テンプレート
            self._create_medical_malpractice_template()
            logging.getLogger(__name__).info("標準テンプレートを作成しました。") # 追加
        except Exception as e: # 追加
            self.error_handler.handle_exception( # 追加
                CompensationSystemError(f"標準テンプレートの作成中にエラーが発生しました: {e}", # 追加
                                        category=ErrorCategory.FILE_IO, # 追加
                                        severity=ErrorSeverity.MEDIUM, # 追加
                                        user_message="標準レポートテンプレートの作成に失敗しました。", # 追加
                                        context={"details": str(e)}) # 追加
            ) # 追加
    
    def _create_traffic_accident_template(self):
        """交通事故用テンプレート"""
        try: # 追加
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "交通事故損害賠償計算書"
            
            # テンプレート固有の項目を設定
            ws['A1'] = "交通事故損害賠償計算書（テンプレート）" # サンプル
            # ヘッダー、フッター、ロゴプレースホルダーなどを設定
            ws['A2'] = "[ロゴプレースホルダー]"
            ws['H10'] = f"作成者: {self.report_config.default_author}"
            
            # template_path = self.template_dir / "traffic_accident_template.xlsx"
            # 設定ファイルで指定されたパスを使用する
            if self.report_config.excel_template_path:
                 template_path = Path(self.report_config.excel_template_path)
            else: # フォールバック
                 template_path = self.template_dir / "default_traffic_accident_template.xlsx"

            wb.save(template_path)
            # logging.getLogger(__name__).debug(f"交通事故テンプレートを作成しました: {template_path}") # 修正
            self.logger.debug(f"交通事故テンプレートを作成/更新しました: {template_path}")
        except Exception as e: # 追加
            self.error_handler.handle_exception( # 追加
                FileIOError(f"交通事故テンプレートの作成に失敗しました: {e}", # 追加
                            user_message="交通事故用レポートテンプレートの作成に失敗しました。", # 追加
                            context={"template_name": "traffic_accident_template.xlsx", "details": str(e)}) # 追加
            ) # 追加
      def _create_work_accident_template(self):
        """労災事故用テンプレート"""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "労災事故損害賠償計算書"
            
            # 基本設定
            ws['A1'] = "労災事故損害賠償計算書（テンプレート）"
            ws['A1'].font = Font(name='Meiryo UI', size=18, bold=True)
            ws.merge_cells('A1:I1')
            
            # ロゴプレースホルダー
            ws['A2'] = "[会社ロゴプレースホルダー]"
            ws['A2'].font = Font(name='Meiryo UI', size=10, italic=True)
            
            # 労災特有項目のヘッダー設定
            headers = [
                "事業場情報", "災害発生年月日", "災害の種類", "災害の原因",
                "被災者情報", "療養給付", "休業給付", "障害給付",
                "遺族給付", "葬祭料", "介護給付", "特別支給金"
            ]
            
            row = 4
            for i, header in enumerate(headers):
                cell = ws.cell(row=row + i, column=1, value=f"{header}:")
                cell.font = Font(name='Meiryo UI', size=11, bold=True)
                ws.cell(row=row + i, column=2, value="[データプレースホルダー]")
            
            # 作成者情報
            ws[f'H{row + len(headers) + 2}'] = f"作成者: {self.report_config.default_author}"
            ws[f'H{row + len(headers) + 3}'] = "作成日: [作成日プレースホルダー]"
            
            # 労災特有の注意事項
            note_row = row + len(headers) + 5
            ws[f'A{note_row}'] = "【労災給付との調整について】"
            ws[f'A{note_row}'].font = Font(name='Meiryo UI', size=12, bold=True)
            ws[f'A{note_row + 1}'] = "・労災給付は損害の填補として控除されます"
            ws[f'A{note_row + 2}'] = "・特別支給金は原則として控除されません"
            ws[f'A{note_row + 3}'] = "・将来の介護費用についても労災給付を考慮します"
            
            template_path = self.template_dir / "work_accident_template.xlsx"
            wb.save(template_path)
            self.logger.debug(f"労災事故テンプレートを作成/更新しました: {template_path}")
        except Exception as e:
            self.error_handler.handle_exception(
                FileIOError(f"労災事故テンプレートの作成に失敗しました: {e}",
                            user_message="労災事故用レポートテンプレートの作成に失敗しました。",
                            context={"template_name": "work_accident_template.xlsx", "details": str(e)})
            )
      def _create_medical_malpractice_template(self):
        """医療過誤用テンプレート"""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "医療過誤損害賠償計算書"
            
            # 基本設定
            ws['A1'] = "医療過誤損害賠償計算書（テンプレート）"
            ws['A1'].font = Font(name='Meiryo UI', size=18, bold=True)
            ws.merge_cells('A1:I1')
            
            # ロゴプレースホルダー
            ws['A2'] = "[会社ロゴプレースホルダー]"
            ws['A2'].font = Font(name='Meiryo UI', size=10, italic=True)
            
            # 医療過誤特有項目のヘッダー設定
            headers = [
                "医療機関情報", "診療科", "主治医", "診療期間",
                "医療行為の内容", "過誤の内容", "因果関係", "過失の程度",
                "既往症・素因", "寄与度減額", "文書料", "鑑定費用",
                "弁護士費用", "遅延損害金"
            ]
            
            row = 4
            for i, header in enumerate(headers):
                cell = ws.cell(row=row + i, column=1, value=f"{header}:")
                cell.font = Font(name='Meiryo UI', size=11, bold=True)
                ws.cell(row=row + i, column=2, value="[データプレースホルダー]")
            
            # 作成者情報
            ws[f'H{row + len(headers) + 2}'] = f"作成者: {self.report_config.default_author}"
            ws[f'H{row + len(headers) + 3}'] = "作成日: [作成日プレースホルダー]"
            
            # 医療過誤特有の注意事項
            note_row = row + len(headers) + 5
            ws[f'A{note_row}'] = "【医療過誤損害賠償の特殊性】"
            ws[f'A{note_row}'].font = Font(name='Meiryo UI', size=12, bold=True)
            ws[f'A{note_row + 1}'] = "・因果関係の立証が重要な争点となります"
            ws[f'A{note_row + 2}'] = "・既往症・素因による寄与度減額を検討します"
            ws[f'A{note_row + 3}'] = "・医師の過失の程度により賠償額が調整されます"
            ws[f'A{note_row + 4}'] = "・医療費の差額、転院費用等も損害に含まれます"
            ws[f'A{note_row + 5}'] = "・鑑定費用、文書取得費用も損害として請求可能です"
            
            template_path = self.template_dir / "medical_malpractice_template.xlsx"
            wb.save(template_path)
            self.logger.debug(f"医療過誤テンプレートを作成/更新しました: {template_path}")
        except Exception as e:
            self.error_handler.handle_exception(
                FileIOError(f"医療過誤テンプレートの作成に失敗しました: {e}",
                            user_message="医療過誤用レポートテンプレートの作成に失敗しました。",
                            context={"template_name": "medical_malpractice_template.xlsx", "details": str(e)})
            )
      def apply_template(self, template_name: str, case_data: CaseData) -> Optional[openpyxl.Workbook]:
        """テンプレートの適用"""
        # テンプレートマッピング
        template_mapping = {
            "traffic_accident": "traffic_accident_template.xlsx",
            "work_accident": "work_accident_template.xlsx", 
            "medical_malpractice": "medical_malpractice_template.xlsx",
            "default": "default_traffic_accident_template.xlsx"
        }
        
        # テンプレートファイル名を決定
        template_filename = template_mapping.get(template_name, template_mapping["default"])
        
        # 設定からテンプレートディレクトリを取得、フォールバック処理
        if self.report_config.excel_template_path:
            # 設定でフルパスが指定されている場合
            template_path = Path(self.report_config.excel_template_path)
        else:
            # ディレクトリ + ファイル名で構成
            template_path = self.template_dir / template_filename
        
        try:
            if template_path.exists():
                wb = openpyxl.load_workbook(template_path)
                
                # テンプレートにケースデータを埋め込む
                self._populate_template_data(wb, case_data, template_name)
                
                self.logger.info(f"テンプレート '{template_name}' ({template_filename}) を適用しました。")
                return wb
            else:
                # テンプレートが存在しない場合、作成を試行
                self.logger.warning(f"テンプレート {template_filename} が見つかりません。作成を試行します。")
                self._create_template_if_missing(template_name)
                
                # 再度読み込みを試行
                if template_path.exists():
                    wb = openpyxl.load_workbook(template_path)
                    self._populate_template_data(wb, case_data, template_name)
                    return wb
                else:
                    self.error_handler.handle_exception(
                        FileNotFoundError(f"テンプレート {template_name} が見つからず、作成にも失敗しました: {template_path}"),
                        user_message=f"指定されたレポートテンプレート '{template_name}' が見つかりませんでした。",
                        context={"template_name": template_name, "path": str(template_path)}
                    )
                    return None
        except Exception as e:
            self.error_handler.handle_exception(
                FileIOError(f"テンプレート '{template_name}' の適用中にエラーが発生しました: {e}",
                            user_message=f"レポートテンプレート '{template_name}' の処理中にエラーが発生しました。",
                            context={"template_name": template_name, "path": str(template_path), "details": str(e)})
            )
            return None
    
    def _create_template_if_missing(self, template_name: str):
        """不足テンプレートの作成"""
        try:
            if template_name == "traffic_accident":
                self._create_traffic_accident_template()
            elif template_name == "work_accident":
                self._create_work_accident_template()
            elif template_name == "medical_malpractice":
                self._create_medical_malpractice_template()
            else:
                self.logger.warning(f"未知のテンプレート名: {template_name}")
        except Exception as e:
            self.logger.error(f"テンプレート {template_name} の作成に失敗しました: {e}")
    
    def _populate_template_data(self, wb: openpyxl.Workbook, case_data: CaseData, template_type: str):
        """テンプレートにデータを埋め込む"""
        try:
            ws = wb.active
            
            # 基本情報の埋め込み
            # 事件番号
            if case_data.case_number:
                self._replace_placeholder(ws, "[事件番号]", case_data.case_number)
            
            # 被害者情報
            if case_data.victim_name:
                self._replace_placeholder(ws, "[被害者名]", case_data.victim_name)
            if case_data.victim_age:
                self._replace_placeholder(ws, "[年齢]", str(case_data.victim_age))
            if case_data.victim_gender:
                self._replace_placeholder(ws, "[性別]", case_data.victim_gender)
            
            # 事故情報
            if case_data.accident_date:
                self._replace_placeholder(ws, "[事故日]", case_data.accident_date.strftime("%Y年%m月%d日"))
            
            # 作成日
            from datetime import datetime
            self._replace_placeholder(ws, "[作成日プレースホルダー]", datetime.now().strftime("%Y年%m月%d日"))
            
            # テンプレート別の特別処理
            if template_type == "work_accident":
                self._populate_work_accident_data(ws, case_data)
            elif template_type == "medical_malpractice":
                self._populate_medical_malpractice_data(ws, case_data)
                
            self.logger.debug(f"テンプレートデータの埋め込みが完了しました: {template_type}")
        except Exception as e:
            self.logger.error(f"テンプレートデータの埋め込み中にエラーが発生しました: {e}")
    
    def _replace_placeholder(self, ws: openpyxl.worksheet.worksheet.Worksheet, placeholder: str, value: str):
        """プレースホルダーの置換"""
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and placeholder in cell.value:
                    cell.value = cell.value.replace(placeholder, value)
    
    def _populate_work_accident_data(self, ws: openpyxl.worksheet.worksheet.Worksheet, case_data: CaseData):
        """労災事故特有データの埋め込み"""
        # 労災特有の情報があれば埋め込み
        # 例: 事業場情報、災害の種類等
        pass
    
    def _populate_medical_malpractice_data(self, ws: openpyxl.worksheet.worksheet.Worksheet, case_data: CaseData):
        """医療過誤特有データの埋め込み"""
        # 医療過誤特有の情報があれば埋め込み
        # 例: 医療機関情報、診療科等
        pass

# 使用例
if __name__ == "__main__":
    # サンプル使用
    generator = ExcelReportGenerator()
    
    # テンプレートマネージャー
    template_mgr = TemplateManager()
    template_mgr.create_standard_templates()
