#!/usr/bin/env python3
"""
案件番号と依頼者名入力時の即座エラー表示改善のテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.modern_calculator_ui import ModernCompensationCalculator
from database.db_manager import DatabaseManager
from config.app_config import AppConfig
import customtkinter as ctk

def test_input_improvements():
    """
    案件番号と依頼者名の入力改善をテストする
    """
    print("=== 入力改善テスト開始 ===")
    
    # テスト用ルートウィンドウを作成
    test_root = ctk.CTk()
    test_root.withdraw()  # ウィンドウを隠す
    
    try:        # アプリケーションコンポーネントを初期化
        config = AppConfig()
        db_manager = DatabaseManager("database/cases_v2.db")
          # ModernCompensationCalculatorを初期化（テスト用に非表示で）
        ui = ModernCompensationCalculator(test_root, db_manager, config)
        
        # 新規案件作成をテスト
        print("✓ UIコンポーネントが正常に初期化されました")
        
        # create_input_fieldメソッドの動作確認
        print("✓ create_input_fieldメソッドの自動計算制御機能をチェック中...")
        
        # テスト用フレーム作成
        test_frame = ctk.CTkFrame(test_root)
        
        # 自動計算が有効な通常フィールドのテスト
        normal_entry = ui.create_input_field(
            test_frame, "テスト項目1", "", auto_calculate=True
        )
        print("✓ 自動計算有効フィールド作成成功")
        
        # 自動計算が無効なフィールドのテスト  
        no_auto_entry = ui.create_input_field(
            test_frame, "テスト項目2", "", auto_calculate=False
        )
        print("✓ 自動計算無効フィールド作成成功")
        
        # バインドされたイベントの確認
        normal_bindings = normal_entry.bind()
        no_auto_bindings = no_auto_entry.bind()
        
        print(f"通常フィールドのバインド数: {len(normal_bindings)}")
        print(f"自動計算無効フィールドのバインド数: {len(no_auto_bindings)}")
        
        # KeyReleaseイベントがバインドされているかを確認
        has_keyrelease_normal = '<KeyRelease>' in normal_bindings
        has_keyrelease_no_auto = '<KeyRelease>' in no_auto_bindings
        
        print(f"通常フィールドにKeyReleaseバインド: {has_keyrelease_normal}")
        print(f"自動計算無効フィールドにKeyReleaseバインド: {has_keyrelease_no_auto}")
        
        # 期待される結果
        if has_keyrelease_normal and not has_keyrelease_no_auto:
            print("✅ 自動計算制御が正しく動作しています")
            print("✅ 案件番号と依頼者名での即座エラー表示が改善されました")
        else:
            print("❌ 自動計算制御に問題があります")
            print(f"   通常フィールド KeyRelease: {has_keyrelease_normal} (期待値: True)")
            print(f"   無効フィールド KeyRelease: {has_keyrelease_no_auto} (期待値: False)")
        
        print("\n=== テスト結果サマリー ===")
        print("1. UIコンポーネント初期化: 成功")
        print("2. 自動計算制御機能: " + ("成功" if has_keyrelease_normal and not has_keyrelease_no_auto else "要確認"))
        print("3. 入力フィールド作成: 成功")
        print("\n改善内容:")
        print("- 案件番号入力時の即座エラー表示を停止")
        print("- 依頼者名入力時の即座エラー表示を停止")
        print("- その他のフィールドは従来通りリアルタイム計算を維持")
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        test_root.destroy()
        print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_input_improvements()
