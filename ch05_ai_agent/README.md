# Amazon Bedrock AgentCore ハンズオン
ここでは、書籍「[AWS生成AIアプリ構築実践ガイド](https://www.amazon.co.jp/dp/4296205234)」の5章「AIエージェント」で紹介した Amazon Bedrock AgentCore について、ハンズオン形式で学びます。

## 5.6.2 カスタマーサポートエージェントの構築例

AgentCore の利用方法を、カスタマーサポートのシナリオで紹介します。顧客からメールでの問い合わせがあった際、サポートチームは以下の作業をする必要があります: 
- メールの妥当性確認
- CRM システムでの顧客特定
- 注文履歴の確認
- 製品固有のナレッジベースでの情報検索
- 回答の準備

AI エージェントは、内部システムに接続し、セマンティックデータソースを使用してコンテキスト情報を取得し、サポートチームの回答草案を作成することで、このプロセスを簡素化できます。

本節では、Strands Agents を使用したシンプルなプロトタイプから、Amazon Bedrock AgentCore を活用してエンタープライズ対応のプロダクションシステムまでを段階的に構築する過程を説明します。
実装の流れ (概要) については書籍を参照してください。

### 詳細な実装方法
このハンズオンでは、具体的に以下の7つのステップで段階的に構築していきます: 
1. 基本実装: Strands Agentsとツールで構築したカスタマーサポートエージェントのプロトタイプ作成
1. クラウドデプロイ: AgentCore Runtimeによるセキュアなサーバーレス環境へのデプロイ
1. コンテキスト管理: AgentCore Memoryによる会話記憶機能の実装
1. アクセス制御: AgentCore Identityによる認証と認可の統合
1. システム統合: AgentCore GatewayによるMCPやAPI経由でのCRMなどへの連携
1. 高度な機能: AgentCore Code InterpreterとBrowser Toolsによる計算処理とWeb自動化
1. 運用監視: AgentCore Observabilityによるパフォーマンス監視とデバッグ

このハンズオンを通じて、プロトタイプから本格的なプロダクション環境まで対応可能な、スケーラブルで安全なAIエージェントシステムの構築方法を学習できます。

### 事前準備
まず、今回のハンズオンで使う仮想環境を作ります。

#### 環境セットアップ
```bash
# Python仮想環境の作成
python -m venv agentcore-env
source agentcore-env/bin/activate  

# 必要なパッケージのインストール
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit
pip install strands-agents strands-agents-tools
```

#### IAM ロールの準備
AgentCore で使用する IAM ロールを作成します。
``` bash
# 環境変数を設定
export YOUR_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export YOUR_REGION=$(aws configure get region)
```

```bash 
# 1. 信頼関係ポリシーファイルを作成
cat > agentcore-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${YOUR_ACCOUNT_ID}"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock-agentcore:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:*"
        }
      }
    }
  ]
}
EOF

# 変数を置換して最終的なポリシーファイルを生成
envsubst < agentcore-trust-policy.json > agentcore-trust-policy-final.json
```

```bash 
# 2. IAMロールを作成
aws iam create-role \
  --role-name AgentCoreExecutionRole \
  --assume-role-policy-document file://agentcore-trust-policy-final.json
```

```bash
# 3. 実行権限ポリシーファイルを作成
cat > agentcore-execution-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:log-group:/aws/bedrock-agentcore/runtimes/*"
    },
    {
        "Effect": "Allow",
        "Action": [
            "ecr:BatchGetImage",
            "ecr:GetAuthorizationToken",
            "ecr:GetDownloadUrlForLayer"
        ],
        "Resource": [
            "arn:aws:ecr:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:repository/bedrock_agentcore-*"
        ]`
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetWorkloadAccessToken",
        "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
        "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:workload-identity-directory/default",
        "arn:aws:bedrock-agentcore:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:workload-identity-directory/default/workload-identity/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": [
        "arn:aws:ecr:${YOUR_REGION}:${YOUR_ACCOUNT_ID}:repository/bedrock_agentcore-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "bedrock-agentcore"
        }
      }
    }
  ]
}
EOF

# 変数を置換して最終的なポリシーファイルを生成
envsubst < agentcore-execution-policy.json > agentcore-execution-policy-final.json
```

```bash 
# 4. ポリシーを作成してロールにアタッチ
aws iam create-policy \
  --policy-name AgentCoreExecutionPolicy \
  --policy-document file://agentcore-execution-policy-final.json

aws iam attach-role-policy \
  --role-name AgentCoreExecutionRole \
  --policy-arn arn:aws:iam::${YOUR_ACCOUNT_ID}:policy/AgentCoreExecutionPolicy
```

```bash
# 5. ロールARNを取得・表示
ROLE_ARN="arn:aws:iam::${YOUR_ACCOUNT_ID}:role/AgentCoreExecutionRole"
echo "Role created successfully: $ROLE_ARN"
echo "Use this ARN in your agentcore configure command:"
echo "agentcore configure --entrypoint your_agent.py -er $ROLE_ARN"

# 一時ファイルを削除
rm agentcore-trust-policy.json agentcore-trust-policy-final.json
rm agentcore-execution-policy.json agentcore-execution-policy-final.json
```

### Step 1: AgentCore Runtime でクラウドにデプロイ
#### 基本的なエージェントプロトタイプの作成
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

#### デプロイ
リモート環境で使われる Docker コンテナ内で必要となるパッケージインストールのため、[`requirements.txt`](./requirements.txt) を以下のように用意しておきます: 
```txt
strands-agents
strands-agents-tools
bedrock-agentcore
bedrock-agentcore-starter-toolkit
boto3
```

先ほど作った IAM ロールを指定し、AgentCore の設定を行います。
```bash
# 上記で作成したロールARNを使用してエージェントの設定
# (IAMロール作成時に出力されたコマンドをコピー&ペーストしてください)
agentcore configure --entrypoint customer_support_agent.py -er arn:aws:iam::${YOUR_ACCOUNT_ID}:role/AgentCoreExecutionRole
```

以下のコマンドを実行すると、Docker コンテナの中で Bedrock AgentCore アプリが起動します。
```bash
# ローカルでの起動
agentcore launch --local
```
別のターミナルを開き (先程作った pyenv `agentcore-env` 環境を有効化しておきましょう)、次のコマンドで実際にエージェントを呼び出します。
```bash
# 別のターミナルでテスト
agentcore invoke --local '{
    "prompt": "差出人: me@example.net - スマートフォンの充電器について、ヨーロッパでも使用できますか？"
}'
```

> [!TIP]
> もし、ローカル実行の際に必要以上に時間がかかるようであれば、上の `agentcore configure` で自動生成された Docker ファイルの中で OpenTelemetry を無効化するとスムーズに実行されるかもしれません。
> ```Dockerfile
> ... (省略)
> # CMD ["opentelemetry-instrument", "python", "-m", "customer_support_agent"]
> CMD ["python", "-m", "customer_support_agent"]
> ```

実行結果例: 
```
{
  "result": "お問い合わせありがとうございます。お客様のスマートフォン充電器は100-240V AC, 50/60Hzに対応しており、US/UK/EUプラグアダプターが付属しているため、ヨーロッパでも問題なくご使用いただけます。安心してご旅行をお楽しみください。"
}
```

同様に、 `--local` オプションを外すとクラウドにデプロイできます。
```bash
# ローカルでの起動
agentcore launch 

# 別のターミナルでテスト
agentcore invoke '{
    "prompt": "差出人: me@example.net - スマートフォンの充電器について、ヨーロッパでも使用できますか？"
}'
```

