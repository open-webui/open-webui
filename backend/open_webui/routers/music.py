import base64
import json
import logging
import mimetypes
import os
import time
import uuid
from pathlib import Path

import aiofiles
import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from open_webui.config import CACHE_DIR
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT, SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user, get_verified_user_or_none
from open_webui.utils.domain_credits import commit_generation, preflight_generation

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ROUTERS", logging.INFO))

MUSIC_CACHE_DIR = CACHE_DIR / "music" / "generations"
MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


_MUSIC_MEDIA_TYPE_BY_EXT: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
}


def _sanitize_ext(ext: str | None) -> str:
    ext = (ext or "").strip().lower()
    if ext.startswith("."):
        ext = ext[1:]
    return ext or "mp3"


def _guess_ext_for_media_type(media_type: str | None) -> str:
    media_type = (media_type or "").split(";", 1)[0].strip().lower()
    if media_type == "audio/mpeg":
        return "mp3"
    if media_type == "audio/wav" or media_type == "audio/wave":
        return "wav"
    if media_type == "audio/ogg":
        return "ogg"
    if media_type == "audio/mp4":
        return "m4a"

    ext = mimetypes.guess_extension(media_type or "") or ""
    return _sanitize_ext(ext)


def _guess_media_type_for_ext(ext: str) -> str:
    ext = _sanitize_ext(ext)
    return (
        _MUSIC_MEDIA_TYPE_BY_EXT.get(ext)
        or mimetypes.types_map.get(f".{ext}")
        or "application/octet-stream"
    )


def _music_cache_paths(*, audio_id: str, ext: str) -> tuple[Path, Path]:
    safe_ext = _sanitize_ext(ext)
    file_path = MUSIC_CACHE_DIR / f"{audio_id}.{safe_ext}"
    meta_path = MUSIC_CACHE_DIR / f"{audio_id}.json"
    return file_path, meta_path


def _get_or_set_anon_id(request: Request, response: Response) -> str:
    anon_id = (
        request.headers.get("X-OWUI-ANON-ID")
        or request.cookies.get("owui_anon_id")
        or ""
    ).strip()
    if anon_id:
        return anon_id

    anon_id = uuid.uuid4().hex
    response.set_cookie(
        key="owui_anon_id",
        value=anon_id,
        max_age=60 * 60 * 24 * 365,
        samesite="lax",
    )
    return anon_id


class MusicConfig(BaseModel):
    ENABLE_MUSIC_GENERATION: bool
    MUSIC_API_BASE_URL: str
    MUSIC_API_KEY: str
    MUSIC_API_GENERATE_PATH: str
    MUSIC_MODEL: str


@router.get("/config", response_model=MusicConfig)
async def get_music_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_MUSIC_GENERATION": bool(
            getattr(request.app.state.config, "ENABLE_MUSIC_GENERATION", False) or False
        ),
        "MUSIC_API_BASE_URL": str(getattr(request.app.state.config, "MUSIC_API_BASE_URL", "") or ""),
        "MUSIC_API_KEY": str(getattr(request.app.state.config, "MUSIC_API_KEY", "") or ""),
        "MUSIC_API_GENERATE_PATH": str(
            getattr(request.app.state.config, "MUSIC_API_GENERATE_PATH", "/generate") or "/generate"
        ),
        "MUSIC_MODEL": str(getattr(request.app.state.config, "MUSIC_MODEL", "") or ""),
    }


