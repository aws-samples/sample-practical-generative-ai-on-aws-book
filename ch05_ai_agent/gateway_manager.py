#!/usr/bin/env python3
"""
AgentCore Gateway 管理スクリプト
Lambda 関数を MCP ツールとして公開するための Gateway を作成・管理
"""

import json
import boto3
import sys
import zipfile
import os
from pathlib import Path
from typing import Dict, Any, List
import time


class GatewayManager:
    def __init__(self):
        self.region = self._get_aws_region()
        self.account_id = self._get_aws_account_id()
        
        # AWS クライアントを初期化
        self.gateway_client = boto3.client("bedrock-agentcore-control", region_name=self.region)
        self.lambda_client = boto3.client("lambda", region_name=self.region)
        self.iam_client = boto3.client("iam", region_name=self.region)
        
        print(f"🌍 リージョン: {self.region}")
        print(f"🏢 アカウントID: {self.account_id}")
    
    def _get_aws_region(self) -> str:
        """現在のAWSリージョンを取得"""
        try:
            session = boto3.Session()
            return session.region_name or 'us-east-1'
        except Exception:
            return 'us-east-1'
    
    def _get_aws_account_id(self) -> str:
        """現在のAWSアカウントIDを取得"""
        try:
            sts = boto3.client('sts')
            return sts.get_caller_identity()['Account']
        except Exception as e:
            print(f"❌ AWSアカウントID取得エラー: {e}")
            sys.exit(1)
    
    def _load_cognito_config(self) -> Dict[str, str]:
        """Cognito設定を読み込み"""
        config_file = Path("cognito_config.json")
        if not config_file.exists():
            print("❌ cognito_config.json が見つかりません")
            print("   先に cognito_setup.py を実行してください")
            sys.exit(1)
        
        with open(config_file) as f:
            return json.load(f)
    
    def _load_api_spec(self) -> List[Dict[str, Any]]:
        """Lambda API仕様を読み込み"""
        spec_file = Path("lambda_api_spec.json")
        if not spec_file.exists():
            print("❌ lambda_api_spec.json が見つかりません")
            sys.exit(1)
        
        with open(spec_file) as f:
            return json.load(f)
    
    def create_lambda_function(self) -> str:
        """Lambda関数を作成"""
        function_name = "CustomerSupportTools"
        
        try:
            # 既存の関数をチェック
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                lambda_arn = response['Configuration']['FunctionArn']
                print(f"✅ 既存のLambda関数を使用: {lambda_arn}")
                
                # 既存の関数のコードを更新
                print("🔄 Lambda関数のコードを更新中...")
                
                # Lambda関数のコードをZIPファイルに圧縮
                zip_path = Path("lambda_function.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write("lambda_tools.py", "lambda_function.py")
                
                # ZIPファイルを読み込み
                with open(zip_path, 'rb') as f:
                    zip_content = f.read()
                
                # 関数のコードを更新
                self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
                
                # ZIPファイルを削除
                zip_path.unlink()
                
                print("✅ Lambda関数のコードを更新しました")
                return lambda_arn
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                pass
            
            print(f"🚀 Lambda関数を作成中: {function_name}")
            
            # Lambda関数のコードをZIPファイルに圧縮
            zip_path = Path("lambda_function.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write("lambda_tools.py", "lambda_function.py")
            
            # ZIPファイルを読み込み
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Lambda実行ロールを作成
            role_arn = self._create_lambda_execution_role()
            
            # Lambda関数を作成
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.12',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Customer Support Tools for AgentCore Gateway',
                Timeout=30,
                MemorySize=256
                # AWS_REGION は Lambda で自動的に設定されるため、環境変数から削除
            )
            
            lambda_arn = response['FunctionArn']
            print(f"✅ Lambda関数を作成しました: {lambda_arn}")
            
            # ZIPファイルを削除
            zip_path.unlink()
            
            return lambda_arn
            
        except Exception as e:
            print(f"❌ Lambda関数作成エラー: {e}")
            sys.exit(1)
    
    def _create_lambda_execution_role(self) -> str:
        """Lambda実行ロールを作成"""
        role_name = "CustomerSupportLambdaRole"
        
        try:
            # 既存のロールをチェック
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                print(f"✅ 既存のLambda実行ロールを使用: {role_arn}")
                return role_arn
            except self.iam_client.exceptions.NoSuchEntityException:
                pass
            
            print(f"🔐 Lambda実行ロールを作成中: {role_name}")
            
            # 信頼ポリシー
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # ロールを作成
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Customer Support Lambda function"
            )
            
            role_arn = response['Role']['Arn']
            
            # 基本実行ポリシーをアタッチ
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
            
            print(f"✅ Lambda実行ロールを作成しました: {role_arn}")
            
            # ロールの作成完了を待機
            time.sleep(10)
            
            return role_arn
            
        except Exception as e:
            print(f"❌ Lambda実行ロール作成エラー: {e}")
            sys.exit(1)
    
    def _create_gateway_execution_role(self) -> str:
        """Gateway実行ロールを作成"""
        role_name = "CustomerSupportGatewayRole"
        
        try:
            # 既存のロールをチェック
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                print(f"✅ 既存のGateway実行ロールを使用: {role_arn}")
                return role_arn
            except self.iam_client.exceptions.NoSuchEntityException:
                pass
            
            print(f"🔐 Gateway実行ロールを作成中: {role_name}")
            
            # 信頼ポリシー
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock-agentcore.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # 実行ポリシー
            execution_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "lambda:InvokeFunction"
                        ],
                        "Resource": f"arn:aws:lambda:{self.region}:{self.account_id}:function:CustomerSupportTools"
                    }
                ]
            }
            
            # ロールを作成
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Customer Support Gateway"
            )
            
            role_arn = response['Role']['Arn']
            
            # インラインポリシーを追加
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="GatewayExecutionPolicy",
                PolicyDocument=json.dumps(execution_policy)
            )
            
            print(f"✅ Gateway実行ロールを作成しました: {role_arn}")
            
            # ロールの作成完了を待機
            time.sleep(10)
            
            return role_arn
            
        except Exception as e:
            print(f"❌ Gateway実行ロール作成エラー: {e}")
            sys.exit(1)
    
    def create_gateway(self, gateway_name: str) -> Dict[str, str]:
        """AgentCore Gatewayを作成"""
        try:
            print(f"🚀 AgentCore Gateway を作成中: {gateway_name}")
            
            # Cognito設定を読み込み
            cognito_config = self._load_cognito_config()
            
            # API仕様を読み込み
            api_spec = self._load_api_spec()
            
            # Lambda関数を作成
            lambda_arn = self.create_lambda_function()
            
            # Gateway実行ロールを作成
            gateway_role_arn = self._create_gateway_execution_role()
            
            # 認証設定
            auth_config = {
                "customJWTAuthorizer": {
                    "discoveryUrl": cognito_config["discovery_url"],
                    "allowedClients": [cognito_config["client_id"]]
                }
            }
            
            # Gatewayを作成
            create_response = self.gateway_client.create_gateway(
                name=gateway_name,
                roleArn=gateway_role_arn,
                protocolType="MCP",
                authorizerType="CUSTOM_JWT",
                authorizerConfiguration=auth_config,
                description="Customer Support MCP Gateway"
            )
            
            gateway_id = create_response['gatewayId']
            gateway_url = create_response['gatewayUrl']
            gateway_arn = create_response['gatewayArn']
            
            print(f"✅ Gateway作成完了: {gateway_id}")
            
            # Lambda Target設定
            lambda_target_config = {
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {"inlinePayload": api_spec}
                    }
                }
            }
            
            # 認証情報設定
            credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
            
            # Gateway Targetを作成
            create_target_response = self.gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name="CustomerSupportTools",
                description="Customer Support Lambda Tools",
                targetConfiguration=lambda_target_config,
                credentialProviderConfigurations=credential_config
            )
            
            target_id = create_target_response['targetId']
            print(f"✅ Gateway Target作成完了: {target_id}")
            
            # 設定を保存
            gateway_config = {
                "gateway_id": gateway_id,
                "gateway_name": gateway_name,
                "gateway_url": gateway_url,
                "gateway_arn": gateway_arn,
                "target_id": target_id,
                "lambda_arn": lambda_arn
            }
            
            with open("gateway_config.json", "w") as f:
                json.dump(gateway_config, f, indent=2)
            
            print(f"✅ Gateway設定を保存しました: gateway_config.json")
            
            return gateway_config
            
        except Exception as e:
            print(f"❌ Gateway作成エラー: {e}")
            sys.exit(1)
    
    def delete_gateway(self, gateway_id: str = None) -> bool:
        """Gatewayを削除"""
        try:
            # 設定ファイルからGateway IDを取得
            if not gateway_id:
                config_file = Path("gateway_config.json")
                if config_file.exists():
                    with open(config_file) as f:
                        config = json.load(f)
                    gateway_id = config.get("gateway_id")
                
                if not gateway_id:
                    print("❌ Gateway IDが見つかりません")
                    return False
            
            print(f"🗑️  Gateway削除中: {gateway_id}")
            
            # すべてのTargetを削除
            try:
                list_response = self.gateway_client.list_gateway_targets(
                    gatewayIdentifier=gateway_id,
                    maxResults=100
                )
                
                for item in list_response["items"]:
                    target_id = item["targetId"]
                    print(f"   Target削除中: {target_id}")
                    self.gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target_id
                    )
                    print(f"   ✅ Target削除完了: {target_id}")
            except Exception as e:
                print(f"   ⚠️  Target削除エラー: {e}")
            
            # Gatewayを削除
            self.gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
            print(f"✅ Gateway削除完了: {gateway_id}")
            
            # 設定ファイルを削除
            config_file = Path("gateway_config.json")
            if config_file.exists():
                config_file.unlink()
                print("🧹 設定ファイルを削除しました")
            
            return True
            
        except Exception as e:
            print(f"❌ Gateway削除エラー: {e}")
            return False
    
    def show_config(self):
        """Gateway設定を表示"""
        config_file = Path("gateway_config.json")
        if not config_file.exists():
            print("❌ gateway_config.json が見つかりません")
            return
        
        with open(config_file) as f:
            config = json.load(f)
        
        print("📋 Gateway設定:")
        print("=" * 50)
        for key, value in config.items():
            print(f"   {key}: {value}")


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python gateway_manager.py create <gateway_name>")
        print("  python gateway_manager.py delete [gateway_id]")
        print("  python gateway_manager.py show-config")
        sys.exit(1)
    
    manager = GatewayManager()
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("❌ Gateway名を指定してください")
            sys.exit(1)
        
        gateway_name = sys.argv[2]
        config = manager.create_gateway(gateway_name)
        
        print("\n🎉 Gateway作成完了!")
        print("=" * 50)
        print(f"Gateway ID: {config['gateway_id']}")
        print(f"Gateway URL: {config['gateway_url']}")
        print(f"Target ID: {config['target_id']}")
        
    elif command == "delete":
        gateway_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        if manager.delete_gateway(gateway_id):
            print("🎉 Gateway削除完了!")
        else:
            print("❌ Gateway削除に失敗しました")
            sys.exit(1)
    
    elif command == "show-config":
        manager.show_config()
    
    else:
        print(f"❌ 不明なコマンド: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()