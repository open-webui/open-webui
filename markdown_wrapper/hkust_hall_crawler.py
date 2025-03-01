import os
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from markdown_translator import translate_file_to_markdown
from collections import deque

# 세션 설정 (자동 재시도 기능 포함)
session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

# User-Agent 설정
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

visited_urls = set()
NUM_LIMIT = 1000  # 테스트용 크롤링 제한

TARGET_URL = [
    "https://shrl.hkust.edu.hk/about/contact-us",
    "https://shrl.hkust.edu.hk/residential-halls/overview",
    "https://shrl.hkust.edu.hk/admission-policy/ug",
    "https://shrl.hkust.edu.hk/apply-for-housing/ug",
    "https://shrl.hkust.edu.hk/off-campus-housing/hkac",
    "https://shrl.hkust.edu.hk/faq/ug-applicant-related"
]

def crawl_bfs(start_urls, output_folder="output_hall_html"):
    queue = deque(start_urls)
    
    while queue and len(visited_urls) < NUM_LIMIT:
        url = queue.popleft()
        if url in visited_urls:
            continue

        print(f"Visiting: {url}")
        visited_urls.add(url)

        # 요청 속도 제한 (1~3초 랜덤 딜레이)
        time.sleep(random.uniform(1, 3))

        try:
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "iframe", "noscript", "meta", "link", "svg"]):
            tag.decompose()

        # 현재 접속 중인 URL의 base URL 추출
        base_url = urlparse(url)._replace(path="", params="", query="", fragment="").geturl()
        relative_path = url.replace(base_url, "").strip("/")
        title_text = relative_path.replace("/", "_") if relative_path else "index"

        # 상대경로 보정
        for tag in soup.find_all(["a", "img"]):
            if tag.has_attr("href") and not tag["href"].startswith(("http", "https", "mailto:")):
                if not tag["href"].startswith("javascript:"):
                    tag["href"] = urljoin(base_url, tag["href"])
            if tag.has_attr("src") and not tag["src"].startswith(("http", "https")):
                if not tag["src"].startswith("javascript:"):
                    tag["src"] = urljoin(base_url, tag["src"])

        # Base64 인코딩된 이미지 제거
        for img_tag in soup.find_all("img"):
            if img_tag.has_attr("src") and img_tag["src"].startswith("data:image"):
                img_tag.decompose()

        # html에 포함된 링크 찾기
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href.startswith(("javascript:", "mailto:")) and "hkust-gz.edu.cn" not in href:
                full_url = urljoin(url, href)
                if full_url not in visited_urls:
                    queue.append(full_url)

        # class가 "mtpc-2col-section-wrapper"인 div 찾기
        resource_div = soup.find("div", class_="mtpc-2col-section-wrapper")
        if resource_div:
            html_content = str(resource_div).replace("\u2028", "").replace("\u2029", "")
            timestamp = time.strftime("%Y%m%d%H%M%S")
            input_file = f"{title_text}_{timestamp}.html"
            input_path = os.path.join(output_folder, input_file)
            os.makedirs(output_folder, exist_ok=True)
            
            with open(input_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            translate_file_to_markdown(input_file, input_path, "output_hall_markdown")

if __name__ == "__main__":
    output_folder = "output_hall_html"
    crawl_bfs(TARGET_URL, output_folder)
    
    with open(os.path.join(output_folder, "visited_urls.txt"), "w", encoding="utf-8") as f:
        for url in visited_urls:
            f.write(f"{url}\n")
