#!/usr/bin/env python3
"""
Observability 機能を統合したカスタマーサポートエージェント
OpenTelemetry (OTEL) インストルメンテーション付き
"""

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

# OpenTelemetry インポート
from opentelemetry import trace, baggage, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.context import attach
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# 環境変数設定（OTEL有効化）
os.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"
os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"
os.environ["AGENT_OBSERVABILITY_ENABLED"] = "true"

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenTelemetry ログインストルメンテーション
LoggingInstrumentor().instrument(set_logging_format=True)

# トレーサーとメーターを取得
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# カスタムメトリクス定義
customer_requests_counter = meter.create_counter(
    "customer_support_requests_total",
    description="Total number of customer support requests",
    unit="1"
)

response_time_histogram = meter.create_histogram(
    "customer_support_response_time_seconds",
    description="Response time for customer support requests",
    unit="s"
)

memory_operations_counter = meter.create_counter(
    "memory_operations_total",
    description="Total number of memory operations",
    unit="1"
)

tool_usage_counter = meter.create_counter(
    "tool_usage_total",
    description="Total number of tool usages",
    unit="1"
)

# Memory 設定を読み込み
def load_memory_config():
    """Memory 設定を読み込み"""
    if os.path.exists("memory_config.json"):
        with open("memory_config.json", "r") as f:
            config = json.load(f)
            return config.get("memory_id")
    else:
        logger.warning("memory_config.json が見つかりません。Memory機能なしで動作します。")
        return None

# Memory ID を取得
MEMORY_ID = load_memory_config()

SYSTEM_PROMPT = """
あなたは親切なカスタマーサポートアシスタントです。
顧客との過去の会話や問題解決履歴を覚えており、パーソナライズされたサポートを提供します。
過去の会話履歴がある場合は、それを参考にして適切な対応を行ってください。

すべての操作は詳細にログ記録され、パフォーマンス監視されています。
"""

# 既存のツール（Step 1から継承）+ Observability 機能付き
@tool
def get_customer_id(email_address: str):
    """メールアドレスから顧客IDを取得します"""
    with tracer.start_as_current_span("get_customer_id") as span:
        span.set_attribute("email_address", email_address)
        tool_usage_counter.add(1, {"tool": "get_customer_id"})
        
        logger.info(f"顧客ID検索: {email_address}")
        
        if email_address == "me@example.net":
            result = {"customer_id": 123}
            span.set_attribute("customer_found", True)
            span.set_attribute("customer_id", 123)
            logger.info(f"顧客が見つかりました: ID=123")
        else:
            result = {"message": "顧客が見つかりません"}
            span.set_attribute("customer_found", False)
            logger.warning(f"顧客が見つかりません: {email_address}")
        
        span.set_status(Status(StatusCode.OK))
        return result

@tool  
def get_orders(customer_id: int):
    """顧客IDから注文履歴を取得します"""
    with tracer.start_as_current_span("get_orders") as span:
        span.set_attribute("customer_id", customer_id)
        tool_usage_counter.add(1, {"tool": "get_orders"})
        
        logger.info(f"注文履歴検索: customer_id={customer_id}")
        
        if customer_id == 123:
            result = [{
                "order_id": 1234,
                "items": ["スマートフォン", "スマートフォン USB-C 充電器", "スマートフォン 黒色カバー"],
                "date": "20250607"
            }]
            span.set_attribute("orders_found", True)
            span.set_attribute("order_count", 1)
            logger.info(f"注文履歴が見つかりました: {len(result)}件")
        else:
            result = {"message": "注文が見つかりません"}
            span.set_attribute("orders_found", False)
            logger.warning(f"注文が見つかりません: customer_id={customer_id}")
        
        span.set_status(Status(StatusCode.OK))
        return result

@tool
def get_knowledge_base_info(topic: str):
    """トピックに関する知識ベース情報を取得します"""
    with tracer.start_as_current_span("get_knowledge_base_info") as span:
        span.set_attribute("topic", topic)
        tool_usage_counter.add(1, {"tool": "get_knowledge_base_info"})
        
        logger.info(f"知識ベース検索: {topic}")
        
        kb_info = []
        if "スマートフォン" in topic:
            if "カバー" in topic:
                kb_info.append("カバーを装着するには、まず底部を挿入し、次に背面から上部まで押し込みます。")
                kb_info.append("カバーを取り外すには、カバーの上部と下部を同時に押してください。")
            if "充電器" in topic:
                kb_info.append("入力: 100-240V AC、50/60Hz")
                kb_info.append("US/UK/EU プラグアダプター付属")
        
        if kb_info:
            result = kb_info
            span.set_attribute("info_found", True)
            span.set_attribute("info_count", len(kb_info))
            logger.info(f"知識ベース情報が見つかりました: {len(kb_info)}件")
        else:
            result = {"message": "情報が見つかりません"}
            span.set_attribute("info_found", False)
            logger.warning(f"知識ベース情報が見つかりません: {topic}")
        
        span.set_status(Status(StatusCode.OK))
        return result

app = BedrockAgentCoreApp()

