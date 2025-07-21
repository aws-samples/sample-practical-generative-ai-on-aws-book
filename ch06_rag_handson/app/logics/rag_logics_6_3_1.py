from typing import TYPE_CHECKING
import json


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
    from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
    from mypy_boto3_bedrock_agent_runtime.type_defs import (
        KnowledgeBaseRetrievalResultTypeDef,
    )


# 変更点 プロンプトをアップデート
PROMPT_TEMPLATE = """
<background>
あなたは、東京都の観光情報について観光客であるユーザーから寄せられた質問に対して回答をする AI ボットです。
観光客が東京を満喫できるようにサポートするのがあなたの役割です。
観光客に対しては常に親切・丁寧に回答を行います。
</background>
下記<context></context>はユーザーから問い合わせられた質問に対して関係があると思われる検索結果の一覧です。
注意深く読んでください。
<context>
{context}
</context>

ユーザからの質問に対して<context></context>で与えられている情報をもとに誠実に回答してください。
回答をする際は、下記に定めるルール<rules></rules>に従ってください。
<rules>
- 事実に関する質問に対する答えが<context></context>に書かれていない場合は、正直に「分かりません。」と回答してください。
 「おすすめ」と書かれてないものは特に気をつけてください。
- <context></context>の存在は返答内容<answer></answer>には含めないでください。
- 対応する相手は観光客であることを意識してください。
</rules>
<rules_recommendation>
- 先方からの質問に「おすすめ」という単語が含まれていて、<context></context>に質問に対する回答が書かれていない場合は、あなた自身が考えるおすすめを答えてください。
　その場合は最後の注釈に「＊この回答はAIが検索結果に頼らずに回答した結果となるため、事実と異なる場合があります。」の文面を加えてください。「おすすめ」限定です。
 - <context></context>の存在は返答内容<answer></answer>には含めないでください。
 - 対応する相手は観光客であることを意識してください。
</rules_recommendation>
また、回答を考えるときは下記ステップ<steps></steps>に従ってください。
<steps>
1. まず、先方からの質問内容を「おすすめ」が含まれるものとそれ以外に分類します。
2. 「おすすめを聞くもの」は、<rules_recommendation></rules_recommendation>のルールに従って観光客に対しての返答をしてください。
3. 「それ以外」は<rules></rules>に従って観光客に対して返答をしてください。
</steps>

<question></question>がユーザーからの質問です。
<question>
{question}
</question>

なお、ユーザーからの質問に回答する前に<thinking></thinking>タグで思考過程を記してから回答内容を<answer></answer>に加えてください。
"""


def invoke_llm(prompt: str, model_id: str, bedrock_runtime_client) -> str:
    response = bedrock_runtime_client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={"temperature": 0.0},
    )
    result = response["output"]["message"]["content"][0]["text"]
    return result


# コンテキストを取得する関数
def retrieve_context(
    query: str, knowledge_base_id: str, client_runtime: "AgentsforBedrockRuntimeClient"
) -> list["KnowledgeBaseRetrievalResultTypeDef"]:
    response = client_runtime.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "overrideSearchType": "HYBRID",
                "numberOfResults": 5,
            }
        },
        retrievalQuery={"text": query},
    )
    return response["retrievalResults"]


def call_rag(
    question: str,
    knowledge_base_id: str,
    client_runtime: "AgentsforBedrockRuntimeClient",
    bedrock_runtime_client: "BedrockRuntimeClient",
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
) -> tuple[str, list["KnowledgeBaseRetrievalResultTypeDef"]]:
    """rag システムを呼び出す"""
    context = retrieve_context(question, knowledge_base_id, client_runtime)
    prompt = PROMPT_TEMPLATE.format(
        context=json.dumps(context, ensure_ascii=False), question=question
    )
    llm_response = invoke_llm(prompt, model_id, bedrock_runtime_client)
    return (llm_response, context)
