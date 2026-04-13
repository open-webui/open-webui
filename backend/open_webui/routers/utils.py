import asyncio
import black
import ipaddress
import logging
import markdown
import socket

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from open_webui.models.chats import ChatTitleMessagesForm
from open_webui.config import DATA_DIR, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from starlette.responses import FileResponse, RedirectResponse


from open_webui.utils.misc import get_gravatar_url
from open_webui.utils.pdf_generator import PDFGenerator
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.code_interpreter import execute_code_jupyter

log = logging.getLogger(__name__)

router = APIRouter()

_FAVICON_CACHE: dict[str, bytes] = {}
_FAVICON_CACHE_MAX = 1024
_FAVICON_MAX_BYTES = 200 * 1024  # 200 KB — skip oversized responses
_FAVICON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}
_FAVICON_TIMEOUT = aiohttp.ClientTimeout(total=5)


async def _is_safe_host(hostname: str) -> bool:
    """Return True only if the hostname resolves to a public IP (not private/loopback/link-local)."""
    try:
        addrs = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
        for addr in addrs:
            ip = ipaddress.ip_address(addr[4][0])
            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False
        return True
    except Exception:
        return False


def _extract_domain(url: str) -> str | None:
    try:
        parsed = urlparse(url if url.startswith('http') else f'https://{url}')
        return parsed.netloc or parsed.path.split('/')[0] or None
    except Exception:
        return None


def _resolve_href(href: str, base: str) -> str:
    """Resolve a potentially relative favicon href to an absolute URL."""
    if href.startswith('data:'):
        return ''
    return urljoin(base, href)


def _pick_best_icon(links: list) -> str:
    """
    Pick the best favicon from a list of <link> tags.
    Priority: SVG > PNG/WebP > ICO, then larger declared size wins.
    """
    FORMAT_RANK = {'svg': 3, 'png': 2, 'webp': 2, 'gif': 1, 'ico': 0}

    def score(tag):
        href = tag.get('href', '')
        mime = (tag.get('type') or '').lower()
        ext = href.rsplit('.', 1)[-1].lower().split('?')[0] if '.' in href else ''
        fmt = ext or mime.split('/')[-1]
        fmt_score = FORMAT_RANK.get(fmt, 1)

        sizes = tag.get('sizes', '')
        try:
            w = int(sizes.split('x')[0]) if sizes and sizes != 'any' else 0
        except (ValueError, IndexError):
            w = 0
        return (fmt_score, w)

    links = [t for t in links if t.get('href')]
    if not links:
        return ''
    return max(links, key=score).get('href', '')


async def _fetch_favicon_bytes(domain: str) -> bytes | None:
    if not await _is_safe_host(domain):
        log.debug('favicon: rejected non-public host %s', domain)
        return None

    base = f'https://{domain}'

    async with aiohttp.ClientSession(headers=_FAVICON_HEADERS, timeout=_FAVICON_TIMEOUT) as session:
        # Step 1: try /favicon.ico directly
        try:
            async with session.get(f'{base}/favicon.ico', allow_redirects=True) as r:
                if r.status == 200 and 'image' in r.content_type:
                    if r.content_length and r.content_length > _FAVICON_MAX_BYTES:
                        log.debug('favicon step 1: response too large for %s', domain)
                    else:
                        data = await r.read()
                        if len(data) <= _FAVICON_MAX_BYTES:
                            return data
        except Exception as e:
            log.debug('favicon step 1 failed for %s: %s', domain, e)

        # Step 2: parse HTML <head> for <link rel="icon"> tags
        try:
            async with session.get(base, allow_redirects=True) as r:
                if r.status == 200:
                    html = await r.text(errors='replace')
                    soup = BeautifulSoup(html, 'html.parser')
                    head = soup.head or soup

                    rel_values = {'icon', 'shortcut icon', 'apple-touch-icon', 'apple-touch-icon-precomposed'}
                    links = [
                        tag for tag in head.find_all('link', rel=True)
                        if set(tag['rel']) & rel_values
                    ]

                    href = _pick_best_icon(links)
                    if href:
                        icon_url = _resolve_href(href, str(r.url))
                        if icon_url:
                            icon_host = urlparse(icon_url).netloc.split(':')[0]
                            if icon_host and not await _is_safe_host(icon_host):
                                log.debug('favicon: rejected non-public icon host %s', icon_host)
                            else:
                                async with session.get(icon_url, allow_redirects=True) as ir:
                                    if ir.status == 200 and 'image' in ir.content_type:
                                        if ir.content_length and ir.content_length > _FAVICON_MAX_BYTES:
                                            log.debug('favicon step 2: icon response too large for %s', icon_host)
                                        else:
                                            data = await ir.read()
                                            if len(data) <= _FAVICON_MAX_BYTES:
                                                return data
        except Exception as e:
            log.debug('favicon step 2 failed for %s: %s', domain, e)

    return None


