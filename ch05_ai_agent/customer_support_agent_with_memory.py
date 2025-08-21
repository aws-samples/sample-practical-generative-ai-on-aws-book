from strands import Agent, tool
from strands_tools import calculator, current_time
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from memory_hook_provider import MemoryHook
import json
import time
import re
import hashlib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Memory 設定を読み込み
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

# Memory ID を取得
MEMORY_ID = load_memory_config()

SYSTEM_PROMPT = """
あなたは親切なカスタマーサポートアシスタントです。
顧客との過去の会話や問題解決履歴を覚えており、パーソナライズされたサポートを提供します。
過去の会話履歴がある場合は、それを参考にして適切な対応を行ってください。
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

app = BedrockAgentCoreApp()

def setup_agent_with_memory(actor_id: str, session_id: str):
    """Memory Hook を設定したエージェントを作成"""
    
    # Memory クライアントを初期化
    memory_client = MemoryClient()
    
    # Memory Hook を作成
    memory_hook = MemoryHook(
        memory_client=memory_client,
        memory_id=MEMORY_ID,
        actor_id=actor_id,
        session_id=session_id,
        # namespace_prefix=""  # デフォルト値を使用
    )
    
    # Hook を含むエージェントを作成
    agent = Agent(
        hooks=[memory_hook],  # Memory Hook を直接渡す
        tools=[
            calculator,
            current_time,
            get_customer_id,
            get_orders,
            get_knowledge_base_info
        ],
        system_prompt=SYSTEM_PROMPT
    )
    
    return agent, memory_client

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "プロンプトが見つかりません")
    
    # メールアドレスからアクターIDを生成
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_message)
    
    if email_match:
        email = email_match.group()
        actor_id = f"customer_{hashlib.md5(email.encode()).hexdigest()[:8]}"
        session_id = f"session_{int(time.time())}"
        
        logger.info(f"顧客を識別: {email} -> {actor_id}")
        
        # Memory Hook 付きエージェントをセットアップ
        agent, memory_client = setup_agent_with_memory(actor_id, session_id)
        
        # エージェントを実行（Memory Hook が自動的に処理）
        response = agent(user_message)
        
        return {
            "result": str(response.message if hasattr(response, 'message') else response),
            "metadata": {
                "actor_id": actor_id,
                "session_id": session_id,
                "email": email
            }
        }
    else:
        # メールアドレスがない場合は Memory なしで処理
        logger.info("メールアドレスが見つかりません。Memory なしで処理します。")
        
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[calculator, current_time, get_customer_id, get_orders, get_knowledge_base_info]
        )
        
        response = agent(user_message)
        
        return {
            "result": str(response.message if hasattr(response, 'message') else response)
        }

if __name__ == "__main__":
    app.run()