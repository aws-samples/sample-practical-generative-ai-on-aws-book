#!/usr/bin/env python3
"""
AgentCore Gateway 統合版カスタマーサポートエージェント
Gateway 経由で MCP ツールを使用する高機能なサポートエージェント
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from strands_agents import Agent, AgentConfig
from strands_agents.tools import MCPTool
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.identity import IdentityClient


class CustomerSupportAgentWithGateway:
    def __init__(self):
        """エージェントを初期化"""
        self.memory_client = None
        self.identity_client = None
        self.gateway_config = self._load_gateway_config()
        self.memory_config = self._load_memory_config()
        
        # エージェント設定
        self.agent_config = AgentConfig(
            name="CustomerSupportAgentWithGateway",
            description="AgentCore Gateway を使用した高機能カスタマーサポートエージェント",
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            system_prompt=self._get_system_prompt(),
            tools=self._setup_tools(),
            memory_config=self._get_memory_config()
        )
        
        self.agent = Agent(self.agent_config)
        print("✅ CustomerSupportAgentWithGateway が初期化されました")
    
    def _load_gateway_config(self) -> Dict[str, Any]:
        """Gateway設定を読み込み"""
        config_file = Path("gateway_config.json")
        if not config_file.exists():
            print("❌ gateway_config.json が見つかりません")
            print("   先に gateway_manager.py create を実行してください")
            raise FileNotFoundError("Gateway configuration not found")
        
        with open(config_file) as f:
            return json.load(f)
    
    def _load_memory_config(self) -> Dict[str, Any]:
        """Memory設定を読み込み"""
        config_file = Path("memory_config.json")
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return {}
    
    def _setup_tools(self) -> List[MCPTool]:
        """MCP ツールを設定"""
        tools = []
        
        try:
            # Gateway URL を使用して MCP ツールを作成
            gateway_url = self.gateway_config["gateway_url"]
            
            # 各ツールを個別に定義
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
            
            print(f"✅ {len(tools)} 個のMCPツールを設定しました")
            
        except Exception as e:
            print(f"⚠️  MCP ツール設定エラー: {e}")
            print("   Gateway なしで動作します")
        
        return tools
    
    def _get_memory_config(self) -> Optional[Dict[str, Any]]:
        """Memory設定を取得"""
        if not self.memory_config:
            return None
        
        return {
            "memory_id": self.memory_config.get("memory_id"),
            "actor_id": "{user_id}",  # 認証されたユーザーIDを使用
            "session_id": "{session_id}"  # セッションIDを使用
        }
    
    def _get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは親切で知識豊富なカスタマーサポートエージェントです。

## あなたの役割
- 顧客の質問や問題に対して、迅速で正確なサポートを提供する
- 利用可能なツールを活用して、具体的で有用な情報を提供する
- 常に丁寧で親しみやすい対応を心がける

## 利用可能なツール
1. **get_order_history**: 顧客の注文履歴を確認
2. **get_product_info**: 製品の詳細情報を検索
3. **check_shipping_status**: 配送状況を追跡
4. **get_support_faq**: よくある質問を検索

## 対応方針
- 顧客の質問内容に応じて、適切なツールを使用して情報を取得する
- 取得した情報を分かりやすく整理して回答する
- 必要に応じて追加の質問をして、より良いサポートを提供する
- 解決できない問題については、適切なエスカレーション先を案内する

## 注意事項
- 個人情報の取り扱いには十分注意する
- 不確実な情報は推測せず、確認できる範囲で回答する
- 顧客の満足度向上を最優先に考える

顧客からの質問をお待ちしています。どのようなことでお困りでしょうか？"""
    
    def _extract_user_info(self, request: Dict[str, Any]) -> Dict[str, str]:
        """リクエストからユーザー情報を抽出"""
        user_info = {
            "user_id": "anonymous",
            "session_id": "default_session",
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
        
        # セッションIDを生成（実際の実装では UUID を使用）
        import uuid
        user_info["session_id"] = str(uuid.uuid4())
        
        return user_info
    
    def _save_conversation_to_memory(self, user_info: Dict[str, str], prompt: str, response: str):
        """会話をMemoryに保存"""
        if not self.memory_config:
            return
        
        try:
            if not self.memory_client:
                self.memory_client = MemoryClient()
            
            # 会話イベントを作成
            event_data = {
                "type": "conversation",
                "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}}),
                "user_message": prompt,
                "assistant_response": response,
                "tools_used": [],  # 使用されたツールの情報
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


# AgentCore Runtime エントリーポイント
def lambda_handler(event, context):
    """AgentCore Runtime のエントリーポイント"""
    try:
        # エージェントを初期化
        agent = CustomerSupportAgentWithGateway()
        
        # リクエストを処理
        response = agent.process_request(event)
        
        return response
        
    except Exception as e:
        print(f"❌ Lambda handler エラー: {e}")
        return {
            "error": "システムエラー",
            "message": f"システムエラーが発生しました: {str(e)}"
        }


# ローカルテスト用
if __name__ == "__main__":
    import time
    
    # テスト用のリクエスト
    test_request = {
        "prompt": "注文履歴を確認したいです。顧客IDは customer_oauth_verified です。"
    }
    
    try:
        agent = CustomerSupportAgentWithGateway()
        response = agent.process_request(test_request)
        
        print("\n" + "="*50)
        print("テスト結果:")
        print("="*50)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")