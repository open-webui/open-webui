import os
import re
import hashlib
import httpx
import orjson
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from app.pseudonymizer import pseudonymize, detect_entities
from app.depseudonymizer import depseudonymize
from app.mapping_store import MappingStore
from app.logs import (
    log_sep, log_garnet, log_entity_filter,
    log_in_user, log_out_user, log_no_pii,
    log_in_file, log_out_file, log_large_file, log_out_file_chunked,
    log_file_scan, log_file_pii, log_file_pii_duplicate,
    log_internal, log_privacy_off, log_history_depseudo,
    log_to_llm, log_from_llm, log_to_user, log_mapping,
    log_self_loop, log_responses_api, log_image,
    log_health, log_vault_start, log_vault_done, log_vault_skip, log_vault_error,
    log_analyze, log_analyze_result,
    log_error, log_error_passthrough,
)

IMAGE_MODELS = ["dall-e-3", "dall-e-2", "gpt-image-1"]
RESPONSES_API_MODELS = {"gpt-5.5", "gpt-5.5-pro", "gpt-5.5-2026-04-23", "gpt-5.5-pro-2026-04-23"}

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")

SYSTEM_PROMPT_MARKERS = [
    "### Task:", "### Guidelines:", "### Output:",
    "JSON format:", "follow_ups", "Generate", "Suggest"
]


class ORJSONResponse(Response):
    media_type = "application/json"
    def render(self, content) -> bytes:
        return orjson.dumps(content)


app = FastAPI(default_response_class=ORJSONResponse)
store = MappingStore(ttl=3600)


def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return str(content)


def rebuild_content(original_content, pseudonymized_text: str):
    if isinstance(original_content, str):
        return pseudonymized_text
    if isinstance(original_content, list):
        result = []
        for block in original_content:
            if isinstance(block, dict) and block.get("type") == "text":
                result.append({"type": "text", "text": pseudonymized_text})
            else:
                result.append(block)
        return result
    return pseudonymized_text


def split_at_safe_boundary(buffer: str):
    TOKEN_NAMES = ['PERSON', 'ORGANIZATION', 'EMAIL_ADDRESS', 'IBAN_CODE', 'PHONE_NUMBER', 'ID', 'LOCATION']
    partial_pattern = r'(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|ID|LOCATION)_[a-f0-9]{0,7}$'

    for token in TOKEN_NAMES:
        for length in range(1, len(token) + 1):
            prefix = token[:length]
            if buffer.endswith(prefix):
                safe = buffer[:-len(prefix)]
                return safe, buffer[len(safe):]

    if re.search(partial_pattern, buffer):
        match = re.search(partial_pattern, buffer)
        safe = buffer[:match.start()]
        return safe, buffer[match.start():]

    return buffer, ""


def detect_internal_type(content: str) -> str:
    if "follow_ups" in content:
        return "follow_ups"
    if "Generate a concise" in content and "title" in content:
        return "title_gen"
    if "Generate 1-3 broad tags" in content or "categorizing the main themes" in content:
        return "tags_gen"
    if "search_query" in content or "Generate a hypothetical" in content:
        return "search_query"
    return "internal"


async def stream_with_depseudo(response_stream, mapping, pseudonymized_prompt, session_id, url, model, file_entity_count=0, garnet_breakdown=None, is_responses_api=False):
    yield orjson.dumps({
        "type": "pseudonymized_prompt",
        "content": pseudonymized_prompt or "",
        "file_entity_count": file_entity_count,
        "garnet_breakdown": garnet_breakdown or {}
    }) + b"\n\n"

    buffer = ""
    first_chunk = True
    async for chunk in response_stream:
        if not chunk:
            continue
        if chunk.startswith(b"data: "):
            raw = chunk[6:].strip()
        else:
            raw = chunk.strip()

        if raw == b"[DONE]":
            break

        try:
            parsed = orjson.loads(raw)
            if is_responses_api:
                if parsed.get("type") == "response.output_text.delta":
                    chunk_text = parsed.get("delta", "")
                else:
                    continue
            else:
                chunk_text = parsed["choices"][0]["delta"].get("content", "")
            if not chunk_text:
                continue
        except Exception:
            continue

        if first_chunk:
            log_from_llm(chunk_text)
            first_chunk = False

        buffer += chunk_text
        safe, remainder = split_at_safe_boundary(buffer)

        if safe:
            for token in sorted(mapping.keys(), key=len, reverse=True):
                safe = safe.replace(token, mapping[token])
            yield b"data: " + orjson.dumps({
                "choices": [{"delta": {"content": safe}}]
            }) + b"\n\n"

        buffer = remainder

    if buffer:
        for token in sorted(mapping.keys(), key=len, reverse=True):
            buffer = buffer.replace(token, mapping[token])
        yield b"data: " + orjson.dumps({
            "choices": [{"delta": {"content": buffer}}]
        }) + b"\n\n"

    log_to_user(len(mapping))
    log_sep()
    yield b"data: [DONE]\n\n"


