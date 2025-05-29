# pdf2md_fast.py (Streamlit GUI版) - 超高速化CPU特化
# ==============================================================================
# 🚀 依存パッケージ:
#   pip install "pymupdf<1.25" streamlit yomi-toku concurrent-futures threadpoolctl
#   # CPU特化で最大パフォーマンス | 並列処理 | 高速OCR
# ==============================================================================
import os, sys, json, hashlib, shutil, subprocess, tempfile, time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial
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
            
            def copy_png(png_path: Path) -> Optional[Path]:
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
                process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            except subprocess.CalledProcessError as e:
                st.error(f"YomiTokuの実行に失敗しました。コマンド: {' '.join(cmd)}")
                st.error(f"エラー出力:\n{e.stderr}")
                return {}
            except FileNotFoundError:
                st.error("YomiTokuコマンドが見つかりません。インストールされているか、PATHが通っているか確認してください。")
                return {}

            md_files = list(ocr_output_tmpdir_path.glob("*.md"))
            if not md_files:
                st.warning("YomiTokuによるOCR結果のMarkdownファイルが見つかりませんでした。")
                return {}
                
            md_text = md_files[0].read_text(encoding="utf-8")
            # YomiToku combine 出力はページ区切りに '---' を使う
            parts = [s.strip() for s in md_text.split("\\n---\\n")] # Adjusted split pattern
            
            # Sort the copied PNG names to match the order of 'parts' from YomiToku's combined output
            sorted_copied_png_names = sorted([p.name for p in copied_png_paths_for_yomitoku])

            if len(parts) != len(sorted_copied_png_names):
                st.warning(f"OCR結果のパーツ数({len(parts)})と画像数({len(sorted_copied_png_names)})が一致しません。処理結果が不正確になる可能性があります。")
                # Attempt to process what we can, or return {}
            
            for i, text_part in enumerate(parts):
                if i < len(sorted_copied_png_names):
                    png_filename = sorted_copied_png_names[i]
                    if png_filename in original_indices_map:
                        original_idx = original_indices_map[png_filename]
                        md_by_page[original_idx] = text_part
                    else:
                        st.warning(f"OCR結果のファイル名 {png_filename} に対応する元のページインデックスが見つかりません。")
                else:
                    # More parts than images, something is wrong
                    st.warning(f"OCR結果のパーツが画像数より多いです。パーツ {i+1} は無視されます。")
                    break 
    except Exception as e:
        st.error(f"OCR処理中（一時ディレクトリ管理など）に予期せぬエラー: {e}")
        return {} # Return empty if any critical error in temp dir handling
    return md_by_page

