#!/usr/bin/env python3
"""
Cognito Credentials Provider
AgentCore Identity用のOAuth2認証プロバイダーを管理
"""

import boto3
import click
import json
import os
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

def get_aws_region() -> str:
    """現在のAWSリージョンを取得"""
    session = boto3.session.Session()
    return session.region_name

def get_ssm_parameter(name: str, with_decryption: bool = True) -> Optional[str]:
    """SSMパラメータから値を取得"""
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except ClientError:
        return None

def store_ssm_parameter(name: str, value: str):
    """SSMパラメータに値を保存"""
    ssm = boto3.client("ssm")
    try:
        ssm.put_parameter(
            Name=name,
            Value=value,
            Type="String",
            Overwrite=True
        )
        click.echo(f"✅ SSMパラメータに保存: {name}")
    except ClientError as e:
        click.echo(f"❌ SSMパラメータ保存エラー: {e}")
        raise

def delete_ssm_parameter(name: str):
    """SSMパラメータを削除"""
    ssm = boto3.client("ssm")
    try:
        ssm.delete_parameter(Name=name)
        click.echo(f"🧹 SSMパラメータを削除: {name}")
    except ClientError as e:
        click.echo(f"⚠️  SSMパラメータ削除エラー: {e}")

def load_cognito_config() -> Optional[Dict[str, Any]]:
    """Cognito設定をJSONファイルから読み込み"""
    if os.path.exists("cognito_config.json"):
        with open("cognito_config.json", "r") as f:
            return json.load(f)
    return None

class CognitoCredentialsProvider:
    def __init__(self):
        self.region = get_aws_region()
        self.identity_client = boto3.client("bedrock-agentcore-control", region_name=self.region)

    def create_oauth2_provider(self, provider_name: str) -> Dict[str, Any]:
        """OAuth2認証プロバイダーを作成"""
        click.echo(f"🏗️  OAuth2認証プロバイダーを作成中: {provider_name}")
        
        try:
            # SSMからCognito設定を取得
            click.echo("📥 SSMからCognito設定を取得中...")
            client_id = get_ssm_parameter("/app/customersupport/agentcore/machine_client_id")
            client_secret = get_ssm_parameter("/app/customersupport/agentcore/cognito_secret")
            discovery_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_discovery_url")
            auth_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_auth_url")
            token_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_token_url")
            
            if not all([client_id, discovery_url, auth_url, token_url]):
                raise ValueError("必要なCognito設定がSSMに見つかりません。先に cognito_setup.py setup を実行してください。")
            
            if not client_secret:
                raise ValueError("OAuth2プロバイダーにはクライアントシークレットが必要です。cognito_setup.py setup を --no-secret オプションなしで実行してください。")
            
            click.echo(f"✅ Client ID: {client_id}")
            click.echo(f"✅ Client Secret: {client_secret[:4]}***")
            click.echo(f"✅ Discovery URL: {discovery_url}")
            click.echo(f"✅ Auth URL: {auth_url}")
            click.echo(f"✅ Token URL: {token_url}")
            
            # OAuth2プロバイダー作成
            response = self.identity_client.create_oauth2_credential_provider(
                name=provider_name,
                credentialProviderVendor="CustomOauth2",
                oauth2ProviderConfigInput={
                    "customOauth2ProviderConfig": {
                        "clientId": client_id,
                        "clientSecret": client_secret,
                        "oauthDiscovery": {
                            "authorizationServerMetadata": {
                                "issuer": discovery_url.replace("/.well-known/openid-configuration", ""),
                                "authorizationEndpoint": auth_url,
                                "tokenEndpoint": token_url,
                                "responseTypes": ["code", "token"],
                            }
                        },
                    }
                },
            )
            
            click.echo("✅ OAuth2認証プロバイダー作成完了")
            provider_arn = response["credentialProviderArn"]
            click.echo(f"   Provider ARN: {provider_arn}")
            click.echo(f"   Provider Name: {response['name']}")
            
            # プロバイダー名をSSMに保存
            store_ssm_parameter("/app/customersupport/agentcore/cognito_provider", provider_name)
            
            return response
            
        except Exception as e:
            click.echo(f"❌ OAuth2認証プロバイダー作成エラー: {e}")
            raise

    def delete_oauth2_provider(self, provider_name: str) -> bool:
        """OAuth2認証プロバイダーを削除"""
        click.echo(f"🗑️  OAuth2認証プロバイダーを削除中: {provider_name}")
        
        try:
            self.identity_client.delete_oauth2_credential_provider(name=provider_name)
            click.echo("✅ OAuth2認証プロバイダー削除完了")
            return True
            
        except Exception as e:
            click.echo(f"❌ OAuth2認証プロバイダー削除エラー: {e}")
            return False

    def list_oauth2_providers(self) -> list:
        """OAuth2認証プロバイダー一覧を取得"""
        try:
            response = self.identity_client.list_oauth2_credential_providers(maxResults=20)
            return response.get("credentialProviders", [])
            
        except Exception as e:
            click.echo(f"❌ OAuth2認証プロバイダー一覧取得エラー: {e}")
            return []

    def find_provider_by_name(self, provider_name: str) -> bool:
        """指定された名前のプロバイダーが存在するかチェック"""
        providers = self.list_oauth2_providers()
        for provider in providers:
            if provider.get("name") == provider_name:
                return True
        return False

