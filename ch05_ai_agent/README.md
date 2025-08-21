# Amazon Bedrock AgentCore ハンズオン
ここでは、書籍「[AWS生成AIアプリ構築実践ガイド](https://www.amazon.co.jp/dp/4296205234)」の5章「AIエージェント」で紹介した Amazon Bedrock AgentCore について、5.6.2 項にあるカスタマーサポートエージェントの構築例をハンズオン形式で学びます。

AgentCore の利用方法を、カスタマーサポートのシナリオで紹介します。顧客からメールでの問い合わせがあった際、サポートチームは以下の作業をする必要があります: 
- メールの妥当性確認
- CRM システムでの顧客特定
- 注文履歴の確認
- 製品固有のナレッジベースでの情報検索
- 回答の準備

AI エージェントは、内部システムに接続し、セマンティックデータソースを使用してコンテキスト情報を取得し、サポートチームの回答草案を作成することで、このプロセスを簡素化できます。

本節では、Strands Agents を使用したシンプルなプロトタイプから、Amazon Bedrock AgentCore を活用してエンタープライズ対応のプロダクションシステムまでを段階的に構築する過程を説明します。
実装の流れ (概要) については書籍を参照してください。

## 詳細な実装方法
このハンズオンでは、Strands Agents とツールで構築したカスタマーサポートエージェントのプロトタイプを、安全で信頼できるスケーラブルなアプリケーションとして step-by-step で書き換えていきます: 
1. [クラウドデプロイ](#step-1-agentcore-runtime-でクラウドにデプロイ): AgentCore Runtime によるセキュアなサーバーレス環境へのデプロイ
1. [コンテキスト管理](#step-2-agentcore-memory-によるコンテキスト管理): AgentCore Memory による会話記憶機能の実装
1. [アクセス制御](#step-3-agentcore-identity-による認証と認可の統合): AgentCore Identity による認証と認可の統合
1. [システム統合](#step-4-agentcore-gateway-による-mcp-ツール統合): AgentCore Gateway による MCP や API 経由での CRM などへの連携
1. 高度な機能: AgentCore Code Interpreter と Browser Tools による計算処理と Web 自動化
1. 運用監視: AgentCore Observability によるパフォーマンス監視とデバッグ

このハンズオンを通じて、プロトタイプから本格的なプロダクション環境まで対応可能な、スケーラブルで安全なAIエージェントシステムの構築方法を学習できます。

## 事前準備
まず、今回のハンズオンで使う仮想環境を作ります。

### 環境セットアップ
```bash
# Python仮想環境の作成
python -m venv agentcore-env
source agentcore-env/bin/activate  

# 必要なパッケージのインストール
pip install boto3 botocore -U 
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit strands-agents strands-agents-tools
```

## Step 1: AgentCore Runtime でクラウドにデプロイ
### 基本的なエージェントプロトタイプの作成
まず、シンプルなカスタマーサポートエージェントを作成します。
[`customer_support_agent.py`](./customer_support_agent.py) として、以下のスクリプトを用意してあります。

```Python
from strands import Agent, tool
from strands_tools import calculator, current_time
from strands.models import BedrockModel
# AgentCore SDK をインポート
from bedrock_agentcore.runtime import BedrockAgentCoreApp

WELCOME_MESSAGE = """
カスタマーサポートアシスタントへようこそ！本日はどのようなご用件でしょうか？
"""

SYSTEM_PROMPT = """
あなたは親切なカスタマーサポートアシスタントです。
顧客からのメールが提供された場合、必要な情報をすべて収集し、返信メールを準備してください。
注文について質問された場合、注文を検索し、注文の詳細と日付をお客様にお伝えください。
返信では顧客IDを言及しないでください。
"""

@tool
def get_customer_id(email_address: str):
    """メールアドレスから顧客IDを取得します"""
    if email_address == "me@example.net":
        return {"customer_id": 123}
    else:
        return {"message": "顧客が見つかりません"}

@tool  
def get_orders(customer_id: int):
    """顧客IDから注文履歴を取得します"""
    if customer_id == 123:
        return [{
        # return {"orders": [{
            "order_id": 1234,
            "items": ["スマートフォン", "スマートフォン USB-C 充電器", "スマートフォン 黒色カバー"],
            "date": "20250607"
        # }]}
        }]
    else:
        return {"message": "注文が見つかりません"}

@tool
def get_knowledge_base_info(topic: str):
    """トピックに関する知識ベース情報を取得します"""
    kb_info = []
    if "スマートフォン" in topic:
        if "カバー" in topic:
            kb_info.append("カバーを装着するには、まず底部を挿入し、次に背面から上部まで押し込みます。")
            kb_info.append("カバーを取り外すには、カバーの上部と下部を同時に押してください。")
        if "充電器" in topic:
            kb_info.append("入力: 100-240V AC、50/60Hz")
            kb_info.append("US/UK/EU プラグアダプター付属")
    if len(kb_info) > 0:
        return kb_info
        # return {"info": kb_info}
    else:
        return {"message": "情報が見つかりません"}

# AgentCore アプリを作成
app = BedrockAgentCoreApp()

agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[calculator, current_time, get_customer_id, get_orders, get_knowledge_base_info]
)

# エントリーポイント関数を指定
@app.entrypoint
def invoke(payload):
    """エージェント呼び出しのハンドラー"""
    user_message = payload.get(
        "prompt", 
        "入力にプロンプトが見つかりません。プロンプトキーを含むJSONペイロードを作成してください"
    )
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

### デプロイ
リモート環境で使われる Docker コンテナ内で必要となるパッケージインストールのため、[`requirements.txt`](./requirements.txt) を以下のように用意しておきます: 
```txt
strands-agents
strands-agents-tools
bedrock-agentcore
```

先ほど作った IAM ロールを指定し、AgentCore の設定を行います。
```bash
# 上記で作成したロールARNを使用してエージェントの設定
agentcore configure --entrypoint customer_support_agent.py 
```

以下のコマンドを実行すると、Docker コンテナの中で Bedrock AgentCore アプリが起動します。
```bash
# ローカルでの起動
agentcore launch --local
```
別のターミナルを開き (先程作った pyenv `agentcore-env` 環境を `source agentcore-env/bin/activate` で有効化しておきましょう)、次のコマンドで実際にエージェントを呼び出します。
```bash
# 別のターミナルでテスト
agentcore invoke --local '{
    "prompt": "差出人: me@example.net - スマートフォンの充電器について、ヨーロッパでも使用できますか？"
}'
```

> [!TIP]
> もし、ローカル実行の際に必要以上に時間がかかるようであれば、上の `agentcore configure` の際に `--disable-otel` オプションを指定することで OpenTelemetry を無効化するとスムーズに実行されるかもしれません。
> ```bash
> agentcore configure --entrypoint customer_support_agent.py --disable-otel 
> ```

実行結果例: 
```
{
  "result": "お問い合わせありがとうございます。お客様のスマートフォン充電器は100-240V AC, 50/60Hzに対応しており、US/UK/EUプラグアダプターが付属しているため、ヨーロッパでも問題なくご使用いただけます。安心してご旅行をお楽しみください。"
}
```

同様に、 `--local` オプションを外すとクラウドにデプロイできます。
```bash
# クラウドへのデプロイ
agentcore launch 

# 別のターミナルでテスト
agentcore invoke '{
    "prompt": "差出人: me@example.net - スマートフォンの充電器について、ヨーロッパでも使用できますか？"
}'
```

## Step 2: AgentCore Memory によるコンテキスト管理
### 会話記憶機能の実装
顧客サポートでは、以前の会話履歴や顧客の過去の問題を覚えておくことが重要です。AgentCore Memory を活用して、短期記憶と長期記憶を実装しましょう。

### 2.1 Memory リソースのセットアップ
まず、Memory リソースを作成するセットアップスクリプトを実行します。

`setup_memory.py`:
```python
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
```

### 2.2 MemoryHook の実装
Memory の管理を自動化する Hook を実装します。Memory hook 方式を採用することで実装を分離し、より保守性が高く、拡張可能なエージェントを構築できます。

`memory_hook_provider.py`:
```python
"""
Memory Hook Provider
会話を自動的に Memory に保存し、過去の記憶を取得する
"""

from bedrock_agentcore.memory import MemoryClient
from strands.hooks.events import AgentInitializedEvent, MessageAddedEvent
from strands.hooks.registry import HookProvider, HookRegistry
import copy


class MemoryHook(HookProvider):
    """Memory 管理を自動化する Hook"""
    
    def __init__(
        self,
        memory_client: MemoryClient,
        memory_id: str,
        actor_id: str,
        session_id: str,
    ):
        """
        Args:
            memory_client: Memory クライアント
            memory_id: Memory リソース ID
            actor_id: アクター（顧客）ID
            session_id: セッション ID
        """
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id

    def on_agent_initialized(self, event: AgentInitializedEvent):
        """エージェント初期化時に最近の会話履歴を読み込む"""
        try:
            # Memory から最新の5ターンの会話を取得
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                k=5,
            )

            if recent_turns:
                # 会話履歴をコンテキスト用にフォーマット
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = "assistant" if message["role"] == "ASSISTANT" else "user"
                        content = message["content"]["text"]
                        context_messages.append(
                            {"role": role, "content": [{"text": content}]}
                        )

                # エージェントのシステムプロンプトにコンテキストを追加
                event.agent.system_prompt += """
                ユーザーの嗜好や事実を直接回答しないでください。
                ユーザーの嗜好や事実は、ユーザーをより理解するために厳密に使用してください。
                また、この情報は古い可能性があることに注意してください。
                """
                event.agent.messages = context_messages

        except Exception as e:
            print(f"Memory 読み込みエラー: {e}")

    def _add_context_user_query(
        self, namespace: str, query: str, init_content: str, event: MessageAddedEvent
    ):
        """ユーザークエリにコンテキストを追加"""
        content = None
        memories = self.memory_client.retrieve_memories(
            memory_id=self.memory_id, namespace=namespace, query=query, top_k=3
        )

        for memory in memories:
            if not content:
                content = "\n\n" + init_content + "\n\n"

            content += memory["content"]["text"]

            if content:
                event.agent.messages[-1]["content"][0]["text"] += content + "\n\n"

    def on_message_added(self, event: MessageAddedEvent):
        """メッセージが追加された時にMemoryに保存"""
        messages = copy.deepcopy(event.agent.messages)
        try:
            if messages[-1]["role"] == "user" or messages[-1]["role"] == "assistant":
                if "text" not in messages[-1]["content"][0]:
                    return

                if messages[-1]["role"] == "user":
                    # ユーザーの嗜好を取得してコンテキストに追加
                    self._add_context_user_query(
                        namespace=f"support/user/{self.actor_id}/preferences",
                        query=messages[-1]["content"][0]["text"],
                        init_content="これらはユーザーの嗜好です:",
                        event=event,
                    )

                    # ユーザーの事実を取得してコンテキストに追加
                    self._add_context_user_query(
                        namespace=f"support/user/{self.actor_id}/facts",
                        query=messages[-1]["content"][0]["text"],
                        init_content="これらはユーザーの事実です:",
                        event=event,
                    )
                
                # 会話をMemoryに保存
                self.memory_client.save_conversation(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=[
                        (messages[-1]["content"][0]["text"], messages[-1]["role"])
                    ],
                )

        except Exception as e:
            raise RuntimeError(f"Memory 保存エラー: {e}")

    def register_hooks(self, registry: HookRegistry):
        """フックをレジストリに登録"""
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
```


### 2.3 Memory Hook を使用するエージェント

`customer_support_agent_with_memory.py`:

```python
from strands import Agent, tool
from strands_tools import calculator, current_time
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from memory_hook_provider import MemoryHook
import json
import time
import re
import hashlib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Memory 設定を読み込み
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

SYSTEM_PROMPT = """
あなたは親切なカスタマーサポートアシスタントです。
顧客との過去の会話や問題解決履歴を覚えており、パーソナライズされたサポートを提供します。
過去の会話履歴がある場合は、それを参考にして適切な対応を行ってください。
"""

# 既存のツール（Step 1から継承）
@tool
def get_customer_id(email_address: str):
    """メールアドレスから顧客IDを取得します"""
    if email_address == "me@example.net":
        return {"customer_id": 123}
    else:
        return {"message": "顧客が見つかりません"}

@tool  
def get_orders(customer_id: int):
    """顧客IDから注文履歴を取得します"""
    if customer_id == 123:
        return [{
            "order_id": 1234,
            "items": ["スマートフォン", "スマートフォン USB-C 充電器", "スマートフォン 黒色カバー"],
            "date": "20250607"
        }]
    else:
        return {"message": "注文が見つかりません"}

@tool
def get_knowledge_base_info(topic: str):
    """トピックに関する知識ベース情報を取得します"""
    kb_info = []
    if "スマートフォン" in topic:
        if "カバー" in topic:
            kb_info.append("カバーを装着するには、まず底部を挿入し、次に背面から上部まで押し込みます。")
        if "充電器" in topic:
            kb_info.append("入力: 100-240V AC、50/60Hz")
            kb_info.append("US/UK/EU プラグアダプター付属")
    return kb_info if kb_info else {"message": "情報が見つかりません"}

app = BedrockAgentCoreApp()

def setup_agent_with_memory(actor_id: str, session_id: str):
    """Memory Hook を設定したエージェントを作成"""
    
    # Memory クライアントを初期化
    memory_client = MemoryClient()
    
    # Memory Hook を作成
    memory_hook = MemoryHook(
        memory_client=memory_client,
        memory_id=MEMORY_ID,
        actor_id=actor_id,
        session_id=session_id,
        namespace=f"/preferences/{actor_id}"
    )
    
    # Hook を含むエージェントを作成
    agent = Agent(
        hooks=[memory_hook],  # Memory Hook を追加
        tools=[
            calculator,
            current_time,
            get_customer_id,
            get_orders,
            get_knowledge_base_info
        ],
        system_prompt=SYSTEM_PROMPT
    )
    
    return agent, memory_client

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "プロンプトが見つかりません")
    
    # メールアドレスからアクターIDを生成
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_message)
    
    if email_match:
        email = email_match.group()
        actor_id = f"customer_{hashlib.md5(email.encode()).hexdigest()[:8]}"
        session_id = f"session_{int(time.time())}"
        
        logger.info(f"顧客を識別: {email} -> {actor_id}")
        
        # Memory Hook 付きエージェントをセットアップ
        agent, memory_client = setup_agent_with_memory(actor_id, session_id)
        
        # エージェントを実行（Memory Hook が自動的に処理）
        response = agent(user_message)
        
        return {
            "result": str(response.message if hasattr(response, 'message') else response),
            "metadata": {
                "actor_id": actor_id,
                "session_id": session_id,
                "email": email
            }
        }
    else:
        # メールアドレスがない場合は Memory なしで処理
        logger.info("メールアドレスが見つかりません。Memory なしで処理します。")
        
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[calculator, current_time, get_customer_id, get_orders, get_knowledge_base_info]
        )
        
        response = agent(user_message)
        
        return {
            "result": str(response.message if hasattr(response, 'message') else response)
        }