@app.get("/health")
async def health():
    log_health()
    return {"status": "ok"}


@app.post("/vault/scan")
async def vault_scan(request: Request):
    body = await request.json()
    text = body.get("text", "")
    file_id = body.get("file_id")
    privacy_enabled = body.get("privacy_proxy", True)

    if not text:
        log_vault_error("text")
        return ORJSONResponse({"error": "text required"})
    if not file_id:
        log_vault_error("file_id")
        return ORJSONResponse({"error": "file_id required"})

    if not privacy_enabled:
        log_vault_skip(file_id)
        return ORJSONResponse({
            "file_id": file_id,
            "session_id": f"file:{file_id}",
            "pseudonymized_text": text,
            "entity_count": 0,
            "entity_breakdown": {},
            "preview": {"before": text[:500], "after": text[:500]}
        })

    enabled_header = request.headers.get("x-garnet-entities", "")
    enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] if enabled_header else None

    session_id = f"file:{file_id}"
    log_vault_start(file_id, session_id, enabled_types)

    existing_keys_before = set(store.get_store().get(session_id, {}).keys())
    pseudonymized = pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)
    new_keys = set(store.get_store().get(session_id, {}).keys()) - existing_keys_before

    report = {}
    for token in new_keys:
        prefix = token.rsplit("_", 1)[0]
        report[prefix] = report.get(prefix, 0) + 1

    log_vault_done(file_id, len(new_keys), report)

    return ORJSONResponse({
        "file_id": file_id,
        "session_id": session_id,
        "pseudonymized_text": pseudonymized,
        "entity_count": len(new_keys),
        "entity_breakdown": report,
        "preview": {"before": text[:500], "after": pseudonymized[:500]},
    })


