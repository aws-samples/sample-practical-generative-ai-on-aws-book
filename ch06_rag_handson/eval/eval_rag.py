"""RAG 評価用パイプラインを実装したスクリプト
"""

import os
import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from datetime import datetime

import boto3
import pandas as pd
from datasets import load_dataset, Dataset
from langchain_aws import ChatBedrockConverse, BedrockEmbeddings
from ragas import evaluate 
from ragas.dataset_schema import EvaluationResult
from ragas.metrics import answer_relevancy, answer_similarity, context_recall, faithfulness
from ragas.run_config import RunConfig

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
    # from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
    # from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient


REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"

# agents_for_bedrock_client: "AgentsforBedrockClient" = boto3.client('bedrock-agent', region_name=REGION)
# agents_for_bedrock_runtime_client: "AgentsforBedrockRuntimeClient" = boto3.client('bedrock-agent-runtime', region_name=REGION)
bedrock_runtime_client: "BedrockRuntimeClient" = boto3.client(
    service_name='bedrock-runtime', region_name=REGION)

bedrock_model = ChatBedrockConverse(
    client=bedrock_runtime_client,
    model=MODEL_ID,
    temperature=0.0
)
bedrock_embedding_model = BedrockEmbeddings(
    client=bedrock_runtime_client,
    model_id=EMBEDDING_MODEL_ID
)
# 評価を回す時の実行設定
run_config = RunConfig(
    max_workers=4,
    timeout=120,
    log_tenacity=True
)


def evaluate_rag(
    rag_func: Callable[[str], "pd.Series"],
    eval_name: str = "",
    result_parent_dir: Path = Path("./eval/results"),
    eval_data_path: Path = Path("./eval/eval_data.csv"),
) -> EvaluationResult:
    """RAG アプリの評価を実施する関数
    
    rag_func では、入力されたテキストに対して、
    - "answer" (str): RAG システムからの出力結果
    - "retrieved_contexts" (list[dict]): retriever からの検索結果
    - "execution_seconds" (float): 実行時間
    のカラムが含まれる pd.Series が出力される関数を想定している
    """
    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y_%m%d_%H%M%S")
    result_dir = result_parent_dir / Path(f"{formatted_time}_{eval_name}")
    os.makedirs(result_dir, exist_ok=True)
    eval_data = pd.read_csv(eval_data_path)
    eval_data[
        ["answer", "retrieved_contexts", "execution_seconds"]
    ] = eval_data["question"].apply(
        lambda x: rag_func(x)
    )
    eval_data.to_csv(result_dir / "full_eval_data.csv")
    eval_dataset = Dataset.from_pandas(eval_data)
    result = evaluate(
        eval_dataset,
        metrics=[answer_relevancy, answer_similarity, context_recall, faithfulness],
        llm=bedrock_model,
        embeddings=bedrock_embedding_model,
        run_config=run_config
    )
    result.to_pandas().to_csv(result_dir / "eval_result.csv")
    print("result")
    print(result)
    with open(result_dir / "scores.json", "w", encoding="utf-8") as _file:
        _file.write(json.dumps(result._repr_dict))
    print(f"Detailed results are successfully saved under {result_dir}")
    return result
