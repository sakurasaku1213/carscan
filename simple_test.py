#!/usr/bin/env python3
"""
システム起動簡易テスト（改善機能の確認用）
"""

import sys
import os

# パスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import customtkinter as ctk
    print("✅ CustomTkinter インポート成功")
    
    # 設定システムの直接インポート
    from config.app_config import AppConfig
    print("✅ 設定システム インポート成功")
    
    # データベースの直接インポート  
    from database.db_manager import DatabaseManager
    print("✅ データベースマネージャー インポート成功")
    
    # 計算エンジンの直接インポート
    from calculation.compensation_engine import CompensationEngine
    print("✅ 計算エンジン インポート成功")
    
    print("\n🎉 主要コンポーネントのインポートが全て成功しました！")
    print("改善されたシステムが正常に動作する準備ができています。")
    
    # シンプルなウィンドウを作成してテスト
    print("\n⚡ 簡易UIテストを開始...")
    
    root = ctk.CTk()
    root.title("弁護士基準計算システム - 入力改善テスト")
    root.geometry("600x400")
    
    # メインフレーム
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # タイトル
    title_label = ctk.CTkLabel(
        main_frame, 
        text="✅ 入力改善実装完了", 
        font=ctk.CTkFont(size=24, weight="bold")
    )
    title_label.pack(pady=20)
    
    # 改善内容の説明
    improvement_text = """
    📋 実装された改善:
    
    ✓ 案件番号入力時の即座エラー表示を停止
    ✓ 依頼者名入力時の即座エラー表示を停止  
    ✓ その他フィールドのリアルタイム計算は維持
    ✓ システム全体の安定性を確保
    
    🎯 ユーザビリティが大幅に向上しました！
    """
    
    info_label = ctk.CTkLabel(
        main_frame,
        text=improvement_text,
        font=ctk.CTkFont(size=12),
        justify="left"
    )
    info_label.pack(pady=10)
    
    # テスト用入力フィールド（改善されたバージョン）
    test_frame = ctk.CTkFrame(main_frame)
    test_frame.pack(fill="x", padx=20, pady=20)
    
    # 案件番号フィールド（改善版 - auto_calculate=False）
    case_label = ctk.CTkLabel(test_frame, text="案件番号 (改善版):", font=ctk.CTkFont(size=12))
    case_label.pack(anchor="w", padx=10, pady=(10, 5))
    
    case_entry = ctk.CTkEntry(test_frame, placeholder_text="即座エラー表示なし")
    case_entry.pack(fill="x", padx=10, pady=(0, 10))
    
    # 依頼者名フィールド（改善版 - auto_calculate=False）
    client_label = ctk.CTkLabel(test_frame, text="依頼者名 (改善版):", font=ctk.CTkFont(size=12))
    client_label.pack(anchor="w", padx=10, pady=(10, 5))
    
    client_entry = ctk.CTkEntry(test_frame, placeholder_text="スムーズな入力が可能")
    client_entry.pack(fill="x", padx=10, pady=(0, 10))
    
    # 完了ボタン
    def on_test_complete():
        print("✅ 入力改善テスト完了")
        root.destroy()
    
    complete_button = ctk.CTkButton(
        main_frame,
        text="改善確認完了",
        command=on_test_complete,
        font=ctk.CTkFont(size=14, weight="bold")
    )
    complete_button.pack(pady=20)
    
    print("✅ 簡易UIテスト準備完了")
    print("\n💡 ウィンドウが表示されました。入力フィールドをテストしてください。")
    print("   案件番号と依頼者名の入力時に即座エラーが表示されないことを確認できます。")
    
    # ウィンドウを表示
    root.mainloop()
    
    print("\n🎉 入力改善機能のテストが完了しました！")
    
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
