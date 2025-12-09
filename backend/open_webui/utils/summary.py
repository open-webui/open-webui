from typing import Dict, List, Optional, Tuple, Sequence, Any
import json
import re
import os
from dataclasses import dataclass
from logging import getLogger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from open_webui.models.chats import Chats
from open_webui.config import OPENAI_API_KEYS, OPENAI_API_BASE_URLS

log = getLogger(__name__)

# --- Constants & Prompts from persona_extractor ---

SUMMARY_PROMPT = """你是一名“对话历史整理员”，请在保持事实准确的前提下，概括当前为止的聊天记录。
## 要求
1. 最终摘要不得超过 1000 字。
2. 聚焦人物状态、事件节点、情绪/意图等关键信息，将片段整合为连贯文字。
3. 输出需包含 who / how / why / what 四个字段，每项不超过 50 字。
4. 禁止臆测或脏话，所有内容都必须能在聊天中找到对应描述。
5. 目标：帮助后续对话快速回忆上下文与人物设定。

已存在的摘要（如无则写“无”）：
{existing_summary}

聊天片段：
---CHATS---
{chat_transcript}
---END---

请严格输出下列 JSON：
{{
  "summary": "不超过1000字的连贯摘要",
  "table": {{
    "who": "不超过50字",
    "how": "不超过50字",
    "why": "不超过50字",
    "what": "不超过50字"
  }}
}}
"""

MERGE_ONLY_PROMPT = """你是一名“对话历史整理员”。
请将以下两段对话摘要（A 和 B）合并为一段连贯的、更新后的对话历史摘要。
摘要 A 是较早的时间段，摘要 B 是较新的时间段。

【摘要 A (旧)】
{summary_a}

【摘要 B (新)】
{summary_b}

## 要求
1. 保持时间线的连贯性，将新发生的事自然接续在旧事之后。
2. 最终摘要不得超过 1000 字。
3. 依然提取 who / how / why / what 四个关键要素（基于合并后的全貌）。
4. 禁止臆测，只基于提供的摘要内容。

请严格输出下列 JSON：
{{
  "summary": "合并后的连贯摘要",
  "table": {{
    "who": "不超过50字",
    "how": "不超过50字",
    "why": "不超过50字",
    "what": "不超过50字"
  }}
}}
"""

@dataclass
class HistorySummary:
    summary: str
    table: dict[str, str]

@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str
    timestamp: Optional[Any] = None
    
    def formatted(self) -> str:
        return f"{self.role}: {self.content}"