# --------- 3. 単一 PDF 変換 (エラー処理と一時ディレクトリ管理を強化) --------
def pdf_to_markdown(pdf_path: Path,
                    dst_dir: Path,
                    cache_dir: Path,
                    device: str = "cuda",
                    progress_bar=None,
                    file_idx=0,
                    total_files=1
                    ) -> None:
    if progress_bar:
        progress_text = f"処理中: {pdf_path.name} ({file_idx+1}/{total_files})"
        try:
            progress_value = (file_idx / total_files) if total_files > 0 else 0
            progress_bar.progress(progress_value, text=progress_text)
        except Exception as e:
            st.warning(f"プログレスバーの更新に失敗: {e}")


    pdf_hash = sha256(pdf_path)
    cache_md = cache_dir / f"{pdf_hash}.md"
    out_md  = dst_dir / f"{pdf_path.stem}.md"

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.warning(f"キャッシュディレクトリの作成/確認に失敗 ({cache_dir}): {e}")
        # Continue without cache if it fails

    if cache_md.exists():
        try:
            shutil.copy(cache_md, out_md)
            st.info(f"キャッシュを利用しました: {pdf_path.name} -> {out_md.name}")
            if progress_bar:
                 new_progress = ((file_idx + 1) / total_files) if total_files > 0 else 1
                 progress_bar.progress(new_progress, text=f"完了 (キャッシュ): {pdf_path.name} ({file_idx+1}/{total_files})")
            return
        except Exception as e:
            st.warning(f"キャッシュファイルのコピーに失敗 ({cache_md} -> {out_md}): {e}。通常変換を試みます。")

    doc = None
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        st.error(f"PDFファイルを開けませんでした: {pdf_path.name} - {e}")
        if progress_bar:
            new_progress = ((file_idx + 1) / total_files) if total_files > 0 else 1
            progress_bar.progress(new_progress, text=f"エラー: {pdf_path.name} ({file_idx+1}/{total_files})")
        return

    md_pages = [page_to_md(p) for p in doc] # Initial conversion from text layer
    need_ocr_pages_indices = [i for i,p in enumerate(doc) if not has_text_layer(p)]

    if need_ocr_pages_indices:
        st.write(f"{pdf_path.name}: {len(need_ocr_pages_indices)} ページでOCRを実行します...")
        png_export_temp_dir = None # Initialize
        try:
            png_export_temp_dir = Path(tempfile.mkdtemp(prefix="pdf2md_gui_png_export_"))
            pngs  = export_pages_as_png(doc, need_ocr_pages_indices, dpi=220, outdir=png_export_temp_dir)
            if pngs: # If any PNGs were successfully exported
                 ocr_md_parts = run_yomitoku(pngs, device=device)
                 for idx_in_doc, md_text_part in ocr_md_parts.items():
                     if 0 <= idx_in_doc < len(md_pages): # Check index bounds
                         md_pages[idx_in_doc] = md_text_part # Overwrite with OCR text
                     else:
                         st.warning(f"OCR結果のインデックス {idx_in_doc} がページ範囲外です ({pdf_path.name})。")
            else:
                st.warning(f"{pdf_path.name}: OCR対象ページの画像エクスポートに失敗、または対象画像がありませんでした。")
        except Exception as e:
            st.error(f"OCR処理中にエラーが発生 ({pdf_path.name}): {e}")
        finally:
            if png_export_temp_dir and png_export_temp_dir.exists():
                try:
                    shutil.rmtree(png_export_temp_dir)
                except Exception as e:
                    st.warning(f"PNGエクスポート用一時ディレクトリの削除に失敗 ({png_export_temp_dir}): {e}")
            
    final_md = "\\n\\n---\\n\\n".join(md_pages) # Page separator for final markdown
    try:
        out_md.write_text(final_md, encoding="utf-8")
        try:
            # Attempt to save to cache even if main write succeeds
            cache_md.write_text(final_md, encoding="utf-8")
        except Exception as e:
            st.warning(f"Markdownのキャッシュ保存に失敗 ({cache_md}): {e}")
        st.success(f"変換完了: {pdf_path.name} -> {out_md.name}")
    except Exception as e:
        st.error(f"Markdownファイルの書き出しに失敗 ({out_md}): {e}")
        if progress_bar:
            new_progress = ((file_idx + 1) / total_files) if total_files > 0 else 1
            progress_bar.progress(new_progress, text=f"エラー(書き出し失敗): {pdf_path.name} ({file_idx+1}/{total_files})")
        # Ensure doc is closed even if write fails, if it was opened
        if doc:
            doc.close()
        return

    if progress_bar:
        new_progress = ((file_idx + 1) / total_files) if total_files > 0 else 1
        progress_bar.progress(new_progress, text=f"完了: {pdf_path.name} ({file_idx+1}/{total_files})")
    
    if doc: # Close the document
        doc.close()

# --------- 4. Streamlit GUI -------------------------------------------------

def select_folder_dialog():
    """フォルダ選択ダイアログを開き、選択されたフォルダパスを返す"""
    root = tk.Tk()
    root.withdraw()  # Tkinterのメインウィンドウを表示しない
    root.attributes('-topmost', True)  # ダイアログを最前面に表示
    folder_selected = filedialog.askdirectory()
    root.destroy()
    return folder_selected

