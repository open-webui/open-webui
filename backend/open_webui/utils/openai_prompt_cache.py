"""OpenAI Responses prompt-cache request helpers."""


def apply_responses_prompt_cache_key(
    payload: dict,
    metadata: dict | None,
    api_config: dict,
) -> dict:
    """日期：2026-07-30；作者：苍朮；用途：按根聊天标识为 OpenAI Responses 请求注入稳定缓存键。

    参数：
        payload：即将发送给 OpenAI-compatible 上游的请求负载。
        metadata：包含当前聊天与可选根聊天标识的 Open WebUI 内部元数据。
        api_config：当前 OpenAI-compatible 连接配置。

    返回：
        注入缓存键后的原请求负载。
    """
    if api_config.get('api_type') != 'responses' or api_config.get('azure') or api_config.get('provider') == 'azure':
        return payload

    if 'prompt_cache_key' in payload:
        return payload

    metadata = metadata or {}
    root_chat_id = metadata.get('root_chat_id')
    chat_id = root_chat_id if isinstance(root_chat_id, str) and root_chat_id.strip() else metadata.get('chat_id')
    if not isinstance(chat_id, str) or not chat_id.strip():
        return payload

    payload['prompt_cache_key'] = chat_id.strip()
    return payload
