import json
from pprint import pprint
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient

bedrock_runtime_client: "BedrockRuntimeClient" = boto3.client(
    service_name="bedrock-runtime"
)


if __name__ == "__main__":
    response = bedrock_runtime_client.converse(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        system=[
            {
                "text": "あなたは愉快なチャットbotです。<response></response>タグで返答をします。"
            }
        ],
        messages=[{"role": "user", "content": [{"text": "こんにちは!"}]}],
        inferenceConfig={
            "temperature": 0.1,
            "maxTokens": 512,
            "stopSequences": ["</response>"],
        },
    )
    pprint(response)

