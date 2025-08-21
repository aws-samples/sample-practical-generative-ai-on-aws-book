#!/usr/bin/env python3
"""
Identity Integration Test
AgentCore Identity統合のテストスクリプト
"""

import json
import click
import requests
import os
import uuid
from typing import Dict, Any, Optional

def load_cognito_config() -> Optional[Dict[str, Any]]:
    """Cognito設定をJSONファイルから読み込み"""
    if os.path.exists("cognito_config.json"):
        with open("cognito_config.json", "r") as f:
            return json.load(f)
    return None

def test_agent_with_token(message: str, access_token: str, endpoint: str = "http://localhost:8080") -> Dict[str, Any]:
    """アクセストークン付きでエージェントをテスト"""
    payload = {
        "prompt": message
    }
    
    try:
        # AgentCore のOAuth Authorizerを使用する場合、Authorizationヘッダーが必要
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": str(uuid.uuid4())
        }
        
        # AgentCore Runtime APIエンドポイントを使用
        response = requests.post(f"{endpoint}/", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}

def test_agent_without_token(message: str, endpoint: str = "http://localhost:8080/invoke_without_auth") -> Dict[str, Any]:
    """アクセストークンなしでエージェントをテスト"""
    payload = {
        "prompt": message
    }
    
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}

@click.group()
def cli():
    """Identity Integration Test CLI"""
    pass

@cli.command()
@click.option("--message", default="こんにちは、注文履歴を確認したいです。", help="テストメッセージ")
@click.option("--endpoint", default="http://localhost:8080", help="エージェントのエンドポイント")
def test_with_auth(message: str, endpoint: str):
    """認証ありでエージェントをテスト"""
    click.echo("🔐 認証ありでエージェントをテスト")
    click.echo("=" * 50)
    
    # Cognito設定を読み込み
    config = load_cognito_config()
    if not config:
        click.echo("❌ cognito_config.json が見つかりません。")
        click.echo("   先に cognito_setup.py setup を実行してください。")
        return
    
    access_token = config.get("test_access_token")
    if not access_token:
        click.echo("❌ テスト用アクセストークンが見つかりません。")
        click.echo("   cognito_setup.py test-auth を実行してトークンを更新してください。")
        return
    
    click.echo(f"📝 メッセージ: {message}")
    click.echo(f"🔑 アクセストークン: {access_token[:20]}...")
    click.echo(f"🌐 エンドポイント: {endpoint}/invoke")
    click.echo()
    
    # エージェントをテスト
    result = test_agent_with_token(message, access_token, f"{endpoint}/invoke")
    
    if "error" in result:
        click.echo(f"❌ エラー: {result['error']}")
        if "message" in result:
            click.echo(f"   詳細: {result['message']}")
    else:
        click.echo("✅ 成功!")
        click.echo(f"🤖 エージェントの応答: {result.get('result', 'N/A')}")
        
        if "metadata" in result:
            metadata = result["metadata"]
            click.echo("\n📊 メタデータ:")
            for key, value in metadata.items():
                click.echo(f"   {key}: {value}")

@cli.command()
@click.option("--message", default="me@example.net のメールアドレスで注文履歴を確認したいです。", help="テストメッセージ")
@click.option("--endpoint", default="http://localhost:8080", help="エージェントのエンドポイント")
def test_without_auth(message: str, endpoint: str):
    """認証なしでエージェントをテスト（後方互換性）"""
    click.echo("🔓 認証なしでエージェントをテスト")
    click.echo("=" * 50)
    
    click.echo(f"📝 メッセージ: {message}")
    click.echo(f"🌐 エンドポイント: {endpoint}/invoke_without_auth")
    click.echo()
    
    # エージェントをテスト
    result = test_agent_without_token(message, f"{endpoint}/invoke_without_auth")
    
    if "error" in result:
        click.echo(f"❌ エラー: {result['error']}")
    else:
        click.echo("✅ 成功!")
        click.echo(f"🤖 エージェントの応答: {result.get('result', 'N/A')}")
        
        if "metadata" in result:
            metadata = result["metadata"]
            click.echo("\n📊 メタデータ:")
            for key, value in metadata.items():
                click.echo(f"   {key}: {value}")

@cli.command()
def test_invalid_token():
    """無効なトークンでのテスト"""
    click.echo("🚫 無効なトークンでテスト")
    click.echo("=" * 50)
    
    invalid_token = "invalid.token.here"
    message = "こんにちは、テストです。"
    
    click.echo(f"📝 メッセージ: {message}")
    click.echo(f"🔑 無効なトークン: {invalid_token}")
    click.echo()
    
    result = test_agent_with_token(message, invalid_token, "http://localhost:8080/invoke")
    
    if "error" in result:
        click.echo("✅ 期待通り認証エラーが発生:")
        click.echo(f"   エラー: {result['error']}")
        if "message" in result:
            click.echo(f"   詳細: {result['message']}")
    else:
        click.echo("❌ 予期しない成功 - セキュリティ問題の可能性があります")