if __name__ == "__main__":
    app.run()
```

### 2.4 Memory の初期データ投入
長期記憶を効果的に検証するため、顧客ごとに初期の会話データを投入します。

`initialize_customer_memory.py`:
```python
#!/usr/bin/env python3
"""
顧客の Memory を初期化し、サンプル会話を投入
長期記憶が機能するための基礎データを作成
"""

from bedrock_agentcore.memory import MemoryClient
import json
import time
import hashlib

def initialize_customer_memory(email: str):
    """特定顧客の Memory を初期化"""
    
    # Memory 設定を読み込み
    with open("memory_config.json", "r") as f:
        MEMORY_ID = json.load(f)["memory_id"]
    
    memory_client = MemoryClient()
    
    # 顧客IDを生成
    actor_id = f"customer_{hashlib.md5(email.encode()).hexdigest()[:8]}"
    
    print(f"顧客 {email} ({actor_id}) の Memory を初期化中...")
    
    # 過去のサポート履歴をシミュレート（複数セッション）
    conversations = [
        {
            "session_id": "session_001_initial_purchase",
            "messages": [
                ("こんにちは。スマートフォンを購入したいのですが、おすすめはありますか？", "USER"),
                ("お問い合わせありがとうございます。お客様のご利用用途を教えていただけますか？", "ASSISTANT"),
                ("主に仕事用です。メールとビデオ会議が多いです。バッテリー持ちを重視します。", "USER"),
                ("ビジネス用途でバッテリー重視でしたら、ProModel-X がおすすめです。", "ASSISTANT"),
                ("それにします。あと、充電器は付属していますか？", "USER"),
                ("はい、USB-C充電器が付属しています。EU/UK/USプラグアダプターも同梱です。", "ASSISTANT"),
                ("完璧です。注文します。カバーも一緒に購入したいです。", "USER"),
                ("承知しました。黒色のプレミアムカバーがビジネス用途に人気です。", "ASSISTANT"),
                ("それも追加でお願いします。", "USER"),
                ("ご注文を承りました。注文番号は#1234です。", "ASSISTANT")
            ]
        },
        {
            "session_id": "session_002_setup_help",
            "messages": [
                ("先日購入したスマートフォンが届きました。初期設定を教えてください。", "USER"),
                ("お買い上げありがとうございます。まず、電源ボタンを3秒長押ししてください。", "ASSISTANT"),
                ("起動しました。次は？", "USER"),
                ("言語設定画面が表示されます。日本語を選択してください。", "ASSISTANT"),
                ("できました。WiFi設定はどうすればいいですか？", "USER"),
                ("設定メニューから「ネットワーク」を選び、お使いのWiFiを選択してください。", "ASSISTANT"),
                ("接続できました。メールの設定も教えてください。", "USER"),
                ("「アカウント」から「メールアカウント追加」を選択し、お使いのメールアドレスを入力してください。", "ASSISTANT"),
                ("すべて設定できました。ありがとうございます。", "USER"),
                ("お役に立てて光栄です。他にご不明な点があればお気軽にお問い合わせください。", "ASSISTANT")
            ]
        },
        {
            "session_id": "session_003_troubleshooting",
            "messages": [
                ("スマートフォンの調子が悪いです。時々フリーズします。", "USER"),
                ("ご不便をおかけして申し訳ございません。いつ頃から発生していますか？", "ASSISTANT"),
                ("2日前からです。アプリを複数起動すると固まります。", "USER"),
                ("メモリ不足の可能性があります。バックグラウンドアプリを終了してみてください。", "ASSISTANT"),
                ("どうやって終了させますか？初心者なので詳しく教えてください。", "USER"),
                ("画面下部から上にスワイプし、起動中のアプリを上にスワイプして終了させてください。", "ASSISTANT"),
                ("できました！動きが軽くなりました。", "USER"),
                ("よかったです。定期的にアプリを終了させることをお勧めします。", "ASSISTANT"),
                ("わかりました。丁寧な説明ありがとうございます。メールで手順書を送ってもらえますか？", "USER"),
                ("承知しました。トラブルシューティングガイドをメールでお送りします。", "ASSISTANT")
            ]
        }
    ]
    
    # 各セッションの会話を Memory に投入
    for conv in conversations:
        print(f"  セッション {conv['session_id']} を投入中...")
        
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=actor_id,
            session_id=conv['session_id'],
            messages=conv['messages']
        )
        
        # API レート制限を考慮
        time.sleep(2)
    
    print(f"✅ 初期会話データを投入しました（{len(conversations)} セッション）")
    
    # 長期記憶が処理されるのを待つ
    print("⏳ 長期記憶の処理を待機中（60秒）...")
    time.sleep(60)
    
    # 長期記憶が生成されたか確認
    try:
        # ユーザー嗜好を確認
        preferences = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/preferences/{actor_id}",
            query="顧客の好みと特徴"
        )
        
        # 過去の問題を確認
        issues = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/issues/{actor_id}/products",
            query="過去の問題と解決策"
        )
        
        # セッションサマリーを確認
        summaries = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/summaries/{actor_id}/session_003_troubleshooting",
            query="トラブルシューティングの要約"
        )
        
        print("\n=== 生成された長期記憶 ===")
        print(f"顧客嗜好: {preferences}")
        print(f"過去の問題: {issues}")
        print(f"セッション要約: {summaries}")
        
        return {
            "actor_id": actor_id,
            "sessions_created": len(conversations),
            "preferences": preferences,
            "issues": issues
        }
        
    except Exception as e:
        print(f"⚠️ 長期記憶の取得に失敗（まだ処理中の可能性）: {e}")
        return {
            "actor_id": actor_id,
            "sessions_created": len(conversations),
            "note": "長期記憶は処理中です。数分後に再度確認してください。"
        }

