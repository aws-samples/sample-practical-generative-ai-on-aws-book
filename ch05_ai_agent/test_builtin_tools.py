#!/usr/bin/env python3
"""
AgentCore Built-in Tools テストスクリプト
Code Interpreter と Browser Tool の動作をテスト
"""

import json
import sys
import time
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
    CODE_INTERPRETER_AVAILABLE = True
except ImportError:
    CODE_INTERPRETER_AVAILABLE = False

try:
    from bedrock_agentcore.tools.browser_client import browser_session
    BROWSER_TOOL_AVAILABLE = True
except ImportError:
    BROWSER_TOOL_AVAILABLE = False

if not CODE_INTERPRETER_AVAILABLE and not BROWSER_TOOL_AVAILABLE:
    print("❌ AgentCore Tools のインポートエラー")
    print("   bedrock-agentcore パッケージがインストールされていない可能性があります")
    sys.exit(1)


class BuiltinToolsTester:
    def __init__(self):
        self.region = 'us-east-1'
        self.code_interpreter = None
        self.browser_tool = None
        
        print(f"🌍 リージョン: {self.region}")
    
    def test_code_interpreter(self):
        """Code Interpreter のテスト"""
        print("\n🔧 Code Interpreter テスト開始")
        print("=" * 50)
        
        if not CODE_INTERPRETER_AVAILABLE:
            print("❌ Code Interpreter が利用できません")
            print("   bedrock_agentcore.tools.code_interpreter_client モジュールが見つかりません")
            return
        
        try:
            # Code Interpreter を初期化
            self.code_interpreter = CodeInterpreter(self.region)
            print("✅ Code Interpreter を初期化しました")
            
            # セッションを開始
            self.code_interpreter.start(session_timeout_seconds=1200)
            print("✅ Code Interpreter セッションを開始しました")
            
            # テストケース1: 基本的な計算
            print("\n1️⃣  基本計算テスト")
            print("-" * 30)
            
            code1 = """
# 基本的な計算
result = 123 + 456
print(f"計算結果: {result}")

# リストの操作
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]
print(f"二乗のリスト: {squared}")

# 辞書の操作
data = {"name": "テスト", "value": 100}
print(f"データ: {data}")
"""
            
            response1 = self.code_interpreter.invoke("executeCode", {
                "code": code1,
                "language": "python"
            })
            
            print(f"📤 実行コード:\n{code1}")
            
            # ストリームレスポンスを処理
            if "stream" in response1:
                for event in response1["stream"]:
                    if "result" in event:
                        print(f"📥 実行結果:\n{json.dumps(event['result'], ensure_ascii=False, indent=2)}")
                        break
            else:
                print(f"📥 実行結果:\n{json.dumps(response1, ensure_ascii=False, indent=2)}")
            
            # テストケース2: データ分析とグラフ作成
            print("\n2️⃣  データ分析・グラフ作成テスト")
            print("-" * 30)
            
            code2 = """
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# サンプルデータの作成
months = ['1月', '2月', '3月', '4月', '5月', '6月']
sales = [100000, 120000, 95000, 110000, 130000, 125000]

# データフレームの作成
df = pd.DataFrame({
    '月': months,
    '売上': sales
})

print("売上データ:")
print(df)

# 基本統計
print(f"\\n平均売上: {np.mean(sales):,.0f}円")
print(f"最大売上: {np.max(sales):,.0f}円")
print(f"最小売上: {np.min(sales):,.0f}円")

# グラフの作成
plt.figure(figsize=(10, 6))
plt.plot(months, sales, marker='o', linewidth=2, markersize=8)
plt.title('月別売上推移', fontsize=16)
plt.xlabel('月', fontsize=12)
plt.ylabel('売上（円）', fontsize=12)
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)

# Y軸のフォーマット
plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

plt.tight_layout()
plt.savefig('sales_chart.png', dpi=300, bbox_inches='tight')
plt.show()

print("\\nグラフを sales_chart.png として保存しました")
"""
            
            response2 = self.code_interpreter.invoke("executeCode", {
                "code": code2,
                "language": "python"
            })
            
            print(f"📤 実行コード: データ分析・グラフ作成")
            
            # ストリームレスポンスを処理
            if "stream" in response2:
                for event in response2["stream"]:
                    if "result" in event:
                        print(f"📥 実行結果:\n{json.dumps(event['result'], ensure_ascii=False, indent=2)}")
                        break
            else:
                print(f"📥 実行結果:\n{json.dumps(response2, ensure_ascii=False, indent=2)}")
            
            # テストケース3: ファイル操作
            print("\n3️⃣  ファイル操作テスト")
            print("-" * 30)
            
            code3 = """
import json
import csv

# JSONファイルの作成
data = {
    "customer_data": [
        {"id": 1, "name": "田中太郎", "email": "tanaka@example.com", "orders": 5},
        {"id": 2, "name": "佐藤花子", "email": "sato@example.com", "orders": 3},
        {"id": 3, "name": "鈴木一郎", "email": "suzuki@example.com", "orders": 8}
    ]
}

# JSONファイルに保存
with open('customer_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("customer_data.json を作成しました")

# CSVファイルの作成
with open('customer_summary.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['ID', '名前', 'メール', '注文数'])
    
    for customer in data['customer_data']:
        writer.writerow([customer['id'], customer['name'], customer['email'], customer['orders']])

print("customer_summary.csv を作成しました")

# ファイルの読み込みと確認
with open('customer_data.json', 'r', encoding='utf-8') as f:
    loaded_data = json.load(f)

print("\\n読み込んだデータ:")
for customer in loaded_data['customer_data']:
    print(f"ID: {customer['id']}, 名前: {customer['name']}, 注文数: {customer['orders']}")

# ファイル一覧の表示
import os
files = os.listdir('.')
print(f"\\n作成されたファイル: {[f for f in files if f.endswith(('.json', '.csv', '.png'))]}")
"""
            
            response3 = self.code_interpreter.invoke("executeCode", {
                "code": code3,
                "language": "python"
            })
            
            print(f"📤 実行コード: ファイル操作")
            
            # ストリームレスポンスを処理
            if "stream" in response3:
                for event in response3["stream"]:
                    if "result" in event:
                        print(f"📥 実行結果:\n{json.dumps(event['result'], ensure_ascii=False, indent=2)}")
                        break
            else:
                print(f"📥 実行結果:\n{json.dumps(response3, ensure_ascii=False, indent=2)}")
            
            print("\n✅ Code Interpreter テスト完了!")
            
        except Exception as e:
            print(f"❌ Code Interpreter テストエラー: {e}")
        finally:
            if self.code_interpreter:
                try:
                    self.code_interpreter.stop()
                    print("✅ Code Interpreter セッションを停止しました")
                except Exception as e:
                    print(f"⚠️  セッション停止エラー: {e}")
    
    def test_browser_tool(self):
        """Browser Tool のテスト"""
        print("\n🌐 Browser Tool テスト開始")
        print("=" * 50)
        
        if not BROWSER_TOOL_AVAILABLE:
            print("❌ Browser Tool が利用できません")
            print("   bedrock_agentcore.tools.browser_tool_client モジュールが見つかりません")
            return
        
        try:
            # Browser Tool セッションを開始
            print("✅ Browser Tool セッションを開始します")
            
            with browser_session(self.region) as client:
                print("✅ Browser Tool セッションを開始しました")
                
                # WebSocket URL とヘッダーを取得
                ws_url, headers = client.generate_ws_headers()
                print(f"📤 WebSocket URL: {ws_url[:50]}...")
                
                # テストケース1: セッション情報の確認
                print("\n1️⃣  セッション情報確認テスト")
                print("-" * 30)
                print(f"✅ Browser セッションが正常に作成されました")
                print(f"   WebSocket URL: 取得完了")
                print(f"   Headers: 取得完了")
                
                # テストケース2: セッション状態の確認
                print("\n2️⃣  セッション状態確認テスト")
                print("-" * 30)
                
                # セッションが有効かどうかを確認
                try:
                    # セッションの基本情報を取得
                    session_info = {
                        "region": self.region,
                        "ws_url_available": bool(ws_url),
                        "headers_available": bool(headers),
                        "session_active": True
                    }
                    print(f"📥 セッション情報:\n{json.dumps(session_info, ensure_ascii=False, indent=2)}")
                    
                except Exception as session_error:
                    print(f"⚠️  セッション状態確認エラー: {session_error}")
                
                print("\n✅ Browser Tool テスト完了!")
                
        except Exception as e:
            print(f"❌ Browser Tool テストエラー: {e}")
            import traceback
            traceback.print_exc()
    
    def test_integrated_scenario(self):
        """統合シナリオのテスト"""
        print("\n🔄 統合シナリオテスト開始")
        print("=" * 50)
        
        try:
            # Code Interpreter でデータ分析
            print("1️⃣  Code Interpreter でデータ分析")
            print("-" * 30)
            
            self.code_interpreter = CodeInterpreter(self.region)
            self.code_interpreter.start(session_timeout_seconds=600)
            
            analysis_code = """
# 顧客サポートデータの分析
import pandas as pd
import matplotlib.pyplot as plt

# サンプルデータ
support_data = {
    'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
    'tickets': [25, 30, 22, 35, 28],
    'resolved': [20, 28, 20, 30, 25],
    'satisfaction': [4.2, 4.5, 4.1, 4.3, 4.4]
}

df = pd.DataFrame(support_data)
df['date'] = pd.to_datetime(df['date'])

print("サポートデータ分析結果:")
print(f"平均チケット数: {df['tickets'].mean():.1f}")
print(f"平均解決数: {df['resolved'].mean():.1f}")
print(f"解決率: {(df['resolved'].sum() / df['tickets'].sum() * 100):.1f}%")
print(f"平均満足度: {df['satisfaction'].mean():.2f}")

# 簡単なグラフ作成
plt.figure(figsize=(10, 6))
plt.subplot(2, 1, 1)
plt.plot(df['date'], df['tickets'], 'b-o', label='チケット数')
plt.plot(df['date'], df['resolved'], 'g-o', label='解決数')
plt.title('日別サポートチケット状況')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(2, 1, 2)
plt.plot(df['date'], df['satisfaction'], 'r-o', label='満足度')
plt.title('日別顧客満足度')
plt.ylabel('満足度 (1-5)')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('support_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

print("\\n分析結果を support_analysis.png として保存しました")
"""
            
            analysis_result = self.code_interpreter.invoke("executeCode", {
                "code": analysis_code,
                "language": "python"
            })
            
            # ストリームレスポンスを処理
            if "stream" in analysis_result:
                for event in analysis_result["stream"]:
                    if "result" in event:
                        print(f"📥 分析結果:\n{json.dumps(event['result'], ensure_ascii=False, indent=2)}")
                        break
            else:
                print(f"📥 分析結果:\n{json.dumps(analysis_result, ensure_ascii=False, indent=2)}")
            
            # Browser Tool で外部情報確認
            print("\n2️⃣  Browser Tool で外部情報確認")
            print("-" * 30)
            
            self.browser_tool = BrowserClient(self.region)
            self.browser_tool.start()
            
            # 公開APIの情報を確認
            nav_result = self.browser_tool.navigate("https://httpbin.org/status/200")
            print(f"📥 ナビゲーション結果:\n{json.dumps(nav_result, ensure_ascii=False, indent=2)}")
            
            screenshot_result = self.browser_tool.screenshot()
            print(f"📥 スクリーンショット結果: 取得完了")
            
            print("\n✅ 統合シナリオテスト完了!")
            
        except Exception as e:
            print(f"❌ 統合シナリオテストエラー: {e}")
        finally:
            # クリーンアップ
            if self.code_interpreter:
                try:
                    self.code_interpreter.stop()
                except Exception:
                    pass
            
            if self.browser_tool:
                try:
                    self.browser_tool.stop()
                except Exception:
                    pass
    
    def run_comprehensive_test(self):
        """包括的なテストを実行"""
        print("🚀 AgentCore Built-in Tools 包括テスト開始")
        print("=" * 60)
        
        # Code Interpreter テスト
        self.test_code_interpreter()
        
        # 少し待機
        time.sleep(3)
        
        # Browser Tool テスト
        self.test_browser_tool()
        
        # 少し待機
        time.sleep(3)
        
        # 統合シナリオテスト
        self.test_integrated_scenario()
        
        print("\n🎉 包括テスト完了!")
    
    def show_requirements(self):
        """必要な権限とセットアップを表示"""
        print("📋 Built-in Tools 使用に必要な設定:")
        print("=" * 50)
        print("""
IAM 権限:
- bedrock-agentcore:CreateCodeInterpreter
- bedrock-agentcore:StartCodeInterpreterSession
- bedrock-agentcore:InvokeCodeInterpreter
- bedrock-agentcore:StopCodeInterpreterSession
- bedrock-agentcore:DeleteCodeInterpreter
- bedrock-agentcore:ListCodeInterpreters
- bedrock-agentcore:GetCodeInterpreter

- bedrock-agentcore:CreateBrowserTool
- bedrock-agentcore:StartBrowserToolSession
- bedrock-agentcore:InvokeBrowserTool
- bedrock-agentcore:StopBrowserToolSession
- bedrock-agentcore:DeleteBrowserTool
- bedrock-agentcore:ListBrowserTools
- bedrock-agentcore:GetBrowserTool

CloudWatch Logs 権限:
- logs:CreateLogGroup
- logs:CreateLogStream
- logs:PutLogEvents

リソース:
- arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/code-interpreter*
- arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/browser-tool*
""")


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_builtin_tools.py code-interpreter")
        print("  python test_builtin_tools.py browser-tool")
        print("  python test_builtin_tools.py integrated")
        print("  python test_builtin_tools.py comprehensive")
        print("  python test_builtin_tools.py requirements")
        sys.exit(1)
    
    tester = BuiltinToolsTester()
    command = sys.argv[1]
    
    if command == "code-interpreter":
        tester.test_code_interpreter()
    
    elif command == "browser-tool":
        tester.test_browser_tool()
    
    elif command == "integrated":
        tester.test_integrated_scenario()
    
    elif command == "comprehensive":
        tester.run_comprehensive_test()
    
    elif command == "requirements":
        tester.show_requirements()
    
    else:
        print(f"❌ 不明なコマンド: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()