@app.post("/analyze")
async def analyze(request: Request):
    body = await request.json()
    text = body.get("text", "")
    language = body.get("language")

    if not text:
        return JSONResponse({"entities": []})

    enabled_header = request.headers.get("x-garnet-entities", "")
    enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] if enabled_header else None

    log_analyze(language, enabled_types, text)
    entities = detect_entities(text, language, enabled_types=enabled_types)
    log_analyze_result(len(entities), [e.get("type") for e in entities])

    return JSONResponse({"entities": entities})


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    body = None
    if request.method in ("POST", "PUT"):
        body = await request.json()

    is_openai = path.startswith("openai/")
    actual_path = path[len("openai/"):] if is_openai else path
    is_chat = actual_path in ("v1/chat/completions", "api/chat", "v1/completions", "chat/completions")

    privacy_enabled = True
    pseudonymized_user_message = None
    session_id = "default"
    file_entity_count = 0
    garnet_breakdown = {}
    use_responses_api = False

    if body:
        privacy_enabled = body.pop("privacy_proxy", True)

    if is_openai:
        openai_url = request.headers.get("x-openai-base-url", OPENAI_API_URL)
        if "privacy-proxy" in openai_url or "localhost:8080" in openai_url:
            auth = request.headers.get("authorization", "")
            model_name = (body or {}).get("model", "").lower()
            if "sk-ant-" in auth:
                openai_url = "https://api.anthropic.com/v1"
            elif "AIza" in auth or "gemini" in model_name:
                openai_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            elif "gsk-" in auth or "groq" in model_name:
                openai_url = "https://api.groq.com/openai/v1"
            elif "sk-or-" in auth:
                openai_url = "https://openrouter.ai/api/v1"
            else:
                openai_url = OPENAI_API_URL
            log_self_loop(openai_url)
        url = f"{openai_url.rstrip('/')}/{actual_path}"
    else:
        url = f"{OLLAMA_URL}/{actual_path}"

    if is_chat and body:
        body["stream"] = False if not is_openai else True

        messages = body.get("messages", [])
        model = body.get("model", "unknown")
        first_msg = extract_text_content(messages[0].get("content", "")) if messages else ""

        session_id = (
            body.get("chat_id")
            or (messages[0].get("id") if messages else None)
            or (hashlib.md5(first_msg.encode()).hexdigest()[:12] if first_msg else "default")
        )
        body.pop("chat_id", None)

        use_responses_api = model in RESPONSES_API_MODELS
        if use_responses_api and is_openai:
            url = f"{openai_url.rstrip('/')}/responses"
            log_responses_api(model)

        if "groq" in url:
            provider_label = "groq"
        elif "gemini" in url or "googleapis" in url:
            provider_label = "gemini"
        elif "ollama" in url or "11434" in url:
            provider_label = "ollama"
        elif "anthropic" in url:
            provider_label = "anthropic"
        else:
            provider_label = "openai"

        log_sep()
        log_garnet(session_id, provider_label, privacy_enabled, model, actual_path)

        enabled_header = request.headers.get("x-garnet-entities", "")
        enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] if enabled_header else None
        if enabled_types:
            log_entity_filter(enabled_types)

        if messages:
            restored_count = 0
            for msg in messages[:-1]:
                if msg.get("role") == "assistant":
                    before = msg["content"]
                    msg["content"] = depseudonymize(msg["content"], session_id, store.get_store())
                    if msg["content"] != before:
                        restored_count += 1
            if restored_count > 0:
                log_history_depseudo(restored_count)

            last_message = messages[-1]
            original_content = last_message["content"]
            original_content_text = extract_text_content(original_content)

            has_rag_context = "<context>" in original_content_text or "<source" in original_content_text or "{{CONTEXT}}" in original_content_text
            is_system_prompt = not has_rag_context and any(marker in original_content_text for marker in SYSTEM_PROMPT_MARKERS)

            if not privacy_enabled:
                log_privacy_off()

            elif is_system_prompt:
                internal_type = detect_internal_type(original_content_text)
                log_internal(internal_type)
                pseudonymized_user_message = original_content_text

            elif last_message.get("role") in ("user", "system", "developer"):
                log_in_user(original_content_text)

                existing_keys_before = set(store.get_store().get(session_id, {}).keys())

                last_msg_index = len(messages) - 1
                file_msgs_scanned = 0
                for i, msg in enumerate(messages):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "assistant":
                        continue
                    if role == "user" and i == last_msg_index:
                        continue
                    content_text = extract_text_content(content)
                    has_rag = "<context>" in content_text or "{{CONTEXT}}" in content_text or "<source" in content_text
                    if not has_rag:
                        continue

                    log_in_file(role, len(content_text), content_text)

                    if len(content_text) > 50000:
                        chunk_size = 10000
                        overlap = 200
                        chunks = [
                            content_text[max(0, i - overlap):i + chunk_size]
                            for i in range(0, len(content_text), chunk_size)
                        ]
                        log_large_file(len(content_text), len(chunks))
                        pseudo_chunks = [
                            pseudonymize(c, session_id, store.get_store(), enabled_types=enabled_types)
                            for c in chunks
                        ]
                        pseudo = "".join(pseudo_chunks)
                        msg["content"] = rebuild_content(msg["content"], pseudo)
                        log_out_file_chunked(len(chunks), len(pseudo))
                        continue

                    try:
                        pseudonymized_text = pseudonymize(
                            content_text, session_id, store.get_store(), enabled_types=enabled_types
                        )
                        msg["content"] = rebuild_content(content, pseudonymized_text)
                        log_out_file(pseudonymized_text)
                        file_msgs_scanned += 1
                    except Exception as e:
                        log_error(f"file pseudonymization failed: {e} — skipping chunk")
                        continue

                if file_msgs_scanned > 0:
                    store.get_store().flush(session_id)
                    log_file_scan(file_msgs_scanned)

                new_keys = set(store.get_store().get(session_id, {}).keys()) - existing_keys_before
                file_entity_count = len(new_keys)

                if file_entity_count == 0:
                    seen_tokens = set()
                    for key, mapping in store._store.items():
                        if key.startswith("file:"):
                            seen_tokens.update(mapping.keys())
                    if not seen_tokens:
                        try:
                            from app.mapping_store import _redis_client
                            if _redis_client:
                                for rkey in _redis_client.keys("garnet:mapping:file:*"):
                                    raw = _redis_client.get(rkey)
                                    if raw:
                                        import json
                                        mapping = json.loads(raw)
                                        seen_tokens.update(mapping.keys())
                        except Exception:
                            pass
                    file_entity_count = len(seen_tokens)

                garnet_breakdown = {}
                try:
                    from app.mapping_store import _redis_client
                    if _redis_client:
                        for rkey in _redis_client.keys("garnet:mapping:file:*"):
                            raw = _redis_client.get(rkey)
                            if raw:
                                import json as _json
                                for token in _json.loads(raw).keys():
                                    prefix = token.rsplit("_", 1)[0]
                                    garnet_breakdown[prefix] = garnet_breakdown.get(prefix, 0) + 1
                except Exception:
                    pass

                if file_entity_count > 0:
                    log_file_pii(file_entity_count, garnet_breakdown)
                else:
                    if file_msgs_scanned > 0:
                        log_file_pii_duplicate()

                try:
                    pseudonymized_text = pseudonymize(
                        original_content_text, session_id, store.get_store(), enabled_types=enabled_types
                    )
                    last_message["content"] = rebuild_content(original_content, pseudonymized_text)
                    pseudonymized_user_message = pseudonymized_text
                    if pseudonymized_user_message != original_content_text:
                        log_out_user(pseudonymized_user_message)
                    else:
                        log_no_pii()
                    store.get_store().flush(session_id)
                except Exception as e:
                    log_error(f"user pseudonymization failed: {e} — forwarding raw")
                    pseudonymized_user_message = original_content_text
                    last_message["content"] = original_content

        log_to_llm(url, model)

    if is_openai:
        forward_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() in ("authorization", "content-type", "openai-organization", "x-openai-base-url")
        }
    else:
        forward_headers = {}

    if body and body.get("model") in IMAGE_MODELS:
        url = f"{openai_url.rstrip('/')}/images/generations"
        messages = body.get("messages", [])
        prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                prompt = extract_text_content(msg.get("content", ""))
                break
        image_body = {
            "model": body.get("model"),
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }
        log_image(body.get("model"), prompt, url)
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="POST",
                url=url,
                json=image_body,
                headers=forward_headers,
                timeout=300.0
            )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type="application/json"
        )

    if is_chat and body and not is_openai:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=url,
                json=body,
                headers=forward_headers,
                timeout=120.0
            )
        try:
            result = orjson.loads(response.content)
            content = result.get("message", {}).get("content", "")

            session_mapping = dict(store.get_store().get(session_id, {}))
            if privacy_enabled:
                for key, mapping in store._store.items():
                    if key.startswith("file:"):
                        session_mapping.update(mapping)

            for token in sorted(session_mapping.keys(), key=len, reverse=True):
                content = content.replace(token, session_mapping[token])

            result["message"]["content"] = content
            result["pseudonymized_prompt"] = pseudonymized_user_message or ""
            result["file_entity_count"] = file_entity_count

            log_to_user(len(session_mapping))
            log_sep()
            return ORJSONResponse(content=result)

        except Exception as e:
            log_error(f"Ollama depseudo failed: {e} | raw={response.content[:200]}")
            return Response(content=response.content, status_code=response.status_code)

    if is_chat and body:
        if use_responses_api:
            body["input"] = [{"role": m["role"], "content": m["content"]} for m in messages]
            body.pop("messages", None)

        async def response_stream():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    method=request.method,
                    url=url,
                    json=body,
                    headers=forward_headers,
                    timeout=120.0
                ) as resp:
                    if resp.status_code != 200:
                        log_error(f"status={resp.status_code} provider={url}")
                    async for line in resp.aiter_lines():
                        if line:
                            yield line.encode()

        session_mapping = dict(store.get_store().get(session_id, {}))
        if privacy_enabled:
            for key, mapping in store._store.items():
                if key.startswith("file:"):
                    session_mapping.update(mapping)

        model = body.get("model", "unknown")
        log_mapping(session_id, len(session_mapping))

        return StreamingResponse(
            stream_with_depseudo(
                response_stream(), session_mapping, pseudonymized_user_message,
                session_id, url, model, file_entity_count, garnet_breakdown,
                is_responses_api=use_responses_api
            ),
            media_type="text/event-stream"
        )

    async with httpx.AsyncClient() as client:
        if body:
            response = await client.request(
                method=request.method,
                url=url,
                json=body,
                headers=forward_headers,
                timeout=120.0
            )
        else:
            response = await client.request(
                method=request.method,
                url=url,
                headers=forward_headers,
                timeout=120.0
            )

    if response.status_code != 200:
        log_error_passthrough(response.status_code, url, response.text)

    excluded_headers = {"content-encoding", "content-length", "transfer-encoding"}
    filtered_headers = {
        k: v for k, v in response.headers.items()
        if k.lower() not in excluded_headers
    }
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=filtered_headers
    )