def bulk_initialize_customers():
    """複数の顧客データを一括初期化"""
    
    test_customers = [
        "me@example.net",
        "john.doe@example.com",
        "support.test@example.org"
    ]
    
    for email in test_customers:
        print(f"\n{'='*50}")
        result = initialize_customer_memory(email)
        print(f"結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print(f"{'='*50}\n")
        
        # 次の顧客の処理前に少し待機
        time.sleep(5)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 特定の顧客を初期化
        email = sys.argv[1]
        result = initialize_customer_memory(email)
        print(f"\n最終結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        # デフォルトの顧客を初期化
        result = initialize_customer_memory("me@example.net")
        print(f"\n最終結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
```

### 2.5 実行手順

```python
# 1. Memory リソースをセットアップ（初回のみ）
python setup_memory.py

# 2. 顧客の初期データを投入（長期記憶を準備）
python initialize_customer_memory.py me@example.net

# 3. エージェントをデプロイ
agentcore configure --entrypoint customer_support_agent_with_memory.py --disable-otel
agentcore launch --local

# 4. 長期記憶が活用されるかテスト
# 新しいセッションで、過去の情報を参照した応答が可能
agentcore invoke --local '{
    "prompt": "差出人: me@example.net - スマートフォンがまたフリーズしました。前回教えてもらった方法を忘れてしまいました。"
}'

# 5. 別の質問で長期記憶を確認
agentcore invoke --local '{
    "prompt": "差出人: me@example.net - 私が購入した製品の型番を教えてください。"
}'
```

## Step 3: AgentCore Identity による認証と認可の統合

### 認証・認可システムの実装
実際のプロダクション環境では、ユーザー認証と適切なアクセス制御が必要です。AgentCore Identity を使用して、Amazon Cognito と連携した認証・認可システムを構築しましょう。

### 3.1 Cognito User Pool のセットアップ
まず、認証基盤となる Amazon Cognito ユーザープールを設定します。

```bash
# Cognito User Pool、Client、Domainを一括設定
python cognito_setup.py setup --domain-prefix your-unique-domain-prefix

# 認証テスト
python cognito_setup.py test-auth

# 設定確認
python cognito_setup.py show-config
```

### 3.2 AgentCore Identity Credentials Provider の作成
Cognito と AgentCore Identity を連携するための OAuth2 認証プロバイダーを作成します。

```bash
# OAuth2認証プロバイダーを作成
python cognito_credentials_provider.py create --name CustomerSupportProvider

# プロバイダー一覧を確認
python cognito_credentials_provider.py list

# 設定確認
python cognito_credentials_provider.py show-config
```

### 3.3 Memory アクセス権限の設定

AgentCore Identity を使用する場合でも、Memory アクセスには適切な IAM 権限が必要です。

#### 自動設定スクリプトの実行

既存の設定ファイル（`memory_config.json`）から情報を自動取得して、IAM権限を一発で設定できます：

```bash
# Memory アクセス権限を自動設定
python setup_memory_permissions.py

# ヘルプを表示
python setup_memory_permissions.py --help
```

このスクリプトは以下を自動実行します：
- 現在のAWSアカウントID・リージョンを取得
- Step 2 で作成された `memory_config.json` から Memory ID を取得
- AgentCore Runtime Role を自動検出
- 適切な Resource ARN でポリシーファイルを生成
- IAM ポリシーの作成またはアップデート
- Runtime Role へのポリシーアタッチ

> [!TIP]
> 複数の Runtime Role がある場合は、スクリプトが自動的に選択します。

### 3.4 Identity統合版エージェントのクラウドデプロイ

認証・認可機能を統合したカスタマーサポートエージェントをクラウドにデプロイします。

```bash
# Identity統合版エージェントを設定（OAuth Authorizerを有効化）
agentcore configure --entrypoint customer_support_agent_with_identity.py --disable-otel

# プロンプトで以下のように回答：
# Configure OAuth authorizer instead? (yes/no) [no]: yes
# OAuth discovery URL: [Cognito設定で取得したURL]
# OAuth client IDs: [Cognito設定で取得したClient ID]
# OAuth audience: [空白のままEnter]

# クラウドにデプロイ
agentcore launch
```

**重要**: 
- OAuth authorizer の設定で必ず `yes` を選択してください
- ローカル実行（`--local`）では OAuth 認証が完全には機能しないため、クラウドデプロイが必要です

### 3.5 クラウド環境での認証テスト

クラウドデプロイされたエージェントで認証機能をテストします。

```bash
# 認証付きテスト（成功するはず）
python test_cloud_identity.py test-authenticated

# 認証なしテスト（エラーになるはず）
python test_cloud_identity.py test-unauthenticated

# 設定確認
python test_cloud_identity.py show-config
```

#### 期待される結果

**認証付きテスト**:
```json
{
  "result": "...",
  "metadata": {
    "user_id": "customer_oauth_verified",
    "session_id": "session_1234567890",
    "user_name": "OAuth認証済みユーザー",
    "user_email": "oauth-verified@example.com",
    "authenticated": true
  }
}
```

**認証なしテスト**:
```json
{
  "message": "OAuth authorization failed: Failed to parse token"
}
```

### 3.6 実装のポイント

#### 認証フロー
1. **OAuth Authorizer**: AgentCore が自動的にBearer tokenを検証
2. **エントリーポイント到達**: 認証済みユーザーのみがエージェントにアクセス可能
3. **ユーザー識別**: 認証されたユーザー情報を基にした処理
4. **パーソナライズ**: 認証されたユーザー情報を基にした応答

#### セキュリティ機能
- **Bearer Token 必須**: HTTP Authorization ヘッダーでのトークン送信が必要
- **自動認証・認可**: AgentCore Runtime レベルでの認証処理
- **セッション管理**: 認証されたユーザーごとの独立したセッション
- **アクセス拒否**: 無効なトークンや認証なしリクエストは自動的に拒否

#### Memory との統合
- **ユーザー固有の記憶**: 認証されたユーザーIDを使用した Memory 管理
- **プライバシー保護**: ユーザー間での記憶の分離
- **長期記憶の活用**: 認証されたユーザーの過去の履歴を活用
- **適切な権限設定**: Memory アクセスには明示的な IAM 権限が必要

### 3.7 HTTP API での直接テスト例

クラウドデプロイされたエージェントに直接HTTPリクエストを送信することも可能です。

```bash
# 認証付きリクエスト例（成功）
curl -X POST "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/YOUR_AGENT_ARN/invocations?qualifier=DEFAULT" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: $(uuidgen)" \
  -d '{
    "prompt": "私の注文履歴を確認してください"
  }'

