#!/usr/bin/env python
"""データベースの構造と内容を確認するスクリプト"""

import sqlite3
import os

def check_database():
    db_path = "database/cases_v2.db"
    
    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return
    
    print(f"✅ データベースファイルが存在します: {db_path}")
    print(f"📁 ファイルサイズ: {os.path.getsize(db_path):,} bytes")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # テーブル一覧を取得
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n📋 テーブル一覧 ({len(tables)}個):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 各テーブルの構造を確認
        for table in tables:
            table_name = table[0]
            print(f"\n🔍 テーブル '{table_name}' の構造:")
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                col_id, name, col_type, not_null, default, pk = col
                pk_marker = " (PRIMARY KEY)" if pk else ""
                null_marker = " NOT NULL" if not_null else ""
                default_marker = f" DEFAULT {default}" if default else ""
                print(f"    {name}: {col_type}{pk_marker}{null_marker}{default_marker}")
            
            # レコード数を確認
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"    📊 レコード数: {count}")
        
        # インデックスを確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
        indexes = cursor.fetchall()
        
        if indexes:
            print(f"\n🔗 インデックス一覧 ({len(indexes)}個):")
            for index in indexes:
                print(f"  - {index[0]}")
        else:
            print("\n🔗 カスタムインデックスはありません")
        
        conn.close()
        print("\n✅ データベース確認完了")
        
    except Exception as e:
        print(f"❌ データベース確認中にエラーが発生しました: {e}")

if __name__ == "__main__":
    check_database()
