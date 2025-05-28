# filepath: e:\\minimal_upload_test.py
import streamlit as st
import tempfile
import os

st.title("最小限のファイルアップロードテスト (PDF)") # タイトル変更

uploaded_file = st.file_uploader("PDFファイル (.pdf) をアップロード", type="pdf") # type を "pdf" に変更

if uploaded_file is not None:
    try:
        # OSのデフォルト一時ディレクトリを使用
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file: # suffix も .pdf に
            bytes_data = uploaded_file.getvalue()
            tmp_file.write(bytes_data)
            st.success(f"ファイル '{uploaded_file.name}' を '{tmp_file.name}' に一時保存しました。")
            st.info(f"一時ファイルパス: {tmp_file.name}")
            
            # すぐに削除する場合は以下を有効化
            # os.remove(tmp_file.name)
            # st.info(f"一時ファイル '{tmp_file.name}' を削除しました。")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        import traceback
        st.text(traceback.format_exc())