# 認証なしリクエスト例（403エラーが返される）
curl -X POST "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/YOUR_AGENT_ARN/invocations?qualifier=DEFAULT" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "私の注文履歴を確認してください"
  }'
```

**注意**: `YOUR_AGENT_ARN` は実際のエージェントARNに置き換えてください。

### 3.8 トラブルシューティング

#### よくある問題と解決方法

**1. Memory アクセス権限エラー**
```
User is not authorized to perform: bedrock-agentcore:CreateEvent
```
→ 3.3 の手順に従って IAM Role に Memory アクセス権限を追加してください

**2. OAuth 認証失敗**
```
OAuth authorization failed: Failed to parse token
```
→ 有効なアクセストークンを使用しているか確認してください

**3. Resource ARN の不一致**
```
because no identity-based policy allows the bedrock-agentcore:CreateEvent action
```
→ Memory アクセス権限を再設定してください：

```bash
# 権限を再設定（自動的に正しいResource ARNを使用）
python setup_memory_permissions.py
```

**4. エージェントが起動しない**
→ CloudWatch ログを確認してください：
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR_AGENT_ID-DEFAULT --follow
```

**5. ローカル実行での認証問題**
→ OAuth Authorizer はクラウド環境でのみ完全に機能します。テストはクラウドデプロイで行ってください。
```
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "私の注文履歴を確認してください"
  }'
```


