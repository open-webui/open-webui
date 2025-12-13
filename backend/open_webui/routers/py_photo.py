import base64
import json
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont

from open_webui.config import CACHE_DIR
from open_webui.env import FONTS_DIR, SRC_LOG_LEVELS
from open_webui.utils.auth import get_verified_user_or_none

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ROUTERS", logging.INFO))

PY_PHOTO_CACHE_DIR = CACHE_DIR / "py_photo" / "generations"
PY_PHOTO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


class PyPhotoGenerateForm(BaseModel):
    input: str
    size: int | None = 1024


class PyPhotoGenerateResponse(BaseModel):
    id: str
    media_type: str = "image/png"
    data_url: str
    view_url: str
    download_url: str


def _py_photo_paths(*, image_id: str) -> tuple[Path, Path]:
    file_path = PY_PHOTO_CACHE_DIR / f"{image_id}.png"
    meta_path = PY_PHOTO_CACHE_DIR / f"{image_id}.json"
    return file_path, meta_path


def _resolve_font_path() -> Path:
    for candidate in (
        FONTS_DIR / "NotoSans-Regular.ttf",
        FONTS_DIR / "NotoSans-Variable.ttf",
    ):
        try:
            if candidate.is_file():
                return candidate
        except Exception:
            continue
    raise RuntimeError("No bundled font available")


_COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "gray": (200, 200, 200),
    "red": (239, 68, 68),
    "green": (34, 197, 94),
    "blue": (59, 130, 246),
    "yellow": (234, 179, 8),
    "orange": (249, 115, 22),
    "purple": (168, 85, 247),
    "cyan": (6, 182, 212),
}


@dataclass(frozen=True)
class _Token:
    text: str
    color: tuple[int, int, int]


def _parse_color_markup(text: str) -> list[tuple[str, tuple[int, int, int]]]:
    default = _COLOR_MAP["white"]
    spans: list[tuple[str, tuple[int, int, int]]] = []
    color_stack: list[tuple[int, int, int]] = [default]

    i = 0
    while i < len(text):
        if text[i] != "[":
            j = text.find("[", i)
            if j == -1:
                j = len(text)
            spans.append((text[i:j], color_stack[-1]))
            i = j
            continue

        end = text.find("]", i + 1)
        if end == -1:
            spans.append((text[i:], color_stack[-1]))
            break

        tag = text[i + 1 : end].strip()
        if not tag:
            spans.append(("[", color_stack[-1]))
            i += 1
            continue

        if tag.startswith("/"):
            tag_name = tag[1:].strip().lower()
            if tag_name in _COLOR_MAP and len(color_stack) > 1:
                color_stack.pop()
            else:
                spans.append((text[i : end + 1], color_stack[-1]))
            i = end + 1
            continue

        tag_name = tag.lower()
        if tag_name in _COLOR_MAP:
            color_stack.append(_COLOR_MAP[tag_name])
            i = end + 1
            continue

        spans.append((text[i : end + 1], color_stack[-1]))
        i = end + 1

    merged: list[tuple[str, tuple[int, int, int]]] = []
    for part, color in spans:
        if not part:
            continue
        if merged and merged[-1][1] == color:
            merged[-1] = (merged[-1][0] + part, color)
        else:
            merged.append((part, color))
    return merged


_TOKEN_RE = re.compile(r"\n|[ \t\r\f\v]+|[^\s]+", re.UNICODE)


def _tokenize(spans: list[tuple[str, tuple[int, int, int]]]) -> list[_Token]:
    tokens: list[_Token] = []
    for text, color in spans:
        for piece in _TOKEN_RE.findall(text):
            tokens.append(_Token(text=piece, color=color))
    return tokens


