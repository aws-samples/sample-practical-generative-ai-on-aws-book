#!/usr/bin/env python3
"""
Cognito Setup
Amazon Cognito User Pool とクライアントを設定し、AgentCore Identity と連携
"""

import boto3
import json
import click
import os
import hmac
import hashlib
import base64
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

def get_aws_region() -> str:
    """現在のAWSリージョンを取得"""
    session = boto3.session.Session()
    return session.region_name

def get_aws_account_id() -> str:
    """現在のAWSアカウントIDを取得"""
    sts = boto3.client("sts")
    return sts.get_caller_identity()["Account"]

def store_ssm_parameter(name: str, value: str, parameter_type: str = "String", secure: bool = False):
    """SSMパラメータに値を保存"""
    ssm = boto3.client("ssm")
    try:
        ssm.put_parameter(
            Name=name,
            Value=value,
            Type="SecureString" if secure else parameter_type,
            Overwrite=True
        )
        click.echo(f"✅ SSMパラメータに保存: {name}")
    except ClientError as e:
        click.echo(f"❌ SSMパラメータ保存エラー: {e}")
        raise

def get_ssm_parameter(name: str, with_decryption: bool = True) -> Optional[str]:
    """SSMパラメータから値を取得"""
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except ClientError:
        return None

def save_cognito_config(config: Dict[str, Any]):
    """Cognito設定をJSONファイルに保存"""
    with open("cognito_config.json", "w") as f:
        json.dump(config, f, indent=2, default=str)
    click.echo("✅ Cognito設定をcognito_config.jsonに保存しました")

def load_cognito_config() -> Optional[Dict[str, Any]]:
    """Cognito設定をJSONファイルから読み込み"""
    if os.path.exists("cognito_config.json"):
        with open("cognito_config.json", "r") as f:
            return json.load(f)
    return None