@cli.command()
def interactive():
    """インタラクティブテストモード"""
    click.echo("🎮 インタラクティブテストモード")
    click.echo("=" * 50)
    
    # Cognito設定を読み込み
    config = load_cognito_config()
    if not config:
        click.echo("❌ cognito_config.json が見つかりません。")
        return
    
    access_token = config.get("test_access_token")
    if not access_token:
        click.echo("❌ テスト用アクセストークンが見つかりません。")
        return
    
    click.echo("認証済みモードでエージェントと対話します。")
    click.echo("終了するには 'quit' または 'exit' を入力してください。")
    click.echo()
    
    while True:
        try:
            message = click.prompt("あなた", type=str)
            
            if message.lower() in ['quit', 'exit', 'q']:
                click.echo("👋 テストを終了します。")
                break
            
            click.echo("🤖 処理中...")
            result = test_agent_with_token(message, access_token, "http://localhost:8080/invoke")
            
            if "error" in result:
                click.echo(f"❌ エラー: {result['error']}")
                if "message" in result:
                    click.echo(f"   詳細: {result['message']}")
            else:
                click.echo(f"エージェント: {result.get('result', 'N/A')}")
            
            click.echo()
            
        except KeyboardInterrupt:
            click.echo("\n👋 テストを終了します。")
            break
        except Exception as e:
            click.echo(f"❌ 予期しないエラー: {e}")

@cli.command()
@click.option("--message", default="こんにちは、注文履歴を確認したいです。", help="テストメッセージ")
def test_with_agentcore_invoke(message: str):
    """agentcore invoke コマンドを使用したテスト"""
    click.echo("🔧 agentcore invoke を使用したテスト")
    click.echo("=" * 50)
    
    config = load_cognito_config()
    if not config:
        click.echo("❌ cognito_config.json が見つかりません。")
        return
    
    access_token = config.get("test_access_token")
    if not access_token:
        click.echo("❌ テスト用アクセストークンが見つかりません。")
        return
    
    click.echo(f"📝 メッセージ: {message}")
    click.echo(f"🔑 アクセストークン: {access_token[:20]}...")
    click.echo()
    
    import subprocess
    import json as json_module
    
    try:
        # agentcore invoke コマンドを実行
        payload = {
            "prompt": message,
            "access_token": access_token
        }
        
        result = subprocess.run([
            "agentcore", "invoke", "--local", json_module.dumps(payload)
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            click.echo("✅ 成功!")
            click.echo("📤 出力:")
            click.echo(result.stdout)
        else:
            click.echo("❌ エラー:")
            click.echo(result.stderr)
            
    except Exception as e:
        click.echo(f"❌ 実行エラー: {e}")

@cli.command()
def show_config():
    """現在の設定を表示"""
    click.echo("📋 現在の設定:")
    click.echo("=" * 40)
    
    config = load_cognito_config()
    if not config:
        click.echo("❌ cognito_config.json が見つかりません。")
        return
    
    click.echo("Cognito設定:")
    for key, value in config.items():
        if "secret" in key.lower() or "token" in key.lower():
            click.echo(f"  {key}: {str(value)[:10]}...")
        else:
            click.echo(f"  {key}: {value}")

@cli.command()
@click.option("--endpoint", default="http://localhost:8080", help="エージェントのエンドポイント")
def health_check(endpoint: str):
    """エージェントのヘルスチェック"""
    click.echo("🏥 エージェントのヘルスチェック")
    click.echo("=" * 40)
    
    try:
        # 簡単なヘルスチェック
        response = requests.get(f"{endpoint}/health", timeout=5)
        if response.status_code == 200:
            click.echo("✅ エージェントは正常に動作しています")
        else:
            click.echo(f"⚠️  エージェントから異常なレスポンス: {response.status_code}")
    except requests.exceptions.ConnectionError:
        click.echo("❌ エージェントに接続できません")
        click.echo("   エージェントが起動していることを確認してください:")
        click.echo("   python customer_support_agent_with_identity.py")
    except requests.exceptions.Timeout:
        click.echo("❌ エージェントからの応答がタイムアウトしました")
    except Exception as e:
        click.echo(f"❌ ヘルスチェックエラー: {e}")

if __name__ == "__main__":
    cli()