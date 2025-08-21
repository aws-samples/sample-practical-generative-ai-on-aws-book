#!/usr/bin/env python3
"""
AgentCore Gateway テストスクリプト
Gateway 経由での MCP ツール呼び出しをテスト
"""

import json
import sys
import boto3
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import uuid


class GatewayTester:
    def __init__(self):
        self.gateway_config = self._load_gateway_config()
        self.cognito_config = self._load_cognito_config()
        self.region = self._get_aws_region()
        
        print(f"🌍 リージョン: {self.region}")
        print(f"🌐 Gateway URL: {self.gateway_config['gateway_url']}")
    
    def _get_aws_region(self) -> str:
        """現在のAWSリージョンを取得"""
        try:
            session = boto3.Session()
            return session.region_name or 'us-east-1'
        except Exception:
            return 'us-east-1'
    
    def _load_gateway_config(self) -> Dict[str, Any]:
        """Gateway設定を読み込み"""
        config_file = Path("gateway_config.json")
        if not config_file.exists():
            print("❌ gateway_config.json が見つかりません")
            print("   先に gateway_manager.py create を実行してください")
            sys.exit(1)
        
        with open(config_file) as f:
            return json.load(f)
    
    def _load_cognito_config(self) -> Dict[str, Any]:
        """Cognito設定を読み込み"""
        config_file = Path("cognito_config.json")
        if not config_file.exists():
            print("❌ cognito_config.json が見つかりません")
            print("   先に cognito_setup.py を実行してください")
            sys.exit(1)
        
        with open(config_file) as f:
            return json.load(f)
    
    def _get_access_token(self) -> str:
        """Cognito からアクセストークンを取得"""
        try:
            # テストユーザー設定を読み込み
            test_config_file = Path("test_user_config.json")
            if test_config_file.exists():
                with open(test_config_file) as f:
                    test_config = json.load(f)
                
                # 保存されたアクセストークンを使用
                access_token = test_config.get("access_token")
                if access_token:
                    print(f"✅ 保存されたアクセストークンを使用")
                    return access_token
            
            # テストユーザー設定がない場合は新規認証
            cognito_client = boto3.client('cognito-idp', region_name=self.region)
            
            # テスト用の認証情報
            username = "test@example.com"
            password = "TempPassword123!"
            
            auth_params = {
                'USERNAME': username,
                'PASSWORD': password
            }
            
            # SECRET_HASH が必要な場合は追加
            if self.cognito_config.get("client_secret"):
                import hmac
                import hashlib
                import base64
                
                message = username + self.cognito_config["client_id"]
                secret_hash = base64.b64encode(
                    hmac.new(
                        self.cognito_config["client_secret"].encode(),
                        message.encode(),
                        digestmod=hashlib.sha256
                    ).digest()
                ).decode()
                auth_params['SECRET_HASH'] = secret_hash
            
            # 認証を実行
            response = cognito_client.admin_initiate_auth(
                UserPoolId=self.cognito_config["user_pool_id"],
                ClientId=self.cognito_config["client_id"],
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters=auth_params
            )
            
            access_token = response['AuthenticationResult']['AccessToken']
            print(f"✅ アクセストークンを取得しました")
            return access_token
            
        except Exception as e:
            print(f"❌ アクセストークン取得エラー: {e}")
            print("   テスト用ユーザーが作成されていない可能性があります")
            print("   python cognito_setup.py create-test-user --username test@example.com を実行してください")
            # デモ用のダミートークンを返す
            return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.demo_token_for_testing"
    
    def test_mcp_list_tools(self, use_auth: bool = True) -> Dict[str, Any]:
        """MCP listTools を呼び出してテスト"""
        try:
            print(f"🔧 MCP listTools テスト (認証: {'有効' if use_auth else '無効'})")
            
            headers = {
                "Content-Type": "application/json"
            }
            
            if use_auth:
                access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {access_token}"
            
            # MCP listTools リクエスト
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list",
                "params": {}
            }
            
            response = requests.post(
                self.gateway_config["gateway_url"],
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"📤 リクエスト: {json.dumps(payload, indent=2)}")
            print(f"📥 レスポンス: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ listTools 成功!")
                return result
            else:
                print(f"❌ listTools 失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ listTools テストエラー: {e}")
            return {"error": str(e)}
    
    def test_mcp_invoke_tool(self, tool_name: str, arguments: Dict[str, Any], use_auth: bool = True) -> Dict[str, Any]:
        """MCP invokeTool を呼び出してテスト"""
        try:
            print(f"🔧 MCP invokeTool テスト: {tool_name} (認証: {'有効' if use_auth else '無効'})")
            
            headers = {
                "Content-Type": "application/json"
            }
            
            if use_auth:
                access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {access_token}"
            
            # MCP invokeTool リクエスト
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = requests.post(
                self.gateway_config["gateway_url"],
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"📤 リクエスト: {json.dumps(payload, indent=2)}")
            print(f"📥 レスポンス: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ invokeTool 成功!")
                return result
            else:
                print(f"❌ invokeTool 失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"❌ invokeTool テストエラー: {e}")
            return {"error": str(e)}
    
    def run_comprehensive_test(self):
        """包括的なテストを実行"""
        print("🚀 AgentCore Gateway 包括テスト開始")
        print("=" * 60)
        
        # 1. listTools テスト（認証あり）
        print("\n1️⃣  listTools テスト（認証あり）")
        print("-" * 40)
        list_result = self.test_mcp_list_tools(use_auth=True)
        
        if "error" not in list_result:
            tools = list_result.get("result", {}).get("tools", [])
            print(f"   利用可能なツール数: {len(tools)}")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # 2. 各ツールのテスト
        test_cases = [
            {
                "name": "get_order_history",
                "arguments": {"customer_id": "customer_oauth_verified", "limit": 3},
                "description": "注文履歴取得テスト"
            },
            {
                "name": "get_product_info",
                "arguments": {"product_name": "スマートフォン"},
                "description": "製品情報取得テスト"
            },
            {
                "name": "check_shipping_status",
                "arguments": {"order_id": "ORD-2024-001"},
                "description": "配送状況確認テスト"
            },
            {
                "name": "get_support_faq",
                "arguments": {"query": "保証"},
                "description": "FAQ検索テスト"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 2):
            print(f"\n{i}️⃣  {test_case['description']}")
            print("-" * 40)
            
            result = self.test_mcp_invoke_tool(
                tool_name=test_case["name"],
                arguments=test_case["arguments"],
                use_auth=True
            )
            
            if "error" not in result:
                content = result.get("result", {}).get("content", [])
                if content:
                    for item in content:
                        if item.get("type") == "text":
                            text = item.get("text", "")
                            # 長いテキストは省略
                            if len(text) > 200:
                                text = text[:200] + "..."
                            print(f"   結果: {text}")
        
        # 3. 認証なしテスト
        print(f"\n{len(test_cases) + 2}️⃣  認証なしテスト")
        print("-" * 40)
        unauth_result = self.test_mcp_list_tools(use_auth=False)
        
        if "error" in unauth_result:
            print("✅ 認証なしリクエストは正しく拒否されました")
        else:
            print("⚠️  認証なしリクエストが通ってしまいました")
        
        print("\n🎉 包括テスト完了!")
    
    def show_config(self):
        """設定情報を表示"""
        print("📋 Gateway設定:")
        print("=" * 50)
        for key, value in self.gateway_config.items():
            print(f"   {key}: {value}")
        
        print("\n📋 Cognito設定:")
        print("=" * 50)
        for key, value in self.cognito_config.items():
            if "secret" not in key.lower():  # シークレット情報は表示しない
                print(f"   {key}: {value}")


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_gateway.py list-tools [--no-auth]")
        print("  python test_gateway.py invoke-tool <tool_name> <arguments_json> [--no-auth]")
        print("  python test_gateway.py comprehensive")
        print("  python test_gateway.py show-config")
        print()
        print("例:")
        print('  python test_gateway.py invoke-tool get_order_history \'{"customer_id": "test123"}\'')
        print("  python test_gateway.py comprehensive")
        sys.exit(1)
    
    tester = GatewayTester()
    command = sys.argv[1]
    
    if command == "list-tools":
        use_auth = "--no-auth" not in sys.argv
        result = tester.test_mcp_list_tools(use_auth=use_auth)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == "invoke-tool":
        if len(sys.argv) < 4:
            print("❌ ツール名と引数を指定してください")
            sys.exit(1)
        
        tool_name = sys.argv[2]
        try:
            arguments = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            print("❌ 引数は有効なJSONで指定してください")
            sys.exit(1)
        
        use_auth = "--no-auth" not in sys.argv
        result = tester.test_mcp_invoke_tool(tool_name, arguments, use_auth=use_auth)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == "comprehensive":
        tester.run_comprehensive_test()
    
    elif command == "show-config":
        tester.show_config()
    
    else:
        print(f"❌ 不明なコマンド: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()