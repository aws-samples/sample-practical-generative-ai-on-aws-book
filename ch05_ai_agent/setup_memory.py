#!/usr/bin/env python3
"""
Memory リソースのセットアップスクリプト
一度だけ実行し、出力された Memory ID を記録してください。
"""

from bedrock_agentcore.memory import MemoryClient
import json
import sys

def create_support_memory():
    """カスタマーサポート用 Memory リソースを作成"""
    
    # Memory クライアントを初期化（リージョンは自動検出）
    memory_client = MemoryClient()
    
    # 既存の Memory をチェック
    existing_memories = list(memory_client.list_memories())
    for mem in existing_memories:
        if mem.get('name') == 'CustomerSupportMemory':
            print(f"既存の Memory が見つかりました: {mem.get('id')}")
            return mem.get('id')
    
    print("新しい Memory リソースを作成中...")
    
    # 長期記憶戦略を含む Memory を作成
    # IAM ロールは自動的に作成・設定される
    memory = memory_client.create_memory_and_wait(
        name="CustomerSupportMemory",
        description="顧客サポート会話の記憶管理",
        strategies=[
            {
                "userPreferenceMemoryStrategy": {
                    "name": "CustomerPreferences",
                    "namespaces": ["/preferences/{actorId}"]
                }
            },
            {
                "semanticMemoryStrategy": {
                    "name": "ProductIssues",
                    "namespaces": ["/issues/{actorId}/products"]
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SessionSummarizer",
                    "namespaces": ["/summaries/{actorId}/{sessionId}"]
                }
            }
        ]
    )
    
    memory_id = memory.get('id')
    print(f"Memory が正常に作成されました!")
    print(f"Memory ID: {memory_id}")
    
    # 設定ファイルに保存
    config = {"memory_id": memory_id}
    with open("memory_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"設定が memory_config.json に保存されました")
    return memory_id

if __name__ == "__main__":
    try:
        memory_id = create_support_memory()
        print(f"\n✅ セットアップ完了")
        print(f"Memory ID: {memory_id}")
    except Exception as e:
        print(f"❌ エラー: {str(e)}", file=sys.stderr)
        sys.exit(1)