#!/usr/bin/env python3
"""
Completely standalone document parsing module for SharePoint content extraction.

This module provides document parsing capabilities using only standard libraries
and direct PDF/document parsing without requiring any open_webui dependencies.
"""
import os
import sys
import logging
import tempfile
import re
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger("standalone_document_parser")


async def parse_document_content(content: bytes, file_name: str) -> str:
    """
    Parse document content using direct PDF/document parsing libraries.

    Args:
        content: Raw binary content
        file_name: Name of the file to determine parsing method

    Returns:
        Parsed text content
    """

    logger.info(
        f"parse_document_content called for {file_name}, content size: {len(content)} bytes"
    )

    try:
        if not isinstance(content, bytes):
            logger.info(f"Content is not bytes for {file_name}, returning as string")
            return str(content)

        # Get file extension for parsing method selection
        file_extension = (
            file_name.split(".")[-1].lower() if "." in file_name else "unknown"
        )
        logger.info(f"File extension: {file_extension} for file: {file_name}")
        logger.info(f"Content size: {len(content)} bytes")

        # Try direct parsing based on file type
        if file_extension == "pdf":
            return await parse_pdf_content(content, file_name)
        elif file_extension in ["docx", "doc"]:
            return await parse_word_content(content, file_name)
        elif file_extension in ["txt", "csv", "log"]:
            return await parse_text_content(content, file_name)
        else:
            # For unknown file types, try to extract any readable text
            return await parse_generic_content(content, file_name)

    except Exception as e:
        logger.error(f"Error parsing document content for {file_name}: {e}")
        import traceback

        logger.debug(f"Full traceback for {file_name}: {traceback.format_exc()}")

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
- Error: {str(e)}

**Recommendation:**
Please access this document directly via SharePoint to view its contents, or contact your system administrator if you believe this should be accessible through the chat interface.

