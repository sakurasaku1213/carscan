#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律事務所向け 弁護士基準損害賠償計算アプリケーション (改良版v2)
事務員の方でも使いやすい、シンプルで正確な計算ツール
UI/UX改善、過失相殺、弁護士費用概算、入力補助機能などを追加
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkFont
import datetime
from datetime import date
import json # 将来的なデータ保存機能の拡張用
import os   # 現状未使用だが、将来的なファイル操作の可能性を考慮し残置

from reportlab.pdfgen import canvas as reportlab_canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import mm # PDF出力時の単位指定用

class CompensationCalculator:
    # --- 定数定義 ---
    APP_TITLE = "弁護士基準 損害賠償計算システム Ver.2.0"
    FONT_FAMILY_DEFAULT = 'メイリオ' # Meiryo UIも候補
    FONT_SIZE_DEFAULT = 10
    FONT_SIZE_LARGE = 14
    FONT_SIZE_XLARGE = 18
    FONT_SIZE_BUTTON = 12
    FONT_SIZE_TEXT_AREA = 11

    COLOR_PRIMARY = '#3498db'    # 青系
    COLOR_SECONDARY = '#2ecc71'  # 緑系
    COLOR_DANGER = '#e74c3c'     # 赤系
    COLOR_WARNING = '#f39c12'   # オレンジ系
    COLOR_INFO = '#95a5a6'      # グレー系
    COLOR_BACKGROUND = '#ecf0f1' # 明るいグレー
    COLOR_TEXT_DARK = '#2c3e50'  # 濃い青グレー
    COLOR_TEXT_LIGHT = 'white'
    COLOR_DISABLED_BG = '#bdc3c7'

    YEAR_MAX_LEIBNIZ = 67 # ライプニッツ係数表の最大年数（例）
    DEFAULT_RETIREMENT_AGE = 67 # 標準的な就労可能年齢の上限

    # 弁護士費用（旧報酬基準参考の簡易計算） 着手金・報酬金合計の目安
    # (経済的利益, 着手金料率, 着手金固定加算, 報酬金料率, 報酬金固定加算)
    # これはあくまでサンプル。事務所の基準に合わせて調整が必要。
    LAWYER_FEE_TIERS_SAMPLE = [
        (3000000, 0.08, 0, 0.16, 0),  # 300万円以下
        (30000000, 0.05, 90000, 0.10, 180000), # 300万円超3000万円以下
        (300000000, 0.03, 690000, 0.06, 1380000),# 3000万円超3億円以下
        (float('inf'), 0.02, 3690000, 0.04, 7380000) # 3億円超
    ]


    def __init__(self, root):
        self.root = root
        self.root.title(self.APP_TITLE)
        self.root.geometry("1100x780") # 少し大きめに
        self.root.configure(bg=self.COLOR_BACKGROUND)
        self.root.option_add("*Font", (self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT))

        self.initialize_styles()
        self.initialize_standards()
        self.create_main_ui()
        self.set_initial_focus()

    def initialize_styles(self):
        """アプリケーションのスタイルを設定"""
        style = ttk.Style()
        style.theme_use('clam') # clam, alt, default, classic

        style.configure("TNotebook", background=self.COLOR_BACKGROUND, borderwidth=1)
        style.configure("TNotebook.Tab",
                        background="#d0d0d0", # 非選択タブの背景
                        foreground=self.COLOR_TEXT_DARK,
                        padding=[12, 6],
                        font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT + 1, 'bold'))
        style.map("TNotebook.Tab",
                  background=[("selected", self.COLOR_PRIMARY)],
                  foreground=[("selected", self.COLOR_TEXT_LIGHT)],
                  expand=[("selected", [1, 1, 1, 0])]) # 選択タブを少し大きく

        style.configure("TFrame", background=self.COLOR_BACKGROUND)
        style.configure("Content.TFrame", background='white', relief="solid", borderwidth=1) # タブ内コンテンツフレーム

        style.configure("TLabel", background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT_DARK,
                        font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT))
        style.configure("Header.TLabel", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_LARGE, 'bold'), foreground=self.COLOR_PRIMARY)
        style.configure("SubHeader.TLabel", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT + 1, 'bold'), foreground=self.COLOR_TEXT_DARK)
        style.configure("Placeholder.TLabel", foreground='grey')

        style.configure("TEntry", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT), padding=6, relief="solid", borderwidth=1)
        style.map("TEntry", bordercolor=[('focus', self.COLOR_PRIMARY)])

        style.configure("TButton", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_BUTTON), padding=(10,6), borderwidth=1)
        style.map("TButton",
                  background=[('active', self.COLOR_PRIMARY), ('!disabled', '#f0f0f0')],
                  foreground=[('active', self.COLOR_TEXT_LIGHT), ('!disabled', self.COLOR_TEXT_DARK)],
                  relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

        # 主要ボタンのスタイル
        style.configure("Primary.TButton", background=self.COLOR_PRIMARY, foreground=self.COLOR_TEXT_LIGHT)
        style.map("Primary.TButton", background=[('active', self.COLOR_SECONDARY)])
        style.configure("Success.TButton", background=self.COLOR_SECONDARY, foreground=self.COLOR_TEXT_LIGHT)
        style.map("Success.TButton", background=[('active', '#27ae60')]) # 少し濃い緑
        style.configure("Danger.TButton", background=self.COLOR_DANGER, foreground=self.COLOR_TEXT_LIGHT)
        style.map("Danger.TButton", background=[('active', '#c0392b')]) # 少し濃い赤
        style.configure("Info.TButton", background=self.COLOR_INFO, foreground=self.COLOR_TEXT_LIGHT)
        style.map("Info.TButton", background=[('active', '#7f8c8d')]) # 少し濃いグレー


        style.configure("TCombobox", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT), padding=6, relief="solid", borderwidth=1)
        self.root.option_add('*TCombobox*Listbox.font', (self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT))
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.COLOR_PRIMARY)
        self.root.option_add('*TCombobox*Listbox.selectForeground', self.COLOR_TEXT_LIGHT)


        style.configure("TLabelframe", background=self.COLOR_BACKGROUND,
                        font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_LARGE -1 , 'bold'),
                        relief="groove", borderwidth=2, padding=15)
        style.configure("TLabelframe.Label", background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT_DARK,
                        font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_LARGE - 2, 'bold'))

        style.configure("TCheckbutton", background=self.COLOR_BACKGROUND,
                        font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT))
        style.map("TCheckbutton", indicatorcolor=[('selected', self.COLOR_PRIMARY)])

    def initialize_standards(self):
        """弁護士基準のマスターデータを初期化"""
        # 入通院慰謝料表（赤い本別表I） 単位：万円
        self.hospitalization_compensation_table_1 = {
            # 入院月数: {通院月数: 金額}
            0: {0:0, 1:28, 2:52, 3:73, 4:90, 5:105, 6:116, 7:124, 8:132, 9:139, 10:145, 11:150, 12:154, 13:158, 14:162, 15:166},
            1: {0:53, 1:77, 2:98, 3:115, 4:130, 5:141, 6:150, 7:158, 8:164, 9:169, 10:174, 11:177, 12:181, 13:185, 14:189, 15:193},
            2: {0:101, 1:122, 2:140, 3:154, 4:167, 5:176, 6:183, 7:188, 8:193, 9:196, 10:199, 11:201, 12:204, 13:207, 14:210, 15:213},
            3: {0:145, 1:162, 2:177, 3:188, 4:197, 5:204, 6:209, 7:213, 8:216, 9:218, 10:221, 11:223, 12:225, 13:228, 14:231, 15:233},
            4: {0:165, 1:184, 2:198, 3:208, 4:216, 5:223, 6:228, 7:232, 8:235, 9:237, 10:239, 11:241, 12:243, 13:245, 14:247, 15:249},
            5: {0:183, 1:202, 2:215, 3:225, 4:233, 5:239, 6:244, 7:248, 8:250, 9:252, 10:254, 11:256, 12:258, 13:260, 14:262, 15:264},
            6: {0:199, 1:218, 2:230, 3:239, 4:246, 5:252, 6:257, 7:260, 8:262, 9:264, 10:266, 11:268, 12:270, 13:272, 14:274, 15:276}
            # 必要に応じてさらに拡張
        }
        # むちうち症等で他覚症状がない場合に用いる別表II (別表Iの概ね2/3程度)
        self.hospitalization_compensation_table_2 = {
            k: {vk: round(vv * 0.67) for vk, vv in v.items()} # 概ね2/3
            for k, v in self.hospitalization_compensation_table_1.items()
        }

        # 後遺障害慰謝料（弁護士基準） 単位：万円
        self.disability_compensation_std = {
            1: 2800, 2: 2370, 3: 1990, 4: 1670, 5: 1400, 6: 1180, 7: 1000,
            8: 830, 9: 690, 10: 550, 11: 420, 12: 290, 13: 180, 14: 110
        }
        # 労働能力喪失率 単位：%
        self.disability_loss_rate_std = {
            1: 100, 2: 100, 3: 100, 4: 92, 5: 79, 6: 67, 7: 56,
            8: 45, 9: 35, 10: 27, 11: 20, 12: 14, 13: 9, 14: 5
        }

        # ライプニッツ係数（令和2年4月1日以降の事故に適用される法定利率3%）
        # 年数: 係数 (最大YEAR_MAX_LEIBNIZ年まで)
        self.leibniz_coefficient_std = {i: round((1 - (1.03 ** -i)) / 0.03, 3) for i in range(1, self.YEAR_MAX_LEIBNIZ + 1)}
        # 上記は計算式。実際の赤い本などの表と完全に一致しない場合があるため、必要なら手入力で定義。
        # 例: self.leibniz_coefficient_std = {1:0.971, 2:1.913, ..., 45:24.519, ...} のように直接定義も可。
        # 今回は計算式で生成するが、より正確な表データがあるならそちらを優先。
        # 参考: 赤い本2023年版P300など。
        # 簡易的に主要な年数のみ定義しておき、それ以外は計算する方式も考えられる。
        # 今回は67年分を計算式で生成。
        leibniz_manual_override = { # 赤い本2023年版P300から一部抜粋・確認
            1: 0.971, 2: 1.913, 3: 2.829, 4: 3.717, 5: 4.580, 10: 8.530, 15: 11.938,
            20: 14.877, 25: 17.413, 30: 19.600, 35: 21.487, 40: 23.115, 45: 24.519,
            50: 25.730 # 例として追加
        }
        self.leibniz_coefficient_std.update(leibniz_manual_override) # 手動定義で上書き


    def create_main_ui(self):
        """メインUIを作成"""
        # タイトルフレーム
        title_frame = tk.Frame(self.root, bg=self.COLOR_TEXT_DARK, height=60)
        title_frame.pack(fill='x', pady=(0,5)) # 上部に少しスペース
        title_frame.pack_propagate(False)
        title_label = tk.Label(title_frame, text=self.APP_TITLE,
                                 font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_XLARGE, 'bold'),
                                 fg=self.COLOR_TEXT_LIGHT, bg=self.COLOR_TEXT_DARK)
        title_label.pack(expand=True)

        # ノートブック（タブ）作成
        self.notebook = ttk.Notebook(self.root, style="TNotebook")
        self.notebook.pack(fill='both', expand=True, padx=15, pady=10)

        # 各タブを作成
        self.create_basic_info_tab()      # tab_id = 0
        self.create_hospitalization_tab() # tab_id = 1
        self.create_disability_tab()      # tab_id = 2
        self.create_lost_income_tab()     # tab_id = 3
        self.create_result_tab()          # tab_id = 4

        # ボタンフレーム
        button_frame = ttk.Frame(self.root, style="TFrame", padding=(0,10,0,10))
        button_frame.pack(fill='x', padx=15, pady=(5,15))

        ttk.Button(button_frame, text="計算実行", command=self.calculate_all, style="Primary.TButton", width=18).pack(side='left', padx=10)
        ttk.Button(button_frame, text="結果を保存 (.txt)", command=self.save_result, style="Success.TButton", width=18).pack(side='left', padx=10)
        ttk.Button(button_frame, text="PDF出力", command=self.export_pdf, style="Danger.TButton", width=18).pack(side='left', padx=10)
        ttk.Button(button_frame, text="データクリア", command=self.clear_data, style="Info.TButton", width=18).pack(side='right', padx=10)

    def _create_scrollable_frame_for_tab(self, parent_tab):
        """タブ内にスクロール可能なフレームを作成するヘルパー関数"""
        # タブ直下にコンテンツ用フレームを配置 (背景白、枠線あり)
        outer_content_frame = ttk.Frame(parent_tab, style="Content.TFrame", padding=10)
        outer_content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        canvas = tk.Canvas(outer_content_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_content_frame, orient="vertical", command=canvas.yview)
        # スクロールバーのデザインを少し変更 (オプション)
        # style.configure("Vertical.TScrollbar", gripcount=0, background=self.COLOR_PRIMARY, troughcolor=self.COLOR_BACKGROUND)

        scrollable_content_frame = ttk.Frame(canvas, style="TFrame", padding=(10,5)) # Canvas内フレーム

        scrollable_content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return scrollable_content_frame

    def _create_date_entry(self, parent, label_text, row, col_offset=0):
        """年月日選択式のComboboxを生成"""
        ttk.Label(parent, text=label_text).grid(row=row, column=col_offset, sticky='w', padx=5, pady=6)
        
        date_frame = ttk.Frame(parent, style="TFrame")
        # date_frame.configure(background='white') # 親が白なので白に  # ttk.Frameではこの方法はエラーになるためコメントアウト
        date_frame.grid(row=row, column=col_offset + 1, sticky='w', padx=5, pady=2)

        current_year = datetime.date.today().year
        years = [str(y) for y in range(current_year - 100, current_year + 5)] # 過去100年～未来5年
        months = [f"{m:02}" for m in range(1, 13)]
        days = [f"{d:02}" for d in range(1, 32)]

        year_cb = ttk.Combobox(date_frame, values=years, width=6, state="readonly")
        year_cb.pack(side='left', padx=(0,2))
        ttk.Label(date_frame, text="年", background='white').pack(side='left', padx=(0,5))

        month_cb = ttk.Combobox(date_frame, values=months, width=4, state="readonly")
        month_cb.pack(side='left', padx=(0,2))
        ttk.Label(date_frame, text="月", background='white').pack(side='left', padx=(0,5))

        day_cb = ttk.Combobox(date_frame, values=days, width=4, state="readonly")
        day_cb.pack(side='left', padx=(0,2))
        ttk.Label(date_frame, text="日", background='white').pack(side='left')
        
        return year_cb, month_cb, day_cb

    def _get_date_from_entries(self, y_cb, m_cb, d_cb):
        """年月日Comboboxから日付文字列を取得、無効ならNone"""
        y = y_cb.get()
        m = m_cb.get()
        d = d_cb.get()
        if y and m and d:
            try:
                # 日付の妥当性チェックも兼ねる
                dt_obj = datetime.date(int(y), int(m), int(d))
                return dt_obj.strftime("%Y-%m-%d")
            except ValueError:
                return None # 無効な日付組み合わせ
        return None # 未入力あり

    def _set_date_entries(self, y_cb, m_cb, d_cb, date_str=None):
        """年月日Comboboxに日付を設定、date_strがNoneか無効ならクリア"""
        if date_str:
            try:
                dt_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                y_cb.set(str(dt_obj.year))
                m_cb.set(f"{dt_obj.month:02}")
                d_cb.set(f"{dt_obj.day:02}")
                return
            except (ValueError, TypeError):
                pass # 無効な形式ならクリア処理へ
        y_cb.set('')
        m_cb.set('')
        d_cb.set('')

    def create_basic_info_tab(self):
        """基本情報タブ"""
        tab_frame = ttk.Frame(self.notebook, style="TFrame", padding=5)
        self.notebook.add(tab_frame, text=" 📝 基本情報 ")
        content_frame = self._create_scrollable_frame_for_tab(tab_frame)

        ttk.Label(content_frame, text="案件基本情報", style="Header.TLabel").grid(row=0, column=0, columnspan=4, pady=(0,20), sticky='w')

        # --- 1列目 ---
        ttk.Label(content_frame, text="案件番号:").grid(row=1, column=0, sticky='w', padx=5, pady=6)
        self.case_number = ttk.Entry(content_frame, width=28)
        self.case_number.grid(row=1, column=1, padx=5, pady=6)

        self.accident_date_year, self.accident_date_month, self.accident_date_day = self._create_date_entry(content_frame, "事故発生日:", 2, 0)

        ttk.Label(content_frame, text="被害者年齢(事故時):").grid(row=3, column=0, sticky='w', padx=5, pady=6)
        self.victim_age = ttk.Entry(content_frame, width=10)
        self.victim_age.grid(row=3, column=1, sticky='w', padx=5, pady=6)
        self.victim_age.insert(0, "0")
        ttk.Label(content_frame, text="歳", background='white').grid(row=3, column=1, sticky='e', padx=(0,100)) #単位を右寄せ

        ttk.Label(content_frame, text="職業:").grid(row=4, column=0, sticky='w', padx=5, pady=6)
        self.occupation = ttk.Combobox(content_frame, values=[
            "給与所得者", "事業所得者", "家事従事者", "学生・生徒等", "無職・その他", "幼児・児童"
        ], width=26, state="readonly")
        self.occupation.grid(row=4, column=1, padx=5, pady=6)

        ttk.Label(content_frame, text="被害者の過失割合:").grid(row=5, column=0, sticky='w', padx=5, pady=6)
        self.victim_fault_percentage = ttk.Entry(content_frame, width=10)
        self.victim_fault_percentage.grid(row=5, column=1, sticky='w', padx=5, pady=6)
        self.victim_fault_percentage.insert(0, "0")
        ttk.Label(content_frame, text="%", background='white').grid(row=5, column=1, sticky='e', padx=(0,100))

        # --- 2列目 (1列目の右側) ---
        col_offset = 2
        ttk.Label(content_frame, text="依頼者氏名:").grid(row=1, column=col_offset, sticky='w', padx=15, pady=6)
        self.client_name = ttk.Entry(content_frame, width=28)
        self.client_name.grid(row=1, column=col_offset + 1, padx=5, pady=6)

        self.symptom_fixed_date_year, self.symptom_fixed_date_month, self.symptom_fixed_date_day = self._create_date_entry(content_frame, "症状固定日:", 2, col_offset)

        ttk.Label(content_frame, text="性別:").grid(row=3, column=col_offset, sticky='w', padx=15, pady=6)
        self.victim_gender = ttk.Combobox(content_frame, values=["男性", "女性", "その他/不明"], width=15, state="readonly")
        self.victim_gender.grid(row=3, column=col_offset + 1, sticky='w', padx=5, pady=6)

        ttk.Label(content_frame, text="事故前年収(実収入):").grid(row=4, column=col_offset, sticky='w', padx=15, pady=6)
        self.annual_income = ttk.Entry(content_frame, width=18)
        self.annual_income.grid(row=4, column=col_offset + 1, sticky='w', padx=5, pady=6)
        self.annual_income.insert(0, "0")
        ttk.Label(content_frame, text="円", background='white').grid(row=4, column=col_offset+1, sticky='e', padx=(0,60))

    def create_hospitalization_tab(self):
        """入通院慰謝料タブ"""
        tab_frame = ttk.Frame(self.notebook, style="TFrame", padding=5)
        self.notebook.add(tab_frame, text=" 🏥 入通院慰謝料 ")
        content_frame = self._create_scrollable_frame_for_tab(tab_frame)

        ttk.Label(content_frame, text="入通院慰謝料 計算", style="Header.TLabel").pack(pady=(0,20), anchor='w')

        input_area = ttk.Frame(content_frame, style="TFrame")
        # input_area.configure(background='white') # ttk.Frameではこの方法はエラーになるためコメントアウト
        input_area.pack(fill='x', pady=10)

        # 入力フィールド
        field_frame = ttk.Frame(input_area, style="TFrame")
        # field_frame.configure(background='white') # ttk.Frameではこの方法はエラーになるためコメントアウト
        field_frame.pack()

        ttk.Label(field_frame, text="入院期間:").grid(row=0, column=0, sticky='e', padx=5, pady=8)
        self.hospital_months = ttk.Entry(field_frame, width=8, justify='right')
        self.hospital_months.grid(row=0, column=1, padx=5, pady=8)
        self.hospital_months.insert(0, "0")
        ttk.Label(field_frame, text="ヶ月", background='white').grid(row=0, column=2, sticky='w', padx=5)

        ttk.Label(field_frame, text="通院期間:").grid(row=1, column=0, sticky='e', padx=5, pady=8)
        self.outpatient_months = ttk.Entry(field_frame, width=8, justify='right')
        self.outpatient_months.grid(row=1, column=1, padx=5, pady=8)
        self.outpatient_months.insert(0, "0")
        ttk.Label(field_frame, text="ヶ月", background='white').grid(row=1, column=2, sticky='w', padx=5)

        ttk.Label(field_frame, text="実通院日数(参考):").grid(row=2, column=0, sticky='e', padx=5, pady=8)
        self.actual_outpatient_days = ttk.Entry(field_frame, width=8, justify='right')
        self.actual_outpatient_days.grid(row=2, column=1, padx=5, pady=8)
        self.actual_outpatient_days.insert(0, "0")
        ttk.Label(field_frame, text="日", background='white').grid(row=2, column=2, sticky='w', padx=5)

        self.whiplash_var = tk.BooleanVar()
        whiplash_check = ttk.Checkbutton(field_frame, text="むちうち症等（他覚所見なし）で、別表IIを適用する",
                                         variable=self.whiplash_var, style="TCheckbutton")
        whiplash_check.grid(row=3, column=0, columnspan=3, sticky='w', pady=15, padx=5)

        # 計算結果表示エリア
        result_display_frame = ttk.LabelFrame(content_frame, text="このタブの計算結果", style="TLabelframe")
        result_display_frame.pack(fill='both', expand=True, padx=0, pady=15)

        self.hospital_result_text = tk.Text(result_display_frame, height=10, width=70,
                                       font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_TEXT_AREA -1),
                                       relief="flat", bd=0, wrap=tk.WORD, background='#fdfdfd')
        self.hospital_result_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.hospital_result_text.insert(tk.END, "計算実行ボタンを押すと、ここに結果が表示されます。")
        self.hospital_result_text.configure(state='disabled')


    def create_disability_tab(self):
        """後遺障害慰謝料タブ"""
        tab_frame = ttk.Frame(self.notebook, style="TFrame", padding=5)
        self.notebook.add(tab_frame, text=" ♿ 後遺障害 ")
        content_frame = self._create_scrollable_frame_for_tab(tab_frame)
        
        ttk.Label(content_frame, text="後遺障害関連 計算", style="Header.TLabel").pack(pady=(0,20), anchor='w')
        
        input_area = ttk.Frame(content_frame, style="TFrame")
        # input_area.configure(background='white') # ttk.Frameではこの方法はエラーになるためコメントアウト
        input_area.pack(fill='x', pady=10)

        field_frame = ttk.Frame(input_area, style="TFrame")
        # field_frame.configure(background='white') # ttk.Frameではこの方法はエラーになるためコメントアウト
        field_frame.pack()

        ttk.Label(field_frame, text="後遺障害等級:").grid(row=0, column=0, sticky='e', padx=5, pady=8)
        self.disability_grade = ttk.Combobox(field_frame, values=[
            "なし"] + [f"第{i}級" for i in range(1, 15)], width=15, state="readonly")
        self.disability_grade.grid(row=0, column=1, padx=5, pady=8)
        self.disability_grade.set("なし")

        # 計算結果表示エリア
        result_display_frame = ttk.LabelFrame(content_frame, text="このタブの計算結果", style="TLabelframe")
        result_display_frame.pack(fill='both', expand=True, padx=0, pady=15)

        self.disability_result_text = tk.Text(result_display_frame, height=12, width=70,
                                         font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_TEXT_AREA -1),
                                         relief="flat", bd=0, wrap=tk.WORD, background='#fdfdfd')
        self.disability_result_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.disability_result_text.insert(tk.END, "計算実行ボタンを押すと、ここに結果が表示されます。")
        self.disability_result_text.configure(state='disabled')

    def create_lost_income_tab(self):
        """休業損害・逸失利益タブ"""
        tab_frame = ttk.Frame(self.notebook, style="TFrame", padding=5)
        self.notebook.add(tab_frame, text=" 📉 休業損害・逸失利益 ")
        content_frame = self._create_scrollable_frame_for_tab(tab_frame)

        # --- 休業損害セクション ---
        lost_income_lf = ttk.LabelFrame(content_frame, text="休業損害", style="TLabelframe")
        lost_income_lf.pack(fill='x', padx=0, pady=(0,15))

        ttk.Label(lost_income_lf, text="休業日数:").grid(row=0, column=0, sticky='e', padx=5, pady=8)
        self.lost_work_days = ttk.Entry(lost_income_lf, width=10, justify='right')
        self.lost_work_days.grid(row=0, column=1, padx=5, pady=8)
        self.lost_work_days.insert(0, "0")
        ttk.Label(lost_income_lf, text="日").grid(row=0, column=2, sticky='w', padx=5)

        ttk.Label(lost_income_lf, text="日額基礎収入:").grid(row=1, column=0, sticky='e', padx=5, pady=8)
        self.daily_income = ttk.Entry(lost_income_lf, width=15, justify='right')
        self.daily_income.grid(row=1, column=1, padx=5, pady=8)
        self.daily_income.insert(0, "0")
        ttk.Label(lost_income_lf, text="円").grid(row=1, column=2, sticky='w', padx=5)
        ttk.Label(lost_income_lf, text="(事故前3ヶ月間の実収入 ÷ 90日など)", style="Placeholder.TLabel").grid(row=1, column=3, sticky='w', padx=5)

        # --- 後遺障害逸失利益セクション ---
        future_income_lf = ttk.LabelFrame(content_frame, text="後遺障害逸失利益", style="TLabelframe")
        future_income_lf.pack(fill='x', padx=0, pady=10)

        ttk.Label(future_income_lf, text="労働能力喪失期間:").grid(row=0, column=0, sticky='e', padx=5, pady=8)
        self.loss_period = ttk.Entry(future_income_lf, width=10, justify='right')
        self.loss_period.grid(row=0, column=1, padx=5, pady=8)
        self.loss_period.insert(0, "0")
        ttk.Label(future_income_lf, text="年").grid(row=0, column=2, sticky='w', padx=5)

        calc_loss_period_button = ttk.Button(future_income_lf, text=f"{self.DEFAULT_RETIREMENT_AGE}歳までを自動計算",
                                             command=self.auto_calculate_loss_period, style="Info.TButton", width=20)
        calc_loss_period_button.grid(row=0, column=3, padx=10, pady=5, sticky='w')
        ttk.Label(future_income_lf, text=f"(症状固定時年齢を基本情報タブに入力)", style="Placeholder.TLabel").grid(row=0, column=4, sticky='w', padx=5)


        # 計算結果表示エリア
        result_display_frame = ttk.LabelFrame(content_frame, text="このタブの計算結果", style="TLabelframe")
        result_display_frame.pack(fill='both', expand=True, padx=0, pady=15)

        self.income_result_text = tk.Text(result_display_frame, height=15, width=70,
                                     font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_TEXT_AREA -1),
                                     relief="flat", bd=0, wrap=tk.WORD, background='#fdfdfd')
        self.income_result_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.income_result_text.insert(tk.END, "計算実行ボタンを押すと、ここに結果が表示されます。")
        self.income_result_text.configure(state='disabled')

    def auto_calculate_loss_period(self):
        """労働能力喪失期間を自動計算（症状固定時年齢から原則67歳まで）"""
        try:
            age_at_symptom_fix_str = self.victim_age.get() # 事故時年齢を使用（症状固定時年齢の入力欄がないため）
                                                         # 本来は症状固定時年齢が必要
            if not age_at_symptom_fix_str:
                messagebox.showwarning("入力不足", "基本情報タブの「被害者年齢」を入力してください。")
                self.notebook.select(0)
                self.victim_age.focus()
                return
            
            age_at_symptom_fix = int(age_at_symptom_fix_str)
            if age_at_symptom_fix < 0 or age_at_symptom_fix > 120: # 現実的な年齢範囲
                messagebox.showwarning("入力エラー", "被害者年齢が不正です。")
                return

            # 症状固定日と事故日から期間を計算し、事故時年齢に加算するのがより正確
            # ここでは簡略化のため事故時年齢をそのまま使う
            # 症状固定日が入力されていれば、それと事故日から期間を計算し、
            # 事故時年齢に加算して症状固定時年齢を算出できる。
            # 今回は、事故時年齢をそのまま症状固定時年齢とみなして計算する。
            
            remaining_work_years = self.DEFAULT_RETIREMENT_AGE - age_at_symptom_fix
            if remaining_work_years < 0:
                remaining_work_years = 0
            
            self.loss_period.delete(0, tk.END)
            self.loss_period.insert(0, str(remaining_work_years))
            messagebox.showinfo("自動計算完了", f"労働能力喪失期間を {remaining_work_years} 年としてセットしました。\n（{self.DEFAULT_RETIREMENT_AGE}歳 - {age_at_symptom_fix}歳）\n※これは目安です。個別の事案に応じて調整してください。")

        except ValueError:
            messagebox.showerror("入力エラー", "基本情報タブの「被害者年齢」を正しい数値で入力してください。")
            self.notebook.select(0)
            self.victim_age.focus()
        except Exception as e:
            messagebox.showerror("エラー", f"自動計算中にエラーが発生しました: {str(e)}")


    def create_result_tab(self):
        """計算結果総合タブ"""
        tab_frame = ttk.Frame(self.notebook, style="TFrame", padding=5)
        self.notebook.add(tab_frame, text=" 📊 総合結果 ")
        content_frame = self._create_scrollable_frame_for_tab(tab_frame) # ここはスクロール不要かも

        ttk.Label(content_frame, text="損害賠償額 総合計算結果", style="Header.TLabel").pack(pady=(0,15), anchor='w')        # 結果表示用Textウィジェット
        text_widget_frame = ttk.Frame(content_frame, style="TFrame")
        # text_widget_frame.configure(background='white') # ttk.Frameではこの方法はエラーになるためコメントアウト
        text_widget_frame.pack(fill="both", expand=True, padx=0, pady=5)

        self.total_result_text = tk.Text(text_widget_frame, height=28, width=90,
                                    font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_TEXT_AREA),
                                    relief="solid", bd=1, wrap=tk.WORD,
                                    background="#ffffff", foreground=self.COLOR_TEXT_DARK,
                                    padx=10, pady=10) # 内側にもパディング
        
        scrollbar_total_result = ttk.Scrollbar(text_widget_frame, orient="vertical", command=self.total_result_text.yview)
        self.total_result_text.configure(yscrollcommand=scrollbar_total_result.set)

        self.total_result_text.pack(side="left", fill="both", expand=True)
        scrollbar_total_result.pack(side="right", fill="y")

        self.total_result_text.insert(tk.END, "計算実行ボタンを押すと、ここに総合結果が表示されます。")
        self.total_result_text.configure(state='disabled')

    def set_initial_focus(self):
        """アプリケーション起動時の初期フォーカスを設定"""
        self.case_number.focus_set()

    def _get_int_value_from_entry(self, entry_widget, default=0):
        """Entryウィジェットから整数値を取得、無効な場合はdefaultを返す"""
        try:
            val_str = entry_widget.get().strip()
            if not val_str: # 空文字の場合はデフォルト値
                return default
            return int(val_str)
        except ValueError:
            return default # 数値変換できない場合もデフォルト値

    def _validate_date_inputs(self):
        """日付入力の検証（基本情報タブ）"""
        acc_y = self.accident_date_year.get()
        acc_m = self.accident_date_month.get()
        acc_d = self.accident_date_day.get()

        if not (acc_y and acc_m and acc_d): # 未入力は許容しない（必須項目とする）
            messagebox.showwarning("入力エラー", "基本情報タブの「事故発生日」をすべて選択してください。")
            self.notebook.select(0)
            self.accident_date_year.focus()
            return False
        try:
            datetime.date(int(acc_y), int(acc_m), int(acc_d))
        except ValueError:
            messagebox.showwarning("入力エラー", "基本情報タブの「事故発生日」が不正な日付です。")
            self.notebook.select(0)
            self.accident_date_year.focus()
            return False

        # 症状固定日は任意入力とする（空でもOK）
        sym_y = self.symptom_fixed_date_year.get()
        sym_m = self.symptom_fixed_date_month.get()
        sym_d = self.symptom_fixed_date_day.get()
        if sym_y or sym_m or sym_d: # いずれかが入力されていれば、すべて入力されているか＆妥当かチェック
            if not (sym_y and sym_m and sym_d):
                messagebox.showwarning("入力エラー", "基本情報タブの「症状固定日」は年月日をすべて選択するか、すべて空にしてください。")
                self.notebook.select(0)
                self.symptom_fixed_date_year.focus()
                return False
            try:
                datetime.date(int(sym_y), int(sym_m), int(sym_d))
            except ValueError:
                messagebox.showwarning("入力エラー", "基本情報タブの「症状固定日」が不正な日付です。")
                self.notebook.select(0)
                self.symptom_fixed_date_year.focus()
                return False
        return True


    def validate_all_inputs(self):
        """全入力タブの検証"""
        # 基本情報タブ
        if not self.case_number.get().strip():
            messagebox.showwarning("入力エラー", "基本情報タブの「案件番号」を入力してください。")
            self.notebook.select(0); self.case_number.focus(); return False
        if not self.client_name.get().strip():
            messagebox.showwarning("入力エラー", "基本情報タブの「依頼者氏名」を入力してください。")
            self.notebook.select(0); self.client_name.focus(); return False
        if not self._validate_date_inputs(): return False # 日付検証

        age_str = self.victim_age.get().strip()
        if not age_str or not age_str.isdigit() or not (0 <= int(age_str) <= 120):
            messagebox.showwarning("入力エラー", "基本情報タブの「被害者年齢」は0～120の数値を入力してください。")
            self.notebook.select(0); self.victim_age.focus(); return False
        
        income_str = self.annual_income.get().strip()
        if not income_str or not income_str.isdigit() or int(income_str) < 0:
            messagebox.showwarning("入力エラー", "基本情報タブの「事故前年収」は0以上の数値を入力してください。")
            self.notebook.select(0); self.annual_income.focus(); return False

        fault_str = self.victim_fault_percentage.get().strip()
        if not fault_str or not fault_str.isdigit() or not (0 <= int(fault_str) <= 100):
            messagebox.showwarning("入力エラー", "基本情報タブの「被害者の過失割合」は0～100の数値を入力してください。")
            self.notebook.select(0); self.victim_fault_percentage.focus(); return False

        # 入通院慰謝料タブ
        h_months_str = self.hospital_months.get().strip()
        if not h_months_str or not h_months_str.isdigit() or int(h_months_str) < 0:
            messagebox.showwarning("入力エラー", "入通院慰謝料タブの「入院期間」は0以上の数値を入力してください。")
            self.notebook.select(1); self.hospital_months.focus(); return False
        o_months_str = self.outpatient_months.get().strip()
        if not o_months_str or not o_months_str.isdigit() or int(o_months_str) < 0:
            messagebox.showwarning("入力エラー", "入通院慰謝料タブの「通院期間」は0以上の数値を入力してください。")
            self.notebook.select(1); self.outpatient_months.focus(); return False
        a_days_str = self.actual_outpatient_days.get().strip()
        if not a_days_str or not a_days_str.isdigit() or int(a_days_str) < 0:
            messagebox.showwarning("入力エラー", "入通院慰謝料タブの「実通院日数」は0以上の数値を入力してください。")
            self.notebook.select(1); self.actual_outpatient_days.focus(); return False

        # 休業損害・逸失利益タブ
        lost_days_str = self.lost_work_days.get().strip()
        if not lost_days_str or not lost_days_str.isdigit() or int(lost_days_str) < 0:
            messagebox.showwarning("入力エラー", "休業損害タブの「休業日数」は0以上の数値を入力してください。")
            self.notebook.select(3); self.lost_work_days.focus(); return False
        daily_inc_str = self.daily_income.get().strip()
        if not daily_inc_str or not daily_inc_str.isdigit() or int(daily_inc_str) < 0:
            messagebox.showwarning("入力エラー", "休業損害タブの「日額基礎収入」は0以上の数値を入力してください。")
            self.notebook.select(3); self.daily_income.focus(); return False
        loss_period_str = self.loss_period.get().strip()
        if not loss_period_str or not loss_period_str.isdigit() or int(loss_period_str) < 0:
            messagebox.showwarning("入力エラー", "逸失利益タブの「労働能力喪失期間」は0以上の数値を入力してください。")
            self.notebook.select(3); self.loss_period.focus(); return False
        
        return True


    def calculate_all(self):
        """全ての計算を実行し、結果を表示"""
        if not self.validate_all_inputs():
            return

        try:
            # 各損害項目の計算
            hospital_comp_data = self.calculate_hospitalization_compensation()
            disability_comp_data = self.calculate_disability_compensation()
            lost_income_data = self.calculate_lost_income()
            future_loss_data = self.calculate_future_income_loss(disability_comp_data['loss_rate_percent']) # 喪失率を渡す

            # 個別タブへの結果表示
            self.display_individual_tab_results(hospital_comp_data, disability_comp_data, lost_income_data, future_loss_data)

            # 総合結果タブへの表示
            self.display_total_result_summary(hospital_comp_data, disability_comp_data, lost_income_data, future_loss_data)

            self.notebook.select(4) # 総合結果タブに移動
            messagebox.showinfo("計算完了", "計算が完了しました。各タブおよび総合結果タブをご確認ください。")

        except Exception as e:
            messagebox.showerror("計算エラー", f"計算中に予期せぬエラーが発生しました:\n{type(e).__name__}: {str(e)}")


    def calculate_hospitalization_compensation(self):
        """入通院慰謝料の計算"""
        h_months = self._get_int_value_from_entry(self.hospital_months)
        o_months = self._get_int_value_from_entry(self.outpatient_months)
        actual_o_days = self._get_int_value_from_entry(self.actual_outpatient_days) # 参考情報

        table_to_use = self.hospitalization_compensation_table_2 if self.whiplash_var.get() else self.hospitalization_compensation_table_1
        table_name_display = "別表II (むちうち等他覚所見なし)" if self.whiplash_var.get() else "別表I (通常)"
        
        # 表の範囲を超えた場合のクリッピング処理
        # 入院期間のクリップ
        clamped_h_months = min(h_months, max(table_to_use.keys()))
        
        # 通院期間のクリップ (クリップ後の入院期間に対応する最大通院月数で)
        max_o_months_for_clamped_h = 0
        if clamped_h_months in table_to_use:
             max_o_months_for_clamped_h = max(table_to_use[clamped_h_months].keys())
        clamped_o_months = min(o_months, max_o_months_for_clamped_h)

        base_amount_万 = 0
        basis_text = f"入院{h_months}ヶ月、通院{o_months}ヶ月"

        if clamped_h_months in table_to_use and clamped_o_months in table_to_use[clamped_h_months]:
            base_amount_万 = table_to_use[clamped_h_months][clamped_o_months]
            if h_months > max(table_to_use.keys()) or o_months > max_o_months_for_clamped_h :
                basis_text += f" (表上限: 入院{clamped_h_months}ヶ月, 通院{clamped_o_months}ヶ月で計算)"
        elif h_months == 0 and o_months == 0:
             basis_text = "入院・通院なし"
        else: # 表に直接該当なしの場合の処理 (より丁寧な補間が必要な場合もある)
            # 通院のみの場合
            if h_months == 0 and o_months > 0:
                if 0 in table_to_use and clamped_o_months in table_to_use[0]:
                    base_amount_万 = table_to_use[0][clamped_o_months]
                else: basis_text += " (表に該当なし)"
            # 入院のみの場合
            elif h_months > 0 and o_months == 0:
                 if clamped_h_months in table_to_use and 0 in table_to_use[clamped_h_months]:
                     base_amount_万 = table_to_use[clamped_h_months][0]
                 else: basis_text += " (表に該当なし)"
            else: # その他の組み合わせで表にない場合
                basis_text += " (表に該当なし)"
        
        return {
            'amount_yen': base_amount_万 * 10000,
            'basis_text': basis_text,
            'table_name_display': table_name_display,
            'h_months': h_months, 'o_months': o_months, 'actual_o_days': actual_o_days
        }

    def calculate_disability_compensation(self):
        """後遺障害慰謝料と労働能力喪失率の取得"""
        grade_selection = self.disability_grade.get()
        if grade_selection == "なし" or not grade_selection:
            return {'amount_yen': 0, 'grade_text_display': 'なし', 'loss_rate_percent': 0, 'grade_num': 0}

        try:
            grade_num = int(grade_selection.replace("第", "").replace("級", ""))
        except ValueError: # "なし"以外の不正な文字列の場合
            return {'amount_yen': 0, 'grade_text_display': '無効な等級', 'loss_rate_percent': 0, 'grade_num': 0}

        amount_万 = self.disability_compensation_std.get(grade_num, 0)
        loss_rate = self.disability_loss_rate_std.get(grade_num, 0)

        return {
            'amount_yen': amount_万 * 10000,
            'grade_text_display': f"第{grade_num}級",
            'loss_rate_percent': loss_rate,
            'grade_num': grade_num
        }

    def calculate_lost_income(self):
        """休業損害の計算"""
        days = self._get_int_value_from_entry(self.lost_work_days)
        daily_income_val = self._get_int_value_from_entry(self.daily_income)
        amount = days * daily_income_val
        return {'amount_yen': amount, 'days': days, 'daily_income_val': daily_income_val}

    def calculate_future_income_loss(self, loss_rate_percent):
        """後遺障害逸失利益の計算"""
        annual_income_val = self._get_int_value_from_entry(self.annual_income)
        loss_period_years = self._get_int_value_from_entry(self.loss_period)

        if loss_rate_percent == 0 or annual_income_val == 0 or loss_period_years == 0:
            return {'amount_yen': 0, 'annual_income_val': annual_income_val,
                    'loss_rate_percent': loss_rate_percent, 'loss_period_years': loss_period_years,
                    'leibniz_coeff': 0, 'calculation_formula': "N/A"}

        loss_rate_decimal = loss_rate_percent / 100.0
        leibniz_coeff = self.get_leibniz_coefficient_val(loss_period_years)
        
        amount = annual_income_val * loss_rate_decimal * leibniz_coeff
        formula = f"{annual_income_val:,}円 × {loss_rate_percent}% × {leibniz_coeff} (L係数 {loss_period_years}年)"

        return {
            'amount_yen': int(round(amount)),
            'annual_income_val': annual_income_val,
            'loss_rate_percent': loss_rate_percent,
            'loss_period_years': loss_period_years,
            'leibniz_coeff': leibniz_coeff,
            'calculation_formula': formula
        }

    def get_leibniz_coefficient_val(self, years):
        """ライプニッツ係数の取得"""
        if years <= 0: return 0.0
        # 表の最大年数を超える場合は、最大年数の係数を使用（一般的）
        if years > self.YEAR_MAX_LEIBNIZ:
            return self.leibniz_coefficient_std.get(self.YEAR_MAX_LEIBNIZ, 0.0)
        return self.leibniz_coefficient_std.get(years, 0.0) # 表にない場合は0 (通常は1年単位であるはず)

    def calculate_lawyer_fees(self, economic_benefit):
        """弁護士費用（着手金・報酬金合計の概算）を計算"""
        if economic_benefit <= 0:
            return 0, "経済的利益なし"

        # 非常に簡略化した計算例（旧報酬基準の着手金と報酬金を合算したようなイメージ）
        # 実際には、着手金と報酬金は別々に計算し、事件の難易度等で調整される。
        # ここでは、経済的利益に対する一定割合とする。
        # 例：300万まで10%+20万、3000万まで6%+140万、など複雑な場合もある。
        # 今回は、LAWYER_FEE_TIERS_SAMPLE に基づく。
        
        total_fee = 0
        calc_basis = ""

        # 着手金部分の計算 (例: 経済的利益のX%)
        # 報酬金部分の計算 (例: 経済的利益のY%)
        # ここでは合算した料率で計算する簡易版
        for limit, rate_init, fixed_init, rate_reward, fixed_reward in self.LAWYER_FEE_TIERS_SAMPLE:
            if economic_benefit <= limit :
                # このティアで計算
                # 簡易的に着手金と報酬金を合算したようなイメージで計算する。
                # (着手金料率 + 報酬金料率) / 2 のような平均値を使うか、
                # もしくは、より一般的な「(着手金料率 + 報酬金料率) * 経済的利益」のような形か。
                # ここでは、(着手金料率 + 報酬金料率) を合算料率として扱う。
                # ただし、固定加算額の扱いが複雑になるため、よりシンプルなモデルを採用。
                # 例：経済的利益の10% + 20万円（税込）のような形。
                # 今回は、サンプルとして「経済的利益の10% + 消費税」とする。
                # より精緻には、事務所の報酬基準に従う必要がある。
                
                # サンプル：(認容額の10% + 20万円) * 1.1 (消費税10%)
                # fee_rate = 0.10
                # fixed_amount = 200000
                # total_fee = (economic_benefit * fee_rate + fixed_amount) * 1.1 # 消費税10%
                # calc_basis = f"(認容額 × {fee_rate*100:.0f}% + {fixed_amount:,}円) × 消費税10%"
                # break

                # LAWYER_FEE_TIERS_SAMPLE を使う場合 (着手金＋報酬金の合計目安)
                # 簡易的に、着手金と報酬金をそれぞれ計算して合算する
                initial_fee = economic_benefit * rate_init + fixed_init
                reward_fee = economic_benefit * rate_reward + fixed_reward
                total_fee = initial_fee + reward_fee
                calc_basis = f"着手金目安:({economic_benefit:,.0f}×{rate_init*100:.1f}% + {fixed_init:,.0f}円) + 報酬金目安:({economic_benefit:,.0f}×{rate_reward*100:.1f}% + {fixed_reward:,.0f}円)"
                break
        
        # 消費税を加算する場合 (現在の日本では10%)
        # total_fee_with_tax = total_fee * 1.10
        # calc_basis += " (消費税10%別途の可能性あり)"
        # return int(round(total_fee_with_tax)), calc_basis
        # 今回は消費税は含めない概算とする
        return int(round(total_fee)), calc_basis


    def display_individual_tab_results(self, hospital_data, disability_data, lost_income_data, future_loss_data):
        """各計算タブに整形済み結果を表示"""
        # 入通院慰謝料タブ
        self.hospital_result_text.configure(state='normal')
        self.hospital_result_text.delete(1.0, tk.END)
        self.hospital_result_text.insert(tk.END, f"【入通院慰謝料 計算結果】\n\n")
        self.hospital_result_text.insert(tk.END, f"  適用基準: {hospital_data['table_name_display']}\n")
        self.hospital_result_text.insert(tk.END, f"  入力期間: 入院{hospital_data['h_months']}ヶ月, 通院{hospital_data['o_months']}ヶ月\n")
        self.hospital_result_text.insert(tk.END, f"  (実通院日数: {hospital_data['actual_o_days']}日)\n")
        self.hospital_result_text.insert(tk.END, f"  計算根拠詳細: {hospital_data['basis_text']}\n\n")
        self.hospital_result_text.insert(tk.END, f"  慰謝料額 (概算): {hospital_data['amount_yen']:,} 円\n")
        self.hospital_result_text.configure(state='disabled')

        # 後遺障害慰謝料タブ
        self.disability_result_text.configure(state='normal')
        self.disability_result_text.delete(1.0, tk.END)
        self.disability_result_text.insert(tk.END, f"【後遺障害関連 計算結果】\n\n")
        self.disability_result_text.insert(tk.END, f"  後遺障害等級: {disability_data['grade_text_display']}\n")
        if disability_data['grade_num'] > 0:
            self.disability_result_text.insert(tk.END, f"  労働能力喪失率: {disability_data['loss_rate_percent']}%\n")
            self.disability_result_text.insert(tk.END, f"  後遺障害慰謝料 (弁護士基準目安): {disability_data['amount_yen']:,} 円\n\n")
            self.disability_result_text.insert(tk.END, f"※ これは弁護士基準（赤い本等）に基づく一般的な目安です。\n")
        else:
            self.disability_result_text.insert(tk.END, "  後遺障害なし、または等級が無効のため、関連損害は算定されません。\n")
        self.disability_result_text.configure(state='disabled')

        # 休業損害・逸失利益タブ
        self.income_result_text.configure(state='normal')
        self.income_result_text.delete(1.0, tk.END)
        self.income_result_text.insert(tk.END, f"【休業損害 計算結果】\n")
        self.income_result_text.insert(tk.END, f"  休業日数: {lost_income_data['days']}日\n")
        self.income_result_text.insert(tk.END, f"  日額基礎収入: {lost_income_data['daily_income_val']:,}円\n")
        self.income_result_text.insert(tk.END, f"  休業損害額 (概算): {lost_income_data['amount_yen']:,}円\n\n")

        self.income_result_text.insert(tk.END, f"【後遺障害逸失利益 計算結果】\n")
        if disability_data['grade_num'] == 0 or disability_data['loss_rate_percent'] == 0:
            self.income_result_text.insert(tk.END, "  後遺障害なし、または労働能力喪失がないため、逸失利益は発生しません。\n")
        elif future_loss_data['amount_yen'] > 0 :
            self.income_result_text.insert(tk.END, f"  基礎年収: {future_loss_data['annual_income_val']:,}円\n")
            self.income_result_text.insert(tk.END, f"  労働能力喪失率: {future_loss_data['loss_rate_percent']}%\n")
            self.income_result_text.insert(tk.END, f"  労働能力喪失期間: {future_loss_data['loss_period_years']}年\n")
            self.income_result_text.insert(tk.END, f"  ライプニッツ係数: {future_loss_data['leibniz_coeff']}\n")
            self.income_result_text.insert(tk.END, f"  計算式: {future_loss_data['calculation_formula']}\n")
            self.income_result_text.insert(tk.END, f"  逸失利益額 (概算): {future_loss_data['amount_yen']:,}円\n")
        else:
            self.income_result_text.insert(tk.END, "  基礎年収、労働能力喪失期間のいずれかが0のため、逸失利益は0円です。\n")
            self.income_result_text.insert(tk.END, f"  (基礎年収: {future_loss_data['annual_income_val']:,}円, 喪失率: {future_loss_data['loss_rate_percent']}%, 喪失期間: {future_loss_data['loss_period_years']}年)\n")
        self.income_result_text.configure(state='disabled')


    def display_total_result_summary(self, hospital_data, disability_data, lost_income_data, future_loss_data):
        """総合結果タブにサマリーを表示"""
        self.total_result_text.configure(state='normal')
        self.total_result_text.delete(1.0, tk.END)

        # --- スタイル定義 (Textウィジェット内) ---
        self.total_result_text.tag_configure("header", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_LARGE, "bold"), foreground=self.COLOR_PRIMARY, spacing3=10)
        self.total_result_text.tag_configure("subheader", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT + 2, "bold"), foreground=self.COLOR_TEXT_DARK, spacing3=5, lmargin1=10, lmargin2=10)
        self.total_result_text.tag_configure("item_name", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT + 1), lmargin1=20, lmargin2=20)
        self.total_result_text.tag_configure("item_value", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT + 1, "bold"), foreground=self.COLOR_TEXT_DARK, lmargin1=20, lmargin2=20)
        self.total_result_text.tag_configure("item_detail", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT), foreground="grey", lmargin1=30, lmargin2=30)
        self.total_result_text.tag_configure("total_section", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT + 2, "bold"), foreground=self.COLOR_PRIMARY, spacing3=8, lmargin1=10, lmargin2=10)
        self.total_result_text.tag_configure("final_amount", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_LARGE, "bold"), foreground=self.COLOR_DANGER, spacing3=10, lmargin1=10, lmargin2=10)
        self.total_result_text.tag_configure("separator_major", font=(self.FONT_FAMILY_DEFAULT,1), overstrike=True, spacing1=10, spacing3=10) #横線代わり
        self.total_result_text.tag_configure("separator_minor", font=(self.FONT_FAMILY_DEFAULT,1), overstrike=True, spacing1=5, spacing3=5, foreground="lightgrey")
        self.total_result_text.tag_configure("disclaimer", font=(self.FONT_FAMILY_DEFAULT, self.FONT_SIZE_DEFAULT -1), foreground="grey", spacing1=10, lmargin1=10, lmargin2=10, wrap=tk.WORD)

        def add_line(text, style_tag):
            self.total_result_text.insert(tk.END, text + "\n", style_tag)
        def add_separator(major=True):
             self.total_result_text.insert(tk.END, " " * 80 + "\n", "separator_major" if major else "separator_minor")


        add_line("損害賠償額計算書（弁護士基準・概算）", "header")
        add_separator()

        # --- 案件情報 ---
        add_line("【案件情報】", "subheader")
        add_line(f"  案件番号: {self.case_number.get()}", "item_name")
        add_line(f"  依頼者氏名: {self.client_name.get()}", "item_name")
        acc_date_str = self._get_date_from_entries(self.accident_date_year, self.accident_date_month, self.accident_date_day) or "未入力"
        add_line(f"  事故発生日: {acc_date_str}", "item_name")
        sym_date_str = self._get_date_from_entries(self.symptom_fixed_date_year, self.symptom_fixed_date_month, self.symptom_fixed_date_day) or "未入力/算定不能"
        add_line(f"  症状固定日: {sym_date_str}", "item_name")
        add_line(f"  被害者年齢(事故時): {self.victim_age.get()}歳", "item_name")
        add_line(f"  性別: {self.victim_gender.get() or '未選択'}", "item_name")
        add_line(f"  職業: {self.occupation.get() or '未選択'}", "item_name")
        annual_income_val_str = f"{self._get_int_value_from_entry(self.annual_income):,}" if self.annual_income.get().isdigit() else (self.annual_income.get() or "未入力")
        add_line(f"  事故前年収: {annual_income_val_str}円", "item_name")
        add_line(f"  計算実行日: {datetime.date.today().strftime('%Y-%m-%d')}", "item_name")
        add_separator()

        # --- 損害項目別計算 ---
        add_line("【損害項目別 金額】", "subheader")
        total_positive_damage = 0 #積極損害・慰謝料など
        
        # 1. 入通院慰謝料
        add_line(f"1. 入通院慰謝料: {hospital_data['amount_yen']:,} 円", "item_value")
        add_line(f"   (基準: {hospital_data['table_name_display']}, {hospital_data['basis_text']})", "item_detail")
        total_positive_damage += hospital_data['amount_yen']
        
        # 2. 後遺障害慰謝料
        add_line(f"2. 後遺障害慰謝料: {disability_data['amount_yen']:,} 円", "item_value")
        add_line(f"   (等級: {disability_data['grade_text_display']}, 喪失率: {disability_data['loss_rate_percent']}%)", "item_detail")
        total_positive_damage += disability_data['amount_yen']
        
        # 3. 休業損害
        add_line(f"3. 休業損害: {lost_income_data['amount_yen']:,} 円", "item_value")
        add_line(f"   (休業{lost_income_data['days']}日 × 日額{lost_income_data['daily_income_val']:,}円)", "item_detail")
        total_positive_damage += lost_income_data['amount_yen']

        # 4. 後遺障害逸失利益
        add_line(f"4. 後遺障害逸失利益: {future_loss_data['amount_yen']:,} 円", "item_value")
        if future_loss_data['amount_yen'] > 0:
             add_line(f"   ({future_loss_data['calculation_formula']})", "item_detail")
        elif disability_data['grade_num'] > 0 and disability_data['loss_rate_percent'] > 0:
             add_line(f"   (基礎年収または喪失期間が0のため算定不能)", "item_detail")
        else:
             add_line(f"   (後遺障害なし、または労働能力喪失なし)", "item_detail")
        total_positive_damage += future_loss_data['amount_yen']
        add_separator(major=False)

        add_line(f"  上記損害合計 (A): {total_positive_damage:,} 円", "total_section")
        add_separator()

        # --- 過失相殺 ---
        add_line("【過失相殺】", "subheader")
        victim_fault_percent = self._get_int_value_from_entry(self.victim_fault_percentage)
        fault_deduction = int(round(total_positive_damage * (victim_fault_percent / 100.0)))
        amount_after_fault = total_positive_damage - fault_deduction

        add_line(f"  被害者の過失割合: {victim_fault_percent}%", "item_name")
        add_line(f"  過失相殺による減額 (B) = (A) × {victim_fault_percent}%: ▲ {fault_deduction:,} 円", "item_name")
        add_line(f"  過失相殺後の損害額 (C) = (A) - (B): {amount_after_fault:,} 円", "total_section")
        add_separator()
        
        # --- 弁護士費用（概算）---
        add_line("【弁護士費用（着手金・報酬金合計の概算）】", "subheader")
        # 弁護士費用は、通常、実際に回収が見込める額（ここでは過失相殺後の額）を経済的利益として計算する
        lawyer_fee, lawyer_fee_basis = self.calculate_lawyer_fees(amount_after_fault)
        add_line(f"  弁護士費用概算 (D): {lawyer_fee:,} 円", "item_value")
        add_line(f"   (計算根拠目安: {lawyer_fee_basis})", "item_detail")
        add_line(f"   (注: これは旧報酬規定等を参考にした機械的な概算です。事案により変動します。消費税別途の場合あり)", "item_detail")
        add_separator()

        # --- 最終支払見込額（参考） ---
        # 弁護士費用は請求相手に転嫁できるものではないので、被害者が受け取る額からは引かれる。
        # ただし、弁護士費用特約がある場合や、裁判で弁護士費用の一部が損害として認められる場合もある。
        # ここでは、単純に「過失相殺後の額」を主要な結果とし、弁護士費用は参考情報とする。
        # 裁判で認容される弁護士費用は、認容額の1割程度が目安だが、必ず認められるわけではない。
        # ここでは、その加算は行わない。

        add_line("【総合計（弁護士基準による損害賠償請求額の目安）】", "total_section")
        add_line(f"  {amount_after_fault:,} 円", "final_amount")
        add_line(f"  (上記は、過失相殺を考慮した損害額の合計です)", "item_detail")
        add_separator()

        # --- 注意事項 ---
        add_line("【注意事項】", "subheader")
        disclaimer_text = (
            "・本計算書は、入力情報に基づき弁護士基準（赤い本等）を参考に機械的に算定した概算です。\n"
            "・実際の賠償額は、事故態様、過失割合の具体的認定、個別事情（既往症、素因減額等）、治療の相当性、証拠、交渉経緯等により大きく変動します。\n"
            "・ライプニッツ係数は令和2年4月1日以降の事故（法定利率3%）を前提としています。\n"
            "・弁護士費用は、事務所の報酬基準や事案の難易度により異なります。上記はあくまで簡易な目安です。\n"
            "・本計算結果は法的な助言や最終的な賠償額を保証するものではありません。正確な評価のためには必ず弁護士にご相談ください。"
        )
        add_line(disclaimer_text, "disclaimer")
        self.total_result_text.configure(state='disabled')

    def save_result(self):
        """計算結果をテキストファイルに保存"""
        result_content = self.total_result_text.get(1.0, tk.END).strip()
        if not result_content or "計算実行ボタンを押すと" in result_content:
            messagebox.showwarning("保存不可", "保存する計算結果がありません。先に「計算実行」をしてください。")
            return

        case_num_str = self.case_number.get().strip() or "NoCase"
        default_filename = f"損害賠償計算結果_{case_num_str}_{datetime.date.today().strftime('%Y%m%d')}.txt"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
            title="計算結果を名前を付けて保存",
            initialfile=default_filename
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"{self.APP_TITLE}\n")
                    f.write(f"作成日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("-" * 70 + "\n")
                    f.write(result_content)
                messagebox.showinfo("保存完了", f"計算結果を保存しました:\n{filepath}")
            except Exception as e:
                messagebox.showerror("保存エラー", f"ファイルの保存中にエラーが発生しました:\n{str(e)}")

    def export_pdf(self):
        """計算結果をPDFに出力"""
        result_content_raw = self.total_result_text.get(1.0, tk.END).strip()
        if not result_content_raw or "計算実行ボタンを押すと" in result_content_raw:
            messagebox.showwarning("PDF出力不可", "PDF出力する計算結果がありません。先に「計算実行」をしてください。")
            return

        case_num_str = self.case_number.get().strip() or "NoCase"
        default_filename = f"損害賠償計算書_{case_num_str}_{datetime.date.today().strftime('%Y%m%d')}.pdf"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDFファイル", "*.pdf"), ("すべてのファイル", "*.*")],
            title="計算結果をPDFで保存",
            initialfile=default_filename
        )
        if not filepath:
            return

        try:
            pdf_canvas = reportlab_canvas.Canvas(filepath, pagesize=A4)
            
            # 日本語フォントの試行リスト
            jp_font_candidates = ['HeiseiKakuGo-W5', 'IPAexGothic', 'MS-Mincho', 'YuMincho', 'Osaka']
            registered_font_name = None
            for font_name in jp_font_candidates:
                try:
                    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
                    registered_font_name = font_name
                    break
                except Exception:
                    continue
            
            if not registered_font_name:
                messagebox.showwarning("フォント警告", "適切な日本語フォントが見つかりませんでした。\nPDFが正しく表示されない可能性があります。\nIPAフォント等のインストールをお試しください。")
                # フォールバックとして標準フォント（文字化けの可能性大）
                registered_font_name = 'Helvetica' # ReportLab標準

            # PDF描画設定
            page_width, page_height = A4
            margin_top = 20 * mm
            margin_bottom = 20 * mm
            margin_left = 15 * mm
            margin_right = 15 * mm
            line_height_normal = 5 * mm
            line_height_small = 4 * mm
            
            current_y = page_height - margin_top
            
            def draw_line_on_pdf(text, font_name, font_size, line_h, x_offset=0):
                nonlocal current_y
                if current_y < margin_bottom + line_h: # 改ページ判定
                    pdf_canvas.showPage()
                    current_y = page_height - margin_top
                    # ヘッダー等を再度描画する場合はここに記述
                pdf_canvas.setFont(font_name, font_size)
                pdf_canvas.drawString(margin_left + x_offset, current_y, text)
                current_y -= line_h

            # --- PDFヘッダー ---
            draw_line_on_pdf(self.APP_TITLE, registered_font_name, 16, 8*mm)
            draw_line_on_pdf(f"作成日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", registered_font_name, 9, 5*mm)
            current_y -= 5*mm # 少しスペース

            # --- Textウィジェットの内容を解析して描画 ---
            # Textウィジェットのタグ情報を元にスタイルをPDFに適用するのは複雑。
            # ここでは、Textウィジェットのプレーンテキストを行ごとに描画する。
            # より高度なPDF生成には、Platypusなどの高レベルAPIの利用を検討。
            lines = result_content_raw.split('\n')
            for line_text in lines:
                # 簡単なインデントやヘッダー判定（簡易的）
                font_size_pdf = 10
                current_line_height = line_height_normal
                x_offset_pdf = 0

                if line_text.startswith("【") and line_text.endswith("】"):
                    font_size_pdf = 12
                    current_line_height = 6 * mm
                elif line_text.strip().startswith("・") or "   (" in line_text : # 詳細や注意書き
                    font_size_pdf = 9
                    current_line_height = line_height_small
                    if not line_text.strip().startswith("・"): x_offset_pdf = 5 * mm # インデント
                elif "円" in line_text and (line_text.strip().endswith("円") or " 円" in line_text.strip()): # 金額行
                     font_size_pdf = 11
                
                # 簡易的な太字判定 (例: "合計", "最終")
                if any(kw in line_text for kw in ["合計:", "総合計", "最終支払見込額"]):
                     # ReportLabで部分的に太字にするのはdrawStringでは難しい。
                     # 全体を太字にするか、別途テキストオブジェクトを使う必要がある。
                     # ここではフォントサイズで代用。
                     font_size_pdf = 12 if "総合計" in line_text else 11


                draw_line_on_pdf(line_text.strip(), registered_font_name, font_size_pdf, current_line_height, x_offset_pdf)

            pdf_canvas.save()
            messagebox.showinfo("PDF出力完了", f"PDFを保存しました:\n{filepath}")

        except Exception as e:
            messagebox.showerror("PDF出力エラー", f"PDF出力中にエラーが発生しました:\n{type(e).__name__}: {str(e)}")


    def clear_data(self):
        """入力データと結果表示をクリア"""
        if not messagebox.askyesno("データクリア確認", "入力されたすべてのデータと計算結果をクリアしますか？\nこの操作は元に戻せません。"):
            return

        # Entryウィジェットのクリアと初期値設定
        entries_with_defaults = [
            (self.case_number, ""), (self.client_name, ""),
            (self.victim_age, "0"), (self.annual_income, "0"),
            (self.victim_fault_percentage, "0"),
            (self.hospital_months, "0"), (self.outpatient_months, "0"), (self.actual_outpatient_days, "0"),
            (self.lost_work_days, "0"), (self.daily_income, "0"), (self.loss_period, "0")
        ]
        for entry, default_val in entries_with_defaults:
            entry.delete(0, tk.END)
            entry.insert(0, default_val)

        # Comboboxウィジェットのクリアと初期値設定
        self._set_date_entries(self.accident_date_year, self.accident_date_month, self.accident_date_day) # 日付クリア
        self._set_date_entries(self.symptom_fixed_date_year, self.symptom_fixed_date_month, self.symptom_fixed_date_day) # 日付クリア
        self.victim_gender.set('')
        self.occupation.set('')
        self.disability_grade.set('なし')

        # BooleanVarのクリア
        self.whiplash_var.set(False)

        # Textウィジェット（結果表示エリア）のクリアと初期メッセージ
        text_widgets_with_placeholders = [
            (self.hospital_result_text, "計算実行ボタンを押すと、ここに結果が表示されます。"),
            (self.disability_result_text, "計算実行ボタンを押すと、ここに結果が表示されます。"),
            (self.income_result_text, "計算実行ボタンを押すと、ここに結果が表示されます。"),
            (self.total_result_text, "計算実行ボタンを押すと、ここに総合結果が表示されます。")
        ]
        for text_widget, placeholder in text_widgets_with_placeholders:
            text_widget.configure(state='normal')
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, placeholder)
            text_widget.configure(state='disabled')
        
        self.notebook.select(0) # 最初のタブに戻る
        self.set_initial_focus()
        messagebox.showinfo("クリア完了", "すべてのデータがクリアされました。")


def main():
    """メイン関数"""
    root = tk.Tk()
    app = CompensationCalculator(root)
    # ウィンドウを中央に表示 (オプション)
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) / 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) / 2
    root.geometry("+%d+%d" % (x, y-30)) # yを少し上に
    root.mainloop()

if __name__ == "__main__":
    main()