## Step 4: AgentCore Gateway による MCP ツール統合

### Model Context Protocol (MCP) ツールの実装
実際のプロダクション環境では、エージェントが外部システムやデータベースにアクセスして情報を取得する必要があります。AgentCore Gateway を使用して、Lambda 関数を MCP ツールとして公開し、統一されたインターフェースでアクセスできるようにしましょう。なお MCP に関しては、本書の5.4節 (p. 139) で解説しています。

### 4.1 AgentCore Gateway のセットアップ

顧客サポートに役立つ各種ツールを Lambda 関数として実装し、これを MCP ツールとして公開するための Gateway を作成します。ここでは注文履歴取得、製品情報検索、配送状況確認、サポートFAQ検索などの顧客サポート機能を提供するモック Lambda 関数を作成し、MCP プロトコル経由でアクセスできるようにします。
`lambda_tools.py` には以下のツールが含まれています：
- **get_order_history**: 顧客の注文履歴を取得
- **get_product_info**: 製品情報を検索
- **check_shipping_status**: 配送状況を確認
- **get_support_faq**: サポートFAQを検索

```bash
# Gateway を作成（Lambda 関数も自動作成）
python gateway_manager.py create CustomerSupportGateway

# 設定確認
python gateway_manager.py show-config
```

このスクリプトは以下を自動実行します：
- **Lambda 関数の作成とデプロイ**: `CustomerSupportTools` という名前で4つのツール機能を含む関数を作成
- **Lambda 実行ロールの作成**: Lambda 関数実行用の IAM ロール
- **Gateway 実行ロールの作成**: Gateway が Lambda を呼び出すための IAM ロール  
- **AgentCore Gateway の作成**: MCP プロトコルに対応したゲートウェイエンドポイント
- **Gateway Target の設定**: Lambda 関数を MCP ツールとして公開する設定
- **OAuth 認証の設定**: Cognito との連携による認証機能

