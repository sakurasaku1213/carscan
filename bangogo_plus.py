#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 証拠番号スタンプツール – 改良版 (bangogo_plus.py)
----------------------------------------------------
* Treeview でファイル一覧 + インライン編集
* ドラッグ & ドロップ追加 (tkinterdnd2)
* 一括設定パネルでテンプレート指定
* プレビューでドラッグ配置 / 回転 / フォントサイズ変更
* 進捗バー + ログウィンドウ
* マルチページ貼付け (先頭 / 全ページ / 指定ページ)

必要ライブラリ:
    pip install PyMuPDF pillow tkinterdnd2 docxtpl python-docx==1.1.0 jinja2

Windows / macOS 共通で動作確認 (高 DPI 対応)
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from io import BytesIO
from typing import List, Optional

try:
    import tkinterdnd2
    from tkinterdnd2 import DND_FILES, TkinterDnD
    try:
        BaseTk = tkinterdnd2.TkinterDnD.Tk
    except (RuntimeError, tk.TclError):
        BaseTk = tk.Tk  # ドロップ不可フォールバック
except ImportError:
    # tkinterdnd2 が利用できない場合は警告を表示してフォールバック
    messagebox.showwarning(
        "警告", "tkinterdnd2 の読み込みに失敗しました。ドラッグ&ドロップ機能が無効化されます。"
    )
    BaseTk = tk.Tk  # フォールバック (ドラッグ&ドロップ不可)

from PIL import Image, ImageTk, ImageDraw, ImageFont
# docxtplはgenerate_evidence_doc内で動的インポートします (トップレベルには定義なし)
from docx import Document

# --- MuPDF (fitz) インポート時の騒音を握りつぶす ----------
import io, contextlib, sys

with contextlib.redirect_stdout(io.StringIO()), \
     contextlib.redirect_stderr(io.StringIO()):
    import fitz          # ← ここで Skia を読み込む
# -----------------------------------------------------------


# -------------------- ユーティリティ --------------------

BASE_FONT_PATH = (
    # pyinstallerバンドル時にはIPAexゴシックを使用
    os.path.join(sys._MEIPASS, "ipaexg.ttf") if hasattr(sys, "_MEIPASS")
    # Windows環境ではMeiryoフォントを使用（日本語対応）
    else r"C:\Windows\Fonts\Meiryo.ttc"
)

MARGIN = 20
DEFAULT_FONT_SIZE = 25
DEFAULT_ROTATION = 0
DEFAULT_OFFSET_X = 65
DEFAULT_OFFSET_Y = 12


def to_fullwidth(num: int | str) -> str:
    return str(num).translate(str.maketrans("0123456789", "０１２３４５６７８９"))


def convert_to_int(s: str) -> Optional[int]:
    try:
        s_conv = "".join(chr(ord(c) - 0xFEE0) if "０" <= c <= "９" else c for c in s)
        return int(s_conv)
    except Exception:
        return None


# ---- Word生成ヘルパー (テンプレート対応版) ----------------------------------------
def generate_evidence_doc(evidences, template_path, context, out_dir):
    """
    evidences     : list[dict]  (no / caption / copy / created / author / purpose / note)
    template_path : テンプレート docx のフルパス
    context       : bundle_title, first, last, court などヘッダ用
    """
    from docxtpl import DocxTemplate
    import os

    doc = DocxTemplate(template_path)
    doc.render({**context, "evidences": evidences})
    fn = context.get("doc_prefix", context.get("bundle_title", "証拠説明書")) + ".docx"
    out_path = os.path.join(out_dir, fn)
    doc.save(out_path)
    return out_path


# -------------------- PDF 操作 --------------------

def build_label_text(mode: str, prefix: str, main_num: int, branch: Optional[str]) -> str:
    if mode == "evidence":
        return (
            f"{prefix}第{to_fullwidth(main_num)}号証"
            + (f"の{to_fullwidth(branch)}" if branch else "")
        )
    else:
        return (
            f"添付資料{to_fullwidth(main_num)}" + (f"の{to_fullwidth(branch)}" if branch else "")
        )


