
from typing import List, Dict


def last_process_payload(
    user_id: str,
    session_id: str,
    messages: List[Dict],
):
    """
    对调用 LLM API 前的上下文信息 进行加工。

    Args:
        user_id (str): 用户的唯一 ID。
        session_id (str): 该用户本次对话/会话的 ID。
        messages (List[Dict]): 该用户在该对话下的聊天消息列表，
            形如 {"role": "system|user|assistant", "content": "...", "timestamp": 0}。
    """
    print("user_id:", user_id)
    print("session_id:", session_id)
    print("messages:", messages)
