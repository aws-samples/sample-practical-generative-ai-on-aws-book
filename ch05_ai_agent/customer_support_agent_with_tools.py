#!/usr/bin/env python3
"""
AgentCore Built-in Tools 統合版カスタマーサポートエージェント
Code Interpreter と Browser Tool を使用した高度な分析・自動化機能
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.tools.browser_client import browser_session

# AgentCore アプリケーションを初期化
app = BedrockAgentCoreApp()

# エージェントを初期化
agent = Agent()

# グローバル変数
memory_client = None
memory_config = {}
gateway_config = {}

def load_config():
    """設定ファイルを読み込み"""
    global memory_config, gateway_config
    
    # Memory設定を読み込み
    memory_file = Path("memory_config.json")
    if memory_file.exists():
        with open(memory_file) as f:
            memory_config = json.load(f)
    
    # Gateway設定を読み込み
    gateway_file = Path("gateway_config.json")
    if gateway_file.exists():
        with open(gateway_file) as f:
            gateway_config = json.load(f)

def execute_code_with_interpreter(code: str) -> str:
    """Code Interpreter でコードを実行"""
    try:
        code_interpreter = CodeInterpreter('us-east-1')
        code_interpreter.start(session_timeout_seconds=600)
        
        response = code_interpreter.invoke("executeCode", {
            "code": code,
            "language": "python"
        })
        
        # ストリームレスポンスを処理
        result = {"status": "success", "output": ""}
        
        if "stream" in response:
            for event in response["stream"]:
                if "result" in event:
                    if "structuredContent" in event["result"]:
                        stdout = event["result"]["structuredContent"].get("stdout", "")
                        stderr = event["result"]["structuredContent"].get("stderr", "")
                        exit_code = event["result"]["structuredContent"].get("exitCode", 0)
                        
                        result["output"] = stdout
                        if stderr:
                            result["stderr"] = stderr
                        result["exit_code"] = exit_code
                    break
        
        code_interpreter.stop()
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"❌ Code Interpreter エラー: {str(e)}"

def browse_web_with_browser_tool(url: str) -> str:
    """Browser Tool でWebページを閲覧"""
    try:
        with browser_session('us-east-1') as client:
            ws_url, headers = client.generate_ws_headers()
            
            result = {
                "status": "success",
                "message": f"Browser セッションが正常に作成されました",
                "url": url,
                "session_info": {
                    "ws_url_available": bool(ws_url),
                    "headers_available": bool(headers),
                    "region": "us-east-1"
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return f"❌ Browser Tool エラー: {str(e)}"

def save_conversation_to_memory(user_id: str, session_id: str, prompt: str, response: str):
    """会話をMemoryに保存"""
    if not memory_config:
        return
    
    try:
        global memory_client
        if not memory_client:
            memory_client = MemoryClient()
        
        import time
        
        # 会話イベントを作成
        event_data = {
            "type": "conversation",
            "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}}),
            "user_message": prompt,
            "assistant_response": response,
            "tools_used": ["code_interpreter", "browser_tool"],
            "session_metadata": {
                "user_id": user_id,
                "session_id": session_id
            }
        }
        
        # Memoryにイベントを保存
        memory_client.create_event(
            memory_id=memory_config["memory_id"],
            actor_id=user_id,
            session_id=session_id,
            event_data=event_data
        )
        
        print(f"💾 会話をMemoryに保存しました (Actor: {user_id})")
        
    except Exception as e:
        print(f"⚠️  Memory保存エラー: {e}")

@app.entrypoint
async def agent_invocation(payload):
    """エージェント呼び出しのエントリーポイント"""
    
    # 設定を読み込み
    load_config()
    
    # ユーザー情報を抽出
    user_id = payload.get("user_id", "anonymous")
    session_id = payload.get("session_id", str(uuid.uuid4()))
    user_message = payload.get("prompt", "No prompt found in input, please guide customer to create a json payload with prompt key")
    
    print(f"🔍 リクエスト処理開始")
    print(f"   ユーザー: {user_id}")
    print(f"   セッション: {session_id}")
    print(f"   プロンプト: {user_message[:100]}...")
    
    # システムプロンプトを設定
    system_prompt = """あなたは高度な分析・自動化機能を持つカスタマーサポートエージェントです。