def _wrap_tokens(
    draw: ImageDraw.ImageDraw,
    *,
    tokens: list[_Token],
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> tuple[list[list[_Token]], list[float]]:
    lines: list[list[_Token]] = []
    line_widths: list[float] = []

    current: list[_Token] = []
    current_width = 0.0

    def flush():
        nonlocal current, current_width
        if current:
            lines.append(current)
            line_widths.append(current_width)
        current = []
        current_width = 0.0

    for token in tokens:
        if token.text == "\n":
            flush()
            continue

        if not current and token.text.isspace():
            continue

        token_width = float(draw.textlength(token.text, font=font))

        if token_width > max_width:
            for ch in token.text:
                ch_width = float(draw.textlength(ch, font=font))
                if current and current_width + ch_width > max_width:
                    flush()
                if ch.isspace() and not current:
                    continue
                current.append(_Token(text=ch, color=token.color))
                current_width += ch_width
            continue

        if current and current_width + token_width > max_width:
            flush()
            if token.text.isspace():
                continue

        current.append(token)
        current_width += token_width

    flush()
    return lines, line_widths


def _max_lines_for_height(*, max_height: int, line_height: int, spacing: int) -> int:
    if line_height <= 0:
        return 1
    return max(1, (max_height + spacing) // (line_height + spacing))


def _truncate_lines_to_fit(
    draw: ImageDraw.ImageDraw,
    *,
    lines: list[list[_Token]],
    line_widths: list[float],
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> tuple[list[list[_Token]], list[float]]:
    if len(lines) <= max_lines:
        return lines, line_widths

    clipped = lines[:max_lines]
    clipped_widths = line_widths[:max_lines]

    if not clipped:
        return [], []

    ellipsis = "…"
    ellipsis_width = float(draw.textlength(ellipsis, font=font))

    last = clipped[-1]
    while last and clipped_widths[-1] + ellipsis_width > max_width:
        removed = last.pop()
        clipped_widths[-1] -= float(draw.textlength(removed.text, font=font))

    if not last:
        last.append(_Token(text=ellipsis, color=_COLOR_MAP["white"]))
        clipped_widths[-1] = ellipsis_width
        return clipped, clipped_widths

    last.append(_Token(text=ellipsis, color=_COLOR_MAP["white"]))
    clipped_widths[-1] += ellipsis_width
    return clipped, clipped_widths


def _layout_text(
    *,
    text: str,
    size: int,
    padding: int,
    font_path: Path,
) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    spans = _parse_color_markup(text)
    tokens = _tokenize(spans)

    max_width = max(1, size - 2 * padding)
    max_height = max(1, size - 2 * padding)

    def fits(font_size: int) -> tuple[bool, list[list[_Token]], list[float], int, int]:
        font = ImageFont.truetype(str(font_path), font_size)
        lines, widths = _wrap_tokens(draw, tokens=tokens, font=font, max_width=max_width)
        ascent, descent = font.getmetrics()
        line_height = int(ascent + descent)
        spacing = max(1, int(line_height * 0.2))
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
        return total_height <= max_height, lines, widths, line_height, spacing

    lo, hi = 8, 120
    best = 8
    best_layout = None

    while lo <= hi:
        mid = (lo + hi) // 2
        ok, lines, widths, line_height, spacing = fits(mid)
        if ok:
            best = mid
            best_layout = (lines, widths, line_height, spacing)
            lo = mid + 1
        else:
            hi = mid - 1

    font = ImageFont.truetype(str(font_path), best)
    if best_layout is None:
        lines, widths = _wrap_tokens(draw, tokens=tokens, font=font, max_width=max_width)
        ascent, descent = font.getmetrics()
        line_height = int(ascent + descent)
        spacing = max(1, int(line_height * 0.2))
    else:
        lines, widths, line_height, spacing = best_layout

    total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
    max_lines = _max_lines_for_height(max_height=max_height, line_height=line_height, spacing=spacing)

    lines, widths = _truncate_lines_to_fit(
        draw,
        lines=lines,
        line_widths=widths,
        font=font,
        max_width=max_width,
        max_lines=max_lines,
    )
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing

    start_y = padding + max(0, (max_height - total_height) // 2)

    y = start_y
    for line, line_width in zip(lines, widths):
        x = padding + max(0, int((max_width - line_width) // 2))
        for token in line:
            if token.text:
                draw.text((x, y), token.text, font=font, fill=token.color)
                x += float(draw.textlength(token.text, font=font))
        y += line_height + spacing

    meta = {
        "size": size,
        "padding": padding,
        "font_size": best,
        "font": font_path.name,
    }
    return img, meta


@router.post("/generate", response_model=PyPhotoGenerateResponse)
async def generate_py_photo(
    request: Request,
    form_data: PyPhotoGenerateForm,
    user=Depends(get_verified_user_or_none),
):
    text = str(form_data.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text is required")

    if len(text) > 10_000:
        raise HTTPException(status_code=400, detail="Input text is too long")

    try:
        size = int(form_data.size or 1024)
    except Exception:
        size = 1024
    size = max(256, min(2048, size))
    padding = max(24, size // 12)

    try:
        font_path = _resolve_font_path()
        img, meta = _layout_text(text=text, size=size, padding=padding, font_path=font_path)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail="Failed to render image")

    image_id = uuid.uuid4().hex
    file_path, meta_path = _py_photo_paths(image_id=image_id)

    try:
        from io import BytesIO

        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(png_bytes)
        async with aiofiles.open(meta_path, "w", encoding="utf-8") as f:
            await f.write(
                json.dumps(
                    {"meta": meta},
                    ensure_ascii=False,
                )
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail="Failed to store image")

    data_url = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}"
    view_url = f"/api/v1/py_photo/{image_id}"
    download_url = f"/api/v1/py_photo/{image_id}/download"

    return {
        "id": image_id,
        "data_url": data_url,
        "view_url": view_url,
        "download_url": download_url,
    }


def _find_cached_png(image_id: str) -> Path | None:
    image_id = str(image_id or "").strip()
    if not image_id:
        return None
    file_path, _meta_path = _py_photo_paths(image_id=image_id)
    return file_path if file_path.is_file() else None


@router.get("/{image_id}")
async def get_py_photo(image_id: str):
    file_path = _find_cached_png(image_id=image_id)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(file_path, media_type="image/png")


@router.get("/{image_id}/download")
async def download_py_photo(image_id: str):
    file_path = _find_cached_png(image_id=image_id)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(
        file_path,
        media_type="image/png",
        filename=f"py-photo-{image_id}.png",
    )

