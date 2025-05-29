#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDFレポート生成モジュール
"""

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image # Image を追加
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from decimal import Decimal
from datetime import datetime
import traceback
import os # os を追加

# 日本語フォント対応のため追加
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models.case_data import CaseData
from calculation.compensation_engine import CalculationResult # CalculationResultをインポート
from utils.error_handler import get_error_handler, CompensationSystemError, ErrorCategory, ErrorSeverity, FileIOError, ConfigurationError # ConfigurationError を追加
from config.app_config import AppConfig # AppConfig をインポート
import logging # 追加

# FONT_NAME_GOTHIC と FONT_FILE_PATH_GOTHIC のグローバル定義は削除し、configから取得する

class PdfReportGenerator:
    """PDFレポート生成クラス"""

    def __init__(self, config: AppConfig, case_data: CaseData, calculation_results: dict[str, CalculationResult]): # config を追加
        self.config = config
        self.report_config = config.report
        self.case_data = case_data
        self.calculation_results = calculation_results
        self.styles = getSampleStyleSheet()
        self.error_handler = get_error_handler()
        self.logger = logging.getLogger(__name__)
        self._register_fonts() # フォント登録処理をメソッド化
        self.custom_styles()

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
            # フォント設定がない場合は処理を続行できないため、例外を発生させるか、デフォルトフォントにフォールバックする
            # ここではエラーを記録し、後続の処理で問題が発生する可能性があることを許容する（reportlabがフォールバックする場合があるため）
            self.logger.error("ゴシックフォントの設定が不完全なため、PDF生成に問題が発生する可能性があります。")
            return # フォント登録をスキップ

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


    def custom_styles(self):
        """カスタムスタイルの定義"""
        font_name_gothic = self.report_config.font_name_gothic
        # フォントが正常に登録されたか確認し、されていなければデフォルトフォントを使用
        base_font = font_name_gothic if pdfmetrics.getFont(font_name_gothic, None) else 'Helvetica'
        
        if base_font == 'Helvetica' and font_name_gothic:
            self.logger.warning(f"指定されたフォント '{font_name_gothic}' が利用できないため、Helveticaにフォールバックします。")


        self.styles.add(ParagraphStyle(name='MainTitle', fontSize=18, alignment=TA_CENTER, spaceAfter=10*mm, fontName=base_font, leading=22))
        self.styles.add(ParagraphStyle(name='SubTitle', fontSize=14, alignment=TA_LEFT, spaceAfter=5*mm, spaceBefore=5*mm, fontName=base_font, leading=18))
        self.styles.add(ParagraphStyle(name='Normal', fontSize=10, alignment=TA_LEFT, fontName=base_font, leading=14))
        self.styles.add(ParagraphStyle(name='NormalRight', fontSize=10, alignment=TA_RIGHT, fontName=base_font, leading=14))
        self.styles.add(ParagraphStyle(name='NormalJustify', fontSize=10, alignment=TA_JUSTIFY, leading=14, fontName=base_font))
        self.styles.add(ParagraphStyle(name='TableHeader', fontSize=10, alignment=TA_CENTER, fontName=base_font, textColor=colors.whitesmoke, leading=12))
        self.styles.add(ParagraphStyle(name='TableCell', fontSize=9, alignment=TA_LEFT, fontName=base_font, leading=11))
        self.styles.add(ParagraphStyle(name='TableCellRight', fontSize=9, alignment=TA_RIGHT, fontName=base_font, leading=11))
        self.styles.add(ParagraphStyle(name='Footer', fontSize=8, alignment=TA_CENTER, fontName=base_font, leading=10))
        self.styles.add(ParagraphStyle(name='SmallText', fontSize=8, alignment=TA_LEFT, fontName=base_font, leading=10))

    def generate_report(self, output_filename: str): # 引数を output_filename に変更
        """PDFレポートを生成"""
        output_dir = self.report_config.default_output_directory
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.logger.info(f"出力ディレクトリ '{output_dir}' を作成しました。")
            except OSError as e:
                self.error_handler.handle_exception(
                    FileIOError(
                        f"出力ディレクトリ '{output_dir}' の作成に失敗しました: {e}",
                        user_message=f"レポートの出力先ディレクトリ '{output_dir}' を作成できませんでした。権限などを確認してください。",
                        severity=ErrorSeverity.HIGH,
                        context={"path": output_dir, "exception": str(e)}
                    )
                )
                return # ディレクトリ作成失敗時は処理を中断

        filepath = os.path.join(output_dir, output_filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                topMargin=20*mm, bottomMargin=20*mm,
                                leftMargin=20*mm, rightMargin=20*mm,
                                author=self.report_config.default_author, #作成者を設定
                                title=f"損害賠償額計算書 - {self.case_data.case_number or 'N/A'}" # タイトルも設定
                                )
        
        story = []

        try:
            # 0. 会社ロゴ (設定されていれば)
            if self.report_config.company_logo_path and os.path.exists(self.report_config.company_logo_path):
                try:
                    logo = Image(self.report_config.company_logo_path)
                    logo.drawHeight = 15*mm # 高さを指定 (幅は自動調整)
                    logo.drawWidth = (logo.drawHeight / logo.imageHeight) * logo.imageWidth # アスペクト比を維持
                    logo.hAlign = 'RIGHT' # 右寄せ
                    story.append(logo)
                    story.append(Spacer(1, 5*mm))
                except Exception as e:
                    self.error_handler.handle_exception(
                        FileIOError(
                            f"会社ロゴファイル '{self.report_config.company_logo_path}' の読み込みまたは処理に失敗しました: {e}",
                            user_message="会社ロゴの表示に失敗しました。ロゴファイルパスやファイル形式を確認してください。",
                            severity=ErrorSeverity.WARNING, # ロゴは警告レベル
                            context={"logo_path": self.report_config.company_logo_path, "exception": str(e)}
                        )
                    )
                    self.logger.warning(f"会社ロゴの読み込みに失敗: {self.report_config.company_logo_path}, エラー: {e}")
            elif self.report_config.company_logo_path: # パスは指定されているが存在しない場合
                 self.logger.warning(f"会社ロゴファイルが見つかりません: {self.report_config.company_logo_path}")


            # 1. ヘッダー情報
            story.append(Paragraph("損害賠償額計算書", self.styles['MainTitle']))
            story.append(Spacer(1, 5*mm))
            
            header_data = [
                [Paragraph("案件番号:", self.styles['Normal']), Paragraph(str(self.case_data.case_number or '未設定'), self.styles['Normal'])],
                [Paragraph("依頼者名:", self.styles['Normal']), Paragraph(str(self.case_data.person_info.name or '未設定'), self.styles['Normal'])],
                [Paragraph("作成日:", self.styles['Normal']), Paragraph(datetime.now().strftime("%Y年%m月%d日"), self.styles['Normal'])],
                [Paragraph("作成者:", self.styles['Normal']), Paragraph(self.report_config.default_author or '未設定', self.styles['Normal'])], # 作成者情報を追加
            ]
            header_table = Table(header_data, colWidths=[40*mm, None])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1*mm),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 10*mm))

            # 2. 基本情報
            story.append(Paragraph("1. 基本情報", self.styles['SubTitle']))
            basic_info_data = [
                [Paragraph("事故発生日:", self.styles['TableCell']), Paragraph(str(self.case_data.accident_info.accident_date or '-'), self.styles['TableCell'])],
                [Paragraph(f"被害者年齢（事故時）:", self.styles['TableCell']), Paragraph(f"{self.case_data.person_info.age} 歳" if self.case_data.person_info.age is not None else '-', self.styles['TableCell'])],
                [Paragraph("性別:", self.styles['TableCell']), Paragraph(str(self.case_data.person_info.gender or '-'), self.styles['TableCell'])],
                [Paragraph("職業:", self.styles['TableCell']), Paragraph(str(self.case_data.person_info.occupation or '-'), self.styles['TableCell'])],
                [Paragraph("事故前年収:", self.styles['TableCell']), Paragraph(f"{self.case_data.person_info.annual_income:,.0f} 円" if self.case_data.person_info.annual_income is not None else '-', self.styles['TableCellRight'])],
                [Paragraph("被害者過失割合:", self.styles['TableCell']), Paragraph(f"{self.case_data.person_info.fault_percentage or 0} %", self.styles['TableCellRight'])],
            ]
            basic_table = Table(basic_info_data, colWidths=[50*mm, None])
            basic_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
            ]))
            story.append(basic_table)
            story.append(Spacer(1, 7*mm))

            # 3. 医療情報
            story.append(Paragraph("2. 医療情報", self.styles['SubTitle']))
            med_info = self.case_data.medical_info
            medical_info_data = [
                [Paragraph("症状固定日:", self.styles['TableCell']), Paragraph(str(self.case_data.accident_info.symptom_fixed_date or '-'), self.styles['TableCell'])],
                [Paragraph("入院期間:", self.styles['TableCell']), Paragraph(f"{med_info.hospital_months} ヶ月" if med_info.hospital_months is not None else '-', self.styles['TableCell'])],
                [Paragraph("通院期間:", self.styles['TableCell']), Paragraph(f"{med_info.outpatient_months} ヶ月" if med_info.outpatient_months is not None else '-', self.styles['TableCell'])],
                [Paragraph("実通院日数:", self.styles['TableCell']), Paragraph(f"{med_info.actual_outpatient_days} 日" if med_info.actual_outpatient_days is not None else '-', self.styles['TableCell'])],
                [Paragraph("むちうち等:", self.styles['TableCell']), Paragraph("該当" if med_info.is_whiplash else "非該当", self.styles['TableCell'])],
                [Paragraph("後遺障害等級:", self.styles['TableCell']), Paragraph(f"第 {med_info.disability_grade} 級" if med_info.disability_grade and med_info.disability_grade > 0 else "なし", self.styles['TableCell'])],
                [Paragraph("後遺障害詳細:", self.styles['TableCell']), Paragraph(med_info.disability_details or '-', self.styles['TableCell'])],
            ]
            medical_table = Table(medical_info_data, colWidths=[50*mm, None])
            medical_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                ('SPAN', (1,6), (-1,6)) # 後遺障害詳細のセルを結合
            ]))
            story.append(medical_table)
            story.append(Spacer(1, 7*mm))

            # 4. 収入・損害情報 (逸失利益関連)
            story.append(Paragraph("3. 収入・損害情報", self.styles['SubTitle']))
            inc_info = self.case_data.income_info
            income_info_data = [
                [Paragraph("休業日数:", self.styles['TableCell']), Paragraph(f"{inc_info.lost_work_days} 日" if inc_info.lost_work_days is not None else '-', self.styles['TableCell'])],
                [Paragraph("日額基礎収入:", self.styles['TableCell']), Paragraph(f"{inc_info.daily_income:,.0f} 円" if inc_info.daily_income is not None else '-', self.styles['TableCellRight'])],
                [Paragraph("基礎年収（逸失利益用）:", self.styles['TableCell']), Paragraph(f"{inc_info.base_annual_income:,.0f} 円" if inc_info.base_annual_income is not None else '-', self.styles['TableCellRight'])],
                [Paragraph("労働能力喪失期間:", self.styles['TableCell']), Paragraph(f"{inc_info.loss_period_years} 年" if inc_info.loss_period_years is not None else '-', self.styles['TableCell'])],
                [Paragraph("就労可能年数上限:", self.styles['TableCell']), Paragraph(f"{self.case_data.person_info.retirement_age} 歳" if self.case_data.person_info.retirement_age is not None else '-', self.styles['TableCell'])],
            ]
            income_table = Table(income_info_data, colWidths=[50*mm, None])
            income_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
            ]))
            story.append(income_table)
            story.append(Spacer(1, 10*mm))
            
            story.append(PageBreak()) # 計算結果は新しいページから

            # 5. 計算結果
            story.append(Paragraph("4. 損害賠償額計算結果", self.styles['SubTitle']))
            
            results_header = [
                Paragraph("<b>費目</b>", self.styles['TableHeader']),
                Paragraph("<b>金額（円）</b>", self.styles['TableHeader']),
            ]
            if self.report_config.include_detailed_calculation_in_pdf: # 詳細表示フラグを確認
                results_header.append(Paragraph("<b>計算根拠・備考</b>", self.styles['TableHeader']))
            
            results_data = [results_header]
            
            ordered_items = [
                'treatment_cost', 'hospital_miscellaneous_expenses', 'attendant_care_hospital',
                'outpatient_transportation_fee', 'document_fee', 'lost_earning_due_to_absence',
                'injury_compensation', 'disability_compensation', 'future_income_loss_disability',
                'funeral_expenses', 'deceased_lost_income', 'deceased_compensation',
                'survivor_compensation', 'property_damage', 'lawyer_fee'
            ]

            total_amount = Decimal(0)
            grand_total_before_fault_offset = Decimal(0)

            for key, result in self.calculation_results.items():
                if key not in ordered_items: # ordered_items にないものはその他として扱うか、ログを出す
                    self.logger.debug(f"Calculation result for '{key}' is not in ordered_items, skipping direct display.")
                    if isinstance(result, CalculationResult): # CalculationResult インスタンスのみ集計対象
                         grand_total_before_fault_offset += result.amount
                    continue

                if isinstance(result, CalculationResult) and result.amount > 0: # 金額が0より大きい場合のみ表示
                    row = [
                        Paragraph(result.item_name, self.styles['TableCell']),
                        Paragraph(f"{result.amount:,.0f}", self.styles['TableCellRight']),
                    ]
                    if self.report_config.include_detailed_calculation_in_pdf:
                        details = result.details or "-"
                        # detailsが長すぎる場合の処理（例：一定文字数で丸める）
                        if len(details) > 100: # 例えば100文字以上なら丸める
                            details = details[:100] + "..."
                        row.append(Paragraph(details, self.styles['TableCell']))
                    results_data.append(row)
                    grand_total_before_fault_offset += result.amount # 過失相殺前の合計に加算

            # 「合計（過失相殺前）」の行を追加
            total_row_before_offset = [
                Paragraph("<b>合計（過失相殺前）</b>", self.styles['TableCell']),
                Paragraph(f"<b>{grand_total_before_fault_offset:,.0f}</b>", self.styles['TableCellRight']),
            ]
            if self.report_config.include_detailed_calculation_in_pdf:
                total_row_before_offset.append(Paragraph("", self.styles['TableCell'])) # 備考欄は空
            results_data.append(total_row_before_offset)
            
            # 過失相殺
            fault_percentage = self.case_data.person_info.fault_percentage or 0
            fault_offset_amount = (grand_total_before_fault_offset * Decimal(fault_percentage) / Decimal(100)).quantize(Decimal('1'))
            
            offset_row = [
                Paragraph(f"過失相殺（{fault_percentage}%）", self.styles['TableCell']),
                Paragraph(f"<u>-{fault_offset_amount:,.0f}</u>", self.styles['TableCellRight']), # 下線を追加
            ]
            if self.report_config.include_detailed_calculation_in_pdf:
                offset_row.append(Paragraph(f"{grand_total_before_fault_offset:,.0f}円 × {fault_percentage}%", self.styles['TableCell']))
            results_data.append(offset_row)

            # 最終合計金額
            final_total_amount = grand_total_before_fault_offset - fault_offset_amount
            final_total_row = [
                Paragraph("<b>最終合計金額</b>", self.styles['TableCell']), # 太字に変更
                Paragraph(f"<b>{final_total_amount:,.0f}</b>", self.styles['TableCellRight']), # 太字に変更
            ]
            if self.report_config.include_detailed_calculation_in_pdf:
                final_total_row.append(Paragraph("", self.styles['TableCell'])) # 備考欄は空
            results_data.append(final_total_row)

            # テーブルスタイル
            col_widths = [60*mm, 40*mm]
            if self.report_config.include_detailed_calculation_in_pdf:
                col_widths.append(None) # 備考欄の幅は残り全て

            results_table = Table(results_data, colWidths=col_widths)
            table_style_commands = [
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4682B4")), # ヘッダー背景色 (SteelBlue)
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'), # 金額列は右寄せ
                ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
                ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
                ('LINEBELOW', (0,-2), (-1,-2), 1, colors.black), # 最終合計の上の線
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black, None, None, 2, 0), # 最終合計の二重線の上側
                ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black, None, None, 0, 0), # 最終合計の二重線の下側
            ]
            # 最終行のフォントを太字にするスタイル (Paragraph内で<b>タグを使っているので不要かもしれないが念のため)
            # table_style_commands.append(('FONTNAME', (0, -1), (-1, -1), self.styles['TableCell'].fontName + '-Bold')) # うまく動かない場合がある
            
            results_table.setStyle(TableStyle(table_style_commands))
            story.append(results_table)
            story.append(Spacer(1, 10*mm))

            # 6. フッター (免責事項など)
            story.append(Paragraph("---", self.styles['NormalCenter'])) # NormalCenterがないのでNormalで代用、または追加
            story.append(Spacer(1, 2*mm))
            disclaimer = "この計算書は、提供された情報に基づいて作成された概算であり、法的な助言や最終的な賠償金額を保証するものではありません。具体的な事案については、弁護士にご相談ください。"
            story.append(Paragraph(disclaimer, self.styles['SmallText']))


            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
            self.logger.info(f"PDFレポート '{filepath}' が正常に生成されました。")

        except CompensationSystemError as e: # アプリケーション固有エラー
            self.error_handler.handle_exception(e) # 既に処理されているはずだが、念のため
            self.logger.error(f"PDFレポート生成中にエラーが発生しました（CompensationSystemError）: {e.log_message}")
        except Exception as e: # 予期せぬエラー
            tb_str = traceback.format_exc()
            self.error_handler.handle_exception(
                CompensationSystemError( # 汎用エラーとしてラップ
                    f"PDFレポート生成中に予期せぬエラーが発生しました: {e}",
                    user_message="PDFレポートの作成中に予期しない問題が発生しました。システム管理者にお問い合わせください。",
                    category=ErrorCategory.REPORT_GENERATION,
                    severity=ErrorSeverity.CRITICAL,
                    context={"filepath": filepath, "exception_type": type(e).__name__, "traceback": tb_str}
                )
            )
            self.logger.error(f"PDFレポート '{filepath}' の生成中に予期せぬエラー: {e}\n{tb_str}")


    def _add_page_number(self, canvas, doc):
        """ページ番号を追加する"""
        canvas.saveState()
        canvas.setFont(self.styles['Footer'].fontName, self.styles['Footer'].fontSize) # フッタースタイルからフォント情報を取得
        page_num_text = f"Page {doc.page}"
        canvas.drawCentredString(A4[0]/2, 10*mm, page_num_text)
        canvas.restoreState()

# 使用例 (テスト用)
if __name__ == '__main__':
    from config.app_config import load_config
    from decimal import Decimal

    # テスト用の設定とデータ
    try:
        # 設定ファイルのロード (実際のパスに置き換えてください)
        # このテストを実行する際は、プロジェクトルートからの相対パス、または絶対パスを指定してください。
        # 例: config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'app_config.json')
        config_path = 'e:\\config\\app_config.json' # 直接指定
        if not os.path.exists(config_path):
            print(f"テスト用の設定ファイルが見つかりません: {config_path}")
            exit()
            
        app_config = load_config(config_path)
        
        # ダミーの CaseData
        case_data = CaseData(
            case_number="TEST-001",
            person_info=CaseData.PersonInfo(name="テスト 太郎", age=30, gender="男性", occupation="会社員", annual_income=5000000, fault_percentage=10, retirement_age=67),
            accident_info=CaseData.AccidentInfo(accident_date="2023-01-15", symptom_fixed_date="2023-07-15"),
            medical_info=CaseData.MedicalInfo(hospital_months=1, outpatient_months=6, actual_outpatient_days=50, is_whiplash=False, disability_grade=14, disability_details="頚椎捻挫による局部の神経症状"),
            income_info=CaseData.IncomeInfo(lost_work_days=30, daily_income=Decimal("15000"), base_annual_income=Decimal("4500000"), loss_period_years=5)
        )
        
        # ダミーの CalculationResult
        calculation_results = {
            'treatment_cost': CalculationResult(item_name="治療費", amount=Decimal("500000"), details="実費"),
            'injury_compensation': CalculationResult(item_name="入通院慰謝料", amount=Decimal("1200000"), details="別表I基準 1ヶ月入院+6ヶ月通院"),
            'future_income_loss_disability': CalculationResult(item_name="後遺障害逸失利益", amount=Decimal("3000000"), details="年収450万 x 5% x 5年 (ライプニッツ係数)"),
            'disability_compensation': CalculationResult(item_name="後遺障害慰謝料", amount=Decimal("1100000"), details="14級基準"),
            'lawyer_fee': CalculationResult(item_name="弁護士費用", amount=Decimal("580000"), details="認容額の10%"),
        }

        generator = PdfReportGenerator(app_config, case_data, calculation_results)
        output_pdf_filename = "test_compensation_report.pdf"
        generator.generate_report(output_pdf_filename)
        print(f"テストレポート '{os.path.join(app_config.report.default_output_directory, output_pdf_filename)}' が生成されました。")

    except ConfigurationError as ce:
        print(f"設定エラー: {ce.user_message} (詳細はログを確認)")
    except FileNotFoundError as fnfe:
        print(f"ファイルが見つかりません: {fnfe}")
    except Exception as ex:
        print(f"テスト中に予期せぬエラーが発生しました: {ex}")
        traceback.print_exc()