## あなたの役割
- 顧客の質問や問題に対して、迅速で正確なサポートを提供する
- 複雑な計算やデータ分析が必要な場合は Code Interpreter を使用する
- Web サイトの情報確認が必要な場合は Browser Tool を使用する

## 利用可能なツール

### Code Interpreter の使用
複雑な計算、データ分析、グラフ作成が必要な場合は、以下の形式でコードを実行してください：

```python
# 例：売上データの分析
import pandas as pd
import matplotlib.pyplot as plt

data = [100000, 120000, 95000, 110000, 130000, 125000]
print(f"平均売上: {sum(data)/len(data):,.0f}円")
```

### Browser Tool の使用
Web サイトの情報確認が必要な場合は、URLを指定してブラウザセッションを作成できます。

## 対応方針
- 顧客の質問内容に応じて、適切なツールを選択して使用する
- 取得した情報を分かりやすく整理して回答する
- 必要に応じて視覚的な資料（グラフ、チャートなど）を作成する

顧客からの質問をお待ちしています。どのようなことでお困りでしょうか？"""
    
    # エージェントにシステムプロンプトを設定
    agent.system_prompt = system_prompt
    
    # エージェントのストリーミング処理
    stream = agent.stream_async(user_message)
    
    response_content = ""
    
    async for event in stream:
        print(f"📤 Event: {event}")
        
        # レスポンス内容を収集
        if hasattr(event, 'content'):
            response_content += str(event.content)
        elif isinstance(event, dict) and 'content' in event:
            response_content += str(event['content'])
        elif isinstance(event, str):
            response_content += event
        
        # Code Interpreter の使用を検出
        if "python" in user_message.lower() or "計算" in user_message or "分析" in user_message or "グラフ" in user_message:
            if "```python" in user_message or "コード" in user_message:
                # ユーザーがコードを含む場合、Code Interpreter で実行
                code_start = user_message.find("```python")
                if code_start != -1:
                    code_end = user_message.find("```", code_start + 9)
                    if code_end != -1:
                        code = user_message[code_start + 9:code_end].strip()
                        code_result = execute_code_with_interpreter(code)
                        yield {"type": "code_execution", "result": code_result}
        
        # Browser Tool の使用を検出
        if "http" in user_message.lower() or "サイト" in user_message or "ブラウザ" in user_message:
            # URLを抽出してブラウザセッションを作成
            import re
            urls = re.findall(r'https?://[^\s]+', user_message)
            if urls:
                browser_result = browse_web_with_browser_tool(urls[0])
                yield {"type": "browser_session", "result": browser_result}
        
        yield event
    
    # 会話をMemoryに保存
    if response_content:
        save_conversation_to_memory(user_id, session_id, user_message, response_content)

# ローカルテスト用
if __name__ == "__main__":
    # テスト用のペイロード
    test_payload = {
        "prompt": "過去6ヶ月の売上データ [100000, 120000, 95000, 110000, 130000, 125000] を分析して、平均と最大値を計算してください。",
        "user_id": "test_user",
        "session_id": "test_session_123"
    }
    
    print("🧪 ローカルテスト開始")
    print("=" * 50)
    
    # 非同期関数をテスト
    import asyncio
    
    async def test_agent():
        async for event in agent_invocation(test_payload):
            print(f"📥 Event: {event}")
    
    # テスト実行
    try:
        asyncio.run(test_agent())
        print("\n✅ ローカルテスト完了")
    except Exception as e:
        print(f"❌ テストエラー: {e}")
    
    # AgentCore アプリケーションを起動（本番環境）
    # app.run()