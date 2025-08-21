#!/usr/bin/env python3
"""
AgentCore Built-in Tools 統合版カスタマーサポートエージェント
Code Interpreter と Browser Tool を使用した高度な分析・自動化機能
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from strands_agents import Agent, AgentConfig
from strands_agents.tools import MCPTool
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.identity import IdentityClient
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.tools.browser_tool_client import BrowserTool


class CustomerSupportAgentWithTools:
    def __init__(self):
        """エージェントを初期化"""
        self.memory_client = None
        self.identity_client = None
        self.code_interpreter = None
        self.browser_tool = None
        
        # 設定を読み込み
        self.gateway_config = self._load_gateway_config()
        self.memory_config = self._load_memory_config()
        
        # Built-in Tools を初期化
        self._initialize_builtin_tools()
        
        # エージェント設定
        self.agent_config = AgentConfig(
            name="CustomerSupportAgentWithTools",
            description="Code Interpreter と Browser Tool を使用した高度なカスタマーサポートエージェント",
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            system_prompt=self._get_system_prompt(),
            tools=self._setup_tools(),
            memory_config=self._get_memory_config()
        )
        
        self.agent = Agent(self.agent_config)
        print("✅ CustomerSupportAgentWithTools が初期化されました")
    
    def _load_gateway_config(self) -> Dict[str, Any]:
        """Gateway設定を読み込み"""
        config_file = Path("gateway_config.json")
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return {}
    
    def _load_memory_config(self) -> Dict[str, Any]:
        """Memory設定を読み込み"""
        config_file = Path("memory_config.json")
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return {}
    
    def _initialize_builtin_tools(self):
        """Built-in Tools を初期化"""
        try:
            # Code Interpreter を初期化
            self.code_interpreter = CodeInterpreter('us-east-1')
            print("✅ Code Interpreter を初期化しました")
            
            # Browser Tool を初期化
            self.browser_tool = BrowserTool('us-east-1')
            print("✅ Browser Tool を初期化しました")
            
        except Exception as e:
            print(f"⚠️  Built-in Tools 初期化エラー: {e}")
            print("   Built-in Tools なしで動作します")
    
    def _setup_tools(self) -> List:
        """ツールを設定"""
        tools = []
        
        # Gateway MCP ツールを追加
        if self.gateway_config:
            try:
                gateway_url = self.gateway_config["gateway_url"]
                
                tool_definitions = [
                    {
                        "name": "get_order_history",
                        "description": "顧客の注文履歴を取得します",
                        "gateway_url": gateway_url
                    },
                    {
                        "name": "get_product_info", 
                        "description": "製品情報を検索します",
                        "gateway_url": gateway_url
                    },
                    {
                        "name": "check_shipping_status",
                        "description": "配送状況を確認します",
                        "gateway_url": gateway_url
                    },
                    {
                        "name": "get_support_faq",
                        "description": "サポートFAQを検索します",
                        "gateway_url": gateway_url
                    }
                ]
                
                for tool_def in tool_definitions:
                    mcp_tool = MCPTool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        server_url=tool_def["gateway_url"]
                    )
                    tools.append(mcp_tool)
                
                print(f"✅ {len(tool_definitions)} 個のMCPツールを設定しました")
                
            except Exception as e:
                print(f"⚠️  MCP ツール設定エラー: {e}")
        
        # Built-in Tools を追加（カスタムツールとして）
        if self.code_interpreter:
            tools.append(self._create_code_interpreter_tool())
        
        if self.browser_tool:
            tools.append(self._create_browser_tool())
        
        return tools
    
    def _create_code_interpreter_tool(self):
        """Code Interpreter ツールを作成"""
        from strands_agents.tools import Tool
        
        def execute_code(code: str, description: str = "") -> str:
            """Python コードを安全な環境で実行"""
            try:
                # セッションを開始（まだ開始していない場合）
                if not hasattr(self.code_interpreter, '_session_active'):
                    self.code_interpreter.start(session_timeout_seconds=1200)
                    self.code_interpreter._session_active = True
                
                # コードを実行
                response = self.code_interpreter.invoke("executeCode", {
                    "code": code,
                    "description": description
                })
                
                return json.dumps(response, ensure_ascii=False, indent=2)
                
            except Exception as e:
                return f"❌ コード実行エラー: {str(e)}"
        
        return Tool(
            name="execute_code",
            description="Python コードを安全な環境で実行します。データ分析、計算、グラフ作成などに使用できます。",
            func=execute_code
        )
    
    def _create_browser_tool(self):
        """Browser Tool を作成"""
        from strands_agents.tools import Tool
        
        def browse_web(action: str, target: str = "", text: str = "") -> str:
            """Web ブラウザを操作"""
            try:
                # セッションを開始（まだ開始していない場合）
                if not hasattr(self.browser_tool, '_session_active'):
                    self.browser_tool.start()
                    self.browser_tool._session_active = True
                
                # ブラウザアクションを実行
                if action == "navigate":
                    response = self.browser_tool.navigate(target)
                elif action == "click":
                    response = self.browser_tool.click(target)
                elif action == "type":
                    response = self.browser_tool.type(target, text)
                elif action == "screenshot":
                    response = self.browser_tool.screenshot()
                else:
                    return f"❌ 不明なアクション: {action}"
                
                return json.dumps(response, ensure_ascii=False, indent=2)
                
            except Exception as e:
                return f"❌ ブラウザ操作エラー: {str(e)}"
        
        return Tool(
            name="browse_web",
            description="Web ブラウザを操作します。ページの閲覧、クリック、テキスト入力、スクリーンショット取得などができます。",
            func=browse_web
        )
    
    def _get_memory_config(self) -> Optional[Dict[str, Any]]:
        """Memory設定を取得"""
        if not self.memory_config:
            return None
        
        return {
            "memory_id": self.memory_config.get("memory_id"),
            "actor_id": "{user_id}",
            "session_id": "{session_id}"
        }
    
    def _get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは高度な分析・自動化機能を持つカスタマーサポートエージェントです。

## あなたの役割
- 顧客の質問や問題に対して、迅速で正確なサポートを提供する
- 複雑な計算やデータ分析が必要な場合は Code Interpreter を使用する
- Web サイトの情報確認や操作が必要な場合は Browser Tool を使用する
- 利用可能なツールを適切に組み合わせて、包括的なサポートを提供する

## 利用可能なツール

### 基本ツール
1. **get_order_history**: 顧客の注文履歴を確認
2. **get_product_info**: 製品の詳細情報を検索
3. **check_shipping_status**: 配送状況を追跡
4. **get_support_faq**: よくある質問を検索

### 高度なツール
5. **execute_code**: Python コードを実行して計算・分析・グラフ作成
6. **browse_web**: Web ブラウザを操作してサイト情報を確認

## 対応方針
- 顧客の質問内容に応じて、適切なツールを選択・組み合わせて使用する
- 複雑な計算や分析が必要な場合は、Code Interpreter でコードを実行する
- Web サイトの最新情報確認が必要な場合は、Browser Tool を使用する
- 取得した情報を分かりやすく整理して回答する
- 必要に応じて視覚的な資料（グラフ、チャートなど）を作成する

## 使用例

### Code Interpreter の使用例
- 売上データの分析とグラフ作成
- 配送コストの計算
- 在庫予測の計算
- 顧客満足度の統計分析

### Browser Tool の使用例
- 製品の最新価格確認
- 競合他社の情報調査
- 配送業者のサイトでの追跡情報確認
- オンラインマニュアルの参照

## 注意事項
- 個人情報の取り扱いには十分注意する
- コード実行時は安全性を最優先に考える
- Web ブラウザ操作時は適切なサイトのみアクセスする
- 不確実な情報は推測せず、確認できる範囲で回答する

顧客からの質問をお待ちしています。どのようなことでお困りでしょうか？"""
    
    def _extract_user_info(self, request: Dict[str, Any]) -> Dict[str, str]:
        """リクエストからユーザー情報を抽出"""
        user_info = {
            "user_id": "anonymous",
            "session_id": str(uuid.uuid4()),
            "user_name": "ゲストユーザー",
            "user_email": "guest@example.com",
            "authenticated": False
        }
        
        # AgentCore Identity からの認証情報を確認
        if hasattr(request, 'context') and request.context:
            context = request.context
            if hasattr(context, 'identity') and context.identity:
                identity = context.identity
                user_info.update({
                    "user_id": getattr(identity, 'user_id', 'authenticated_user'),
                    "user_name": getattr(identity, 'name', 'OAuth認証済みユーザー'),
                    "user_email": getattr(identity, 'email', 'oauth-verified@example.com'),
                    "authenticated": True
                })
        
        return user_info
    
    def _save_conversation_to_memory(self, user_info: Dict[str, str], prompt: str, response: str):
        """会話をMemoryに保存"""
        if not self.memory_config:
            return
        
        try:
            if not self.memory_client:
                self.memory_client = MemoryClient()
            
            import time
            
            # 会話イベントを作成
            event_data = {
                "type": "conversation",
                "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}}),
                "user_message": prompt,
                "assistant_response": response,
                "tools_used": ["code_interpreter", "browser_tool"],
                "session_metadata": {
                    "user_name": user_info["user_name"],
                    "user_email": user_info["user_email"],
                    "authenticated": user_info["authenticated"]
                }
            }
            
            # Memoryにイベントを保存
            self.memory_client.create_event(
                memory_id=self.memory_config["memory_id"],
                actor_id=user_info["user_id"],
                session_id=user_info["session_id"],
                event_data=event_data
            )
            
            print(f"💾 会話をMemoryに保存しました (Actor: {user_info['user_id']})")
            
        except Exception as e:
            print(f"⚠️  Memory保存エラー: {e}")
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """リクエストを処理"""
        try:
            prompt = request.get("prompt", "")
            if not prompt:
                return {
                    "error": "プロンプトが指定されていません",
                    "message": "prompt パラメータを指定してください"
                }
            
            # ユーザー情報を抽出
            user_info = self._extract_user_info(request)
            
            print(f"🔍 リクエスト処理開始")
            print(f"   ユーザー: {user_info['user_name']} ({user_info['user_id']})")
            print(f"   認証状態: {user_info['authenticated']}")
            print(f"   プロンプト: {prompt[:100]}...")
            
            # エージェントでリクエストを処理
            response = self.agent.invoke(
                prompt=prompt,
                context={
                    "user_id": user_info["user_id"],
                    "session_id": user_info["session_id"],
                    "user_name": user_info["user_name"],
                    "user_email": user_info["user_email"]
                }
            )
            
            # レスポンスを整形
            if hasattr(response, 'content'):
                result_content = response.content
            elif isinstance(response, dict):
                result_content = response.get('content', str(response))
            else:
                result_content = str(response)
            
            # Memoryに保存
            self._save_conversation_to_memory(user_info, prompt, result_content)
            
            return {
                "result": result_content,
                "metadata": user_info
            }
            
        except Exception as e:
            error_message = f"エージェント実行エラー: {str(e)}"
            print(f"❌ {error_message}")
            
            return {
                "error": "エージェント実行エラー",
                "message": f"処理中にエラーが発生しました: {str(e)}"
            }
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            if self.code_interpreter and hasattr(self.code_interpreter, '_session_active'):
                self.code_interpreter.stop()
                print("✅ Code Interpreter セッションを停止しました")
            
            if self.browser_tool and hasattr(self.browser_tool, '_session_active'):
                self.browser_tool.stop()
                print("✅ Browser Tool セッションを停止しました")
                
        except Exception as e:
            print(f"⚠️  クリーンアップエラー: {e}")