@router.post("/config/update", response_model=MusicConfig)
async def update_music_config(
    request: Request, form_data: MusicConfig, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_MUSIC_GENERATION = bool(form_data.ENABLE_MUSIC_GENERATION)
    request.app.state.config.MUSIC_API_BASE_URL = str(form_data.MUSIC_API_BASE_URL or "").strip()
    request.app.state.config.MUSIC_API_KEY = str(form_data.MUSIC_API_KEY or "").strip()
    request.app.state.config.MUSIC_API_GENERATE_PATH = (
        str(form_data.MUSIC_API_GENERATE_PATH or "/generate").strip() or "/generate"
    )
    request.app.state.config.MUSIC_MODEL = str(form_data.MUSIC_MODEL or "").strip()

    return await get_music_config(request, user=user)


class MusicStatus(BaseModel):
    available: bool
    enabled: bool
    configured: bool
    redis_available: bool
    credits_required: bool
    default_model: str


@router.get("/status", response_model=MusicStatus)
async def music_status(
    request: Request,
    response: Response,
    user=Depends(get_verified_user_or_none),
):
    if user is None:
        _get_or_set_anon_id(request, response)

    enabled = bool(getattr(request.app.state.config, "ENABLE_MUSIC_GENERATION", False) or False)
    base_url = str(getattr(request.app.state.config, "MUSIC_API_BASE_URL", "") or "").strip()
    configured = bool(base_url)

    is_admin = getattr(user, "role", None) == "admin"
    redis_available = request.app.state.redis is not None
    credits_required = not is_admin

    available = bool(enabled and configured and (not credits_required or redis_available))
    return {
        "available": available,
        "enabled": enabled,
        "configured": configured,
        "redis_available": redis_available,
        "credits_required": credits_required,
        "default_model": str(getattr(request.app.state.config, "MUSIC_MODEL", "") or ""),
    }


class MusicGenerateForm(BaseModel):
    prompt: str
    model: str | None = None


class MusicGenerateResponse(BaseModel):
    id: str
    ext: str
    media_type: str
    data_url: str | None = None
    play_url: str
    download_url: str
    charged: bool = False


async def _fetch_bytes_from_url(url: str, *, headers: dict | None = None) -> tuple[bytes, str]:
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.get(url, headers=headers or {}, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
            r.raise_for_status()
            media_type = str(r.headers.get("Content-Type") or "").split(";", 1)[0].strip()
            return await r.read(), media_type or "application/octet-stream"


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    if not data_url.startswith("data:"):
        raise ValueError("Invalid data_url")
    try:
        header, b64 = data_url.split(",", 1)
    except ValueError as e:
        raise ValueError("Invalid data_url") from e

    media_type = header.split(";", 1)[0].replace("data:", "").strip() or "application/octet-stream"
    data = base64.b64decode(b64)
    return data, media_type


async def _provider_generate_music(
    request: Request,
    *,
    prompt: str,
    model: str,
    user,
) -> tuple[bytes, str, str]:
    base_url = str(getattr(request.app.state.config, "MUSIC_API_BASE_URL", "") or "").strip()
    if not base_url:
        raise HTTPException(status_code=400, detail="Music API is not configured")

    generate_path = str(
        getattr(request.app.state.config, "MUSIC_API_GENERATE_PATH", "/generate") or "/generate"
    ).strip() or "/generate"

    url = base_url.rstrip("/") + (generate_path if generate_path.startswith("/") else f"/{generate_path}")

    api_key = str(getattr(request.app.state.config, "MUSIC_API_KEY", "") or "").strip()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["x-api-key"] = api_key

    payload = {"prompt": prompt, "model": model}

    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.post(url, json=payload, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
            if r.status >= 400:
                detail = "Music provider error"
                try:
                    err_json = await r.json(content_type=None)
                    if isinstance(err_json, dict):
                        detail = str(err_json.get("detail") or err_json.get("error") or detail)
                except Exception:
                    try:
                        detail = (await r.text())[:500] or detail
                    except Exception:
                        pass
                raise HTTPException(status_code=502, detail=detail)

            content_type = str(r.headers.get("Content-Type") or "")
            content_type_base = content_type.split(";", 1)[0].strip().lower()

            if content_type_base.startswith("audio/"):
                data = await r.read()
                ext = _guess_ext_for_media_type(content_type_base)
                return data, ext, content_type_base

            raw = await r.read()
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception:
                raise HTTPException(status_code=502, detail="Unexpected music provider response")

            if isinstance(parsed, dict):
                if isinstance(parsed.get("data_url"), str) and parsed["data_url"].startswith("data:"):
                    data, media_type = _decode_data_url(parsed["data_url"])
                    ext = _guess_ext_for_media_type(media_type)
                    return data, ext, media_type

                for key in ("audio_base64", "audio_b64", "b64", "base64", "audio"):
                    val = parsed.get(key)
                    if isinstance(val, str) and val.strip():
                        data = base64.b64decode(val)
                        media_type = (
                            str(parsed.get("media_type") or parsed.get("content_type") or "")
                            .split(";", 1)[0]
                            .strip()
                        )
                        if not media_type:
                            media_type = "audio/mpeg"
                        ext = _guess_ext_for_media_type(media_type)
                        return data, ext, media_type

                for key in ("url", "audio_url", "download_url"):
                    val = parsed.get(key)
                    if isinstance(val, str) and val.strip():
                        data, media_type = await _fetch_bytes_from_url(val.strip(), headers=None)
                        ext = _guess_ext_for_media_type(media_type)
                        return data, ext, media_type

            raise HTTPException(status_code=502, detail="Unsupported music provider response")


@router.post("/generate", response_model=MusicGenerateResponse)
async def generate_music(
    request: Request,
    response: Response,
    form_data: MusicGenerateForm,
    user=Depends(get_verified_user_or_none),
):
    prompt = str(form_data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    if not bool(getattr(request.app.state.config, "ENABLE_MUSIC_GENERATION", False) or False):
        raise HTTPException(status_code=503, detail="Music generation is disabled.")

    model = (
        str(form_data.model).strip()
        if form_data.model is not None and str(form_data.model).strip()
        else str(getattr(request.app.state.config, "MUSIC_MODEL", "") or "").strip()
    )

    is_admin = getattr(user, "role", None) == "admin"
    redis = request.app.state.redis

    subject_id = None
    free_limit = None
    cost = None
    preflight = None

    if not is_admin:
        if redis is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Music generation temporarily unavailable",
            )

        subject_id = user.id if user is not None else f"anon:{_get_or_set_anon_id(request, response)}"
        free_limit = (
            int(getattr(request.app.state.config, "MUSIC_CREDITS_FREE_AUTH", 0) or 0)
            if user is not None
            else int(getattr(request.app.state.config, "MUSIC_CREDITS_FREE_ANON", 0) or 0)
        )
        cost = int(getattr(request.app.state.config, "MUSIC_CREDITS_COST", 0) or 0)
        try:
            preflight = await preflight_generation(
                redis,
                domain="music",
                subject_id=subject_id,
                free_limit=free_limit,
                cost_credits=cost,
                require_auth_after_free=False,
                is_authenticated=user is not None,
            )
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please sign in to continue music generation",
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for music generation",
            )

    audio_bytes, ext, media_type = await _provider_generate_music(
        request, prompt=prompt, model=model, user=user
    )

    audio_id = uuid.uuid4().hex
    file_path, meta_path = _music_cache_paths(audio_id=audio_id, ext=ext)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(audio_bytes)
        async with aiofiles.open(meta_path, "w", encoding="utf-8") as f:
            await f.write(
                json.dumps(
                    {"prompt": prompt, "model": model, "ext": ext, "media_type": media_type},
                    ensure_ascii=False,
                )
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail="Failed to store generated music")

    charged_paid = False
    if not is_admin and redis is not None and subject_id and preflight and free_limit is not None:
        try:
            _status_after, charged_paid = await commit_generation(
                redis,
                domain="music",
                subject_id=subject_id,
                free_limit=free_limit,
                mode=preflight.mode,
                cost_credits=cost or 0,
                now_ts=int(time.time()),
            )
        except Exception:
            log.exception("Failed to commit music credits charge")

    data_url = None
    try:
        if len(audio_bytes) <= 8 * 1024 * 1024:
            data_url = f"data:{media_type};base64,{base64.b64encode(audio_bytes).decode('utf-8')}"
    except Exception:
        data_url = None

    play_url = f"/api/v1/music/{audio_id}"
    download_url = f"/api/v1/music/{audio_id}/download"

    return {
        "id": audio_id,
        "ext": _sanitize_ext(ext),
        "media_type": media_type or _guess_media_type_for_ext(ext),
        "data_url": data_url,
        "play_url": play_url,
        "download_url": download_url,
        "charged": bool(charged_paid),
    }


def _find_cached_music_file(audio_id: str) -> tuple[Path, str, str] | None:
    audio_id = str(audio_id or "").strip()
    if not audio_id:
        return None

    for p in MUSIC_CACHE_DIR.glob(f"{audio_id}.*"):
        if p.name.endswith(".json"):
            continue
        ext = _sanitize_ext(p.suffix)
        media_type = _guess_media_type_for_ext(ext)
        return p, ext, media_type
    return None


@router.get("/{audio_id}")
async def get_music(audio_id: str):
    found = _find_cached_music_file(audio_id=audio_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
    file_path, _ext, media_type = found
    return FileResponse(file_path, media_type=media_type)


@router.get("/{audio_id}/download")
async def download_music(audio_id: str):
    found = _find_cached_music_file(audio_id=audio_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
    file_path, ext, media_type = found
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=f"music-{audio_id}.{ext}",
    )

