import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import whisper
import threading # GUIのフリーズを防ぐためにWhisper処理を別スレッドで実行
import torch # GPUが利用可能かチェックするためなど
import gc # ガベージコレクションを追加

# --- グローバル変数（必要に応じて調整） ---
SELECTED_MODEL_NAME = "base" # デフォルトモデル
SELECTED_LANGUAGE = "ja"    # デフォルトは自動検出 -> 日本語固定
AUDIO_FILE_PATH = ""

# --- Whisper処理関数 (スレッドで実行) ---
def run_whisper_transcription(file_path, model_name, language, progress_var, result_text_widget, status_label, run_button):
    global SELECTED_MODEL_NAME # SELECTED_LANGUAGE は "ja" 固定なので global から削除
    try:
        status_label.config(text=f"モデル ({model_name}) をロード中...")
        progress_var.set(10) # プログレスバーを進める (適宜調整)

        # デバイスの選択 (GPUが利用可能ならGPUを、そうでなければCPUを自動選択)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}") # コンソールにデバイス情報を表示

        model = whisper.load_model(model_name, device=device)
        status_label.config(text="音声ファイルを処理中...")
        progress_var.set(30)

        options = {"language": "ja", "fp16": False} # language を "ja" に固定
        if device == "cuda":
            options["fp16"] = True # GPUなら半精度浮動小数点を利用して高速化を試みる

        result = model.transcribe(file_path, **options, verbose=True) # verbose=Trueでコンソールに進捗表示

        progress_var.set(90)
        result_text_widget.delete(1.0, tk.END) # 既存のテキストをクリア
        result_text_widget.insert(tk.END, result["text"])
        status_label.config(text="完了！")
        progress_var.set(100)

    except MemoryError as me:
        messagebox.showerror("メモリ エラー", f"文字起こし中にメモリが不足しました: {me}\\n\\n試せること:\\n- より小さなモデル (tiny, base など) を選択してください。\\n- 他のアプリケーションを閉じてメモリを解放してください。\\n- 可能であれば、より短い音声ファイルでお試しください。")
        status_label.config(text="エラー: メモリ不足")
    except FileNotFoundError:
        messagebox.showerror("エラー", f"音声ファイルが見つかりません: {file_path}")
        status_label.config(text="エラー: ファイル未選択")
    except Exception as e:
        messagebox.showerror("エラー", f"文字起こし中に予期せぬエラーが発生しました: {type(e).__name__}: {e}")
        status_label.config(text=f"エラー: {type(e).__name__}")
    finally:
        progress_var.set(0) # プログレスバーをリセット
        run_button.config(state=tk.NORMAL) # 実行ボタンを再度有効化
        if 'model' in locals() and model is not None: # modelオブジェクトが存在すれば明示的に削除
            del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect() # ガベージコレクションを強制

# --- GUI関連の関数 ---
def select_audio_file():
    global AUDIO_FILE_PATH
    file_path = filedialog.askopenfilename(
        title="音声ファイルを選択",
        filetypes=(("音声ファイル", "*.wav *.mp3 *.m4a *.ogg *.flac *.mp4"), ("すべてのファイル", "*.*"))
    )
    if file_path:
        AUDIO_FILE_PATH = file_path
        selected_file_label.config(text=f"選択中: {AUDIO_FILE_PATH.split('/')[-1]}")
        status_label.config(text="ファイル選択済み")
    else:
        AUDIO_FILE_PATH = ""
        selected_file_label.config(text="ファイルが選択されていません")

def start_transcription():
    if not AUDIO_FILE_PATH:
        messagebox.showwarning("注意", "まず音声ファイルを選択してください。")
        return

    global SELECTED_MODEL_NAME
    SELECTED_MODEL_NAME = model_var.get()
    # SELECTED_LANGUAGE = lang_var.get() # lang_var を使わないので削除

    run_button.config(state=tk.DISABLED) # 処理中はボタンを無効化
    status_label.config(text="準備中...")
    progress_var.set(5)

    # Whisper処理を別スレッドで開始
    thread = threading.Thread(target=run_whisper_transcription,
                               args=(AUDIO_FILE_PATH, SELECTED_MODEL_NAME, "ja", # language引数に "ja" を直接渡す
                                     progress_var, result_text, status_label, run_button))
    thread.daemon = True # メインウィンドウが閉じたらスレッドも終了するように
    thread.start()

# --- メインウィンドウの作成 ---
root = tk.Tk()
root.title("Whisper 文字起こしアプリ")
root.geometry("700x600") # ウィンドウサイズ

# --- UI要素の作成と配置 ---
# フレームを使って要素をグループ化するとレイアウトしやすい
top_frame = ttk.Frame(root, padding="10")
top_frame.pack(fill=tk.X)

middle_frame = ttk.Frame(root, padding="10")
middle_frame.pack(fill=tk.X)

bottom_frame = ttk.Frame(root, padding="10")
bottom_frame.pack(fill=tk.BOTH, expand=True)

status_frame = ttk.Frame(root, padding="5")
status_frame.pack(fill=tk.X, side=tk.BOTTOM)


# ファイル選択
select_button = ttk.Button(top_frame, text="音声ファイルを選択", command=select_audio_file)
select_button.pack(side=tk.LEFT, padx=5)
selected_file_label = ttk.Label(top_frame, text="ファイルが選択されていません", width=60)
selected_file_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

# モデル選択
model_label = ttk.Label(middle_frame, text="モデル:")
model_label.pack(side=tk.LEFT, padx=(0, 5))
model_options = ["tiny", "base", "small", "medium", "large", "large-v3"] # 利用可能なモデルに応じて
model_var = tk.StringVar(value=SELECTED_MODEL_NAME)
model_menu = ttk.OptionMenu(middle_frame, model_var, SELECTED_MODEL_NAME, *model_options)
model_menu.pack(side=tk.LEFT, padx=5)

# 言語選択 (日本語固定のため、UI要素をコメントアウトまたは削除)
# lang_label = ttk.Label(middle_frame, text="言語 (空で自動):")
# lang_label.pack(side=tk.LEFT, padx=(10, 5))
# lang_var = tk.StringVar(value=SELECTED_LANGUAGE) # SELECTED_LANGUAGE は "ja" 固定
# lang_entry = ttk.Entry(middle_frame, textvariable=lang_var, width=10)
# lang_entry.pack(side=tk.LEFT, padx=5)
# (より親切にするなら、よく使う言語のドロップダウンも良い)

# 実行ボタン
run_button = ttk.Button(middle_frame, text="文字起こし実行", command=start_transcription)
run_button.pack(side=tk.LEFT, padx=10)

# 結果表示テキストエリア
result_text_label = ttk.Label(bottom_frame, text="文字起こし結果:")
result_text_label.pack(anchor=tk.W)
result_text = scrolledtext.ScrolledText(bottom_frame, wrap=tk.WORD, height=15, width=80)
result_text.pack(fill=tk.BOTH, expand=True, pady=5)

# ステータス表示 & プログレスバー
status_label = ttk.Label(status_frame, text="待機中")
status_label.pack(side=tk.LEFT, padx=5)
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(status_frame, variable=progress_var, maximum=100)
progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)


root.mainloop()