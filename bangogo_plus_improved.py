#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 証拠番号スタンプツール – 超改良版 (bangogo_plus_v2.py)
----------------------------------------------------
* ttkbootstrap によるモダンなUI
* Treeview でファイル一覧 + インライン編集 + 詳細情報表示
* ドラッグ & ドロップ追加 (tkinterdnd2)
* 一括設定パネルでテンプレート指定
* プレビューでドラッグ配置 / 回転 / フォントサイズ変更 / 色変更 / ページめくり
* 進捗バー + 詳細ログウィンドウ
* マルチページ貼付け (先頭 / 全ページ / 指定ページ)
* スタンプの色指定機能
* 設定の保存・読み込みの強化
* Word形式での証拠説明書生成

必要ライブラリ:
    pip install PyMuPDF pillow tkinterdnd2 docxtpl python-docx==1.1.0 jinja2 ttkbootstrap
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from io import BytesIO
from typing import List, Optional, Tuple, Dict, Any, Union # Union を追加
import datetime
import logging
import shutil # For backup_file

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    # tkinterdnd2.TkinterDnD.Tk は ttkbootstrap.Window と競合する可能性があるため、
    # DND機能は特定のウィジェットにのみ適用する形を推奨。
    # ここでは、DND機能を持つToplevelウィンドウを作成するアプローチは取らず、
    # Treeviewウィジェット自体にドロップターゲットを設定します。
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# --- MuPDF (fitz) インポート時の出力を抑制 ---
import io
import contextlib
with contextlib.redirect_stdout(io.StringIO()), \
     contextlib.redirect_stderr(io.StringIO()):
    import fitz  # PyMuPDF

from PIL import Image, ImageTk, ImageDraw, ImageFont
from docx import Document # generate_evidence_doc で使用
from docxtpl import DocxTemplate # generate_evidence_doc で使用

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.dialogs import Messagebox, Querybox
from ttkbootstrap.scrolled import ScrolledText, ScrolledFrame

# --- アプリケーション定数 ---
APP_NAME = "証拠番号スタンプツール 超改良版"
CONFIG_FILE = "bangogo_plus_v2_config.json"
DEFAULT_FONT_SIZE = 22
DEFAULT_ROTATION = 0
DEFAULT_OFFSET_X = 60
DEFAULT_OFFSET_Y = 10
DEFAULT_STAMP_COLOR = (255, 0, 0)  # RGB Red

# --- ロガー設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- フォントパス設定 ---
def get_font_path():
    if hasattr(sys, "_MEIPASS"): # PyInstaller でバンドルされた場合
        font_path = os.path.join(sys._MEIPASS, "ipaexg.ttf")
        if os.path.exists(font_path):
            return font_path
    # Windows
    font_paths_win = [
        r"C:\Windows\Fonts\Meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc"
    ]
    # macOS
    font_paths_mac = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", # Hiragino Sans W3
        "/Library/Fonts/Arial Unicode.ttf" # Fallback
    ]
    # Linux (一般的なパス)
    font_paths_linux = [
        "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" # Fallback
    ]

    potential_paths = []
    if sys.platform == "win32":
        potential_paths.extend(font_paths_win)
    elif sys.platform == "darwin":
        potential_paths.extend(font_paths_mac)
    else: # Linux or other
        potential_paths.extend(font_paths_linux)

    for path in potential_paths:
        if os.path.exists(path):
            return path
    logger.warning("適切な日本語フォントが見つかりませんでした。デフォルトフォントを使用します。")
    return ImageFont.load_default() # 見つからない場合はPillowのデフォルト

BASE_FONT_PATH = get_font_path()

# --- ユーティリティ関数 ---
def to_fullwidth(num: Union[int, str]) -> str:
    """数値を全角文字に変換します。"""
    return str(num).translate(str.maketrans("0123456789", "０１２３４５６７８９"))

def convert_to_int(s: str) -> Optional[int]:
    """全角数字を含む文字列を整数に変換します。"""
    try:
        s_conv = "".join(chr(ord(c) - 0xFEE0) if "０" <= c <= "９" else c for c in s)
        return int(s_conv)
    except (ValueError, TypeError):
        return None

def safe_int_convert(value: str, default: int = 1) -> int:
    """文字列を安全に整数に変換します。失敗した場合はデフォルト値を返します。"""
    num = convert_to_int(value)
    return num if num is not None else default

def format_bytes(size: int) -> str:
    """バイト数を適切な単位（KB, MB, GB）に変換します。"""
    for unit in ['', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:3.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"

def validate_pdf_file(file_path: str) -> bool:
    """PDFファイルが有効かどうかをチェックします。"""
    if not os.path.exists(file_path):
        logger.error(f"ファイルが見つかりません: {file_path}")
        return False
    try:
        doc = fitz.open(file_path)
        is_valid = len(doc) > 0
        doc.close()
        if not is_valid:
            logger.warning(f"無効なPDF（ページ数0）: {file_path}")
        return is_valid
    except Exception as e:
        logger.error(f"PDFファイル読み込みエラー ({file_path}): {e}")
        return False

def backup_file(file_path: str, backup_dir: Optional[str] = None) -> Optional[str]:
    """ファイルのバックアップを作成します。"""
    try:
        if backup_dir:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            base, ext = os.path.splitext(os.path.basename(file_path))
            backup_path = os.path.join(backup_dir, f"{base}_backup{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")
        else:
            backup_path = f"{file_path}.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
        
        shutil.copy2(file_path, backup_path)
        logger.info(f"バックアップを作成しました: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"バックアップ作成失敗 ({file_path}): {e}")
        return None

def get_file_details(file_path: str) -> Dict[str, Any]:
    """ファイルの詳細情報を取得します。"""
    details = {
        "path": file_path,
        "name": os.path.basename(file_path),
        "size_bytes": 0,
        "size_str": "0B",
        "pages": 0,
        "modified_timestamp": 0,
        "modified_str": "N/A",
        "is_pdf": file_path.lower().endswith(".pdf"),
        "valid_pdf": False,
    }
    try:
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            details["size_bytes"] = stat.st_size
            details["size_str"] = format_bytes(stat.st_size)
            details["modified_timestamp"] = stat.st_mtime
            details["modified_str"] = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')

            if details["is_pdf"]:
                doc = fitz.open(file_path)
                details["pages"] = len(doc)
                doc.close()
                details["valid_pdf"] = details["pages"] > 0
    except Exception as e:
        logger.warning(f"ファイル情報取得エラー ({file_path}): {e}")
    return details

# --- 設定管理 ---
class AppConfig:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.defaults: Dict[str, Any] = {
            "theme": "litera", # ttkbootstrap theme
            "mode": "evidence",  # "evidence" | "attachment"
            "prefix": "甲",
            "start_main": 1,
            "branch_auto": False,
            "font_size": DEFAULT_FONT_SIZE,
            "rotation": DEFAULT_ROTATION,
            "offset_x": DEFAULT_OFFSET_X,
            "offset_y": DEFAULT_OFFSET_Y,
            "stamp_color_rgb": DEFAULT_STAMP_COLOR, # (R, G, B)
            "target_pages": "first",  # "first" | "all" | comma-separated list
            "make_docx": False,
            "tpl_path": "",
            "doc_prefix": "証拠説明書",
            "create_backup": False,
            "backup_dir": "", # New: Custom backup directory
            "auto_save_config": True,
            "show_file_details_cols": ["size_str", "pages", "modified_str"], # Columns to show in treeview
            "output_filename_template": "{text}_{original_basename}", # New: Filename template
            "log_level": "INFO", # New: Log level
            "window_geometry": "1000x700", # New: Main window size and position
        }
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # デフォルト値にないキーや型が異なる場合は補完・修正
                    config = self.defaults.copy()
                    config.update(loaded_data) # loaded_data で上書き
                    # 型チェックと修正 (例: stamp_color_rgb がリストで保存されていたらタプルに)
                    if isinstance(config.get("stamp_color_rgb"), list):
                        config["stamp_color_rgb"] = tuple(config["stamp_color_rgb"])
                    return config
            return self.defaults.copy()
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return self.defaults.copy()

    def save(self):
        try:
            # 確実に親ディレクトリが存在するか確認 (通常はカレントだが念のため)
            os.makedirs(os.path.dirname(self.file_path) or '.', exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"設定を保存しました: {self.file_path}")
        except Exception as e:
            logger.error(f"設定ファイル保存エラー: {e}")

    def get(self, key: str, default_override: Optional[Any] = None) -> Any:
        if default_override is not None:
            return self.data.get(key, default_override)
        return self.data.get(key, self.defaults.get(key))

    def set(self, key: str, value: Any):
        self.data[key] = value
        if self.get("auto_save_config", True):
            self.save()

    def reset_to_defaults(self):
        self.data = self.defaults.copy()
        self.save()
        logger.info("設定をデフォルトに戻しました。")

# --- PDF操作コア ---
def build_label_text(mode: str, prefix: str, main_num: int, branch: Optional[str]) -> str:
    """スタンプ用のラベル文字列を生成します。"""
    if mode == "evidence":
        text = f"{prefix}第{to_fullwidth(main_num)}号証"
        if branch:
            text += f"の{to_fullwidth(branch)}"
        return text
    else:  # attachment
        text = f"添付資料{to_fullwidth(main_num)}"
        if branch:
            text += f"の{to_fullwidth(branch)}"
        return text

def render_label_image(text: str, font_size: int, rotation: int, color: Tuple[int, int, int]) -> Image.Image:
    """指定されたテキスト、フォントサイズ、回転、色でラベル画像をレンダリングします。"""
    try:
        font = ImageFont.truetype(BASE_FONT_PATH, font_size)
    except Exception as e:
        logger.warning(f"指定フォント読み込み失敗 ({BASE_FONT_PATH}): {e}。デフォルトフォントを使用します。")
        font = ImageFont.load_default(size=font_size) # Pillow 9.2.0+
    
    # テキストのバウンディングボックスを取得
    dummy_img = Image.new("RGBA", (1,1))
    draw = ImageDraw.Draw(dummy_img)
    try: # Pillow 10.0.0+
        bbox = draw.textbbox((0, 0), text, font=font)
    except AttributeError: # Older Pillow
        text_width, text_height = draw.textsize(text, font=font)
        bbox = (0, 0, text_width, text_height)

    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # 適切なパディングを追加
    padding = max(5, font_size // 10) 
    img_w, img_h = w + padding * 2, h + padding * 2
    
    img = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 0)) # 透明背景
    draw = ImageDraw.Draw(img)
    
    # テキスト描画位置（パディング考慮）
    text_x, text_y = padding - bbox[0], padding - bbox[1]
    draw.text((text_x, text_y), text, font=font, fill=color + (255,)) # RGBA

    if rotation != 0:
        img = img.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
    return img

def stamp_pdf(
    pdf_path: str,
    out_dir: str,
    text: str, # スタンプ文字列（ファイル名生成にも使用）
    pos_x: float,
    pos_y: float,
    font_size: int,
    rotation: int,
    color: Tuple[int, int, int],
    target_pages_str: str = "first",
    output_filename_template: str = "{text}_{original_basename}"
) -> str:
    """PDFにスタンプを付与します。"""
    label_img = render_label_image(text, font_size, rotation, color)
    
    img_byte_arr = BytesIO()
    label_img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    doc = fitz.open(pdf_path)
    
    pages_to_stamp: List[int] = []
    if target_pages_str == "all":
        pages_to_stamp = list(range(len(doc)))
    elif target_pages_str == "first":
        pages_to_stamp = [0] if len(doc) > 0 else []
    else:
        try:
            pages_to_stamp = [int(p.strip()) - 1 for p in target_pages_str.split(",") if p.strip().isdigit()]
            pages_to_stamp = [p for p in pages_to_stamp if 0 <= p < len(doc)] # 範囲チェック
        except ValueError:
            logger.error(f"無効なページ指定: {target_pages_str}。先頭ページにスタンプします。")
            pages_to_stamp = [0] if len(doc) > 0 else []

    if not pages_to_stamp and len(doc) > 0: # 処理対象ページがないがドキュメントはある場合
        logger.warning(f"スタンプ対象ページがありません ({pdf_path})。処理をスキップします。")

    rect = fitz.Rect(pos_x, pos_y, pos_x + label_img.width, pos_y + label_img.height)

    for pno in pages_to_stamp:
        try:
            page = doc[pno]
            page.insert_image(rect, stream=img_byte_arr.getvalue(), overlay=True)
        except Exception as e:
            logger.error(f"ページ {pno+1} へのスタンプ失敗 ({pdf_path}): {e}")

    original_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # 出力ファイル名生成
    # 使用可能なプレースホルダー: {text}, {original_basename}, {prefix}, {main_num}, {branch_num}
    # (prefix, main_num, branch_num は text からパースする必要があるが、今回は単純に text を使用)
    # サニタイズ: ファイル名に使えない文字を除去
    safe_text_for_filename = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in text)
    
    filename_vars = {
        "text": safe_text_for_filename,
        "original_basename": original_basename,
    }
    
    try:
        out_name_base = output_filename_template.format(**filename_vars)
    except KeyError as e:
        logger.warning(f"ファイル名テンプレートのキーエラー: {e}。デフォルトテンプレートを使用します。")
        out_name_base = f"{safe_text_for_filename}_{original_basename}"

    out_name = f"{out_name_base}.pdf"
    out_path = os.path.join(out_dir, out_name)
    
    counter = 1
    while os.path.exists(out_path):
        out_path = os.path.join(out_dir, f"{out_name_base}({counter}).pdf")
        counter += 1
        if counter > 100: # 無限ループ防止
            logger.error(f"出力ファイル名の重複解決に失敗しました: {out_name_base}")
            raise IOError(f"出力ファイル名の重複解決に失敗: {out_name_base}")

    doc.save(out_path, garbage=4, deflate=True, clean=True) # garbage=4 for thorough cleaning
    doc.close()
    logger.info(f"スタンプ済みPDFを保存: {out_path}")
    return out_path