class HistorySummarizer:
    def __init__(
        self,
        *,
        client: Optional[Any] = None,
        model: str = "gpt-4.1-mini",
        max_output_tokens: int = 800,
        temperature: float = 0.1,
        max_messages: int = 120,
    ) -> None:
        if client is None:
            if OpenAI is None:
                log.warning("OpenAI client not available. Install openai>=1.0.0.")
            else:
                try:
                    # 尝试从配置获取 API Key 和 Base URL
                    api_keys = OPENAI_API_KEYS.value if hasattr(OPENAI_API_KEYS, "value") else []
                    base_urls = OPENAI_API_BASE_URLS.value if hasattr(OPENAI_API_BASE_URLS, "value") else []
                    
                    api_key = api_keys[0] if api_keys else os.environ.get("OPENAI_API_KEY")
                    base_url = base_urls[0] if base_urls else os.environ.get("OPENAI_API_BASE_URL")
                    
                    if api_key:
                        kwargs = {"api_key": api_key}
                        if base_url:
                            kwargs["base_url"] = base_url
                        client = OpenAI(**kwargs)
                    else:
                        log.warning("No OpenAI API key found.")

                except Exception as e:
                    log.warning(f"Failed to init OpenAI client: {e}")
        
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
        self._max_messages = max_messages

    def summarize(
        self,
        messages: Sequence[Dict],
        *,
        existing_summary: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[HistorySummary]:
        if not messages and not existing_summary:
            return None
        
        # 转换 dict 消息为 ChatMessage 格式用于 prompt 生成
        # 确保消息按时间戳排序，防止乱序导致切片错误
        sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', 0) if isinstance(m.get('timestamp'), (int, float)) else 0)
        
        # 如果有 existing_summary，我们可以适当减少这里的消息量，或者依然取最近的
        # 但为了逻辑简单，我们还是取最近的 max_messages
        trail = sorted_messages[-self._max_messages :]
        transcript = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in trail)
        
        prompt = SUMMARY_PROMPT.format(
            existing_summary=existing_summary.strip() if existing_summary else "无",
            chat_transcript=transcript,
        )
        
        if not self._client:
            log.error("No OpenAI client available for summarization.")
            return None

        log.info(f"Starting summary generation for {len(messages)} messages...")
        
        # Try primary client first
        try:
            # 增加 max_tokens 限制，避免摘要过长被截断，同时留给 JSON 结构足够的空间
            # 根据经验，1000 字摘要 + JSON 结构大约需要 1500 tokens
            safe_max_tokens = max(max_tokens or self._max_output_tokens, 2000)
            
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=safe_max_tokens,
                temperature=self._temperature,
            )
            
            # Debug: Print full response to investigate empty content issues
            log.info(f"Full Summary API Response: {response}")

            payload = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            if finish_reason == "length":
                log.warning("Summary generation was truncated due to length limit!")
                
            log.info(f"Summary generation completed. Payload length: {len(payload)}")
            log.info(f"Summary Content:\n{payload}")
            
            return self._parse_response(payload)

        except Exception as e:
            log.warning(f"Summarization failed: {e}")
            return None

    def merge_summaries(
        self,
        summary_a: str,
        summary_b: str,
        *,
        max_tokens: Optional[int] = None,
    ) -> Optional[HistorySummary]:
        if not summary_a and not summary_b:
            return None
            
        prompt = MERGE_ONLY_PROMPT.format(
            summary_a=summary_a or "无",
            summary_b=summary_b or "无",
        )
        
        if not self._client:
            return None

        log.info(f"Starting summary merge (A len={len(summary_a)}, B len={len(summary_b)})...")
        
        # Try primary client
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens or self._max_output_tokens,
                temperature=self._temperature,
            )
            
            payload = response.choices[0].message.content or ""
            log.info("Summary merge completed successfully.")
            return self._parse_response(payload)

        except Exception as e:
            log.warning(f"Merge failed: {e}")
            return None

    def _parse_response(self, payload: str) -> HistorySummary:
        data = _safe_json_loads(payload)
        
        # 如果解析出的 data 是空或者不是 dict，尝试直接用 payload
        if not isinstance(data, dict) or (not data and not payload.strip().startswith("{")):
             summary = payload.strip()
             table = {}
        else:
            summary = str(data.get("summary", "")).strip()
            table_payload = data.get("table", {}) or {}
            table = {
                "who": str(table_payload.get("who", "")).strip(),
                "how": str(table_payload.get("how", "")).strip(),
                "why": str(table_payload.get("why", "")).strip(),
                "what": str(table_payload.get("what", "")).strip(),
            }

        if not summary:
            summary = payload.strip()
            
        if len(summary) > 1000:
            summary = summary[:1000].rstrip() + "..."
            
        return HistorySummary(summary=summary, table=table)

