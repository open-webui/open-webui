import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from markdown_translator import translate_html_file_to_markdown

visited_urls = set()
NUM_LIMIT = 10

def crawl(url, output_folder="output_hmtl"):
    # 갯수 제한(테스트용): NUM_LIMIT 이하로 호출되도록 설정
    if visited_urls.__len__() > NUM_LIMIT:
        return
    
    
    if url in visited_urls:
        return  # 이미 방문한 URL은 스킵
    
    print(f"Visiting: {url}")
    visited_urls.add(url)
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 불필요한 태그 제거
    for tag in soup(['img', 'script', 'style', 'iframe', 'noscript', 'meta', 'link', 'svg']):
        tag.decompose()
    
    # 상대경로 보정
    for tag in soup.find_all(['a']):
        if tag.has_attr('href') and not tag['href'].startswith(('http', 'https')):
            tag['href'] = urljoin("https://registry.hkust.edu.hk/", tag['href'])
        if tag.has_attr('src') and not tag['src'].startswith(('http', 'https')):
            tag['src'] = urljoin("https://registry.hkust.edu.hk/", tag['src'])
    
    # "resource-library" 포함된 링크 찾기
    for a_tag in soup.find_all("a", href=True):
        if "resource-library" in a_tag["href"]:
            next_url = urljoin(url, a_tag["href"])
            crawl(next_url, output_folder)
    
    # class가 "resource__left-column"인 div 찾기
    resource_div = soup.find("div", class_="resource__left-column")
    if resource_div:
        html_content = str(resource_div)
        title_div = soup.find("h1", class_="resource__title")
        title_text = title_div.get_text(strip=True) if title_div else "untitled"
        title_text = "_".join(title_text.split())[:50]  # 공백을 '_'로 변환하고 길이 제한
        timestamp = time.strftime("%Y%m%d%H%M%S")
        input_file = f"{title_text}_{timestamp}.html"
        input_path = os.path.join(output_folder, input_file)
        os.makedirs(output_folder, exist_ok=True)
        
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 변환 함수 호출
        translate_html_file_to_markdown(input_file, input_path)

if __name__ == "__main__":
    start_url = "https://registry.hkust.edu.hk/resource-library"
    crawl(start_url)

    with open("visited_urls.txt", "w", encoding="utf-8") as f:
        for url in visited_urls:
            f.write(f"{url}\n")
    