> [!NOTE]
> 作成された Lambda 関数は AWS マネジメントコンソールの Lambda サービスページで確認できます。関数名は `CustomerSupportTools` で、実際のプロダクション環境では、この関数を DynamoDB や外部 API と連携させることで、リアルなデータを取得できます。

#### 実行例

```
🌍 リージョン: us-east-1
🏢 アカウントID: 443338083294
🚀 Lambda関数を作成中: CustomerSupportTools
🔐 Lambda実行ロールを作成中: CustomerSupportLambdaRole
✅ Lambda実行ロールを作成しました: arn:aws:iam::443338083294:role/CustomerSupportLambdaRole
✅ Lambda関数を作成しました: arn:aws:lambda:us-east-1:443338083294:function:CustomerSupportTools
🚀 AgentCore Gateway を作成中: CustomerSupportGateway
🔐 Gateway実行ロールを作成中: CustomerSupportGatewayRole
✅ Gateway実行ロールを作成しました: arn:aws:iam::443338083294:role/CustomerSupportGatewayRole
✅ Gateway作成完了: gw-abc123def456
✅ Gateway Target作成完了: tgt-xyz789abc123
✅ Gateway設定を保存しました: gateway_config.json

🎉 Gateway作成完了!
==================================================
Gateway ID: gw-abc123def456
Gateway URL: https://bedrock-agentcore.us-east-1.amazonaws.com/gateways/gw-abc123def456
Target ID: tgt-xyz789abc123
```

### 4.2 MCP ツールのテスト

Gateway 経由で MCP ツールが正しく動作するかテストします。

```bash
# 利用可能なツール一覧を取得
python test_gateway.py list-tools

# 特定のツールを呼び出し
python test_gateway.py invoke-tool get_order_history '{"customer_id": "customer_oauth_verified", "limit": 3}'

# 包括的なテスト実行
python test_gateway.py comprehensive

# 設定確認
python test_gateway.py show-config
```

#### 期待される結果

**ツール一覧取得**:
```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "result": {
    "tools": [
      {
        "name": "get_order_history",
        "description": "顧客の注文履歴を取得します。最新の注文から指定された件数を返します。"
      },
      {
        "name": "get_product_info", 
        "description": "製品名で製品情報を検索し、詳細な仕様や価格情報を取得します。"
      }
    ]
  }
}
```