def _safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 简单的正则提取尝试
        match = re.search(r'(\{.*\})', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {}


# --- Core Logic Modules ---

def build_ordered_messages(
    messages_map: Optional[Dict], anchor_id: Optional[str] = None
) -> List[Dict]:
    """
    将消息 map 还原为有序列表

    策略：
    1. 优先：基于 parentId 链条追溯（从 anchor_id 向上回溯到根消息）
    2. 退化：按时间戳排序（无 anchor_id 或追溯失败时）

    参数：
        messages_map: 消息 map，格式 {"msg-id": {"role": "user", "content": "...", "parentId": "...", "timestamp": 123456}}
        anchor_id: 锚点消息 ID（链尾），从此消息向上追溯

    返回：
        有序的消息列表，每个消息包含 id 字段
    """
    if not messages_map:
        return []

    # 补齐消息的 id 字段
    def with_id(message_id: str, message: Dict) -> Dict:
        return {**message, **({"id": message_id} if "id" not in message else {})}

    # 模式 1：基于 parentId 链条追溯
    if anchor_id and anchor_id in messages_map:
        ordered: List[Dict] = []
        current_id: Optional[str] = anchor_id

        while current_id:
            current_msg = messages_map.get(current_id)
            if not current_msg:
                break
            ordered.insert(0, with_id(current_id, current_msg))
            current_id = current_msg.get("parentId")

        return ordered

    # 模式 2：基于时间戳排序
    sortable: List[Tuple[int, str, Dict]] = []
    for mid, message in messages_map.items():
        ts = (
            message.get("createdAt")
            or message.get("created_at")
            or message.get("timestamp")
            or 0
        )
        sortable.append((int(ts), mid, message))

    sortable.sort(key=lambda x: x[0])
    return [with_id(mid, msg) for _, mid, msg in sortable]


def get_recent_messages_by_user_id(user_id: str, chat_id: str, num: int) -> List[Dict]:
    """
    获取指定用户的最近 N 条消息（优先当前会话，然后按时间顺序）

    参数：
        user_id: 用户 ID
        chat_id: 当前会话 ID（用于优先提取）
        num: 需要获取的消息数量（<= 0 时返回全部）

    返回：
        有序的消息列表（优先当前会话，不足时由全局最近补齐）
    """
    current_chat_messages: List[Dict] = []
    other_messages: List[Dict] = []

    # 遍历用户的所有聊天
    chats = Chats.get_chat_list_by_user_id(user_id, include_archived=True)
    for chat in chats:
        messages_map = chat.chat.get("history", {}).get("messages", {}) or {}
        # 简单判断是否为当前会话
        is_current_chat = (str(chat.id) == str(chat_id))

        for mid, msg in messages_map.items():
            # 跳过空内容
            if msg.get("content", "") == "":
                continue
            ts = (
                msg.get("createdAt")
                or msg.get("created_at")
                or msg.get("timestamp")
                or 0
            )
            entry = {**msg, "id": mid}
            entry.setdefault("chat_id", chat.id)
            entry.setdefault("timestamp", int(ts))
            
            if is_current_chat:
                current_chat_messages.append(entry)
            else:
                other_messages.append(entry)

    # 分别排序
    current_chat_messages.sort(key=lambda m: m.get("timestamp", 0))
    other_messages.sort(key=lambda m: m.get("timestamp", 0))

    if num <= 0:
        combined = current_chat_messages + other_messages
        combined.sort(key=lambda m: m.get("timestamp", 0))
        return combined

    # 策略：优先保留当前会话消息
    if len(current_chat_messages) >= num:
        return current_chat_messages[-num:]
    
    # 补充不足的部分
    needed = num - len(current_chat_messages)
    supplement = other_messages[-needed:] if other_messages else []
    
    # 合并并最终按时间排序
    final_list = supplement + current_chat_messages
    final_list.sort(key=lambda m: m.get("timestamp", 0))
    
    return final_list


def slice_messages_with_summary(
    messages_map: Dict,
    boundary_message_id: Optional[str],
    anchor_id: Optional[str],
    pre_boundary: int = 20,
) -> List[Dict]:
    """
    基于摘要边界裁剪消息列表（返回摘要前 N 条 + 摘要后全部消息）

    策略：保留摘要边界前 N 条消息（提供上下文）+ 摘要后全部消息（最新对话）
    目的：降低 token 消耗，同时保留足够的上下文信息

    参数：
        messages_map: 消息 map
        boundary_message_id: 摘要边界消息 ID（None 时返回全量消息）
        anchor_id: 锚点消息 ID（链尾）
        pre_boundary: 摘要边界前保留的消息数量（默认 20）

    返回：
        裁剪后的有序消息列表

    示例：
        100 条消息，摘要边界在第 50 条，pre_boundary=20
        → 返回消息 29-99（共 71 条）
    """
    ordered = build_ordered_messages(messages_map, anchor_id)

    if boundary_message_id:
        try:
            # 查找摘要边界消息的索引
            boundary_idx = next(
                idx for idx, msg in enumerate(ordered) if msg.get("id") == boundary_message_id
            )
            # 计算裁剪起点
            start_idx = max(boundary_idx - pre_boundary, 0)
            ordered = ordered[start_idx:]
        except StopIteration:
            # 边界消息不存在，返回全量
            pass

    return ordered


def summarize(messages: List[Dict], old_summary: Optional[str] = None, model: Optional[str] = None) -> str:
    """
    生成对话摘要

    参数：
        messages: 需要摘要的消息列表
        old_summary: 旧摘要
        model: 指定使用的模型 ID（如果为 None，则使用类内部默认值）

    返回：
        摘要字符串
    """
    summarizer = HistorySummarizer(model=model) if model else HistorySummarizer()
    result = summarizer.summarize(messages, existing_summary=old_summary)
    return result.summary if result else ""

def compute_token_count(messages: List[Dict]) -> int:
    """
    计算消息的 token 数量（占位实现）

    当前算法：4 字符 ≈ 1 token（粗略估算）
    TODO：接入真实 tokenizer（如 tiktoken for OpenAI models）
    """
    total_chars = 0
    for msg in messages:
        content = msg.get('content')
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
             for item in content:
                 if isinstance(item, dict) and 'text' in item:
                     total_chars += len(item['text'])
    
    return max(total_chars // 4, 0)
