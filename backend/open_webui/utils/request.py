from fastapi import Request


def extract_language(request: Request):
    accept_language = request.headers.get("accept-language") or "en-US"
    return accept_language.split(",")[0]
