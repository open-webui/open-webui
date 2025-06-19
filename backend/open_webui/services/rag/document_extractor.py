import PyPDF2
import markdown2
from bs4 import BeautifulSoup
from PIL import Image
import os

def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {file_path}: {e}")
        return ""

def extract_text_from_markdown(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        html_content = markdown2.markdown(md_content)
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text()
    except Exception as e:
        print(f"Error extracting text from Markdown {file_path}: {e}")
        return ""

def extract_text_from_image(file_path: str) -> str:
    try:
        with Image.open(file_path) as img:
            filename = os.path.basename(file_path)
            # For MVP, return metadata as text. OCR is more complex.
            text_data = f"Image: {filename}, Format: {img.format}, Mode: {img.mode}, Size: {img.size}"
        return text_data
    except Exception as e:
        print(f"Error extracting metadata from image {file_path}: {e}")
        return ""