@router.get('/favicon')
async def get_favicon(url: str, user=Depends(get_verified_user)):
    """
    Proxy a source website's favicon server-side.
    Results are cached in memory for the lifetime of the process.
    Falls back to Open WebUI's own favicon if none can be found.
    """
    domain = _extract_domain(url)
    if not domain:
        return RedirectResponse('/favicon.png')

    data = _FAVICON_CACHE.get(domain)
    if data is None:
        data = await _fetch_favicon_bytes(domain)
        if data and len(_FAVICON_CACHE) < _FAVICON_CACHE_MAX:
            _FAVICON_CACHE[domain] = data

    if not data:
        return RedirectResponse('/favicon.png')

    # Detect content type from magic bytes
    if data[:4] == b'\x89PNG':
        ct = 'image/png'
    elif data[:2] == b'\xff\xd8':
        ct = 'image/jpeg'
    elif data[:3] == b'GIF':
        ct = 'image/gif'
    elif data[:14].startswith(b'<svg') or b'<svg' in data[:256]:
        ct = 'image/svg+xml'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        ct = 'image/webp'
    elif data[:4] == b'\x00\x00\x01\x00':
        ct = 'image/x-icon'
    else:
        ct = 'image/x-icon'

    return Response(
        content=data,
        media_type=ct,
        headers={'Cache-Control': 'public, max-age=86400'},
    )


@router.get('/gravatar')
async def get_gravatar(email: str, user=Depends(get_verified_user)):
    return get_gravatar_url(email)


class CodeForm(BaseModel):
    code: str


@router.post('/code/format')
async def format_code(form_data: CodeForm, user=Depends(get_admin_user)):
    try:
        formatted_code = black.format_str(form_data.code, mode=black.Mode())
        return {'code': formatted_code}
    except black.NothingChanged:
        return {'code': form_data.code}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/code/execute')
async def execute_code(request: Request, form_data: CodeForm, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_CODE_EXECUTION:
        raise HTTPException(
            status_code=403,
            detail=ERROR_MESSAGES.FEATURE_DISABLED('Code execution'),
        )

    if request.app.state.config.CODE_EXECUTION_ENGINE == 'jupyter':
        output = await execute_code_jupyter(
            request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
            form_data.code,
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == 'token'
                else None
            ),
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == 'password'
                else None
            ),
            request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        )

        return output
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.DEFAULT('Code execution engine not supported'),
        )


class MarkdownForm(BaseModel):
    md: str


@router.post('/markdown')
async def get_html_from_markdown(form_data: MarkdownForm, user=Depends(get_verified_user)):
    return {'html': markdown.markdown(form_data.md)}


class ChatForm(BaseModel):
    title: str
    messages: list[dict]


@router.post('/pdf')
async def download_chat_as_pdf(form_data: ChatTitleMessagesForm, user=Depends(get_verified_user)):
    try:
        pdf_bytes = PDFGenerator(form_data).generate_chat_pdf()

        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': 'attachment;filename=chat.pdf'},
        )
    except Exception as e:
        log.exception(f'Error generating PDF: {e}')
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/db/download')
async def download_db(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    from open_webui.internal.db import engine

    if engine.name != 'sqlite':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_NOT_SQLITE,
        )
    return FileResponse(
        engine.url.database,
        media_type='application/octet-stream',
        filename='webui.db',
    )
