#!/usr/bin/env python3
"""
AgentCore Built-in Tools 権限設定スクリプト
Code Interpreter と Browser Tool の使用に必要な IAM 権限を自動設定
"""

import json
import boto3
import sys
import time
from pathlib import Path
from typing import Dict, Any


class BuiltinToolsPermissionManager:
    def __init__(self):
        self.region = self._get_aws_region()
        self.account_id = self._get_aws_account_id()
        
        # AWS クライアントを初期化
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
    
    def _get_current_agent_role(self) -> str:
        """現在のエージェント設定から使用中のRoleを取得"""
        try:
            # .bedrock_agentcore.yaml から現在のRole情報を取得
            agentcore_config = Path(".bedrock_agentcore.yaml")
            if agentcore_config.exists():
                import yaml
                with open(agentcore_config) as f:
                    config = yaml.safe_load(f)
                
                # デフォルトエージェントを取得
                default_agent = config.get('default_agent')
                if default_agent and 'agents' in config:
                    agent_config = config['agents'].get(default_agent, {})
                    aws_config = agent_config.get('aws', {})
                    execution_role = aws_config.get('execution_role')
                    
                    if execution_role:
                        # ARNからRole名を抽出
                        role_name = execution_role.split('/')[-1]
                        return role_name
            
            # 古い形式の .agentcore.yaml もチェック
            old_config = Path(".agentcore.yaml")
            if old_config.exists():
                import yaml
                with open(old_config) as f:
                    config = yaml.safe_load(f)
                
                execution_role = config.get('executionRole')
                if execution_role:
                    role_name = execution_role.split('/')[-1]
                    return role_name
                    
        except Exception:
            pass
        
        return None
    
    def _get_agentcore_runtime_role(self) -> str:
        """AgentCore Runtime Roleを自動検出"""
        try:
            # 現在のエージェント設定から使用中のRoleを取得
            current_role = self._get_current_agent_role()
            if current_role:
                try:
                    response = self.iam_client.get_role(RoleName=current_role)
                    print(f"🎯 現在のエージェント設定から使用中のRoleを検出: {current_role}")
                    return current_role
                except self.iam_client.exceptions.NoSuchEntityException:
                    pass
            
            # 自動検出できない場合は一覧から選択
            response = self.iam_client.list_roles()
            
            runtime_roles = [
                role for role in response['Roles']
                if 'AmazonBedrockAgentCoreSDKRuntime' in role['RoleName']
            ]
            
            if not runtime_roles:
                print("❌ AgentCore Runtime Role が見つかりません")
                print("   先に agentcore configure を実行してください")
                sys.exit(1)
            
            if len(runtime_roles) > 1:
                print("🔍 複数のRuntime Roleが見つかりました:")
                for i, role in enumerate(runtime_roles):
                    print(f"   {i+1}. {role['RoleName']}")
                
                while True:
                    try:
                        choice = int(input("使用するRoleの番号を選択してください: ")) - 1
                        if 0 <= choice < len(runtime_roles):
                            return runtime_roles[choice]['RoleName']
                        else:
                            print("❌ 無効な選択です")
                    except ValueError:
                        print("❌ 数字を入力してください")
            
            return runtime_roles[0]['RoleName']
            
        except Exception as e:
            print(f"❌ Runtime Role取得エラー: {e}")
            sys.exit(1)
    
    def create_builtin_tools_policy(self) -> str:
        """Built-in Tools アクセス用のIAMポリシーを作成"""
        policy_name = "BedrockAgentCoreBuiltinToolsAccess"
        
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CodeInterpreterAccess",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:CreateCodeInterpreter",
                        "bedrock-agentcore:StartCodeInterpreterSession",
                        "bedrock-agentcore:InvokeCodeInterpreter",
                        "bedrock-agentcore:StopCodeInterpreterSession",
                        "bedrock-agentcore:DeleteCodeInterpreter",
                        "bedrock-agentcore:ListCodeInterpreters",
                        "bedrock-agentcore:GetCodeInterpreter"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "BrowserToolAccess",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:CreateBrowserTool",
                        "bedrock-agentcore:StartBrowserToolSession",
                        "bedrock-agentcore:InvokeBrowserTool",
                        "bedrock-agentcore:StopBrowserToolSession",
                        "bedrock-agentcore:DeleteBrowserTool",
                        "bedrock-agentcore:ListBrowserTools",
                        "bedrock-agentcore:GetBrowserTool"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "CloudWatchLogsAccess",
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": [
                        f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/bedrock-agentcore/code-interpreter*",
                        f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/bedrock-agentcore/browser-tool*"
                    ]
                }
            ]
        }
        
        try:
            # 既存のポリシーをチェック
            policy_arn = f"arn:aws:iam::{self.account_id}:policy/{policy_name}"
            
            try:
                self.iam_client.get_policy(PolicyArn=policy_arn)
                print(f"📝 既存のポリシーを更新します: {policy_name}")
                
                # 新しいバージョンを作成
                self.iam_client.create_policy_version(
                    PolicyArn=policy_arn,
                    PolicyDocument=json.dumps(policy_document),
                    SetAsDefault=True
                )
                print("✅ ポリシーを更新しました")
                
            except self.iam_client.exceptions.NoSuchEntityException:
                print(f"🆕 新しいポリシーを作成します: {policy_name}")
                
                self.iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_document),
                    Description="AgentCore Built-in Tools access permissions"
                )
                print("✅ ポリシーを作成しました")
            
            return policy_arn
            
        except Exception as e:
            print(f"❌ ポリシー作成エラー: {e}")
            sys.exit(1)
    
    def setup_permissions(self):
        """Built-in Tools の権限を自動設定"""
        print("🚀 Built-in Tools アクセス権限の自動設定を開始します...")
        print("=" * 60)
        
        # Runtime Role を取得
        role_name = self._get_agentcore_runtime_role()
        
        print(f"📋 設定情報:")
        print(f"   AWSアカウントID: {self.account_id}")
        print(f"   リージョン: {self.region}")
        print(f"   Runtime Role: {role_name}")
        print()
        
        # Built-in Tools ポリシーを作成
        policy_arn = self.create_builtin_tools_policy()
        
        # ロールにポリシーをアタッチ
        try:
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"✅ ポリシーをロールにアタッチしました: {role_name}")
        except Exception as e:
            if "PolicyNotAttachable" in str(e):
                print("ℹ️  ポリシーは既にアタッチされています")
            else:
                print(f"❌ ポリシーアタッチエラー: {e}")
                sys.exit(1)
        
        print()
        print("🎉 Built-in Tools アクセス権限の設定が完了しました！")
        print("   Code Interpreter と Browser Tool が使用可能になりました。")
        
        # 設定を保存
        config = {
            "policy_arn": policy_arn,
            "role_name": role_name,
            "region": self.region,
            "account_id": self.account_id
        }
        
        with open("builtin_tools_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ 設定が builtin_tools_config.json に保存されました")
    
    def show_config(self):
        """Built-in Tools 設定を表示"""
        config_file = Path("builtin_tools_config.json")
        if not config_file.exists():
            print("❌ builtin_tools_config.json が見つかりません")
            return
        
        with open(config_file) as f:
            config = json.load(f)
        
        print("📋 Built-in Tools 設定:")
        print("=" * 50)
        for key, value in config.items():
            print(f"   {key}: {value}")
    
    def test_permissions(self):
        """権限設定をテスト"""
        print("🧪 Built-in Tools 権限テスト開始...")
        print("=" * 50)
        
        try:
            # Code Interpreter のテスト
            print("1️⃣  Code Interpreter 権限テスト")
            from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
            
            code_client = CodeInterpreter(self.region)
            print("✅ Code Interpreter クライアント作成成功")
            
            # Browser Tool のテスト
            print("2️⃣  Browser Tool 権限テスト")
            from bedrock_agentcore.tools.browser_tool_client import BrowserTool
            
            browser_client = BrowserTool(self.region)
            print("✅ Browser Tool クライアント作成成功")
            
            print("\n🎉 権限テスト完了！Built-in Tools が使用可能です。")
            
        except Exception as e:
            print(f"❌ 権限テストエラー: {e}")
            print("   権限設定を確認してください")


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python setup_builtin_tools_permissions.py setup")
        print("  python setup_builtin_tools_permissions.py show-config")
        print("  python setup_builtin_tools_permissions.py test")
        sys.exit(1)
    
    manager = BuiltinToolsPermissionManager()
    command = sys.argv[1]
    
    if command == "setup":
        manager.setup_permissions()
    
    elif command == "show-config":
        manager.show_config()
    
    elif command == "test":
        manager.test_permissions()
    
    else:
        print(f"❌ 不明なコマンド: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()