@click.group()
def cli():
    """Cognito Credentials Provider CLI - AgentCore Identity用OAuth2プロバイダー管理"""
    pass

@cli.command()
@click.option("--name", required=True, help="認証プロバイダー名（必須）")
def create(name: str):
    """新しいCognito OAuth2認証プロバイダーを作成"""
    click.echo(f"🚀 Cognito認証プロバイダーを作成: {name}")
    click.echo(f"📍 リージョン: {get_aws_region()}")
    
    # 既存のプロバイダーをチェック
    existing_name = get_ssm_parameter("/app/customersupport/agentcore/cognito_provider")
    if existing_name:
        click.echo(f"⚠️  既存のプロバイダーがSSMに登録されています: {existing_name}")
        if not click.confirm("置き換えますか？"):
            click.echo("❌ 操作をキャンセルしました")
            return
    
    provider = CognitoCredentialsProvider()
    
    try:
        result = provider.create_oauth2_provider(name)
        click.echo("\n🎉 Cognito認証プロバイダー作成完了！")
        click.echo("=" * 50)
        click.echo(f"Provider ARN: {result['credentialProviderArn']}")
        click.echo(f"Provider Name: {result['name']}")
        click.echo("=" * 50)
        click.echo("次のステップ:")
        click.echo("python customer_support_agent_with_identity.py でテスト")
        
    except Exception as e:
        click.echo(f"❌ 認証プロバイダー作成失敗: {e}")

@cli.command()
@click.option("--name", help="削除する認証プロバイダー名（省略時はSSMから取得）")
@click.option("--confirm", is_flag=True, help="確認プロンプトをスキップ")
def delete(name: Optional[str], confirm: bool):
    """Cognito OAuth2認証プロバイダーを削除"""
    
    # 名前が指定されていない場合はSSMから取得
    if not name:
        name = get_ssm_parameter("/app/customersupport/agentcore/cognito_provider")
        if not name:
            click.echo("❌ プロバイダー名が指定されておらず、SSMパラメータからも取得できません")
            click.echo("   ヒント: list コマンドで利用可能なプロバイダーを確認してください")
            return
        click.echo(f"📖 SSMからプロバイダー名を取得: {name}")
    
    provider = CognitoCredentialsProvider()
    
    # プロバイダーの存在確認
    if not provider.find_provider_by_name(name):
        click.echo(f"❌ 認証プロバイダーが見つかりません: {name}")
        click.echo("   ヒント: list コマンドで利用可能なプロバイダーを確認してください")
        return
    
    click.echo(f"📖 プロバイダーを発見: {name}")
    
    # 確認プロンプト
    if not confirm:
        if not click.confirm(f"⚠️  認証プロバイダー '{name}' を削除しますか？この操作は元に戻せません。"):
            click.echo("❌ 操作をキャンセルしました")
            return
    
    if provider.delete_oauth2_provider(name):
        click.echo(f"✅ 認証プロバイダー '{name}' を削除しました")
        
        # SSMパラメータも削除
        delete_ssm_parameter("/app/customersupport/agentcore/cognito_provider")
        click.echo("🎉 認証プロバイダーとSSMパラメータを削除しました")
    else:
        click.echo("❌ 認証プロバイダーの削除に失敗しました")

@cli.command("list")
def list_providers():
    """OAuth2認証プロバイダー一覧を表示"""
    provider = CognitoCredentialsProvider()
    providers = provider.list_oauth2_providers()
    
    if not providers:
        click.echo("ℹ️  認証プロバイダーが見つかりません")
        return
    
    click.echo(f"📋 {len(providers)}個の認証プロバイダーが見つかりました:")
    click.echo("=" * 60)
    
    for p in providers:
        click.echo(f"• 名前: {p.get('name', 'N/A')}")
        click.echo(f"  ARN: {p['credentialProviderArn']}")
        click.echo(f"  ベンダー: {p.get('credentialProviderVendor', 'N/A')}")
        if "createdTime" in p:
            click.echo(f"  作成日時: {p['createdTime']}")
        click.echo()

@cli.command()
def show_config():
    """現在のCognito設定を表示"""
    click.echo("📋 現在のCognito設定:")
    click.echo("=" * 40)
    
    # ローカル設定ファイル
    config = load_cognito_config()
    if config:
        click.echo("ローカル設定 (cognito_config.json):")
        for key, value in config.items():
            if "secret" in key.lower() or "token" in key.lower():
                click.echo(f"  {key}: {str(value)[:10]}...")
            else:
                click.echo(f"  {key}: {value}")
        click.echo()
    
    # SSM設定
    click.echo("SSM設定:")
    ssm_params = [
        "/app/customersupport/agentcore/userpool_id",
        "/app/customersupport/agentcore/machine_client_id",
        "/app/customersupport/agentcore/cognito_discovery_url",
        "/app/customersupport/agentcore/cognito_auth_url",
        "/app/customersupport/agentcore/cognito_token_url",
        "/app/customersupport/agentcore/cognito_provider"
    ]
    
    for param in ssm_params:
        value = get_ssm_parameter(param)
        if value:
            if "secret" in param.lower():
                click.echo(f"  {param}: {value[:4]}***")
            else:
                click.echo(f"  {param}: {value}")
        else:
            click.echo(f"  {param}: (未設定)")

if __name__ == "__main__":
    cli()