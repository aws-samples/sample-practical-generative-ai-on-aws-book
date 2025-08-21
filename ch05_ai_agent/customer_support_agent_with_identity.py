#!/usr/bin/env python3
"""
Customer Support Agent with Identity
AgentCore Identity による認証・認可を統合したカスタマーサポートエージェント
"""

from strands import Agent, tool
from strands_tools import calculator, current_time
from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext, RequestContext
from bedrock_agentcore.memory import MemoryClient
from memory_hook_provider import MemoryHook
import json
import time
import re
import hashlib
import os
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_memory_config():
    """Memory 設定を読み込み"""
    if os.path.exists("memory_config.json"):
        with open("memory_config.json", "r") as f:
            config = json.load(f)
            return config.get("memory_id")
    else:
        raise ValueError(
            "memory_config.json が見つかりません。"
            "先に setup_memory.py を実行してください。"
        )

def load_cognito_config():
    """Cognito 設定を読み込み"""
    if os.path.exists("cognito_config.json"):
        with open("cognito_config.json", "r") as f:
            return json.load(f)
    else:
        raise ValueError(
            "cognito_config.json が見つかりません。"
            "先に cognito_setup.py setup を実行してください。"
        )

def get_ssm_parameter(name: str, with_decryption: bool = True) -> Optional[str]:
    """SSMパラメータから値を取得"""
    import boto3
    from botocore.exceptions import ClientError
    
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except ClientError:
        return None

# 設定を読み込み
MEMORY_ID = load_memory_config()
COGNITO_CONFIG = load_cognito_config()

SYSTEM_PROMPT = """
あなたは親切なカスタマーサポートアシスタントです。
認証されたユーザーとの過去の会話や問題解決履歴を覚えており、パーソナライズされたサポートを提供します。

重要な注意事項:
- ユーザーは既に認証済みです
- 過去の会話履歴がある場合は、それを参考にして適切な対応を行ってください
- セキュリティ上重要な操作の場合は、追加の確認を求めてください
- 個人情報は適切に保護し、必要以上に表示しないでください
"""

# 既存のツール（Step 1から継承）
@tool
def get_customer_id(email_address: str):
    """メールアドレスから顧客IDを取得します"""
    if email_address == "me@example.net":
        return {"customer_id": 123}
    else:
        return {"message": "顧客が見つかりません"}

@tool  
def get_orders(customer_id: int):
    """顧客IDから注文履歴を取得します"""
    if customer_id == 123:
        return [{
            "order_id": 1234,
            "items": ["スマートフォン", "スマートフォン USB-C 充電器", "スマートフォン 黒色カバー"],
            "date": "20250607"
        }]
    else:
        return {"message": "注文が見つかりません"}

@tool
def get_knowledge_base_info(topic: str):
    """トピックに関する知識ベース情報を取得します"""
    kb_info = []
    if "スマートフォン" in topic:
        if "カバー" in topic:
            kb_info.append("カバーを装着するには、まず底部を挿入し、次に背面から上部まで押し込みます。")
        if "充電器" in topic:
            kb_info.append("入力: 100-240V AC、50/60Hz")
            kb_info.append("US/UK/EU プラグアダプター付属")
    return kb_info if kb_info else {"message": "情報が見つかりません"}

@tool
def get_user_profile(user_id: str):
    """認証されたユーザーのプロファイル情報を取得します（模擬）"""
    # 実際の実装では、認証されたユーザーIDを使用してデータベースから情報を取得
    profiles = {
        "customer_oauth_verified": {
            "name": "OAuth認証ユーザー",
            "email": "oauth-verified@example.com",
            "membership_level": "プレミアム",
            "registration_date": "2024-01-15",
            "preferred_language": "日本語"
        }
    }
    
    return profiles.get(user_id, {"message": "ユーザープロファイルが見つかりません"})

@tool
def check_access_permissions(user_id: str, resource: str):
    """ユーザーのリソースアクセス権限をチェックします（模擬）"""
    # 実際の実装では、Identity Clientを使用して権限をチェック
    permissions = {
        "customer_oauth_verified": {
            "order_history": True,
            "billing_info": True,
            "support_tickets": True,
            "admin_functions": False
        }
    }
    
    user_permissions = permissions.get(user_id, {})
    has_access = user_permissions.get(resource, False)
    
    return {
        "user_id": user_id,
        "resource": resource,
        "has_access": has_access,
        "permissions": user_permissions
    }

