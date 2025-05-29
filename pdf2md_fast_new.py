# pdf2md_fast.py (超高速化版) - CPU最適化・並列処理対応
# ==============================================================================
# 🚀 依存パッケージ:
#   pip install "pymupdf<1.25" streamlit yomi-toku
#   # CPU特化で最大パフォーマンス | 並列処理 | 高速OCR
# ==============================================================================
import os, sys, json, hashlib, shutil, subprocess, tempfile, time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp
import threading

import fitz                # PyMuPDF
import streamlit as st
import tkinter as tk
from tkinter import filedialog

# CPU最適化設定
os.environ["OMP_NUM_THREADS"] = str(mp.cpu_count())
os.environ["OPENBLAS_NUM_THREADS"] = str(mp.cpu_count())

# ページ設定
st.set_page_config(
    page_title="PDF→Markdown 超高速変換",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================= 高速化ユーティリティ =========================================

@st.cache_data
def sha256_cached(file_path_str: str) -> str:
    """キャッシュ化されたハッシュ計算"""
    fp = Path(file_path_str)
    h = hashlib.sha256()
    with fp.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256(fp: Path) -> str:
    """高速ハッシュ計算（キャッシュ対応）"""
    return sha256_cached(str(fp))

# ========================================= 高速テキスト抽出 =========================================

_MIN_CHARS = 30

def has_text_layer(page: fitz.Page, min_chars: int = _MIN_CHARS) -> bool:
    """テキスト層の存在チェック（高速化）"""
    try:
        text = page.get_text()
        return len(text.strip()) >= min_chars
    except:
        return False

def page_to_md_fast(page: fitz.Page) -> str:
    """高速Markdown変換（最適化済み）"""
    try:
        # 高速テキスト抽出
        text_dict = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
        if not text_dict or "blocks" not in text_dict:
            return ""
        
        lines = []
        for block in text_dict["blocks"]:
            if block.get("type") != 0:  # テキストブロックのみ
                continue
            
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                
                span = spans[0]
                text = span.get("text", "").rstrip()
                if text:
                    lines.append({
                        "size": span.get("size", 12),
                        "text": text
                    })
        
        if not lines:
            return ""
        
        # サイズ別見出し判定（高速化）
        sizes = sorted(set(l["size"] for l in lines), reverse=True)
        h1_size = sizes[0] if sizes else 12
        h2_size = sizes[1] if len(sizes) > 1 else h1_size
        
        # Markdown変換（最適化）
        md_lines = []
        bullet_prefixes = ("•", "・", "〇", "◯", "-", "―", "–", "*")
        
        for line in lines:
            txt = line["text"]
            if not txt:
                continue
                
            size = line["size"]
            if size >= h1_size:
                md_lines.append(f"# {txt}")
            elif size >= h2_size:
                md_lines.append(f"## {txt}")
            elif txt.lstrip().startswith(bullet_prefixes):
                clean_text = txt.lstrip('•・〇◯-–―* ')
                md_lines.append(f"- {clean_text}")
            else:
                md_lines.append(txt)
        
        return "\n".join(md_lines)
        
    except Exception as e:
        st.warning(f"ページのMarkdown変換でエラー: {e}")
        return ""

# 下位互換性のためのエイリアス
page_to_md = page_to_md_fast

# ========================================= 超高速OCR処理 =========================================

def export_pages_as_png_parallel(doc: fitz.Document, indices: List[int], 
                                dpi: int = 150, outdir: Path = None, 
                                max_workers: int = None) -> List[Path]:
    """並列画像エクスポート（DPI下げて高速化）"""
    if outdir is None:
        try:
            outdir = Path(tempfile.mkdtemp(prefix="pdf2md_png_fast_"))
        except Exception as e:
            st.error(f"PNGエクスポート用ディレクトリ作成失敗: {e}")
            return []
    else:
        outdir = Path(outdir)
    
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.error(f"PNGエクスポート先作成失敗: {e}")
        return []
    
    if max_workers is None:
        max_workers = min(mp.cpu_count(), len(indices))
    
    def export_single_page(page_idx: int) -> Optional[Path]:
        try:
            page = doc.load_page(page_idx)
            # 高速化: より小さなDPIと圧縮画像
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            png_path = outdir / f"page_{page_idx+1}.png"
            pix.save(png_path)
            pix = None  # メモリ解放
            return png_path
        except Exception as e:
            st.warning(f"ページ {page_idx+1} のPNGエクスポート失敗: {e}")
            return None
    
    png_paths = []
    # スレッドプールで並列処理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(export_single_page, idx): idx for idx in indices}
        for future in as_completed(future_to_idx):
            result = future.result()
            if result:
                png_paths.append(result)
    
    return sorted(png_paths)  # ページ順序を保持

def run_yomitoku_fast(png_paths: List[Path], device: str = "cpu") -> Dict[int, str]:
    """YomiToku高速実行（CPU最適化）"""
    if not png_paths:
        return {}
    
    md_by_page = {}
    
    try:
        with tempfile.TemporaryDirectory(prefix="yomitoku_fast_out_") as ocr_output_tmpdir_str, \
             tempfile.TemporaryDirectory(prefix="yomitoku_fast_in_") as input_img_tmpdir_str:
            
            ocr_output_tmpdir_path = Path(ocr_output_tmpdir_str)
            input_img_tmpdir_path = Path(input_img_tmpdir_str)
            
            # 高速ファイルコピー（並列）
            original_indices_map = {}
            
            def copy_png(png_path: Path) -> Optional[Tuple[Path, int]]:
                try:
                    original_page_index = int(png_path.stem.split('_')[1]) - 1
                    copied_path = input_img_tmpdir_path / png_path.name
                    shutil.copy2(png_path, copied_path)  # copy2は高速
                    return copied_path, original_page_index
                except Exception:
                    return None
            
            copied_paths = []
            with ThreadPoolExecutor(max_workers=mp.cpu_count()) as executor:
                results = list(executor.map(copy_png, png_paths))
                for result in results:
                    if result:
                        copied_path, original_idx = result
                        copied_paths.append(copied_path)
                        original_indices_map[copied_path.name] = original_idx
            
            if not copied_paths:
                return {}
            
            # YomiToku実行（CPU最適化設定）
            cmd = [
                "yomitoku", str(input_img_tmpdir_path),
                "-f", "md", "-o", str(ocr_output_tmpdir_path),
                "--device", device,
                "--combine", "--lite",
                "--batch-size", "4" if device == "cpu" else "8"  # CPU時はバッチサイズ小さく
            ]
            
            try:
                process = subprocess.run(
                    cmd, 
                    check=True, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8', 
                    errors='replace',
                    timeout=300  # 5分タイムアウト
                )
            except subprocess.TimeoutExpired:
                st.error("OCR処理がタイムアウトしました（5分）")
                return {}
            except subprocess.CalledProcessError as e:
                st.error(f"YomiToku実行失敗: {e.stderr}")
                return {}
            except FileNotFoundError:
                st.error("YomiTokuコマンドが見つかりません")
                return {}
            
            # 結果読み込み
            md_files = list(ocr_output_tmpdir_path.glob("*.md"))
            if not md_files:
                return {}
                
            md_text = md_files[0].read_text(encoding="utf-8")
            parts = [s.strip() for s in md_text.split("\n---\n")]
            
            # 結果マッピング
            sorted_names = sorted([p.name for p in copied_paths])
            for i, text_part in enumerate(parts):
                if i < len(sorted_names):
                    png_filename = sorted_names[i]
                    if png_filename in original_indices_map:
                        original_idx = original_indices_map[png_filename]
                        md_by_page[original_idx] = text_part
                        
    except Exception as e:
        st.error(f"OCR処理中エラー: {e}")
        return {}
    
    return md_by_page

# ========================================= 超高速並列PDF変換 =========================================

def pdf_to_markdown_ultra_fast(pdf_path: Path, dst_dir: Path, cache_dir: Path, 
                               device: str = "cpu") -> Tuple[str, str]:
    """超高速PDF変換（並列処理）"""
    start_time = time.time()
    
    try:
        # キャッシュチェック（高速）
        pdf_hash = sha256(pdf_path)
        cache_md = cache_dir / f"{pdf_hash}.md"
        out_md = dst_dir / f"{pdf_path.stem}.md"
        
        if cache_md.exists():
            try:
                shutil.copy2(cache_md, out_md)
                elapsed = time.time() - start_time
                return "cached", f"⚡ キャッシュ利用 ({elapsed:.2f}秒)"
            except Exception:
                pass
        
        # PDF読み込み
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        
        # 並列テキスト抽出
        def extract_page_text(page_idx: int) -> Tuple[int, str, bool]:
            page = doc.load_page(page_idx)
            has_text = has_text_layer(page)
            if has_text:
                md_text = page_to_md_fast(page)
                return page_idx, md_text, True
            else:
                return page_idx, "", False
        
        # CPU並列処理
        max_workers = min(mp.cpu_count(), total_pages, 8)  # 最大8並列
        md_pages = [""] * total_pages
        need_ocr_indices = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(extract_page_text, i): i for i in range(total_pages)}
            for future in as_completed(future_to_idx):
                page_idx, md_text, has_text = future.result()
                if has_text:
                    md_pages[page_idx] = md_text
                else:
                    need_ocr_indices.append(page_idx)
        
        # OCR処理（必要な場合のみ）
        if need_ocr_indices:
            st.info(f"🔬 OCR実行: {len(need_ocr_indices)}ページ")
            
            with tempfile.TemporaryDirectory(prefix="pdf2md_ultra_fast_") as png_temp_dir:
                png_temp_path = Path(png_temp_dir)
                
                # 並列画像エクスポート
                pngs = export_pages_as_png_parallel(
                    doc, need_ocr_indices, 
                    dpi=150,  # 高速化のため低DPI
                    outdir=png_temp_path,
                    max_workers=max_workers
                )
                
                if pngs:
                    # OCR実行
                    ocr_results = run_yomitoku_fast(pngs, device=device)
                    for page_idx, ocr_text in ocr_results.items():
                        if 0 <= page_idx < total_pages:
                            md_pages[page_idx] = ocr_text
        
        # 最終結果統合
        final_md = "\n\n---\n\n".join(filter(None, md_pages))
        
        # 並列ファイル書き出し
        def write_file(path: Path, content: str) -> bool:
            try:
                path.write_text(content, encoding="utf-8")
                return True
            except:
                return False
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            output_future = executor.submit(write_file, out_md, final_md)
            cache_future = executor.submit(write_file, cache_md, final_md)
            
            output_success = output_future.result()
            cache_future.result()  # キャッシュは失敗しても問題なし
        
        doc.close()
        elapsed = time.time() - start_time
        
        if output_success:
            return "success", f"✅ 変換完了 ({elapsed:.2f}秒)"
        else:
            return "failed", f"❌ 書き出し失敗 ({elapsed:.2f}秒)"
            
    except Exception as e:
        return "failed", f"❌ 変換失敗: {e}"

