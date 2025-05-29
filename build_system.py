#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弁護士基準損害賠償計算システム - 統合ビルドシステム
テスト実行、品質チェック、パッケージング、デプロイまでを統合管理
"""

import os
import sys
import subprocess
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class BuildSystem:
    """統合ビルドシステム"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent
        self.logger = logging.getLogger(__name__)
        self.build_config = self._load_build_config()
        
        # ビルド用ディレクトリ
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.temp_dir = self.project_root / "temp"
        
        # 必要なツールの確認
        self._check_dependencies()
    
    def _load_build_config(self) -> Dict[str, Any]:
        """ビルド設定を読み込み"""
        config_path = self.project_root / "build_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"ビルド設定読み込みエラー: {e}")
        
        # デフォルト設定
        return {
            "app_name": "CompensationCalculator",
            "version": "1.0.0",
            "main_script": "lawyer_compensation_calculator.py",
            "icon_file": "Icon1.ico",
            "exclude_modules": [
                "matplotlib", "numpy.tests", "scipy", "pandas",
                "jupyter", "IPython", "notebook", "qtconsole",
                "spyder", "pydoc", "doctest", "unittest.mock",
                "test", "tests", "tkinter.test"
            ],
            "include_files": [
                "config/",
                "*.json"
            ],
            "optimization_level": 2,
            "console": False,
            "onefile": True
        }
    
    def _check_dependencies(self) -> None:
        """必要なツールがインストールされているか確認"""
        required_tools = [
            "pyinstaller",
            "pytest",
            "black",
            "flake8",
            "mypy"
        ]
        
        missing_tools = []
        for tool in required_tools:
            try:
                subprocess.run([sys.executable, "-m", tool, "--version"], 
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)
        
        if missing_tools:
            self.logger.info(f"不足しているツールをインストールします: {missing_tools}")
            self._install_dependencies(missing_tools)
    
    def _install_dependencies(self, tools: List[str]) -> None:
        """依存関係をインストール"""
        for tool in tools:
            try:
                self.logger.info(f"インストール中: {tool}")
                subprocess.run([sys.executable, "-m", "pip", "install", tool], 
                             check=True, capture_output=True)
                self.logger.info(f"インストール完了: {tool}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"{tool}のインストールに失敗: {e}")
    
    def clean(self) -> bool:
        """ビルド成果物をクリーンアップ"""
        self.logger.info("クリーンアップを開始します")
        
        try:
            # ビルド関連ディレクトリを削除
            for dir_path in [self.build_dir, self.dist_dir, self.temp_dir]:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    self.logger.info(f"削除: {dir_path}")
            
            # __pycache__を削除
            for pycache in self.project_root.rglob("__pycache__"):
                shutil.rmtree(pycache)
            
            # .pyc ファイルを削除
            for pyc_file in self.project_root.rglob("*.pyc"):
                pyc_file.unlink()
            
            self.logger.info("クリーンアップが完了しました")
            return True
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
            return False
    
    def format_code(self) -> bool:
        """コードフォーマッターを実行"""
        self.logger.info("コードフォーマットを開始します")
        
        try:
            # Blackでフォーマット
            result = subprocess.run([
                sys.executable, "-m", "black",
                "--line-length", "88",
                "--target-version", "py39",
                str(self.project_root)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("コードフォーマットが完了しました")
                return True
            else:
                self.logger.error(f"フォーマットエラー: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"フォーマット実行エラー: {e}")
            return False
    
    def lint_code(self) -> bool:
        """コード品質チェックを実行"""
        self.logger.info("コード品質チェックを開始します")
        
        success = True
        
        try:
            # Flake8による静的解析
            self.logger.info("Flake8によるリンティング...")
            result = subprocess.run([
                sys.executable, "-m", "flake8",
                "--max-line-length", "88",
                "--ignore", "E203,W503,E501",
                str(self.project_root)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.warning(f"Flake8警告:\n{result.stdout}")
                success = False
            
            # MyPyによる型チェック
            self.logger.info("MyPyによる型チェック...")
            result = subprocess.run([
                sys.executable, "-m", "mypy",
                "--ignore-missing-imports",
                "--follow-imports=silent",
                str(self.project_root)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.warning(f"MyPy警告:\n{result.stdout}")
                # 型エラーは警告扱い（ビルドは継続）
            
            if success:
                self.logger.info("コード品質チェックが完了しました")
            
            return success
            
        except Exception as e:
            self.logger.error(f"リント実行エラー: {e}")
            return False
    
    def run_tests(self) -> bool:
        """テストを実行"""
        self.logger.info("テストを開始します")
        
        try:
            # Pytestでテスト実行
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "-v",
                "--tb=short",
                "--cov=.",
                "--cov-report=term-missing",
                str(self.project_root / "tests")
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                self.logger.info("すべてのテストが成功しました")
                self.logger.info(f"テスト結果:\n{result.stdout}")
                return True
            else:
                self.logger.error(f"テストが失敗しました:\n{result.stdout}\n{result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"テスト実行エラー: {e}")
            return False
    
    def build_executable(self) -> bool:
        """実行ファイルをビルド"""
        self.logger.info("実行ファイルのビルドを開始します")
        
        try:
            # ビルドディレクトリを作成
            self.dist_dir.mkdir(exist_ok=True)
            
            # メインスクリプトパス
            main_script = self.project_root / self.build_config["main_script"]
            if not main_script.exists():
                self.logger.error(f"メインスクリプトが見つかりません: {main_script}")
                return False
            
            # PyInstallerコマンドを構築
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                f"--distpath={self.dist_dir}",
                f"--workpath={self.build_dir}",
                f"--specpath={self.temp_dir}"
            ]
            
            # 設定に基づいてオプションを追加
            if self.build_config["onefile"]:
                cmd.append("--onefile")
            
            if not self.build_config["console"]:
                cmd.append("--windowed")
            
            cmd.extend([
                "--optimize", str(self.build_config["optimization_level"]),
                "--strip"
            ])
            
            # アイコンファイル
            icon_path = self.project_root / self.build_config["icon_file"]
            if icon_path.exists():
                cmd.extend(["--icon", str(icon_path)])
            
            # 除外モジュール
            for module in self.build_config["exclude_modules"]:
                cmd.extend(["--exclude-module", module])
            
            # 含めるファイル
            for include_pattern in self.build_config["include_files"]:
                include_path = self.project_root / include_pattern
                if include_path.exists():
                    if include_path.is_dir():
                        cmd.extend(["--add-data", f"{include_path};{include_pattern}"])
                    else:
                        cmd.extend(["--add-data", f"{include_path};."])
            
            # アプリケーション名
            cmd.extend(["--name", self.build_config["app_name"]])
            
            # メインスクリプト
            cmd.append(str(main_script))
            
            self.logger.info(f"ビルドコマンド: {' '.join(cmd)}")
            
            # PyInstallerを実行
            result = subprocess.run(cmd, cwd=self.project_root, 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # 成果物の確認
                exe_name = f"{self.build_config['app_name']}.exe"
                exe_path = self.dist_dir / exe_name
                
                if exe_path.exists():
                    file_size = exe_path.stat().st_size / (1024 * 1024)
                    self.logger.info(f"ビルド成功: {exe_path} ({file_size:.1f} MB)")
                    
                    # 追加ファイルのコピー
                    self._copy_additional_files()
                    
                    return True
                else:
                    self.logger.error("実行ファイルが見つかりません")
                    return False
            else:
                self.logger.error(f"ビルドエラー:\n{result.stdout}\n{result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"ビルド実行エラー: {e}")
            return False
    
    def _copy_additional_files(self) -> None:
        """追加ファイルをdistディレクトリにコピー"""
        try:
            # 設定ファイル
            config_files = [
                "config/app_config.json",
                "README_弁護士基準計算システム.md"
            ]
            
            for file_path in config_files:
                src = self.project_root / file_path
                if src.exists():
                    if src.is_file():
                        dest = self.dist_dir / src.name
                        shutil.copy2(src, dest)
                        self.logger.info(f"ファイルをコピー: {src.name}")
                    else:
                        # ディレクトリの場合
                        dest = self.dist_dir / src.name
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(src, dest)
                        self.logger.info(f"ディレクトリをコピー: {src.name}")
            
        except Exception as e:
            self.logger.warning(f"追加ファイルのコピーエラー: {e}")
    
    def create_installer(self) -> bool:
        """インストーラーを作成（NSIS使用）"""
        self.logger.info("インストーラーの作成は現在未実装です")
        # 将来的にNSISスクリプトでインストーラー作成
        return True
    
    def generate_build_report(self) -> Dict[str, Any]:
        """ビルドレポートを生成"""
        report = {
            "build_date": datetime.now().isoformat(),
            "version": self.build_config["version"],
            "app_name": self.build_config["app_name"],
            "build_success": True,
            "artifacts": []
        }
        
        # 成果物の確認
        if self.dist_dir.exists():
            for item in self.dist_dir.iterdir():
                if item.is_file():
                    report["artifacts"].append({
                        "name": item.name,
                        "size": item.stat().st_size,
                        "path": str(item)
                    })
        
        # レポートファイルを保存
        report_path = self.dist_dir / "build_report.json"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.logger.info(f"ビルドレポートを保存: {report_path}")
        except Exception as e:
            self.logger.warning(f"ビルドレポート保存エラー: {e}")
        
        return report
    
    def full_build(self, skip_tests: bool = False, skip_lint: bool = False) -> bool:
        """フルビルドプロセスを実行"""
        self.logger.info("=== フルビルドプロセスを開始 ===")
        
        steps = [
            ("クリーンアップ", self.clean),
            ("コードフォーマット", self.format_code)
        ]
        
        if not skip_lint:
            steps.append(("コード品質チェック", self.lint_code))
        
        if not skip_tests:
            steps.append(("テスト実行", self.run_tests))
        
        steps.extend([
            ("実行ファイルビルド", self.build_executable),
            ("インストーラー作成", self.create_installer)
        ])
        
        success = True
        for step_name, step_func in steps:
            self.logger.info(f"=== {step_name} ===")
            if not step_func():
                self.logger.error(f"{step_name}が失敗しました")
                success = False
                # テスト以外の失敗はビルドを中止
                if step_name != "テスト実行":
                    break
        
        # ビルドレポート生成
        report = self.generate_build_report()
        report["build_success"] = success
        
        if success:
            self.logger.info("=== フルビルドが成功しました ===")
        else:
            self.logger.error("=== フルビルドが失敗しました ===")
        
        return success

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="統合ビルドシステム")
    parser.add_argument("--clean", action="store_true", help="クリーンアップのみ実行")
    parser.add_argument("--format", action="store_true", help="コードフォーマットのみ実行")
    parser.add_argument("--lint", action="store_true", help="リントのみ実行")
    parser.add_argument("--test", action="store_true", help="テストのみ実行")
    parser.add_argument("--build", action="store_true", help="ビルドのみ実行")
    parser.add_argument("--skip-tests", action="store_true", help="テストをスキップ")
    parser.add_argument("--skip-lint", action="store_true", help="リントをスキップ")
    parser.add_argument("--full", action="store_true", help="フルビルド実行")
    
    args = parser.parse_args()
    
    build_system = BuildSystem()
    
    try:
        if args.clean:
            return 0 if build_system.clean() else 1
        elif args.format:
            return 0 if build_system.format_code() else 1
        elif args.lint:
            return 0 if build_system.lint_code() else 1
        elif args.test:
            return 0 if build_system.run_tests() else 1
        elif args.build:
            return 0 if build_system.build_executable() else 1
        elif args.full or not any(vars(args).values()):
            # デフォルトはフルビルド
            return 0 if build_system.full_build(args.skip_tests, args.skip_lint) else 1
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logging.getLogger().info("ビルドが中断されました")
        return 1
    except Exception as e:
        logging.getLogger().error(f"予期しないエラー: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
