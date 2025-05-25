import json
import logging
import mimetypes
import os
import shutil
import asyncio


import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Union

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    Request,
    status,
    APIRouter,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import tiktoken

# Enhanced text processing imports for all files
import re
import unicodedata
from html import unescape
from urllib.parse import unquote

from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document

from open_webui.models.files import FileModel, Files
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage


from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

# Document loaders
from open_webui.retrieval.loaders.main import Loader
from open_webui.retrieval.loaders.youtube import YoutubeLoader

# Note: Unstructured.io is now the DEFAULT document processing engine
# It's imported and handled in the Loader class in retrieval/loaders/main.py

# Web search engines
from open_webui.retrieval.web.main import SearchResult
from open_webui.retrieval.web.utils import get_web_loader
from open_webui.retrieval.web.brave import search_brave
from open_webui.retrieval.web.kagi import search_kagi
from open_webui.retrieval.web.mojeek import search_mojeek
from open_webui.retrieval.web.bocha import search_bocha
from open_webui.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.retrieval.web.google_pse import search_google_pse
from open_webui.retrieval.web.jina_search import search_jina
from open_webui.retrieval.web.searchapi import search_searchapi
from open_webui.retrieval.web.serpapi import search_serpapi
from open_webui.retrieval.web.searxng import search_searxng
from open_webui.retrieval.web.yacy import search_yacy
from open_webui.retrieval.web.serper import search_serper
from open_webui.retrieval.web.serply import search_serply
from open_webui.retrieval.web.serpstack import search_serpstack
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.bing import search_bing
from open_webui.retrieval.web.exa import search_exa
from open_webui.retrieval.web.perplexity import search_perplexity
from open_webui.retrieval.web.sougou import search_sougou
from open_webui.retrieval.web.firecrawl import search_firecrawl
from open_webui.retrieval.web.external import search_external

