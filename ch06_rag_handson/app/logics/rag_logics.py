from typing import TYPE_CHECKING
import json


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
    from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
    from mypy_boto3_bedrock_agent_runtime.type_defs import (
        KnowledgeBaseRetrievalResultTypeDef,
    )


PROMPT_TEMPLATE = \
"""下記<context></context>はユーザーから問い合わせられた質問に対して関係があると思われる検索結果の一覧です。
注意深く読んでください。
<context>
{context}
</context>
あなたは親切なAIボットです。ユーザからの質問に対して<context></context>で与えられている情報をもとに誠実に回答します。
ただし、質問に対する答えが<context></context>に書かれていない場合は、正直に「分かりません。」と回答してください。

下記<question></question>がユーザーからの質問です。
<question>
{question}
</question>
ユーザーからの質問に回答してください。

なお、ユーザーからの質問に回答する前に<thinking></thinking>タグで思考過程を記してから回答内容を<answer></answer>に加えてください。
"""


def invoke_llm(prompt: str, model_id: str, bedrock_runtime_client) -> str:
    response = bedrock_runtime_client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ],
            }
        ],
        inferenceConfig={
            "temperature": 0.0
        }
    )
    result = response['output']['message']['content'][0]['text']
    return result


# コンテキストを取得する関数
def retrieve_context(query: str, knowledge_base_id: str, client_runtime) -> list[dict]:
    response = client_runtime.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'overrideSearchType': 'HYBRID',
                'numberOfResults': 3
            }
        },
        retrievalQuery={
            'text': query
        }
    )
    return response["retrievalResults"]


def call_rag(
    question: str,
    knowledge_base_id: str,
    client_runtime: "AgentsforBedrockRuntimeClient",
    bedrock_runtime_client: "BedrockRuntimeClient",
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
) -> tuple[str, list["KnowledgeBaseRetrievalResultTypeDef"]]:
    """質問→検索→LLm→回答 という最もシンプルな流れを実現する
    """
    context = retrieve_context(question, knowledge_base_id, client_runtime)
    prompt = PROMPT_TEMPLATE.format(
        context=json.dumps(context, ensure_ascii=False),
        question=question
    )
    llm_response = invoke_llm(prompt, model_id, bedrock_runtime_client)
    return llm_response, context
