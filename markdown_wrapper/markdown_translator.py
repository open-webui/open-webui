import os
import time
import fitz  # pymupdf4llm
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key="1777ac2662f649a7bbc0c905d85eb7bd",
    api_version="2025-02-01-preview",
    azure_endpoint="https://hkust.azure-api.net"
)

SYSTEM_PROMPT_HTML = '''
You are an AI that performs the task of understanding advanced HTML content and converting it into Markdown format. Your job is to read all the information from the provided HTML code accurately, without missing any details, and generate a Markdown document while retaining the original language. The result should be a clear and structured document, categorizing information like titles, links, dates, descriptions, lists and images.

Example Input:
```html
<!-- Provided HTML code -->
```

Example Output:
```markdown
# Title

## Categories

- Category 1
- Category 2

## Link

[Link Text](url)

## Image

![Alt Text](image-url "Image Title")

## Access

**Date:** Date  
**Access Level:** Level  

## Guide Resource

Description text...

## Additional Sections
```

Please adhere to the following guidelines:

1. Accurately translate the original content.
2. Maintain the structure of the Markdown document.
3. Include all information from the HTML comprehensively.
4. Consider readability and use appropriate headings and subheadings.
5. Do not include any additional commentary, information, or instructions in your response. Provide only the generated Markdown content.
'''

SYSTEM_PROMPT_PDF = '''
You are an AI that specializes in reading and converting PDF documents into structured Markdown format. Your job is to accurately extract text, maintain the original structure, and format the content properly in Markdown.

Please adhere to the following guidelines:

1. Extract and convert the full text from the PDF accurately.
2. Retain the original document's structure using appropriate Markdown headings and lists.
3. Format tables, lists, and key sections correctly.
4. Ensure readability and logical content organization.
5. Do not include any additional commentary or instructions in your response. Provide only the structured Markdown output.
6. Make sure to include all objective facts and exclude subjective information such as interviews as much as possible. However, make sure to include objective facts included in the interview
'''


# 파일의 확장자를 읽고, HTML-> Markdown, PDF-> Markdown 변환.
# 확장자 별로 다른 프롬프트를 호출
# TODO: 프롬프트를 따로 저장해두는 디렉토리가 있으면 좋을듯
def load_file_content(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext in (".html", ".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return [f.read()], SYSTEM_PROMPT_HTML
    elif ext == ".pdf":
        return process_pdf(file_path), SYSTEM_PROMPT_PDF
    return None, None

# fitz.open(pdf)으로 pdf 파일을 열면, pdf에 있는 텍스트를 organized 되지 않은 형태로 반환함(pdf의 형식이 깨진 상태)
# 해당 상태의 text를 chunks로 분할하여 chunks 리스트로 반환한뒤, 하나의 chunk를 markdown 형식으로 변환함.
# text를 chunks로 분할하여 처리하는 이유는, pdf의 내용이 많을 시에는 max_completion_token을 초과하여 일부 내용이 누락 될 수 있기 때문임.
def process_pdf(file_path: str):
    """PDF를 페이지 단위로 분할하고 청크 생성. PDF의 길이가 길어지면 max_completion_token을 초과하여 일부 내용이 누락되는 현상이 있음"""
    doc = fitz.open(file_path)
    paragraphs = [paragraph.get_text("text") for paragraph in doc]

    # 페이지 내용 기반 동적 청크 분할
    chunks = []
    current_chunk = []
    current_length = 0
    
    for idx, paragraph in enumerate(paragraphs):
        paragraph_length = len(paragraph.split())
        if current_length + paragraph_length > 5000:  # 단어 수 기준 5000단어 + 안전마진
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [paragraph]
            current_length = paragraph_length
        else:
            current_chunk.append(paragraph)
            current_length += paragraph_length
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def translate_markdown_from_text(text: str, system_prompt: str, is_first_chunk: bool = False) -> str:
    if not text:
        return ""
    
    # 첫 청크인 경우 문서 제목 생성 지시 추가
    if is_first_chunk and "PDF" in system_prompt:
        system_prompt += "\n\nIn the first input chunk, create a document title as # header."
    
    prompt = f"{system_prompt}\n\n## Input:\n{text}\n\n## Output:"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16000,
        )
        
        content = response.choices[0].message.content
        if "```markdown" in content:
            temp = content.split("```markdown")[1]
            if "```" in temp:
                return temp.split("```")[0]
        return content
    except Exception as e:
        print(f"API 오류 발생: {str(e)}")
        return ""

# load_file_content를 통해 chunks, system_prompt 로드
# 만약 html 파일일 경우 chunks는 하나의 text chunk로 구성되어있고.
# 만약 pdf 파일일 경우 해당 파일의 내용이 많을 경우 chunks는 chunk들로 구성되어있음.
def translate_file_to_markdown(filename: str, input_file: str, output_folder: str = "output_markdown"):
    chunks, system_prompt = load_file_content(input_file)
    if not chunks or not system_prompt:
        return None

    combined_md = []
    for i, chunk in enumerate(chunks):
        is_first = (i == 0)
        md_part = translate_markdown_from_text(chunk, system_prompt, is_first)
        if md_part:
            # 중복 헤더 제거
            if i > 0:
                md_part = remove_duplicate_headers(md_part)
            combined_md.append(md_part)
    
    final_md = "\n\n".join(combined_md)
    return save_to_markdown(filename, final_md, output_folder)

def remove_duplicate_headers(text: str) -> str:
    """중복된 최상위 헤더 제거"""
    lines = text.split('\n')
    filtered = [line for line in lines if not line.strip().startswith('# ')]
    return '\n'.join(filtered)


def save_to_markdown(filename, markdown_text, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d%H%M%S")
    output_file = f"{filename}_{timestamp}.md"
    output_path = os.path.join(output_folder, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)
    return output_path

# def translate_file_to_markdown(filename: str, input_file: str, output_folder: str = "output_markdown"):
#     text, system_prompt = load_file_content(input_file)
#     if text and system_prompt:
#         translated_markdown = translate_markdown_from_text(text, system_prompt)
#         if translated_markdown:
#             return save_to_markdown(filename, translated_markdown, output_folder)
#     return None

if __name__ == "__main__":
    input_file = 'test_document.pdf'  # 또는 'test_html.txt'
    output_folder = 'output'
    filename = 'test_file'
    result_path = translate_file_to_markdown(filename, input_file, output_folder)
    if result_path:
        print(f"Markdown file saved at: {result_path}")
