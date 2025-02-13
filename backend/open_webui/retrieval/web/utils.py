import asyncio
import socket
import urllib.parse
import validators
from typing import Union, Sequence, Iterator, List, Optional
import aiodns
import aiohttp
from async_lru import alru_cache
from readability import Document as ReadabilityDocument
import html2text
from lxml_html_clean import Cleaner
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document as LangchainDocument  # 重命名解决冲突
from open_webui.constants import ERROR_MESSAGES
from open_webui.config import ENABLE_RAG_LOCAL_WEB_FETCH
from open_webui.env import SRC_LOG_LEVELS
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def validate_url(url: Union[str, Sequence[str]]):
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)
        if not ENABLE_RAG_LOCAL_WEB_FETCH:
            # Local web fetch is disabled, filter out any URLs that resolve to private IP addresses
            parsed_url = urllib.parse.urlparse(url)
            # Get IPv4 and IPv6 addresses
            ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
            # Check if any of the resolved addresses are private
            # This is technically still vulnerable to DNS rebinding attacks, as we don't control WebBaseLoader
            for ip in ipv4_addresses:
                if validators.ipv4(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
            for ip in ipv6_addresses:
                if validators.ipv6(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
        return True
    elif isinstance(url, Sequence):
        return all(validate_url(u) for u in url)
    else:
        return False


def safe_validate_urls(url: Sequence[str]) -> Sequence[str]:
    valid_urls = []
    for u in url:
        try:
            if validate_url(u):
                valid_urls.append(u)
        except ValueError:
            continue
    return valid_urls


def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with enhanced error handling for URLs."""

    def lazy_load(self) -> Iterator[LangchainDocument]:
        """Lazy load text from the url(s) in web_path with error handling."""
        for path in self.web_paths:
            try:
                soup = self._scrape(path, bs_kwargs=self.bs_kwargs)
                text = soup.get_text(**self.bs_get_text_kwargs)

                # Build metadata
                metadata = {"source": path}
                if title := soup.find("title"):
                    metadata["title"] = title.get_text()
                if description := soup.find("meta", attrs={"name": "description"}):
                    metadata["description"] = description.get(
                        "content", "No description found."
                    )
                if html := soup.find("html"):
                    metadata["language"] = html.get("lang", "No language found.")

                yield LangchainDocument(page_content=text, metadata=metadata)
            except Exception as e:
                # Log the error and continue with the next URL
                log.error(f"Error loading {path}: {e}")


def get_web_loader(
        urls: Union[str, Sequence[str]],
        requests_per_second: int = 2,
):
    return OptimizedWebLoader(
        urls=urls,
        timeout=requests_per_second,
        concurrency=10,
        max_content=100000
    )


# ================== 异步DNS解析 ==================
@alru_cache(maxsize=500, ttl=300)  # 使用异步缓存
async def async_resolve_hostname(hostname: str) -> tuple[List[str], List[str]]:
    """异步DNS解析器（带缓存）"""
    try:
        resolver = aiodns.DNSResolver()
        ipv4, ipv6 = await asyncio.gather(
            resolver.query(hostname, 'A'),
            resolver.query(hostname, 'AAAA')
        )
        return (
            [record.host for record in ipv4],
            [record.host for record in ipv6]
        )
    except Exception as e:
        log.warning(f"DNS解析失败 {hostname}: {str(e)}")
        return [], []


# ================== URL验证模块 ==================
async def async_validate_url(url: str) -> bool:
    """异步URL验证器"""
    try:
        # 基础验证
        if not validators.url(url):
            return False

        # 本地获取保护
        if not ENABLE_RAG_LOCAL_WEB_FETCH:
            parsed = urllib.parse.urlparse(url)
            ipv4_list, ipv6_list = await async_resolve_hostname(parsed.hostname)

            # 检查IP地址
            for ip in ipv4_list + ipv6_list:
                if (validators.ipv4(ip, private=True) or
                        validators.ipv6(ip, private=True)):
                    log.warning(f"拒绝私有IP地址: {ip}")
                    return False

        return True
    except Exception as e:
        log.error(f"URL验证异常: {str(e)}")
        return False


# ================== 高性能异步加载器 ==================
class OptimizedWebLoader(WebBaseLoader):
    """优化后的异步网页加载器"""

    def __init__(self, urls: Union[str, List[str]], timeout: int = 5, max_content: int = 100000,
                 concurrency: int = 10):
        super().__init__()
        self.urls = [urls] if isinstance(urls, str) else urls
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_content = max_content
        self.concurrency = concurrency

        self.cleaner = Cleaner(
            scripts=True, javascript=True, comments=True,
            style=True, links=True, meta=True,
            safe_attrs_only=True,
            safe_attrs=frozenset(['src', 'alt', 'href', 'title']),
            remove_tags=['iframe', 'object', 'embed']
        )

    async def _fetch_page(self, url: str, session: aiohttp.ClientSession) -> Optional[LangchainDocument]:
        try:
            async with session.get(url) as response:
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    log.warning(f"跳过非HTML内容: {url} ({content_type})")
                    return None

                # 内容长度预检
                if (content_length := int(response.headers.get('Content-Length', 0))) > self.max_content * 2:
                    log.warning(f"内容过大跳过: {url} ({content_length}字节)")
                    return None

                # 流式处理内容
                current_length = 0
                html = []
                async for chunk in response.content.iter_chunked(4096):
                    decoded_chunk = chunk.decode(errors='ignore')
                    current_length += len(decoded_chunk)
                    html.append(decoded_chunk)
                    if current_length >= self.max_content:
                        break

                full_html = "".join(html)[:self.max_content]
                # 使用readability提取内容
                read_doc = ReadabilityDocument(full_html)

                h = html2text.HTML2Text()
                h.ignore_links = True
                read_doc_content = read_doc.title() + '\n\n' + h.handle(read_doc.summary())
                return LangchainDocument(
                    page_content=f"# {read_doc_content}",
                    metadata={
                        "source": url,
                        "title": read_doc.title(),
                        "description": read_doc.title(),
                        "language": "zh-CN"  # 可添加语言检测逻辑
                    }
                )
        except Exception as e:
            log.error(f"页面加载失败 {url}: {str(e)}")
            return None

    async def aload(self) -> List[LangchainDocument]:
        """异步加载入口"""
        # 并行验证URL
        validation_results = await asyncio.gather(
            *(async_validate_url(url) for url in self.urls)
        )
        valid_urls = [url for url, valid in zip(self.urls, validation_results) if valid]

        # 并发获取页面
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        async with aiohttp.ClientSession(
                timeout=self.timeout,
                connector=connector,
                trust_env=True
        ) as session:
            tasks = [self._fetch_page(url, session) for url in valid_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return [doc for doc in results if isinstance(doc, LangchainDocument)]

#
# if __name__ == "__main__":
#     async def main():
#         loader = get_web_loader(
#             urls=[
#                 "https://www.bing.com/search?q=%E4%B8%8A%E6%B5%B7%E9%92%A2%E8%81%942024%E5%B9%B4%E4%B8%9A%E7%BB%A9%E6%8A%A5%E5%91%8A",
#                 "https://yuanchuang.10jqka.com.cn/20241023/c662721907.shtml",
#                 "https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?stockid=300226&id=10418230",
#                 "https://about.mysteel.com/ir.html",
#                 "https://static.cninfo.com.cn/finalpage/2024-10-24/1221489738.PDF",
#                 "http://static.cninfo.com.cn/finalpage/2024-10-24/1221489743.PDF",
#                 "http://money.finance.sina.com.cn/corp/go.php/vCB_Bulletin/stockid/300226/page_type/ndbg.phtml"
#             ]
#         )
#         print("测试流程开始")
#
#         docs = await loader.aload()
#         for doc in docs:
#             print(f"Loaded: {doc.metadata['source']}")
#             print(f"Title: {doc.metadata['title']}")
#             print(f"Content length: {len(doc.page_content)}")
#             print("-" * 50)
#
#         print("测试流程结束")
#
#
#     asyncio.run(main())
