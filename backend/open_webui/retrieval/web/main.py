import validators

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel

from urllib.parse import urlparse
import validators


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results

    allowed_extensions = [".html", ".shtml"]
    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "")
        # 检查URL的有效性
        if not validators.url(url):
            continue
        # 提取域名
        domain = urlparse(url).netloc
        # 校验域名是否在过滤列表内
        if any(domain.endswith(filtered_domain) for filtered_domain in filter_list):
            # 校验文件后缀
            lower_url = url.lower()
            if any(lower_url.endswith(ext) for ext in allowed_extensions):
                filtered_results.append(result)
            elif '.' not in lower_url.split('/')[-1]:
                filtered_results.append(result)

    return filtered_results



class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
