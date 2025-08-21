"""
Memory Hook Provider
会話を自動的に Memory に保存し、過去の記憶を取得する
"""

from bedrock_agentcore.memory import MemoryClient
from strands.hooks.events import AgentInitializedEvent, MessageAddedEvent
from strands.hooks.registry import HookProvider, HookRegistry
from typing import Optional
import copy


class MemoryHook(HookProvider):
    """Memory 管理を自動化する Hook"""
    
    def __init__(
        self,
        memory_client: MemoryClient,
        memory_id: str,
        actor_id: str,
        session_id: str,
        namespace_prefix: Optional[str] = None,
    ):
        """
        Args:
            memory_client: Memory クライアント
            memory_id: Memory リソース ID
            actor_id: アクター（顧客）ID
            session_id: セッション ID
            namespace_prefix: 名前空間のプレフィックス（デフォルト: ""）
        """
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespace_prefix = namespace_prefix or ""

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
                ユーザーの嗜好や問題を直接回答しないでください。
                ユーザーの嗜好や問題は、ユーザーをより理解するために厳密に使用してください。
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
                        namespace=f"{self.namespace_prefix}/preferences/{self.actor_id}",
                        query=messages[-1]["content"][0]["text"],
                        init_content="これらはユーザーの嗜好です:",
                        event=event,
                    )

                    # ユーザーの問題を取得してコンテキストに追加
                    self._add_context_user_query(
                        namespace=f"{self.namespace_prefix}/issues/{self.actor_id}",
                        query=messages[-1]["content"][0]["text"],
                        init_content="これらはユーザーの問題です:",
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