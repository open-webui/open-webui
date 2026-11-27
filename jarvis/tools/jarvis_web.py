"""
title: JARVIS Web
author: JoshTXWC
description: Quick web search (DuckDuckGo, no API key) and page fetch-to-text. Ported from JoshTXWC/JARVIS web_tools.
version: 1.0.0
license: MIT
"""

import html
import ipaddress
import re
import socket
from urllib.parse import parse_qs, unquote, urlparse

import aiohttp
from pydantic import BaseModel, Field

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 JARVIS"


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def is_public_url(url: str) -> bool:
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    try:
        for info in socket.getaddrinfo(u.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except Exception:
        return False
    return True


class Tools:
    class Valves(BaseModel):
        MAX_CHARS: int = Field(default=12000, description="Max characters returned by web_fetch.")
        ALLOW_LOCAL_URLS: bool = Field(default=False, description="Allow web_fetch on localhost / LAN addresses.")

    def __init__(self):
        self.valves = self.Valves()

    async def web_search(self, query: str, max_results: int = 8) -> str:
        """
        Search the web and return titles, links and snippets.
        :param query: Search query.
        :param max_results: Number of results.
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20), headers={"User-Agent": UA}) as s:
                async with s.post("https://html.duckduckgo.com/html/", data={"q": query}) as r:
                    page = await r.text()
        except Exception as e:
            return f"Search failed: {e}"
        results = []
        for m in re.finditer(r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)', page):
            href, title, rest = m.groups()
            if "uddg=" in href:
                href = unquote(parse_qs(urlparse(href).query).get("uddg", [href])[0])
            sn = re.search(r'(?is)class="result__snippet"[^>]*>(.*?)</a>', rest)
            results.append(f"{len(results)+1}. {html_to_text(title)}\n   {href}\n   {html_to_text(sn.group(1)) if sn else ''}")
            if len(results) >= max_results:
                break
        return "\n".join(results) or "No results."

    async def web_fetch(self, url: str) -> str:
        """
        Download a web page and return its readable text.
        :param url: http(s) URL.
        """
        if not self.valves.ALLOW_LOCAL_URLS and not is_public_url(url):
            return "Refused: only public http(s) URLs (local/LAN addresses are blocked by default)."
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), headers={"User-Agent": UA}) as s:
                async with s.get(url, allow_redirects=True) as r:
                    ctype = r.headers.get("content-type", "")
                    raw = await r.text(errors="replace")
        except Exception as e:
            return f"Fetch failed: {e}"
        text = html_to_text(raw) if "html" in ctype or "<html" in raw[:500].lower() else raw
        if len(text) > self.valves.MAX_CHARS:
            text = text[: self.valves.MAX_CHARS] + "\n... [truncated]"
        return text