st.set_page_config(page_title="PDF to Markdown Converter", layout="wide")
st.title("📄 PDF to Markdown 一括変換ツール")

st.sidebar.header("設定")
uploaded_files = st.sidebar.file_uploader("PDFファイルを選択 (複数可)", type="pdf", accept_multiple_files=True)

st.sidebar.markdown("---")
st.sidebar.subheader("またはフォルダを指定")

# セッションステートでフォルダパスを管理
if 'folder_path_for_text_input' not in st.session_state:
    st.session_state.folder_path_for_text_input = ""

if st.sidebar.button("フォルダを選択してパスを入力", key="select_folder_button"):
    selected_path = select_folder_dialog()
    if selected_path:
        st.session_state.folder_path_for_text_input = selected_path
    # ボタンが押されたら一度スクリプトを再実行してテキスト入力に反映させる
    st.rerun()


folder_path_str = st.sidebar.text_input(
    "PDFが含まれるフォルダのパスを入力",
    value=st.session_state.folder_path_for_text_input, # セッションステートから値を取得
    help="上のボタンで選択するか、ここに直接パスを入力または貼り付けしてください。例: D:\\\\scanned_documents (サブフォルダも検索します)"
)

# --- 出力先フォルダ選択 ---
st.sidebar.markdown("---") # 区切り線
st.sidebar.subheader("出力先フォルダ")

if 'dst_folder_path' not in st.session_state:
    st.session_state.dst_folder_path = str(Path.home() / "Documents" / "pdf2md_output") # 初期値を設定

if st.sidebar.button("出力先フォルダを選択", key="select_dst_folder_button"):
    selected_dst_path = select_folder_dialog()
    if selected_dst_path:
        st.session_state.dst_folder_path = selected_dst_path
    st.rerun()

# 選択された出力先フォルダパスを表示 (編集不可)
st.sidebar.caption(f"現在の出力先: {st.session_state.dst_folder_path}")


device_options = ["cpu"]
if shutil.which("nvidia-smi"): # Check if nvidia-smi (CUDA utility) is available
    device_options.insert(0, "cuda") # Add cuda as first option if available
device_default_index = 0 # Default to first option (cuda if available, else cpu)

device = st.sidebar.selectbox("OCRデバイス", device_options, index=device_default_index) 

cache_dir = Path(".mdcache_gui") # GUI-specific cache directory

