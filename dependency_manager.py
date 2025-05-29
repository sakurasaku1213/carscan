#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依存関係管理とシステム要件チェック

機能:
- 必要なパッケージの自動インストール
- システム要件の確認
- 環境の診断とレポート
- 依存関係の競合解決
"""

import subprocess
import sys
import importlib
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
from dataclasses import dataclass, asdict

@dataclass
class PackageInfo:
    """パッケージ情報"""
    name: str
    version: Optional[str] = None
    required: bool = True
    install_name: Optional[str] = None  # pip install時の名前が異なる場合
    description: str = ""

class DependencyManager:
    """依存関係管理システム"""
    
    def __init__(self, requirements_file: str = "requirements.txt"):
        self.requirements_file = Path(requirements_file)
        self.logger = logging.getLogger(__name__)
        
        # 必須パッケージの定義
        self.core_packages = [
            PackageInfo("customtkinter", ">=5.2.0", True, 
                       description="現代的なTkinter UI フレームワーク"),
            PackageInfo("pandas", ">=2.0.0", True, 
                       description="データ処理・分析ライブラリ"),
            PackageInfo("openpyxl", ">=3.1.0", True, 
                       description="Excel ファイル生成・編集"),
            PackageInfo("reportlab", ">=4.0.0", True, 
                       description="PDF 生成ライブラリ"),
            PackageInfo("numpy", ">=1.24.0", True, 
                       description="数値計算ライブラリ"),
            PackageInfo("pillow", ">=10.0.0", True, "Pillow",
                       description="画像処理ライブラリ"),
            PackageInfo("matplotlib", ">=3.7.0", False, 
                       description="グラフ・可視化ライブラリ"),
        ]
        
        # オプショナルパッケージ
        self.optional_packages = [
            PackageInfo("scipy", ">=1.11.0", False, 
                       description="科学計算ライブラリ"),
            PackageInfo("cryptography", ">=41.0.0", False, 
                       description="暗号化・セキュリティ"),
            PackageInfo("psutil", ">=5.9.0", False, 
                       description="システム監視"),
        ]
        
        # 開発用パッケージ
        self.dev_packages = [
            PackageInfo("pytest", ">=7.4.0", False, 
                       description="テストフレームワーク"),
            PackageInfo("black", ">=23.7.0", False, 
                       description="コードフォーマッター"),
            PackageInfo("flake8", ">=6.0.0", False, 
                       description="コード品質チェック"),
            PackageInfo("mypy", ">=1.5.0", False, 
                       description="型チェッカー"),
        ]

    def check_package_installation(self, package: PackageInfo) -> Tuple[bool, Optional[str]]:
        """パッケージのインストール状況をチェック"""
        try:
            # パッケージをインポートしてみる
            module = importlib.import_module(package.name)
            
            # バージョン情報を取得
            version = None
            if hasattr(module, '__version__'):
                version = module.__version__
            elif hasattr(module, 'version'):
                version = module.version
            elif hasattr(module, 'VERSION'):
                version = module.VERSION
                
            self.logger.debug(f"パッケージ {package.name} は利用可能です (バージョン: {version})")
            return True, version
            
        except ImportError:
            self.logger.warning(f"パッケージ {package.name} がインストールされていません")
            return False, None
        except Exception as e:
            self.logger.error(f"パッケージ {package.name} のチェック中にエラー: {e}")
            return False, None

    def install_package(self, package: PackageInfo, force_upgrade: bool = False) -> bool:
        """パッケージをインストール"""
        try:
            install_name = package.install_name or package.name
            cmd = [sys.executable, "-m", "pip", "install"]
            
            if force_upgrade:
                cmd.append("--upgrade")
            
            if package.version:
                cmd.append(f"{install_name}{package.version}")
            else:
                cmd.append(install_name)
            
            self.logger.info(f"パッケージをインストール中: {install_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"パッケージ {install_name} のインストールが完了しました")
                return True
            else:
                self.logger.error(f"パッケージ {install_name} のインストールに失敗: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"パッケージ {package.name} のインストールがタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"パッケージ {package.name} のインストール中にエラー: {e}")
            return False

    def check_system_requirements(self) -> Dict[str, any]:
        """システム要件をチェック"""
        requirements = {
            "python_version": {
                "current": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "required": ">=3.8.0",
                "status": sys.version_info >= (3, 8, 0)
            },
            "platform": sys.platform,
            "architecture": sys.maxsize > 2**32 and "64bit" or "32bit",
            "pip_available": False,
            "git_available": False
        }
        
        # pipの確認
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            requirements["pip_available"] = result.returncode == 0
            if result.returncode == 0:
                requirements["pip_version"] = result.stdout.strip()
        except:
            pass
        
        # gitの確認
        try:
            result = subprocess.run(["git", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            requirements["git_available"] = result.returncode == 0
            if result.returncode == 0:
                requirements["git_version"] = result.stdout.strip()
        except:
            pass
        
        return requirements

    def generate_dependency_report(self) -> Dict[str, any]:
        """依存関係レポートを生成"""
        report = {
            "timestamp": str(datetime.now()),
            "system": self.check_system_requirements(),
            "packages": {
                "core": [],
                "optional": [],
                "development": []
            },
            "missing_required": [],
            "recommendations": []
        }
        
        # コアパッケージのチェック
        for package in self.core_packages:
            installed, version = self.check_package_installation(package)
            package_info = {
                "name": package.name,
                "installed": installed,
                "version": version,
                "required": package.required,
                "description": package.description
            }
            report["packages"]["core"].append(package_info)
            
            if package.required and not installed:
                report["missing_required"].append(package.name)
        
        # オプショナルパッケージのチェック
        for package in self.optional_packages:
            installed, version = self.check_package_installation(package)
            package_info = {
                "name": package.name,
                "installed": installed,
                "version": version,
                "description": package.description
            }
            report["packages"]["optional"].append(package_info)
        
        # 開発パッケージのチェック
        for package in self.dev_packages:
            installed, version = self.check_package_installation(package)
            package_info = {
                "name": package.name,
                "installed": installed,
                "version": version,
                "description": package.description
            }
            report["packages"]["development"].append(package_info)
        
        # 推奨事項の生成
        if report["missing_required"]:
            report["recommendations"].append(
                "必須パッケージがインストールされていません。install_missing_packages() を実行してください。"
            )
        
        if not report["system"]["pip_available"]:
            report["recommendations"].append(
                "pip が利用できません。Python の pip をインストールしてください。"
            )
        
        return report

    def install_missing_packages(self, include_optional: bool = False, 
                                include_dev: bool = False) -> bool:
        """不足しているパッケージをインストール"""
        packages_to_install = []
        
        # 必須パッケージをチェック
        for package in self.core_packages:
            installed, _ = self.check_package_installation(package)
            if not installed:
                packages_to_install.append(package)
        
        # オプショナルパッケージ
        if include_optional:
            for package in self.optional_packages:
                installed, _ = self.check_package_installation(package)
                if not installed:
                    packages_to_install.append(package)
        
        # 開発パッケージ
        if include_dev:
            for package in self.dev_packages:
                installed, _ = self.check_package_installation(package)
                if not installed:
                    packages_to_install.append(package)
        
        if not packages_to_install:
            self.logger.info("すべての必要なパッケージがインストールされています")
            return True
        
        success_count = 0
        for package in packages_to_install:
            if self.install_package(package):
                success_count += 1
        
        self.logger.info(f"インストール完了: {success_count}/{len(packages_to_install)} パッケージ")
        return success_count == len(packages_to_install)

    def save_report(self, filepath: str = "dependency_report.json") -> bool:
        """依存関係レポートをファイルに保存"""
        try:
            report = self.generate_dependency_report()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.logger.info(f"依存関係レポートを保存しました: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"レポート保存エラー: {e}")
            return False

# 便利関数
def quick_setup(install_missing: bool = True) -> bool:
    """クイックセットアップ"""
    dm = DependencyManager()
    
    print("🔍 システム要件を確認中...")
    requirements = dm.check_system_requirements()
    
    if not requirements["python_version"]["status"]:
        print(f"❌ Python バージョンが古すぎます: {requirements['python_version']['current']}")
        print(f"   必要バージョン: {requirements['python_version']['required']}")
        return False
    
    if not requirements["pip_available"]:
        print("❌ pip が利用できません。Python の pip をインストールしてください。")
        return False
    
    print("✅ システム要件を満たしています")
    
    if install_missing:
        print("📦 不足しているパッケージをインストール中...")
        success = dm.install_missing_packages()
        if success:
            print("✅ すべてのパッケージのインストールが完了しました")
        else:
            print("⚠️  一部のパッケージのインストールに失敗しました")
        return success
    
    return True

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="依存関係管理ツール")
    parser.add_argument("--install", action="store_true", help="不足しているパッケージをインストール")
    parser.add_argument("--report", action="store_true", help="依存関係レポートを生成")
    parser.add_argument("--quick", action="store_true", help="クイックセットアップを実行")
    
    args = parser.parse_args()
    
    dm = DependencyManager()
    
    if args.quick:
        quick_setup()
    elif args.install:
        dm.install_missing_packages(include_optional=True)
    elif args.report:
        dm.save_report()
        print("依存関係レポートを dependency_report.json に保存しました")
    else:
        # デフォルト: レポート表示
        report = dm.generate_dependency_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
