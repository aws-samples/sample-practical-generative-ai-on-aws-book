#!/usr/bin/env python3
"""
Memory Inspector
Long Term Memory の内容を確認するためのツール

基本的な使い方
# ヘルプを表示
python memory_inspector.py --help

# Memory の概要を表示
python memory_inspector.py summary --actor-id customer_12345678

# セッション一覧を表示
python memory_inspector.py list-sessions --actor-id customer_12345678

# 最新セッションのイベント一覧を表示
python memory_inspector.py list-events --actor-id customer_12345678

# Long Term Memory の記録を表示
python memory_inspector.py list-memories --actor-id customer_12345678

# Memory から検索
python memory_inspector.py search-memories --actor-id customer_12345678 --query "スマートフォン"
"""

import json
import click
from bedrock_agentcore.memory import MemoryClient
import boto3
import os
from typing import Optional

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

# Boto3 クライアント（低レベルAPI用）
bedrock_client = boto3.client("bedrock-agentcore")

@click.group()
def cli():
    """Memory Inspector - Long Term Memory 確認ツール"""
    pass

@cli.command()
@click.option("--actor-id", default="default", help="アクターID（顧客ID）")
@click.option("--max-results", default=10, help="最大結果数")
def list_sessions(actor_id: str, max_results: int):
    """指定されたアクターのセッション一覧を表示"""
    click.echo("=== セッション一覧 ===")
    click.echo(f"Memory ID: {MEMORY_ID}")
    click.echo(f"Actor ID: {actor_id}")
    click.echo("=" * 50)
    
    try:
        response = bedrock_client.list_sessions(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            maxResults=max_results
        )
        
        sessions = response.get("sessionSummaries", [])
        if not sessions:
            click.echo("セッションが見つかりません。")
            return
            
        for i, session in enumerate(sessions, 1):
            click.echo(f"{i}. Session ID: {session['sessionId']}")
            click.echo(f"   作成日時: {session.get('createdAt', 'N/A')}")
            click.echo(f"   更新日時: {session.get('updatedAt', 'N/A')}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ エラー: {e}")

@cli.command()
@click.option("--actor-id", default="default", help="アクターID（顧客ID）")
@click.option("--session-id", help="セッションID（指定しない場合は最新のセッション）")
@click.option("--max-results", default=20, help="最大結果数")
def list_events(actor_id: str, session_id: Optional[str], max_results: int):
    """指定されたセッションのイベント一覧を表示"""
    click.echo("=== イベント一覧 ===")
    click.echo(f"Memory ID: {MEMORY_ID}")
    click.echo(f"Actor ID: {actor_id}")
    
    try:
        # セッションIDが指定されていない場合は最新のセッションを取得
        if not session_id:
            sessions_response = bedrock_client.list_sessions(
                memoryId=MEMORY_ID,
                actorId=actor_id,
                maxResults=1
            )
            sessions = sessions_response.get("sessionSummaries", [])
            if not sessions:
                click.echo("セッションが見つかりません。")
                return
            session_id = sessions[0]["sessionId"]
        
        click.echo(f"Session ID: {session_id}")
        click.echo("=" * 50)
        
        response = bedrock_client.list_events(
            memoryId=MEMORY_ID,
            sessionId=session_id,
            actorId=actor_id,
            includePayloads=True,
            maxResults=max_results
        )
        
        events = response.get("events", [])
        if not events:
            click.echo("イベントが見つかりません。")
            return
            
        for i, event in enumerate(events, 1):
            click.echo(f"{i}. Event ID: {event['eventId']}")
            click.echo(f"   タイプ: {event.get('eventType', 'N/A')}")
            click.echo(f"   作成日時: {event.get('createdAt', 'N/A')}")
            
            # ペイロードがある場合は表示
            if 'payload' in event:
                payload = event['payload']
                if 'messages' in payload:
                    click.echo("   メッセージ:")
                    for msg in payload['messages']:
                        role = msg.get('role', 'UNKNOWN')
                        content = msg.get('content', {}).get('text', 'N/A')
                        click.echo(f"     [{role}] {content[:100]}{'...' if len(content) > 100 else ''}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ エラー: {e}")

@cli.command()
@click.option("--actor-id", default="default", help="アクターID（顧客ID）")
@click.option("--namespace-type", 
              type=click.Choice(['facts', 'preferences', 'all']), 
              default='all', 
              help="表示する名前空間のタイプ")
