#!/usr/bin/env python3
"""
Memory アクセス権限の自動設定スクリプト
既存の設定ファイルから情報を取得して、IAM権限を一発で設定します。
"""

import json
import boto3
import subprocess
import sys
from pathlib import Path

def get_aws_account_id():
    """現在のAWSアカウントIDを取得"""
    try:
        sts = boto3.client('sts')
        return sts.get_caller_identity()['Account']
    except Exception as e:
        print(f"❌ AWSアカウントID取得エラー: {e}")
        sys.exit(1)

def get_aws_region():
    """現在のAWSリージョンを取得"""
    try:
        session = boto3.Session()
        return session.region_name or 'us-east-1'
    except Exception:
        return 'us-east-1'

def load_memory_config():
    """memory_config.jsonからMemory IDを取得"""
    config_file = Path("memory_config.json")
    if not config_file.exists():
        print("❌ memory_config.json が見つかりません")
        print("   先に setup_memory.py を実行してください")
        sys.exit(1)
    
    with open(config_file) as f:
        config = json.load(f)
    
    memory_id = config.get('memory_id')
    if not memory_id:
        print("❌ memory_config.json に memory_id が見つかりません")
        sys.exit(1)
    
    return memory_id

def get_current_agent_role():
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

def get_agentcore_runtime_role():
    """AgentCore Runtime Roleを自動検出"""
    try:
        iam = boto3.client('iam')
        response = iam.list_roles()
        
        runtime_roles = [
            role for role in response['Roles']
            if 'AmazonBedrockAgentCoreSDKRuntime' in role['RoleName']
        ]
        
        if not runtime_roles:
            print("❌ AgentCore Runtime Role が見つかりません")
            print("   先に agentcore configure を実行してください")
            sys.exit(1)
        
        # 現在のエージェント設定から使用中のRoleを取得
        current_role = get_current_agent_role()
        if current_role:
            for role in runtime_roles:
                if role['RoleName'] == current_role:
                    print(f"🎯 現在のエージェント設定から使用中のRoleを検出: {current_role}")
                    return current_role
        
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

def create_memory_policy(account_id, region, memory_id):
    """Memory アクセス用のIAMポリシーを作成"""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:ListMemories",
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:GetMemoryRecord",
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:SaveConversation",
                    "bedrock-agentcore:GetLastKTurns",
                    "bedrock-agentcore:RetrieveMemories"
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{memory_id}*"
                ]
            }
        ]
    }
    
    # ポリシーファイルを作成
    policy_file = Path("memory-policy.json")
    with open(policy_file, 'w') as f:
        json.dump(policy, f, indent=2)
    
    print(f"✅ ポリシーファイルを作成しました: {policy_file}")
    return policy_file

def setup_iam_permissions():
    """IAM権限を自動設定"""
    print("🚀 Memory アクセス権限の自動設定を開始します...")
    print("=" * 50)
    
    # 設定情報を取得
    account_id = get_aws_account_id()
    region = get_aws_region()
    memory_id = load_memory_config()
    role_name = get_agentcore_runtime_role()
    
    print(f"📋 設定情報:")
    print(f"   AWSアカウントID: {account_id}")
    print(f"   リージョン: {region}")
    print(f"   Memory ID: {memory_id}")
    print(f"   Runtime Role: {role_name}")
    print()
    
    # ポリシーファイルを作成
    policy_file = create_memory_policy(account_id, region, memory_id)
    
    # IAMポリシーを作成またはアップデート
    policy_name = "BedrockAgentCoreMemoryAccess"
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    
    try:
        iam = boto3.client('iam')
        
        # ポリシーが既に存在するかチェック
        try:
            iam.get_policy(PolicyArn=policy_arn)
            print(f"📝 既存のポリシーを更新します: {policy_name}")
            
            # 新しいバージョンを作成
            with open(policy_file) as f:
                policy_document = f.read()
            
            iam.create_policy_version(
                PolicyArn=policy_arn,
                PolicyDocument=policy_document,
                SetAsDefault=True
            )
            print("✅ ポリシーを更新しました")
            
        except iam.exceptions.NoSuchEntityException:
            print(f"🆕 新しいポリシーを作成します: {policy_name}")
            
            with open(policy_file) as f:
                policy_document = f.read()
            
            iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=policy_document,
                Description="AgentCore Memory access permissions"
            )
            print("✅ ポリシーを作成しました")
        
        # ロールにポリシーをアタッチ
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"✅ ポリシーをロールにアタッチしました: {role_name}")
        except iam.exceptions.PolicyNotAttachableException:
            print("ℹ️  ポリシーは既にアタッチされています")
        
        print()
        print("🎉 Memory アクセス権限の設定が完了しました！")
        print("   数分待ってからテストを実行してください。")
        
    except Exception as e:
        print(f"❌ IAM設定エラー: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Memory アクセス権限の自動設定スクリプト")
        print()
        print("使用方法:")
        print("  python setup_memory_permissions.py")
        print()
        print("前提条件:")
        print("  - memory_config.json が存在すること")
        print("  - AgentCore Runtime Role が作成済みであること")
        print("  - AWS CLI が設定済みであること")
        return
    
    setup_iam_permissions()

if __name__ == "__main__":
    main()