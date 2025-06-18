import os
import re
from typing import TYPE_CHECKING
from dotenv import load_dotenv

import streamlit as st
import boto3

# from logics.rag_logics import call_rag
# from logics.rag_logics_6_3_1 import call_rag
from logics.rag_logics_6_3_3 import call_rag

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
    from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient


# 環境変数の読み込み
load_dotenv(".env", verbose=True)

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
REGION = "us-west-2"

agents_for_bedrock_runtime: "AgentsforBedrockRuntimeClient" = boto3.client(
    "bedrock-agent-runtime", region_name=REGION)
bedrock_runtime: "BedrockRuntimeClient" = boto3.client(
    service_name="bedrock-runtime",
    region_name=REGION
)


def split_answer_and_thinking(llm_output: str) -> dict:
    """LLM から生成された出力内容が<thinking></thinking> タグと <anwer></answer> タグで
    囲まれているのでそれぞれ分離する。
    """
    result = {"answer": "", "thinking": ""}
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_output, re.DOTALL)
    if thinking_match:
        result["thinking"] = thinking_match.group(1).strip()

    # answer タグの内容を抽出
    answer_match = re.search(r'<answer>(.*?)</answer>', llm_output, re.DOTALL)
    if answer_match:
        result["answer"] = answer_match.group(1).strip()

    return result


def main():
    # Streamlitアプリケーション
    st.title("Bedrock Chat App")
    st.sidebar.title("LLM の出力した思考過程")
    thinking_display = st.sidebar.empty()
    st.sidebar.title("検索結果")
    context_display = st.sidebar.empty()

    # セッション状態の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザー入力
    if question := st.chat_input("あなたの質問を入力してください"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        response, context = call_rag(
            question,
            KNOWLEDGE_BASE_ID,
            agents_for_bedrock_runtime,
            bedrock_runtime,
            MODEL_ID
        )
        splitted_output = split_answer_and_thinking(response)
        # サイドバーに LLM の思考過程を表示
        with thinking_display.container():
            st.markdown(splitted_output["thinking"])
        # サイドバーに検索結果を表示
        with context_display.container():
            st.json(context)

        # 応答の表示
        st.session_state.messages.append({"role": "assistant", "content": splitted_output["answer"]})
        with st.chat_message("assistant"):
            st.markdown(splitted_output["answer"])


if __name__ == "__main__":
    main()

