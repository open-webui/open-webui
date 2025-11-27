
async def mem0_search(user_id: str, chat_id: str, last_message: str) -> list[str]:
    """
    预留的 Mem0 检索接口：当前为占位实现。
    未来可替换为实际检索逻辑，返回若干相关记忆条目（字符串）。
    增加 chat_id 便于按会话窗口区分/隔离记忆。
    """
    try:
        # TODO: 接入真实 Mem0 检索
        print("mem0_search")
        print("user_id:", user_id)
        print("chat_id:", chat_id)
        print("last_message:", last_message)
        return []
    except Exception as e:
        log.debug(f"Mem0 search failed: {e}")
        return []


async def mem0_delete(user_id: str, chat_id: str) -> bool:
    """
    删除指定用户在指定 chat 窗口下的所有 Mem0 相关记忆（占位实现）。
    未来可替换为实际删除逻辑。
    """
    try:
        # TODO: 接入真实删除逻辑（如按 chat_id 过滤）
        print("mem0_delete")
        print("user_id:", user_id)
        print("chat_id:", chat_id)
        return True
    except Exception as e:
        log.debug(f"Mem0 delete failed: {e}")
        return False
