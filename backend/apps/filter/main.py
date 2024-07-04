import logging
import os
import time

from apps.filter.wordsSearch import wordsSearch
from config import (
    ENABLE_MESSAGE_FILTER,
    CHAT_FILTER_WORDS_FILE,
    CHAT_FILTER_WORDS,
    ENABLE_REPLACE_FILTER_WORDS,
    REPLACE_FILTER_WORDS,
    AppConfig,
)
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils.utils import (
    get_admin_user,
)
from pydantic import BaseModel
from config import SRC_LOG_LEVELS, DATA_DIR, PersistentConfig

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["FILTER"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()

app.state.config.ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER
app.state.config.CHAT_FILTER_WORDS_FILE = CHAT_FILTER_WORDS_FILE
app.state.config.CHAT_FILTER_WORDS = CHAT_FILTER_WORDS
app.state.config.ENABLE_REPLACE_FILTER_WORDS = ENABLE_REPLACE_FILTER_WORDS
app.state.config.REPLACE_FILTER_WORDS = REPLACE_FILTER_WORDS

file_path = os.path.join(DATA_DIR, app.state.config.CHAT_FILTER_WORDS_FILE)


def init_file():
    if app.state.config.CHAT_FILTER_WORDS_FILE:
        if os.path.exists(DATA_DIR):
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    lines = file.readlines()
                    unique_lines = set(line.strip() for line in lines)
                    joined_text = ",".join(unique_lines)
                    app.state.config.CHAT_FILTER_WORDS = joined_text if joined_text else "",
            else:
                write_words_to_file()


init_file()
search = None
if app.state.config.ENABLE_MESSAGE_FILTER and app.state.config.CHAT_FILTER_WORDS:
    search = wordsSearch()
    search.SetKeywords(str(app.state.config.CHAT_FILTER_WORDS).split(","))


class FILTERConfigForm(BaseModel):
    ENABLE_MESSAGE_FILTER: bool
    CHAT_FILTER_WORDS: str
    CHAT_FILTER_WORDS_FILE: str
    ENABLE_REPLACE_FILTER_WORDS: bool
    REPLACE_FILTER_WORDS: str


@app.get("/config")
async def get_filter_config(user=Depends(get_admin_user)):
    return {
        "ENABLE_MESSAGE_FILTER": app.state.config.ENABLE_MESSAGE_FILTER,
        "CHAT_FILTER_WORDS": app.state.config.CHAT_FILTER_WORDS,
        "CHAT_FILTER_WORDS_FILE": app.state.config.CHAT_FILTER_WORDS_FILE,
        "ENABLE_REPLACE_FILTER_WORDS": app.state.config.ENABLE_REPLACE_FILTER_WORDS,
        "REPLACE_FILTER_WORDS": app.state.config.REPLACE_FILTER_WORDS,
    }


@app.post("/config/update")
async def update_filter_config(
    form_data: FILTERConfigForm, user=Depends(get_admin_user)
):
    global search
    global file_path

    app.state.config.ENABLE_MESSAGE_FILTER = form_data.ENABLE_MESSAGE_FILTER
    app.state.config.CHAT_FILTER_WORDS_FILE = form_data.CHAT_FILTER_WORDS_FILE
    app.state.config.ENABLE_REPLACE_FILTER_WORDS = form_data.ENABLE_REPLACE_FILTER_WORDS
    app.state.config.REPLACE_FILTER_WORDS = form_data.REPLACE_FILTER_WORDS

    request_file_path = os.path.join(DATA_DIR, app.state.config.CHAT_FILTER_WORDS_FILE)

    if request_file_path != file_path:
        app.state.config.CHAT_FILTER_WORDS = form_data.CHAT_FILTER_WORDS
        file_path = request_file_path
        init_file()

    else:
        if app.state.config.CHAT_FILTER_WORDS != form_data.CHAT_FILTER_WORDS:
            app.state.config.CHAT_FILTER_WORDS = form_data.CHAT_FILTER_WORDS
            write_words_to_file()

    search = wordsSearch()
    search.SetKeywords(str(app.state.config.CHAT_FILTER_WORDS).split(","))

    return {
        "ENABLE_MESSAGE_FILTER": app.state.config.ENABLE_MESSAGE_FILTER,
        "CHAT_FILTER_WORDS": app.state.config.CHAT_FILTER_WORDS,
        "CHAT_FILTER_WORDS_FILE": app.state.config.CHAT_FILTER_WORDS_FILE,
        "ENABLE_REPLACE_FILTER_WORDS": app.state.config.ENABLE_REPLACE_FILTER_WORDS,
        "REPLACE_FILTER_WORDS": app.state.config.REPLACE_FILTER_WORDS,
    }


def filter_message(payload: dict):
    if app.state.config.ENABLE_MESSAGE_FILTER and search:
        if payload.get("messages") and search:
            start_time = time.time()
            for message in reversed(payload["messages"]):
                if message.get("role") == "user":
                    content = message.get("content")
                    if not isinstance(content, list):
                        filter_condition = search.FindFirst(content)
                        if filter_condition:
                            if not app.state.config.ENABLE_REPLACE_FILTER_WORDS:
                                filter_word = filter_condition["Keyword"]
                                detail_message = (
                                    f"Open WebUI: Your message contains bad words (`{filter_word}`) "
                                    "and cannot be sent. Please create a new topic and try again."
                                )
                                log.info(
                                    "The time taken to check the filter words: %.6fs",
                                    time.time() - start_time,
                                )
                                raise HTTPException(
                                    status_code=503, detail=detail_message
                                )
                            else:
                                message["content"] = search.Replace(
                                    content, app.state.config.REPLACE_FILTER_WORDS
                                )
                                log.info(
                                    f"Replace bad words in content: {message['content']}"
                                )
            log.info(
                "The time taken to check the bad words: %.6fs",
                time.time() - start_time,
            )


def write_words_to_file():
    new_bad_words = set(
        word.strip() for word in app.state.config.CHAT_FILTER_WORDS.split(",")
    )
    app.state.config.CHAT_FILTER_WORDS = ",".join(sorted(new_bad_words))
    if app.state.config.CHAT_FILTER_WORDS:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("\n".join(sorted(new_bad_words)) + "\n")
    else:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("")
    log.info(f"Create a new bad words file: {file_path}")
