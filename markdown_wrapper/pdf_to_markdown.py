import os
import glob
import threading
from concurrent.futures import ThreadPoolExecutor
from markdown_translator import translate_file_to_markdown

# 스레드 안전한 파일 작성을 위한 Lock 객체
write_lock = threading.Lock()

def load_converted_files(converted_file: str) -> set:
    """변환 완료된 파일 목록 불러오기"""
    try:
        with write_lock:
            with open(converted_file, 'r') as f:
                return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def convert_pdf_to_markdown(pdf_path: str, output_folder: str, converted_file: str):
    """개별 PDF 파일 변환 처리"""
    try:
        abs_pdf_path = os.path.abspath(pdf_path)
        file_name = os.path.basename(abs_pdf_path)
        
        # 실제 변환 작업 수행
        result_path = translate_file_to_markdown(file_name, abs_pdf_path, output_folder)
        
        if result_path:
            # 성공 시 변환 목록에 추가
            with write_lock:
                with open(converted_file, 'a') as f:
                    f.write(f"{abs_pdf_path}\n")
            
            print(f"[SUCCESS]: {abs_pdf_path}")
        else:
            print(f"[FAIL]: {abs_pdf_path}")
            
    except Exception as e:
        print(f"{abs_pdf_path} [ERROR]: {str(e)}")

def main():
    # 경로 설정
    pdf_folder = "./pdf_list"
    output_folder = "./output_from_pdf"
    converted_file = os.path.join(output_folder, "converted_pdf.txt")
    
    # 출력 폴더 생성
    os.makedirs(output_folder, exist_ok=True)
    
    # 이미 변환된 파일 목록 불러오기
    converted_files = load_converted_files(converted_file)
    
    # 처리 대상 파일 필터링
    all_pdfs = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    new_pdfs = [
        os.path.abspath(pdf) 
        for pdf in all_pdfs 
        if os.path.abspath(pdf) not in converted_files
    ]
    
    print(f"처리 대상 파일 수: {len(new_pdfs)}")
    
    # 병렬 처리 실행
    with ThreadPoolExecutor() as executor:
        tasks = [
            executor.submit(
                convert_pdf_to_markdown,
                pdf,
                output_folder,
                converted_file
            ) 
            for pdf in new_pdfs
        ]
        
        # 모든 작업 완료 대기
        for future in tasks:
            future.result()

if __name__ == "__main__":
    main()