def render_label_image(text: str, font_size: int, rotation: int) -> Image.Image:
    try:
        font = ImageFont.truetype(BASE_FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
    dummy = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    img = Image.new("RGBA", (w + 10, h + 10), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.text((5, 5), text, font=font, fill=(255, 0, 0))
    return img.rotate(rotation, expand=True)


def stamp_pdf(
    pdf_path: str,
    out_dir: str,
    text: str,
    pos_x: float,
    pos_y: float,
    font_size: int,
    rotation: int,
    target_pages: str = "first",  # "first" | "all" | comma‑separated list e.g. "1,3,5"
):
    img = render_label_image(text, font_size + 5, rotation)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    doc = fitz.open(pdf_path)

    pages_to_stamp: List[int]
    if target_pages == "all":
        pages_to_stamp = list(range(len(doc)))
    elif target_pages == "first":
        pages_to_stamp = [0]
    else:
        pages_to_stamp = [int(p) - 1 for p in target_pages.split(",") if p.strip().isdigit()]
    rect = fitz.Rect(pos_x, pos_y, pos_x + img.size[0], pos_y + img.size[1])
    for pno in pages_to_stamp:
        try:
            page = doc[pno]
            page.insert_image(rect, stream=buf.getvalue(), overlay=True)
        except Exception as e:
            print(f"[WARN] ページ {pno+1}: {e}")
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_name = f"{text}_{base_name}.pdf"
    out_path = os.path.join(out_dir, out_name)
    counter = 1
    while os.path.exists(out_path):
        out_path = os.path.join(out_dir, f"{text}_{base_name}({counter}).pdf")
        counter += 1
    doc.save(out_path, clean=True, deflate=True)
    doc.close()
    return out_path


# -------------------- プレビューウィンドウ --------------------
class PreviewDialog(tk.Toplevel):
    def __init__(
        self,
        master,
        pdf_path: str,
        text: str,
        font_size: int = DEFAULT_FONT_SIZE,
        offset_x: float = DEFAULT_OFFSET_X,
        offset_y: float = DEFAULT_OFFSET_Y,
        rotation: int = DEFAULT_ROTATION,
    ):
        super().__init__(master)
        self.title(f"プレビュー – {os.path.basename(pdf_path)}")
        self.geometry("620x720")
        self.resizable(False, False)

        self.pdf_path = pdf_path
        self.text = text
        self.rotation = rotation
        self.font_size = font_size

        self.canvas = tk.Canvas(self, width=600, height=600, bg="white")
        self.canvas.pack(side=tk.TOP)
        self.controls = tk.Frame(self)
        self.controls.pack(fill=tk.X, pady=4)

        # 画像準備
        doc = fitz.open(pdf_path)
        pix = doc[0].get_pixmap()
        self.bg_img_orig = Image.open(BytesIO(pix.tobytes("ppm")))
        scale = min(600 / self.bg_img_orig.width, 600 / self.bg_img_orig.height)
        self.scale = scale
        disp = self.bg_img_orig.resize(
            (int(self.bg_img_orig.width * scale), int(self.bg_img_orig.height * scale)),
            Image.Resampling.LANCZOS,
        )
        self.bg_photo = ImageTk.PhotoImage(disp)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")

        self.label_img = render_label_image(text, font_size, rotation)
        self.label_photo = ImageTk.PhotoImage(self.label_img)
        self.item = self.canvas.create_image(
            offset_x * scale,
            offset_y * scale,
            image=self.label_photo,
            anchor="nw",
        )
        self.drag_data = {"x": 0, "y": 0}
        self.canvas.tag_bind(self.item, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.item, "<B1-Motion>", self.on_drag)

        ttk.Label(self.controls, text="サイズ:").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.IntVar(value=font_size)
        ttk.Spinbox(self.controls, from_=10, to=200, textvariable=self.size_var, width=5, command=self.update_label).pack(side=tk.LEFT)
        ttk.Button(self.controls, text="回転", command=self.rotate).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.controls, text="確定", command=self.confirm).pack(side=tk.RIGHT, padx=10)

        self.result = None  # (fontsize, abs_x, abs_y, rotation)

    # ------- drag -------
    def on_press(self, event):
        self.drag_data["x"], self.drag_data["y"] = event.x, event.y

    def on_drag(self, event):
        dx, dy = event.x - self.drag_data["x"], event.y - self.drag_data["y"]
        self.canvas.move(self.item, dx, dy)
        self.drag_data["x"], self.drag_data["y"] = event.x, event.y

    # ------- update / rotate -------
    def update_label(self):
        self.font_size = int(self.size_var.get())
        self.label_img = render_label_image(self.text, self.font_size, self.rotation)
        self.label_photo = ImageTk.PhotoImage(self.label_img)
        self.canvas.itemconfigure(self.item, image=self.label_photo)

    def rotate(self):
        self.rotation = (self.rotation + 90) % 360
        self.update_label()

    # ------- confirm -------
    def confirm(self):
        x, y = self.canvas.coords(self.item)
        abs_x = x / self.scale
        abs_y = y / self.scale
        self.result = (self.font_size, abs_x, abs_y, self.rotation)
        self.destroy()


# -------------------- メインアプリ --------------------
class BangogoApp(BaseTk):
    def __init__(self):
        super().__init__()
        self.title("証拠番号スタンプツール 改良版")
        self.geometry("900x600")
        self.option_add("*Font", ("Meiryo", 12))
        self.files: List[dict] = []
        
        # 設定を読み込み
        self.config_dict = load_config()
        
        # ファイル行の全体管理用リスト
        self.all_items: List[str] = []
        # ソートの状態管理
        self.sort_states: dict = {}

        self._setup_ui()
        # 並べ替え前の順序を保存する履歴スタック
        self.move_history = []
        # Ctrl+Z で並べ替えを Undo
        self.bind("<Control-z>", lambda e: self.undo_move())
        
        # 終了時に設定を保存
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 設定の読み込み
        self.load_config()

    # ---------------- 基本設定パネルの同期 ----------------
    def update_basic_panel(self):
        """
        config_dict の値を基本設定パネルのウィジェット変数に反映します。
        起動時と設定ダイアログOK後に呼び出し。
        """
        cfg = self.config_dict
        # デフォルト値補正: 読み取り専用パネルの初期化を安定化
        # var_mode は日本語表示        self.var_mode.set(self._mode_map.get(cfg.get("mode", "evidence"), "証拠番号"))
        self.var_prefix.set(cfg.get("prefix", "甲"))
        self.var_startmain.set(cfg.get("start_main", 1))
        self.var_branch.set(cfg.get("branch_auto", False))
        
    def _basic_changed(self, *args):
        """基本設定パネル → config_dict への即時反映コールバック"""
        # 日本語から内部コードに変換して格納
        self.config_dict["mode"] = self._mode_map_inv.get(self.var_mode.get(), "evidence")
        self.config_dict["prefix"] = self.var_prefix.get().strip()
        # 開始主番号: 空文字 or 非数値はデフォルト1
        self.config_dict["start_main"] = safe_int_convert(str(self.var_startmain.get()), 1)
        # 枝番自動増加
        self.config_dict["branch_auto"] = bool(self.var_branch.get())



    # ---------------- UI ----------------
    def _setup_ui(self):
        
        # フィルタ用変数（未実装フィルタ UI の仮設定）
        self.filter_var = tk.StringVar(value="全て")
        # ---- 基本設定パネル (常時編集ウィジェット表示) ----
        self.basic_frame = ttk.LabelFrame(self, text="基本設定")
        self.basic_frame.pack(fill="x", padx=5, pady=(5, 0))

        # モードの日本語表示マッピング
        self._mode_map     = {"evidence": "証拠番号", "attachment": "添付資料"}
        self._mode_map_inv = {v: k for k, v in self._mode_map.items()}
        # 変数バインド
        # var_mode は表示用日本語
        self.var_mode      = tk.StringVar(value=self._mode_map.get(self.config_dict["mode"], "証拠番号"))
        # var_prefix は選択式接頭辞
        self.var_prefix    = tk.StringVar(value=self.config_dict["prefix"])
        self.var_startmain = tk.IntVar(  value=self.config_dict["start_main"])
        self.var_branch    = tk.BooleanVar(value=self.config_dict["branch_auto"])

        # 1行目：モード / 接頭辞
        ttk.Label(self.basic_frame, text="モード").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            self.basic_frame,
            textvariable=self.var_mode,
            values=tuple(self._mode_map.values()),
            state="readonly", width=10
        ).grid(row=0, column=1, sticky="w", padx=(4, 20))
        ttk.Label(self.basic_frame, text="接頭辞").grid(row=0, column=2, sticky="w")
        # 接頭辞は選択式
        ttk.Combobox(
            self.basic_frame,
            textvariable=self.var_prefix,
            values=("甲", "乙", "弁"),
            state="readonly",
            width=5
        ).grid(row=0, column=3, sticky="w", padx=(4, 20))

        # 2行目：開始主番号 / 枝番自動増加
        ttk.Label(self.basic_frame, text="開始主番号").grid(row=1, column=0, sticky="w")
        ttk.Spinbox(
            self.basic_frame, from_=1, to=9999,
            textvariable=self.var_startmain, width=6
        ).grid(row=1, column=1, sticky="w", padx=(4, 20))
        ttk.Checkbutton(
            self.basic_frame, text="枝番自動増加", variable=self.var_branch
        ).grid(row=1, column=2, columnspan=2, sticky="w")
        # ---- 基本設定パネル 編集ウィジェット設定後に1回だけ反映 ----
        self.update_basic_panel()

        # 変更を即反映
        for v in (self.var_mode, self.var_prefix, self.var_startmain, self.var_branch):
            v.trace_add("write", self._basic_changed)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # left – file list
        # --- _setup_ui 内（最初に出てくる Treeview 関連）----
        cols = ("file", "main", "branch", "status")
        headers = {"file":"ファイル", "main":"主番号", "branch":"枝番", "status":"ステータス"}
        widths  = [400, 80, 80, 80]

        self.tree = ttk.Treeview(main_frame, columns=cols, show="headings", selectmode="extended")
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=headers[col], command=lambda c=col: self.on_heading_click(c))
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.on_tree_edit)
        # ツリー行ドラッグ並び替え
        self.tree.bind('<ButtonPress-1>', self.on_row_press)
        self.tree.bind('<B1-Motion>', self.on_row_motion)
        self.tree.bind('<ButtonRelease-1>', self.on_row_release)
        # Ctrl+A で全行選択
        self.tree.bind("<Control-a>",
               lambda e: self.tree.selection_set(self.tree.get_children()),
               add="+")
        # 右クリックで枝番クリア用コンテキストメニュー
        self.tree.bind("<Button-3>", self._popup_menu, add="+")
        try:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self.on_drop)
        except AttributeError:
            pass  # DND not available        # right – controls
        ctrl = ttk.Frame(main_frame)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=4)
        # ---- add / remove ----
        ttk.Button(ctrl, text="ファイル追加", command=self.add_files).pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="選択削除", command=self.remove_selected).pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="全削除", command=self.clear_all_files).pack(fill=tk.X, pady=2)
        ttk.Separator(ctrl).pack(fill=tk.X, pady=5)
        
        # ---- 設定・操作 ----
        ttk.Button(ctrl, text="設定", command=self.open_config).pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="番号自動設定", command=self.auto_number).pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="番号リセット", command=self.reset_numbers).pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="プレビュー", command=self.preview_selected).pack(fill=tk.X, pady=2)
        ttk.Separator(ctrl).pack(fill=tk.X, pady=5)
        
        # ---- ソート・フィルタ ----
        ttk.Label(ctrl, text="ソート: 列ヘッダをクリック").pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="リセット順序", command=lambda: self.apply_filter(reset_sort=True)).pack(fill=tk.X, pady=2)
        
        # ---- ファイル操作 ----
        ttk.Separator(ctrl).pack(fill=tk.X, pady=5)
        ttk.Button(ctrl, text="設定をエクスポート", command=self.export_config).pack(fill=tk.X, pady=2)
        ttk.Button(ctrl, text="設定をインポート", command=self.import_config).pack(fill=tk.X, pady=2)
        
        # ---- 実行 ----
        ttk.Separator(ctrl).pack(fill=tk.X, pady=5)
        ttk.Button(ctrl, text="実行", command=self.execute).pack(fill=tk.X, pady=10)

        # progress + log
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill=tk.X, padx=10, pady=2)
        self.log = tk.Text(self, height=5, state="disabled")
        self.log.pack(fill=tk.X, padx=10, pady=2)

    # ---------------- drag & drop ----------------
    def on_drop(self, event):
        files = self.tk.splitlist(event.data)
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        self._append_files(pdfs)

    # ---------------- tree editing ----------------
    # --- on_tree_edit をそっくり置き換え ----
    def on_tree_edit(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not item_id or col_id == "#1":
            return
        col_idx = int(col_id[1:]) - 1
        col_key = ("file", "main", "branch", "status")[col_idx]
        old_val = self.tree.set(item_id, col_key)
        x, y, w, h = self.tree.bbox(item_id, col_id)
        if not (w and h):
            return
        v = tk.StringVar(value=old_val)
        # 主番号のみ Spinbox、その他（枝番・ステータス・ファイル）は Entry
        if col_key == "main":
            editor = tk.Spinbox(self, from_=0, to=9999, increment=1,
                                textvariable=v, justify="center", width=max(4, len(str(old_val))))
        else:
            editor = ttk.Entry(self, textvariable=v)
        editor.place(in_=self.tree, x=x, y=y, width=w, height=h)
        editor.focus_set()
        editor.bind("<Return>",  lambda e: self._finish_edit(editor, item_id, col_key, v))
        editor.bind("<FocusOut>",lambda e: self._finish_edit(editor, item_id, col_key, v))
        editor.bind("<Escape>",  lambda e: editor.destroy())

    # ----- 追加: 編集確定用ヘルパーメソッド ------------------------------------------
    def _finish_edit(self, widget, item_id, col_key, var):
        new = var.get().strip()

        if col_key == "main":             # 主番号：必ず整数
            if new == "":
                messagebox.showwarning("入力エラー", "主番号を空欄にはできません")
                widget.focus_set()
                return
            num = convert_to_int(new)
            if num is None:
                messagebox.showwarning("入力エラー", "主番号は整数で入力してください")
                widget.focus_set()
                return
            new = str(num)

        elif col_key == "branch":         # 枝番：空欄 OK／整数も OK
            if new == "":                 # 空欄ならそのままクリア
                self.tree.set(item_id, col_key, "")
                self.tree.set(item_id, "status", "編集済")
                widget.destroy()
                return
            num = convert_to_int(new)
            if num is None:
                messagebox.showwarning("入力エラー", "枝番は整数で入力するか空欄にしてください")
                widget.focus_set()
                return
            new = str(num)

        # 他列（status など）はそのまま
        self.tree.set(item_id, col_key, new)
        self.tree.set(item_id, "status", "編集済")
        widget.destroy()

    # ---------------- add/remove files ----------------    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        self._append_files(files)

    def _append_files(self, files: List[str]):
        """ファイルを追加する際の改良版処理"""
        valid_files = []
        invalid_files = []
        
        for f in files:
            if not os.path.exists(f):
                invalid_files.append(f"ファイルが見つかりません: {os.path.basename(f)}")
                continue
                
            if not f.lower().endswith('.pdf'):
                invalid_files.append(f"PDFファイルではありません: {os.path.basename(f)}")
                continue
                
            if not validate_pdf_file(f):
                invalid_files.append(f"無効なPDFファイル: {os.path.basename(f)}")
                continue
                
            # 重複チェック
            existing = [self.tree.item(item, "values")[0] for item in self.tree.get_children()]
            if f in existing:
                invalid_files.append(f"既に追加済み: {os.path.basename(f)}")
                continue
                
            valid_files.append(f)
        
        # 有効なファイルのみ追加
        for f in valid_files:
            file_info = get_file_info(f)
            # ツールチップ用にファイル情報を含める
            tooltip_info = f"ページ数: {file_info['pages']}, サイズ: {file_info['size']//1024}KB"
            self.tree.insert("", tk.END, values=(f, "", "", "未設定"), tags=(tooltip_info,))
            
        # 結果をログに表示
        if valid_files:
            self.log_msg(f"✔ {len(valid_files)}個のファイルを追加しました")
            
        if invalid_files:
            error_msg = "\n".join(invalid_files)
            messagebox.showwarning("ファイル追加エラー", f"以下のファイルは追加できませんでした:\n\n{error_msg}")
            self.log_msg(f"✖ {len(invalid_files)}個のファイルでエラーが発生")

    def remove_selected(self):
        for sel in self.tree.selection():
            self.tree.delete(sel)

    def clear_all_files(self):
        """全ファイルを削除"""
        if self.tree.get_children():
            result = messagebox.askyesno("確認", "すべてのファイルを削除しますか？")
            if result:
                for item in self.tree.get_children():
                    self.tree.delete(item)
                self.log_msg("全ファイルを削除しました")

    def reset_numbers(self):
        """全ての番号をリセット"""
        items = self.tree.get_children()
        if not items:
            return
            
        result = messagebox.askyesno("確認", "すべての番号をリセットしますか？")
        if result:
            for item in items:
                path, _, _, _ = self.tree.item(item, "values")
                self.tree.item(item, values=(path, "", "", "未設定"))
            self.log_msg("番号をリセットしました")

    # ---------------- config dialog ----------------
    def open_config(self):
        dlg = ConfigDialog(self, self.config_dict.copy())
        self.wait_window(dlg)
        if dlg.result:
            self.config_dict.update(dlg.result)
            self.update_basic_panel()
            # 設定をファイルに保存
            save_config(self.config_dict)

    # ---------------- preview ----------------
    def preview_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("警告", "行を選択してください")
            return
        item_id = sel[0]
        path, main, branch, _status = self.tree.item(item_id, "values")
        if main == "":
            messagebox.showwarning("警告", "主番号が未設定です")
            return
        text = build_label_text(self.config_dict["mode"], self.config_dict["prefix"], int(main), branch or None)
        dlg = PreviewDialog(
            self,
            path,
            text,
            self.config_dict["font_size"],
            self.config_dict["offset_x"],
            self.config_dict["offset_y"],
            self.config_dict["rotation"],
        )
        self.wait_window(dlg)
        if dlg.result:
            fsize, ox, oy, rot = dlg.result
            self.config_dict.update({
                "font_size": fsize,
                "offset_x": ox,
                "offset_y": oy,
                "rotation": rot,
            })
            self.log_msg("プレビュー結果を既定に反映しました")

    def execute(self):
        """改良版実行処理 - より詳細なエラーハンドリングと進捗表示"""
        dir_out = filedialog.askdirectory(title="出力フォルダを選択")
        if not dir_out:
            return
            
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("警告", "ファイルがありません")
            return
            
        # 事前検証
        todo = []
        validation_errors = []
        
        for it in items:
            path, main, branch, _status = self.tree.item(it, "values")
            
            # ファイル存在確認
            if not os.path.exists(path):
                validation_errors.append(f"ファイルが見つかりません: {os.path.basename(path)}")
                self.tree.set(it, "status", "ファイル不在")
                continue
                
            # 主番号確認
            if main == "":
                validation_errors.append(f"主番号未設定: {os.path.basename(path)}")
                self.tree.set(it, "status", "主番号不足")
                continue
                
            # PDFファイル有効性確認
            if not validate_pdf_file(path):
                validation_errors.append(f"無効なPDFファイル: {os.path.basename(path)}")
                self.tree.set(it, "status", "無効PDF")
                continue
                
            todo.append((it, path, int(main), branch or None))
        
        # 検証結果の表示
        if validation_errors:
            error_msg = "\n".join(validation_errors[:10])  # 最初の10個のエラーのみ表示
            if len(validation_errors) > 10:
                error_msg += f"\n... 他{len(validation_errors) - 10}個のエラー"
            messagebox.showerror("検証エラー", f"以下のエラーが発見されました:\n\n{error_msg}")
        
        if not todo:
            messagebox.showwarning("警告", "処理可能なファイルがありません")
            return
        
        # 処理確認
        result = messagebox.askyesno("実行確認", 
            f"{len(todo)}個のファイルを処理します。\n出力先: {dir_out}\n\n実行しますか？")
        if not result:
            return
            
        # 進捗初期化
        self.progress.configure(maximum=len(todo), value=0)
        success_count = 0
        error_count = 0
        
        self.log_msg(f"=== 処理開始: {len(todo)}個のファイル ===")
        
        for idx, (it, path, main_num, branch) in enumerate(todo, 1):
            try:
                # ステータス更新
                self.tree.set(it, "status", "処理中...")
                self.update_idletasks()
                
                text = build_label_text(
                    self.config_dict["mode"], 
                    self.config_dict["prefix"], 
                    main_num, 
                    branch
                )
                
                # バックアップ作成（オプション）
                if self.config_dict.get("create_backup", False):
                    backup_file(path)
                
                out = stamp_pdf(
                    path,
                    dir_out,
                    text,
                    self.config_dict["offset_x"],
                    self.config_dict["offset_y"],
                    self.config_dict["font_size"],
                    self.config_dict["rotation"],
                    self.config_dict["target_pages"],
                )
                
                self.tree.set(it, "status", "完了")
                self.log_msg(f"✔ ({idx}/{len(todo)}) {os.path.basename(path)} → {os.path.basename(out)}")
                success_count += 1
                
            except Exception as e:
                self.tree.set(it, "status", "失敗")
                self.log_msg(f"✖ ({idx}/{len(todo)}) {os.path.basename(path)}: {str(e)}")
                error_count += 1
                
            finally:
                self.progress.configure(value=idx)
                self.update_idletasks()
        
        # Word文書生成処理
        if self.config_dict.get("make_docx"):
            self.log_msg("=== Word文書生成開始 ===")
            try:
                evidence_rows = []
                for it in self.tree.get_children():
                    file, main, branch, status = self.tree.item(it, "values")
                    if not main or status != "完了":
                        continue
                    no = build_label_text("evidence", self.config_dict["prefix"], int(main), branch or None)
                    evidence_rows.append({
                        "no": no,
                        "caption": "",
                        "copy": "写し",
                        "created": "",
                        "author": "",
                        "purpose": "",
                        "note": ""
                    })
                
                if evidence_rows:
                    ctx = {
                        "bundle_title": self.config_dict.get("doc_prefix", "証拠説明書"),
                        "first": evidence_rows[0]["no"],
                        "last": evidence_rows[-1]["no"],
                        "court": ""
                    }
                    
                    tpl_path = self.config_dict["tpl_path"].strip().strip("'\"")
                    if not os.path.exists(tpl_path):
                        raise FileNotFoundError(f"テンプレートファイルが見つかりません: {tpl_path}")
                    
                    out = generate_evidence_doc(evidence_rows, tpl_path, ctx, dir_out)
                    self.log_msg(f"✔ Word生成完了: {os.path.basename(out)}")
                else:
                    self.log_msg("✖ 完了したファイルがないため、Word文書は生成されませんでした")
                    
            except Exception as e:
                self.log_msg(f"✖ Word生成失敗: {str(e)}")
          # 処理結果サマリー
        self.log_msg(f"=== 処理完了 ===")
        self.log_msg(f"成功: {success_count}個, 失敗: {error_count}個")
        
        if error_count == 0:
            messagebox.showinfo("完了", f"すべての処理が正常に完了しました。\n成功: {success_count}個")
        else:
            messagebox.showwarning("完了", 
                f"処理が完了しました。\n成功: {success_count}個\n失敗: {error_count}個\n\n詳細はログを確認してください。")

    # ---------------- utils ----------------
    def log_msg(self, msg: str, level: str = "INFO"):
        """改良版ログメッセージ - レベル付きログ"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # レベルに応じた色分け
        color_map = {
            "INFO": "black",
            "SUCCESS": "green", 
            "WARNING": "orange",
            "ERROR": "red"
        }
        
        formatted_msg = f"[{timestamp}] {level}: {msg}"
        
        self.log.configure(state="normal")
        self.log.insert(tk.END, formatted_msg + "\n")
        
        # 色を適用（最後の行に）
        if level in color_map:
            line_start = self.log.index("end-1c linestart")
            line_end = self.log.index("end-1c")
            self.log.tag_add(level, line_start, line_end)
            self.log.tag_config(level, foreground=color_map[level])
        
        self.log.configure(state="disabled")
        self.log.see(tk.END)
        
        # ログをファイルにも保存（オプション）
        if self.config_dict.get("save_log", False):
            self._save_log_to_file(formatted_msg)

    def _save_log_to_file(self, message: str):
        """ログをファイルに保存"""
        try:
            log_file = f"bangogo_log_{create_timestamp()[:8]}.txt"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception:
            pass  # ログ保存エラーは無視
    
    # ---------------- 自動番号設定 ----------------
    def auto_number(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("警告", "行を選択してください")
            return
        children = self.tree.get_children()
        sel_ordered = [it for it in children if it in sel]
        start = self.config_dict.get("start_main", 1)
        for idx, item in enumerate(sel_ordered, start):
            path, _, branch, _status = self.tree.item(item, "values")
            # 枝番自動増加
            if self.config_dict.get("branch_auto"):
                # start_main を基準に a1, a2, ... の形式で付与
                branch_chr = f"a{idx - start + 1}"
            else:
                branch_chr = branch or ""
            # 文字列化して格納
            self.tree.item(item, values=(path, str(idx), branch_chr, "編集済"))
        self.log_msg("番号を自動設定しました")

    # ---------------- ソート & フィルタ ----------------
    def on_heading_click(self, col):
        items = list(self.tree.get_children())
        data = []
        for it in items:
            val = self.tree.set(it, col)
            data.append((int(val) if col=="main" and val.isdigit() else val, it))
        asc = self.sort_states.get(col, True)
        data.sort(key=lambda x: x[0], reverse=not asc)
        for idx, (_, it) in enumerate(data):
            self.tree.move(it, '', idx)
        self.sort_states[col] = not asc

    def apply_filter(self, reset_sort=False):
        if reset_sort:
            # デフォルトの追加順に戻す
            return  # TODO: implement reset順序
        status_map = {'全て': None, '完了': True, '未処理': False}
        fl = self.filter_var.get()
        for it in self.tree.get_children():
            st = self.tree.set(it, 'status')
            show = (status_map[fl] is None) or (status_map[fl] and st=='完了') or (not status_map[fl] and st!='完了')
            if show:
                self.tree.reattach(it, '', 'end')
            else:
                self.tree.detach(it)
    
    def on_row_press(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return

        # ゴーストが既にあれば破棄
        if hasattr(self, '_ghost'):
            try:
                self._ghost.destroy()
            except Exception:
                pass
        # --- 修飾キー判定 -------------------------------------------------
        ctrl  = (event.state & 0x0004) != 0     # Windows: Ctrl
        shift = (event.state & 0x0001) != 0     # Windows: Shift
        if ctrl or shift:
            # Tk 組み込みに任せる（並べ替えは開始しない）
            self._dragged_item = None
            return

        # --- ここを修正 ---------------------------------------------------
        # 無修飾クリック → “常に” その行だけを選択にする
        #   ・複数選択が残っている場合もクリアして 1 行に
        #   ・既に 1 行選択されていても anchor を更新
        self.tree.selection_set(iid)

        # ---------------------------------------------------------------
        # 以下は従来どおり並べ替えドラッグの準備
        # 並べ替え前の順序を履歴に保存
        self.move_history.append(list(self.tree.get_children()))
        # 履歴は最大20ステップ
        if len(self.move_history) > 20:
            self.move_history.pop(0)
        self._dragged_item = iid
        self._drag_start_y = event.y
        self.tree.configure(cursor="fleur")

        # ゴースト表示（省略可、既存コードそのまま）
        import os
        text = os.path.basename(self.tree.item(iid, 'values')[0])
        self._ghost = tk.Toplevel(self)
        self._ghost.overrideredirect(True)
        ttk.Label(self._ghost, text=text, background='white').pack()
        self._ghost.attributes('-alpha', 0.5)
        self._ghost.geometry(f"+{event.x_root}+{event.y_root}")

    def on_row_motion(self, event):
        if not getattr(self, '_dragged_item', None):
            return
        # --- ここから追記: 3px 未満ならドラッグ処理をスキップ ----------
        if abs(event.y - self._drag_start_y) < 3:
            return
        # オートスクロール
        margin = 15
        if event.y < margin:
            self.tree.yview_scroll(-1, "units")
        elif event.y > self.tree.winfo_height() - margin:
            self.tree.yview_scroll(1, "units")
        target = self.tree.identify_row(event.y)
        if not target or target == self._dragged_item:
            return
        tx, ty, tw, th = self.tree.bbox(target)
        midline = ty + th // 2
        src_idx = self.tree.index(self._dragged_item)
        dest_idx = self.tree.index(target)
        # 半分を境に上か下かで移動
        if event.y < midline and src_idx != dest_idx:
            self.tree.move(self._dragged_item, '', dest_idx)
        elif event.y >= midline and src_idx != dest_idx + 1:
            self.tree.move(self._dragged_item, '', dest_idx + 1)
        # ghostウィンドウをマウス位置に追従させる
        if hasattr(self, '_ghost'):
            self._ghost.geometry(f"+{event.x_root}+{event.y_root}")

    def on_row_release(self, event):
        self.tree.configure(cursor="")        # カーソル戻す
        # ghostウィンドウを破棄
        if hasattr(self, '_ghost'):
            self._ghost.destroy()
            del self._ghost
        self._dragged_item = None

    def undo_move(self, event=None):
        """
        Ctrl+Z で呼び出される移動Undo。
        move_historyに保存した直前のアイテム順序を復元します。
        """
        if not self.move_history:
            return
        last_order = self.move_history.pop()
        for idx, iid in enumerate(last_order):
            try:
                self.tree.move(iid, '', idx)
            except Exception:
                pass
    # ---------------- 右クリックメニュー ----------------
    def _popup_menu(self, event):
        # 枝番セル上で右クリックすると、枝番をクリア
        iid = self.tree.identify_row(event.y)
        # 行クリックで単一選択に
        if iid:
            self.tree.selection_set(iid)
        else:
            return
        col_id = self.tree.identify_column(event.x)
        # 枝番列 (#3) 以外ではメニュー不要
        if col_id != '#3':
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label='枝番クリア', command=lambda: self._clear_branch(iid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _clear_branch(self, item_id):
        # 枝番をクリアしてステータスを編集済に
        self.tree.set(item_id, 'branch', '')
        self.tree.set(item_id, 'status', '編集済')

    # ---------------- 設定ダイアログ ----------------
class ConfigDialog(tk.Toplevel):
    def __init__(self, master, cfg: dict):
        super().__init__(master)
        self.title("設定")
        self.geometry("450x400")
        self.resizable(False, False)
        
        # Word生成設定
        self.make_docx_var = tk.BooleanVar(value=cfg.get("make_docx", False))
        self.tpl_path_var = tk.StringVar(value=cfg.get("tpl_path",""))
        self.doc_prefix_var = tk.StringVar(value=cfg.get("doc_prefix","証拠説明書"))
        
        # 新しい設定項目
        self.create_backup_var = tk.BooleanVar(value=cfg.get("create_backup", False))
        self.auto_save_config_var = tk.BooleanVar(value=cfg.get("auto_save_config", True))
        self.show_file_info_var = tk.BooleanVar(value=cfg.get("show_file_info", True))

        self.cfg = cfg
        self.result = None  # 結果格納用
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---- 基本 ----
        frame_base = ttk.Frame(nb)
        nb.add(frame_base, text="基本")
        row = 0
        ttk.Label(frame_base, text="モード:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.mode_var = tk.StringVar(value=cfg["mode"])
        ttk.Radiobutton(frame_base, text="証拠番号", variable=self.mode_var, value="evidence").grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(frame_base, text="添付資料", variable=self.mode_var, value="attachment").grid(row=row, column=2, sticky="w")
        row += 1
        ttk.Label(frame_base, text="接頭辞 (甲/乙/弁)").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.prefix_var = tk.StringVar(value=cfg["prefix"])
        ttk.Combobox(frame_base, textvariable=self.prefix_var, values=["甲", "乙", "弁"], width=5).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frame_base, text="開始主番号").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.start_var = tk.IntVar(value=cfg["start_main"])
        ttk.Entry(frame_base, textvariable=self.start_var, width=6).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frame_base, text="枝番自動増加").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.branch_auto_var = tk.BooleanVar(value=cfg["branch_auto"])
        ttk.Checkbutton(frame_base, variable=self.branch_auto_var).grid(row=row, column=1, sticky="w")

        # ---- 配置 ----
        frame_pos = ttk.Frame(nb)
        nb.add(frame_pos, text="配置")
        row = 0
        ttk.Label(frame_pos, text="フォントサイズ").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.font_size_var = tk.IntVar(value=cfg["font_size"])
        ttk.Entry(frame_pos, textvariable=self.font_size_var, width=6).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frame_pos, text="回転角 (°)").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.rot_var = tk.IntVar(value=cfg["rotation"])
        ttk.Combobox(frame_pos, textvariable=self.rot_var, values=[0, 90, 180, 270], width=5).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frame_pos, text="X オフセット (pt)").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.offx_var = tk.DoubleVar(value=cfg["offset_x"])
        ttk.Entry(frame_pos, textvariable=self.offx_var, width=8).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frame_pos, text="Y オフセット (pt)").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.offy_var = tk.DoubleVar(value=cfg["offset_y"])
        ttk.Entry(frame_pos, textvariable=self.offy_var, width=8).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frame_pos, text="対象ページ").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        self.pages_var = tk.StringVar(value=cfg["target_pages"])
        ttk.Combobox(frame_pos, textvariable=self.pages_var, values=["first", "all", "1,3,5"], width=10).grid(row=row, column=1, sticky="w")

        # ---- Wordタブ ----
        frame_word = ttk.Frame(nb)
        nb.add(frame_word, text="Word")
        row = 0
        ttk.Checkbutton(frame_word, text="スタンプ後に証拠説明書を生成", variable=self.make_docx_var).grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row+=1
        ttk.Label(frame_word, text="テンプレートパス").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame_word, textvariable=self.tpl_path_var, width=25).grid(row=row, column=1, sticky="w")
        ttk.Button(frame_word, text="参照", command=self.browse_template).grid(row=row, column=2, padx=5)
        row+=1
        ttk.Label(frame_word, text="出力名 prefix").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame_word, textvariable=self.doc_prefix_var, width=20).grid(row=row, column=1, sticky="w")

        # ---- オプションタブ ----
        frame_options = ttk.Frame(nb)
        nb.add(frame_options, text="オプション")
        row = 0
        ttk.Checkbutton(frame_options, text="処理前にファイルのバックアップを作成", 
                       variable=self.create_backup_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        row += 1
        ttk.Checkbutton(frame_options, text="設定変更時に自動保存", 
                       variable=self.auto_save_config_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        row += 1
        ttk.Checkbutton(frame_options, text="ファイル情報をツールチップで表示", 
                       variable=self.show_file_info_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # ---- buttons ----
        btnf = ttk.Frame(self)
        btnf.pack(fill=tk.X, pady=5)
        ttk.Button(btnf, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btnf, text="キャンセル", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(btnf, text="デフォルトに戻す", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)

    def browse_template(self):
        """テンプレートファイルを参照する"""
        filename = filedialog.askopenfilename(
            title="Wordテンプレートファイルを選択",
            filetypes=[("Word文書", "*.docx"), ("すべてのファイル", "*.*")]
        )
        if filename:
            self.tpl_path_var.set(filename)

    def reset_to_defaults(self):
        """設定をデフォルト値に戻す"""
        result = messagebox.askyesno("確認", "設定をデフォルト値に戻しますか？")
        if result:
            defaults = load_config()  # デフォルト設定を取得
            self.mode_var.set(defaults["mode"])
            self.prefix_var.set(defaults["prefix"])
            self.start_var.set(defaults["start_main"])
            self.branch_auto_var.set(defaults["branch_auto"])
            self.font_size_var.set(defaults["font_size"])
            self.rot_var.set(defaults["rotation"])
            self.offx_var.set(defaults["offset_x"])
            self.offy_var.set(defaults["offset_y"])
            self.pages_var.set(defaults["target_pages"])
            self.make_docx_var.set(defaults["make_docx"])
            self.tpl_path_var.set(defaults["tpl_path"])
            self.doc_prefix_var.set(defaults["doc_prefix"])
            self.create_backup_var.set(defaults.get("create_backup", False))
            self.auto_save_config_var.set(defaults.get("auto_save_config", True))
            self.show_file_info_var.set(defaults.get("show_file_info", True))

    def on_ok(self):
        self.result = {
            "mode": self.mode_var.get(),
            "prefix": self.prefix_var.get(),
            "start_main": self.start_var.get(),
            "branch_auto": self.branch_auto_var.get(),
            "font_size": self.font_size_var.get(),
            "rotation": self.rot_var.get(),
            "offset_x": self.offx_var.get(),
            "offset_y": self.offy_var.get(),
            "target_pages": self.pages_var.get(),
            # Word生成設定
            "make_docx": self.make_docx_var.get(),
            "tpl_path": self.tpl_path_var.get(),
            "doc_prefix": self.doc_prefix_var.get(),
            # 新しいオプション
            "create_backup": self.create_backup_var.get(),
            "auto_save_config": self.auto_save_config_var.get(),
            "show_file_info": self.show_file_info_var.get(),
        }
        self.destroy()


# -------------------- 設定の保存・読み込み --------------------
CONFIG_FILE = "bangogo_config.json"

def load_config() -> dict:
    """設定ファイルを読み込みます。ファイルが存在しない場合はデフォルト設定を返します."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
    
    # デフォルト設定
    return {
        "mode": "evidence",
        "prefix": "甲",
        "start_main": 1,
        "branch_auto": False,
        "font_size": DEFAULT_FONT_SIZE,
        "rotation": DEFAULT_ROTATION,
        "offset_x": DEFAULT_OFFSET_X,
        "offset_y": DEFAULT_OFFSET_Y,
        "target_pages": "first",
        "make_docx": False,
        "tpl_path": "",
        "doc_prefix": "証拠説明書",
    }

def save_config(config: dict) -> None:
    """設定をファイルに保存します."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"設定ファイル保存エラー: {e}")

def safe_int_convert(value: str, default: int = 1) -> int:
    """文字列を安全に整数に変換します."""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default

def validate_pdf_file(file_path: str) -> bool:
    """PDFファイルが有効かどうかチェックします."""
    if not os.path.exists(file_path):
        return False
    try:
        doc = fitz.open(file_path)
        valid = len(doc) > 0
        doc.close()
        return valid
    except Exception:
        return False

def backup_file(file_path: str) -> str:
    """ファイルのバックアップを作成します."""
    backup_path = f"{file_path}.backup"
    import shutil
    shutil.copy2(file_path, backup_path)
    return backup_path

def get_file_info(file_path: str) -> dict:
    """ファイルの詳細情報を取得します."""
    info = {
        "size": 0,
        "pages": 0,
        "created": "",
        "modified": ""
    }
    
    try:
        stat = os.stat(file_path)
        info["size"] = stat.st_size
        info["created"] = os.path.getctime(file_path)
        info["modified"] = os.path.getmtime(file_path)
        
        doc = fitz.open(file_path)
        info["pages"] = len(doc)
        doc.close()
    except Exception:
        pass
    
    return info

def save_config_to_file(config: dict, filename: str) -> None:
    """設定を指定されたファイルに保存します。"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"設定ファイル保存エラー: {e}")

def load_config_from_file(filename: str) -> dict:
    """指定されたファイルから設定を読み込みます。"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"設定ファイル読み込みエラー: {e}")

def create_timestamp() -> str:
    """現在時刻のタイムスタンプを生成"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def format_file_size(size_bytes: int) -> str:
    """ファイルサイズを読みやすい形式でフォーマット"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


# ---------------- main ----------------
if __name__ == "__main__":
    app = BangogoApp()
    app.mainloop()

# To create an executable, run the following command in the terminal:
# cd C:\Users\yoshida\Desktop\アプリ倉庫
# pyinstaller --noconsole --onefile --add-data "ipaexg.ttf;." bangogo_plus.py