if st.sidebar.button("変換開始", type="primary", key="start_conversion_button"):
    pdf_paths_to_process = []
    source_type = None

    # folder_path_str に st.session_state の最新値を代入し直す (ボタン経由の場合を考慮)
    current_folder_path_from_input = folder_path_str

    # 1. Determine the source of PDF files
    if current_folder_path_from_input: # テキスト入力フィールドの値を使用
        # folder_path = Path(folder_path_str) # Keep for rglob, but check with os.path.isdir
        if os.path.isdir(current_folder_path_from_input): # Use os.path.isdir for initial validation
            folder_path = Path(current_folder_path_from_input) # Convert to Path after validation for rglob
            # Use rglob for recursive search and sort the results
            pdf_paths_to_process = sorted(list(folder_path.rglob("*.pdf")))
            if not pdf_paths_to_process:
                st.warning(f"指定フォルダ '{current_folder_path_from_input}' (サブフォルダ含む) にPDFファイルが見つかりません。")
                st.stop() # Use st.stop() to halt execution cleanly
            source_type = "folder"
            st.info(f"フォルダ '{current_folder_path_from_input}' 内のPDFを処理します ({len(pdf_paths_to_process)}件)。")
        else:
            st.error(f"指定されたパス '{current_folder_path_from_input}' は有効なフォルダではありません。")
            st.stop()
    elif uploaded_files:
        source_type = "upload"
        st.info(f"アップロードされた {len(uploaded_files)}個のPDFファイルを処理します。")
    else:
        st.sidebar.warning("PDFファイルを選択するか、フォルダパスを指定してください。")
        st.stop()

    # 2. Validate destination directory
    dst_dir_str = st.session_state.dst_folder_path # セッションステートから取得
    if not dst_dir_str:
        st.sidebar.error("出力先フォルダが選択されていません。") # エラーメッセージに変更
        st.stop()
    dst_dir = Path(dst_dir_str)
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.error(f"出力先フォルダの作成に失敗: {dst_dir} - {e}")
        st.stop()

    # 3. Setup cache
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.warning(f"キャッシュフォルダの作成に失敗 ({cache_dir}): {e}")
    
    st.info(f"出力先フォルダ: {dst_dir}")
    st.info(f"OCRデバイス: {device}")

    # 4. Process PDFs
    progress_bar_area = st.empty() # Placeholder for the progress bar

    if source_type == "upload":
        # Use a context manager for the temporary directory for uploads
        with tempfile.TemporaryDirectory(prefix="pdf2md_gui_upload_") as upload_tmpdir_str:
            upload_tmpdir_path = Path(upload_tmpdir_str)
            temp_pdf_paths_from_upload = [] # Store paths of successfully saved temp files
            for uploaded_file_data in uploaded_files:
                try:
                    temp_pdf_path = upload_tmpdir_path / uploaded_file_data.name
                    with open(temp_pdf_path, "wb") as f:
                        f.write(uploaded_file_data.getbuffer())
                    temp_pdf_paths_from_upload.append(temp_pdf_path)
                except Exception as e:
                    st.error(f"アップロードファイル {uploaded_file_data.name} の一時保存失敗: {e}")
            
            if not temp_pdf_paths_from_upload: # If no files were successfully saved
                st.error("処理対象のPDFファイルがありません（一時保存失敗）。")
                progress_bar_area.empty() # Clear progress bar area
                st.stop()
            
            pdf_paths_to_process = temp_pdf_paths_from_upload # Update the list to process    # This block will now execute for both 'folder' and 'upload' (after uploads are prepared)
    if pdf_paths_to_process: # Ensure there are files to process
        total_files = len(pdf_paths_to_process)
        progress_bar = progress_bar_area.progress(0, text=f"準備中... (0/{total_files})")
        
        # Progress callback function
        def progress_callback(current: int, total: int, file_name: str):
            progress = current / total if total > 0 else 1
            progress_bar.progress(progress, text=f"処理中: {file_name} ({current}/{total})")
        
        # Use the ultra-fast parallel processing function
        results = process_pdfs_ultra_fast(pdf_paths_to_process, dst_dir, cache_dir, device, progress_callback)
        
        progress_bar_area.empty() # Clear progress bar after completion
        st.balloons()
        st.success(f"すべてのファイルの変換が完了しました！ ({total_files}件処理)")
    else:
        # This case should ideally be caught earlier, but as a fallback:
        st.warning("処理対象のPDFファイルが見つかりませんでした。")


st.markdown("---")
st.markdown("""
### 使い方のヒント
1.  左のサイドバーから、個別のPDFファイルを選択するか、PDFが含まれるフォルダのパスを指定します。
    （フォルダパスを指定した場合、アップロードされたファイルは無視されます。）
2.  Markdownファイルの出力先フォルダを指定します（存在しない場合は作成されます）。
3.  OCRに使用するデバイスを選択します（CUDA対応GPUがあれば `cuda` を、なければ `cpu` を選択）。
4.  「変換開始」ボタンを押すと、処理が始まります。
""")

# To run this script: streamlit run your_script_name.py
# Ensure Typer related app.run() or similar is removed if this was converted from a Typer CLI.
# The main execution flow is now handled by Streamlit's rendering of the script from top to bottom.