# --- Word生成ヘルパー ---
def generate_evidence_doc(evidences: List[Dict[str, str]], template_path: str, context: Dict[str, str], out_dir: str) -> str:
    """証拠説明書のWord文書を生成します。"""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Wordテンプレートが見つかりません: {template_path}")

    doc = DocxTemplate(template_path)
    doc.render({**context, "evidences": evidences})
    
    fn_prefix = context.get("doc_prefix", context.get("bundle_title", "証拠説明書"))
    # ファイル名に使えない文字を除去
    safe_fn_prefix = "".join(c if c.isalnum() else '_' for c in fn_prefix)
    
    out_filename = f"{safe_fn_prefix}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.docx"
    out_path = os.path.join(out_dir, out_filename)

    counter = 1
    base_name, ext = os.path.splitext(out_filename)
    while os.path.exists(out_path):
        out_path = os.path.join(out_dir, f"{base_name}({counter}){ext}")
        counter += 1
        if counter > 100:
            raise IOError(f"Word出力ファイル名の重複解決に失敗: {base_name}")
            
    doc.save(out_path)
    logger.info(f"証拠説明書を生成しました: {out_path}")
    return out_path

# --- プレビューウィンドウ ---
class PreviewDialog(tk.Toplevel):
    def __init__(
        self,
        master,
        app_config: AppConfig,
        pdf_path: str,
        text: str,
        initial_font_size: int,
        initial_offset_x: float,
        initial_offset_y: float,
        initial_rotation: int,
        initial_color_rgb: Tuple[int, int, int],
    ):
        super().__init__(master)
        self.master = master
        self.app_config = app_config
        self.pdf_path = pdf_path
        self.text_to_stamp = text
        
        self.current_font_size = tk.IntVar(value=initial_font_size)
        self.current_rotation = tk.IntVar(value=initial_rotation)
        self.current_color_rgb = list(initial_color_rgb) # 色選択用にリストにする

        self.title(f"プレビュー – {os.path.basename(pdf_path)}")        # ウィンドウサイズは内容に応じて調整されるべきだが、初期値を設定
        self.geometry("700x850") 
        
        self.doc = None
        try:
            self.doc = fitz.open(pdf_path)
        except Exception as e:
            Messagebox.show_error(f"PDF読み込みエラー: {e}", title="エラー", parent=self)
            self.destroy()
            return
        
        if not self.doc or len(self.doc) == 0:
            Messagebox.show_error("PDFファイルが開けないか、ページがありません。", title="エラー", parent=self)
            self.destroy()
            return

        self.bg_photo_image = None  # Initialize here
        self.stamp_image_on_canvas = None  # Initialize here
        self.current_page_num = tk.IntVar(value=0) # 初期ページを0に設定
        self.total_pages = len(self.doc)
        
        # 初期のページラベルを設定
        self.page_label_var = tk.StringVar()
        self.page_label_var.set(f"1 / {self.total_pages}")  # 初期表示を設定

        # --- UI要素 ---
        # メインフレーム
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=BOTH, expand=True)

        # キャンバスフレーム (スクロール可能にする)
        canvas_frame = ScrolledFrame(main_frame, autohide=True)
        canvas_frame.pack(side=TOP, fill=BOTH, expand=True, pady=5)
        
        self.canvas_width = 650 
        self.canvas_height = 750 # 初期値、PDFに合わせて調整
        self.canvas = tk.Canvas(canvas_frame, width=self.canvas_width, height=self.canvas_height, bg="lightgrey")
        self.canvas.pack(side=TOP, fill=BOTH, expand=True) # ScrolledFrameの子として配置

        # コントロールフレーム
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(side=BOTTOM, fill=X, pady=10)

        # ページナビゲーション
        page_nav_frame = ttk.Labelframe(controls_frame, text="ページ", padding=5)
        page_nav_frame.pack(side=LEFT, padx=5, fill=Y)
        ttk.Button(page_nav_frame, text="<<", command=lambda: self.change_page(-100), width=3, style="Outline.TButton").pack(side=LEFT, padx=2)
        ttk.Button(page_nav_frame, text="<", command=lambda: self.change_page(-1), width=3, style="Outline.TButton").pack(side=LEFT, padx=2)
        self.page_label_var = tk.StringVar()
        ttk.Label(page_nav_frame, textvariable=self.page_label_var, width=10, anchor=CENTER).pack(side=LEFT, padx=2)
        ttk.Button(page_nav_frame, text=">", command=lambda: self.change_page(1), width=3, style="Outline.TButton").pack(side=LEFT, padx=2)
        ttk.Button(page_nav_frame, text=">>", command=lambda: self.change_page(100), width=3, style="Outline.TButton").pack(side=LEFT, padx=2)        # スタンプ調整
        stamp_adjust_frame = ttk.Labelframe(controls_frame, text="スタンプ調整", padding=5)
        stamp_adjust_frame.pack(side=LEFT, padx=5, fill=Y)
        
        ttk.Label(stamp_adjust_frame, text="サイズ:").grid(row=0, column=0, padx=2, pady=2, sticky=W)
        ttk.Spinbox(stamp_adjust_frame, from_=8, to=200, textvariable=self.current_font_size, width=5, command=self.redraw_canvas).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(stamp_adjust_frame, text="回転:").grid(row=0, column=2, padx=2, pady=2, sticky=W)
        self.rotation_combo = ttk.Combobox(stamp_adjust_frame, values=[0, 90, 180, 270], textvariable=self.current_rotation, width=4, state="readonly")
        self.rotation_combo.grid(row=0, column=3, padx=2, pady=2)
        self.rotation_combo.bind('<<ComboboxSelected>>', lambda e: self.redraw_canvas())
        self.current_rotation.trace_add("write", lambda *args: self.redraw_canvas()) # Spinboxと挙動を合わせる

        ttk.Button(stamp_adjust_frame, text="色変更", command=self.pick_color, style="Outline.TButton").grid(row=0, column=4, padx=5, pady=2)
        self.color_preview_label = ttk.Label(stamp_adjust_frame, text="■", width=2) # 色プレビュー用
        self.color_preview_label.grid(row=0, column=5, padx=2, pady=2)
        self.update_color_preview_label()


        # 確定/キャンセルボタン
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(side=RIGHT, padx=5, fill=Y)
        ttk.Button(action_frame, text="確定", command=self.confirm, style="success.TButton").pack(pady=2, fill=X)
        ttk.Button(action_frame, text="キャンセル", command=self.cancel, style="danger.Outline.TButton").pack(pady=2, fill=X)

        # --- 初期描画 ---
        self.bg_photo = None  # PhotoImageオブジェクトを保持
        self.label_photo = None
        self.stamp_item_id = None
        self.pdf_display_scale = 1.0
        
        # ドラッグ用
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)        # 初期オフセット (これはPDF上の実座標)
        self.stamp_abs_x = initial_offset_x 
        self.stamp_abs_y = initial_offset_y
        
        # プレビューダイアログが開いた時に、必ず初回のページと全体が描画されるようにする
        # 初期ページ番号を0に設定し、確実に初期描画を実行
        self.current_page_num.set(0)
        self.page_label_var.set(f"1 / {self.total_pages}")
        
        # ウィンドウが完全に初期化された後に描画を実行
        self.after(200, self.redraw_canvas) # より確実な初期描画のため少し遅延
        self.protocol("WM_DELETE_WINDOW", self.cancel) # Xボタンで閉じた時

        self.result: Optional[Tuple[int, float, float, int, Tuple[int,int,int]]] = None

    def update_color_preview_label(self):
        hex_color = f"#{self.current_color_rgb[0]:02x}{self.current_color_rgb[1]:02x}{self.current_color_rgb[2]:02x}"
        self.color_preview_label.config(foreground=hex_color)


    def pick_color(self):
        # ttkbootstrap.dialogs.colorchooser.ColorChooserDialog を使う
        # 初期色を渡す
        initial_hex = f"#{self.current_color_rgb[0]:02x}{self.current_color_rgb[1]:02x}{self.current_color_rgb[2]:02x}"
        
        # ColorChooserDialogはモーダルではないので、wait_windowで待つ
        # Querybox.askcolorは古いtkカラーチューザーなので使わない
        # 代わりに、色選択ボタンを作成し、それをクリックしたら色選択ダイアログを出す
        # ここでは簡易的に Querybox を使う (ttkbootstrap の ColorChooserDialog は少し複雑)
        
        # tk.colorchooser.askcolor を使用
        from tkinter import colorchooser
        # askcolor は ( (r,g,b), "#rrggbb" ) というタプルを返す
        new_color_tuple = colorchooser.askcolor(color=f"#{self.current_color_rgb[0]:02x}{self.current_color_rgb[1]:02x}{self.current_color_rgb[2]:02x}", 
                                                parent=self, title="スタンプの色を選択")
        if new_color_tuple and new_color_tuple[0]: # 色が選択された場合
            rgb_float = new_color_tuple[0] # (r_float, g_float, b_float) 各要素は 0-255
            self.current_color_rgb = [int(c) for c in rgb_float]
            self.update_color_preview_label()
            self.redraw_canvas()


    def change_page(self, delta: int):
        new_page = self.current_page_num.get() + delta
        if 0 <= new_page < self.total_pages:
            self.current_page_num.set(new_page)
            self.redraw_canvas()
        elif new_page < 0:
            self.current_page_num.set(0)
            self.redraw_canvas()
        elif new_page >= self.total_pages:
            self.current_page_num.set(self.total_pages - 1)
            self.redraw_canvas()
    def redraw_canvas(self, event=None):
        logger.debug("redraw_canvas called")
        ImageTk = get_PIL("ImageTk")
        Image = get_PIL("Image")
        if not ImageTk or not Image:
            logger.error("PIL.ImageTk or PIL.Image is not available.")
            return

        if not self.pdf_document:
            logger.warning("redraw_canvas: PDF document is not loaded.")
            return

        current_page_index = self.current_page_num.get()
        logger.debug(f"redraw_canvas: Rendering page {current_page_index + 1}")

        # PDFページを画像として取得
        try:
            page = self.pdf_document.load_page(current_page_index)
            logger.debug(f"Page {current_page_index} loaded.")

            # DPIと回転を考慮して画像をレンダリング
            rotation = int(self.rotation_combo.get())
            zoom_x = self.dpi / 72.0
            zoom_y = self.dpi / 72.0
            mat = fitz.Matrix(zoom_x, zoom_y).prerotate(rotation)
            
            pix = page.get_pixmap(matrix=mat, alpha=False)
            logger.debug(f"Pixmap created for page {current_page_index} with DPI {self.dpi} and rotation {rotation}")

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            logger.debug(f"Image created from pixmap: mode={img.mode}, size={img.size}")

            # キャンバスサイズに合わせて画像をリサイズ
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # ウィンドウがまだ描画されていない場合、デフォルトサイズを使用
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 800 # デフォルトの幅
                canvas_height = 600 # デフォルトの高さ
                logger.warning(f"Canvas not yet drawn, using default size: {canvas_width}x{canvas_height}")


            img_aspect_ratio = img.width / img.height
            canvas_aspect_ratio = canvas_width / canvas_height

            if img_aspect_ratio > canvas_aspect_ratio:
                # 画像の幅がキャンバスの幅にフィット
                new_width = canvas_width
                new_height = int(new_width / img_aspect_ratio)
            else:
                # 画像の高さがキャンバスの高さにフィット
                new_height = canvas_height
                new_width = int(new_height * img_aspect_ratio)
            
            # 画像が大きすぎる場合はリサイズするが、小さすぎる場合は拡大しない方針も検討
            # ここでは、常にキャンバスにフィットするようにリサイズ
            resized_img = img.resize((new_width, new_height), Image.LANCZOS) #Image.Resampling.LANCZOS for newer Pillow
            logger.debug(f"Image resized to: {resized_img.size}")

            self.bg_photo_image = ImageTk.PhotoImage(resized_img)
            logger.debug("PhotoImage created and assigned to self.bg_photo_image.")

            # キャンバスの中央に画像を描画
            self.canvas.delete("all")
            img_x = (canvas_width - new_width) // 2
            img_y = (canvas_height - new_height) // 2
            self.canvas.create_image(img_x, img_y, anchor=tk.NW, image=self.bg_photo_image, tags="pdf_page")
            logger.debug(f"Image drawn on canvas at ({img_x}, {img_y}) with anchor NW.")

            # 境界線を描画 (リサイズ後の画像のサイズと位置に合わせる)
            border_x0 = img_x
            border_y0 = img_y
            border_x1 = img_x + new_width
            border_y1 = img_y + new_height
            self.canvas.create_rectangle(border_x0, border_y0, border_x1, border_y1, outline="black", width=1, tags="pdf_border")
            logger.debug(f"Border drawn around image: ({border_x0},{border_y0}) to ({border_x1},{border_y1})")

        except Exception as e:
            logger.error(f"Error rendering PDF page {current_page_index}: {e}", exc_info=True)
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() / 2,
                self.canvas.winfo_height() / 2,
                text=f"ページ {current_page_index + 1} の表示エラー:\n{e}",
                fill="red",
                justify=tk.CENTER
            )
            self.bg_photo_image = None # エラー時はクリア
            return # エラーが発生したらスタンプ処理は行わない

        # スタンプの再描画
        if self.stamp_image_on_canvas: # self.stamp_image_on_canvas が None でないことを確認
            self.canvas.delete(self.stamp_image_on_canvas)
            self.stamp_image_on_canvas = None # 削除したのでNoneにリセット
            logger.debug("Deleted old stamp image from canvas.")
        
        # スタンプ画像生成
        stamp_font_size = self.current_font_size.get()
        stamp_rotation = self.current_rotation.get()
        
        # スタンプの実座標をキャンバス座標に変換
        stamp_canvas_x = self.stamp_abs_x * self.pdf_display_scale
        stamp_canvas_y = self.stamp_abs_y * self.pdf_display_scale

        # スタンプ画像生成
        label_img_pil = render_label_image(
            self.text_to_stamp,
            stamp_font_size, # フォントサイズはスケーリングしない（見た目のサイズ）
            stamp_rotation,
            tuple(self.current_color_rgb) # type: ignore
        )
        self.label_photo = ImageTk.PhotoImage(label_img_pil)
        
        self.stamp_item_id = self.canvas.create_image(
            stamp_canvas_x,
            stamp_canvas_y,
            image=self.label_photo,
            anchor="nw",
            tags="stamp"
        )
        
        logger.debug(f"redraw_canvas: 完了 - スタンプ位置 ({stamp_canvas_x}, {stamp_canvas_y})")
        self.update_idletasks() # 即時描画更新

    def on_press(self, event):
        item = self.canvas.find_withtag(CURRENT)
        if item and "stamp" in self.canvas.gettags(item):
            self.drag_data["item"] = item[0]
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            # ドラッグ開始時にスタンプを最前面に
            self.canvas.tag_raise(self.drag_data["item"])

    def on_drag(self, event):
        if self.drag_data["item"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.canvas.move(self.drag_data["item"], dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def on_release(self, event):
        if self.drag_data["item"]:
            # ドラッグ終了時のキャンバス座標を取得
            canvas_x, canvas_y = self.canvas.coords(self.drag_data["item"])
            # PDF上の実座標に変換して保存
            self.stamp_abs_x = canvas_x / self.pdf_display_scale
            self.stamp_abs_y = canvas_y / self.pdf_display_scale
            
            self.drag_data["item"] = None


    def confirm(self):
        # 最終的なスタンプ位置（PDF実座標）を取得
        if self.stamp_item_id:
            canvas_x, canvas_y = self.canvas.coords(self.stamp_item_id)
            final_abs_x = canvas_x / self.pdf_display_scale
            final_abs_y = canvas_y / self.pdf_display_scale
        else: # スタンプがない場合（エラーケース）
            final_abs_x = self.stamp_abs_x
            final_abs_y = self.stamp_abs_y

        self.result = (
            self.current_font_size.get(),
            final_abs_x,
            final_abs_y,
            self.current_rotation.get(),
            tuple(self.current_color_rgb) # type: ignore
        )
        if self.doc: self.doc.close()
        self.destroy()

    def cancel(self):
        self.result = None
        if self.doc: self.doc.close()
        self.destroy()


# -------------------- 設定ダイアログ --------------------
class ConfigDialog(tk.Toplevel):
    def __init__(self, master, app_config: AppConfig):
        super().__init__(master, padx=10, pady=10)
        self.transient(master)
        self.grab_set()
        self.app_config = app_config
        self.current_config_vars: Dict[str, tk.Variable] = {} # 一時的な設定値を保持

        self.title("設定")
        self.geometry("600x550") # 少し広めに

        self.result: Optional[Dict[str, Any]] = None

        self._create_ui()
        self._load_config_to_vars()
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)


    def _create_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=BOTH, expand=True, pady=5)

        # --- 基本設定タブ ---
        tab_basic = ttk.Frame(notebook, padding=10)
        notebook.add(tab_basic, text="基本")
        self._create_basic_tab(tab_basic)

        # --- 配置設定タブ ---
        tab_layout = ttk.Frame(notebook, padding=10)
        notebook.add(tab_layout, text="スタンプ配置")
        self._create_layout_tab(tab_layout)

        # --- Word出力タブ ---
        tab_word = ttk.Frame(notebook, padding=10)
        notebook.add(tab_word, text="Word出力")
        self._create_word_tab(tab_word)

        # --- その他オプションタブ ---
        tab_options = ttk.Frame(notebook, padding=10)
        notebook.add(tab_options, text="その他")
        self._create_options_tab(tab_options)
        
        # --- ボタンフレーム ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10,0))

        ttk.Button(btn_frame, text="デフォルトに戻す", command=self._on_reset_defaults, style="warning.Outline.TButton").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="OK", command=self._on_ok, style="success.TButton").pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self._on_cancel, style="danger.Outline.TButton").pack(side=RIGHT)

    def _add_config_entry(self, parent, label_text: str, key: str, var_type: type, **kwargs) -> tk.Widget:
        """設定項目用のラベルと入力ウィジェットを生成・配置し、StringVarなどを返すヘルパー"""
        ttk.Label(parent, text=label_text).pack(side=LEFT, padx=(0,5))
        
        current_value = self.app_config.get(key)
        
        if var_type == tk.StringVar:
            var = tk.StringVar(value=str(current_value))
        elif var_type == tk.IntVar:
            var = tk.IntVar(value=int(current_value))
        elif var_type == tk.DoubleVar:
            var = tk.DoubleVar(value=float(current_value))
        elif var_type == tk.BooleanVar:
            var = tk.BooleanVar(value=bool(current_value))
        else:
            raise ValueError(f"Unsupported var_type: {var_type}")
            
        self.current_config_vars[key] = var

        widget_type = kwargs.pop("widget", ttk.Entry)
        entry_width = kwargs.pop("width", 25)

        if widget_type == ttk.Combobox:
            widget = widget_type(parent, textvariable=var, width=entry_width, **kwargs)
        elif widget_type == ttk.Checkbutton:
            widget = widget_type(parent, variable=var, **kwargs)
        elif widget_type == ttk.Spinbox:
             widget = widget_type(parent, textvariable=var, width=entry_width, **kwargs)
        else: # ttk.Entry
            widget = widget_type(parent, textvariable=var, width=entry_width, **kwargs)
        
        widget.pack(side=LEFT, fill=X, expand=True, padx=(0,10))
        return widget

    def _create_basic_tab(self, parent_frame: ttk.Frame):
        # モード
        f_mode = ttk.Frame(parent_frame); f_mode.pack(fill=X, pady=3)
        ttk.Label(f_mode, text="モード:").pack(side=LEFT, padx=(0,5))
        self.current_config_vars["mode"] = tk.StringVar(value=self.app_config.get("mode"))
        rb_evidence = ttk.Radiobutton(f_mode, text="証拠番号", variable=self.current_config_vars["mode"], value="evidence")
        rb_evidence.pack(side=LEFT, padx=2)
        rb_attachment = ttk.Radiobutton(f_mode, text="添付資料", variable=self.current_config_vars["mode"], value="attachment")
        rb_attachment.pack(side=LEFT, padx=2)

        # 接頭辞
        f_prefix = ttk.Frame(parent_frame); f_prefix.pack(fill=X, pady=3)
        self._add_config_entry(f_prefix, "接頭辞:", "prefix", tk.StringVar, widget=ttk.Combobox, values=["甲", "乙", "弁", "その他"], width=10)
        
        # 開始主番号
        f_start_main = ttk.Frame(parent_frame); f_start_main.pack(fill=X, pady=3)
        self._add_config_entry(f_start_main, "開始主番号:", "start_main", tk.IntVar, widget=ttk.Spinbox, from_=1, to=9999, width=10)

        # 枝番自動増加
        f_branch_auto = ttk.Frame(parent_frame); f_branch_auto.pack(fill=X, pady=3)
        self._add_config_entry(f_branch_auto, "枝番自動増加:", "branch_auto", tk.BooleanVar, widget=ttk.Checkbutton, text="")
        
        # 対象ページ
        f_target_pages = ttk.Frame(parent_frame); f_target_pages.pack(fill=X, pady=3)
        self._add_config_entry(f_target_pages, "対象ページ:", "target_pages", tk.StringVar, widget=ttk.Combobox, values=["first", "all", "1,3,5 (例)"], width=15)
        ToolTip(f_target_pages.winfo_children()[-1], text="first: 先頭ページのみ\nall: 全ページ\n例: 1,3,5 (カンマ区切りでページ番号指定)")


    def _create_layout_tab(self, parent_frame: ttk.Frame):
        # フォントサイズ
        f_font_size = ttk.Frame(parent_frame); f_font_size.pack(fill=X, pady=3)
        self._add_config_entry(f_font_size, "フォントサイズ:", "font_size", tk.IntVar, widget=ttk.Spinbox, from_=8, to=200, width=10)

        # 回転角
        f_rotation = ttk.Frame(parent_frame); f_rotation.pack(fill=X, pady=3)
        self._add_config_entry(f_rotation, "回転角 (°):", "rotation", tk.IntVar, widget=ttk.Combobox, values=[0, 90, 180, 270], state="readonly", width=10)

        # X オフセット
        f_offset_x = ttk.Frame(parent_frame); f_offset_x.pack(fill=X, pady=3)
        self._add_config_entry(f_offset_x, "X オフセット (pt):", "offset_x", tk.DoubleVar, widget=ttk.Spinbox, from_=-1000, to=1000, increment=0.5, width=10)

        # Y オフセット
        f_offset_y = ttk.Frame(parent_frame); f_offset_y.pack(fill=X, pady=3)
        self._add_config_entry(f_offset_y, "Y オフセット (pt):", "offset_y", tk.DoubleVar, widget=ttk.Spinbox, from_=-1000, to=1000, increment=0.5, width=10)
        
        # スタンプ色
        f_color = ttk.Frame(parent_frame); f_color.pack(fill=X, pady=3)
        ttk.Label(f_color, text="スタンプ色:").pack(side=LEFT, padx=(0,5))
        self.current_config_vars["stamp_color_rgb"] = tk.StringVar(value=str(self.app_config.get("stamp_color_rgb"))) # 文字列で保持
        self.color_btn = ttk.Button(f_color, text="色を選択", command=self._pick_stamp_color, style="Outline.TButton")
        self.color_btn.pack(side=LEFT)
        self.color_preview_label_cfg = ttk.Label(f_color, text="■", width=3)
        self.color_preview_label_cfg.pack(side=LEFT, padx=5)
        self._update_color_preview_config_dialog()


    def _pick_stamp_color(self):
        from tkinter import colorchooser
        current_rgb_str = self.current_config_vars["stamp_color_rgb"].get()
        try:
            # 文字列 '(r, g, b)' をタプルに変換
            current_rgb = tuple(map(int, current_rgb_str.strip("()").split(',')))
        except:
            current_rgb = DEFAULT_STAMP_COLOR

        initial_hex = f"#{current_rgb[0]:02x}{current_rgb[1]:02x}{current_rgb[2]:02x}"
        
        new_color_tuple = colorchooser.askcolor(color=initial_hex, parent=self, title="スタンプの色を選択")
        if new_color_tuple and new_color_tuple[0]:
            rgb_int = tuple(int(c) for c in new_color_tuple[0])
            self.current_config_vars["stamp_color_rgb"].set(str(rgb_int))
            self._update_color_preview_config_dialog()

    def _update_color_preview_config_dialog(self):
        rgb_str = self.current_config_vars["stamp_color_rgb"].get()
        try:
            rgb = tuple(map(int, rgb_str.strip("()").split(',')))
            hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            self.color_preview_label_cfg.config(foreground=hex_color)
        except: # パース失敗時
            self.color_preview_label_cfg.config(foreground="black")


    def _create_word_tab(self, parent_frame: ttk.Frame):
        # Word文書を生成
        f_make_docx = ttk.Frame(parent_frame); f_make_docx.pack(fill=X, pady=3)
        self._add_config_entry(f_make_docx, "証拠説明書を生成:", "make_docx", tk.BooleanVar, widget=ttk.Checkbutton, text="")

        # テンプレートパス
        f_tpl_path = ttk.Frame(parent_frame); f_tpl_path.pack(fill=X, pady=3)
        ttk.Label(f_tpl_path, text="テンプレートパス:").pack(side=LEFT, padx=(0,5))
        self.current_config_vars["tpl_path"] = tk.StringVar(value=self.app_config.get("tpl_path"))
        entry_tpl = ttk.Entry(f_tpl_path, textvariable=self.current_config_vars["tpl_path"], width=35)
        entry_tpl.pack(side=LEFT, fill=X, expand=True)
        btn_browse_tpl = ttk.Button(f_tpl_path, text="参照...", command=lambda: self._browse_file("tpl_path", [("Word Template", "*.docx")]), style="Outline.TButton")
        btn_browse_tpl.pack(side=LEFT, padx=(5,0))

        # 出力名prefix
        f_doc_prefix = ttk.Frame(parent_frame); f_doc_prefix.pack(fill=X, pady=3)
        self._add_config_entry(f_doc_prefix, "出力名Prefix:", "doc_prefix", tk.StringVar, width=30)

    def _create_options_tab(self, parent_frame: ttk.Frame):
        # バックアップを作成
        f_backup = ttk.Frame(parent_frame); f_backup.pack(fill=X, pady=3)
        self._add_config_entry(f_backup, "処理前にバックアップ作成:", "create_backup", tk.BooleanVar, widget=ttk.Checkbutton, text="")

        # バックアップ先フォルダ
        f_backup_dir = ttk.Frame(parent_frame); f_backup_dir.pack(fill=X, pady=3)
        ttk.Label(f_backup_dir, text="バックアップ先フォルダ:").pack(side=LEFT, padx=(0,5))
        self.current_config_vars["backup_dir"] = tk.StringVar(value=self.app_config.get("backup_dir"))
        entry_backup_dir = ttk.Entry(f_backup_dir, textvariable=self.current_config_vars["backup_dir"], width=30)
        entry_backup_dir.pack(side=LEFT, fill=X, expand=True)
        btn_browse_backup_dir = ttk.Button(f_backup_dir, text="参照...", command=lambda: self._browse_directory("backup_dir"), style="Outline.TButton")
        btn_browse_backup_dir.pack(side=LEFT, padx=(5,0))
        ToolTip(entry_backup_dir, text="空の場合、元ファイルと同じ場所に作成します。")

        # 設定自動保存
        f_autosave = ttk.Frame(parent_frame); f_autosave.pack(fill=X, pady=3)
        self._add_config_entry(f_autosave, "設定変更時に自動保存:", "auto_save_config", tk.BooleanVar, widget=ttk.Checkbutton, text="")

        # 出力ファイル名テンプレート
        f_out_template = ttk.Frame(parent_frame); f_out_template.pack(fill=X, pady=3)
        self._add_config_entry(f_out_template, "出力ファイル名テンプレート:", "output_filename_template", tk.StringVar, width=30)
        ToolTip(f_out_template.winfo_children()[-1], text="使用可能: {text}, {original_basename}")

        # UIテーマ
        f_theme = ttk.Frame(parent_frame); f_theme.pack(fill=X, pady=3)
        themes = sorted(tb.Style().theme_names())
        self._add_config_entry(f_theme, "UIテーマ:", "theme", tk.StringVar, widget=ttk.Combobox, values=themes, state="readonly", width=15)
        ToolTip(f_theme.winfo_children()[-1], text="変更はアプリ再起動後に反映されます。")
        
        # ログレベル
        f_loglevel = ttk.Frame(parent_frame); f_loglevel.pack(fill=X, pady=3)
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self._add_config_entry(f_loglevel, "ログレベル:", "log_level", tk.StringVar, widget=ttk.Combobox, values=log_levels, state="readonly", width=10)
        ToolTip(f_loglevel.winfo_children()[-1], text="変更はアプリ再起動後に反映されます。")


    def _browse_file(self, config_key: str, filetypes: List[Tuple[str, str]]):
        var = self.current_config_vars.get(config_key)
        if not var: return
        
        initial_dir = os.path.dirname(var.get()) if var.get() else os.path.expanduser("~")
        filepath = filedialog.askopenfilename(
            title="ファイルを選択",
            initialdir=initial_dir,
            filetypes=filetypes,
            parent=self
        )
        if filepath:
            var.set(filepath)

    def _browse_directory(self, config_key: str):
        var = self.current_config_vars.get(config_key)
        if not var: return

        initial_dir = var.get() if var.get() and os.path.isdir(var.get()) else os.path.expanduser("~")
        dirpath = filedialog.askdirectory(
            title="フォルダを選択",
            initialdir=initial_dir,
            parent=self
        )
        if dirpath:
            var.set(dirpath)

    def _load_config_to_vars(self):
        """app_config の値を current_config_vars にロード"""
        for key, var in self.current_config_vars.items():
            value = self.app_config.get(key)
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            elif isinstance(var, tk.IntVar):
                var.set(int(value))
            elif isinstance(var, tk.DoubleVar):
                var.set(float(value))
            else: # tk.StringVar
                var.set(str(value))
        self._update_color_preview_config_dialog() # 色プレビューも更新

    def _on_ok(self):
        self.result = {}
        for key, var in self.current_config_vars.items():
            val = var.get()
            # 特殊な変換が必要な場合 (例: 色)
            if key == "stamp_color_rgb":
                try:
                    val = tuple(map(int, str(val).strip("()").split(',')))
                except:
                    val = DEFAULT_STAMP_COLOR # エラー時はデフォルト
            self.result[key] = val
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    def _on_reset_defaults(self):
        if Messagebox.yesno("設定をデフォルトに戻しますか？", parent=self) == "Yes":
            # app_config のデフォルト値を current_config_vars にロード
            temp_defaults = self.app_config.defaults.copy()
            for key, var in self.current_config_vars.items():
                value = temp_defaults.get(key)
                if isinstance(var, tk.BooleanVar): var.set(bool(value))
                elif isinstance(var, tk.IntVar): var.set(int(value))
                elif isinstance(var, tk.DoubleVar): var.set(float(value))
                else: var.set(str(value))
            self._update_color_preview_config_dialog()
            logger.info("設定ダイアログの値をデフォルトに戻しました（未確定）。")


