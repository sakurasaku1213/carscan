import streamlit as st
import tempfile
import os

# G_DRIVE_TEMP_DIR = "G:\\streamlit_temp_test" # この行をコメントアウト
G_DRIVE_TEMP_DIR = None # この行のコメントを解除し、OSのデフォルト一時ディレクトリを使用

# Gドライブ用のディレクトリ作成処理は不要になるのでコメントアウトまたは削除
# if G_DRIVE_TEMP_DIR and not os.path.exists(G_DRIVE_TEMP_DIR):
#     try:
#         os.makedirs(G_DRIVE_TEMP_DIR)
#         print(f"テスト用一時ディレクトリを作成しました: {G_DRIVE_TEMP_DIR}")
#     except Exception as e:
#         print(f"テスト用一時ディレクトリの作成に失敗しました: {e}")
#         pass

st.title("ファイルアップロードテスト")
# 表示メッセージを修正
st.write(f"一時ファイル保存先ディレクトリ: {'OSのデフォルト一時ディレクトリ'}")

uploaded_file = st.file_uploader("テスト用PDFをアップロード", type="pdf")

if uploaded_file is not None:
    st.write(f"アップロードされたファイル: {uploaded_file.name}, サイズ: {uploaded_file.size} bytes")
    try:
        # dir=G_DRIVE_TEMP_DIR は dir=None と同じ意味になる (OSデフォルト)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=G_DRIVE_TEMP_DIR) as tmp_file:
            bytes_data = uploaded_file.getvalue()
            tmp_file.write(bytes_data)
            st.success(f"ファイル '{uploaded_file.name}' ({len(bytes_data)} bytes) を '{tmp_file.name}' に一時保存しました。")
            st.info(f"一時ファイルパス: {tmp_file.name}")

    except Exception as e:
        st.error(f"ファイルの一時保存中にエラーが発生しました: {e}")
        st.error(f"エラータイプ: {type(e)}")
        import traceback
        st.text(traceback.format_exc())
