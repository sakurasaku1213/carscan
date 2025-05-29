#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロフェッショナルUI設計計画

現在のTkinterベースのUIを大幅に改善し、実用的で美しいインターフェースを実現

改善戦略:
1. CustomTkinter導入による現代的デザイン
2. データ入力の効率化
3. リアルタイム計算・検証
4. 直感的なナビゲーション
5. 豊富な可視化機能
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from datetime import datetime, date
from typing import Optional, Dict, Any, Callable
import threading
from decimal import Decimal, InvalidOperation
import logging
import json
from pathlib import Path

from models import CaseData, PersonInfo, AccidentInfo, MedicalInfo, IncomeInfo
from calculation.compensation_engine import CompensationEngine, CalculationResult
from database.db_manager import DatabaseManager
from config.app_config import ConfigManager, get_config_manager

# CustomTkinterのテーマ設定
ctk.set_appearance_mode("light")  # "light" または "dark"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class ModernCompensationCalculator:
    """次世代損害賠償計算システムUI"""
    
    def __init__(self):
        # 設定管理システムの初期化
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        
        # ロギング設定
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level),
            format=self.config.logging.format,
            filename=self.config.logging.file_path if self.config.logging.file_path else None
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("現代的損害賠償計算システムを開始")
          # UI初期化
        self.root = ctk.CTk()
        self.setup_window()
        self.init_components()
        
        # コンポーネント初期化（UIコンポーネントが使用する前に初期化）
        try:
            self.calculation_engine = CompensationEngine()
            self.db_manager = DatabaseManager(self.config.database.file_path)
            self.current_case: CaseData = CaseData()
            
            # リアルタイム計算フラグ
            self.auto_calculate = ctk.BooleanVar(value=self.config.ui.auto_calculate)
            self.calculation_timer = None
            
            # UIコンポーネントの作成（すべての属性が初期化された後）
            self.create_modern_ui()
            
            self.logger.info("すべてのコンポーネントが正常に初期化されました")
        except Exception as e:
            self.logger.error(f"コンポーネント初期化エラー: {e}", exc_info=True)
            messagebox.showerror("初期化エラー", f"システム初期化に失敗しました:\n{e}")
            raise
        
        # ログ設定の改善
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def setup_window(self):
        """ウィンドウの基本設定"""
        self.root.title("弁護士基準損害賠償計算システム Pro")
        self.root.geometry("1400x900")
        
        # ウィンドウを中央に配置
        self.root.after(100, self.center_window) # 100ms後に実行することでウィンドウサイズ確定を待つ
        
        # アイコン設定（オプション）
        # self.root.iconbitmap("path/to/your/icon.ico") # 正しいパスに置き換えてください
    
    def center_window(self):
        """ウィンドウを画面中央に配置"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def init_components(self):
        """UIコンポーネントの初期化"""
        # カラーテーマ
        self.colors = {
            'primary': '#2196F3',
            'primary_dark': '#1976D2',
            'secondary': '#4CAF50',
            'accent': '#FF9800',
            'error': '#F44336',
            'warning': '#FF5722',
            'success': '#4CAF50',
            'background': '#FAFAFA',
            'surface': '#FFFFFF',
            'text_primary': '#212121',
            'text_secondary': '#757575'
        }
        
        # フォント設定
        self.fonts = {
            'title': ctk.CTkFont(family="Meiryo UI", size=24, weight="bold"),
            'subtitle': ctk.CTkFont(family="Meiryo UI", size=18, weight="bold"),
            'body': ctk.CTkFont(family="Meiryo UI", size=14),
            'small': ctk.CTkFont(family="Meiryo UI", size=12),
            'large': ctk.CTkFont(family="Meiryo UI", size=16)
        }
    
    def create_modern_ui(self):
        """モダンUIの構築"""
        # メインコンテナ
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ヘッダー部分
        self.create_header()
        
        # メインコンテンツエリア
        self.content_frame = ctk.CTkFrame(self.main_container)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        # サイドバー（案件リスト・設定）
        self.create_sidebar()
        
        # メインパネル（タブエリア）
        self.create_main_panel()
        
        # ステータスバー
        self.create_status_bar()
    
    def create_header(self):
        """ヘッダーセクション"""
        header_frame = ctk.CTkFrame(self.main_container, height=80)
        header_frame.pack(fill="x", padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        # タイトル
        title_label = ctk.CTkLabel(
            header_frame,
            text="🏛️ 弁護士基準損害賠償計算システム Pro",
            font=self.fonts['title']
        )
        title_label.pack(side="left", padx=20, pady=20)
        
        # ヘッダーボタン群
        header_buttons = ctk.CTkFrame(header_frame)
        header_buttons.pack(side="right", padx=20, pady=15)
        
        # 新規案件
        new_case_btn = ctk.CTkButton(
            header_buttons,
            text="📝 新規案件",
            command=self.new_case,
            width=100,
            font=self.fonts['body']
        )
        new_case_btn.pack(side="left", padx=5)
        
        # 保存
        save_btn = ctk.CTkButton(
            header_buttons,
            text="💾 保存",
            command=self.save_case,
            width=80,
            font=self.fonts['body']
        )
        save_btn.pack(side="left", padx=5)
        
        # 読み込み
        load_btn = ctk.CTkButton(
            header_buttons,
            text="📂 読み込み",
            command=self.load_case,
            width=100,
            font=self.fonts['body']
        )
        load_btn.pack(side="left", padx=5)
        
        # 設定
        settings_btn = ctk.CTkButton(
            header_buttons,
            text="⚙️ 設定",
            command=self.open_settings,
            width=80,
            font=self.fonts['body']
        )
        settings_btn.pack(side="left", padx=5)
    
    def create_sidebar(self):
        """サイドバー（案件リスト・クイック機能）"""
        # サイドバーは画面左側に配置
        self.sidebar = ctk.CTkFrame(self.content_frame, width=300)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)
        
        # サイドバータイトル
        sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="📋 案件管理",
            font=self.fonts['subtitle']
        )
        sidebar_title.pack(pady=15)
          # 検索フィールド
        search_frame = ctk.CTkFrame(self.sidebar)
        search_frame.pack(fill="x", padx=15, pady=10)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            font=self.fonts['body']
        )
        self.search_entry.pack(fill="x", padx=10, pady=10)
        self.search_entry.bind("<KeyRelease>", self.on_search_change)
        
        # 案件リスト
        self.case_list_frame = ctk.CTkScrollableFrame(self.sidebar, height=400)
        self.case_list_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # クイック機能
        quick_frame = ctk.CTkFrame(self.sidebar)
        quick_frame.pack(fill="x", padx=15, pady=10)
        
        quick_title = ctk.CTkLabel(quick_frame, text="🚀 クイック機能", font=self.fonts['body'])
        quick_title.pack(pady=10)
        
        # リアルタイム計算トグル
        self.auto_calc_switch = ctk.CTkSwitch(
            quick_frame,
            text="リアルタイム計算",
            variable=self.auto_calculate,
            command=self.toggle_auto_calculate,
            font=self.fonts['small']
        )
        self.auto_calc_switch.pack(pady=5)
          # テンプレート機能
        template_btn = ctk.CTkButton(
            quick_frame,
            text="📋 テンプレート適用",
            command=self.apply_template,
            width=200,
            font=self.fonts['small']
        )
        template_btn.pack(pady=5)
        
        save_template_btn = ctk.CTkButton(
            quick_frame,
            text="💾 テンプレート保存",
            command=self.save_as_template,
            width=200,
            font=self.fonts['small']
        )
        save_template_btn.pack(pady=5)
        
        # 計算実行ボタン
        self.calculate_btn = ctk.CTkButton(
            quick_frame,
            text="🧮 計算実行",
            command=self.calculate_all, # ここは calculate_all のまま
            width=200,
            height=40,
            font=self.fonts['body'],
            fg_color=self.colors['secondary']
        )
        self.calculate_btn.pack(pady=10)
        
        # 案件リストを更新
        self.refresh_case_list()
    
    def create_main_panel(self):
        """メインパネル（入力・結果表示）"""
        self.main_panel = ctk.CTkFrame(self.content_frame)
        self.main_panel.pack(side="right", fill="both", expand=True)
        
        # タブビューの作成
        self.tabview = ctk.CTkTabview(self.main_panel)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 各タブの作成
        self.create_basic_info_tab()
        self.create_medical_tab()
        self.create_income_tab()
        self.create_results_tab()
        self.create_documents_tab()
    
    def create_basic_info_tab(self):
        """基本情報タブ（改良版）"""
        tab = self.tabview.add("📝 基本情報")
        
        # スクロール可能フレーム
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 案件情報セクション
        case_section = self.create_section(scroll_frame, "📋 案件情報")
        
        # 2列レイアウト
        left_col = ctk.CTkFrame(case_section) # fg_color="transparent" を削除または適切な色に
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_col = ctk.CTkFrame(case_section) # fg_color="transparent" を削除または適切な色に
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))
          # 左列
        self.case_number_entry = self.create_input_field(
            left_col, "案件番号 *", required=True,
            placeholder="例: 2024-001",
            variable_name="case_number", # current_caseの属性名
            auto_calculate=False # 案件番号はリアルタイム計算を無効化
        )        
        self.client_name_entry = self.create_input_field(
            left_col, "依頼者氏名 *", required=True,
            placeholder="姓名を入力",
            variable_name="person_info.name",
            auto_calculate=False # 依頼者氏名もリアルタイム計算を無効化
        )
        
        self.accident_date_picker = self.create_date_picker(
            left_col, "事故発生日 *", required=True,
            variable_name_prefix="accident_info.accident_date" # Y,M,Dのプレフィックス
        )
        
        # 右列
        self.victim_age_entry = self.create_input_field(
            right_col, "被害者年齢（事故時）", 
            placeholder="歳",
            input_type="number",
            variable_name="person_info.age"
        )
        
        self.occupation_dropdown = self.create_dropdown(
            right_col, "職業",
            values=["給与所得者", "事業所得者", "家事従事者", "学生・生徒等", "無職・その他", "幼児・児童"],
            variable_name="person_info.occupation"
        )
        
        self.symptom_fixed_date_picker = self.create_date_picker(
            right_col, "症状固定日",
            variable_name_prefix="accident_info.symptom_fixed_date" # medical_info から accident_info に変更
        )
        
        # 過失・収入情報セクション
        fault_section = self.create_section(scroll_frame, "⚖️ 過失・収入情報")
        
        self.fault_percentage_entry = self.create_input_field(
            fault_section, "被害者過失割合",
            placeholder="%",
            input_type="number",
            variable_name="person_info.fault_percentage"
        )
        
        self.annual_income_entry = self.create_input_field( # このフィールドは IncomeInfo に移動する可能性あり
            fault_section, "事故前年収（実収入）",
            placeholder="円",
            input_type="number",
            variable_name="person_info.annual_income" # income_info から person_info に変更
        )
        
        self.gender_dropdown = self.create_dropdown(
            fault_section, "性別",
            values=["男性", "女性", "その他"],
            variable_name="person_info.gender"
        )
    
    def create_medical_tab(self):
        """医療情報タブ"""
        tab = self.tabview.add("🏥 医療情報")
        
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 入通院情報
        treatment_section = self.create_section(scroll_frame, "🏥 入通院情報")
        
        # 2列レイアウト
        treatment_left_col = ctk.CTkFrame(treatment_section)
        treatment_left_col.pack(side="left", fill="x", expand=True, padx=(0, 5))
        treatment_right_col = ctk.CTkFrame(treatment_section)
        treatment_right_col.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        self.hospital_months_entry = self.create_input_field(
            treatment_left_col, "入院期間", placeholder="ヶ月", input_type="number",
            variable_name="medical_info.hospitalization_months"
        )
        
        self.outpatient_months_entry = self.create_input_field(
            treatment_left_col, "通院期間", placeholder="ヶ月", input_type="number",
            variable_name="medical_info.outpatient_months"
        )
        
        self.actual_outpatient_days_entry = self.create_input_field(
            treatment_right_col, "実通院日数", placeholder="日", input_type="number",
            variable_name="medical_info.actual_outpatient_days"
        )
        
        # むちうち症チェック
        self.whiplash_var = ctk.BooleanVar(value=False) # 初期値をFalseに
        whiplash_check = ctk.CTkCheckBox(
            treatment_section, # 配置場所を調整 (セクション直下)
            text="むちうち症等（他覚症状なし）",
            variable=self.whiplash_var,
            font=self.fonts['body'],
            command=self.schedule_calculation # チェック変更時も計算スケジュール
        )
        whiplash_check.pack(pady=10, anchor="w", padx=15) # 左寄せ
        whiplash_check.variable_name = "medical_info.is_whiplash" # CaseData連携用
        
        # 後遺障害情報
        disability_section = self.create_section(scroll_frame, "♿ 後遺障害情報")
        
        self.disability_grade_dropdown = self.create_dropdown(
            disability_section, "後遺障害等級",
            values=["なし"] + [f"第{i}級" for i in range(1, 15)],
            variable_name="medical_info.disability_grade"
        )
        
        disability_details_label = ctk.CTkLabel(disability_section, text="後遺障害の詳細:", font=self.fonts['body'])
        disability_details_label.pack(anchor="w", padx=15, pady=(10,0))
        self.disability_details_text = ctk.CTkTextbox(
            disability_section,
            height=100,
            font=self.fonts['body']
        )
        self.disability_details_text.pack(fill="x", padx=15, pady=(0,10))
        self.disability_details_text.bind("<KeyRelease>", self.schedule_calculation)
        self.disability_details_text.variable_name = "medical_info.disability_details" # CaseData連携用
        
        # 費用情報
        costs_section = self.create_section(scroll_frame, "💰 医療関係費")
        costs_grid = ctk.CTkFrame(costs_section)
        costs_grid.pack(fill="x", pady=5)
        costs_left_col = ctk.CTkFrame(costs_grid)
        costs_left_col.pack(side="left", fill="x", expand=True, padx=(0,5))
        costs_right_col = ctk.CTkFrame(costs_grid)
        costs_right_col.pack(side="right", fill="x", expand=True, padx=(5,0))

        self.medical_expenses_entry = self.create_input_field(
            costs_left_col, "治療費", placeholder="円", input_type="number",
            variable_name="medical_info.medical_expenses"
        )
        
        self.transportation_costs_entry = self.create_input_field(
            costs_left_col, "通院交通費", placeholder="円", input_type="number",
            variable_name="medical_info.transportation_costs"
        )
        
        self.nursing_costs_entry = self.create_input_field(
            costs_right_col, "付添看護費", placeholder="円", input_type="number",
            variable_name="medical_info.nursing_costs"
        )
        self.other_medical_costs_entry = self.create_input_field(
            costs_right_col, "その他医療関係費", placeholder="円", input_type="number",
            variable_name="medical_info.other_medical_costs"
        )

    def create_income_tab(self):
        """収入・損害タブ"""
        tab = self.tabview.add("💰 収入・損害")
        
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 休業損害
        lost_income_section = self.create_section(scroll_frame, "📉 休業損害")
        lost_income_grid = ctk.CTkFrame(lost_income_section)
        lost_income_grid.pack(fill="x", pady=5)
        lost_income_left = ctk.CTkFrame(lost_income_grid)
        lost_income_left.pack(side="left", fill="x", expand=True, padx=(0,5))
        lost_income_right = ctk.CTkFrame(lost_income_grid)
        lost_income_right.pack(side="right", fill="x", expand=True, padx=(5,0))

        self.lost_work_days_entry = self.create_input_field(
            lost_income_left, "休業日数", placeholder="日", input_type="number",
            variable_name="income_info.lost_work_days"
        )
        
        self.daily_income_entry = self.create_input_field(
            lost_income_right, "日額基礎収入", placeholder="円", input_type="number",
            variable_name="income_info.daily_income"
        )
        
        # 逸失利益
        future_loss_section = self.create_section(scroll_frame, "📊 後遺障害逸失利益")
        future_loss_grid = ctk.CTkFrame(future_loss_section)
        future_loss_grid.pack(fill="x", pady=5)
        future_loss_left = ctk.CTkFrame(future_loss_grid)
        future_loss_left.pack(side="left", fill="x", expand=True, padx=(0,5))
        future_loss_right = ctk.CTkFrame(future_loss_grid)
        future_loss_right.pack(side="right", fill="x", expand=True, padx=(5,0))
        
        self.loss_period_entry = self.create_input_field(
            future_loss_left, "労働能力喪失期間", placeholder="年", input_type="number",
            variable_name="income_info.loss_period_years"
        )
        
        self.retirement_age_entry = self.create_input_field(
            future_loss_left, "就労可能年数上限", placeholder="例: 67歳", input_type="number",
            variable_name="person_info.retirement_age" # PersonInfoへ
        )
        # 自動計算ボタン
        auto_calc_btn = ctk.CTkButton(
            future_loss_left, # 配置場所を調整
            text="喪失期間を症状固定時から上限まで自動計算",
            command=self.auto_calculate_loss_period,
            font=self.fonts['small']
        )
        auto_calc_btn.pack(pady=10, fill="x", padx=10)
        
        self.base_annual_income_entry = self.create_input_field(
            future_loss_right, "基礎年収（逸失利益用）", placeholder="円", input_type="number",
            variable_name="income_info.base_annual_income"
        )
        self.leibniz_rate_entry = self.create_input_field(
            future_loss_right, "ライプニッツ係数", placeholder="自動計算可", input_type="number",
            variable_name="income_info.leibniz_coefficient" # 手入力も可能にする
        )
        leibniz_auto_btn = ctk.CTkButton(
            future_loss_right,
            text="ライプニッツ係数 自動計算",
            command=lambda: self.auto_calculate_leibniz(self.loss_period_entry.get()),
            font=self.fonts['small']
        )
        leibniz_auto_btn.pack(pady=10, fill="x", padx=10)

    def create_results_tab(self):
        """計算結果タブ"""
        tab = self.tabview.add("📊 計算結果")
        
        # 結果表示エリア
        self.results_frame = ctk.CTkScrollableFrame(tab)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # エクスポートボタン
        export_frame = ctk.CTkFrame(tab, height=60)
        export_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        export_frame.pack_propagate(False)
        
        # PDF出力
        pdf_btn = ctk.CTkButton(
            export_frame,
            text="📄 PDF出力",
            command=self.export_pdf,
            width=120,
            font=self.fonts['body']
        )
        pdf_btn.pack(side="left", padx=10, pady=15)
        
        # Excel出力
        excel_btn = ctk.CTkButton(
            export_frame,
            text="📊 Excel出力",
            command=self.export_excel,
            width=120,
            font=self.fonts['body']
        )
        excel_btn.pack(side="left", padx=10, pady=15)
        
        # 印刷
        print_btn = ctk.CTkButton(
            export_frame,
            text="🖨️ 印刷",
            command=self.print_results,
            width=120,
            font=self.fonts['body']
        )
        print_btn.pack(side="left", padx=10, pady=15)
    
    def create_documents_tab(self):
        """書類管理タブ"""
        tab = self.tabview.add("📎 書類管理")
        
        # ファイル管理エリア
        files_frame = ctk.CTkScrollableFrame(tab)
        files_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ファイル操作ボタン
        file_ops_frame = ctk.CTkFrame(tab, height=60)
        file_ops_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        file_ops_frame.pack_propagate(False)
        
        upload_btn = ctk.CTkButton(
            file_ops_frame,
            text="📎 ファイル追加",
            command=self.upload_file,
            width=120,
            font=self.fonts['body']
        )
        upload_btn.pack(side="left", padx=10, pady=15)
    
    def create_status_bar(self):
        """ステータスバー"""
        self.status_bar = ctk.CTkFrame(self.main_container, height=30)
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        self.status_bar.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="準備完了",
            font=self.fonts['small']
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        # 最終更新時刻
        self.last_saved_label = ctk.CTkLabel(
            self.status_bar,
            text="",
            font=self.fonts['small']
        )
        self.last_saved_label.pack(side="right", padx=10, pady=5)
    
    # ヘルパーメソッド
    def create_section(self, parent, title: str) -> ctk.CTkFrame:
        """セクションフレームを作成"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=15)
        
        title_label = ctk.CTkLabel(section, text=title, font=self.fonts['subtitle'])
        title_label.pack(anchor="w", padx=15, pady=10)
        
        return section
    
    def create_input_field(self, parent, label: str, required: bool = False, 
                          placeholder: str = "", input_type: str = "text", variable_name: str = None, auto_calculate: bool = True) -> ctk.CTkEntry:
        """入力フィールドを作成"""
        field_frame = ctk.CTkFrame(parent)
        field_frame.pack(fill="x", padx=15, pady=5)
        
        label_text = f"{label} {'*' if required else ''}"
        field_label = ctk.CTkLabel(field_frame, text=label_text, font=self.fonts['body'])
        field_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        entry = ctk.CTkEntry(
            field_frame,
            font=self.fonts['body']
        )
        entry.pack(fill="x", padx=10, pady=(0, 10))
        
        if variable_name: # variable_name をウィジェットに保存
            entry.variable_name = variable_name

        # リアルタイム計算のトリガー (auto_calculateがTrueの場合のみ)
        if auto_calculate:
            entry.bind("<KeyRelease>", self.schedule_calculation)
        
        return entry

    def create_dropdown(self, parent, label: str, values: list, variable_name: str = None) -> ctk.CTkComboBox:
        """ドロップダウンを作成"""
        field_frame = ctk.CTkFrame(parent)
        field_frame.pack(fill="x", padx=15, pady=5)
        
        field_label = ctk.CTkLabel(field_frame, text=label, font=self.fonts['body'])
        field_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        dropdown = ctk.CTkComboBox(
            field_frame,
            values=values,
            font=self.fonts['body'],
            state="readonly" # 手入力不可にする場合
        )
        dropdown.pack(fill="x", padx=10, pady=(0, 10))
        
        if variable_name: # variable_name をウィジェットに保存
            dropdown.variable_name = variable_name
        
        dropdown.bind("<<ComboboxSelected>>", self.schedule_calculation) # 選択変更時にも計算をスケジュール
        return dropdown

    def create_date_picker(self, parent, label: str, required: bool = False, variable_name_prefix: str = None) -> Dict[str, ctk.CTkComboBox]:
        """日付選択を作成"""
        field_frame = ctk.CTkFrame(parent)
        field_frame.pack(fill="x", padx=15, pady=5)
        
        label_text = f"{label} {'*' if required else ''}"
        field_label = ctk.CTkLabel(field_frame, text=label_text, font=self.fonts['body'])
        field_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        date_frame = ctk.CTkFrame(field_frame) # fg_color="transparent" を削除または適切な色に
        date_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # 年月日のドロップダウン
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 100, current_year + 5)] # 年の範囲を広げる
        months = [f"{m:02d}" for m in range(1, 13)]
        days = [f"{d:02d}" for d in range(1, 32)]

        year_combo = ctk.CTkComboBox(date_frame, values=years, width=100, state="readonly") # 幅調整
        year_combo.pack(side="left", padx=(0, 5))
        
        month_combo = ctk.CTkComboBox(date_frame, values=months, width=70, state="readonly") # 幅調整
        month_combo.pack(side="left", padx=5)
        
        day_combo = ctk.CTkComboBox(date_frame, values=days, width=70, state="readonly") # 幅調整
        day_combo.pack(side="left", padx=5)

        if variable_name_prefix: # variable_name_prefix を各コンボボックスに保存
            year_combo.variable_name = f"{variable_name_prefix}_year"
            month_combo.variable_name = f"{variable_name_prefix}_month"
            day_combo.variable_name = f"{variable_name_prefix}_day"
            
        for combo in [year_combo, month_combo, day_combo]:
            combo.bind("<<ComboboxSelected>>", self.schedule_calculation)

        return {"year": year_combo, "month": month_combo, "day": day_combo}

    # イベントハンドラー
    def schedule_calculation(self, event=None):
        """リアルタイム計算のスケジューリング"""
        if self.calculation_timer:
            self.root.after_cancel(self.calculation_timer)
        
        # 500ms後に計算実行（ユーザーの入力を待つ）
        self.calculation_timer = self.root.after(500, self.calculate_all)
    
    def toggle_auto_calculate(self):
        """リアルタイム計算のオン/オフ"""
        if self.auto_calculate.get():
            self.status_label.configure(text="リアルタイム計算: ON")
        else:
            self.status_label.configure(text="リアルタイム計算: OFF")
    
    # 案件管理メソッド
    def new_case(self):
        """新規案件作成"""
        if messagebox.askyesno("確認", "現在の入力内容を破棄し、新しい案件を作成しますか？", icon=messagebox.WARNING):
            self.current_case = CaseData() # 新しいCaseDataインスタンス
            self.clear_all_inputs()
            self.status_label.configure(text="新規案件")
            self.last_saved_label.configure(text="")
            # 必要であれば案件リストも更新（選択解除など）
            self.refresh_case_list() # 案件リストをリフレッシュして選択状態をクリアするイメージ

    def save_case(self):
        """案件保存"""
        # 必須フィールドの検証を先に行う
        if not self.validate_required_fields():
            return

        # UIからデータを更新し、その際に発生した検証エラーもチェック
        if not self.update_case_data_from_ui(): # update_case_data_from_ui が False を返したらエラー
            # update_case_data_from_ui 内で既にエラーメッセージは表示されているはず
            self.status_label.configure(text="入力内容にエラーがあります。修正してください。")
            return
        
        is_new_case = not self.current_case.id  # DBに保存されていなければ新規

        if is_new_case and not self.current_case.case_number:
            # validate_required_fields で案件番号はチェックされるはずだが、念のため
            # 新規案件で案件番号が空の場合は、ここで再度促すか、エラーとする
            # ここでは validate_required_fields を信頼し、案件番号は入力済みと仮定
            pass # 案件番号は validate_required_fields でチェック済み

        # 案件番号が設定されていることを再度確認 (特に新規の場合)
        if not self.current_case.case_number:
            messagebox.showerror("保存エラー", "案件番号が設定されていません。案件番号を入力してください。")
            if hasattr(self, 'case_number_entry'):
                self.case_number_entry.focus_set()
            return

        try:
            saved_case_id = self.db_manager.save_case(self.current_case)
            if saved_case_id:
                self.current_case.id = saved_case_id
                self.current_case.last_modified = datetime.now()
                self.status_label.configure(text=f"案件 '{self.current_case.case_number}' を保存しました")
                self.last_saved_label.configure(text=f"最終保存: {self.current_case.last_modified.strftime('%H:%M:%S')}")
                self.refresh_case_list()
            else:
                messagebox.showerror("エラー", "案件の保存に失敗しました。データベースを確認してください。")
        except Exception as e:
            self.logger.error(f"案件保存中にエラー: {e}", exc_info=True)
            messagebox.showerror("重大なエラー", f"案件の保存中に予期せぬエラーが発生しました: {str(e)}")

    def load_case(self):
        """案件読み込み（ダイアログ経由）"""
        messagebox.showinfo("案件読み込み", "左側の案件リストから読み込む案件を選択し、「読込」ボタンを押してください。")


    def refresh_case_list(self):
        """案件リストの更新"""
        for widget in self.case_list_frame.winfo_children():
            widget.destroy()
        
        try:
            search_term = self.search_entry.get() if hasattr(self, 'search_entry') else ""
            cases = self.db_manager.search_cases(search_term=search_term, limit=50) 
            
            if not cases:
                no_case_label = ctk.CTkLabel(self.case_list_frame, text="該当する案件はありません", font=self.fonts['small'])
                no_case_label.pack(pady=10)
                return

            for case_summary in cases: 
                case_id = case_summary.get('id') 
                display_text = f"{case_summary.get('case_number', 'N/A')}\n{case_summary.get('client_name', 'N/A')}"
                
                case_item_frame = ctk.CTkFrame(self.case_list_frame, corner_radius=5) 
                case_item_frame.pack(fill="x", pady=3, padx=5)
                
                case_label = ctk.CTkLabel(
                    case_item_frame,
                    text=display_text,
                    font=self.fonts['small'],
                    anchor="w",
                    justify="left"
                )
                case_label.pack(side="left", padx=10, pady=5, expand=True, fill="x")
                
                load_button = ctk.CTkButton(
                    case_item_frame,
                    text="読込",
                    width=60,
                    font=self.fonts['small'],
                    command=lambda c_id=case_id: self.load_case_by_id(c_id) 
                )
                load_button.pack(side="right", padx=10, pady=5)
        except Exception as e:
            self.logger.error(f"案件リストの更新中にエラー: {e}")
            error_label = ctk.CTkLabel(self.case_list_frame, text="案件リストの読み込みに失敗しました。", font=self.fonts['small'], text_color="red")
            error_label.pack(pady=10)


    def load_case_by_id(self, case_id: int): 
        """案件IDで案件を読み込み"""
        if self.current_case and self.current_case.id == case_id: # 同じ案件を再度読み込もうとした場合
            messagebox.showinfo("情報", "選択された案件は既に表示中です。")
            return

        if messagebox.askyesno("確認", "現在の入力内容を破棄し、選択した案件を読み込みますか？", icon=messagebox.WARNING):
            try:
                case_data_dict = self.db_manager.load_case_by_id(case_id) 
                if case_data_dict:
                    self.current_case = CaseData.from_dict(case_data_dict) 
                    self.load_case_data_to_ui() # これでlast_modifiedもUIに反映される
                    self.status_label.configure(text=f"案件 '{self.current_case.case_number}' を読み込みました")
                    # self.last_saved_label は load_case_data_to_ui 内で更新される
                else:
                    messagebox.showerror("エラー", f"ID {case_id} の案件が見つかりません。")
            except Exception as e:
                self.logger.error(f"案件 (ID: {case_id}) の読み込み中にエラー: {e}")
                messagebox.showerror("エラー", f"案件の読み込み中に予期せぬエラーが発生しました: {e}")
    
    def _get_widget_value(self, widget):
        if widget is None: return None # ウィジェットが存在しない場合
        if isinstance(widget, ctk.CTkEntry):
            return widget.get()
        elif isinstance(widget, ctk.CTkComboBox):
            return widget.get()
        elif isinstance(widget, ctk.CTkCheckBox): # チェックボックス対応
            return widget.get() # BooleanVar().get() のように取得できるはず
        elif isinstance(widget, ctk.CTkTextbox): # テキストボックス対応
            return widget.get("1.0", tk.END).strip()
        return None

    def _set_widget_value(self, widget, value):
        if widget is None: return # ウィジェットが存在しない場合
        
        if isinstance(widget, ctk.CTkEntry):
            current_val = widget.get()
            if current_val != str(value if value is not None else ""):
                 widget.delete(0, tk.END)
                 widget.insert(0, str(value if value is not None else ""))
        elif isinstance(widget, ctk.CTkComboBox):
            str_value = str(value if value is not None else "")
            if str_value in widget.cget("values"):
                 if widget.get() != str_value: widget.set(str_value)
            elif widget.cget("values"): # 値リストがあり、該当がない場合
                 if widget.get() != "": widget.set("") # 空にするか、最初の値にする
            else: # 値リストが空の場合
                 if widget.get() != "": widget.set("")
        elif isinstance(widget, ctk.CTkCheckBox): # チェックボックス対応
            if isinstance(value, bool):
                if widget.get() != value: widget.set(value) # BooleanVar().set()
            elif value is not None: # bool以外だがNoneでない場合、Trueとみなすか要検討
                if widget.get() != bool(value): widget.set(bool(value))
        elif isinstance(widget, ctk.CTkTextbox): # テキストボックス対応
            current_val = widget.get("1.0", tk.END).strip()
            new_val = str(value if value is not None else "")
            if current_val != new_val:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", new_val)
    
    def _get_date_from_picker(self, picker: Dict[str, ctk.CTkComboBox]) -> Optional[date]: # Changed return type
        if not picker or not all(key in picker for key in ['year', 'month', 'day']):
            self.logger.warning("日付ピッカーの構造が不正です。")
            return None
        try:
            year_widget = picker.get('year')
            month_widget = picker.get('month')
            day_widget = picker.get('day')

            if not (year_widget and month_widget and day_widget):
                return None

            year_str = year_widget.get()
            month_str = month_widget.get()
            day_str = day_widget.get()
            
            if year_str and month_str and day_str:
                # 日付の妥当性チェック (ValueErrorを捕捉)
                return date(int(year_str), int(month_str), int(day_str))
            elif not year_str and not month_str and not day_str: # 全て空なら未入力
                return None
            else: # 一部だけ入力されている場合はエラー
                self.logger.warning(f"日付の一部のみ入力されています: Y:{year_str}, M:{month_str}, D:{day_str}")
                # messagebox.showwarning は呼び出し元で行う
                return None # 部分的な入力は無効としてNoneを返す
        except ValueError: # 無効な日付 (例: 2月30日)
            self.logger.warning(f"無効な日付が入力されました: {year_str}-{month_str}-{day_str}")
            # messagebox.showwarning は呼び出し元で行う
            return None # 無効な日付はNoneを返す
        except KeyError:
            self.logger.warning("日付ピッカーのキーが不正です。")
        except Exception as e:
            self.logger.error(f"日付ピッカーからの日付取得エラー: {e}")
        return None

    def _set_date_to_picker(self, picker: Dict[str, ctk.CTkComboBox], date_str: Optional[str]):
        if not picker or not all(key in picker for key in ['year', 'month', 'day']):
            return

        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                if picker['year'].get() != str(dt.year): picker['year'].set(str(dt.year))
                if picker['month'].get() != f"{dt.month:02d}": picker['month'].set(f"{dt.month:02d}")
                if picker['day'].get() != f"{dt.day:02d}": picker['day'].set(f"{dt.day:02d}")
                return
            except (ValueError, TypeError) as e:
                self.logger.warning(f"日付文字列 '{date_str}' の解析に失敗: {e}")
        # クリア処理
        if picker['year'].get() != "": picker['year'].set("")
        if picker['month'].get() != "": picker['month'].set("")
        if picker['day'].get() != "": picker['day'].set("")

    def update_case_data_from_ui(self) -> bool: # 返り値をboolに統一
        """UIから案件データを更新し、検証を行う"""
        if not self.current_case:
            self.current_case = CaseData()

        error_messages = []

        # Helper function for parsing and validating decimals
        def parse_decimal(widget_attr: str, field_name: str, allow_negative: bool = False, min_val: Optional[Decimal] = None, max_val: Optional[Decimal] = None) -> Optional[Decimal]:
            val_str = self._get_widget_value(getattr(self, widget_attr, None))
            if not val_str:
                return Decimal('0') # 空の場合は0として扱うか、フィールドによってNoneを許容するか検討
            try:
                val = Decimal(val_str)
                if not allow_negative and val < Decimal('0'):
                    error_messages.append(f"{field_name}には正の数を入力してください。")
                    return None
                if min_val is not None and val < min_val:
                    error_messages.append(f"{field_name}は{min_val}以上である必要があります。")
                    return None
                if max_val is not None and val > max_val:
                    error_messages.append(f"{field_name}は{max_val}以下である必要があります。")
                    return None
                return val
            except InvalidOperation:
                error_messages.append(f"{field_name}には有効な数値を入力してください。")
                return None

        # Helper function for parsing and validating integers
        def parse_int(widget_attr: str, field_name: str, allow_negative: bool = False, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
            val_str = self._get_widget_value(getattr(self, widget_attr, None))
            if not val_str: # 空の場合は0として扱う
                return 0
            try:
                val = int(val_str)
                if not allow_negative and val < 0:
                    error_messages.append(f"{field_name}には正の整数を入力してください。")
                    return None
                if min_val is not None and val < min_val:
                    error_messages.append(f"{field_name}は{min_val}以上である必要があります。")
                    return None
                if max_val is not None and val > max_val:
                    error_messages.append(f"{field_name}は{max_val}以下である必要があります。")
                    return None
                return val
            except (ValueError, TypeError):
                error_messages.append(f"{field_name}には有効な整数を入力してください。")
                return None

        # 基本情報タブ
        self.current_case.case_number = self._get_widget_value(getattr(self, 'case_number_entry', None))
        self.current_case.person_info.name = self._get_widget_value(getattr(self, 'client_name_entry', None))
        
        age_val = parse_int('victim_age_entry', "被害者年齢（事故時）", min_val=0, max_val=150)
        if age_val is not None: self.current_case.person_info.age = age_val
        else: self.current_case.person_info.age = 0 # エラー時はデフォルト値

        self.current_case.person_info.occupation = self._get_widget_value(getattr(self, 'occupation_dropdown', None))
        self.current_case.person_info.gender = self._get_widget_value(getattr(self, 'gender_dropdown', None))
        
        fault_val = parse_int('fault_percentage_entry', "被害者過失割合", min_val=0, max_val=100)
        if fault_val is not None: self.current_case.person_info.fault_percentage = fault_val
        else: self.current_case.person_info.fault_percentage = 0
        
        # 事故発生日の処理
        acc_date_picker_widget = getattr(self, 'accident_date_picker', None)
        acc_date_obj = self._get_date_from_picker(acc_date_picker_widget)
        raw_year_acc = acc_date_picker_widget['year'].get() if acc_date_picker_widget and acc_date_picker_widget.get('year') else ""
        raw_month_acc = acc_date_picker_widget['month'].get() if acc_date_picker_widget and acc_date_picker_widget.get('month') else ""
        raw_day_acc = acc_date_picker_widget['day'].get() if acc_date_picker_widget and acc_date_picker_widget.get('day') else ""

        if acc_date_obj:
            self.current_case.accident_info.accident_date = acc_date_obj.strftime("%Y-%m-%d")
        elif raw_year_acc or raw_month_acc or raw_day_acc: # 何か入力があったが、無効だった場合
            error_messages.append("事故発生日の形式が無効です。正しい日付を入力してください。")
            self.current_case.accident_info.accident_date = None
        else: # 全て空欄
            self.current_case.accident_info.accident_date = None

        # 症状固定日の処理
        sym_date_picker_widget = getattr(self, 'symptom_fixed_date_picker', None)
        sym_date_obj = self._get_date_from_picker(sym_date_picker_widget)
        raw_year_sym = sym_date_picker_widget['year'].get() if sym_date_picker_widget and sym_date_picker_widget.get('year') else ""
        raw_month_sym = sym_date_picker_widget['month'].get() if sym_date_picker_widget and sym_date_picker_widget.get('month') else ""
        raw_day_sym = sym_date_picker_widget['day'].get() if sym_date_picker_widget and sym_date_picker_widget.get('day') else ""

        if sym_date_obj:
            self.current_case.accident_info.symptom_fixed_date = sym_date_obj.strftime("%Y-%m-%d")
        elif raw_year_sym or raw_month_sym or raw_day_sym: # 何か入力があったが、無効だった場合
            error_messages.append("症状固定日の形式が無効です。正しい日付を入力してください。")
            self.current_case.accident_info.symptom_fixed_date = None
        else: # 全て空欄
            self.current_case.accident_info.symptom_fixed_date = None

        # 日付の論理チェック (両方の日付が有効な場合のみ)
        if acc_date_obj and sym_date_obj:
            if sym_date_obj < acc_date_obj:
                error_messages.append("症状固定日は事故発生日より後の日付である必要があります。")
        
        annual_income_val = parse_decimal('annual_income_entry', "事故前年収（実収入）")
        if annual_income_val is not None: self.current_case.person_info.annual_income = annual_income_val
        else: self.current_case.person_info.annual_income = Decimal('0')
        
        # 医療情報タブ
        hospital_months_val = parse_int('hospital_months_entry', "入院期間", min_val=0)
        if hospital_months_val is not None: self.current_case.medical_info.hospital_months = hospital_months_val
        else: self.current_case.medical_info.hospital_months = 0

        outpatient_months_val = parse_int('outpatient_months_entry', "通院期間", min_val=0)
        if outpatient_months_val is not None: self.current_case.medical_info.outpatient_months = outpatient_months_val
        else: self.current_case.medical_info.outpatient_months = 0
        
        actual_outpatient_days_val = parse_int('actual_outpatient_days_entry', "実通院日数", min_val=0)
        if actual_outpatient_days_val is not None: self.current_case.medical_info.actual_outpatient_days = actual_outpatient_days_val
        else: self.current_case.medical_info.actual_outpatient_days = 0

        if hasattr(self, 'whiplash_var'):
             self.current_case.medical_info.is_whiplash = self.whiplash_var.get()
        
        grade_str = self._get_widget_value(getattr(self, 'disability_grade_dropdown', None))
        if grade_str == "なし": self.current_case.medical_info.disability_grade = 0
        elif grade_str:
            try: self.current_case.medical_info.disability_grade = int(grade_str.replace("第","").replace("級",""))
            except (ValueError, TypeError): 
                error_messages.append("後遺障害等級の形式が無効です。")
                self.current_case.medical_info.disability_grade = 0
        else: self.current_case.medical_info.disability_grade = 0
        
        self.current_case.medical_info.disability_details = self._get_widget_value(getattr(self, 'disability_details_text', None))
        
        medical_fields_to_parse = [
            ('medical_expenses_entry', 'medical_expenses', "治療費"), 
            ('transportation_costs_entry', 'transportation_costs', "通院交通費"),
            ('nursing_costs_entry', 'nursing_costs', "付添看護費"),
            ('other_medical_costs_entry', 'other_medical_costs', "その他医療関係費")
        ]
        for widget_attr, model_attr, field_name in medical_fields_to_parse:
            val = parse_decimal(widget_attr, field_name)
            if val is not None: setattr(self.current_case.medical_info, model_attr, val)
            else: setattr(self.current_case.medical_info, model_attr, Decimal('0'))

        # 収入・損害タブ
        lost_work_days_val = parse_int('lost_work_days_entry', "休業日数", min_val=0)
        if lost_work_days_val is not None: self.current_case.income_info.lost_work_days = lost_work_days_val
        else: self.current_case.income_info.lost_work_days = 0
        
        daily_income_val = parse_decimal('daily_income_entry', "日額基礎収入")
        if daily_income_val is not None: self.current_case.income_info.daily_income = daily_income_val
        else: self.current_case.income_info.daily_income = Decimal('0')

        loss_period_years_val = parse_int('loss_period_entry', "労働能力喪失期間", min_val=0, max_val=100) #妥当な上限を設定
        if loss_period_years_val is not None: self.current_case.income_info.loss_period_years = loss_period_years_val
        else: self.current_case.income_info.loss_period_years = 0
        
        retirement_age_val = parse_int('retirement_age_entry', "就労可能年数上限", min_val=0, max_val=120)
        if retirement_age_val is not None: self.current_case.person_info.retirement_age = retirement_age_val
        else: self.current_case.person_info.retirement_age = 0 # デフォルトは67歳だが、入力エラー時は0

        base_annual_income_val = parse_decimal('base_annual_income_entry', "基礎年収（逸失利益用）")
        if base_annual_income_val is not None: self.current_case.income_info.base_annual_income = base_annual_income_val
        else: self.current_case.income_info.base_annual_income = Decimal('0')
        
        leibniz_val_str = self._get_widget_value(getattr(self, 'leibniz_rate_entry', None))
        if not leibniz_val_str: # 空ならNone
            self.current_case.income_info.leibniz_coefficient = None
        else:
            try:
                leibniz_decimal = Decimal(leibniz_val_str)
                if leibniz_decimal < Decimal('0'):
                     error_messages.append("ライプニッツ係数には正の数を入力してください。")
                     self.current_case.income_info.leibniz_coefficient = None
                else:
                     self.current_case.income_info.leibniz_coefficient = leibniz_decimal
            except InvalidOperation:
                error_messages.append("ライプニッツ係数には有効な数値を入力してください。")
                self.current_case.income_info.leibniz_coefficient = None
        
        self.current_case.last_modified = datetime.now() # last_modified を updated_at から変更

        if error_messages:
            messagebox.showerror("入力エラー", "\\n".join(error_messages))
            return False # 検証エラーあり
        return True # 更新成功

    def load_case_data_to_ui(self):
        """案件データをUIに読み込み"""
        if not self.current_case:
            self.clear_all_inputs()
            return

        # 基本情報タブ
        self._set_widget_value(getattr(self, 'case_number_entry', None), self.current_case.case_number)
        self._set_widget_value(getattr(self, 'client_name_entry', None), self.current_case.person_info.name)
        self._set_widget_value(getattr(self, 'victim_age_entry', None), self.current_case.person_info.age)
        self._set_widget_value(getattr(self, 'occupation_dropdown', None), self.current_case.person_info.occupation)
        self._set_widget_value(getattr(self, 'gender_dropdown', None), self.current_case.person_info.gender)
        self._set_widget_value(getattr(self, 'fault_percentage_entry', None), self.current_case.person_info.fault_percentage)
        
        self._set_date_to_picker(getattr(self, 'accident_date_picker', None), self.current_case.accident_info.accident_date)
        self._set_date_to_picker(getattr(self, 'symptom_fixed_date_picker', None), self.current_case.accident_info.symptom_fixed_date)

        # 収入情報 (PersonInfoから取得)
        self._set_widget_value(getattr(self, 'annual_income_entry', None), self.current_case.person_info.annual_income)

        # 医療情報タブ
        self._set_widget_value(getattr(self, 'hospital_months_entry', None), self.current_case.medical_info.hospital_months) # medical_info.hospitalization_months を medical_info.hospital_months に変更
        self._set_widget_value(getattr(self, 'outpatient_months_entry', None), self.current_case.medical_info.outpatient_months)
        self._set_widget_value(getattr(self, 'actual_outpatient_days_entry', None), self.current_case.medical_info.actual_outpatient_days)
        
        if hasattr(self, 'whiplash_var') and self.current_case.medical_info.is_whiplash is not None:
             current_check_val = bool(self.whiplash_var.get()) # bool型に変換
             if current_check_val != self.current_case.medical_info.is_whiplash:
                 self.whiplash_var.set(self.current_case.medical_info.is_whiplash)

        if hasattr(self, 'disability_grade_dropdown'):
            grade = self.current_case.medical_info.disability_grade
            grade_text = f"第{grade}級" if grade and grade > 0 else "なし"
            if self.disability_grade_dropdown.get() != grade_text: self.disability_grade_dropdown.set(grade_text)
        
        self._set_widget_value(getattr(self, 'disability_details_text', None), self.current_case.medical_info.disability_details)

        for field, attr in [('medical_expenses_entry', 'medical_expenses'), 
                            ('transportation_costs_entry', 'transportation_costs'),
                            ('nursing_costs_entry', 'nursing_costs'),
                            ('other_medical_costs_entry', 'other_medical_costs')]: # other_medical_costs_entry を追加
            self._set_widget_value(getattr(self, field, None), getattr(self.current_case.medical_info, attr, Decimal('0')))

        # 収入・損害タブ
        self._set_widget_value(getattr(self, 'lost_work_days_entry', None), self.current_case.income_info.lost_work_days)
        self._set_widget_value(getattr(self, 'daily_income_entry', None), self.current_case.income_info.daily_income)
        self._set_widget_value(getattr(self, 'loss_period_entry', None), self.current_case.income_info.loss_period_years)
        self._set_widget_value(getattr(self, 'retirement_age_entry', None), self.current_case.person_info.retirement_age)
        self._set_widget_value(getattr(self, 'base_annual_income_entry', None), self.current_case.income_info.base_annual_income)
        self._set_widget_value(getattr(self, 'leibniz_rate_entry', None), self.current_case.income_info.leibniz_coefficient)

        self.status_label.configure(text=f"案件 '{self.current_case.case_number}' を表示中")
        updated_at_str = self.current_case.last_modified.strftime('%Y-%m-%d %H:%M:%S') if self.current_case.last_modified else 'N/A' # updated_at を last_modified に変更
        self.last_saved_label.configure(text=f"最終更新: {updated_at_str}")


    def clear_all_inputs(self):
        """すべてのUI入力をクリア"""
        # 基本情報タブ
        for attr_name in ["case_number_entry", "client_name_entry", "victim_age_entry", 
                          "occupation_dropdown", "gender_dropdown", "fault_percentage_entry",
                          "annual_income_entry"]: 
            self._set_widget_value(getattr(self, attr_name, None), "")

        self._set_date_to_picker(getattr(self, 'accident_date_picker', None), None)
        self._set_date_to_picker(getattr(self, 'symptom_fixed_date_picker', None), None)

        # 医療情報タブ
        for attr_name in ["hospital_months_entry", "outpatient_months_entry", "actual_outpatient_days_entry",
                          "medical_expenses_entry", "transportation_costs_entry", "nursing_costs_entry",
                          "other_medical_costs_entry"]:
            self._set_widget_value(getattr(self, attr_name, None), "")
        
        if hasattr(self, 'whiplash_var'): self.whiplash_var.set(False)
        if hasattr(self, 'disability_grade_dropdown'): self.disability_grade_dropdown.set("なし")
        self._set_widget_value(getattr(self, 'disability_details_text', None), "")


        # 収入・損害タブ
        for attr_name in ["lost_work_days_entry", "daily_income_entry", "loss_period_entry",
                          "retirement_age_entry", "base_annual_income_entry", "leibniz_rate_entry"]:
            self._set_widget_value(getattr(self, attr_name, None), "")
        
        if hasattr(self, 'results_frame'):
            for widget in self.results_frame.winfo_children():
                widget.destroy()
        
        self.status_label.configure(text="入力フィールドをクリアしました")


    def validate_required_fields(self) -> bool:
        """必須フィールドの検証"""
        error_messages = []
        # (フィールド名, ウィジェット属性名, フォーカス先ウィジェット属性名 (オプション))
        required_field_checks = [
            ("案件番号", 'case_number_entry'),
            ("依頼者氏名", 'client_name_entry'),
            # ("被害者年齢（事故時）", 'victim_age_entry'), # 年齢は必須ではない場合もある
        ]

        # _first_error_widget_to_focus を初期化
        if hasattr(self, '_first_error_widget_to_focus'):
            delattr(self, '_first_error_widget_to_focus')

        for label, widget_attr, *_ in required_field_checks:
            widget = getattr(self, widget_attr, None)
            if widget and not self._get_widget_value(widget).strip():
                error_messages.append(f"{label} は必須です。")
                if not hasattr(self, '_first_error_widget_to_focus'):
                     self._first_error_widget_to_focus = widget

        # 事故発生日の必須チェック
        acc_date_picker_widget = getattr(self, 'accident_date_picker', None)
        acc_date_obj = self._get_date_from_picker(acc_date_picker_widget) # _get_date_from_picker は無効な場合Noneを返す

        raw_year_acc = acc_date_picker_widget['year'].get() if acc_date_picker_widget and acc_date_picker_widget.get('year') else ""
        raw_month_acc = acc_date_picker_widget['month'].get() if acc_date_picker_widget and acc_date_picker_widget.get('month') else ""
        raw_day_acc = acc_date_picker_widget['day'].get() if acc_date_picker_widget and acc_date_picker_widget.get('day') else ""

        if not acc_date_obj: # 日付オブジェクトが取得できなかった (空または無効)
            if not (raw_year_acc or raw_month_acc or raw_day_acc): # 全ての年月日フィールドが空の場合
                 error_messages.append("事故発生日は必須です。")
            else: # 何か入力があるが日付として無効な場合
                 error_messages.append("事故発生日の形式が無効です。正しい日付を入力してください。")
            
            if not hasattr(self, '_first_error_widget_to_focus') and acc_date_picker_widget and acc_date_picker_widget.get('year'):
                self._first_error_widget_to_focus = acc_date_picker_widget['year']
        
        # 症状固定日は必須ではないが、入力されていれば形式をチェック (update_case_data_from_ui でエラーメッセージ追加)
        # sym_date_picker_widget = getattr(self, 'symptom_fixed_date_picker', None)
        # sym_date_obj = self._get_date_from_picker(sym_date_picker_widget)
        # raw_year_sym = sym_date_picker_widget['year'].get() if sym_date_picker_widget and sym_date_picker_widget.get('year') else ""
        # raw_month_sym = sym_date_picker_widget['month'].get() if sym_date_picker_widget and sym_date_picker_widget.get('month') else ""
        # raw_day_sym = sym_date_picker_widget['day'].get() if sym_date_picker_widget and sym_date_picker_widget.get('day') else ""
        # if not sym_date_obj and (raw_year_sym or raw_month_sym or raw_day_sym):
        #     error_messages.append("症状固定日の形式が無効です。正しい日付を入力してください。")
        #     if not hasattr(self, '_first_error_widget_to_focus') and sym_date_picker_widget and sym_date_picker_widget.get('year'):
        #         self._first_error_widget_to_focus = sym_date_picker_widget['year']


        if error_messages:
            messagebox.showerror("入力エラー", "\\\\n".join(error_messages))
            if hasattr(self, '_first_error_widget_to_focus') and self._first_error_widget_to_focus:
                self._first_error_widget_to_focus.focus_set()
                delattr(self, '_first_error_widget_to_focus') # 一時変数を削除
            return False
        return True
    
    # 計算・出力メソッド
    def calculate_all(self):
        """全項目計算"""
        # 1. 必須フィールドの検証
        if not self.validate_required_fields():
            self.status_label.configure(text="入力エラー: 必須項目を確認してください。")
            # validate_required_fields内でエラーメッセージ表示とフォーカス設定済み
            return

        # 2. UIからデータをcurrent_caseに更新し、その際の詳細な入力値検証も行う
        # update_case_data_from_ui は内部でエラーメッセージを表示し、問題があれば False を返す
        if not self.update_case_data_from_ui(): 
            self.status_label.configure(text="入力エラー: 各項目の入力値を確認してください。")
            # update_case_data_from_ui内でエラーメッセージ表示とフォーカス設定の試みがあるかもしれない
            return
            
        # 3. 計算の実行と結果表示
        try:
            # calculation_engine.calculate_all に渡すのは更新済みの self.current_case
            results = self.calculation_engine.calculate_all(self.current_case)
            
            if results: # 計算結果が得られた場合
                self.display_results(results)
                self.status_label.configure(text="計算完了")
                # 計算結果をcurrent_caseにも保存（PDF/Excel出力時の一貫性のため）
                if isinstance(results, dict) and all(isinstance(v, CalculationResult) for v in results.values()):
                    self.current_case.calculation_results = {k: v.to_dict() for k, v in results.items()}
                else:
                    self.logger.warning("calculate_all から予期しない形式の結果が返されました。")
                    # 必要であれば、ここで calculation_results を空にするなどの処理
                    self.current_case.calculation_results = {} 
            else: # 計算結果がNoneや空だった場合（エンジン側でエラー処理された可能性）
                self.logger.warning("CalculationEngine.calculate_all が結果を返しませんでした。")
                # 結果フレームをクリアするなどの処理が必要か検討
                if hasattr(self, 'results_frame'):
                    for widget in self.results_frame.winfo_children():
                        widget.destroy()
                    ctk.CTkLabel(self.results_frame, text="計算結果を取得できませんでした。入力内容を確認してください。", font=self.fonts['body']).pack(pady=10)
                self.status_label.configure(text="計算エラー: 結果を取得できませんでした。")

        except Exception as e:
            self.logger.error(f"計算中に予期せぬエラーが発生: {e}", exc_info=True)
            messagebox.showerror("計算エラー", f"計算中に予期せぬエラーが発生しました。\n詳細はログファイルを確認してください。\nエラー: {str(e)}")
            self.status_label.configure(text="計算エラー: 予期せぬ問題が発生しました。")
            # 結果表示エリアをクリアまたはエラーメッセージ表示
            if hasattr(self, 'results_frame'):
                for widget in self.results_frame.winfo_children():
                    widget.destroy()
                ctk.CTkLabel(self.results_frame, text=f"計算エラーが発生しました。\n{str(e)}", font=self.fonts['body'], text_color="red").pack(pady=10)

    def display_results(self, results: Dict[str, CalculationResult]):
        """計算結果を表示"""
        if not hasattr(self, 'results_frame'):
            self.logger.warning("results_frame が見つかりません。結果表示をスキップします。")
            return
            
        # 既存の結果をクリア
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        try:
            # タイトル
            title_label = ctk.CTkLabel(
                self.results_frame,
                text="💰 損害賠償計算結果",
                font=self.fonts['subtitle']
            )
            title_label.pack(pady=(0, 20))
            
            # 各項目の結果を表示
            for key, result in results.items():
                if not isinstance(result, CalculationResult):
                    continue
                    
                # 項目フレーム
                item_frame = ctk.CTkFrame(self.results_frame)
                item_frame.pack(fill="x", padx=10, pady=5)
                
                # 項目名と金額
                header_frame = ctk.CTkFrame(item_frame)
                header_frame.pack(fill="x", padx=10, pady=(10, 5))
                
                item_name_label = ctk.CTkLabel(
                    header_frame,
                    text=result.item_name,
                    font=self.fonts['body']
                )
                item_name_label.pack(side="left")
                
                amount_label = ctk.CTkLabel(
                    header_frame,
                    text=f"¥{result.amount:,}",
                    font=self.fonts['body']
                )
                amount_label.pack(side="right")
                
                # 詳細情報（折りたたみ可能にする場合は後で実装）
                if result.calculation_details:
                    details_text = ctk.CTkTextbox(
                        item_frame,
                        height=60,
                        font=self.fonts['small']
                    )
                    details_text.pack(fill="x", padx=10, pady=(0, 10))
                    details_text.insert("0.0", result.calculation_details)
                    details_text.configure(state="disabled")
            
            # 合計欄を強調表示
            if 'summary' in results:
                summary_result = results['summary']
                summary_frame = ctk.CTkFrame(self.results_frame)
                summary_frame.pack(fill="x", padx=10, pady=15)
                
                summary_label = ctk.CTkLabel(
                    summary_frame,
                    text=f"🎯 {summary_result.item_name}: ¥{summary_result.amount:,}",
                    font=self.fonts['subtitle']
                )
                summary_label.pack(pady=15)
                
        except Exception as e:
            self.logger.error(f"結果表示中にエラー: {e}", exc_info=True)
            error_label = ctk.CTkLabel(
                self.results_frame,
                text=f"結果表示エラー: {str(e)}",
                font=self.fonts['body'],
                text_color="red"
            )
            error_label.pack(pady=10)

    def on_search_change(self, event=None):
        """検索フィールドの変更時に案件リストを更新"""
        if hasattr(self, 'search_entry'): 
            self.refresh_case_list()

    def apply_template(self):
        """テンプレート適用機能"""
        try:
            # テンプレート一覧を取得
            templates = self.db_manager.get_all_templates_summary()
            if not templates:
               
                messagebox.showinfo("テンプレート", "保存されているテンプレートがありません。")
                return
            
            # テンプレート選択ダイアログ
            template_names = [f"{template[1]} (更新: {template[2][:10]})" for template in templates]
            template_ids = [template[0] for template in templates]
            
            # 簡易的な選択ダイアログ（ctk.CTkInputDialog の代替）
            selection_window = ctk.CTkToplevel(self.root)
            selection_window.title("テンプレート選択")
            selection_window.geometry("400x300")
            selection_window.transient(self.root)
            selection_window.grab_set()
            
            # 選択結果を格納する変数
            selected_template_id = None
            
            def on_template_select():
                nonlocal selected_template_id
                selection = template_listbox.curselection()
                if selection:
                    selected_template_id = template_ids[selection[0]]
                    selection_window.destroy()
                else:
                    messagebox.showwarning("選択エラー", "テンプレートを選択してください。")
            
            def on_cancel():
                selection_window.destroy()
            
            # ウィジェット配置
            ctk.CTkLabel(selection_window, text="適用するテンプレートを選択してください:", 
                        font=self.fonts['body']).pack(pady=10)
            
            # リストボックス用フレーム
            listbox_frame = ctk.CTkFrame(selection_window)
            listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # tkinter.Listboxを使用（CustomTkinterにはListboxがないため）
            import tkinter as tk
            template_listbox = tk.Listbox(listbox_frame, font=("Meiryo UI", 12))
            template_listbox.pack(fill="both", expand=True, padx=10, pady=10)
            
            for name in template_names:
                template_listbox.insert(tk.END, name)
              # ボタンフレーム
            button_frame = ctk.CTkFrame(selection_window)
            button_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkButton(button_frame, text="適用", command=on_template_select, 
                         width=100).pack(side="left", padx=10)
            ctk.CTkButton(button_frame, text="キャンセル", command=on_cancel, 
                         width=100).pack(side="right", padx=10)
            
            # ダイアログの完了を待つ
            self.root.wait_window(selection_window)
            
            if selected_template_id:
                # テンプレートを読み込み
                template_data = self.db_manager.load_template(selected_template_id)
                if template_data:
                    if messagebox.askyesno("確認", "現在の入力内容を破棄し、テンプレートを適用しますか？"):
                        self.current_case = template_data
                        # 案件固有の情報をクリア
                        self.current_case.id = None
                        self.current_case.case_number = ""
                        self.current_case.created_date = datetime.now()
                        self.current_case.last_modified = datetime.now()
                        self.current_case.status = "作成中"
                        self.current_case.calculation_results = {}
                          # UIに反映
                        self.load_case_data_to_ui()
                        self.status_label.configure(text="テンプレートを適用しました")
                        messagebox.showinfo("成功", "テンプレートが適用されました。\n案件番号を設定して保存してください。")
                else:
                    messagebox.showerror("エラー", "テンプレートの読み込みに失敗しました。")
                    
        except Exception as e:
            self.logger.error(f"テンプレート適用エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"テンプレート適用中にエラーが発生しました: {str(e)}")

    def save_as_template(self):
        """テンプレートとして保存機能"""
        try:
            # テンプレート名入力ダイアログ
            template_name_window = ctk.CTkToplevel(self.root)
            template_name_window.title("テンプレート保存")
            template_name_window.geometry("400x200")
            template_name_window.transient(self.root)
            template_name_window.grab_set()
            
            template_name = None
            
            def on_save():
                nonlocal template_name
                name = name_entry.get().strip()
                if name:
                    template_name = name
                    template_name_window.destroy()
                else:
                    messagebox.showwarning("入力エラー", "テンプレート名を入力してください。")
            
            def on_cancel():
                template_name_window.destroy()
            
            # ウィジェット配置
            ctk.CTkLabel(template_name_window, text="テンプレート名を入力してください:", 
                        font=self.fonts['body']).pack(pady=20)
            
            name_entry = ctk.CTkEntry(template_name_window, width=300, font=self.fonts['body'])
            name_entry.pack(pady=10)
            name_entry.focus()
            
            # ボタンフレーム
            button_frame = ctk.CTkFrame(template_name_window)
            button_frame.pack(fill="x", padx=20, pady=20)
            
            ctk.CTkButton(button_frame, text="保存", command=on_save, 
                         width=100).pack(side="left", padx=10)
            ctk.CTkButton(button_frame, text="キャンセル", command=on_cancel, 
                         width=100).pack(side="right", padx=10)
            
            # Enterキーでも保存
            name_entry.bind("<Return>", lambda event: on_save())
            
            # ダイアログの完了を待つ
            self.root.wait_window(template_name_window)
            
            if template_name:
                # 現在の案件データからテンプレート用データを作成
                template_data = CaseData()
                template_data.person_info = self.current_case.person_info
                template_data.accident_info = self.current_case.accident_info
                template_data.medical_info = self.current_case.medical_info
                template_data.income_info = self.current_case.income_info
                
                # テンプレート固有の情報をクリア
                template_data.id = None
                template_data.case_number = ""
                template_data.status = "テンプレート"
                template_data.calculation_results = {}
                
                # データベースに保存
                success = self.db_manager.save_template(template_name, template_data)
                if success:
                    self.status_label.configure(text=f"テンプレート '{template_name}' を保存しました")
                    messagebox.showinfo("成功", f"テンプレート '{template_name}' が保存されました。")
                else:
                    messagebox.showerror("エラー", f"テンプレート '{template_name}' の保存に失敗しました。\n同名のテンプレートが既に存在する可能性があります。")
                    
        except Exception as e:
            self.logger.error(f"テンプレート保存エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"テンプレート保存中にエラーが発生しました: {str(e)}")
    
    def auto_calculate_loss_period(self):
        """労働能力喪失期間の自動計算 (症状固定日から指定年齢まで)"""
        try:
            symptom_fixed_date_str = self._get_date_from_picker(getattr(self, 'symptom_fixed_date_picker', None))
            victim_age_str = self._get_widget_value(getattr(self, 'victim_age_entry', None))
            retirement_age_str = self._get_widget_value(getattr(self, 'retirement_age_entry', None))

            if not symptom_fixed_date_str or symptom_fixed_date_str == "INVALID_DATE":
                messagebox.showerror("入力エラー", "症状固定日を正しく入力してください。")
                return
            if not victim_age_str:
                messagebox.showerror("入力エラー", "被害者年齢（事故時）を入力してください。")
                return
            if not retirement_age_str:
                messagebox.showerror("入力エラー", "就労可能年数上限を入力してください。")
                return

            symptom_fixed_date = datetime.strptime(symptom_fixed_date_str, "%Y-%m-%d")
            victim_age_at_accident = int(victim_age_str)
            retirement_age = int(retirement_age_str)
            
            # 症状固定時の年齢を計算 (事故日から症状固定日までの経過年数を事故時年齢に加算)
            # より正確には事故発生日も考慮すべきだが、ここでは簡略化し症状固定日時点の年を基準とする
            # 事故発生日からの経過年数を加味した方がより正確
            accident_date_str = self._get_date_from_picker(getattr(self, 'accident_date_picker', None))
            if not accident_date_str or accident_date_str == "INVALID_DATE":
                 messagebox.showerror("入力エラー", "事故発生日を正しく入力してください。")
                 return
            accident_date = datetime.strptime(accident_date_str, "%Y-%m-%d")
            
            age_at_symptom_fixed = victim_age_at_accident + (symptom_fixed_date.year - accident_date.year)
            # 誕生日が来ていない場合は1歳引く (より厳密な計算)
            if (symptom_fixed_date.month, symptom_fixed_date.day) < (accident_date.month, accident_date.day):
                age_at_symptom_fixed -=1
            
            if age_at_symptom_fixed >= retirement_age:
                loss_period = 0
            else:
                loss_period = retirement_age - age_at_symptom_fixed
            
            self._set_widget_value(getattr(self, 'loss_period_entry', None), str(loss_period))
            self.status_label.configure(text=f"労働能力喪失期間を {loss_period} 年に設定しました。")
            self.schedule_calculation() # 値変更後に計算をスケジュール

        except ValueError as e:
            messagebox.showerror("入力エラー", f"年齢または日付の形式が無効です: {e}")
        except Exception as e:
            self.logger.error(f"労働能力喪失期間の自動計算エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"自動計算中にエラーが発生しました: {e}")

    def auto_calculate_leibniz(self, loss_period_str: Optional[str]):
        """ライプニッツ係数を自動計算"""
        if not loss_period_str:
            messagebox.showerror("入力エラー", "労働能力喪失期間を入力してください。")
            return
        try:
            loss_period = int(loss_period_str)
            if loss_period <= 0:
                leibniz_coeff = Decimal("0.0")
            else:
                # CalculationEngineにライプニッツ係数表や計算ロジックを持たせるのが望ましい
                # ここでは簡易的に標準的な計算式を使用 (3%の場合)
                # 実際には、法的基準の変更に対応できるよう、エンジン側で管理すべき
                if hasattr(self.calculation_engine, 'get_leibniz_coefficient'):
                    leibniz_coeff = self.calculation_engine.get_leibniz_coefficient(loss_period)
                else: # フォールバック (簡易計算)
                    rate = Decimal("0.03") # 法定利率 (本来は設定や法的基準から取得)
                    leibniz_coeff = (Decimal(1) - (Decimal(1) + rate) ** -loss_period) / rate
            
            # 丸め処理 (小数点以下3桁など、基準に合わせる)
            # ここでは Decimal の標準的な丸めを使用せず、文字列として設定
            # calculation_engine側で丸めた値を取得するのが理想
            formatted_coeff = f"{leibniz_coeff:.3f}" # 例: 小数点以下3桁
            self._set_widget_value(getattr(self, 'leibniz_rate_entry', None), formatted_coeff)
            self.status_label.configure(text=f"ライプニッツ係数を {formatted_coeff} に設定しました。")
            self.schedule_calculation()
        except ValueError:
            messagebox.showerror("入力エラー", "労働能力喪失期間は数値で入力してください。")
        except Exception as e:
            self.logger.error(f"ライプニッツ係数自動計算エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"ライプニッツ係数の計算中にエラーが発生しました: {e}")

    def export_pdf(self):
        if not self.current_case or not self.current_case.case_number: # 案件番号で存在確認
            messagebox.showwarning("注意", "案件が選択されていないか、案件番号がありません。まず案件を読み込むか新規作成してください。")
            return

        # 計算結果の取得 (最新の状態を反映するため)
        if not self.update_case_data_from_ui(): 
            self.status_label.configure(text="PDF出力中止: 入力内容が無効です。")
            return
        
        # 計算を実行して最新の結果を取得
        results_objects: Dict[str, CalculationResult] # 型ヒント
        try:
            results_objects = self.calculation_engine.calculate_all(self.current_case)
            if not results_objects:
                messagebox.showerror("エラー", "計算結果がありません。PDF出力を中止します。")
                return
            # 計算結果をcurrent_caseにも保存（Excel出力など他の機能と一貫性のため）
            self.current_case.calculation_results = {k: v.to_dict() for k, v in results_objects.items()} 
        except Exception as e:
            self.logger.error(f"PDF出力のための計算中にエラー: {e}", exc_info=True)
            messagebox.showerror("計算エラー", f"PDF出力のための計算中にエラーが発生しました: {str(e)}")
            return

        try:
            from reports.pdf_generator import PdfReportGenerator # PdfReportGenerator をインポート
            
            default_filename = f"損害賠償計算書_{self.current_case.case_number}.pdf"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDFファイル", "*.pdf")],
                title="PDFファイルとして保存",
                initialfile=default_filename
            )
            if not filepath:
                return # キャンセルされた

            # PdfReportGenerator には CalculationResult オブジェクトの辞書を渡す
            generator = PdfReportGenerator(self.current_case, results_objects) 
            if generator.generate_report(filepath):
                messagebox.showinfo("成功", f"PDFレポートが正常に出力されました。\\n{filepath}")
                self.status_label.configure(text=f"PDFレポート出力完了: {filepath}")
            else:
                # pdf_generator側でエラーログ出力と基本的なメッセージ表示を期待
                messagebox.showerror("PDF出力エラー", "PDFレポートの生成に失敗しました。詳細はログを確認してください。\n日本語フォントがシステムに正しく設定されていない場合、文字化けやエラーが発生することがあります。")

        except ImportError:
            self.logger.error("PdfReportGenerator のインポートに失敗しました。")
            messagebox.showerror("エラー", "PDF出力機能の読み込みに失敗しました。reports.pdf_generator を確認してください。")
        except Exception as e:
            self.logger.error(f"PDF出力中にエラー: {e}", exc_info=True)
            messagebox.showerror("PDF出力エラー", f"PDFレポートの出力中に予期せぬエラーが発生しました: {str(e)}")

    def export_excel(self):
        # 以前の excel_generator.py を呼び出す形を想定
        if not self.current_case or not self.current_case.id:
            messagebox.showwarning("注意", "保存されている案件がありません。まず案件を保存してください。")
            return
        
        # 計算結果を取得
        if not self.update_case_data_from_ui(): return
        results = self.calculation_engine.calculate_all(self.current_case)
        if not results:
            messagebox.showerror("エラー", "計算結果がありません。Excel出力を中止します。")
            return

        try:
            from reports.excel_generator import ExcelReportGenerator # 動的インポート
            
            # 保存ダイアログ
            default_filename = f"損害賠償計算書_{self.current_case.case_number or '無題'}.xlsx"



            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excelファイル", "*.xlsx")],
                title="Excelファイルとして保存",
                initialfile=default_filename
            )
            if not filepath:
                return # キャンセルされた

            generator = ExcelReportGenerator(self.current_case, results)
            generator.generate_report(filepath)
            messagebox.showinfo("成功", f"Excelレポートが正常に出力されました。\\n{filepath}")
            self.status_label.configure(text=f"Excelレポート出力完了: {filepath}")
        except ImportError:
            self.logger.error("ExcelReportGenerator のインポートに失敗しました。")
            messagebox.showerror("エラー", "Excel出力機能の読み込みに失敗しました。reports.excel_generator を確認してください。")
        except Exception as e:
            self.logger.error(f"Excel出力中にエラー: {e}", exc_info=True)
            messagebox.showerror("Excel出力エラー", f"Excelレポートの出力中にエラーが発生しました: {str(e)}")

    def print_results(self):
        if not self.current_case or not self.current_case.case_number:
            messagebox.showwarning("注意", "印刷対象の案件が選択されていないか、案件番号がありません。")
            return

        if not self.update_case_data_from_ui():
            self.status_label.configure(text="印刷中止: 入力内容が無効です。")
            return

        results_objects: Dict[str, CalculationResult]
        try:
            results_objects = self.calculation_engine.calculate_all(self.current_case)
            if not results_objects:
                messagebox.showerror("エラー", "計算結果がありません。印刷を中止します。")
                return
            self.current_case.calculation_results = {k: v.to_dict() for k, v in results_objects.items()}
        except Exception as e:
            self.logger.error(f"印刷のための計算中にエラー: {e}", exc_info=True)
            messagebox.showerror("計算エラー", f"印刷のための計算中にエラーが発生しました: {str(e)}")
            return

        try:
            from reports.pdf_generator import PdfReportGenerator
            import tempfile
            import os
            import platform
            import subprocess

            # 一時PDFファイルを作成
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                temp_pdf_path = tmp_pdf.name
            
            generator = PdfReportGenerator(self.current_case, results_objects)
            if generator.generate_report(temp_pdf_path):
                self.status_label.configure(text=f"印刷用PDFを準備しました: {temp_pdf_path}")
                
                # OSに応じてファイルを開く
                try:
                    if platform.system() == "Windows":
                        os.startfile(temp_pdf_path)
                    elif platform.system() == "Darwin": # macOS
                        subprocess.call(["open", temp_pdf_path])
                    else: # Linux and other Unix-like
                        subprocess.call(["xdg-open", temp_pdf_path])
                    messagebox.showinfo("印刷準備完了", f"計算書がPDFビューアで開かれました。\nビューアの印刷機能を使用してください。")
                except Exception as e_open:
                    self.logger.error(f"PDFファイルを開けませんでした: {e_open}", exc_info=True)
                    messagebox.showerror("ファイルオープンエラー", f"PDFファイルを開けませんでした。\n{temp_pdf_path}\n手動で開いて印刷してください。")
            else:
                messagebox.showerror("印刷エラー", "印刷用PDFの生成に失敗しました。ログを確認してください。")
                if os.path.exists(temp_pdf_path): # 生成失敗してもファイルが残っていれば削除
                    try:
                        os.remove(temp_pdf_path)
                    except Exception as e_remove:
                        self.logger.warning(f"一時PDFファイルの削除に失敗: {e_remove}")

        except ImportError:
            self.logger.error("PdfReportGenerator のインポートに失敗しました。")
            messagebox.showerror("エラー", "PDF出力機能の読み込みに失敗しました。")
        except Exception as e:
            self.logger.error(f"印刷処理中にエラー: {e}", exc_info=True)
            messagebox.showerror("印刷エラー", f"印刷処理中に予期せぬエラーが発生しました: {str(e)}")

    def upload_file(self):
        messagebox.showinfo("機能開発中", "ファイル管理機能は現在開発中です。ご期待ください！")

    def open_settings(self):
        messagebox.showinfo("機能開発中", "設定画面は現在開発中です。より便利になる予定です！")

    def run(self):
        """アプリケーションのメインループを開始"""
        try:
            self.logger.info("GUI アプリケーションを開始します...")
            self.root.mainloop()
            self.logger.info("GUI アプリケーションが正常に終了しました")
        except Exception as e:
            self.logger.error(f"GUI アプリケーション実行中にエラーが発生しました: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    app = ModernCompensationCalculator()
    app.run()
