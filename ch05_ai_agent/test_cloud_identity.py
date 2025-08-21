#!/usr/bin/env python3
"""
Cloud Identity Test
クラウドデプロイされたエージェントのIdentity機能をテスト
"""

import json
import requests
import uuid
import click
import os
from urllib.parse import quote

def load_cognito_config():
    """Cognito設定を読み込み"""
    if os.path.exists("cognito_config.json"):
        with open("cognito_config.json", "r") as f:
            return json.load(f)
    return None

def load_agent_config():
    """エージェント設定を読み込み"""
    if os.path.exists(".bedrock_agentcore.yaml"):
        import yaml
        with open(".bedrock_agentcore.yaml", "r") as f:
            config = yaml.safe_load(f)
            agent_config = config.get("agents", {}).get("customer_support_agent_with_identity", {})
            return agent_config.get("bedrock_agentcore", {}).get("agent_arn")
    return None

def invoke_cloud_agent(agent_arn: str, payload: dict, access_token: str) -> dict:
    """クラウドエージェントを呼び出し"""
    
    # AgentCore Runtime API エンドポイント
    escaped_arn = quote(agent_arn, safe="")
    url = f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{escaped_arn}/invocations"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": str(uuid.uuid4())
    }
    
    try:
        response = requests.post(
            url,
            params={"qualifier": "DEFAULT"},
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "response": response.text}
        else:
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}"}

@click.group()
def cli():
    """Cloud Identity Test CLI"""
    pass

@cli.command()
@click.option("--message", default="こんにちは、注文履歴を確認したいです。", help="テストメッセージ")
def test_authenticated(message: str):
    """認証付きでクラウドエージェントをテスト"""
    click.echo("🔐 認証付きクラウドエージェントテスト")
    click.echo("=" * 50)
    
    # 設定を読み込み
    cognito_config = load_cognito_config()
    if not cognito_config:
        click.echo("❌ cognito_config.json が見つかりません。")
        return
    
    agent_arn = load_agent_config()
    if not agent_arn:
        click.echo("❌ エージェントARNが見つかりません。")
        return
    
    access_token = cognito_config.get("test_access_token")
    if not access_token:
        click.echo("❌ アクセストークンが見つかりません。")
        return
    
    click.echo(f"📝 メッセージ: {message}")
    click.echo(f"🔑 アクセストークン: {access_token[:20]}...")
    click.echo(f"🌐 エージェントARN: {agent_arn}")
    click.echo()
    
    # エージェントを呼び出し
    payload = {"prompt": message}
    result = invoke_cloud_agent(agent_arn, payload, access_token)
    
    if result["success"]:
        click.echo("✅ 成功!")
        click.echo("📤 レスポンス:")
        
        # レスポンスをパース
        try:
            response_data = json.loads(result["response"])
            click.echo(json.dumps(response_data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            click.echo(result["response"])
    else:
        click.echo("❌ エラー:")
        click.echo(result["error"])

@cli.command()
@click.option("--message", default="テスト", help="テストメッセージ")
def test_unauthenticated(message: str):
    """認証なしでクラウドエージェントをテスト（エラーになるはず）"""
    click.echo("🔓 認証なしクラウドエージェントテスト")
    click.echo("=" * 50)
    
    agent_arn = load_agent_config()
    if not agent_arn:
        click.echo("❌ エージェントARNが見つかりません。")
        return
    
    click.echo(f"📝 メッセージ: {message}")
    click.echo(f"🌐 エージェントARN: {agent_arn}")
    click.echo()
    
    # 無効なトークンで呼び出し
    payload = {"prompt": message}
    result = invoke_cloud_agent(agent_arn, payload, "invalid-token")
    
    if result["success"]:
        click.echo("❌ 予期しない成功 - セキュリティ問題の可能性")
        click.echo(result["response"])
    else:
        click.echo("✅ 期待通り認証エラーが発生:")
        click.echo(result["error"])

@cli.command()
def show_config():
    """現在の設定を表示"""
    click.echo("📋 現在の設定:")
    click.echo("=" * 40)
    
    cognito_config = load_cognito_config()
    if cognito_config:
        click.echo("Cognito設定:")
        for key, value in cognito_config.items():
            if "secret" in key.lower() or "token" in key.lower():
                click.echo(f"  {key}: {str(value)[:10]}...")
            else:
                click.echo(f"  {key}: {value}")
        click.echo()
    
    agent_arn = load_agent_config()
    if agent_arn:
        click.echo(f"エージェントARN: {agent_arn}")
    else:
        click.echo("エージェントARN: 見つかりません")

if __name__ == "__main__":
    cli()