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
1. コンテキスト管理: AgentCore Memory による会話記憶機能の実装
1. アクセス制御: AgentCore Identity による認証と認可の統合
1. システム統合: AgentCore Gateway による MCP や API 経由での CRM などへの連携
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

## Step 2 以降は準備中です 🙇
