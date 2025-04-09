import os
from pathlib import Path
from markdown_translator import translate_file_to_markdown
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_single_file(html_file, input_dir, output_dir):
    input_path = os.path.join(input_dir, html_file)
    filename = os.path.splitext(html_file)[0]  # 확장자 제거

    print(f"Processing: {html_file}")
    result = translate_file_to_markdown(filename, input_path, output_dir)

    if result:
        return f"Successfully converted to: {result}"
    else:
        return f"Failed to convert: {html_file}"

def process_html_files(input_dir: str = "./target_html", output_dir: str = "output_markdown", max_workers: int = 4):
    # 출력 디렉토리 생성
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 입력 디렉토리에서 HTML 파일 찾기
    html_files = [f for f in os.listdir(input_dir) if f.endswith('.html')]

    # 병렬 처리
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, html_file, input_dir, output_dir): html_file
            for html_file in html_files
        }

        for future in as_completed(future_to_file):
            print(future.result())

# 사용 예시
if __name__ == "__main__":
    process_html_files()