def process_pdfs_ultra_fast(pdf_paths: List[Path], dst_dir: Path, cache_dir: Path, 
                           device: str = "cpu", progress_callback=None) -> Dict[str, int]:
    """並列PDF一括変換"""
    total_files = len(pdf_paths)
    results = {"success": 0, "cached": 0, "failed": 0}
    
    # キャッシュディレクトリ作成
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except:
        pass
    
    # 並列処理（CPUコア数に基づく）
    max_workers = min(mp.cpu_count() // 2, 4, total_files)  # メモリ使用量を考慮
    
    def process_single_pdf(args):
        idx, pdf_path = args
        result, message = pdf_to_markdown_ultra_fast(pdf_path, dst_dir, cache_dir, device)
        return idx, pdf_path.name, result, message
    
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # タスク提出
        future_to_args = {
            executor.submit(process_single_pdf, (i, pdf_path)): (i, pdf_path) 
            for i, pdf_path in enumerate(pdf_paths)
        }
        
        # 結果収集
        for future in as_completed(future_to_args):
            idx, filename, result, message = future.result()
            results[result] += 1
            completed += 1
            
            # プログレス更新
            if progress_callback:
                progress_value = completed / total_files
                progress_callback(progress_value, f"{message} | {filename} ({completed}/{total_files})")
            
            # ログ出力
            if result == "success":
                st.success(message + f" | {filename}")
            elif result == "cached":
                st.info(message + f" | {filename}")
            else:
                st.error(message + f" | {filename}")
    
    return results

# ========================================= フォルダ選択 =========================================

def select_folder_dialog():
    """フォルダ選択ダイアログを開き、選択されたフォルダパスを返す"""
    root = tk.Tk()
    root.withdraw()  # Tkinterのメインウィンドウを表示しない
    root.attributes('-topmost', True)  # ダイアログを最前面に表示
    folder_selected = filedialog.askdirectory()
    root.destroy()
    return folder_selected

# ========================================= Streamlit GUI =========================================

# メインタイトル + ヒーロー画像風のヘッダー
st.markdown("""
<div style="background: linear-gradient(90deg, #FF6B35 0%, #F7931E 50%, #FFD23F 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
    <h1 style="color: white; text-align: center; margin: 0; font-size: 2.5rem;">
        ⚡ PDF→Markdown 超高速変換ツール
    </h1>
    <p style="color: #f0f0f0; text-align: center; margin: 1rem 0 0 0; font-size: 1.2rem;">
        並列処理 | CPU最適化 | キャッシュ機能 | 高速OCR対応
    </p>
</div>
""", unsafe_allow_html=True)

# CPU情報表示
cpu_count = mp.cpu_count()
st.info(f"🖥️ 検出されたCPUコア数: {cpu_count} | 最大並列処理数: {min(cpu_count, 8)}")

# ========= セッションステート初期化 =========
if 'input_folder_path' not in st.session_state:
    st.session_state.input_folder_path = ""
if 'dst_folder_path' not in st.session_state:
    st.session_state.dst_folder_path = str(Path.home() / "Documents" / "pdf2md_output")
if 'processing_mode' not in st.session_state:
    st.session_state.processing_mode = "upload"

# ========= サイドバー - 設定パネル =========
with st.sidebar:
    st.markdown("## ⚙️ 設定パネル")
    st.markdown("---")
    
    # 処理モード選択
    st.markdown("### 📂 入力方式選択")
    processing_mode = st.radio(
        "PDFファイルの入力方式を選択",
        ["ファイルアップロード", "フォルダ選択"],
        index=0 if st.session_state.processing_mode == "upload" else 1,
        help="個別ファイルをアップロードするか、フォルダから一括処理するかを選択"
    )
    st.session_state.processing_mode = "upload" if processing_mode == "ファイルアップロード" else "folder"
    
    st.markdown("---")
    
    # 入力ファイル/フォルダ設定
    if st.session_state.processing_mode == "upload":
        st.markdown("### 📄 ファイルアップロード")
        uploaded_files = st.file_uploader(
            "PDFファイルを選択",
            type=["pdf"],
            accept_multiple_files=True,
            help="複数のPDFファイルを同時にアップロード可能"
        )
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)}個のファイルが選択されました")
            for i, file in enumerate(uploaded_files[:5]):  # 最初の5ファイルのみ表示
                st.text(f"• {file.name}")
            if len(uploaded_files) > 5:
                st.text(f"... 他 {len(uploaded_files) - 5}ファイル")
    else:
        st.markdown("### 📁 入力フォルダ")
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.input_folder_path:
                st.text_input(
                    "選択中のフォルダ",
                    value=st.session_state.input_folder_path,
                    disabled=True,
                    key="input_display"
                )
            else:
                st.info("フォルダが選択されていません")
        
        with col2:
            if st.button("📁 選択", key="select_input_folder", help="フォルダを選択"):
                selected_folder = select_folder_dialog()
                if selected_folder:
                    st.session_state.input_folder_path = selected_folder
                    st.rerun()
        
        uploaded_files = None  # フォルダモードでは None に設定
    
    st.markdown("---")
    
    # 出力フォルダ設定
    st.markdown("### 💾 出力先フォルダ")
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.dst_folder_path:
            st.text_input(
                "選択中の出力先",
                value=st.session_state.dst_folder_path,
                disabled=True,
                key="output_display"
            )
        else:
            st.info("出力先が選択されていません")
    
    with col2:
        if st.button("📁 選択", key="select_output_folder", help="出力フォルダを選択"):
            selected_folder = select_folder_dialog()
            if selected_folder:
                st.session_state.dst_folder_path = selected_folder
                st.rerun()
    
    st.markdown("---")
    
    # OCR設定
    st.markdown("### 🔬 OCR設定")
    
    # CUDA検出
    cuda_available = shutil.which("nvidia-smi") is not None
    device_options = ["cpu"]
    if cuda_available:
        device_options.insert(0, "cuda")
    
    device = st.selectbox(
        "処理デバイス",
        device_options,
        index=0,
        help="CUDA対応GPUがある場合はcudaを選択（高速処理）"
    )
    
    # デバイス情報表示
    if device == "cuda":
        st.success("🚀 CUDA使用（超高速処理）")
    else:
        st.info(f"🖥️ CPU使用（{cpu_count}コア並列処理）")

