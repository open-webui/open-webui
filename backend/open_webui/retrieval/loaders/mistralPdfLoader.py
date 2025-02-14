from typing import List
from pathlib import Path
from open_webui.env import MISTRAL_API_KEY
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import time
import pytesseract
from mistralai import Mistral
from langchain_core.documents import Document
from tenacity import retry, stop_after_attempt, wait_exponential
import re

class MistralVisionPDFLoader:
    """PDF Loader that uses OCR and Mistral's vision model capabilities."""
    
    def __init__(self, file_path: str, max_retries: int = 3):
        """Initialize the loader with file path and Mistral API key."""
        self.file_path = Path(file_path)
        if not MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY is not set")
        self.client = Mistral(api_key=MISTRAL_API_KEY)
        self.max_retries = max_retries

    def _convert_pdf_page_to_image(self, page) -> Image.Image:
        """Convert a PDF page to PIL Image."""
        # Get the page's pixmap with higher DPI for better quality
        zoom = 2  # zoom factor
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    def _optimize_image(self, image: Image.Image, max_size: tuple = (800, 1000)) -> str:
        """Optimize image and convert to base64."""
        width, height = image.size
        aspect_ratio = width / height
        
        # Calculate target dimensions
        if width > max_size[0] or height > max_size[1]:
            if aspect_ratio > 1:
                new_width = min(width, max_size[0])
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = min(height, max_size[1])
                new_width = int(new_height * aspect_ratio)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(buffered.getvalue()).decode()

    def _clean_markdown(self, content: str) -> str:
        """Clean and format markdown content."""
        # Replace escaped newlines with actual newlines
        content = content.replace("\\n", "\n")
        
        # Remove any markdown code block wrapping
        content = content.strip()
        if content.startswith("```") and content.endswith("```"):
            content = content[3:-3].strip()
        if content.startswith("```markdown") and content.endswith("```"):
            content = content[10:-3].strip()

        # Fix table formatting
        lines = content.split('\n')
        in_table = False
        fixed_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Detect table start
            if line.startswith('|'):
                if not in_table:
                    in_table = True
                    fixed_lines.append('')  # Add blank line before table
                
                # Ensure proper cell spacing in tables
                cells = [cell.strip() for cell in line.split('|')]
                line = '| ' + ' | '.join(filter(None, cells)) + ' |'
                
                # Add separator line after header if missing
                if in_table and i > 0 and lines[i-1].startswith('|') and not line.replace('-', '|').strip('|').strip():
                    separator = '|' + '|'.join('-' * len(cell) for cell in cells[1:-1]) + '|'
                    fixed_lines.append(separator)
                
            elif in_table:
                in_table = False
                fixed_lines.append('')  # Add blank line after table
            
            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)
        
        # Clean up multiple consecutive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Ensure proper list formatting
        content = re.sub(r'(?m)^(\s*[-*+])\s', r'\1 ', content)  # Fix bullet points
        content = re.sub(r'(?m)^(\s*\d+\.)\s', r'\1 ', content)  # Fix numbered lists
        
        # Ensure proper header formatting
        content = re.sub(r'(?m)^(#{1,6})\s*', r'\1 ', content)
        
        # Add two spaces for line breaks where needed
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.rstrip()
            if (line and 
                not line.startswith('|') and  # Skip table rows
                not line.startswith('#') and  # Skip headers
                not line.startswith('---') and  # Skip horizontal rules
                not line.startswith('> ') and  # Skip blockquotes
                not line.endswith(':') and  # Skip lines ending with colon
                not line.endswith('.') and  # Skip lines ending with period
                not line.endswith('  ')):  # Skip lines already having line breaks
                line += '  '
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Ensure proper spacing around elements
        content = re.sub(r'([^\n])\n---', r'\1\n\n---', content)
        content = re.sub(r'---\n([^\n])', r'---\n\n\1', content)
        
        return content.strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _process_page_with_vision(self, image: Image.Image, extracted_text: str) -> str:
        """Process an image using OCR and Mistral's vision model with retry logic."""
        try:
            # Convert image to base64
            img_base64 = self._optimize_image(image)

            # Create message for Mistral's vision model
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": """You are a document transcription assistant. Your task is to:
                            1. Carefully read and transcribe all text from the image. Use the reference extracted text as a foundation.
                            2. Preserve the document structure using proper markdown formatting
                            3. Use appropriate markdown syntax for:
                               - Headers (# for main headers, ## for subheaders, etc.)
                               - Lists (- or * for bullet points, 1. for numbered lists)
                               - Tables (using proper | column | format |)
                               - Bold text using **bold**
                               - Italic text using *italic*
                            4. For tables:
                               - Add proper column separators (|)
                               - Include header separator row (| --- | --- |)
                               - Align content within cells
                            5. Maintain document hierarchy and layout
                            6. Return clean markdown without code blocks or escaping"""
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe this document section into clean markdown, paying special attention to table formatting and structure."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Reference OCR text:\n{extracted_text}"
                        }
                    ]
                }
            ]

            # Get response from Mistral's vision model
            response = self.client.chat.complete(
                model="pixtral-12b-2409",
                messages=messages,
                stream=False,
                max_tokens=4000
            )

            content = response.choices[0].message.content
            return self._clean_markdown(content)

        except Exception as e:
            print(f"Error processing page: {str(e)}")
            time.sleep(2)
            raise

    def load(self) -> List[Document]:
        """Load PDF and convert it to documents using OCR and Mistral's vision model."""
        documents = []
        
        # Open PDF file
        pdf_document = fitz.open(self.file_path)
        
        for page_num in range(len(pdf_document)):
            try:
                page = pdf_document[page_num]
                
                # Convert PDF page to image with higher quality
                image = self._convert_pdf_page_to_image(page)
                
                # Extract text using Tesseract OCR
                extracted_text = pytesseract.image_to_string(image)
                
                # Process with Mistral's vision model
                content = self._process_page_with_vision(image, extracted_text)
                
                # Create Document object
                metadata = {
                    "source": str(self.file_path),
                    "page": page_num + 1
                }
                documents.append(Document(page_content=content, metadata=metadata))
                
                # Add a small delay between pages to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing page {page_num + 1}: {str(e)}")
                documents.append(Document(
                    page_content=f"Error processing page: {str(e)}",
                    metadata={"source": str(self.file_path), "page": page_num + 1, "error": True}
                ))
        
        pdf_document.close()
        return documents