class IdentityManager:
    """Identity管理クラス"""
    
    def __init__(self):
        self.cognito_provider = get_ssm_parameter("/app/customersupport/agentcore/cognito_provider")
        
    def validate_token(self, access_token: str) -> Dict[str, Any]:
        """アクセストークンを検証してユーザー情報を取得"""
        try:
            # AgentCore Runtime環境では、トークン検証は自動的に行われる
            # ここでは開発・テスト用の模擬実装
            if access_token == COGNITO_CONFIG.get("test_access_token"):
                return {
                    "valid": True,
                    "user_id": "customer_12345678",
                    "email": "me@example.net",
                    "name": "田中太郎",
                    "sub": "12345678-1234-1234-1234-123456789012"
                }
            else:
                return {"valid": False, "error": "Invalid token"}
                
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {"valid": False, "error": str(e)}
    
    def get_user_permissions(self, user_id: str) -> Dict[str, bool]:
        """ユーザーの権限を取得"""
        # 実際の実装では、AgentCore Identity を使用して権限を取得
        default_permissions = {
            "read_orders": True,
            "read_profile": True,
            "update_profile": True,
            "create_support_ticket": True,
            "admin_access": False
        }
        
        return default_permissions

def setup_agent_with_identity_and_memory(user_info: Dict[str, Any], session_id: str):
    """Identity と Memory Hook を設定したエージェントを作成"""
    
    user_id = user_info["user_id"]
    
    # Memory クライアントを初期化
    memory_client = MemoryClient()
    
    # Memory Hook を作成
    memory_hook = MemoryHook(
        memory_client=memory_client,
        memory_id=MEMORY_ID,
        actor_id=user_id,
        session_id=session_id,
        namespace_prefix="support/user"
    )
    
    # Identity情報を含むシステムプロンプトを作成
    identity_prompt = f"""
{SYSTEM_PROMPT}

現在認証されているユーザー情報:
- ユーザーID: {user_id}
- 名前: {user_info.get('name', 'N/A')}
- メールアドレス: {user_info.get('email', 'N/A')}

この情報を参考にして、パーソナライズされたサポートを提供してください。
"""
    
    # Hook を含むエージェントを作成
    agent = Agent(
        hooks=[memory_hook],
        tools=[
            calculator,
            current_time,
            get_customer_id,
            get_orders,
            get_knowledge_base_info,
            get_user_profile,
            check_access_permissions
        ],
        system_prompt=identity_prompt
    )
    
    return agent, memory_client

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context=None):
    """統合エントリーポイント - Identity認証対応"""
    user_message = payload.get("prompt", "プロンプトが見つかりません")
    
    # セッションIDを取得
    session_id = None
    if context:
        session_id = getattr(context, 'session_id', None)
        logger.info(f"Context情報: session_id={session_id}")
    
    if not session_id:
        session_id = f"session_{int(time.time())}"
    
    # OAuth Authorizerが設定されている場合、エントリーポイントに到達 = 認証済み
    # クラウド環境では認証が自動的に処理される
    is_authenticated = True
    user_info = {
        "user_id": "customer_oauth_verified",
        "email": "oauth-verified@example.com",
        "name": "OAuth認証済みユーザー",
        "authenticated_via": "oauth_authorizer"
    }
    logger.info("OAuth Authorizer経由での認証を確認")
    
    user_id = user_info["user_id"]
    
    try:
        # Identity と Memory Hook 付きエージェントをセットアップ
        agent, memory_client = setup_agent_with_identity_and_memory(user_info, session_id)
        
        # エージェントを実行（Memory Hook が自動的に処理）
        response = agent(user_message)
        
        return {
            "result": str(response.message if hasattr(response, 'message') else response),
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "user_name": user_info.get("name"),
                "user_email": user_info.get("email"),
                "authenticated": True
            }
        }
        
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        return {
            "error": "エージェント実行エラー",
            "message": f"処理中にエラーが発生しました: {str(e)}"
        }

if __name__ == "__main__":
    app.run()