# ========= メインエリア =========
# ステータス表示
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.processing_mode == "upload":
        input_status = f"📄 {len(uploaded_files)}ファイル" if uploaded_files else "❌ 未選択"
    else:
        if st.session_state.input_folder_path and os.path.isdir(st.session_state.input_folder_path):
            folder_path = Path(st.session_state.input_folder_path)
            pdf_count = len(list(folder_path.rglob("*.pdf")))
            input_status = f"📁 {pdf_count}個のPDF" if pdf_count > 0 else "⚠️ PDFなし"
        else:
            input_status = "❌ 未選択"
    
    st.metric("入力", input_status)

with col2:
    output_status = "✅ 設定済み" if st.session_state.dst_folder_path else "❌ 未選択"
    st.metric("出力先", output_status)

with col3:
    device_status = "🚀 CUDA" if device == "cuda" else f"🖥️ CPU({cpu_count})"
    st.metric("処理デバイス", device_status)

st.markdown("---")

# 変換開始ボタンと処理
st.markdown("### ⚡ 超高速変換処理")

# キャッシュディレクトリ設定
cache_dir = Path.home() / ".cache" / "pdf2md_ultra_fast"

# 変換開始の条件チェック
can_start = False
if st.session_state.processing_mode == "upload":
    can_start = uploaded_files and st.session_state.dst_folder_path
