# app.py
import streamlit as st
import tempfile, os, asyncio, shutil, subprocess
# from yomitoku import DocumentAnalyzer  # コメントアウト
# from yomitoku.data.functions import load_pdf # コメントアウト

# Eドライブ上の一時ディレクトリを指定
E_DRIVE_TEMP_DIR = "E:\\streamlit_temp" 
# 指定した一時ディレクトリが存在するか確認し、なければ作成
if not os.path.exists(E_DRIVE_TEMP_DIR):
    try:
        os.makedirs(E_DRIVE_TEMP_DIR)
        print(f"一時ディレクトリを作成しました: {E_DRIVE_TEMP_DIR}")
    except Exception as e:
        print(f"一時ディレクトリの作成に失敗しました: {E_DRIVE_TEMP_DIR}, エラー: {e}")
        # エラーが発生した場合、デフォルトの動作にフォールバックするか、アプリを停止するか検討
        # ここでは簡単のため、エラーメッセージを表示して続行（デフォルトの場所に作成される）
        pass

# Web UI
st.title("PDF→Markdown 変換アプリ")
uploaded = st.file_uploader("PDF をアップロード", type="pdf")

if uploaded:
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=E_DRIVE_TEMP_DIR) as tmp_pdf:
        tmp_pdf.write(uploaded.read())
        pdf_path = tmp_pdf.name

    # 出力ディレクトリ設定
    out_dir = tempfile.mkdtemp(dir=E_DRIVE_TEMP_DIR)

    # 【方法 A】Python API で逐次解析
    # async def to_markdown_via_api(pdf_path, out_dir):
    #     analyzer = DocumentAnalyzer(configs={}, device="cuda", visualize=False) # configs={} を追加
    #     images = load_pdf(pdf_path)  # PDF→画像変換
    #     md_parts = []
    #     for i, img in enumerate(images): # Modified: Added enumerate for unique filenames
    #         results, *_ = await analyzer.run(img=img)

    #         # Workaround for TypeError: 'NoneType' object is not subscriptable in figure_to_md
    #         # This occurs if results.image is None but results.figures is not empty.
    #         if hasattr(results, 'image') and results.image is None and \\
    #            hasattr(results, 'figures') and results.figures:
    #             st.warning(f"ページ {i+1} の画像データが解析結果にありませんが、図が検出されました。このページの図はMarkdown出力でスキップされます。")
    #             results.figures = [] # Clear figures to prevent error

    #         # Added: Logic to handle to_markdown requiring out_path
    #         # Define a temporary path for this part's markdown output
    #         intermediate_md_part_path = os.path.join(out_dir, f"__ocr_intermediate_part_{i}.md")
            
    #         # Call results.to_markdown() with the required out_path argument
    #         results.to_markdown(out_path=intermediate_md_part_path) 
            
    #         # Read the content from the temporary file
    #         with open(intermediate_md_part_path, "r", encoding="utf-8") as temp_f:
    #             md_parts.append(temp_f.read())
            
    #         # Clean up the temporary intermediate file
    #         os.remove(intermediate_md_part_path)
            
    #     md_text = "\\\\n\\\\n".join(md_parts)
    #     # Using a consistent variable for the final output path
    #     final_md_output_path = os.path.join(out_dir, "output.md")
    #     with open(final_md_output_path, "w", encoding="utf-8") as f:
    #         f.write(md_text)
    #     return final_md_output_path # Modified: Return consistent path variable

    # 【方法 B】CLI をサブプロセス呼び出し
    def to_markdown_via_cli(pdf_path, out_dir):
        # yomitoku input.pdf -f md -o out_dir
        process = subprocess.run([
            "yomitoku", "-v", pdf_path, # -v を追加
            "-f", "md",
            "-o", out_dir,
        ], capture_output=True, text=True, check=False)  # Modified to capture output and not raise immediately

        if process.returncode != 0:
            st.error(f"yomitoku CLI エラー (終了コード: {process.returncode}):")
            if process.stdout:
                st.text_area("Standard Output:", process.stdout, height=150)
            if process.stderr:
                st.text_area("Standard Error:", process.stderr, height=150)
            raise subprocess.CalledProcessError(process.returncode, process.args, output=process.stdout, stderr=process.stderr)
        
        if process.returncode == 0: # Check for success before looking for files
            base_pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            st.info(f"yomitoku CLI正常終了。出力ディレクトリ: {out_dir}, 入力ベース名: {base_pdf_name}")

            # 出力ディレクトリ内のすべての .md ファイルをリストアップ
            try:
                all_files = os.listdir(out_dir)
            except Exception as e:
                st.error(f"出力ディレクトリ '{out_dir}' のリスト作成中にエラー: {e}")
                raise FileNotFoundError(f"出力ディレクトリ {out_dir} の内容を確認できませんでした。")

            # ページごとのMarkdownファイル (例: base_p1.md, base_p2.md) を収集
            page_md_files = []
            for f_name in all_files:
                # ページ番号を抽出するための正規表現パターンを改良
                # ファイル名が <base_pdf_name>_p<数字>.md の形式であることを期待
                import re
                match = re.match(rf"{re.escape(base_pdf_name)}_p(\\d+)\\.md", f_name)
                if match:
                    page_num = int(match.group(1))
                    page_md_files.append((page_num, os.path.join(out_dir, f_name)))
            
            if not page_md_files:
                # フォールバックとして、単純にディレクトリ内の全ての .md ファイルを名前順で結合することも検討できる
                # ここでは、期待する命名規則のファイルが見つからない場合はエラーとする
                st.warning(f"期待されるページ分割されたMarkdownファイル ({base_pdf_name}_p<N>.md) が見つかりませんでした。")
                # 代わりにディレクトリ内の最初の .md ファイルを探す (以前のフォールバックに近いが、複数ページには対応しない)
                md_files_in_dir = [f for f in all_files if f.endswith(".md") and os.path.isfile(os.path.join(out_dir, f))]
                if md_files_in_dir:
                    st.info(f"フォールバックとして、ディレクトリ内の最初のMarkdownファイル '{md_files_in_dir[0]}' を使用します。")
                    return os.path.join(out_dir, md_files_in_dir[0])
                else:
                    st.error(f"Markdown出力ファイルが出力ディレクトリ '{out_dir}' に見つかりませんでした。")
                    raise FileNotFoundError(f"出力ディレクトリ {out_dir} にMarkdownファイルが見つかりません。")

            # ページ番号でソート
            page_md_files.sort()

            # 各ページのMarkdownコンテンツを結合
            combined_md_content = []
            st.info(f"以下のページ分割されたMarkdownファイルを結合します: {[f[1] for f in page_md_files]}")
            for page_num, file_path in page_md_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        combined_md_content.append(f.read())
                    # 個別のページファイルは不要なら削除してもよい
                    # os.remove(file_path) 
                except Exception as e:
                    st.error(f"ファイル '{file_path}' の読み込み中にエラー: {e}")
                    # エラーが発生しても処理を続けるか、ここで中断するかを決定
                    continue 
            
            final_md_text = "\\n\\n---\\n\\n".join(combined_md_content) # ページ間に区切り線を追加

            # 結合されたMarkdownを新しいファイルに保存
            combined_output_filename = f"{base_pdf_name}_combined.md"
            final_output_path = os.path.join(out_dir, combined_output_filename)
            
            try:
                with open(final_output_path, "w", encoding="utf-8") as f:
                    f.write(final_md_text)
                st.success(f"結合されたMarkdownファイルを作成しました: {final_output_path}")
                return final_output_path
            except Exception as e:
                st.error(f"結合されたMarkdownファイル '{final_output_path}' の書き込み中にエラー: {e}")
                raise

            # 古いファイル検索ロジックは不要になるためコメントアウトまたは削除
            # # 試行1: <input_basename>_0.md (例: document_0.md)
            # expected_filename_1 = f"{base_pdf_name}_0.md"
            # potential_output_path_1 = os.path.join(out_dir, expected_filename_1)
            # st.info(f"出力ファイルを探しています (試行1 - input_basename_0.md 形式): {potential_output_path_1}")
            # if os.path.exists(potential_output_path_1):
            #     st.success(f"出力ファイル発見: {potential_output_path_1}")
            #     return potential_output_path_1

            # # 試行2: output_0.md (固定名での出力の場合)
            # expected_filename_2 = "output_0.md" # yomitokuが固定名で出力する場合
            # potential_output_path_2 = os.path.join(out_dir, expected_filename_2)
            # st.info(f"出力ファイルを探しています (試行2 - output_0.md 形式): {potential_output_path_2}")
            # if os.path.exists(potential_output_path_2):
            #     st.success(f"出力ファイル発見: {potential_output_path_2}")
            #     return potential_output_path_2
            
            # # 試行3: <input_basename>.md (例: document.md)
            # expected_filename_3 = f"{base_pdf_name}.md"
            # potential_output_path_3 = os.path.join(out_dir, expected_filename_3)
            # st.info(f"出力ファイルを探しています (試行3 - input_basename.md 形式): {potential_output_path_3}")
            # if os.path.exists(potential_output_path_3):
            #     st.success(f"出力ファイル発見: {potential_output_path_3}")
            #     return potential_output_path_3

            # # フォールバック: ディレクトリ内の最初の .md ファイルを探す
            # st.warning(f"期待された名前の出力ファイルが見つかりませんでした。ディレクトリ '{out_dir}' の内容を確認します...")
            # files_in_out_dir = []
            # try:
            #     files_in_out_dir = os.listdir(out_dir)
            #     st.info(f"出力ディレクトリ '{out_dir}' 内のファイル/ディレクトリ: {files_in_out_dir}")
            # except Exception as e:
            #     st.error(f"出力ディレクトリ '{out_dir}' のリスト作成中にエラー: {e}")
            #     raise FileNotFoundError(f"出力ディレクトリ {out_dir} の内容を確認できませんでした。")

            # md_files = [f for f in files_in_out_dir if f.endswith(".md") and os.path.isfile(os.path.join(out_dir, f))]
            # if md_files:
            #     found_md_file = md_files[0]
            #     st.success(f"フォールバックで見つかったMarkdownファイル: {found_md_file}")
            #     return os.path.join(out_dir, found_md_file)
            # else:
            #     st.error(f"Markdown出力ファイルが出力ディレクトリ '{out_dir}' に見つかりませんでした。")
            #     raise FileNotFoundError(f"出力ディレクトリ {out_dir} にMarkdownファイルが見つかりません。yomitoku CLIの実行は成功しましたが、出力ファイルがありませんでした。")
        
        # process.returncode != 0 の場合、エラーは既に上で処理され、CalledProcessError が発生しているはずです。
        # この部分は、もしエラーが上でキャッチされずにここまで来た場合のフォールバックですが、
        # 現在のコードでは到達しない想定です。
        # st.error("yomitoku CLIがエラーで終了したため、出力ファイル処理をスキップします。")
        return None # エラーケースではNoneを返すべきだが、実際には例外が発生している

    # 実行ボタン
    if st.button("変換開始"):
        try:
            # 非同期版を使う場合:
            # md_path = asyncio.run(to_markdown_via_api(pdf_path, out_dir))
            # または CLI 版:
            md_path = to_markdown_via_cli(pdf_path, out_dir)

            # ダウンロードリンクを表示
            with open(md_path, "rb") as f:
                st.download_button(
                    label="Markdown をダウンロード",
                    data=f,
                    file_name="converted.md",
                    mime="text/markdown"
                )
        finally:
            # 一時ファイル/ディレクトリを削除
            os.remove(pdf_path)
            shutil.rmtree(out_dir)