from open_webui.retrieval.utils import (
    get_embedding_function,
    get_model_path,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from open_webui.utils.misc import (
    calculate_sha256_string,
)
from open_webui.utils.auth import get_admin_user, get_verified_user

from open_webui.config import (
    ENV,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    UPLOAD_DIR,
    DEFAULT_LOCALE,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_QUERY_PREFIX,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    DEVICE_TYPE,
    DOCKER,
    SENTENCE_TRANSFORMERS_BACKEND,
    SENTENCE_TRANSFORMERS_MODEL_KWARGS,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
)

from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

##########################################
#
# Enhanced Document Cleaning Functions
#
##########################################


def clean_text_for_vector_db(text: str) -> str:
    """
    Comprehensive text cleaning function that removes unwanted characters,
    normalizes encoding, and prepares text for vector database storage.
    
    Args:
        text (str): Raw text content from document processing
        
    Returns:
        str: Cleaned and normalized text ready for embedding
    """
    if not text or not isinstance(text, str):
        return ""
    
    try:
        # Pre-sanitization: Handle edge cases that could break regex
        # Remove null bytes and other problematic characters that could cause regex errors
        text = text.replace('\x00', '')  # Remove null bytes
        
        # Ensure we have a valid string (convert bytes if needed)
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Handle extremely malformed text that could break regex
        if len(text) > 1000000:  # Limit extremely large texts
            log.warning("Text is very large, truncating for safety")
            text = text[:1000000]
        
        # Step 1: Handle HTML entities and URL encoding
        text = unescape(text)  # Convert HTML entities like &amp; to &
        text = unquote(text)   # Decode URL-encoded characters
        
        # Step 2: Normalize Unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Step 3: Remove or replace problematic control characters
        # Keep newlines, tabs, and carriage returns but remove other control chars
        control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
        text = control_chars.sub('', text)
        
        # Step 4: Clean up escape sequences and special characters
        escape_patterns = [
            (r'\\n', '\n'),           # Convert literal \n to actual newlines
            (r'\\t', '\t'),           # Convert literal \t to actual tabs
            (r'\\r', '\r'),           # Convert literal \r to carriage returns
            (r'\\/', '/'),            # Convert literal \/ to /
            (r'\\"', '"'),            # Convert literal \" to "
            (r"\\\'", "'"),           # Convert literal \' to '
            (r'\\\\', '\\'),          # Convert double backslashes to single
        ]
        
        for pattern, replacement in escape_patterns:
            try:
                # Special handling for backslash pattern to avoid regex errors
                if pattern == r'\\\\':
                    # Use string replacement for double backslashes instead of regex
                    text = text.replace('\\\\', '\\')
                else:
                    text = re.sub(pattern, replacement, text)
            except re.error as e:
                log.warning(f"Regex error with pattern '{pattern}': {e}")
                continue
        
        # Step 5: Remove excessive whitespace while preserving structure
        # Replace multiple consecutive spaces with single space
        try:
            text = re.sub(r' {2,}', ' ', text)
        except re.error:
            log.warning("Error removing excessive spaces")
        
        # Replace multiple consecutive newlines with double newline (paragraph break)
        try:
            text = re.sub(r'\n{3,}', '\n\n', text)
        except re.error:
            log.warning("Error normalizing newlines")
        
        # Remove trailing/leading whitespace from each line
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        # Step 6: Remove common document artifacts
        # Remove page numbers at start/end of lines
        try:
            text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        except re.error:
            log.warning("Error removing page numbers")
        
        # Remove common headers/footers patterns
        header_footer_patterns = [
            r'^\s*Page \d+ of \d+\s*$',
            r'^\s*\d+/\d+\s*$',
            r'^\s*\[Page \d+\]\s*$',
            r'^\s*- \d+ -\s*$',
        ]
        
        for pattern in header_footer_patterns:
            try:
                text = re.sub(pattern, '', text, flags=re.MULTILINE)
            except re.error as e:
                log.warning(f"Regex error with header/footer pattern '{pattern}': {e}")
                continue
        
        # Step 7: Clean up document structure markers
        # Remove excessive dashes or underscores used as separators
        try:
            text = re.sub(r'^[-_]{3,}\s*$', '', text, flags=re.MULTILINE)
        except re.error:
            log.warning("Error removing document separators")
        
        # Remove table-of-contents dots
        try:
            text = re.sub(r'\.{3,}', '...', text)
        except re.error:
            log.warning("Error cleaning table-of-contents dots")
        
        # Step 8: Handle special PDF/OCR artifacts
        # Remove soft hyphens and zero-width characters
        text = text.replace('\u00AD', '')  # Soft hyphen
        text = text.replace('\u200B', '')  # Zero-width space
        text = text.replace('\u200C', '')  # Zero-width non-joiner
        text = text.replace('\u200D', '')  # Zero-width joiner
        text = text.replace('\uFEFF', '')  # Byte order mark
        
        # Step 9: Fix common OCR/extraction errors
        # Fix common letter substitutions (be careful not to break legitimate text)
        try:
            text = re.sub(r'\.([A-Z])', r'. \1', text)  # Add space after periods if missing
        except re.error:
            log.warning("Error fixing sentence spacing")
        
        # Step 10: Final cleanup
        # Remove any remaining excessive whitespace
        try:
            text = re.sub(r'\s+', ' ', text)
        except re.error:
            log.warning("Error in final whitespace cleanup")
        text = text.strip()
        
        # Step 11: Validate result
        if len(text) == 0:
            log.warning("Text cleaning resulted in empty string")
            return ""
        
        # Check for encoding issues by trying to encode/decode
        try:
            text.encode('utf-8').decode('utf-8')
        except UnicodeError as e:
            log.warning(f"Text contains encoding issues after cleaning: {e}")
            # Fall back to replacing problematic characters
            text = text.encode('utf-8', errors='replace').decode('utf-8')
        
        log.debug(f"Text cleaned successfully. Length: {len(text)} chars")
        return text
        
    except Exception as e:
        log.error(f"Error during text cleaning: {e}")
        # Return original text if cleaning fails
        return text if isinstance(text, str) else str(text)


def clean_document_content(doc: Document) -> Document:
    """
    Clean a Document object's page_content using the comprehensive text cleaner.
    
    Args:
        doc (Document): Document with potentially messy content
        
    Returns:
        Document: Document with cleaned content
    """
    try:
        cleaned_content = clean_text_for_vector_db(doc.page_content)
        
        # Create new document with cleaned content
        return Document(
            page_content=cleaned_content,
            metadata=doc.metadata
        )
    except Exception as e:
        log.error(f"Error cleaning document content: {e}")
        return doc


##########################################
#
# Content-Aware Text Splitting
#
##########################################


class ContentAwareTextSplitter:
    """
    Advanced text splitter that recognizes document structure and splits on semantic boundaries.
    Preserves context and hierarchical relationships while respecting chunk size limits.
    
    Available TEXT_SPLITTER options in OpenWebUI config:
    - "character" or "": Basic recursive character splitting (legacy)
    - "token": Token-based splitting using tiktoken
    - "content_aware": Intelligent document structure-aware splitting (NEW)
    - Any other value: Defaults to content_aware splitting (ENHANCED DEFAULT)
    
    Features:
    - Document structure detection (headings, sections, paragraphs)
    - Semantic boundary detection and preservation
    - Hierarchical context preservation
    - Intelligent overlap handling
    - Fallback to character-based splitting if needed
    - Enhanced metadata with chunk information
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000,
        preserve_headers: bool = True,
        add_start_index: bool = True,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.preserve_headers = preserve_headers
        self.add_start_index = add_start_index
        
        # Patterns for detecting document structure
        self.heading_patterns = [
            # Markdown-style headings
            (r'^#{1,6}\s+(.+)$', 'markdown_heading'),
            # Numbered sections
            (r'^\d+\.?\s+([A-Z][^.!?]*[.!?]?)$', 'numbered_section'),
            # Chapter/Section titles
            (r'^(Chapter|Section|Part|Article)\s+\d+[:\s]+(.+)$', 'chapter_section'),
            # All caps headings
            (r'^[A-Z\s]{3,}$', 'caps_heading'),
            # Underlined headings (text followed by === or ---)
            (r'^(.+)\n[=-]{3,}$', 'underlined_heading'),
        ]
        
        # Patterns for semantic boundaries
        self.boundary_patterns = [
            # Paragraph breaks (double newline)
            (r'\n\s*\n', 'paragraph_break'),
            # List items
            (r'^\s*[-*+•]\s+', 'list_item'),
            (r'^\s*\d+\.\s+', 'numbered_list'),
            # Table rows (basic detection)
            (r'\|.*\|', 'table_row'),
            # Code blocks
            (r'```[\s\S]*?```', 'code_block'),
            (r'`[^`]+`', 'inline_code'),
        ]
    
    def _detect_document_structure(self, text: str) -> list:
        """
        Analyze text to identify document structure elements.
        Returns list of (start_pos, end_pos, element_type, content, hierarchy_level)
        """
        elements = []
        lines = text.split('\n')
        current_pos = 0
        
        print(f"CONTENT-AWARE DIAGNOSTICS: Analyzing document structure for {len(lines)} lines...")
        
        for i, line in enumerate(lines):
            line_start = current_pos
            line_end = current_pos + len(line)
            
            # Check for headings
            for pattern, element_type in self.heading_patterns:
                match = re.match(pattern, line.strip(), re.MULTILINE)
                if match:
                    # Determine hierarchy level
                    if element_type == 'markdown_heading':
                        level = len(line.strip()) - len(line.strip().lstrip('#'))
                    elif element_type in ['numbered_section', 'chapter_section']:
                        level = 1
                    else:
                        level = 2
                    
                    elements.append((
                        line_start, line_end, element_type, 
                        line.strip(), level
                    ))
                    print(f"  📋 Found {element_type} (level {level}): '{line.strip()[:50]}...'")
                    break
            
            # Check for list items and other elements
            for pattern, element_type in self.boundary_patterns:
                if re.match(pattern, line.strip()):
                    elements.append((
                        line_start, line_end, element_type, 
                        line.strip(), 0
                    ))
                    print(f"  🔹 Found {element_type}: '{line.strip()[:30]}...'")
                    break
            
            current_pos = line_end + 1  # +1 for newline
        
        print(f"CONTENT-AWARE DIAGNOSTICS: Detected {len(elements)} structure elements")
        return elements
    
    def _find_optimal_split_points(self, text: str, elements: list) -> list:
        """
        Find optimal split points based on document structure and chunk size constraints.
        """
        split_points = [0]  # Always start at beginning
        
        # Sort elements by position
        elements.sort(key=lambda x: x[0])
        
        current_chunk_start = 0
        current_chunk_size = 0
        
        print(f"CONTENT-AWARE DIAGNOSTICS: Finding optimal split points (target chunk size: {self.chunk_size})")
        
        for start_pos, end_pos, element_type, content, level in elements:
            # Calculate distance from chunk start
            distance_from_start = start_pos - current_chunk_start
            
            # If we're approaching chunk size limit, consider this as a split point
            if (distance_from_start >= self.chunk_size - self.chunk_overlap and 
                element_type in ['paragraph_break', 'markdown_heading', 'numbered_section', 'chapter_section']):
                
                # Ensure minimum chunk size
                if distance_from_start >= self.min_chunk_size:
                    split_points.append(start_pos)
                    print(f"  ✂️ Split point at {start_pos} (distance: {distance_from_start}) - {element_type}")
                    current_chunk_start = start_pos
                    current_chunk_size = 0
                else:
                    print(f"  ⚠️ Skipping split at {start_pos} - below minimum chunk size ({distance_from_start} < {self.min_chunk_size})")
            
            # Force split if we exceed max chunk size
            elif distance_from_start >= self.max_chunk_size:
                split_points.append(start_pos)
                print(f"  🚨 FORCED split at {start_pos} (distance: {distance_from_start}) - exceeded max chunk size")
                current_chunk_start = start_pos
                current_chunk_size = 0
        
        # Always end at text end
        if split_points[-1] != len(text):
            split_points.append(len(text))
        
        print(f"CONTENT-AWARE DIAGNOSTICS: Generated {len(split_points)} split points: {split_points}")
        return split_points
    
    def _create_chunk_with_context(self, text: str, start: int, end: int, 
                                  elements: list, chunk_index: int) -> str:
        """
        Create a text chunk with preserved context and hierarchy.
        """
        chunk_text = text[start:end].strip()
        
        if not self.preserve_headers:
            return chunk_text
        
        # Find relevant headers that provide context
        context_headers = []
        for elem_start, elem_end, element_type, content, level in elements:
            if (elem_start < start and 
                element_type in ['markdown_heading', 'numbered_section', 'chapter_section'] and
                level <= 3):  # Only include top-level headers for context
                context_headers.append((level, content))
        
        # Add hierarchical context at the beginning of chunk
        if context_headers and chunk_index > 0:
            # Sort by hierarchy level and take the most relevant
            context_headers.sort(key=lambda x: x[0])
            context_text = " > ".join([header[1] for header in context_headers[-2:]])
            chunk_text = f"[Context: {context_text}]\n\n{chunk_text}"
        
        return chunk_text
    
    def _handle_overlap(self, text: str, split_points: list) -> list:
        """
        Adjust split points to include overlap between chunks.
        """
        if len(split_points) <= 2:
            return split_points
        
        adjusted_points = [split_points[0]]
        
        for i in range(1, len(split_points) - 1):
            current_start = split_points[i]
            overlap_start = max(
                adjusted_points[-1],
                current_start - self.chunk_overlap
            )
            adjusted_points.append(overlap_start)
        
        adjusted_points.append(split_points[-1])
        return adjusted_points
    
    def split_text(self, text: str) -> list:
        """
        Split text into content-aware chunks.
        """
        if not text or len(text) <= self.min_chunk_size:
            return [text] if text else []
        
        print(f"CONTENT-AWARE DIAGNOSTICS: Starting content-aware text splitting...")
        print(f"  📊 Input text length: {len(text)} characters")
        print(f"  ⚙️ Chunk size: {self.chunk_size}, Overlap: {self.chunk_overlap}")
        print(f"  📏 Min chunk: {self.min_chunk_size}, Max chunk: {self.max_chunk_size}")
        
        try:
            # Detect document structure
            print(f"  🔍 Step 1: Detecting document structure...")
            elements = self._detect_document_structure(text)
            
            # Find optimal split points
            print(f"  ✂️ Step 2: Finding optimal split points...")
            split_points = self._find_optimal_split_points(text, elements)
            
            # Handle overlap
            print(f"  🔄 Step 3: Handling overlap...")
            split_points = self._handle_overlap(text, split_points)
            
            # Create chunks with context
            print(f"  📝 Step 4: Creating chunks with context...")
            chunks = []
            for i in range(len(split_points) - 1):
                start = split_points[i]
                end = split_points[i + 1]
                
                chunk_text = self._create_chunk_with_context(
                    text, start, end, elements, i
                )
                
                if chunk_text.strip():
                    chunks.append(chunk_text)
                    print(f"    📄 Chunk {i+1}: {len(chunk_text)} chars (positions {start}-{end})")
            
            # Validate chunks
            print(f"  ✅ Step 5: Validating chunks...")
            valid_chunks = []
            for i, chunk in enumerate(chunks):
                if len(chunk) >= self.min_chunk_size or len(chunks) == 1:
                    valid_chunks.append(chunk)
                    print(f"    ✓ Chunk {i+1} validated: {len(chunk)} chars")
                elif valid_chunks:
                    # Merge small chunks with previous chunk
                    print(f"    🔗 Merging small chunk {i+1} ({len(chunk)} chars) with previous chunk")
                    valid_chunks[-1] += "\n\n" + chunk
            
            print(f"CONTENT-AWARE DIAGNOSTICS: ✨ Splitting completed successfully!")
            print(f"  📈 Final result: {len(valid_chunks)} content-aware chunks")
            
            # Show chunk size distribution
            chunk_sizes = [len(chunk) for chunk in valid_chunks]
            if chunk_sizes:
                print(f"  📊 Chunk size stats: min={min(chunk_sizes)}, max={max(chunk_sizes)}, avg={sum(chunk_sizes)//len(chunk_sizes)}")
            
            return valid_chunks if valid_chunks else [text]
            
        except Exception as e:
            print(f"CONTENT-AWARE DIAGNOSTICS: ❌ Error during content-aware splitting: {e}")
            log.warning(f"Content-aware splitting failed: {e}. Falling back to simple splitting.")
            # Fallback to simple character-based splitting
            fallback_chunks = self._fallback_split(text)
            print(f"CONTENT-AWARE DIAGNOSTICS: 🔄 Fallback splitting produced {len(fallback_chunks)} chunks")
            return fallback_chunks
    
    def _fallback_split(self, text: str) -> list:
        """
        Fallback to simple character-based splitting if content-aware splitting fails.
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Try to break at word boundary
            if end < len(text):
                # Look for sentence or paragraph boundary within overlap range
                for boundary in ['. ', '.\n', '\n\n', '\n', '. ']:
                    boundary_pos = text.rfind(boundary, start, end)
                    if boundary_pos > start:
                        end = boundary_pos + len(boundary)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = max(start + self.chunk_size - self.chunk_overlap, end)
        
        return chunks
    
    def split_documents(self, documents: list) -> list:
        """
        Split a list of Document objects using content-aware splitting.
        """
        split_docs = []
        
        for doc in documents:
            chunks = self.split_text(doc.page_content)
            
            for i, chunk in enumerate(chunks):
                # Create new document with chunk
                chunk_metadata = doc.metadata.copy()
                
                if self.add_start_index:
                    # Calculate approximate start index
                    chunk_start = doc.page_content.find(chunk.split('\n\n')[-1][:50])
                    if chunk_start == -1:
                        chunk_start = i * self.chunk_size
                    chunk_metadata['start_index'] = chunk_start
                
                chunk_metadata['chunk_index'] = i
                chunk_metadata['total_chunks'] = len(chunks)
                chunk_metadata['chunk_method'] = 'content_aware'
                
                split_docs.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
        
        return split_docs


##########################################
#
# Utility functions
#
##########################################


def get_ef(
    engine: str,
    embedding_model: str,
    auto_update: bool = False,
):
    ef = None
    if embedding_model and engine == "":
        from sentence_transformers import SentenceTransformer

        try:
            ef = SentenceTransformer(
                get_model_path(embedding_model, auto_update),
                device=DEVICE_TYPE,
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
                backend=SENTENCE_TRANSFORMERS_BACKEND,
                model_kwargs=SENTENCE_TRANSFORMERS_MODEL_KWARGS,
            )
        except Exception as e:
            log.debug(f"Error loading SentenceTransformer: {e}")

    return ef


def get_rf(
    engine: str = "",
    reranking_model: Optional[str] = None,
    external_reranker_url: str = "",
    external_reranker_api_key: str = "",
    auto_update: bool = False,
):
    rf = None
    if reranking_model:
        if any(model in reranking_model for model in ["jinaai/jina-colbert-v2"]):
            try:
                from open_webui.retrieval.models.colbert import ColBERT

                rf = ColBERT(
                    get_model_path(reranking_model, auto_update),
                    env="docker" if DOCKER else None,
                )

            except Exception as e:
                log.error(f"ColBERT: {e}")
                raise Exception(ERROR_MESSAGES.DEFAULT(e))
        else:
            if engine == "external":
                try:
                    from open_webui.retrieval.models.external import ExternalReranker

                    rf = ExternalReranker(
                        url=external_reranker_url,
                        api_key=external_reranker_api_key,
                        model=reranking_model,
                    )
                except Exception as e:
                    log.error(f"ExternalReranking: {e}")
                    raise Exception(ERROR_MESSAGES.DEFAULT(e))
            else:
                import sentence_transformers

                try:
                    rf = sentence_transformers.CrossEncoder(
                        get_model_path(reranking_model, auto_update),
                        device=DEVICE_TYPE,
                        trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                        backend=SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
                        model_kwargs=SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
                    )
                except Exception as e:
                    log.error(f"CrossEncoder: {e}")
                    raise Exception(ERROR_MESSAGES.DEFAULT("CrossEncoder error"))

    return rf


##########################################
#
# API routes
#
##########################################


router = APIRouter()


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class SearchForm(BaseModel):
    queries: List[str]


@router.get("/")
async def get_status(request: Request):
    return {
        "status": True,
        "chunk_size": request.app.state.config.CHUNK_SIZE,
        "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
        "template": request.app.state.config.RAG_TEMPLATE,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    }


@router.get("/embedding")
async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        "openai_config": {
            "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
            "key": request.app.state.config.RAG_OPENAI_API_KEY,
        },
        "ollama_config": {
            "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
            "key": request.app.state.config.RAG_OLLAMA_API_KEY,
        },
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class OllamaConfigForm(BaseModel):
    url: str
    key: str


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    ollama_config: Optional[OllamaConfigForm] = None
    embedding_engine: str
    embedding_model: str
    embedding_batch_size: Optional[int] = 1


@router.post("/embedding/update")
async def update_embedding_config(
    request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating embedding model: {request.app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        request.app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        request.app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if request.app.state.config.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            if form_data.openai_config is not None:
                request.app.state.config.RAG_OPENAI_API_BASE_URL = (
                    form_data.openai_config.url
                )
                request.app.state.config.RAG_OPENAI_API_KEY = (
                    form_data.openai_config.key
                )

            if form_data.ollama_config is not None:
                request.app.state.config.RAG_OLLAMA_BASE_URL = (
                    form_data.ollama_config.url
                )
                request.app.state.config.RAG_OLLAMA_API_KEY = (
                    form_data.ollama_config.key
                )

            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE = (
                form_data.embedding_batch_size
            )

        request.app.state.ef = get_ef(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
        )

        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_BASE_URL
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_API_KEY
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        return {
            "status": True,
            "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
            "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
            "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            "openai_config": {
                "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
                "key": request.app.state.config.RAG_OPENAI_API_KEY,
            },
            "ollama_config": {
                "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
                "key": request.app.state.config.RAG_OLLAMA_API_KEY,
            },
        }
    except Exception as e:
        log.exception(f"Problem updating embedding model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.get("/config")
async def get_rag_config(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        # RAG settings
        "RAG_TEMPLATE": request.app.state.config.RAG_TEMPLATE,
        "TOP_K": request.app.state.config.TOP_K,
        "BYPASS_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        "ENABLE_RAG_HYBRID_SEARCH": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        "TOP_K_RERANKER": request.app.state.config.TOP_K_RERANKER,
        "RELEVANCE_THRESHOLD": request.app.state.config.RELEVANCE_THRESHOLD,
        # Content extraction settings
        "CONTENT_EXTRACTION_ENGINE": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
        "PDF_EXTRACT_IMAGES": request.app.state.config.PDF_EXTRACT_IMAGES,
        "EXTERNAL_DOCUMENT_LOADER_URL": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
        "EXTERNAL_DOCUMENT_LOADER_API_KEY": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        "TIKA_SERVER_URL": request.app.state.config.TIKA_SERVER_URL,
        "DOCLING_SERVER_URL": request.app.state.config.DOCLING_SERVER_URL,
        "DOCLING_OCR_ENGINE": request.app.state.config.DOCLING_OCR_ENGINE,
        "DOCLING_OCR_LANG": request.app.state.config.DOCLING_OCR_LANG,
        "DOCLING_DO_PICTURE_DESCRIPTION": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
        "DOCUMENT_INTELLIGENCE_ENDPOINT": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        "DOCUMENT_INTELLIGENCE_KEY": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
        "MISTRAL_OCR_API_KEY": request.app.state.config.MISTRAL_OCR_API_KEY,
        # Reranking settings
        "RAG_RERANKING_MODEL": request.app.state.config.RAG_RERANKING_MODEL,
        "RAG_RERANKING_ENGINE": request.app.state.config.RAG_RERANKING_ENGINE,
        "RAG_EXTERNAL_RERANKER_URL": request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
        "RAG_EXTERNAL_RERANKER_API_KEY": request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
        # Chunking settings
        "TEXT_SPLITTER": request.app.state.config.TEXT_SPLITTER,
        "CHUNK_SIZE": request.app.state.config.CHUNK_SIZE,
        "CHUNK_OVERLAP": request.app.state.config.CHUNK_OVERLAP,
        # File upload settings
        "FILE_MAX_SIZE": request.app.state.config.FILE_MAX_SIZE,
        "FILE_MAX_COUNT": request.app.state.config.FILE_MAX_COUNT,
        "ALLOWED_FILE_EXTENSIONS": request.app.state.config.ALLOWED_FILE_EXTENSIONS,
        # Integration settings
        "ENABLE_GOOGLE_DRIVE_INTEGRATION": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        "ENABLE_ONEDRIVE_INTEGRATION": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        "web": {
            "ENABLE_WEB_SEARCH": request.app.state.config.ENABLE_WEB_SEARCH,
            "WEB_SEARCH_ENGINE": request.app.state.config.WEB_SEARCH_ENGINE,
            "WEB_SEARCH_TRUST_ENV": request.app.state.config.WEB_SEARCH_TRUST_ENV,
            "WEB_SEARCH_RESULT_COUNT": request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            "WEB_SEARCH_CONCURRENT_REQUESTS": request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            "WEB_SEARCH_DOMAIN_FILTER_LIST": request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            "SEARXNG_QUERY_URL": request.app.state.config.SEARXNG_QUERY_URL,
            "YACY_QUERY_URL": request.app.state.config.YACY_QUERY_URL,
            "YACY_USERNAME": request.app.state.config.YACY_USERNAME,
            "YACY_PASSWORD": request.app.state.config.YACY_PASSWORD,
            "GOOGLE_PSE_API_KEY": request.app.state.config.GOOGLE_PSE_API_KEY,
            "GOOGLE_PSE_ENGINE_ID": request.app.state.config.GOOGLE_PSE_ENGINE_ID,
            "BRAVE_SEARCH_API_KEY": request.app.state.config.BRAVE_SEARCH_API_KEY,
            "KAGI_SEARCH_API_KEY": request.app.state.config.KAGI_SEARCH_API_KEY,
            "MOJEEK_SEARCH_API_KEY": request.app.state.config.MOJEEK_SEARCH_API_KEY,
            "BOCHA_SEARCH_API_KEY": request.app.state.config.BOCHA_SEARCH_API_KEY,
            "SERPSTACK_API_KEY": request.app.state.config.SERPSTACK_API_KEY,
            "SERPSTACK_HTTPS": request.app.state.config.SERPSTACK_HTTPS,
            "SERPER_API_KEY": request.app.state.config.SERPER_API_KEY,
            "SERPLY_API_KEY": request.app.state.config.SERPLY_API_KEY,
            "TAVILY_API_KEY": request.app.state.config.TAVILY_API_KEY,
            "SEARCHAPI_API_KEY": request.app.state.config.SEARCHAPI_API_KEY,
            "SEARCHAPI_ENGINE": request.app.state.config.SEARCHAPI_ENGINE,
            "SERPAPI_API_KEY": request.app.state.config.SERPAPI_API_KEY,
            "SERPAPI_ENGINE": request.app.state.config.SERPAPI_ENGINE,
            "JINA_API_KEY": request.app.state.config.JINA_API_KEY,
            "BING_SEARCH_V7_ENDPOINT": request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            "BING_SEARCH_V7_SUBSCRIPTION_KEY": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            "EXA_API_KEY": request.app.state.config.EXA_API_KEY,
            "PERPLEXITY_API_KEY": request.app.state.config.PERPLEXITY_API_KEY,
            "SOUGOU_API_SID": request.app.state.config.SOUGOU_API_SID,
            "SOUGOU_API_SK": request.app.state.config.SOUGOU_API_SK,
            "WEB_LOADER_ENGINE": request.app.state.config.WEB_LOADER_ENGINE,
            "ENABLE_WEB_LOADER_SSL_VERIFICATION": request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            "PLAYWRIGHT_WS_URL": request.app.state.config.PLAYWRIGHT_WS_URL,
            "PLAYWRIGHT_TIMEOUT": request.app.state.config.PLAYWRIGHT_TIMEOUT,
            "FIRECRAWL_API_KEY": request.app.state.config.FIRECRAWL_API_KEY,
            "FIRECRAWL_API_BASE_URL": request.app.state.config.FIRECRAWL_API_BASE_URL,
            "TAVILY_EXTRACT_DEPTH": request.app.state.config.TAVILY_EXTRACT_DEPTH,
            "EXTERNAL_WEB_SEARCH_URL": request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
            "EXTERNAL_WEB_SEARCH_API_KEY": request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
            "EXTERNAL_WEB_LOADER_URL": request.app.state.config.EXTERNAL_WEB_LOADER_URL,
            "EXTERNAL_WEB_LOADER_API_KEY": request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY,
            "YOUTUBE_LOADER_LANGUAGE": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "YOUTUBE_LOADER_PROXY_URL": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
            "YOUTUBE_LOADER_TRANSLATION": request.app.state.YOUTUBE_LOADER_TRANSLATION,
        },
    }


class WebConfig(BaseModel):
    ENABLE_WEB_SEARCH: Optional[bool] = None
    WEB_SEARCH_ENGINE: Optional[str] = None
    WEB_SEARCH_TRUST_ENV: Optional[bool] = None
    WEB_SEARCH_RESULT_COUNT: Optional[int] = None
    WEB_SEARCH_CONCURRENT_REQUESTS: Optional[int] = None
    WEB_SEARCH_DOMAIN_FILTER_LIST: Optional[List[str]] = []
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    SEARXNG_QUERY_URL: Optional[str] = None
    YACY_QUERY_URL: Optional[str] = None
    YACY_USERNAME: Optional[str] = None
    YACY_PASSWORD: Optional[str] = None
    GOOGLE_PSE_API_KEY: Optional[str] = None
    GOOGLE_PSE_ENGINE_ID: Optional[str] = None
    BRAVE_SEARCH_API_KEY: Optional[str] = None
    KAGI_SEARCH_API_KEY: Optional[str] = None
    MOJEEK_SEARCH_API_KEY: Optional[str] = None
    BOCHA_SEARCH_API_KEY: Optional[str] = None
    SERPSTACK_API_KEY: Optional[str] = None
    SERPSTACK_HTTPS: Optional[bool] = None
    SERPER_API_KEY: Optional[str] = None
    SERPLY_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    SEARCHAPI_API_KEY: Optional[str] = None
    SEARCHAPI_ENGINE: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    SERPAPI_ENGINE: Optional[str] = None
    JINA_API_KEY: Optional[str] = None
    BING_SEARCH_V7_ENDPOINT: Optional[str] = None
    BING_SEARCH_V7_SUBSCRIPTION_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    SOUGOU_API_SID: Optional[str] = None
    SOUGOU_API_SK: Optional[str] = None
    WEB_LOADER_ENGINE: Optional[str] = None
    ENABLE_WEB_LOADER_SSL_VERIFICATION: Optional[bool] = None
    PLAYWRIGHT_WS_URL: Optional[str] = None
    PLAYWRIGHT_TIMEOUT: Optional[int] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_API_BASE_URL: Optional[str] = None
    TAVILY_EXTRACT_DEPTH: Optional[str] = None
    EXTERNAL_WEB_SEARCH_URL: Optional[str] = None
    EXTERNAL_WEB_SEARCH_API_KEY: Optional[str] = None
    EXTERNAL_WEB_LOADER_URL: Optional[str] = None
    EXTERNAL_WEB_LOADER_API_KEY: Optional[str] = None
    YOUTUBE_LOADER_LANGUAGE: Optional[List[str]] = None
    YOUTUBE_LOADER_PROXY_URL: Optional[str] = None
    YOUTUBE_LOADER_TRANSLATION: Optional[str] = None


class ConfigForm(BaseModel):
    # RAG settings
    RAG_TEMPLATE: Optional[str] = None
    TOP_K: Optional[int] = None
    BYPASS_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    RAG_FULL_CONTEXT: Optional[bool] = None

    # Hybrid search settings
    ENABLE_RAG_HYBRID_SEARCH: Optional[bool] = None
    TOP_K_RERANKER: Optional[int] = None
    RELEVANCE_THRESHOLD: Optional[float] = None

    # Content extraction settings
    CONTENT_EXTRACTION_ENGINE: Optional[str] = None
    PDF_EXTRACT_IMAGES: Optional[bool] = None
    EXTERNAL_DOCUMENT_LOADER_URL: Optional[str] = None
    EXTERNAL_DOCUMENT_LOADER_API_KEY: Optional[str] = None

    TIKA_SERVER_URL: Optional[str] = None
    DOCLING_SERVER_URL: Optional[str] = None
    DOCLING_OCR_ENGINE: Optional[str] = None
    DOCLING_OCR_LANG: Optional[str] = None
    DOCLING_DO_PICTURE_DESCRIPTION: Optional[bool] = None
    DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None
    MISTRAL_OCR_API_KEY: Optional[str] = None

    # Reranking settings
    RAG_RERANKING_MODEL: Optional[str] = None
    RAG_RERANKING_ENGINE: Optional[str] = None
    RAG_EXTERNAL_RERANKER_URL: Optional[str] = None
    RAG_EXTERNAL_RERANKER_API_KEY: Optional[str] = None

    # Chunking settings
    TEXT_SPLITTER: Optional[str] = None
    CHUNK_SIZE: Optional[int] = None
    CHUNK_OVERLAP: Optional[int] = None

    # File upload settings
    FILE_MAX_SIZE: Optional[int] = None
    FILE_MAX_COUNT: Optional[int] = None
    ALLOWED_FILE_EXTENSIONS: Optional[List[str]] = None

    # Integration settings
    ENABLE_GOOGLE_DRIVE_INTEGRATION: Optional[bool] = None
    ENABLE_ONEDRIVE_INTEGRATION: Optional[bool] = None

    # Web search settings
    web: Optional[WebConfig] = None


@router.post("/config/update")
async def update_rag_config(
    request: Request, form_data: ConfigForm, user=Depends(get_admin_user)
):
    # RAG settings
    request.app.state.config.RAG_TEMPLATE = (
        form_data.RAG_TEMPLATE
        if form_data.RAG_TEMPLATE is not None
        else request.app.state.config.RAG_TEMPLATE
    )
    request.app.state.config.TOP_K = (
        form_data.TOP_K
        if form_data.TOP_K is not None
        else request.app.state.config.TOP_K
    )
    request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL = (
        form_data.BYPASS_EMBEDDING_AND_RETRIEVAL
        if form_data.BYPASS_EMBEDDING_AND_RETRIEVAL is not None
        else request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
    )
    request.app.state.config.RAG_FULL_CONTEXT = (
        form_data.RAG_FULL_CONTEXT
        if form_data.RAG_FULL_CONTEXT is not None
        else request.app.state.config.RAG_FULL_CONTEXT
    )

    # Hybrid search settings
    request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = (
        form_data.ENABLE_RAG_HYBRID_SEARCH
        if form_data.ENABLE_RAG_HYBRID_SEARCH is not None
        else request.app.state.config.ENABLE_RAG_HYBRID_SEARCH
    )
    # Free up memory if hybrid search is disabled
    if not request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
        request.app.state.rf = None

    request.app.state.config.TOP_K_RERANKER = (
        form_data.TOP_K_RERANKER
        if form_data.TOP_K_RERANKER is not None
        else request.app.state.config.TOP_K_RERANKER
    )
    request.app.state.config.RELEVANCE_THRESHOLD = (
        form_data.RELEVANCE_THRESHOLD
        if form_data.RELEVANCE_THRESHOLD is not None
        else request.app.state.config.RELEVANCE_THRESHOLD
    )

    # Content extraction settings
    request.app.state.config.CONTENT_EXTRACTION_ENGINE = (
        form_data.CONTENT_EXTRACTION_ENGINE
        if form_data.CONTENT_EXTRACTION_ENGINE is not None
        else request.app.state.config.CONTENT_EXTRACTION_ENGINE
    )
    request.app.state.config.PDF_EXTRACT_IMAGES = (
        form_data.PDF_EXTRACT_IMAGES
        if form_data.PDF_EXTRACT_IMAGES is not None
        else request.app.state.config.PDF_EXTRACT_IMAGES
    )
    request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL = (
        form_data.EXTERNAL_DOCUMENT_LOADER_URL
        if form_data.EXTERNAL_DOCUMENT_LOADER_URL is not None
        else request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL
    )
    request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY = (
        form_data.EXTERNAL_DOCUMENT_LOADER_API_KEY
        if form_data.EXTERNAL_DOCUMENT_LOADER_API_KEY is not None
        else request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY
    )
    request.app.state.config.TIKA_SERVER_URL = (
        form_data.TIKA_SERVER_URL
        if form_data.TIKA_SERVER_URL is not None
        else request.app.state.config.TIKA_SERVER_URL
    )
    request.app.state.config.DOCLING_SERVER_URL = (
        form_data.DOCLING_SERVER_URL
        if form_data.DOCLING_SERVER_URL is not None
        else request.app.state.config.DOCLING_SERVER_URL
    )
    request.app.state.config.DOCLING_OCR_ENGINE = (
        form_data.DOCLING_OCR_ENGINE
        if form_data.DOCLING_OCR_ENGINE is not None
        else request.app.state.config.DOCLING_OCR_ENGINE
    )
    request.app.state.config.DOCLING_OCR_LANG = (
        form_data.DOCLING_OCR_LANG
        if form_data.DOCLING_OCR_LANG is not None
        else request.app.state.config.DOCLING_OCR_LANG
    )

    request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION = (
        form_data.DOCLING_DO_PICTURE_DESCRIPTION
        if form_data.DOCLING_DO_PICTURE_DESCRIPTION is not None
        else request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION
    )

    request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT = (
        form_data.DOCUMENT_INTELLIGENCE_ENDPOINT
        if form_data.DOCUMENT_INTELLIGENCE_ENDPOINT is not None
        else request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT
    )
    request.app.state.config.DOCUMENT_INTELLIGENCE_KEY = (
        form_data.DOCUMENT_INTELLIGENCE_KEY
        if form_data.DOCUMENT_INTELLIGENCE_KEY is not None
        else request.app.state.config.DOCUMENT_INTELLIGENCE_KEY
    )
    request.app.state.config.MISTRAL_OCR_API_KEY = (
        form_data.MISTRAL_OCR_API_KEY
        if form_data.MISTRAL_OCR_API_KEY is not None
        else request.app.state.config.MISTRAL_OCR_API_KEY
    )

    # Reranking settings
    request.app.state.config.RAG_RERANKING_ENGINE = (
        form_data.RAG_RERANKING_ENGINE
        if form_data.RAG_RERANKING_ENGINE is not None
        else request.app.state.config.RAG_RERANKING_ENGINE
    )

    request.app.state.config.RAG_EXTERNAL_RERANKER_URL = (
        form_data.RAG_EXTERNAL_RERANKER_URL
        if form_data.RAG_EXTERNAL_RERANKER_URL is not None
        else request.app.state.config.RAG_EXTERNAL_RERANKER_URL
    )

    request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY = (
        form_data.RAG_EXTERNAL_RERANKER_API_KEY
        if form_data.RAG_EXTERNAL_RERANKER_API_KEY is not None
        else request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY
    )

    log.info(
        f"Updating reranking model: {request.app.state.config.RAG_RERANKING_MODEL} to {form_data.RAG_RERANKING_MODEL}"
    )
    try:
        request.app.state.config.RAG_RERANKING_MODEL = form_data.RAG_RERANKING_MODEL

        try:
            request.app.state.rf = get_rf(
                request.app.state.config.RAG_RERANKING_ENGINE,
                request.app.state.config.RAG_RERANKING_MODEL,
                request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
                request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
                True,
            )
        except Exception as e:
            log.error(f"Error loading reranking model: {e}")
            request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = False
    except Exception as e:
        log.exception(f"Problem updating reranking model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )

    # Chunking settings
    request.app.state.config.TEXT_SPLITTER = (
        form_data.TEXT_SPLITTER
        if form_data.TEXT_SPLITTER is not None
        else request.app.state.config.TEXT_SPLITTER
    )
    request.app.state.config.CHUNK_SIZE = (
        form_data.CHUNK_SIZE
        if form_data.CHUNK_SIZE is not None
        else request.app.state.config.CHUNK_SIZE
    )
    request.app.state.config.CHUNK_OVERLAP = (
        form_data.CHUNK_OVERLAP
        if form_data.CHUNK_OVERLAP is not None
        else request.app.state.config.CHUNK_OVERLAP
    )

    # File upload settings
    request.app.state.config.FILE_MAX_SIZE = (
        form_data.FILE_MAX_SIZE
        if form_data.FILE_MAX_SIZE is not None
        else request.app.state.config.FILE_MAX_SIZE
    )
    request.app.state.config.FILE_MAX_COUNT = (
        form_data.FILE_MAX_COUNT
        if form_data.FILE_MAX_COUNT is not None
        else request.app.state.config.FILE_MAX_COUNT
    )
    request.app.state.config.ALLOWED_FILE_EXTENSIONS = (
        form_data.ALLOWED_FILE_EXTENSIONS
        if form_data.ALLOWED_FILE_EXTENSIONS is not None
        else request.app.state.config.ALLOWED_FILE_EXTENSIONS
    )

    # Integration settings
    request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = (
        form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION
        if form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION is not None
        else request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION
    )
    request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION = (
        form_data.ENABLE_ONEDRIVE_INTEGRATION
        if form_data.ENABLE_ONEDRIVE_INTEGRATION is not None
        else request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION
    )

    if form_data.web is not None:
        # Web search settings
        request.app.state.config.ENABLE_WEB_SEARCH = form_data.web.ENABLE_WEB_SEARCH
        request.app.state.config.WEB_SEARCH_ENGINE = form_data.web.WEB_SEARCH_ENGINE
        request.app.state.config.WEB_SEARCH_TRUST_ENV = (
            form_data.web.WEB_SEARCH_TRUST_ENV
        )
        request.app.state.config.WEB_SEARCH_RESULT_COUNT = (
            form_data.web.WEB_SEARCH_RESULT_COUNT
        )
        request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS = (
            form_data.web.WEB_SEARCH_CONCURRENT_REQUESTS
        )
        request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST = (
            form_data.web.WEB_SEARCH_DOMAIN_FILTER_LIST
        )
        request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
            form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
        )
        request.app.state.config.SEARXNG_QUERY_URL = form_data.web.SEARXNG_QUERY_URL
        request.app.state.config.YACY_QUERY_URL = form_data.web.YACY_QUERY_URL
        request.app.state.config.YACY_USERNAME = form_data.web.YACY_USERNAME
        request.app.state.config.YACY_PASSWORD = form_data.web.YACY_PASSWORD
        request.app.state.config.GOOGLE_PSE_API_KEY = form_data.web.GOOGLE_PSE_API_KEY
        request.app.state.config.GOOGLE_PSE_ENGINE_ID = (
            form_data.web.GOOGLE_PSE_ENGINE_ID
        )
        request.app.state.config.BRAVE_SEARCH_API_KEY = (
            form_data.web.BRAVE_SEARCH_API_KEY
        )
        request.app.state.config.KAGI_SEARCH_API_KEY = form_data.web.KAGI_SEARCH_API_KEY
        request.app.state.config.MOJEEK_SEARCH_API_KEY = (
            form_data.web.MOJEEK_SEARCH_API_KEY
        )
        request.app.state.config.BOCHA_SEARCH_API_KEY = (
            form_data.web.BOCHA_SEARCH_API_KEY
        )
        request.app.state.config.SERPSTACK_API_KEY = form_data.web.SERPSTACK_API_KEY
        request.app.state.config.SERPSTACK_HTTPS = form_data.web.SERPSTACK_HTTPS
        request.app.state.config.SERPER_API_KEY = form_data.web.SERPER_API_KEY
        request.app.state.config.SERPLY_API_KEY = form_data.web.SERPLY_API_KEY
        request.app.state.config.TAVILY_API_KEY = form_data.web.TAVILY_API_KEY
        request.app.state.config.SEARCHAPI_API_KEY = form_data.web.SEARCHAPI_API_KEY
        request.app.state.config.SEARCHAPI_ENGINE = form_data.web.SEARCHAPI_ENGINE
        request.app.state.config.SERPAPI_API_KEY = form_data.web.SERPAPI_API_KEY
        request.app.state.config.SERPAPI_ENGINE = form_data.web.SERPAPI_ENGINE
        request.app.state.config.JINA_API_KEY = form_data.web.JINA_API_KEY
        request.app.state.config.BING_SEARCH_V7_ENDPOINT = (
            form_data.web.BING_SEARCH_V7_ENDPOINT
        )
        request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY = (
            form_data.web.BING_SEARCH_V7_SUBSCRIPTION_KEY
        )
        request.app.state.config.EXA_API_KEY = form_data.web.EXA_API_KEY
        request.app.state.config.PERPLEXITY_API_KEY = form_data.web.PERPLEXITY_API_KEY
        request.app.state.config.SOUGOU_API_SID = form_data.web.SOUGOU_API_SID
        request.app.state.config.SOUGOU_API_SK = form_data.web.SOUGOU_API_SK

        # Web loader settings
        request.app.state.config.WEB_LOADER_ENGINE = form_data.web.WEB_LOADER_ENGINE
        request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION = (
            form_data.web.ENABLE_WEB_LOADER_SSL_VERIFICATION
        )
        request.app.state.config.PLAYWRIGHT_WS_URL = form_data.web.PLAYWRIGHT_WS_URL
        request.app.state.config.PLAYWRIGHT_TIMEOUT = form_data.web.PLAYWRIGHT_TIMEOUT
        request.app.state.config.FIRECRAWL_API_KEY = form_data.web.FIRECRAWL_API_KEY
        request.app.state.config.FIRECRAWL_API_BASE_URL = (
            form_data.web.FIRECRAWL_API_BASE_URL
        )
        request.app.state.config.EXTERNAL_WEB_SEARCH_URL = (
            form_data.web.EXTERNAL_WEB_SEARCH_URL
        )
        request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY = (
            form_data.web.EXTERNAL_WEB_SEARCH_API_KEY
        )
        request.app.state.config.EXTERNAL_WEB_LOADER_URL = (
            form_data.web.EXTERNAL_WEB_LOADER_URL
        )
        request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY = (
            form_data.web.EXTERNAL_WEB_LOADER_API_KEY
        )
        request.app.state.config.TAVILY_EXTRACT_DEPTH = (
            form_data.web.TAVILY_EXTRACT_DEPTH
        )
        request.app.state.config.YOUTUBE_LOADER_LANGUAGE = (
            form_data.web.YOUTUBE_LOADER_LANGUAGE
        )
        request.app.state.config.YOUTUBE_LOADER_PROXY_URL = (
            form_data.web.YOUTUBE_LOADER_PROXY_URL
        )
        request.app.state.YOUTUBE_LOADER_TRANSLATION = (
            form_data.web.YOUTUBE_LOADER_TRANSLATION
        )

    return {
        "status": True,
        # RAG settings
        "RAG_TEMPLATE": request.app.state.config.RAG_TEMPLATE,
        "TOP_K": request.app.state.config.TOP_K,
        "BYPASS_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        "ENABLE_RAG_HYBRID_SEARCH": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        "TOP_K_RERANKER": request.app.state.config.TOP_K_RERANKER,
        "RELEVANCE_THRESHOLD": request.app.state.config.RELEVANCE_THRESHOLD,
        # Content extraction settings
        "CONTENT_EXTRACTION_ENGINE": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
        "PDF_EXTRACT_IMAGES": request.app.state.config.PDF_EXTRACT_IMAGES,
        "EXTERNAL_DOCUMENT_LOADER_URL": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
        "EXTERNAL_DOCUMENT_LOADER_API_KEY": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        "TIKA_SERVER_URL": request.app.state.config.TIKA_SERVER_URL,
        "DOCLING_SERVER_URL": request.app.state.config.DOCLING_SERVER_URL,
        "DOCLING_OCR_ENGINE": request.app.state.config.DOCLING_OCR_ENGINE,
        "DOCLING_OCR_LANG": request.app.state.config.DOCLING_OCR_LANG,
        "DOCLING_DO_PICTURE_DESCRIPTION": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
        "DOCUMENT_INTELLIGENCE_ENDPOINT": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        "DOCUMENT_INTELLIGENCE_KEY": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
        "MISTRAL_OCR_API_KEY": request.app.state.config.MISTRAL_OCR_API_KEY,
        # Reranking settings
        "RAG_RERANKING_MODEL": request.app.state.config.RAG_RERANKING_MODEL,
        "RAG_RERANKING_ENGINE": request.app.state.config.RAG_RERANKING_ENGINE,
        "RAG_EXTERNAL_RERANKER_URL": request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
        "RAG_EXTERNAL_RERANKER_API_KEY": request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
        # Chunking settings
        "TEXT_SPLITTER": request.app.state.config.TEXT_SPLITTER,
        "CHUNK_SIZE": request.app.state.config.CHUNK_SIZE,
        "CHUNK_OVERLAP": request.app.state.config.CHUNK_OVERLAP,
        # File upload settings
        "FILE_MAX_SIZE": request.app.state.config.FILE_MAX_SIZE,
        "FILE_MAX_COUNT": request.app.state.config.FILE_MAX_COUNT,
        "ALLOWED_FILE_EXTENSIONS": request.app.state.config.ALLOWED_FILE_EXTENSIONS,
        # Integration settings
        "ENABLE_GOOGLE_DRIVE_INTEGRATION": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        "ENABLE_ONEDRIVE_INTEGRATION": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        "web": {
            "ENABLE_WEB_SEARCH": request.app.state.config.ENABLE_WEB_SEARCH,
            "WEB_SEARCH_ENGINE": request.app.state.config.WEB_SEARCH_ENGINE,
            "WEB_SEARCH_TRUST_ENV": request.app.state.config.WEB_SEARCH_TRUST_ENV,
            "WEB_SEARCH_RESULT_COUNT": request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            "WEB_SEARCH_CONCURRENT_REQUESTS": request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            "WEB_SEARCH_DOMAIN_FILTER_LIST": request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            "SEARXNG_QUERY_URL": request.app.state.config.SEARXNG_QUERY_URL,
            "YACY_QUERY_URL": request.app.state.config.YACY_QUERY_URL,
            "YACY_USERNAME": request.app.state.config.YACY_USERNAME,
            "YACY_PASSWORD": request.app.state.config.YACY_PASSWORD,
            "GOOGLE_PSE_API_KEY": request.app.state.config.GOOGLE_PSE_API_KEY,
            "GOOGLE_PSE_ENGINE_ID": request.app.state.config.GOOGLE_PSE_ENGINE_ID,
            "BRAVE_SEARCH_API_KEY": request.app.state.config.BRAVE_SEARCH_API_KEY,
            "KAGI_SEARCH_API_KEY": request.app.state.config.KAGI_SEARCH_API_KEY,
            "MOJEEK_SEARCH_API_KEY": request.app.state.config.MOJEEK_SEARCH_API_KEY,
            "BOCHA_SEARCH_API_KEY": request.app.state.config.BOCHA_SEARCH_API_KEY,
            "SERPSTACK_API_KEY": request.app.state.config.SERPSTACK_API_KEY,
            "SERPSTACK_HTTPS": request.app.state.config.SERPSTACK_HTTPS,
            "SERPER_API_KEY": request.app.state.config.SERPER_API_KEY,
            "SERPLY_API_KEY": request.app.state.config.SERPLY_API_KEY,
            "TAVILY_API_KEY": request.app.state.config.TAVILY_API_KEY,
            "SEARCHAPI_API_KEY": request.app.state.config.SEARCHAPI_API_KEY,
            "SEARCHAPI_ENGINE": request.app.state.config.SEARCHAPI_ENGINE,
            "SERPAPI_API_KEY": request.app.state.config.SERPAPI_API_KEY,
            "SERPAPI_ENGINE": request.app.state.config.SERPAPI_ENGINE,
            "JINA_API_KEY": request.app.state.config.JINA_API_KEY,
            "BING_SEARCH_V7_ENDPOINT": request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            "BING_SEARCH_V7_SUBSCRIPTION_KEY": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            "EXA_API_KEY": request.app.state.config.EXA_API_KEY,
            "PERPLEXITY_API_KEY": request.app.state.config.PERPLEXITY_API_KEY,
            "SOUGOU_API_SID": request.app.state.config.SOUGOU_API_SID,
            "SOUGOU_API_SK": request.app.state.config.SOUGOU_API_SK,
            "WEB_LOADER_ENGINE": request.app.state.config.WEB_LOADER_ENGINE,
            "ENABLE_WEB_LOADER_SSL_VERIFICATION": request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            "PLAYWRIGHT_WS_URL": request.app.state.config.PLAYWRIGHT_WS_URL,
            "PLAYWRIGHT_TIMEOUT": request.app.state.config.PLAYWRIGHT_TIMEOUT,
            "FIRECRAWL_API_KEY": request.app.state.config.FIRECRAWL_API_KEY,
            "FIRECRAWL_API_BASE_URL": request.app.state.config.FIRECRAWL_API_BASE_URL,
            "TAVILY_EXTRACT_DEPTH": request.app.state.config.TAVILY_EXTRACT_DEPTH,
            "EXTERNAL_WEB_SEARCH_URL": request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
            "EXTERNAL_WEB_SEARCH_API_KEY": request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
            "EXTERNAL_WEB_LOADER_URL": request.app.state.config.EXTERNAL_WEB_LOADER_URL,
            "EXTERNAL_WEB_LOADER_API_KEY": request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY,
            "YOUTUBE_LOADER_LANGUAGE": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "YOUTUBE_LOADER_PROXY_URL": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
            "YOUTUBE_LOADER_TRANSLATION": request.app.state.YOUTUBE_LOADER_TRANSLATION,
        },
    }


####################################
#
# Document process and retrieval
#
####################################


def save_docs_to_vector_db(
    request: Request,
    docs,
    collection_name,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
    user=None,
) -> bool:
    def _get_docs_info(docs: list[Document]) -> str:
        docs_info = set()

        # Trying to select relevant metadata identifying the document.
        for doc in docs:
            metadata = getattr(doc, "metadata", {})
            doc_name = metadata.get("name", "")
            if not doc_name:
                doc_name = metadata.get("title", "")
            if not doc_name:
                doc_name = metadata.get("source", "")
            if doc_name:
                docs_info.add(doc_name)

        return ", ".join(docs_info)

    log.info(
        f"save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}"
    )

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and "hash" in metadata:
        result = VECTOR_DB_CLIENT.query(
            collection_name=collection_name,
            filter={"hash": metadata["hash"]},
        )

        if result is not None:
            existing_doc_ids = result.ids[0]
            if existing_doc_ids:
                log.info(f"Document with hash {metadata['hash']} already exists")
                raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        elif request.app.state.config.TEXT_SPLITTER == "token":
            log.info(
                f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
            )

            tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
            text_splitter = TokenTextSplitter(
                encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        elif request.app.state.config.TEXT_SPLITTER == "content_aware":
            log.info("Using content-aware text splitter for intelligent document structure recognition")
            print(f"REFACTORED: Using CONTENT-AWARE text splitter for enhanced chunking")
            text_splitter = ContentAwareTextSplitter(
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                min_chunk_size=max(50, request.app.state.config.CHUNK_SIZE // 10),
                preserve_headers=True,
                add_start_index=True,
            )
        else:
            # DEFAULT TO CONTENT-AWARE for better document processing
            log.info("Using DEFAULT content-aware text splitter for enhanced document structure recognition")
            print(f"REFACTORED: Using DEFAULT CONTENT-AWARE text splitter (fallback from invalid option)")
            text_splitter = ContentAwareTextSplitter(
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                min_chunk_size=max(50, request.app.state.config.CHUNK_SIZE // 10),
                preserve_headers=True,
                add_start_index=True,
            )

        print(f"REFACTORED: Splitting {len(docs)} documents into content-aware chunks...")
        
        # Show original document info
        total_chars = sum(len(doc.page_content) for doc in docs)
        print(f"CONTENT-AWARE SPLITTING INFO:")
        print(f"  📊 Total documents: {len(docs)}")
        print(f"  📏 Total characters: {total_chars}")
        print(f"  ⚙️ Chunk settings: size={request.app.state.config.CHUNK_SIZE}, overlap={request.app.state.config.CHUNK_OVERLAP}")
        
        docs = text_splitter.split_documents(docs)
        
        # Show results and comparison
        final_chars = sum(len(doc.page_content) for doc in docs)
        print(f"REFACTORED: Content-aware splitting completed. Result: {len(docs)} chunks")
        print(f"CONTENT-AWARE SPLITTING RESULTS:")
        print(f"  📈 Final chunks: {len(docs)}")
        print(f"  📏 Total characters after chunking: {final_chars}")
        print(f"  📊 Average chunk size: {final_chars // len(docs) if docs else 0} characters")
        
        # Quick comparison with what basic splitting would produce
        if docs and len(docs) > 0:
            try:
                # Sample one document for comparison
                sample_doc = docs[0] if docs else None
                if sample_doc and len(sample_doc.page_content) > 200:
                    basic_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=request.app.state.config.CHUNK_SIZE,
                        chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                    )
                    basic_chunks = basic_splitter.split_text(sample_doc.page_content)
                    print(f"  🔄 Comparison (sample doc): Content-aware=1 chunk vs Basic={len(basic_chunks)} chunks")
            except:
                pass

    if len(docs) == 0:
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    texts = [doc.page_content for doc in docs]
    metadatas = [
        {
            **doc.metadata,
            **(metadata if metadata else {}),
            "embedding_config": json.dumps(
                {
                    "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
                    "model": request.app.state.config.RAG_EMBEDDING_MODEL,
                }
            ),
        }
        for doc in docs
    ]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if (
                isinstance(value, datetime)
                or isinstance(value, list)
                or isinstance(value, dict)
            ):
                metadata[key] = str(value)

    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            log.info(f"collection {collection_name} already exists")

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                log.info(f"deleting existing collection {collection_name}")
            elif add is False:
                log.info(
                    f"collection {collection_name} already exists, overwrite is False and add is False"
                )
                return True

        log.info(f"adding to collection {collection_name}")
        embedding_function = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_BASE_URL
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_API_KEY
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        embeddings = embedding_function(
            list(map(lambda x: x.replace("\n", " "), texts)),
            prefix=RAG_EMBEDDING_CONTENT_PREFIX,
            user=user,
        )

        items = [
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "vector": embeddings[idx],
                "metadata": metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        VECTOR_DB_CLIENT.insert(
            collection_name=collection_name,
            items=items,
        )

        return True
    except Exception as e:
        log.exception(e)
        raise e


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


@router.post("/process/file")
def process_file(
    request: Request,
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
):
    try:
        file = Files.get_file_by_id(form_data.file_id)

        collection_name = form_data.collection_name

        if collection_name is None:
            collection_name = f"file-{file.id}"

        if form_data.content:
            # Update the content in the file
            # Usage: /files/{file_id}/data/content/update, /files/ (audio file upload pipeline)

            try:
                # /files/{file_id}/data/content/update
                VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{file.id}")
            except:
                # Audio file upload pipeline
                pass

            # Clean the provided content before creating document
            cleaned_content = clean_text_for_vector_db(form_data.content.replace("<br/>", "\n"))
            
            docs = [
                Document(
                    page_content=cleaned_content,
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

            text_content = cleaned_content
        elif form_data.collection_name:
            # Check if the file has already been processed and save the content
            # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

            result = VECTOR_DB_CLIENT.query(
                collection_name=f"file-{file.id}", filter={"file_id": file.id}
            )

            if result is not None and len(result.ids[0]) > 0:
                docs = [
                    Document(
                        page_content=result.documents[0][idx],
                        metadata=result.metadatas[0][idx],
                    )
                    for idx, id in enumerate(result.ids[0])
                ]
                # Clean existing documents from vector DB
                docs = [clean_document_content(doc) for doc in docs]
            else:
                # Clean the file content before creating document
                raw_content = file.data.get("content", "")
                cleaned_content = clean_text_for_vector_db(raw_content)
                
                docs = [
                    Document(
                        page_content=cleaned_content,
                        metadata={
                            **file.meta,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                ]

            text_content = " ".join([doc.page_content for doc in docs])
        else:
                        # Process the file and save the content - RESPECT USER'S ENGINE CHOICE
            # Usage: /files/
            file_path = file.path
            if file_path:
                file_path = Storage.get_file(file_path)
                
                # Respect user's choice of content extraction engine
                # When empty/default, use Unstructured.io as the DEFAULT engine
                engine = request.app.state.config.CONTENT_EXTRACTION_ENGINE
                
                if not engine or engine.lower() in ["default", ""]:
                    engine_display = "DEFAULT (Unstructured.io)"
                    actual_engine = ""  # Empty string triggers Unstructured.io default
                else:
                    engine_display = engine.upper()
                    actual_engine = engine
                
                print(f"REFACTORED: Processing file {file.filename} with {engine_display} engine")
                print(f"  📋 User setting: '{request.app.state.config.CONTENT_EXTRACTION_ENGINE}'")
                print(f"  ⚙️ Actual engine: '{actual_engine}' (empty = Unstructured.io default)")
                
                # Build loader kwargs based on engine to avoid unnecessary API key loading
                loader_kwargs = {
                    "CHUNK_SIZE": request.app.state.config.CHUNK_SIZE,
                    "CHUNK_OVERLAP": request.app.state.config.CHUNK_OVERLAP,
                    "PDF_EXTRACT_IMAGES": request.app.state.config.PDF_EXTRACT_IMAGES,
                }
                
                # Only add engine-specific configurations when needed
                if actual_engine == "external":
                    loader_kwargs.update({
                        "EXTERNAL_DOCUMENT_LOADER_URL": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
                        "EXTERNAL_DOCUMENT_LOADER_API_KEY": request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
                        "MISTRAL_OCR_API_KEY": request.app.state.config.MISTRAL_OCR_API_KEY,
                    })
                elif actual_engine == "tika":
                    loader_kwargs["TIKA_SERVER_URL"] = request.app.state.config.TIKA_SERVER_URL
                elif actual_engine == "docling":
                    loader_kwargs.update({
                        "DOCLING_SERVER_URL": request.app.state.config.DOCLING_SERVER_URL,
                        "DOCLING_OCR_ENGINE": request.app.state.config.DOCLING_OCR_ENGINE,
                        "DOCLING_OCR_LANG": request.app.state.config.DOCLING_OCR_LANG,
                        "DOCLING_DO_PICTURE_DESCRIPTION": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
                    })
                elif actual_engine == "document_intelligence":
                    loader_kwargs.update({
                        "DOCUMENT_INTELLIGENCE_ENDPOINT": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                        "DOCUMENT_INTELLIGENCE_KEY": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
                    })
                elif actual_engine == "mistral_ocr":
                    loader_kwargs["MISTRAL_OCR_API_KEY"] = request.app.state.config.MISTRAL_OCR_API_KEY
                # For default/empty engine (Unstructured.io), no additional configs needed
                
                loader = Loader(engine=actual_engine, **loader_kwargs)
                
                print(f"REFACTORED: Loading file with {engine_display}...")
                docs = loader.load(
                    file.filename, file.meta.get("content_type"), file_path
                )
                
                print(f"REFACTORED: Loaded {len(docs)} documents, applying comprehensive cleaning...")
                
                # Apply comprehensive cleaning to all extracted documents
                docs = [
                    Document(
                        page_content=clean_text_for_vector_db(doc.page_content),
                        metadata={
                            # Clean metadata to remove null values (Pinecone compatibility)
                            **{k: v for k, v in doc.metadata.items() if v is not None},
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                    for doc in docs
                ]
                
                print(f"REFACTORED: Document cleaning completed")
            else:
                # Fallback: clean existing file content
                raw_content = file.data.get("content", "")
                cleaned_content = clean_text_for_vector_db(raw_content)
                
                docs = [
                    Document(
                        page_content=cleaned_content,
                        metadata={
                            # Clean metadata to remove null values (Pinecone compatibility)
                            **{k: v for k, v in file.meta.items() if v is not None},
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                ]
            text_content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {text_content}")
        Files.update_file_data_by_id(
            file.id,
            {"content": text_content},
        )

        hash = calculate_sha256_string(text_content)
        Files.update_file_hash_by_id(file.id, hash)

        if not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
            try:
                result = save_docs_to_vector_db(
                    request,
                    docs=docs,
                    collection_name=collection_name,
                    metadata={
                        "file_id": file.id,
                        "name": file.filename,
                        "hash": hash,
                    },
                    add=(True if form_data.collection_name else False),
                    user=user,
                )

                if result:
                    Files.update_file_metadata_by_id(
                        file.id,
                        {
                            "collection_name": collection_name,
                        },
                    )

                    return {
                        "status": True,
                        "collection_name": collection_name,
                        "filename": file.filename,
                        "content": text_content,
                    }
            except Exception as e:
                raise e
        else:
            return {
                "status": True,
                "collection_name": None,
                "filename": file.filename,
                "content": text_content,
            }

    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )


class ProcessTextForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


@router.post("/process/text")
def process_text(
    request: Request,
    form_data: ProcessTextForm,
    user=Depends(get_verified_user),
):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)

    # Clean the text content before creating document
    cleaned_content = clean_text_for_vector_db(form_data.content)
    
    docs = [
        Document(
            page_content=cleaned_content,
            metadata={"name": form_data.name, "created_by": user.id},
        )
    ]
    text_content = cleaned_content
    log.debug(f"text_content: {text_content}")

    result = save_docs_to_vector_db(request, docs, collection_name, user=user)
    if result:
        return {
            "status": True,
            "collection_name": collection_name,
            "content": text_content,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post("/process/youtube")
def process_youtube_video(
    request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = YoutubeLoader(
            form_data.url,
            language=request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            proxy_url=request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
        )

        docs = loader.load()
        
        # Apply comprehensive cleaning to YouTube transcript content
        docs = [clean_document_content(doc) for doc in docs]
        
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")

        save_docs_to_vector_db(
            request, docs, collection_name, overwrite=True, user=user
        )

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/process/web")
def process_web(
    request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = get_web_loader(
            form_data.url,
            verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
        )
        docs = loader.load()
        
        # Apply comprehensive cleaning to web content
        docs = [clean_document_content(doc) for doc in docs]
        
        content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {content}")

        if not request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
            save_docs_to_vector_db(
                request, docs, collection_name, overwrite=True, user=user
            )
        else:
            collection_name = None

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                    "source": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def search_web(request: Request, engine: str, query: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - YACY_QUERY_URL + YACY_USERNAME + YACY_PASSWORD
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - KAGI_SEARCH_API_KEY
    - MOJEEK_SEARCH_API_KEY
    - BOCHA_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    - EXA_API_KEY
    - PERPLEXITY_API_KEY
    - SOUGOU_API_SID + SOUGOU_API_SK
    - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default `google`)
    - SERPAPI_API_KEY + SERPAPI_ENGINE (by default `google`)
    Args:
        query (str): The query to search for
    """

    # TODO: add playwright to search the web
    if engine == "searxng":
        if request.app.state.config.SEARXNG_QUERY_URL:
            return search_searxng(
                request.app.state.config.SEARXNG_QUERY_URL,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARXNG_QUERY_URL found in environment variables")
    elif engine == "yacy":
        if request.app.state.config.YACY_QUERY_URL:
            return search_yacy(
                request.app.state.config.YACY_QUERY_URL,
                request.app.state.config.YACY_USERNAME,
                request.app.state.config.YACY_PASSWORD,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No YACY_QUERY_URL found in environment variables")
    elif engine == "google_pse":
        if (
            request.app.state.config.GOOGLE_PSE_API_KEY
            and request.app.state.config.GOOGLE_PSE_ENGINE_ID
        ):
            return search_google_pse(
                request.app.state.config.GOOGLE_PSE_API_KEY,
                request.app.state.config.GOOGLE_PSE_ENGINE_ID,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
            )
    elif engine == "brave":
        if request.app.state.config.BRAVE_SEARCH_API_KEY:
            return search_brave(
                request.app.state.config.BRAVE_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
    elif engine == "kagi":
        if request.app.state.config.KAGI_SEARCH_API_KEY:
            return search_kagi(
                request.app.state.config.KAGI_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No KAGI_SEARCH_API_KEY found in environment variables")
    elif engine == "mojeek":
        if request.app.state.config.MOJEEK_SEARCH_API_KEY:
            return search_mojeek(
                request.app.state.config.MOJEEK_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No MOJEEK_SEARCH_API_KEY found in environment variables")
    elif engine == "bocha":
        if request.app.state.config.BOCHA_SEARCH_API_KEY:
            return search_bocha(
                request.app.state.config.BOCHA_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No BOCHA_SEARCH_API_KEY found in environment variables")
    elif engine == "serpstack":
        if request.app.state.config.SERPSTACK_API_KEY:
            return search_serpstack(
                request.app.state.config.SERPSTACK_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=request.app.state.config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception("No SERPSTACK_API_KEY found in environment variables")
    elif engine == "serper":
        if request.app.state.config.SERPER_API_KEY:
            return search_serper(
                request.app.state.config.SERPER_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPER_API_KEY found in environment variables")
    elif engine == "serply":
        if request.app.state.config.SERPLY_API_KEY:
            return search_serply(
                request.app.state.config.SERPLY_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPLY_API_KEY found in environment variables")
    elif engine == "duckduckgo":
        return search_duckduckgo(
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "tavily":
        if request.app.state.config.TAVILY_API_KEY:
            return search_tavily(
                request.app.state.config.TAVILY_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No TAVILY_API_KEY found in environment variables")
    elif engine == "searchapi":
        if request.app.state.config.SEARCHAPI_API_KEY:
            return search_searchapi(
                request.app.state.config.SEARCHAPI_API_KEY,
                request.app.state.config.SEARCHAPI_ENGINE,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARCHAPI_API_KEY found in environment variables")
    elif engine == "serpapi":
        if request.app.state.config.SERPAPI_API_KEY:
            return search_serpapi(
                request.app.state.config.SERPAPI_API_KEY,
                request.app.state.config.SERPAPI_ENGINE,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPAPI_API_KEY found in environment variables")
    elif engine == "jina":
        return search_jina(
            request.app.state.config.JINA_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
        )
    elif engine == "bing":
        return search_bing(
            request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            str(DEFAULT_LOCALE),
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "exa":
        return search_exa(
            request.app.state.config.EXA_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "perplexity":
        return search_perplexity(
            request.app.state.config.PERPLEXITY_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "sougou":
        if (
            request.app.state.config.SOUGOU_API_SID
            and request.app.state.config.SOUGOU_API_SK
        ):
            return search_sougou(
                request.app.state.config.SOUGOU_API_SID,
                request.app.state.config.SOUGOU_API_SK,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                "No SOUGOU_API_SID or SOUGOU_API_SK found in environment variables"
            )
    elif engine == "firecrawl":
        return search_firecrawl(
            request.app.state.config.FIRECRAWL_API_BASE_URL,
            request.app.state.config.FIRECRAWL_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "external":
        return search_external(
            request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
            request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    else:
        raise Exception("No search engine API key found in environment variables")


@router.post("/process/web/search")
async def process_web_search(
    request: Request, form_data: SearchForm, user=Depends(get_verified_user)
):

    urls = []
    try:
        logging.info(
            f"trying to web search with {request.app.state.config.WEB_SEARCH_ENGINE, form_data.queries}"
        )

        search_tasks = [
            run_in_threadpool(
                search_web,
                request,
                request.app.state.config.WEB_SEARCH_ENGINE,
                query,
            )
            for query in form_data.queries
        ]

        search_results = await asyncio.gather(*search_tasks)

        for result in search_results:
            if result:
                for item in result:
                    if item and item.link:
                        urls.append(item.link)

        urls = list(dict.fromkeys(urls))
        log.debug(f"urls: {urls}")

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    try:
        loader = get_web_loader(
            urls,
            verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            trust_env=request.app.state.config.WEB_SEARCH_TRUST_ENV,
        )
        docs = await loader.aload()
        
        # Apply comprehensive cleaning to web search content
        docs = [clean_document_content(doc) for doc in docs]
        
        urls = [
            doc.metadata.get("source") for doc in docs if doc.metadata.get("source")
        ]  # only keep the urls returned by the loader

        if request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
            return {
                "status": True,
                "collection_name": None,
                "filenames": urls,
                "docs": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                    }
                    for doc in docs
                ],
                "loaded_count": len(docs),
            }
        else:
            # Create a single collection for all documents
            collection_name = (
                f"web-search-{calculate_sha256_string('-'.join(form_data.queries))}"[
                    :63
                ]
            )

            try:
                await run_in_threadpool(
                    save_docs_to_vector_db,
                    request,
                    docs,
                    collection_name,
                    overwrite=True,
                    user=user,
                )
            except Exception as e:
                log.debug(f"error saving docs: {e}")

            return {
                "status": True,
                "collection_names": [collection_name],
                "filenames": urls,
                "loaded_count": len(docs),
            }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    k_reranker: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post("/query/doc")
def query_doc_handler(
    request: Request,
    form_data: QueryDocForm,
    user=Depends(get_verified_user),
):
    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            collection_results = {}
            collection_results[form_data.collection_name] = VECTOR_DB_CLIENT.get(
                collection_name=form_data.collection_name
            )
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                collection_result=collection_results[form_data.collection_name],
                query=form_data.query,
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=request.app.state.rf,
                k_reranker=form_data.k_reranker
                or request.app.state.config.TOP_K_RERANKER,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
                user=user,
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query_embedding=request.app.state.EMBEDDING_FUNCTION(
                    form_data.query, prefix=RAG_EMBEDDING_QUERY_PREFIX, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                user=user,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: Optional[int] = None
    k_reranker: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post("/query/collection")
def query_collection_handler(
    request: Request,
    form_data: QueryCollectionsForm,
    user=Depends(get_verified_user),
):
    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=request.app.state.rf,
                k_reranker=form_data.k_reranker
                or request.app.state.config.TOP_K_RERANKER,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


####################################
#
# Vector DB operations
#
####################################


class DeleteForm(BaseModel):
    collection_name: str
    file_id: str


@router.post("/delete")
def delete_entries_from_collection(form_data: DeleteForm, user=Depends(get_admin_user)):
    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=form_data.collection_name):
            file = Files.get_file_by_id(form_data.file_id)
            hash = file.hash

            VECTOR_DB_CLIENT.delete(
                collection_name=form_data.collection_name,
                metadata={"hash": hash},
            )
            return {"status": True}
        else:
            return {"status": False}
    except Exception as e:
        log.exception(e)
        return {"status": False}


@router.post("/reset/db")
def reset_vector_db(user=Depends(get_admin_user)):
    VECTOR_DB_CLIENT.reset()
    Knowledges.delete_all_knowledge()


@router.post("/reset/uploads")
def reset_upload_dir(user=Depends(get_admin_user)) -> bool:
    folder = f"{UPLOAD_DIR}"
    try:
        # Check if the directory exists
        if os.path.exists(folder):
            # Iterate over all the files and directories in the specified directory
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f"Failed to delete {file_path}. Reason: {e}")
        else:
            log.warning(f"The directory {folder} does not exist")
    except Exception as e:
        log.exception(f"Failed to process the directory {folder}. Reason: {e}")
    return True


if ENV == "dev":

    @router.get("/ef/{text}")
    async def get_embeddings(request: Request, text: Optional[str] = "Hello World!"):
        return {
            "result": request.app.state.EMBEDDING_FUNCTION(
                text, prefix=RAG_EMBEDDING_QUERY_PREFIX
            )
        }


class BatchProcessFilesForm(BaseModel):
    files: List[FileModel]
    collection_name: str


class BatchProcessFilesResult(BaseModel):
    file_id: str
    status: str
    error: Optional[str] = None


class BatchProcessFilesResponse(BaseModel):
    results: List[BatchProcessFilesResult]
    errors: List[BatchProcessFilesResult]


@router.post("/process/files/batch")
def process_files_batch(
    request: Request,
    form_data: BatchProcessFilesForm,
    user=Depends(get_verified_user),
) -> BatchProcessFilesResponse:
    """
    Process a batch of files and save them to the vector database.
    """
    results: List[BatchProcessFilesResult] = []
    errors: List[BatchProcessFilesResult] = []
    collection_name = form_data.collection_name

    # Prepare all documents first
    all_docs: List[Document] = []
    for file in form_data.files:
        try:
            text_content = file.data.get("content", "")
            
            # Apply comprehensive cleaning to batch file content
            cleaned_content = clean_text_for_vector_db(text_content.replace("<br/>", "\n"))

            docs: List[Document] = [
                Document(
                    page_content=cleaned_content,
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

            hash = calculate_sha256_string(cleaned_content)
            Files.update_file_hash_by_id(file.id, hash)
            Files.update_file_data_by_id(file.id, {"content": cleaned_content})

            all_docs.extend(docs)
            results.append(BatchProcessFilesResult(file_id=file.id, status="prepared"))

        except Exception as e:
            log.error(f"process_files_batch: Error processing file {file.id}: {str(e)}")
            errors.append(
                BatchProcessFilesResult(file_id=file.id, status="failed", error=str(e))
            )

    # Save all documents in one batch
    if all_docs:
        try:
            save_docs_to_vector_db(
                request=request,
                docs=all_docs,
                collection_name=collection_name,
                add=True,
                user=user,
            )

            # Update all files with collection name
            for result in results:
                Files.update_file_metadata_by_id(
                    result.file_id, {"collection_name": collection_name}
                )
                result.status = "completed"

        except Exception as e:
            log.error(
                f"process_files_batch: Error saving documents to vector DB: {str(e)}"
            )
            for result in results:
                result.status = "failed"
                errors.append(
                    BatchProcessFilesResult(file_id=result.file_id, error=str(e))
                )

    return BatchProcessFilesResponse(results=results, errors=errors)