class CognitoSetup:
    def __init__(self):
        self.region = get_aws_region()
        self.account_id = get_aws_account_id()
        self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
        
    def create_user_pool(self, pool_name: str = "CustomerSupportPool") -> Dict[str, Any]:
        """Cognito User Poolを作成"""
        click.echo(f"🏗️  Cognito User Pool を作成中: {pool_name}")
        
        try:
            response = self.cognito_client.create_user_pool(
                PoolName=pool_name,
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': False
                    }
                },
                AutoVerifiedAttributes=['email'],
                UsernameAttributes=['email'],
                Schema=[
                    {
                        'Name': 'email',
                        'AttributeDataType': 'String',
                        'Required': True,
                        'Mutable': True
                    },
                    {
                        'Name': 'name',
                        'AttributeDataType': 'String',
                        'Required': False,
                        'Mutable': True
                    }
                ]
            )
            
            pool_id = response['UserPool']['Id']
            click.echo(f"✅ User Pool作成完了: {pool_id}")
            return response['UserPool']
            
        except ClientError as e:
            click.echo(f"❌ User Pool作成エラー: {e}")
            raise

    def create_user_pool_client(self, pool_id: str, client_name: str = "CustomerSupportClient", generate_secret: bool = True) -> Dict[str, Any]:
        """Cognito User Pool Clientを作成"""
        click.echo(f"🏗️  User Pool Client を作成中: {client_name}")
        
        try:
            response = self.cognito_client.create_user_pool_client(
                UserPoolId=pool_id,
                ClientName=client_name,
                GenerateSecret=generate_secret,  # OAuth2用にシークレットを生成
                ExplicitAuthFlows=[
                    'ALLOW_USER_PASSWORD_AUTH',
                    'ALLOW_REFRESH_TOKEN_AUTH',
                    'ALLOW_ADMIN_USER_PASSWORD_AUTH'
                ],
                SupportedIdentityProviders=['COGNITO'],
                CallbackURLs=['https://localhost:3000/callback'],  # 開発用
                LogoutURLs=['https://localhost:3000/logout'],      # 開発用
                AllowedOAuthFlows=['code', 'implicit'],
                AllowedOAuthScopes=['openid', 'email', 'profile'],
                AllowedOAuthFlowsUserPoolClient=True
            )
            
            client_id = response['UserPoolClient']['ClientId']
            click.echo(f"✅ User Pool Client作成完了: {client_id}")
            return response['UserPoolClient']
            
        except ClientError as e:
            click.echo(f"❌ User Pool Client作成エラー: {e}")
            raise

    def create_user_pool_domain(self, pool_id: str, domain_prefix: str) -> str:
        """Cognito User Pool Domainを作成"""
        click.echo(f"🏗️  User Pool Domain を作成中: {domain_prefix}")
        
        try:
            response = self.cognito_client.create_user_pool_domain(
                Domain=domain_prefix,
                UserPoolId=pool_id
            )
            
            domain_name = f"{domain_prefix}.auth.{self.region}.amazoncognito.com"
            click.echo(f"✅ User Pool Domain作成完了: {domain_name}")
            return domain_name
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidParameterException':
                click.echo(f"⚠️  ドメイン '{domain_prefix}' は既に使用されています")
                # 既存のドメインを使用
                return f"{domain_prefix}.auth.{self.region}.amazoncognito.com"
            else:
                click.echo(f"❌ User Pool Domain作成エラー: {e}")
                raise

    def create_test_user(self, pool_id: str, username: str = "me@example.net", 
                        email: str = "me@example.net", password: str = "TempPass123!"):
        """テストユーザーを作成"""
        click.echo(f"👤 テストユーザーを作成中: {username}")
        
        try:
            # ユーザー作成
            self.cognito_client.admin_create_user(
                UserPoolId=pool_id,
                Username=username,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                MessageAction='SUPPRESS'  # ウェルカムメールを送信しない
            )
            
            # パスワード設定
            self.cognito_client.admin_set_user_password(
                UserPoolId=pool_id,
                Username=username,
                Password=password,
                Permanent=True
            )
            
            click.echo(f"✅ テストユーザー作成完了: {username}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                click.echo(f"⚠️  ユーザー '{username}' は既に存在します")
            else:
                click.echo(f"❌ テストユーザー作成エラー: {e}")
                raise

    def get_client_secret(self, pool_id: str, client_id: str) -> str:
        """User Pool Clientのシークレットを取得"""
        try:
            response = self.cognito_client.describe_user_pool_client(
                UserPoolId=pool_id,
                ClientId=client_id
            )
            return response['UserPoolClient']['ClientSecret']
        except ClientError as e:
            click.echo(f"❌ クライアントシークレット取得エラー: {e}")
            raise

    def calculate_secret_hash(self, username: str, client_id: str, client_secret: str) -> str:
        """SECRET_HASHを計算"""
        message = username + client_id
        dig = hmac.new(
            client_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    def authenticate_user(self, client_id: str, client_secret: Optional[str] = None, username: str = "me@example.net", 
                         password: str = "TempPass123!") -> str:
        """ユーザー認証してアクセストークンを取得"""
        click.echo(f"🔐 ユーザー認証中: {username}")
        
        try:
            auth_parameters = {
                'USERNAME': username,
                'PASSWORD': password
            }
            
            # クライアントシークレットがある場合はSECRET_HASHを追加
            if client_secret:
                secret_hash = self.calculate_secret_hash(username, client_id, client_secret)
                auth_parameters['SECRET_HASH'] = secret_hash
                click.echo("🔑 SECRET_HASHを使用して認証")
            else:
                click.echo("🔓 シークレットなしで認証")
            
            response = self.cognito_client.initiate_auth(
                ClientId=client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters=auth_parameters
            )
            
            access_token = response['AuthenticationResult']['AccessToken']
            click.echo(f"✅ 認証成功、アクセストークン取得")
            return access_token
            
        except ClientError as e:
            click.echo(f"❌ 認証エラー: {e}")
            raise

@click.group()
def cli():
    """Cognito Setup CLI - AgentCore Identity連携用のCognito設定"""
    pass

@cli.command()
@click.option("--pool-name", default="CustomerSupportPool", help="User Pool名")
@click.option("--client-name", default="CustomerSupportClient", help="User Pool Client名")
@click.option("--domain-prefix", required=True, help="ドメインプレフィックス（一意である必要があります）")
@click.option("--no-secret", is_flag=True, help="クライアントシークレットを生成しない（開発用）")
def setup(pool_name: str, client_name: str, domain_prefix: str, no_secret: bool):
    """Cognito User Pool、Client、Domainを一括設定"""
    click.echo("🚀 Cognito セットアップを開始します")
    click.echo(f"📍 リージョン: {get_aws_region()}")
    click.echo(f"🏢 アカウントID: {get_aws_account_id()}")
    
    cognito_setup = CognitoSetup()
    
    try:
        # User Pool作成
        user_pool = cognito_setup.create_user_pool(pool_name)
        pool_id = user_pool['Id']
        
        # User Pool Client作成
        user_pool_client = cognito_setup.create_user_pool_client(pool_id, client_name, generate_secret=not no_secret)
        client_id = user_pool_client['ClientId']
        
        # User Pool Domain作成
        domain_name = cognito_setup.create_user_pool_domain(pool_id, domain_prefix)
        
        # クライアントシークレット取得（シークレットが生成されている場合のみ）
        client_secret = None
        try:
            client_secret = cognito_setup.get_client_secret(pool_id, client_id)
        except Exception as e:
            click.echo(f"⚠️  クライアントシークレット取得をスキップ: {e}")
            click.echo("   シークレットなしのクライアントとして動作します")
        
        # テストユーザー作成
        cognito_setup.create_test_user(pool_id)
        
        # 認証テスト
        access_token = cognito_setup.authenticate_user(client_id, client_secret)
        
        # 設定情報を構築
        config = {
            "user_pool_id": pool_id,
            "client_id": client_id,
            "domain_name": domain_name,
            "region": cognito_setup.region,
            "discovery_url": f"https://cognito-idp.{cognito_setup.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration",
            "auth_url": f"https://{domain_name}/oauth2/authorize",
            "token_url": f"https://{domain_name}/oauth2/token",
            "test_access_token": access_token
        }
        
        # クライアントシークレットがある場合のみ追加
        if client_secret:
            config["client_secret"] = client_secret
        
        # SSMパラメータに保存
        store_ssm_parameter("/app/customersupport/agentcore/userpool_id", pool_id)
        store_ssm_parameter("/app/customersupport/agentcore/machine_client_id", client_id)
        if client_secret:
            store_ssm_parameter("/app/customersupport/agentcore/cognito_secret", client_secret, secure=True)
        store_ssm_parameter("/app/customersupport/agentcore/cognito_discovery_url", config["discovery_url"])
        store_ssm_parameter("/app/customersupport/agentcore/cognito_auth_url", config["auth_url"])
        store_ssm_parameter("/app/customersupport/agentcore/cognito_token_url", config["token_url"])
        
        # ローカル設定ファイルに保存
        save_cognito_config(config)
        
        click.echo("\n🎉 Cognito セットアップ完了！")
        click.echo("=" * 50)
        click.echo(f"User Pool ID: {pool_id}")
        click.echo(f"Client ID: {client_id}")
        click.echo(f"Domain: {domain_name}")
        click.echo(f"Discovery URL: {config['discovery_url']}")
        click.echo("=" * 50)
        click.echo("次のステップ:")
        click.echo("1. python cognito_credentials_provider.py create --name <provider-name>")
        click.echo("2. python customer_support_agent_with_identity.py でテスト")
        
    except Exception as e:
        click.echo(f"❌ セットアップ失敗: {e}")
        raise

@cli.command()
def test_auth():
    """既存のCognito設定で認証テスト"""
    config = load_cognito_config()
    if not config:
        click.echo("❌ cognito_config.json が見つかりません。先に setup を実行してください。")
        return
    
    cognito_setup = CognitoSetup()
    
    try:
        client_secret = config.get("client_secret")
        access_token = cognito_setup.authenticate_user(config["client_id"], client_secret)
        click.echo("✅ 認証テスト成功")
        click.echo(f"アクセストークン: {access_token[:20]}...")
        
        # 設定を更新
        config["test_access_token"] = access_token
        save_cognito_config(config)
        
    except Exception as e:
        click.echo(f"❌ 認証テスト失敗: {e}")

@cli.command()
def show_config():
    """現在のCognito設定を表示"""
    config = load_cognito_config()
    if not config:
        click.echo("❌ cognito_config.json が見つかりません。")
        return
    
    click.echo("📋 現在のCognito設定:")
    click.echo("=" * 40)
    for key, value in config.items():
        if "secret" in key.lower() or "token" in key.lower():
            click.echo(f"{key}: {str(value)[:10]}...")
        else:
            click.echo(f"{key}: {value}")

if __name__ == "__main__":
    cli()