**ツール呼び出し**:
```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"customer_id\": \"customer_oauth_verified\",\n  \"orders\": [\n    {\n      \"order_id\": \"ORD-2024-001\",\n      \"date\": \"2024-01-15\",\n      \"status\": \"配送完了\",\n      \"items\": [...],\n      \"total\": 89800\n    }\n  ]\n}"
      }
    ]
  }
}
```

### 4.3 Gateway 統合エージェントのデプロイ

Gateway を使用する高機能なカスタマーサポートエージェントをデプロイします。

```bash
# Gateway統合版エージェントを設定
agentcore configure --entrypoint customer_support_agent_with_gateway.py --disable-otel

# クラウドにデプロイ
agentcore launch
```

### 4.4 統合テスト

認証 + Memory + Gateway の全機能を統合したテストを実行します。

```bash
# 統合エージェントのテスト
agentcore invoke '{
    "prompt": "顧客ID customer_oauth_verified の注文履歴を確認して、最新の注文の配送状況も教えてください。"
}'
```

#### 期待される結果

エージェントが以下の処理を自動実行します：
1. `get_order_history` ツールで注文履歴を取得
2. 最新注文の `order_id` を特定
3. `check_shipping_status` ツールで配送状況を確認
4. 結果を統合して分かりやすく回答

### 4.5 実装のポイント

#### MCP ツールの利点
- **統一インターフェース**: すべてのツールが MCP プロトコルで統一
- **自動認証**: Gateway レベルでの OAuth 認証
- **スケーラビリティ**: Lambda による自動スケーリング
- **セキュリティ**: IAM ロールによる細かい権限制御

#### Gateway の特徴
- **Lambda 統合**: 既存の Lambda 関数を簡単に MCP 化
- **認証統合**: AgentCore Identity との自動連携
- **ツール検索**: セマンティック検索による適切なツール選択
- **エラーハンドリング**: 統一されたエラー処理とレスポンス

#### 開発効率の向上
- **再利用性**: Lambda 関数は他のシステムからも利用可能
- **テスタビリティ**: 各ツールを個別にテスト可能
- **保守性**: ツールごとに独立した開発・デプロイ
- **監視**: CloudWatch による詳細なログとメトリクス

#### 外部 CRM システムとの連携例

AgentCore Gateway は OpenAPI 仕様を持つ外部システム（Salesforce、HubSpot、Zendesk など）との連携も可能です：

```python
# Salesforce API 連携の Lambda 関数例
def get_salesforce_contact(email: str) -> Dict[str, Any]:
    """Salesforce から顧客情報を取得"""
    access_token = get_salesforce_oauth_token()
    
    response = requests.get(
        f"{os.environ['SALESFORCE_INSTANCE_URL']}/services/data/v58.0/query/",
        params={"q": f"SELECT Id, Name, Email FROM Contact WHERE Email = '{email}'"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()

# OpenAPI 仕様による自動ツール生成
python gateway_manager.py create-api-target \
  --name SalesforceIntegration \
  --openapi-spec salesforce-rest-api.json \
  --auth-type oauth2
```

これにより、内部システムと外部 CRM の情報を統合した、より高度なカスタマーサポート体験を提供できます。

## Step 5: 高度な機能: AgentCore Code Interpreter と Browser Tools による計算処理と Web 自動化

### Built-in Tools の活用
AgentCore では、Code Interpreter と Browser Tool という2つの強力な built-in ツールが提供されています。これらのツールを使用することで、エージェントに高度な計算処理能力と Web 自動化機能を追加できます。

### 5.1 Built-in Tools 権限の設定

Code Interpreter と Browser Tool を使用するために必要な IAM 権限を設定します。

```bash
# Built-in Tools の権限を自動設定
python setup_builtin_tools_permissions.py setup

# 設定確認
python setup_builtin_tools_permissions.py show-config

# 権限テスト
python setup_builtin_tools_permissions.py test
```

このスクリプトは以下を自動実行します：
- **Code Interpreter 権限**: セッション作成・実行・停止権限
- **Browser Tool 権限**: ブラウザセッション管理・操作権限
- **CloudWatch Logs 権限**: ツール実行ログの記録権限
- **Runtime Role への権限アタッチ**: 現在使用中のエージェントロールに権限を追加

#### 実行例

```
🚀 Built-in Tools アクセス権限の自動設定を開始します...
============================================================
🎯 現在のエージェント設定から使用中のRoleを検出: AmazonBedrockAgentCoreSDKRuntime-us-east-1-6a76038ec1
📋 設定情報:
   AWSアカウントID: 443338083294
   リージョン: us-east-1
   Runtime Role: AmazonBedrockAgentCoreSDKRuntime-us-east-1-6a76038ec1

🆕 新しいポリシーを作成します: BedrockAgentCoreBuiltinToolsAccess
✅ ポリシーを作成しました
✅ ポリシーをロールにアタッチしました: AmazonBedrockAgentCoreSDKRuntime-us-east-1-6a76038ec1

🎉 Built-in Tools アクセス権限の設定が完了しました！
   Code Interpreter と Browser Tool が使用可能になりました。
```

### 5.2 Built-in Tools のテスト

各ツールが正しく動作するかテストします。

```bash
# Code Interpreter のテスト
python test_builtin_tools.py code-interpreter

# Browser Tool のテスト
python test_builtin_tools.py browser-tool

# 統合シナリオのテスト
python test_builtin_tools.py integrated

# 包括的なテスト実行
python test_builtin_tools.py comprehensive
```

#### 期待される結果