# -------------------- メインアプリ --------------------
class BangogoApp(tb.Window):
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        # テーマを適用してWindowを初期化
        super().__init__(themename=self.app_config.get("theme", "litera"))
        
        self.title(APP_NAME)
        try:
            self.geometry(self.app_config.get("window_geometry"))
        except:
            self.geometry("1000x700") # フォールバック
            
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # フォント設定 (ttkbootstrapはデフォルトで良い感じのフォントを使うが、明示も可能)
        # self.style.configure('.', font=(BASE_FONT_PATH.split('\\')[-1].split('.')[0] if '\\' in BASE_FONT_PATH else 'Meiryo UI', 10)) # Windows向け例

        self.files_data: List[Dict[str, Any]] = [] # Treeviewに表示するファイルのメタデータリスト
        self.sort_states: Dict[str, bool] = {} # 列ソート状態 (True:昇順, False:降順)
        self.move_history: List[List[str]] = [] # Treeview行移動のUndo用

        self._setup_styles()
        self._setup_ui()
        self._update_basic_panel_from_config() # 初期値をUIに反映

        # DND初期化 (Treeviewに対して)
        if DND_AVAILABLE:
            try:
                # self.tree が TkinterDnD.DnDWrapper インスタンスになる
                self.tree.drop_target_register(DND_FILES)
                self.tree.dnd_bind('<<Drop>>', self._on_drop)
                logger.info("ドラッグ＆ドロップ機能を有効化しました。")
            except Exception as e:
                logger.warning(f"ドラッグ＆ドロップ初期化失敗: {e}")
                # messagebox.showwarning("警告", f"ドラッグ＆ドロップ機能の初期化に失敗しました。\n{e}")
        else:
            logger.info("tkinterdnd2が見つからないため、ドラッグ＆ドロップ機能は無効です。")
            # messagebox.showinfo("情報", "tkinterdnd2ライブラリが見つかりません。\nドラッグ＆ドロップ機能は利用できません。")
        
        # ログレベル設定
        log_level_str = self.app_config.get("log_level", "INFO").upper()
        if hasattr(logging, log_level_str):
            logger.setLevel(getattr(logging, log_level_str))
            logging.getLogger().setLevel(getattr(logging, log_level_str)) # root loggerも
        
        self.log_message(f"{APP_NAME} を起動しました。テーマ: {self.app_config.get('theme')}", "info")

    def _setup_styles(self):
        # カスタムスタイルが必要な場合ここに記述
        # 例: self.style.configure('Custom.TButton', font=('Helvetica', 12))
        pass

    def _setup_ui(self):
        # --- メインフレーム分割 (PanedWindow) ---
        main_paned_window = ttk.PanedWindow(self, orient=HORIZONTAL)
        main_paned_window.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # 左側フレーム (ファイルリストと基本設定)
        left_frame_outer = ttk.Frame(main_paned_window)
        main_paned_window.add(left_frame_outer, weight=2) # weightで初期サイズ比率

        # 右側フレーム (コントロールボタン)
        right_frame_outer = ttk.Frame(main_paned_window) # ttk.Labelframe(main_paned_window, text="操作") も可
        main_paned_window.add(right_frame_outer, weight=1)

        # --- 左側フレームの内容 ---
        # 基本設定パネル
        self._create_basic_settings_panel(left_frame_outer)
        
        # ファイルリスト (Treeview)
        self._create_file_list_treeview(left_frame_outer)

        # --- 右側フレームの内容 (コントロールボタン) ---
        self._create_control_buttons_panel(right_frame_outer)
        
        # --- 下部 (進捗バーとログ) ---
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=X, padx=5, pady=(0,5))

        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(bottom_frame, variable=self.progress_var, mode='determinate', length=300)
        self.progressbar.pack(fill=X, expand=True, pady=(5,2))

        # ScrolledText for logging
        self.log_text = ScrolledText(bottom_frame, height=6, autohide=True, relief="solid", borderwidth=1)
        # ScrolledText の初期 state は __init__ で textkwargs を通じて設定されるべき。
        # ここでは、log_message 内で都度 normal/disabled を切り替えるので、初期設定は必須ではない。
        # self.log_text.text.config(state="disabled") # 初期状態をdisabledにする場合
        self.log_text.pack(fill=X, expand=True, pady=(2,5))
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("info", foreground="blue")
        self.log_text.tag_config("success", foreground="green")


    def _create_basic_settings_panel(self, parent: ttk.Frame):
        """基本設定パネルを生成"""
        panel = ttk.Labelframe(parent, text="基本設定", padding=10)
        panel.pack(fill=X, padx=5, pady=(5,0))

        self.basic_config_vars: Dict[str, tk.Variable] = {}

        # モード
        f_mode = ttk.Frame(panel); f_mode.grid(row=0, column=0, columnspan=2, sticky=W, pady=2)
        ttk.Label(f_mode, text="モード:").pack(side=LEFT)
        self.basic_config_vars["mode"] = tk.StringVar()
        rb_e = ttk.Radiobutton(f_mode, text="証拠番号", variable=self.basic_config_vars["mode"], value="evidence", command=self._on_basic_config_change)
        rb_e.pack(side=LEFT, padx=(5,2))
        rb_a = ttk.Radiobutton(f_mode, text="添付資料", variable=self.basic_config_vars["mode"], value="attachment", command=self._on_basic_config_change)
        rb_a.pack(side=LEFT, padx=2)

        # 接頭辞
        f_prefix = ttk.Frame(panel); f_prefix.grid(row=1, column=0, sticky=W, pady=2)
        ttk.Label(f_prefix, text="接頭辞:").pack(side=LEFT)
        self.basic_config_vars["prefix"] = tk.StringVar()
        combo_prefix = ttk.Combobox(f_prefix, textvariable=self.basic_config_vars["prefix"], values=["甲", "乙", "弁", "その他"], width=8, state="readonly")
        combo_prefix.pack(side=LEFT, padx=5)
        combo_prefix.bind("<<ComboboxSelected>>", self._on_basic_config_change) # Combobox用
        self.basic_config_vars["prefix"].trace_add("write", self._on_basic_config_change) # 手入力も対応する場合

        # 開始主番号
        f_start_main = ttk.Frame(panel); f_start_main.grid(row=1, column=1, sticky=W, pady=2)
        ttk.Label(f_start_main, text="開始主番号:").pack(side=LEFT)
        self.basic_config_vars["start_main"] = tk.IntVar()
        spin_start = ttk.Spinbox(f_start_main, from_=1, to=9999, textvariable=self.basic_config_vars["start_main"], width=6, command=self._on_basic_config_change)
        spin_start.pack(side=LEFT, padx=5)
        self.basic_config_vars["start_main"].trace_add("write", self._on_basic_config_change)


        # 枝番自動増加
        f_branch_auto = ttk.Frame(panel); f_branch_auto.grid(row=2, column=0, columnspan=2, sticky=W, pady=2)
        self.basic_config_vars["branch_auto"] = tk.BooleanVar()
        cb_branch = ttk.Checkbutton(f_branch_auto, text="枝番自動増加", variable=self.basic_config_vars["branch_auto"], command=self._on_basic_config_change)
        cb_branch.pack(side=LEFT, padx=5)


    def _update_basic_panel_from_config(self):
        """app_config の値を基本設定パネルのウィジェット変数に反映"""
        for key, var in self.basic_config_vars.items():
            value = self.app_config.get(key)
            try:
                if isinstance(var, tk.BooleanVar): var.set(bool(value))
                elif isinstance(var, tk.IntVar): var.set(int(value))
                else: var.set(str(value)) # StringVar
            except Exception as e:
                logger.error(f"基本設定UIへの値設定エラー (key: {key}, value: {value}): {e}")


    def _on_basic_config_change(self, *args):
        """基本設定パネルの変更を app_config に即時反映"""
        for key, var in self.basic_config_vars.items():
            try:
                self.app_config.set(key, var.get())
            except Exception as e:
                logger.error(f"基本設定のconfigへの保存エラー (key: {key}): {e}")
        # self.log_message("基本設定が変更されました。", "debug") # ログがうるさい場合はdebugレベル


    def _create_file_list_treeview(self, parent: ttk.Frame):
        """ファイルリスト用のTreeviewを生成"""
        list_frame = ttk.Labelframe(parent, text="ファイルリスト", padding=10)
        list_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Treeviewのカラム定義
        # (key, header_text, width, anchor, show_by_default)
        self.tree_cols_def = [
            ("name", "ファイル名", 250, W, True),
            ("main_num", "主番号", 60, CENTER, True),
            ("branch_num", "枝番", 50, CENTER, True),
            ("status", "状態", 80, CENTER, True),
            ("pages", "頁数", 40, E, True),
            ("size_str", "サイズ", 70, E, False),
            ("modified_str", "更新日時", 120, CENTER, False),
            ("full_path", "フルパス", 0, W, False), # 非表示だがデータ保持用
        ]
        
        # 設定に基づいて表示するカラムを決定
        visible_col_keys_from_config = self.app_config.get("show_file_details_cols", [])
        # 必須カラムは常に追加
        self.visible_cols = [c for c in self.tree_cols_def if c[4] or c[0] in visible_col_keys_from_config]
        # ただし、フルパスは表示しない
        self.visible_cols = [c for c in self.visible_cols if c[0] != "full_path"]


        self.tree = ttk.Treeview(
            list_frame,
            columns=[c[0] for c in self.visible_cols],
            show="headings",
            selectmode="extended",
            style="Treeview" # ttkbootstrapが自動で適用
        )

        for key, header, width, anchor, _ in self.visible_cols:
            self.tree.heading(key, text=header, command=lambda c=key: self._on_tree_heading_click(c))
            self.tree.column(key, width=width, anchor=anchor, stretch=(key=="name")) # ファイル名列のみ伸縮

        # スクロールバー
        tree_ysb = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        tree_xsb = ttk.Scrollbar(list_frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_ysb.set, xscrollcommand=tree_xsb.set)

        tree_ysb.pack(side=RIGHT, fill=Y)
        tree_xsb.pack(side=BOTTOM, fill=X)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        # イベントバインド
        self.tree.bind("<Double-1>", self._on_tree_double_click_edit)
        self.tree.bind("<Delete>", lambda e: self._remove_selected_files()) # Deleteキーで削除
        self.tree.bind("<Control-a>", lambda e: self.tree.selection_add(self.tree.get_children())) # 全選択
        self.tree.bind("<Button-3>", self._on_tree_right_click) # 右クリックメニュー

        # DND用 (初期化はメインクラスの __init__ で)
        # self.tree.dnd_bind('<<Drop>>', self._on_drop) # ここではなく __init__ で

        # 行ドラッグ並び替え用 (ttkbootstrapのTreeviewはネイティブDNDと異なる場合あり)
        self.tree.bind('<ButtonPress-1>', self._on_row_press_for_dnd)
        self.tree.bind('<B1-Motion>', self._on_row_motion_for_dnd)
        self.tree.bind('<ButtonRelease-1>', self._on_row_release_for_dnd)
        self._dragged_item_dnd = None # ドラッグ中アイテムID
        self._drag_start_y_dnd = 0


    def _create_control_buttons_panel(self, parent: ttk.Frame):
        """操作ボタンパネルを生成"""
        panel = ttk.Frame(parent, padding=10)
        panel.pack(fill=BOTH, expand=True, padx=5, pady=5)

        btn_width = 15 # ボタンの幅を統一

        # ファイル操作セクション
        file_ops_frame = ttk.Labelframe(panel, text="ファイル操作", padding=10)
        file_ops_frame.pack(fill=X, pady=(0,10))
        ttk.Button(file_ops_frame, text="ファイル追加", command=self._add_files_dialog, style="primary.TButton", width=btn_width).pack(fill=X, pady=3)
        ttk.Button(file_ops_frame, text="選択削除", command=self._remove_selected_files, style="danger.Outline.TButton", width=btn_width).pack(fill=X, pady=3)
        ttk.Button(file_ops_frame, text="全削除", command=self._clear_all_files, style="danger.TButton", width=btn_width).pack(fill=X, pady=3)

        # 番号設定セクション
        num_ops_frame = ttk.Labelframe(panel, text="番号設定", padding=10)
        num_ops_frame.pack(fill=X, pady=(0,10))
        ttk.Button(num_ops_frame, text="番号自動設定", command=self._auto_number_selected, style="info.TButton", width=btn_width).pack(fill=X, pady=3)
        ttk.Button(num_ops_frame, text="番号リセット", command=self._reset_numbers_all, style="warning.Outline.TButton", width=btn_width).pack(fill=X, pady=3)
        
        # プレビューと設定
        preview_conf_frame = ttk.Labelframe(panel, text="プレビューと設定", padding=10)
        preview_conf_frame.pack(fill=X, pady=(0,10))
        ttk.Button(preview_conf_frame, text="プレビュー", command=self._preview_selected_file, style="info.Outline.TButton", width=btn_width).pack(fill=X, pady=3)
        ttk.Button(preview_conf_frame, text="詳細設定", command=self._open_config_dialog, style="secondary.TButton", width=btn_width).pack(fill=X, pady=3)

        # ソート・フィルタ (将来用)
        # sort_filter_frame = ttk.Labelframe(panel, text="表示", padding=10)
        # sort_filter_frame.pack(fill=X, pady=(0,10))
        # ttk.Button(sort_filter_frame, text="ソートリセット", command=self._reset_tree_sort_order, width=btn_width).pack(fill=X, pady=3)
        # (フィルタ機能は未実装)

        # 実行ボタン (目立つように下部に配置)
        ttk.Button(panel, text="実行", command=self._execute_stamping, style="success.Large.TButton").pack(side=BOTTOM, fill=X, pady=(20,5))


    # --- Treeview DND (ファイルドロップ) ---
    def _on_drop(self, event):
        if not DND_AVAILABLE: return
        try:
            # event.data はスペース区切りのファイルパス文字列 (例: "{C:/path/to/file1.pdf} {C:/path/to/file2.pdf}")
            # tk.splitlist を使うと {} を適切に処理できる
            raw_files = self.tk.splitlist(event.data)
            # PDFファイルのみをフィルタリング
            pdf_files = [f for f in raw_files if f.lower().endswith(".pdf")]
            if pdf_files:
                self._add_files_to_tree(pdf_files)
            else:
                self.log_message("ドロップされたファイルにPDFが含まれていません。", "warning")
        except Exception as e:
            logger.error(f"ファイルドロップ処理エラー: {e}")
            self.log_message(f"ファイルドロップ処理エラー: {e}", "error")


    # --- Treeview編集 ---
    def _on_tree_double_click_edit(self, event):
        """Treeviewのセルをダブルクリックで編集可能にする。主番号と枝番のみ。"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        column_id_str = self.tree.identify_column(event.x) # "#1", "#2" など

        if not item_id or not column_id_str:
            return

        # column_id_str (#1など) からカラムキー (name, main_numなど) を取得
        col_idx = int(column_id_str.replace("#", "")) -1
        if not (0 <= col_idx < len(self.visible_cols)): return # 範囲外
        
        col_key = self.visible_cols[col_idx][0]

        # 主番号(main_num)と枝番(branch_num)のみ編集可能とする
        if col_key not in ["main_num", "branch_num"]:
            return

        x, y, width, height = self.tree.bbox(item_id, column_id_str)
        
        # 編集中の値を取得
        old_value_str = str(self.tree.set(item_id, col_key))
        
        entry_var = tk.StringVar(value=old_value_str)
        
        # インプレースエディタ (Entry) を作成
        editor = ttk.Entry(self.tree, textvariable=entry_var, justify=CENTER)
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()
       
        editor.selection_range(0, END)

        def _finish_edit(event_type: str):
            new_value_str = entry_var.get().strip()
            editor.destroy() # 先に破棄しないとフォーカスアウトで再帰することがある

            if event_type == "Return": # Enterキーで確定
                # 値の検証と更新
                if col_key == "main_num":
                    num = convert_to_int(new_value_str)
                    if new_value_str and num is None: # 空でなく、かつ変換失敗
                        Messagebox.show_warning("主番号は半角または全角の数字で入力してください。", parent=self)
                        return
                    # 空文字の場合はクリア、それ以外は数値化してセット
                    self.tree.set(item_id, col_key, str(num) if num is not None else "")
                elif col_key == "branch_num":
                    num = convert_to_int(new_value_str)
                    if new_value_str and num is None:
                        Messagebox.show_warning("枝番は半角または全角の数字で入力してください。", parent=self)
                        return
                    self.tree.set(item_id, col_key, str(num) if num is not None else "")
                
                self.tree.set(item_id, "status", "編集済" if new_value_str else "未設定")
                self._update_file_data_from_tree(item_id) # files_dataも更新
            # EscapeキーやFocusOutの場合は何もしない（元の値のまま）

        editor.bind("<Return>", lambda e: _finish_edit("Return"))
        editor.bind("<FocusOut>", lambda e: _finish_edit("FocusOut"))
        editor.bind("<Escape>", lambda e: _finish_edit("Escape"))

    def _update_file_data_from_tree(self, item_id: str):
        """Treeviewの変更をself.files_dataに反映する"""
        try:
            idx = self.tree.index(item_id) # Treeview内のインデックス
            if 0 <= idx < len(self.files_data):
                tree_values = self.tree.item(item_id, "values")
                # tree_values は表示されているカラムの順序
                # self.files_data のキーとマッピングする
                for i, col_def in enumerate(self.visible_cols):
                    col_key = col_def[0]
                    if col_key in self.files_data[idx]: # files_dataにキーが存在すれば更新
                         # 型変換を試みる
                        new_val_str = tree_values[i]
                        current_val_type = type(self.files_data[idx].get(col_key))
                        
                        if current_val_type == int:
                            converted_val = convert_to_int(new_val_str)
                            self.files_data[idx][col_key] = converted_val if converted_val is not None else 0 # or some default
                        elif current_val_type == float:
                            try: self.files_data[idx][col_key] = float(new_val_str)
                            except: pass # 変換失敗時はそのまま
                        else: # str or other
                            self.files_data[idx][col_key] = new_val_str
                        
                # 特に main_num, branch_num, status は直接更新
                self.files_data[idx]["main_num"] = convert_to_int(self.tree.set(item_id, "main_num"))
                self.files_data[idx]["branch_num"] = convert_to_int(self.tree.set(item_id, "branch_num"))
                self.files_data[idx]["status"] = self.tree.set(item_id, "status")

        except ValueError: # item_id がTreeviewにない場合など
            logger.warning(f"Treeviewからfiles_dataへの更新失敗: item_id {item_id} が見つかりません。")
        except Exception as e:
            logger.error(f"Treeviewからfiles_dataへの更新中エラー: {e}")


    # --- ファイル操作 ---
    def _add_files_dialog(self):
        """ファイル追加ダイアログを開き、選択されたPDFをリストに追加する。"""
        files = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDFファイル", "*.pdf"), ("すべてのファイル", "*.*")],
            parent=self
        )
        if files:
            self._add_files_to_tree(list(files))

    def _add_files_to_tree(self, file_paths: List[str]):
        """指定されたファイルパスのリストをTreeviewと内部データに追加する。"""
        added_count = 0
        skipped_count = 0
        
        # 既存のファイルパスをセットで保持（重複チェック用）
        existing_paths = {data["full_path"] for data in self.files_data}

        for f_path in file_paths:
            abs_path = os.path.abspath(f_path)
            if abs_path in existing_paths:
                self.log_message(f"スキップ (重複): {os.path.basename(abs_path)}", "warning")
                skipped_count += 1
                continue

            if not abs_path.lower().endswith(".pdf"):
                self.log_message(f"スキップ (非PDF): {os.path.basename(abs_path)}", "warning")
                skipped_count += 1
                continue
            
            if not validate_pdf_file(abs_path): # ここで簡易検証
                self.log_message(f"スキップ (無効PDF): {os.path.basename(abs_path)}", "error")
                Messagebox.show_error(f"ファイル '{os.path.basename(abs_path)}' は無効なPDFか、読み込めませんでした。", parent=self)
                skipped_count += 1
                continue

            file_details = get_file_details(abs_path)
            
            # Treeviewに表示する値のタプルを作成
            # self.visible_cols の順序に従う
            values_for_tree = []
            for col_key, _, _, _, _ in self.visible_cols:
                if col_key == "name": values_for_tree.append(file_details["name"])
                elif col_key == "main_num": values_for_tree.append("") # 初期値
                elif col_key == "branch_num": values_for_tree.append("") # 初期値
                elif col_key == "status": values_for_tree.append("未設定") # 初期値
                else: values_for_tree.append(file_details.get(col_key, ""))
            
            # files_data に格納するデータ (Treeview非表示のものも含む)
            new_file_data = {
                "name": file_details["name"],
                "full_path": abs_path, # 内部データとしてはフルパスを保持
                "main_num": None, # 初期値はNone
                "branch_num": None, # 初期値はNone
                "status": "未設定",
                "pages": file_details["pages"],
                "size_str": file_details["size_str"],
                "size_bytes": file_details["size_bytes"],
                "modified_str": file_details["modified_str"],
                "modified_timestamp": file_details["modified_timestamp"],
                # 他のメタデータも必要なら追加
            }
            
            item_id = self.tree.insert("", tk.END, values=tuple(values_for_tree))
            # files_data にも追加 (Treeviewの順序と一致させるため、ここでは単純append)
            # TreeviewのソートやD&D後はインデックスがずれるので注意が必要。
            # Treeviewのitem_idとfiles_dataの要素を紐付ける方法を検討すべき。
            # 簡単なのは、files_dataもitem_idをキーにした辞書にするか、
            # files_dataの各要素にitem_idを持たせる。
            # ここでは、files_dataのインデックスとTreeviewのインデックスが（初期追加時は）一致すると仮定。
            new_file_data["_tree_id"] = item_id # TreeviewのIDを紐付け
            self.files_data.append(new_file_data)
            
            existing_paths.add(abs_path)
            added_count += 1
        
        if added_count > 0:
            self.log_message(f"{added_count}個のPDFファイルを追加しました。", "success")
        if skipped_count > 0:
            self.log_message(f"{skipped_count}個のファイルはスキップされました（重複または非対応）。詳細はログ参照。", "warning")
        
        self._update_tree_alternating_rows()


    def _remove_selected_files(self):
        """選択されたファイルをTreeviewと内部データから削除する。"""
        selected_item_ids = self.tree.selection()
        if not selected_item_ids:
            Messagebox.show_info("削除するファイルが選択されていません。", parent=self)
            return

        if Messagebox.yesno(f"{len(selected_item_ids)}個のファイルをリストから削除しますか？", parent=self) == "Yes":
            # 削除対象の full_path を集める (files_dataからの削除用)
            paths_to_remove = set()
            for item_id in selected_item_ids:
                # files_data から対応する要素を探す
                # _tree_id を使って効率的に探せるように files_data の構造を見直すのが理想
                # ここでは線形探索で対応
                found_data = next((data for data in self.files_data if data.get("_tree_id") == item_id), None)
                if found_data:
                    paths_to_remove.add(found_data["full_path"])
            
            # self.files_data から削除
            self.files_data = [data for data in self.files_data if data["full_path"] not in paths_to_remove]
            
            # Treeview から削除
            for item_id in selected_item_ids:
                self.tree.delete(item_id)
            
            self.log_message(f"{len(selected_item_ids)}個のファイルを削除しました。", "info")
            self._update_tree_alternating_rows()


    def _clear_all_files(self):
        """すべてのファイルをTreeviewと内部データから削除する。"""
        if not self.tree.get_children():
            Messagebox.show_info("リストにファイルがありません。", parent=self)
            return
        
        if Messagebox.yesno("リスト内のすべてのファイルを削除しますか？", parent=self) == "Yes":
            self.tree.delete(*self.tree.get_children())
            self.files_data.clear()
            self.log_message("すべてのファイルを削除しました。", "info")


    # --- 番号設定 ---
    def _auto_number_selected(self):
        """選択された行に番号を自動設定する。"""
        selected_item_ids = self.tree.selection()
        if not selected_item_ids:
            Messagebox.show_warning("番号を設定する行を選択してください。", parent=self)
            return

        # Treeviewでの現在の表示順で処理
        # (Treeview.get_children() は表示順とは限らないので、selection() の順序を使うか、
        #  明示的にソートされた順序を取得する必要がある。ここでは選択順。)
        
        # files_data と Treeview の item_id を紐付けて処理
        # 選択された item_id に対応する files_data の要素を取得
        # (ソートやD&Dを考慮すると、item_id から files_data の要素を引く必要がある)
        
        # ここでは簡単化のため、Treeviewの表示順（選択順）で処理
        # ただし、files_dataの更新は _update_file_data_from_tree で行う
        
        start_main = self.app_config.get("start_main", 1)
        branch_auto = self.app_config.get("branch_auto", False)
        
        # 選択されたアイテムをTreeview上の順序でソート (もし必要なら)
        # sorted_selected_ids = sorted(selected_item_ids, key=lambda item_id: self.tree.index(item_id))
        # (Treeview.selection() は通常選択順なので、ソートは不要かもしれない)

        current_main_num = start_main
        
        # 複数選択時の主番号の扱い:
        #   1. 全て同じ主番号にするか (枝番で区別)
        #   2. 連番にするか
        # ここでは、選択された各アイテムに連番の主番号を振る
        
        for i, item_id in enumerate(selected_item_ids):
            main_to_set = current_main_num + i
            branch_to_set_str = ""


            if branch_auto:
                # 枝番自動増加ロジック (例: 1, 2, 3... or a, b, c...)
                # ここでは単純に数字の枝番を振る (選択されたアイテム内での連番)
                # もし主番号が同じアイテムが連続する場合の枝番処理はより複雑になる
                # ここでは、選択されたアイテムごとに主番号がインクリメントされるので、
                # 枝番は常に1から、または空にする。
                # もし「同じ主番号で枝番を振る」なら、そのロジックが必要。
                # 今回は、選択されたものに連番の主番号を振る。
                # ただし、枝番自動がONなら、各アイテムに「の1」をつけるなど。
                #     → シンプルに、枝番自動ONなら、各アイテムに「1」を振る (もし枝番が空なら)
                
                # current_branch_val_str = self.tree.set(item_id, "branch_num")
                # if not current_branch_val_str: # 枝番が空の場合のみ自動設定
                # branch_to_set_str = "1" # もし枝番自動なら、とりあえず "1" を入れるなど。
                pass # 枝番自動の具体的なロジックは要件次第。ここでは主番号のみ設定。


            self.tree.set(item_id, "main_num", str(main_to_set))
            if branch_to_set_str: # 枝番も設定する場合
                self.tree.set(item_id, "branch_num", branch_to_set_str)
            
            self.tree.set(item_id, "status", "編集済")
            self._update_file_data_from_tree(item_id)

        self.log_message(f"{len(selected_item_ids)}個のファイルに番号を自動設定しました。", "info")


    def _reset_numbers_all(self):
        """すべてのファイルの番号と状態をリセットする。"""
        if not self.tree.get_children():
            Messagebox.show_info("リストにファイルがありません。", parent=self)
            return
        
        if Messagebox.yesno("すべてのファイルの番号をリセットしますか？", parent=self) == "Yes":
            for item_id in self.tree.get_children():
                self.tree.set(item_id, "main_num", "")
                self.tree.set(item_id, "branch_num", "")
                self.tree.set(item_id, "status", "未設定")
                self._update_file_data_from_tree(item_id)
            self.log_message("すべてのファイルの番号をリセットしました。", "info")

    # --- プレビューと設定 ---
    def _preview_selected_file(self):
        selected_item_ids = self.tree.selection()
        if not selected_item_ids:
            Messagebox.show_warning("プレビューするファイルを選択してください。", parent=self)
            return
        if len(selected_item_ids) > 1:
            Messagebox.show_info("プレビューは一度に1つのファイルのみ可能です。最初の選択ファイルを使用します。", parent=self)

        item_id = selected_item_ids[0]
        
        # item_id から files_data の要素を取得
        file_data = next((data for data in self.files_data if data.get("_tree_id") == item_id), None)
        if not file_data:
            Messagebox.show_error("選択されたファイルのデータが見つかりません。", parent=self)
            return

        pdf_path = file_data["full_path"]
        
        # スタンプ文字列を生成
        main_num_str = self.tree.set(item_id, "main_num")
        branch_num_str = self.tree.set(item_id, "branch_num")

        if not main_num_str: # 主番号が未設定の場合はプレビューできない
            # 自動で仮の番号を振るか、エラーにするか
            # ここでは、仮番号(1)を振ってプレビューを試みる
            # Messagebox.show_warning("主番号が未設定です。プレビューできません。", parent=self)
            # return
            if Messagebox.yesno("主番号が未設定です。仮の番号（1番）でプレビューしますか？", parent=self) != "Yes":
                return
            main_num_to_use = 1
            self.tree.set(item_id, "main_num", "1") # 仮で設定
            self.tree.set(item_id, "status", "編集済")
            self._update_file_data_from_tree(item_id)
        else:
            main_num_to_use = convert_to_int(main_num_str)
            if main_num_to_use is None: # 変換失敗
                 Messagebox.show_error("主番号が無効な値です。", parent=self)
                 return
        
        branch_val = branch_num_str if branch_num_str else None

        text_to_stamp = build_label_text(
            self.app_config.get("mode"),
            self.app_config.get("prefix"),
            main_num_to_use,
            branch_val
        )

        preview_dialog = PreviewDialog(
            self,
            self.app_config,
            pdf_path,
            text_to_stamp,
            self.app_config.get("font_size"),
            self.app_config.get("offset_x"),
            self.app_config.get("offset_y"),
            self.app_config.get("rotation"),
            self.app_config.get("stamp_color_rgb")
        )
        self.wait_window(preview_dialog) # ダイアログが閉じるまで待つ

        if preview_dialog.result:
            fsize, ox, oy, rot, color_rgb = preview_dialog.result
            self.app_config.set("font_size", fsize)
            self.app_config.set("offset_x", ox)
            self.app_config.set("offset_y", oy)
            self.app_config.set("rotation", rot)
            self.app_config.set("stamp_color_rgb", color_rgb)
            # self.app_config.save() # set内で自動保存されるはず
            self.log_message("プレビュー結果を既定の設定に反映しました。", "info")
            # 基本設定パネルも更新 (もし関連項目があれば)
            # self._update_basic_panel_from_config() # offsetなどは基本パネルにないので不要


    def _open_config_dialog(self):
        config_dialog = ConfigDialog(self, self.app_config)
        self.wait_window(config_dialog)

        if config_dialog.result:
            changed_keys = []
            for key, value in config_dialog.result.items():
                if self.app_config.get(key) != value:
                    changed_keys.append(key)
                self.app_config.set(key, value) # これで保存もされる (auto_save_config=Trueの場合)
            
            if not self.app_config.get("auto_save_config"): # 手動保存の場合
                self.app_config.save()

            if changed_keys:
                self.log_message(f"設定が変更されました: {', '.join(changed_keys)}", "info")
                # UIテーマやログレベルの変更は再起動が必要なことを通知
                if "theme" in changed_keys:
                    Messagebox.show_info("UIテーマの変更は、アプリケーションの再起動後に反映されます。", parent=self)
                if "log_level" in changed_keys:
                    new_level_str = self.app_config.get("log_level").upper()
                    if hasattr(logging, new_level_str):
                        logger.setLevel(getattr(logging, new_level_str))
                        logging.getLogger().setLevel(getattr(logging, new_level_str))
                    Messagebox.show_info("ログレベルの変更は、一部即時、一部再起動後に完全に反映されます。", parent=self)

            self._update_basic_panel_from_config() # 基本設定パネルを更新
            # Treeviewの表示カラムも更新する必要がある場合
            # self._rebuild_treeview_columns_and_data()


    # --- 実行 ---
    def _execute_stamping(self):
        """スタンプ処理を実行する。"""
        if not self.tree.get_children():
            Messagebox.show_warning("処理対象のファイルがリストにありません。", parent=self)
            return

        out_dir = filedialog.askdirectory(title="出力先フォルダを選択", parent=self)
        if not out_dir:
            self.log_message("出力先フォルダが選択されませんでした。処理を中止します。", "info")
            return

        # 処理対象アイテムのリストを作成 (Treeviewの現在の順序で)
        items_to_process = []
        validation_errors = 0
        for item_id in self.tree.get_children(): # Treeviewの表示順
            file_data = next((data for data in self.files_data if data.get("_tree_id") == item_id), None)
            if not file_data:
                logger.error(f"Treeviewアイテム {item_id} に対応する内部データが見つかりません。スキップします。")
                validation_errors +=1
                self.tree.set(item_id, "status", "エラー(内部)")
                continue

            pdf_path = file_data["full_path"]
            main_num_str = self.tree.set(item_id, "main_num")
            branch_num_str = self.tree.set(item_id, "branch_num")

            if not os.path.exists(pdf_path):
                self.log_message(f"エラー: ファイルが見つかりません - {os.path.basename(pdf_path)}", "error")
                self.tree.set(item_id, "status", "ファイル不在")
                validation_errors += 1
                continue
            
            if not main_num_str:
                self.log_message(f"エラー: 主番号未設定 - {os.path.basename(pdf_path)}", "error")
                self.tree.set(item_id, "status", "主番号不足")
                validation_errors += 1
                continue
            
            main_num = convert_to_int(main_num_str)
            if main_num is None:
                self.log_message(f"エラー: 主番号が無効 - {os.path.basename(pdf_path)} ({main_num_str})", "error")
                self.tree.set(item_id, "status", "主番号無効")
                validation_errors +=1
                continue
            
            branch_val = branch_num_str if branch_num_str else None # 空文字列はNoneとして扱う

            items_to_process.append({
                "item_id": item_id,
                "pdf_path": pdf_path,
                "main_num": main_num,
                "branch_val": branch_val,
                "file_data_ref": file_data # 元のfile_dataへの参照 (更新用)
            })

        if validation_errors > 0:
            Messagebox.show_error(f"{validation_errors}個のファイルで検証エラーが発生しました。リストを確認してください。", parent=self)
            return
        
        if not items_to_process:
            Messagebox.show_info("処理可能なファイルがありません。", parent=self)
            return

        if Messagebox.yesno(f"{len(items_to_process)}個のファイルにスタンプ処理を実行しますか？\n出力先: {out_dir}", parent=self) != "Yes":
            self.log_message("ユーザーにより処理がキャンセルされました。", "info")
            return

        # --- 処理開始 ---
        self.log_message(f"=== スタンプ処理開始 ({len(items_to_process)}件) ===", "info")
        self.progress_var.set(0)
        self.progressbar.config(maximum=len(items_to_process))
        
        success_count = 0
        fail_count = 0
        processed_evidence_data_for_word = [] # Word生成用のデータ

        # 設定を取得
        cfg = self.app_config.data # 直接dataを参照して高速化 (setは使わないので)
        stamp_mode = cfg["mode"]
        stamp_prefix = cfg["prefix"]
        font_size = cfg["font_size"]
        rotation = cfg["rotation"]
        offset_x = cfg["offset_x"]
        offset_y = cfg["offset_y"]
        stamp_color = cfg["stamp_color_rgb"]
        target_pages = cfg["target_pages"]
        output_template = cfg["output_filename_template"]
        create_backup_flag = cfg["create_backup"]
        backup_dir_path = cfg["backup_dir"] if cfg.get("backup_dir") else None


        for i, item_info in enumerate(items_to_process):
            item_id = item_info["item_id"]
            pdf_path = item_info["pdf_path"]
            
            self.tree.set(item_id, "status", "処理中...")
            self.update_idletasks() # UI更新

            try:
                text_to_stamp = build_label_text(
                    stamp_mode,
                    stamp_prefix,
                    item_info["main_num"],
                    item_info["branch_val"]
                )

                if create_backup_flag:
                    backup_file(pdf_path, backup_dir_path) # バックアップ作成

                stamped_pdf_path = stamp_pdf(
                    pdf_path,
                    out_dir,
                    text_to_stamp,
                    offset_x,
                    offset_y,
                    font_size,
                    rotation,
                    stamp_color,
                    target_pages,
                    output_template
                )
                self.tree.set(item_id, "status", "完了")
                item_info["file_data_ref"]["status"] = "完了" # files_dataも更新
                self.log_message(f"✔ {os.path.basename(pdf_path)} → {os.path.basename(stamped_pdf_path)}", "success")
                success_count += 1
                
                # Word生成用データに追加
                processed_evidence_data_for_word.append({
                    "no": text_to_stamp,
                    "caption": os.path.basename(pdf_path), # とりあえずファイル名をキャプションに
                    "copy": "写し", # デフォルト
                    # 以下は空欄または固定値 (必要ならユーザー入力やPDF解析で取得)
                    "created": "", 
                    "author": "", 
                    "purpose": "",
                    "note": "" 
                })

            except Exception as e:
                self.tree.set(item_id, "status", "失敗")
                item_info["file_data_ref"]["status"] = "失敗"
                logger.error(f"スタンプ処理失敗 ({os.path.basename(pdf_path)}): {e}", exc_info=True)
                self.log_message(f"✖ {os.path.basename(pdf_path)}: 処理失敗 - {e}", "error")
                fail_count += 1
            
            self.progress_var.set(i + 1)
            self.update_idletasks()

        self.log_message(f"=== スタンプ処理完了 (成功: {success_count}, 失敗: {fail_count}) ===", "info")

        # Word文書生成
        if cfg["make_docx"] and processed_evidence_data_for_word:
            self.log_message("--- Word証拠説明書生成開始 ---", "info")
            try:
                tpl_path = cfg["tpl_path"]
                if not tpl_path or not os.path.exists(tpl_path):
                    raise FileNotFoundError(f"Wordテンプレートパスが無効です: {tpl_path}")
                
                # Word文書のコンテキスト情報
                # (例: 事件名、裁判所名など。これらは設定ダイアログで入力できるようにするのが望ましい)
                word_context = {
                    "bundle_title": cfg["doc_prefix"], # "証拠説明書" など
                    "first": processed_evidence_data_for_word[0]["no"] if processed_evidence_data_for_word else "",
                    "last": processed_evidence_data_for_word[-1]["no"] if processed_evidence_data_for_word else "",
                    "court": "（裁判所名）", # 固定値または設定から
                    "case_name": "（事件名）", # 固定値または設定から
                    "submitted_date": datetime.date.today().strftime("%Y年%m月%d日"),
                    "doc_prefix": cfg["doc_prefix"], # generate_evidence_doc内で使用
                }
                
                generated_word_path = generate_evidence_doc(
                    processed_evidence_data_for_word,
                    tpl_path,
                    word_context,
                    out_dir
                )
                self.log_message(f"Word証拠説明書を生成しました: {os.path.basename(generated_word_path)}", "success")
            except Exception as e:
                logger.error(f"Word証拠説明書生成失敗: {e}", exc_info=True)
                self.log_message(f"Word証拠説明書生成失敗: {e}", "error")
                Messagebox.show_error(f"Word証拠説明書の生成に失敗しました。\n{e}", parent=self)
        elif cfg["make_docx"] and not processed_evidence_data_for_word:
             self.log_message("スタンプ処理成功ファイルがないため、Word文書は生成されませんでした。", "warning")


        # 完了メッセージ
        if fail_count == 0:
            Messagebox.show_info(f"すべての処理が正常に完了しました。\n成功: {success_count}件", parent=self)
        else:
            Messagebox.show_warning(
                f"処理が完了しましたが、一部エラーが発生しました。\n成功: {success_count}件, 失敗: {fail_count}件\n詳細はログを確認してください。",
                parent=self
            )


    # --- Treeviewソートと表示 ---
    def _on_tree_heading_click(self, col_key: str):
        """Treeviewの列ヘッダクリックでソートを実行する。"""
        if not self.files_data: return

        # ソート方向 (昇順/降順の切り替え)
        current_sort_asc = self.sort_states.get(col_key, True) # デフォルトは昇順ソート開始
        new_sort_asc = not current_sort_asc
        self.sort_states = {col_key: new_sort_asc} # 他の列のソート状態はリセット

        # ソートキー関数
        def sort_key_func(item_data: Dict[str, Any]):
            val = item_data.get(col_key)
            if val is None: # Noneは最後に
                return (float('inf'),) if new_sort_asc else (float('-inf'),) 
            
            # 数値として比較できるものは数値に変換
            if col_key in ["main_num", "branch_num", "pages", "size_bytes", "modified_timestamp"]:
                num_val = convert_to_int(str(val)) # main_num, branch_num は None の可能性あり
                if num_val is not None: return num_val
                if isinstance(val, (int, float)): return val # pages, size_bytes など
            
            return str(val).lower() # 文字列として比較 (大文字小文字無視)

        self.files_data.sort(key=sort_key_func, reverse=not new_sort_asc)
        
        # Treeview再描画
        self._redisplay_treeview_from_files_data()
        
        # ヘッダにソート方向インジケータ (ttkbootstrapでは自動でない場合がある)
        for key, _, _, _, _ in self.visible_cols:
            current_text = self.tree.heading(key, "text")
            # 既存のインジケータを削除
            current_text = current_text.replace(" ▲", "").replace(" ▼", "")
            if key == col_key:
                indicator = " ▲" if new_sort_asc else " ▼"
                self.tree.heading(key, text=current_text + indicator)
            else:
                self.tree.heading(key, text=current_text)


    def _redisplay_treeview_from_files_data(self):
        """self.files_data の内容に基づいてTreeviewを再描画する。"""
        self.tree.delete(*self.tree.get_children()) # 全行削除
        
        for file_data in self.files_data:
            values_for_tree = []
            for col_key_def, _, _, _, _ in self.visible_cols:
                val = file_data.get(col_key_def)
                # main_num, branch_num が None の場合は空文字にする
                if val is None and col_key_def in ["main_num", "branch_num"]:
                    values_for_tree.append("")

                else:
                    values_for_tree.append(str(val) if val is not None else "")
            
            item_id = self.tree.insert("", tk.END, values=tuple(values_for_tree))
            file_data["_tree_id"] = item_id # Treeview IDを更新/設定

        self._update_tree_alternating_rows()

    def _update_tree_alternating_rows(self):
        """Treeviewの行に交互の背景色を適用する (ttkbootstrapのテーマによっては不要)"""
        self.tree.tag_configure("oddrow", background="white")
        self.tree.tag_configure("evenrow", background="lightgrey") # またはテーマに合わせた色
        
        for i, item_id in enumerate(self.tree.get_children()):
            if i % 2 == 0:
                self.tree.item(item_id, tags=("evenrow",))
            else:
                self.tree.item(item_id, tags=("oddrow",))
        # ttkbootstrapの標準スタイルで十分な場合はこの処理は不要か、style.map('Treeview', background=[('selected', ...)]) などで対応。
        # ここでは簡易的にタグで。


    # --- Treeview行ドラッグD&D (並び替え) ---
    def _on_row_press_for_dnd(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return

        # 修飾キー(Ctrl, Shift)が押されている場合は、Tk標準の選択処理に任せる
        # (event.state で判定: 0x0004 for Ctrl, 0x0001 for Shift on Windows)
        # 厳密な判定はプラットフォーム依存性があるため、ここでは単純化
        if event.state & (0x0004 | 0x0001): # Ctrl or Shift (Windows-like)
            self._dragged_item_dnd = None
            return

        # 無修飾クリックの場合、その行のみを選択状態にする
        self.tree.selection_set(iid) 
        self._dragged_item_dnd = iid
        self._drag_start_y_dnd = event.y
        self.tree.config(cursor="hand2") # ドラッグ中カーソル

        # 並び替え前の順序を履歴に保存 (Undo用)
        current_order_ids = list(self.tree.get_children())
        # files_data の順序も保存する必要がある
        # ここでは item_id の順序のみ保存。復元時に files_data も並べ替える。
        self.move_history.append(current_order_ids)
        if len(self.move_history) > 20: # 履歴上限
            self.move_history.pop(0)


    def _on_row_motion_for_dnd(self, event):
        if not self._dragged_item_dnd: return

        # y方向に一定以上動いたらドラッグ開始とみなす (クリックとの誤認防止)
        if abs(event.y - self._drag_start_y_dnd) < 5: # 閾値
            return

        target_iid = self.tree.identify_row(event.y)
        if target_iid and target_iid != self._dragged_item_dnd:
            # 移動先のインデックスを取得
            target_idx = self.tree.index(target_iid)
            
            # アイテムを移動
            # target_iid の「上」に移動するか「下」に移動するかを判定
            # (event.y が target_iid の bounding box の中央より上か下か)
            _, y, _, h = self.tree.bbox(target_iid)
            if event.y < y + h / 2:
                self.tree.move(self._dragged_item_dnd, "", target_idx)
            else:
                self.tree.move(self._dragged_item_dnd, "", target_idx + 1)


    def _on_row_release_for_dnd(self, event):
        if self._dragged_item_dnd:
            self.tree.config(cursor="")
            self._dragged_item_dnd = None
            # D&D完了後、files_dataの順序をTreeviewに合わせる
            self._reorder_files_data_from_treeview()
            self.log_message("ファイルリストの順序を変更しました。", "debug")


    def _reorder_files_data_from_treeview(self):
        """Treeviewの現在の行順序に合わせて self.files_data を並べ替える。"""
        current_tree_order_ids = list(self.tree.get_children())
        
        # files_data を _tree_id をキーにした辞書に一時変換
        data_map = {data["_tree_id"]: data for data in self.files_data if "_tree_id" in data}
        
        new_files_data_order = []
        for item_id in current_tree_order_ids:
            if item_id in data_map:
                new_files_data_order.append(data_map[item_id])
            else:
                # Treeviewにあってfiles_dataにない場合 (通常は発生しないはず)
                logger.warning(f"D&D後データ不整合: Tree item {item_id} が files_data に見つかりません。")

        # files_data にまだ含まれていないが、data_map には残っている要素を追加 (これも通常ないはず)
        # for item_id, data_item in data_map.items():
        #     if data_item not in new_files_data_order: # オブジェクト比較
        #         new_files_data_order.append(data_item)

        self.files_data = new_files_data_order
        self._update_tree_alternating_rows() # 行の背景色更新


    # --- Treeview行ドラッグによる並び替えはtkinterdnd2では直接サポートされていない。
    # 手動で実装する必要がある。
    def _undo_last_move(self): # Ctrl+Z などで呼び出す
        if not self.move_history:
            self.log_message("Undoする移動履歴がありません。", "info")
            return
        
        last_order_ids = self.move_history.pop()
        
        # Treeviewの順序を復元
        # (Treeview.move を使うが、一度全削除して再挿入の方が確実な場合もある)
        # ここでは、last_order_ids の順にアイテムを先頭からmoveしていく
        # ただし、Treeview.move は既存アイテムの相対位置を変えるので、
        # 正しく復元するには、一度detachして正しい順序でreattachするか、
        # files_data をこの順序に並べ替えて _redisplay_treeview_from_files_data を呼び出す。
        
        # files_data を last_order_ids の順に並べ替える
        data_map = {data["_tree_id"]: data for data in self.files_data if "_tree_id" in data}
        restored_files_data = []
        for item_id in last_order_ids:
            if item_id in data_map:
                restored_files_data.append(data_map[item_id])
            else:
                # Treeviewにあってfiles_dataにない場合 (通常は発生しないはず)
                logger.warning(f"D&D後データ不整合: Tree item {item_id} が files_data に見つかりません。")

        # files_data にまだ含まれていないが、data_map には残っている要素を追加 (これも通常ないはず)
        # for item_id, data_item in data_map.items():
        #     if data_item not in restored_files_data: # オブジェクト比較
        #         restored_files_data.append(data_item)

        self.files_data = restored_files_data
        self._redisplay_treeview_from_files_data() # これでTreeviewも復元される
        self.log_message("直前の行移動を元に戻しました。", "info")


    # --- 右クリックメニュー ---
    def _on_tree_right_click(self, event):
        """Treeviewでの右クリックイベント。コンテキストメニューを表示。"""
        iid = self.tree.identify_row(event.y)
        if not iid: # 行がない場所での右クリック
            # リスト全体に対するメニュー (例: 全て展開/折り畳み、表示列設定など)
            menu = tb.Menu(self, tearoff=False)
            menu.add_command(label="表示列のカスタマイズ...", command=self._customize_tree_columns)
            menu.add_separator()
            menu.add_command(label="設定をエクスポート...", command=self._export_app_config)
            menu.add_command(label="設定をインポート...", command=self._import_app_config)

            try: menu.tk_popup(event.x_root, event.y_root)
            finally: menu.grab_release()
            return

        # 行の上で右クリックされた場合
        # 複数選択されている場合と単一選択の場合でメニュー内容を変えてもよい
        if iid not in self.tree.selection(): # クリックされた行が選択されていなければ選択する
            self.tree.selection_set(iid)

        menu = tb.Menu(self, tearoff=False)
        menu.add_command(label="プレビュー", command=self._preview_selected_file)
        menu.add_separator()
        menu.add_command(label="主番号クリア", command=lambda i=iid: self._clear_tree_cell(i, "main_num"))
        menu.add_command(label="枝番クリア", command=lambda i=iid: self._clear_tree_cell(i, "branch_num"))
        menu.add_separator()
        menu.add_command(label="選択削除", command=self._remove_selected_files)
        # TODO: 他の便利な操作 (例: このファイルをFinder/Explorerで表示)
        
        try: menu.tk_popup(event.x_root, event.y_root)
        finally: menu.grab_release()

    def _clear_tree_cell(self, item_id: str, col_key: str):
        """指定されたアイテムの指定列の値をクリアする。"""
        if col_key in ["main_num", "branch_num"]:
            self.tree.set(item_id, col_key, "")
            # statusも更新
            main_val = self.tree.set(item_id, "main_num")
            if not main_val: # 主番号も空になったら未設定
                self.tree.set(item_id, "status", "未設定")
            else:
                self.tree.set(item_id, "status", "編集済")
            self._update_file_data_from_tree(item_id)
            self.log_message(f"アイテム {os.path.basename(self.tree.item(item_id, 'values')[0])} の {col_key} をクリアしました。", "debug")


    def _customize_tree_columns(self):
        """Treeviewの表示列をカスタマイズするダイアログ（未実装・アイデア）"""
        # TODO: チェックボックスリストで表示する列を選択できるようにする
        Messagebox.show_info("この機能は現在開発中です。", title="未実装", parent=self)
        # 実装する場合:
        # ConfigDialogのようなToplevelウィンドウを作成し、
        # self.tree_cols_def の各項目についてチェックボックスを生成。
        # 結果を self.app_config の "show_file_details_cols" に保存。
        # その後、self._rebuild_treeview_columns_and_data() を呼び出してTreeviewを再構築。


    # --- 設定のエクスポート・インポート ---
    def _export_app_config(self):
        filepath = filedialog.asksaveasfilename(
            title="設定をエクスポート",
            defaultextension=".json",
            filetypes=[("JSONファイル", "*.json")],
            initialfile="bangogo_config_export.json",
            parent=self
        )
        if filepath:
            try:
                # 現在のapp_config.dataをエクスポート
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.app_config.data, f, ensure_ascii=False, indent=2)
                self.log_message(f"設定をエクスポートしました: {filepath}", "success")
                Messagebox.show_info(f"設定をエクスポートしました:\n{filepath}", parent=self)
            except Exception as e:
                logger.error(f"設定エクスポート失敗: {e}")
                Messagebox.show_error(f"設定のエクスポートに失敗しました:\n{e}", parent=self)

    def _import_app_config(self):
        filepath = filedialog.askopenfilename(
            title="設定をインポート",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")],
            parent=self
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                
                # インポートしたデータで現在の設定を上書き
                # (バリデーションやデフォルト値とのマージが必要な場合がある)
                # ここでは単純に上書きし、AppConfigクラスのloadメソッドに似た処理を行う
                
                temp_config = self.app_config.defaults.copy()
                temp_config.update(imported_data)
                
                # 型チェックなど (AppConfig.load参照)
                if isinstance(temp_config.get("stamp_color_rgb"), list):
                    temp_config["stamp_color_rgb"] = tuple(temp_config["stamp_color_rgb"])
                
                self.app_config.data = temp_config
                self.app_config.save() # インポートした設定を保存
                
                self.log_message(f"設定をインポートしました: {filepath}", "success")
                Messagebox.show_info(
                    "設定をインポートしました。\n一部の設定はアプリケーションの再起動後に反映されます。",
                    parent=self
                )
                # UIを更新
                self._update_basic_panel_from_config()
                # 必要ならウィンドウテーマなども即時変更 (ttkbootstrapなら可能)
                if self.style.theme_use() != self.app_config.get("theme"):
                    try:
                        self.style.theme_use(self.app_config.get("theme"))
                    except tk.TclError:
                        logger.warning(f"インポートされたテーマ '{self.app_config.get('theme')}' の適用に失敗しました。")


            except Exception as e:
                logger.error(f"設定インポート失敗: {e}")
                Messagebox.show_error(f"設定のインポートに失敗しました:\n{e}", parent=self)


    # --- ログ ---
    def log_message(self, message: str, level: str = "info"): # level: "info", "warning", "error", "success", "debug"
        """ログウィンドウにメッセージを表示する。"""
        # loggerにも出力
        if level == "error": logger.error(message)
        elif level == "warning": logger.warning(message)
        elif level == "success": logger.info(message) # loggerにはinfoとして
        elif level == "debug": logger.debug(message)
        else: logger.info(message)

        # ログレベルがDEBUG未満の場合はDEBUGログをUIに表示しない
        current_log_level_str = self.app_config.get("log_level", "INFO").upper()
        if level == "debug" and current_log_level_str != "DEBUG":
            return

        # ttkbootstrap.ScrolledText の内部 Text ウィジェットの state を変更
        self.log_text.text.config(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        if level in ["error", "warning", "success", "info", "debug"]: # tagがあれば使う
             self.log_text.insert(tk.END, formatted_message, level)
        else:
             self.log_text.insert(tk.END, formatted_message)
            
        self.log_text.text.config(state="disabled") # ScrolledText内のTextウィジェットのstateを変更
        self.log_text.see(tk.END) # 自動スクロール

    # --- アプリケーション終了処理 ---
    def _on_closing(self):
        """ウィンドウが閉じられるときの処理。"""
        # 現在のウィンドウジオメトリを保存
        self.app_config.set("window_geometry", self.geometry())
        
        if self.app_config.get("auto_save_config", True):
            self.app_config.save() # 念のため最新の設定を保存
        
        if Messagebox.yesno("アプリケーションを終了しますか？", parent=self) == "Yes":
            self.destroy()
            logger.info(f"{APP_NAME} を終了しました。")
        #else:
            # キャンセルされた場合は何もしない (ウィンドウは閉じない)


# --- メイン処理 ---
def main():
    # 設定ファイルのパスを決定 (ユーザーのAppDataなどにするのがより堅牢)
    # ここではカレントディレクトリに保存
    config_path = os.path.join(os.getcwd(), CONFIG_FILE)
    
    app_config = AppConfig(config_path)

    # アプリケーション実行
    app = BangogoApp(app_config)
    app.mainloop()

if __name__ == "__main__":
    # 高DPI対応 (Windows) - ttkbootstrapがある程度対応してくれるはず
    # try:
    #     from ctypes import windll
    #     windll.shcore.SetProcessDpiAwareness(1) # DPI_AWARENESS_PER_MONITOR_AWARE
    # except Exception:
    #     pass # Windows以外または失敗時
    main()

# PyInstaller で実行ファイルを作成する場合のコマンド例:
# pyinstaller --noconsole --onefile --windowed \
#   --add-data "path/to/ipaexg.ttf:." \
#   --add-data "path/to/your_default_word_template.docx:." \
#   --icon="path/to/your_app_icon.ico" \
#   bangogo_plus_v2.py
#
# 注意: 
# - ipaexg.ttf やデフォルトのWordテンプレートは、スクリプトと同じディレクトリか、
#   --add-data で指定した相対パス先に配置されるようにする。
# - tkinterdnd2 を使う場合、Windowsでは tcl/tkライブラリの配置も必要になることがある。
#   (通常PyInstallerがうまく処理するが、環境による)
# - ttkbootstrap のテーマファイルもバンドルされる必要がある (通常PyInstallerが処理)