@click.option("--max-results", default=20, help="最大結果数")
def list_memories(actor_id: str, namespace_type: str, max_results: int):
    """Long Term Memory の記録を表示"""
    click.echo("=== Long Term Memory 記録 ===")
    click.echo(f"Memory ID: {MEMORY_ID}")
    click.echo(f"Actor ID: {actor_id}")
    click.echo(f"Namespace Type: {namespace_type}")
    click.echo("=" * 50)
    
    namespaces = []
    if namespace_type == 'all':
        namespaces = ['preferences', 'issues', 'summaries']
    else:
        namespaces = [namespace_type]
    
    try:
        for ns in namespaces:
            namespace = f"/{ns}/{actor_id}"
            click.echo(f"\n📁 名前空間: {namespace}")
            click.echo("-" * 40)
            
            response = bedrock_client.list_memory_records(
                memoryId=MEMORY_ID,
                namespace=namespace,
                maxResults=max_results
            )
            
            records = response.get("memoryRecordSummaries", [])
            if not records:
                click.echo("  記録が見つかりません。")
                continue
                
            for i, record in enumerate(records, 1):
                click.echo(f"  {i}. Record ID: {record['recordId']}")
                click.echo(f"     作成日時: {record.get('createdAt', 'N/A')}")
                click.echo(f"     更新日時: {record.get('updatedAt', 'N/A')}")
                
                content = record.get('content', {}).get('text', 'N/A')
                # 長いコンテンツは省略
                if len(content) > 200:
                    content = content[:200] + "..."
                click.echo(f"     内容: {content}")
                click.echo()
                
    except Exception as e:
        click.echo(f"❌ エラー: {e}")

@cli.command()
@click.option("--actor-id", default="default", help="アクターID（顧客ID）")
@click.option("--query", required=True, help="検索クエリ")
@click.option("--namespace", help="検索する名前空間（省略時は全体検索）")
@click.option("--top-k", default=5, help="取得する上位結果数")
def search_memories(actor_id: str, query: str, namespace: Optional[str], top_k: int):
    """Memory から関連する記録を検索"""
    click.echo("=== Memory 検索 ===")
    click.echo(f"Memory ID: {MEMORY_ID}")
    click.echo(f"Actor ID: {actor_id}")
    click.echo(f"Query: {query}")
    click.echo(f"Namespace: {namespace or 'all'}")
    click.echo("=" * 50)
    
    try:
        memory_client = MemoryClient()
        
        # 検索パラメータを準備
        search_params = {
            "memory_id": MEMORY_ID,
            "query": query,
            "top_k": top_k
        }
        
        if namespace:
            search_params["namespace"] = namespace
        
        memories = memory_client.retrieve_memories(**search_params)
        
        if not memories:
            click.echo("関連する記録が見つかりません。")
            return
            
        for i, memory in enumerate(memories, 1):
            click.echo(f"{i}. スコア: {memory.get('score', 'N/A')}")
            click.echo(f"   名前空間: {memory.get('namespace', 'N/A')}")
            
            content = memory.get('content', {}).get('text', 'N/A')
            click.echo(f"   内容: {content}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ エラー: {e}")

@cli.command()
@click.option("--actor-id", default="default", help="アクターID（顧客ID）")
def summary(actor_id: str):
    """指定されたアクターのMemory概要を表示"""
    click.echo("=== Memory 概要 ===")
    click.echo(f"Memory ID: {MEMORY_ID}")
    click.echo(f"Actor ID: {actor_id}")
    click.echo("=" * 50)
    
    try:
        # セッション数を取得
        sessions_response = bedrock_client.list_sessions(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            maxResults=100
        )
        session_count = len(sessions_response.get("sessionSummaries", []))
        
        # 各名前空間の記録数を取得
        namespaces = ['preferences', 'issues', 'summaries']
        namespace_counts = {}
        
        for ns in namespaces:
            namespace = f"/{ns}/{actor_id}"
            try:
                response = bedrock_client.list_memory_records(
                    memoryId=MEMORY_ID,
                    namespace=namespace,
                    maxResults=100
                )
                namespace_counts[ns] = len(response.get("memoryRecordSummaries", []))
            except:
                namespace_counts[ns] = 0
        
        click.echo(f"📊 セッション数: {session_count}")
        click.echo(f"⚙️  Preferences 記録数: {namespace_counts['preferences']}")
        click.echo(f"📝 Issues 記録数: {namespace_counts['issues']}")
        click.echo(f" Summaries 記録数: {namespace_counts['summaries']}")
        
        click.echo()
        
        # 最新のセッション情報
        if session_count > 0:
            latest_session = sessions_response["sessionSummaries"][0]
            click.echo(f"🕒 最新セッション: {latest_session['sessionId']}")
            click.echo(f"   更新日時: {latest_session.get('updatedAt', 'N/A')}")
        
    except Exception as e:
        click.echo(f"❌ エラー: {e}")

if __name__ == "__main__":
    cli()