def setup_agent_with_memory_and_observability(actor_id: str, session_id: str):
    """Memory Hook と Observability を設定したエージェントを作成"""
    
    with tracer.start_as_current_span("setup_agent") as span:
        span.set_attribute("actor_id", actor_id)
        span.set_attribute("session_id", session_id)
        
        logger.info(f"エージェント初期化: actor_id={actor_id}, session_id={session_id}")
        
        if MEMORY_ID:
            # Memory クライアントを初期化
            memory_client = MemoryClient()
            
            # Memory Hook を作成
            memory_hook = MemoryHook(
                memory_client=memory_client,
                memory_id=MEMORY_ID,
                actor_id=actor_id,
                session_id=session_id
            )
            
            # Hook を含むエージェントを作成
            agent = Agent(
                hooks=[memory_hook],  # Memory Hook を追加
                tools=[
                    calculator,
                    current_time,
                    get_customer_id,
                    get_orders,
                    get_knowledge_base_info
                ],
                system_prompt=SYSTEM_PROMPT
            )
            
            span.set_attribute("memory_enabled", True)
            memory_operations_counter.add(1, {"operation": "agent_setup"})
            logger.info("Memory機能付きエージェントを作成しました")
            
        else:
            # Memory なしエージェント
            agent = Agent(
                system_prompt=SYSTEM_PROMPT,
                tools=[
                    calculator, 
                    current_time, 
                    get_customer_id, 
                    get_orders, 
                    get_knowledge_base_info
                ]
            )
            
            span.set_attribute("memory_enabled", False)
            logger.info("Memory機能なしエージェントを作成しました")
        
        span.set_status(Status(StatusCode.OK))
        return agent, memory_client if MEMORY_ID else None

@app.entrypoint
def invoke(payload):
    """エージェント呼び出しのハンドラー（Observability 機能付き）"""
    
    # リクエスト開始時刻を記録
    start_time = time.time()
    
    with tracer.start_as_current_span("customer_support_request") as span:
        try:
            user_message = payload.get("prompt", "プロンプトが見つかりません")
            span.set_attribute("user_message_length", len(user_message))
            
            # カスタムメトリクス更新
            customer_requests_counter.add(1)
            
            # メールアドレスからアクターIDを生成
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_message)
            
            if email_match:
                email = email_match.group()
                actor_id = f"customer_{hashlib.md5(email.encode()).hexdigest()[:8]}"
                session_id = f"session_{int(time.time())}"
                
                # セッションIDをバゲージに設定
                ctx = baggage.set_baggage("session.id", session_id)
                attach(ctx)
                
                span.set_attribute("email", email)
                span.set_attribute("actor_id", actor_id)
                span.set_attribute("session_id", session_id)
                span.set_attribute("customer_identified", True)
                
                logger.info(f"顧客を識別: {email} -> {actor_id}")
                
                # Memory Hook 付きエージェントをセットアップ
                agent, memory_client = setup_agent_with_memory_and_observability(actor_id, session_id)
                
                # エージェントを実行（Memory Hook が自動的に処理）
                with tracer.start_as_current_span("agent_execution") as exec_span:
                    response = agent(user_message)
                    exec_span.set_attribute("response_length", len(str(response.message if hasattr(response, 'message') else response)))
                    exec_span.set_status(Status(StatusCode.OK))
                
                result = {
                    "result": str(response.message if hasattr(response, 'message') else response),
                    "metadata": {
                        "actor_id": actor_id,
                        "session_id": session_id,
                        "email": email,
                        "memory_enabled": MEMORY_ID is not None,
                        "observability_enabled": True
                    }
                }
                
            else:
                # メールアドレスがない場合は Memory なしで処理
                span.set_attribute("customer_identified", False)
                logger.info("メールアドレスが見つかりません。Memory なしで処理します。")
                
                agent = Agent(
                    system_prompt=SYSTEM_PROMPT,
                    tools=[calculator, current_time, get_customer_id, get_orders, get_knowledge_base_info]
                )
                
                with tracer.start_as_current_span("agent_execution_no_memory") as exec_span:
                    response = agent(user_message)
                    exec_span.set_attribute("response_length", len(str(response.message if hasattr(response, 'message') else response)))
                    exec_span.set_status(Status(StatusCode.OK))
                
                result = {
                    "result": str(response.message if hasattr(response, 'message') else response),
                    "metadata": {
                        "memory_enabled": False,
                        "observability_enabled": True
                    }
                }
            
            # レスポンス時間を記録
            response_time = time.time() - start_time
            response_time_histogram.record(response_time)
            
            span.set_attribute("response_time_seconds", response_time)
            span.set_attribute("success", True)
            span.set_status(Status(StatusCode.OK))
            
            logger.info(f"リクエスト処理完了: {response_time:.2f}秒")
            
            return result
            
        except Exception as e:
            # エラー処理とログ記録
            error_message = str(e)
            span.set_attribute("error", True)
            span.set_attribute("error_message", error_message)
            span.set_status(Status(StatusCode.ERROR, error_message))
            
            logger.error(f"エージェント実行エラー: {error_message}", exc_info=True)
            
            # エラーメトリクス更新
            customer_requests_counter.add(1, {"status": "error"})
            
            return {
                "error": error_message,
                "metadata": {
                    "observability_enabled": True,
                    "error_occurred": True
                }
            }

if __name__ == "__main__":
    logger.info("Observability機能付きカスタマーサポートエージェントを起動中...")
    app.run()