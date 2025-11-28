#!/usr/bin/env python3
"""
Standalone document parsing module for SharePoint content extraction.

This module provides document parsing capabilities using the configured
document extraction engine (Docling, Tika, etc.) without requiring
SharePoint OAuth dependencies.
"""
import os
import sys
import logging
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger("sharepoint_document_parser")

async def parse_document_content(content: bytes, file_name: str) -> str:
    """
    Parse document content using the configured document extraction engine.
    
    Args:
        content: Raw binary content
        file_name: Name of the file to determine parsing method
        
    Returns:
        Parsed text content
    """
    from open_webui.retrieval.loaders.main import Loader
    from open_webui.config import CONTENT_EXTRACTION_ENGINE, TIKA_SERVER_URL
    
    # Add backend path to Python path for imports
    import sys
    import os
    backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    logger.info(f"parse_document_content called for {file_name}, content size: {len(content)} bytes")
    
    try:
        if not isinstance(content, bytes):
            logger.info(f"Content is not bytes for {file_name}, returning as string")
            return str(content)
        
        # Get file extension for MIME type approximation
        file_extension = file_name.split('.')[-1].lower() if '.' in file_name else 'unknown'
        logger.info(f"File extension: {file_extension} for file: {file_name}")
        logger.info(f"Content size: {len(content)} bytes")
        
        # Map file extensions to MIME types
        mime_type_mapping = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'html': 'text/html',
            'xml': 'application/xml'
        }
        
        file_content_type = mime_type_mapping.get(file_extension, 'application/octet-stream')
        logger.info(f"Mapped MIME type: {file_content_type} for {file_name}")
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(suffix=f'.{file_extension}', delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            
            try:
                # Get current engine configuration
                engine = CONTENT_EXTRACTION_ENGINE.value if hasattr(CONTENT_EXTRACTION_ENGINE, 'value') else str(CONTENT_EXTRACTION_ENGINE)
                logger.info(f"Using document extraction engine: {engine} for {file_name}")
                
                # Initialize loader with current engine configuration
                loader_kwargs = {}
                if engine == "tika":
                    tika_url = TIKA_SERVER_URL.value if hasattr(TIKA_SERVER_URL, 'value') else str(TIKA_SERVER_URL)
                    loader_kwargs["TIKA_SERVER_URL"] = tika_url
                    logger.info(f"Configured Tika server URL: {tika_url}")
                
                loader = Loader(engine=engine, **loader_kwargs)
                logger.info(f"Created loader with engine: {engine} for {file_name}")
                
                # Load and process document
                logger.info(f"Starting document processing for {file_name} with temp file: {temp_file.name}")
                documents = loader.load(file_name, file_content_type, temp_file.name)
                logger.info(f"Loader returned {len(documents) if documents else 0} documents for {file_name}")
                
                if documents:
                    # Combine all document content (usually just one document)
                    combined_content = ""
                    for i, doc in enumerate(documents):
                        if hasattr(doc, 'page_content'):
                            content_length = len(doc.page_content) if doc.page_content else 0
                            logger.info(f"Document {i+1} content length: {content_length} characters")
                            if doc.page_content:
                                combined_content += doc.page_content + "\n\n"
                    
                    if combined_content.strip():
                        logger.info(f"Successfully extracted {len(combined_content)} characters of content")
                        return combined_content.strip()
                    else:
                        warning_msg = f"[{file_extension.upper()} Document - {len(content)} bytes]\n\nDocument processed but no text content extracted"
                        logger.warning(f"No content extracted from {file_name}")
                        return warning_msg
                else:
                    warning_msg = f"[{file_extension.upper()} Document - {len(content)} bytes]\n\nNo content could be extracted from document"
                    logger.warning(f"No documents returned for {file_name}")
                    return warning_msg
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file.name)
                    logger.debug(f"Cleaned up temporary file: {temp_file.name}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"Error parsing document content with engine for {file_name}: {e}")
        import traceback
        logger.debug(f"Full traceback for {file_name}: {traceback.format_exc()}")
        
        # More aggressive fallback attempts
        logger.info(f"Attempting fallback extraction methods for {file_name}")
        
        # Fallback to basic text extraction for plain text files
        if file_extension in ['txt', 'csv', 'log']:
            try:
                fallback_content = content.decode('utf-8', errors='ignore')
                if fallback_content.strip():
                    logger.info(f"Successfully extracted text content from {file_name} using UTF-8 fallback")
                    return f"# {file_name}\n\n{fallback_content}"
            except Exception as txt_error:
                logger.debug(f"UTF-8 fallback failed for {file_name}: {txt_error}")
        
        # Try alternative extraction for Office documents when Docling fails
        if file_extension in ['docx', 'doc']:
            logger.info(f"Attempting alternative Word document extraction for: {file_name}")
            try:
                # Try python-docx for simple text extraction
                import zipfile
                import xml.etree.ElementTree as ET
                from io import BytesIO
                
                # Word documents are ZIP files containing XML
                with zipfile.ZipFile(BytesIO(content), 'r') as docx_zip:
                    # Try to extract text from document.xml
                    if 'word/document.xml' in docx_zip.namelist():
                        xml_content = docx_zip.read('word/document.xml')
                        root = ET.fromstring(xml_content)
                        
                        # Extract text content more thoroughly
                        text_elements = []
                        for elem in root.iter():
                            if elem.text and elem.text.strip():
                                text_elements.append(elem.text.strip())
                        
                        if text_elements:
                            extracted_text = ' '.join(text_elements)
                            logger.info(f"Alternative Word extraction successful for {file_name}: {len(extracted_text)} characters")
                            return f"# {file_name}\n\n{extracted_text}"
                        else:
                            logger.warning(f"Alternative Word extraction found no text content in {file_name}")
                        
            except Exception as alt_error:
                logger.warning(f"Alternative Word extraction failed for {file_name}: {alt_error}")
        
        # Try PDF text extraction for PDF files
        if file_extension == 'pdf':
            logger.info(f"Attempting alternative PDF extraction for: {file_name}")
            try:
                # Try multiple PDF extraction methods
                extracted_text = None
                
                # Method 1: Try PyPDF2 if available
                try:
                    import PyPDF2
                    import io
                    
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                    text_parts = []
                    
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text_parts.append(page.extract_text())
                    
                    extracted_text = '\n'.join(text_parts)
                    if extracted_text.strip():
                        logger.info(f"PyPDF2 extraction successful for {file_name}: {len(extracted_text)} characters")
                        return f"# {file_name}\n\n{extracted_text}"
                        
                except ImportError:
                    logger.debug(f"PyPDF2 not available for {file_name}")
                except Exception as pypdf_error:
                    logger.debug(f"PyPDF2 extraction failed for {file_name}: {pypdf_error}")
                
                # Method 2: Try pdfplumber if available
                try:
                    import pdfplumber
                    import io
                    
                    with pdfplumber.open(io.BytesIO(content)) as pdf:
                        text_parts = []
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        
                        extracted_text = '\n'.join(text_parts)
                        if extracted_text.strip():
                            logger.info(f"pdfplumber extraction successful for {file_name}: {len(extracted_text)} characters")
                            return f"# {file_name}\n\n{extracted_text}"
                            
                except ImportError:
                    logger.debug(f"pdfplumber not available for {file_name}")
                except Exception as plumber_error:
                    logger.debug(f"pdfplumber extraction failed for {file_name}: {plumber_error}")
                
                # Method 3: Try basic text search in PDF bytes
                try:
                    # Look for common text patterns in the raw PDF bytes
                    content_str = content.decode('utf-8', errors='ignore')
                    
                    # Extract potential text content from PDF stream objects
                    import re
                    
                    # Look for text in PDF stream objects
                    text_patterns = re.findall(r'stream\s*(.*?)\s*endstream', content_str, re.DOTALL | re.IGNORECASE)
                    extracted_parts = []
                    
                    for pattern in text_patterns:
                        # Clean up and extract readable text
                        cleaned = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', ' ', pattern)
                        words = [word for word in cleaned.split() if len(word) > 2 and word.isalpha()]
                        if len(words) > 3:  # Only include patterns with reasonable text
                            extracted_parts.append(' '.join(words))
                    
                    if extracted_parts:
                        extracted_text = '\n'.join(extracted_parts)
                        logger.info(f"Basic PDF text extraction found some content for {file_name}: {len(extracted_text)} characters")
                        return f"# {file_name}\n\n{extracted_text}"
                        
                except Exception as basic_error:
                    logger.debug(f"Basic PDF extraction failed for {file_name}: {basic_error}")
                
                logger.warning(f"All PDF extraction methods failed for {file_name}")
                
            except Exception as pdf_error:
                logger.warning(f"Alternative PDF extraction failed for {file_name}: {pdf_error}")
        
        # Final fallback with detailed error information
        error_details = f"Document parsing failed with engine '{CONTENT_EXTRACTION_ENGINE}': {str(e)}"
        
        return f"""# {file_name}

**Document Parsing Error**

The document could not be parsed automatically. This may be due to:
- Document protection or encryption
- Unsupported document format or corruption
- Missing document processing libraries
- Network or temporary processing issues

**Technical Details:**
- File size: {len(content)} bytes
- File type: {file_extension.upper()}
- Error: {error_details}

**Recommendation:**
Please access this document directly via SharePoint to view its contents, or contact your system administrator if you believe this should be accessible through the chat interface.

**Note:** The document exists and was successfully retrieved from SharePoint, but content extraction failed during processing.
"""