**Code Interpreter テスト**:
- 基本的な Python コードの実行
- データ分析とグラフ作成
- ファイル操作（JSON、CSV、画像ファイルの作成・読み込み）

**Browser Tool テスト**:
- Web ページへのナビゲーション
- スクリーンショットの取得
- ページ間の移動

### 5.3 Built-in Tools 統合エージェントのデプロイ

Code Interpreter と Browser Tool を統合したエージェントをデプロイします。

```bash
# Built-in Tools統合版エージェントを設定
agentcore configure --entrypoint customer_support_agent_with_tools.py --disable-otel

# プロンプトで以下のように回答：
# Configure OAuth authorizer instead? (yes/no) [no]: yes
# OAuth discovery URL: [Cognito設定で取得したURL]
# OAuth client IDs: [Cognito設定で取得したClient ID]

# クラウドにデプロイ
agentcore launch
```

### 5.4 統合テスト

認証 + Memory + Gateway + Built-in Tools の全機能を統合したテストを実行します。

```bash
# データ分析テスト
agentcore invoke '{
    "prompt": "過去6ヶ月の売上データ [100000, 120000, 95000, 110000, 130000, 125000] を分析して、トレンドをグラフで可視化してください。"
}'

# Web 情報確認テスト
agentcore invoke '{
    "prompt": "httpbin.org にアクセスして、API の動作確認を行ってください。"
}'

# 複合タスクテスト
agentcore invoke '{
    "prompt": "顧客の注文データを分析し、Web で競合他社の価格も調査して、総合的なレポートを作成してください。"
}'
```

#### 期待される結果

エージェントが以下の処理を自動実行します：
1. **データ分析**: Code Interpreter で売上データを分析・グラフ化
2. **Web 調査**: Browser Tool で外部サイトの情報を取得
3. **統合レポート**: 複数のツールの結果を組み合わせた包括的な回答

### 5.5 実装のポイント

#### Code Interpreter の特徴
- **安全な実行環境**: 隔離されたサンドボックスでのコード実行
- **多言語サポート**: Python、JavaScript、TypeScript に対応
- **ファイル操作**: データファイルの読み込み・保存・処理
- **可視化機能**: matplotlib、pandas を使用したグラフ・チャート作成

#### Browser Tool の特徴
- **企業グレードセキュリティ**: VM レベルの分離とVPC接続
- **モデル非依存**: 様々な AI モデルのコマンド構文に対応
- **包括的な監査**: CloudTrail ログとセッション記録
- **リアルタイム監視**: Live View と Session Replay 機能

#### 統合による価値
- **高度な分析**: 数値計算とデータ可視化による深い洞察
- **リアルタイム情報**: Web から最新情報を取得
- **自動化ワークフロー**: 複数ステップの処理を自動実行
- **エンタープライズ対応**: セキュリティと監査要件を満たす

#### 実用的なユースケース

**Code Interpreter の活用例**:
```python
# 売上予測分析
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

# 過去データから将来の売上を予測
sales_data = [100000, 120000, 95000, 110000, 130000, 125000]
months = np.array(range(len(sales_data))).reshape(-1, 1)
model = LinearRegression().fit(months, sales_data)

# 次の3ヶ月を予測
future_months = np.array([[6], [7], [8]])
predictions = model.predict(future_months)
print(f"予測売上: {predictions}")
```

**Browser Tool の活用例**:
```python
# 競合他社の価格調査
browser_tool.navigate("https://competitor-site.com/products")
screenshot = browser_tool.screenshot()
price_element = browser_tool.find_element("price-display")
current_price = browser_tool.get_text(price_element)
```

### 5.6 セキュリティとベストプラクティス

#### セキュリティ機能
- **隔離実行環境**: クロス汚染を防ぐ独立した実行環境
- **セッションタイムアウト**: リソース使用量を制限する設定可能なタイムアウト
- **IAM 統合**: アクセス制御のための IAM 権限管理
- **ネットワークセキュリティ**: 外部アクセスを制限するネットワーク制御

#### ベストプラクティス
- **適切なセッション管理**: 使用後は必ずセッションを停止
- **リソース監視**: CloudWatch でリソース使用量を監視
- **エラーハンドリング**: 例外処理による安全な実行
- **権限の最小化**: 必要最小限の権限のみを付与

## Step 6. 運用監視: AgentCore Observability によるパフォーマンス監視とデバッグ
### 🔜 次回予告: Step 6

**Step 6: 運用監視: AgentCore Observability による統合監視とデバッグ**
- **OpenTelemetry (OTEL) 互換** テレメトリデータの収集
- **Amazon CloudWatch** 統合ダッシュボードによる可視化
- **トレース・スパン・ログ** による詳細な実行分析
- **パフォーマンス監視** とボトルネック特定
- **エラー追跡** とデバッグ支援
- **カスタムメトリクス** による運用最適化

Step 6 では、プロダクション環境での運用に不可欠な監視・デバッグ機能を実装し、完全なエンタープライズAIエージェントシステムを完成させます！

### 📋 実装された機能一覧

1. **基本エージェント**: Strands Agents による基本的な対話機能
1. **Memory 統合**: 長期記憶による個人化された体験
1. **認証・認可**: Amazon Cognito + AgentCore Identity による安全なアクセス制御
1. **MCP ツール**: AgentCore Gateway による外部システム連携
1. **Built-in Tools**: Code Interpreter + Browser Tool による高度な分析・自動化
1. **Observability**: OTEL + CloudWatch によるパフォーマンス監視とデバッグ

これらの機能を組み合わせることで、エンタープライズレベルの AI エージェントシステムを構築できます！
