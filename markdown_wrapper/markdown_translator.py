import os
import time
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key="1777ac2662f649a7bbc0c905d85eb7bd",
    api_version="2024-10-21",
    azure_endpoint="https://hkust.azure-api.net"
)

SYSTEM_PROMPT = '''
You are an AI that performs the task of understanding advanced HTML content and converting it into Markdown format. Your job is to read all the information from the provided HTML code accurately, without missing any details, and generate a Markdown document while retaining the original language. The result should be a clear and structured document, categorizing information like titles, links, dates, descriptions, and lists.

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

def load_html_in_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def translate_markdown_from_html(html_text: str) -> str:
    if not html_text:
        return None
    prompt = SYSTEM_PROMPT + "\n\n## Input\n\n{input}\n\n## Output\n".format(input=html_text)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=16000,
        stream=False,
    )
    return response.choices[0].message.content

def save_to_markdown(filename, markdown_text, output_folder):
    os.makedirs(output_folder, exist_ok=True)  # 폴더 생성
    timestamp = time.strftime("%Y%m%d%H%M%S")  # 현재 시간을 기반으로 파일명 생성
    output_file = f"{filename}_{timestamp}.md"
    output_path = os.path.join(output_folder, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)
    return output_path

def translate_html_file_to_markdown(filename: str, input_file: str, output_folder: str = "output_markdown"):
    chat_log = load_html_in_txt(input_file)
    translated_markdown = translate_markdown_from_html(chat_log)
    if translated_markdown:
        return save_to_markdown(filename, translated_markdown, output_folder)
    return None

if __name__ == "__main__":
    input_file = 'test_html.txt'
    output_folder = 'output'
    filename = 'test_file'
    result_path = translate_html_file_to_markdown(filename, input_file, output_folder)
    if result_path:
        print(f"Markdown file saved at: {result_path}")