**Note:** The document exists and was successfully retrieved from SharePoint, but content extraction failed during processing.
"""


async def parse_pdf_content(content: bytes, file_name: str) -> str:
    """Parse PDF content using multiple extraction methods."""
    logger.info(f"Attempting PDF extraction for: {file_name}")

    # Method 1: Try pypdf if available
    try:
        import pypdf
        import io

        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        text_parts = []

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        extracted_text = "\n".join(text_parts)
        if extracted_text.strip():
            logger.info(
                f"pypdf extraction successful for {file_name}: {len(extracted_text)} characters"
            )
            return f"# {file_name}\n\n{extracted_text}"

    except ImportError:
        logger.debug(f"pypdf not available for {file_name}")
    except Exception as pypdf_error:
        logger.debug(f"pypdf extraction failed for {file_name}: {pypdf_error}")

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

            extracted_text = "\n".join(text_parts)
            if extracted_text.strip():
                logger.info(
                    f"pdfplumber extraction successful for {file_name}: {len(extracted_text)} characters"
                )
                return f"# {file_name}\n\n{extracted_text}"

    except ImportError:
        logger.debug(f"pdfplumber not available for {file_name}")
    except Exception as plumber_error:
        logger.debug(f"pdfplumber extraction failed for {file_name}: {plumber_error}")

    # Method 3: Try basic text search in PDF bytes
    try:
        # Look for common text patterns in the raw PDF bytes
        content_str = content.decode("utf-8", errors="ignore")

        # Extract potential text content from PDF stream objects
        text_patterns = re.findall(
            r"stream\s*(.*?)\s*endstream", content_str, re.DOTALL | re.IGNORECASE
        )
        extracted_parts = []

        for pattern in text_patterns:
            # Clean up and extract readable text
            cleaned = re.sub(r"[^\w\s\.\,\;\:\!\?\-\(\)]", " ", pattern)
            words = [
                word for word in cleaned.split() if len(word) > 2 and word.isalpha()
            ]
            if len(words) > 3:  # Only include patterns with reasonable text
                extracted_parts.append(" ".join(words))

        if extracted_parts:
            extracted_text = "\n".join(extracted_parts)
            logger.info(
                f"Basic PDF text extraction found some content for {file_name}: {len(extracted_text)} characters"
            )
            return f"# {file_name}\n\n{extracted_text}"

    except Exception as basic_error:
        logger.debug(f"Basic PDF extraction failed for {file_name}: {basic_error}")

    # If all methods fail, return error
    return f"# {file_name}\n\n**PDF Parsing Failed**\n\nUnable to extract text content from this PDF document using available parsers. Please access the document directly via SharePoint."


async def parse_word_content(content: bytes, file_name: str) -> str:
    """Parse Word document content using XML extraction."""
    logger.info(f"Attempting Word document extraction for: {file_name}")

    try:
        # Word documents are ZIP files containing XML
        with zipfile.ZipFile(BytesIO(content), "r") as docx_zip:
            # Try to extract text from document.xml
            if "word/document.xml" in docx_zip.namelist():
                xml_content = docx_zip.read("word/document.xml")
                root = ET.fromstring(xml_content)

                # Extract text content more thoroughly
                text_elements = []
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_elements.append(elem.text.strip())

                if text_elements:
                    extracted_text = " ".join(text_elements)
                    logger.info(
                        f"Word extraction successful for {file_name}: {len(extracted_text)} characters"
                    )
                    return f"# {file_name}\n\n{extracted_text}"
                else:
                    logger.warning(
                        f"Word extraction found no text content in {file_name}"
                    )

    except Exception as word_error:
        logger.warning(f"Word extraction failed for {file_name}: {word_error}")

    return f"# {file_name}\n\n**Word Document Parsing Failed**\n\nUnable to extract text content from this Word document. Please access the document directly via SharePoint."


async def parse_text_content(content: bytes, file_name: str) -> str:
    """Parse plain text content."""
    try:
        text_content = content.decode("utf-8", errors="ignore")
        if text_content.strip():
            logger.info(
                f"Text extraction successful for {file_name}: {len(text_content)} characters"
            )
            return f"# {file_name}\n\n{text_content}"
    except Exception as text_error:
        logger.warning(f"Text extraction failed for {file_name}: {text_error}")

    return f"# {file_name}\n\n**Text File Parsing Failed**\n\nUnable to decode text content. Please access the document directly."


async def parse_generic_content(content: bytes, file_name: str) -> str:
    """Try to extract any readable text from unknown file types."""
    try:
        # Try basic text extraction
        text_content = content.decode("utf-8", errors="ignore")

        # Look for meaningful text patterns
        lines = text_content.split("\n")
        meaningful_lines = []

        for line in lines:
            # Keep lines that have reasonable text content
            clean_line = re.sub(r"[^\w\s\.\,\;\:\!\?\-\(\)]", " ", line)
            words = [
                word
                for word in clean_line.split()
                if len(word) > 2
                and word.replace("-", "").replace(".", "").replace(",", "").isalnum()
            ]

            if len(words) >= 3:  # Lines with at least 3 meaningful words
                meaningful_lines.append(" ".join(words))

        if meaningful_lines:
            extracted_text = "\n".join(
                meaningful_lines[:50]
            )  # Limit to first 50 meaningful lines
            logger.info(
                f"Generic text extraction found content for {file_name}: {len(extracted_text)} characters"
            )
            return f"# {file_name}\n\n{extracted_text}"

    except Exception as generic_error:
        logger.warning(
            f"Generic text extraction failed for {file_name}: {generic_error}"
        )

    return f"# {file_name}\n\n**Unknown File Type**\n\nUnable to extract readable content from this file type. Please access the document directly via SharePoint."


def search_content_for_keywords(content: str, keywords: List[str]) -> Dict[str, Any]:
    """
    Search extracted content for specific keywords and patterns.

    Args:
        content: Extracted document content
        keywords: List of keywords to search for

    Returns:
        Dictionary with search results and relevance score
    """
    if not content or not keywords:
        return {"relevance_score": 0, "found_keywords": [], "matched_text": ""}

    # Convert to lowercase for case-insensitive search
    content_lower = content.lower()
    found_keywords = []
    matched_sections = []

    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in content_lower:
            found_keywords.append(keyword)

            # Extract context around the keyword
            keyword_index = content_lower.find(keyword_lower)
            start = max(0, keyword_index - 100)
            end = min(len(content), keyword_index + len(keyword) + 100)
            context = content[start:end].strip()
            matched_sections.append(f"...{context}...")

    # Calculate relevance score based on keyword matches
    relevance_score = len(found_keywords) / len(keywords) if keywords else 0

    # Boost score if multiple keywords found
    if len(found_keywords) > 1:
        relevance_score = min(1.0, relevance_score * 1.5)

    return {
        "relevance_score": relevance_score,
        "found_keywords": found_keywords,
        "matched_text": "\n\n".join(matched_sections[:3]),  # Limit to first 3 matches
    }
