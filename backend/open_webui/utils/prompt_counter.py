import time
from typing import List, Dict
from fastapi import Request, Depends
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
import logging
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

PROMPT_KEYWORDS: Dict[str, List[str]] = {
    "/help_study": ["help me study", "vocabulary", "помоги с учебой", "учить слова","поможешь с учебой"],
    "/code_snippet": ["code snippet", "sticky header", "фрагмент кода", "кусок кода"],
    "/fun_fact": ["fun fact", "roman empire", "интересный факт", "римская империя"],
    "/options_trading": ["options trading", "stocks", "торговля опционами", "акции"],
    "/procrastination_tips": ["procrastination", "tips", "прокрастинация", "советы"],
    "/kids_art_ideas": ["kids art", "creative things", "идеи для детского творчества", "поделки"],
}

def detect_prompt_usage(message_content: str) -> List[str]:
    text = (message_content or "").lower()
    detected_prompts = []

    for prompt_command, keywords in PROMPT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            detected_prompts.append(prompt_command)
    
    return detected_prompts

def update_prompt_counter(request: Request, user_id: str, prompts_used: List[str]) -> None:
    if not prompts_used: return
    today = time.strftime("%Y-%m-%d")
    c = request.app.state.PROMPT_USAGE_COUNTER
    for p in prompts_used:
        c["total_usage"] += 1
        c["by_prompt"][p] = c["by_prompt"].get(p, 0) + 1
        c["by_user"][user_id] = c["by_user"].get(user_id, 0) + 1
        c["by_date"][today] = c["by_date"].get(today, 0) + 1
    log.info("Счетчик успешно обновлен.")

def process_prompt_usage(
    request: Request,
    user: UserModel,
    form_data: dict
) -> None:
    log.info(f"DEBUG: process_prompt_usage вызвана для пользователя {user.id}")

    messages = form_data.get("messages", [])
    if not messages:
        log.debug("DEBUG: В теле запроса нет сообщений.")
        return
    last_user_msg = next((m for m in reversed(messages) 
                          if m.get("role") == "user" 
                          and isinstance(m.get("content"),str)),None)
    log.debug(f"DEBUG: Последнее сообщение пользователя: {last_user_msg}")

    if last_user_msg:
        user_content = last_user_msg["content"]
        if user_content.strip().startswith("### Task:"):
            log.debug("DEBUG: Обнаружено системное сообщение для 'follow-up', подсчет пропущен.")
            return
        prompts = detect_prompt_usage(last_user_msg["content"])
        log.debug(f"DEBUG: Обнаруженные промпты: {prompts}")
        if prompts:
            log.info("Обновление счетчика!")
            update_prompt_counter(request, user.id, prompts)
    else:
        log.debug("DEBUG: Сообщений от пользователя не найдено.")