# AgentCore Runtime エントリーポイント
def lambda_handler(event, context):
    """AgentCore Runtime のエントリーポイント"""
    agent = None
    try:
        # エージェントを初期化
        agent = CustomerSupportAgentWithTools()
        
        # リクエストを処理
        response = agent.process_request(event)
        
        return response
        
    except Exception as e:
        print(f"❌ Lambda handler エラー: {e}")
        return {
            "error": "システムエラー",
            "message": f"システムエラーが発生しました: {str(e)}"
        }
    finally:
        # クリーンアップ
        if agent:
            agent.cleanup()


# ローカルテスト用
if __name__ == "__main__":
    # テスト用のリクエスト
    test_requests = [
        {
            "prompt": "過去3ヶ月の売上データを分析して、グラフで可視化してください。売上データ: [100000, 120000, 95000, 110000, 130000, 125000, 140000, 135000, 150000, 145000, 160000, 155000]"
        },
        {
            "prompt": "Amazon の公式サイトで「Echo Dot」の価格を確認してください。"
        },
        {
            "prompt": "顧客ID customer_oauth_verified の注文履歴を確認して、配送状況も調べてください。"
        }
    ]
    
    agent = None
    try:
        agent = CustomerSupportAgentWithTools()
        
        for i, test_request in enumerate(test_requests, 1):
            print(f"\n{'='*60}")
            print(f"テスト {i}: {test_request['prompt'][:50]}...")
            print("="*60)
            
            response = agent.process_request(test_request)
            print(json.dumps(response, ensure_ascii=False, indent=2))
            
            # テスト間の待機
            import time
            time.sleep(2)
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
    finally:
        if agent:
            agent.cleanup()