else:
    can_start = st.session_state.input_folder_path and st.session_state.dst_folder_path

if st.button("🚀 超高速変換開始", disabled=not can_start, type="primary", use_container_width=True):
    if not can_start:
        st.error("変換を開始するには、入力と出力先の両方を設定してください。")
        st.stop()
    
    # ========= 処理開始 =========
    pdf_paths_to_process = []
    
    # 1. 入力ファイルの決定
    if st.session_state.processing_mode == "upload":
        source_type = "upload"
        st.info(f"📄 アップロードされた {len(uploaded_files)}個のPDFファイルを処理します")
    else:
        if not os.path.isdir(st.session_state.input_folder_path):
            st.error(f"❌ 指定されたパス '{st.session_state.input_folder_path}' は有効なフォルダではありません")
            st.stop()
        
        folder_path = Path(st.session_state.input_folder_path)
        pdf_paths_to_process = sorted(list(folder_path.rglob("*.pdf")))
        
        if not pdf_paths_to_process:
            st.warning(f"⚠️ フォルダ '{st.session_state.input_folder_path}' (サブフォルダ含む) にPDFファイルが見つかりません")
            st.stop()
        
        source_type = "folder"
        st.info(f"📁 フォルダ内の {len(pdf_paths_to_process)}個のPDFファイルを処理します")
    
    # 2. 出力先フォルダの検証・作成
    dst_dir = Path(st.session_state.dst_folder_path)
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.error(f"❌ 出力先フォルダの作成に失敗: {e}")
        st.stop()
    
    # 処理情報表示
    st.markdown("#### 処理設定")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📂 **出力先**: {dst_dir}")
    with col2:
        st.info(f"🔬 **OCRデバイス**: {device.upper()}")
    
    # 4. PDF処理実行
    progress_container = st.container()
    
    with progress_container:
        if source_type == "upload":
            # アップロードファイルの処理
            with tempfile.TemporaryDirectory(prefix="pdf2md_ultra_upload_") as upload_tmpdir_str:
                upload_tmpdir_path = Path(upload_tmpdir_str)
                temp_pdf_paths = []
                
                # アップロードファイルを一時保存
                save_progress = st.progress(0, text="📤 ファイルを一時保存中...")
                for i, uploaded_file in enumerate(uploaded_files):
                    try:
                        temp_pdf_path = upload_tmpdir_path / uploaded_file.name
                        with open(temp_pdf_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        temp_pdf_paths.append(temp_pdf_path)
                        save_progress.progress((i + 1) / len(uploaded_files), 
                                             text=f"📤 保存中: {uploaded_file.name}")
                    except Exception as e:
                        st.error(f"❌ {uploaded_file.name} の一時保存に失敗: {e}")
                
                save_progress.empty()
                
                if not temp_pdf_paths:
                    st.error("❌ 処理対象のPDFファイルがありません（一時保存失敗）")
                    st.stop()
                
                pdf_paths_to_process = temp_pdf_paths
                
                # PDF変換処理
                main_progress = st.progress(0, text="🚀 超高速変換処理を開始中...")
                
                def progress_callback(value, text):
                    main_progress.progress(value, text=text)
                
                start_time = time.time()
                results = process_pdfs_ultra_fast(pdf_paths_to_process, dst_dir, cache_dir, device, progress_callback)
                total_time = time.time() - start_time
                
        else:
            # フォルダ内ファイルの処理
            main_progress = st.progress(0, text="🚀 超高速変換処理を開始中...")
            
            def progress_callback(value, text):
                main_progress.progress(value, text=text)
            
            start_time = time.time()
            results = process_pdfs_ultra_fast(pdf_paths_to_process, dst_dir, cache_dir, device, progress_callback)
            total_time = time.time() - start_time
    
    # 完了
    main_progress.progress(1.0, text="✅ すべての変換が完了しました！")
    
    # 最終結果表示
    st.markdown("### 📊 変換結果")
    total_files = sum(results.values())
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📄 総ファイル数", total_files)
    with col2:
        st.metric("✅ 成功", results["success"], delta=f"{results['success']/total_files*100:.1f}%")
    with col3:
        st.metric("⚡ キャッシュ利用", results["cached"], delta=f"{results['cached']/total_files*100:.1f}%")
    with col4:
        st.metric("❌ 失敗", results["failed"], delta=f"{results['failed']/total_files*100:.1f}%" if results["failed"] > 0 else None)
    with col5:
        st.metric("⏱️ 総処理時間", f"{total_time:.1f}秒", delta=f"{total_files/total_time:.1f}ファイル/秒")
    
    if results["failed"] == 0:
        st.balloons()
        st.success(f"🎉 すべてのファイルが正常に変換されました！")
    else:
        st.warning(f"⚠️ {results['failed']}個のファイルで変換に失敗しました")

# ========= フッター情報 =========
st.markdown("---")

# 使い方ガイド
with st.expander("📖 使い方ガイド", expanded=False):
    st.markdown(f"""
    ### 🚀 クイックスタート
    1. **📂 入力方式選択**: ファイルアップロードまたはフォルダ選択
    2. **💾 出力先設定**: 変換されたMarkdownファイルの保存先
    3. **🔬 OCR設定**: CUDA（超高速）またはCPU（{cpu_count}コア並列）を選択
    4. **⚡ 変換開始**: ボタンを押して超高速処理開始
    
    ### 💡 超高速化機能
    - **⚡ 並列処理**: 最大{min(cpu_count, 8)}並列でページ処理
    - **🎯 CPU最適化**: マルチスレッド・プロセス最適化
    - **📊 キャッシュ機能**: SHA256ハッシュベースの重複排除
    - **🔬 高速OCR**: バッチサイズ最適化・DPI調整
    - **🚀 メモリ効率**: リアルタイムメモリ解放
    
    ### ⚙️ システム要件
    - **Python 3.7+** + 必要パッケージ
    - **CPU**: マルチコア推奨（現在: {cpu_count}コア）
    - **CUDA GPU**: オプション（超高速処理用）
    - **YomiToku**: OCR処理用
    """)

# 技術情報
with st.expander("🔧 技術情報", expanded=False):
    st.markdown(f"""
    ### 📦 使用技術
    - **PyMuPDF**: PDF読み込み・高速テキスト抽出
    - **YomiToku**: 高精度OCRエンジン（バッチ最適化）
    - **Streamlit**: モダンなWebUI
    - **ThreadPoolExecutor**: CPU並列処理
    - **Tkinter**: ネイティブフォルダ選択
    
    ### 📈 パフォーマンス最適化
    - **並列処理**: 最大{min(cpu_count, 8)}スレッド同時実行
    - **メモリ効率**: ページ単位での即座メモリ解放
    - **キャッシュ機能**: ハッシュベースの高速重複検出
    - **OCR最適化**: DPI150・バッチサイズ調整
    - **ファイルI/O**: copy2による高速ファイル操作
    
    ### 🎯 対応形式
    - **入力**: PDF (テキスト付き・スキャン画像両対応)
    - **出力**: Markdown (.md)
    - **画像**: 中間PNG生成 (DPI 150, 高速化)
    - **エンコーディング**: UTF-8
    """)

st.markdown(f"""
<div style="text-align: center; color: #666; margin-top: 2rem;">
    <small>PDF→Markdown超高速変換ツール v3.0 | {cpu_count}コア並列処理対応 | Built with ⚡ and ❤️</small>
</div>
""", unsafe_allow_html=True)
