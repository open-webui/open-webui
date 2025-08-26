import time
from typing import List, Dict
from fastapi import Request, Depends
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
import logging
from open_webui.env import SRC_LOG_LEVELS
from datetime import date
import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from open_webui.internal.db import SessionLocal
from open_webui.models.prompt_usage import PromptUsage
from open_webui.models.prompts import Prompts

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
    text = (message_content or "").strip()
    lower_text = text.lower()
    detected_prompts: List[str] = []

    # 1) Приоритет: явные слэш-команды, существующие в БД Prompts
    if text.startswith("/"):
        first_token = text.split(maxsplit=1)[0]  # до первого пробела
        # команда в БД хранится с ведущим '/'
        prompt = Prompts.get_prompt_by_command(first_token)
        if prompt is not None:
            detected_prompts.append(first_token)
            return detected_prompts

    # 2) Фолбэк: эвристика по ключевым словам (для стартовых подсказок UI)
    for prompt_command, keywords in PROMPT_KEYWORDS.items():
        if any(keyword in lower_text for keyword in keywords):
            detected_prompts.append(prompt_command)
    
    return detected_prompts

def update_prompt_counter_db(user_id: str, prompts_used: List[str]) -> None:
    if not prompts_used:
        return
    today = date.today()
    now_ms = int(time.time() * 1000)
    db = SessionLocal()
    try:
        for p in prompts_used:
            # попытка найти существующую запись на сегодня
            existing = db.execute(
                select(PromptUsage).where(
                    PromptUsage.user_id == user_id,
                    PromptUsage.prompt == p,
                    PromptUsage.used_date == today,
                )
            ).scalar_one_or_none()

            if existing:
                existing.count = (existing.count or 0) + 1
                existing.updated_at = now_ms
            else:
                db.add(
                    PromptUsage(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        prompt=p,
                        used_date=today,
                        count=1,
                        created_at=now_ms,
                        updated_at=now_ms,
                    )
                )
        db.commit()
    except IntegrityError:
        db.rollback()
        # В редких гонках повторим поиск/инкремент
        for p in prompts_used:
            existing = db.execute(
                select(PromptUsage).where(
                    PromptUsage.user_id == user_id,
                    PromptUsage.prompt == p,
                    PromptUsage.used_date == today,
                )
            ).scalar_one_or_none()
            if existing:
                existing.count = (existing.count or 0) + 1
                existing.updated_at = now_ms
        db.commit()
    finally:
        db.close()


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
    # Дополнительно сохраним в БД
    update_prompt_counter_db(user_id, prompts_used)


def process_prompt_usage(
    request: Request,
    user: UserModel,
    form_data: dict
) -> None:
    # Подсчет производится только по клику на подсказку через /prompts/usage/click
    return