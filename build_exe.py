#!/usr/bin/env python3
"""
Bangogo Plus Improved - EXE Build Script
高速起動のための最適化されたビルドスクリプト
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """EXEファイルをビルドします"""
    
    # 現在のディレクトリ
    current_dir = Path(__file__).parent
    script_path = current_dir / "bangogo_plus_improved.py"
    
    if not script_path.exists():
        print(f"エラー: {script_path} が見つかりません")
        return 1
    
    # PyInstallerがインストールされているか確認
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} が見つかりました")
    except ImportError:
        print("PyInstallerをインストールしています...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # ビルドディレクトリをクリーンアップ
    for dir_name in ["build", "dist", "__pycache__"]:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            print(f"クリーンアップ: {dir_path}")
            shutil.rmtree(dir_path)
    
    # PyInstallerコマンドを構築
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # 単一EXEファイル
        "--windowed",  # コンソールウィンドウを非表示
        "--optimize", "2",  # Python最適化レベル2
        "--strip",  # シンボル除去
        "--noupx",  # UPX圧縮を無効化（起動速度優先）
        
        # 不要なモジュールを除外（起動時間短縮）
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy.tests",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "jupyter",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        "--exclude-module", "qtconsole",
        "--exclude-module", "spyder",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",
        "--exclude-module", "unittest",
        "--exclude-module", "test",
        "--exclude-module", "tests",
        
        # アイコンが存在する場合
        "--icon", str(current_dir / "Icon1.ico") if (current_dir / "Icon1.ico").exists() else "NONE",
        
        # 出力名
        "--name", "BangogoPlus",
        
        # スクリプトファイル
        str(script_path)
    ]
    
    print("EXEファイルをビルドしています...")
    print("コマンド:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, cwd=current_dir, check=True, capture_output=True, text=True)
        print("ビルドが完了しました！")
        
        # 出力ファイルの確認
        exe_path = current_dir / "dist" / "BangogoPlus.exe"
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"出力ファイル: {exe_path}")
            print(f"ファイルサイズ: {file_size:.1f} MB")
            
            # 設定ファイルをコピー
            for config_file in current_dir.glob("*.json"):
                dest = current_dir / "dist" / config_file.name
                shutil.copy2(config_file, dest)
                print(f"設定ファイルをコピー: {config_file.name}")
                
        else:
            print("警告: EXEファイルが見つかりません")
            
    except subprocess.CalledProcessError as e:
        print(f"ビルドエラー: {e}")
        if e.stdout:
            print("標準出力:", e.stdout)
        if e.stderr:
            print("標準エラー:", e.stderr)
        return 1
    
    print("\n=== ビルド完了 ===")
    print("EXEファイルは dist/ フォルダにあります")
    return 0

if __name__ == "__main__":
    sys.exit(main())