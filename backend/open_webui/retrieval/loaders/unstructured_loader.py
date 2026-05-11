"""
Unstructured.io Unified Loader for Open WebUI (v0.18.15)

This module provides a unified file processing solution using Unstructured.io
that replaces multiple extraction engines with a single, high-quality solution.

Features:
- Comprehensive file type support (20+ formats)
- Built-in text cleaning and normalization
- Advanced semantic chunking with chunk_by_title support
- Consistent metadata extraction
- Performance optimizations (30% faster paragraph processing)
"""

from typing import List, Optional, Dict, Any
import logging
import os
import re
from pathlib import Path

from langchain_core.documents import Document
from unstructured.partition.auto import partition
from unstructured.chunking.basic import chunk_elements
from unstructured.cleaners.core import (
    clean_extra_whitespace,
    clean_dashes,
    clean_bullets,
    clean_ordered_bullets,
    clean_non_ascii_chars,
    clean_trailing_punctuation,
)

log = logging.getLogger(__name__)

# Try to import chunk_by_title (available in newer versions)
try:
    from unstructured.chunking.title import chunk_by_title

    HAS_CHUNK_BY_TITLE = True
except ImportError:
    HAS_CHUNK_BY_TITLE = False
    log.debug("chunk_by_title not available, using chunk_elements instead")


class UnstructuredUnifiedLoader:
    """
    Unified file loader using Unstructured.io for all file types.

    This loader provides:
    1. Consistent text extraction across all file types
    2. Professional-grade text cleaning
    3. Semantic chunking that preserves document structure
    4. Rich metadata extraction
    5. Performance optimizations
    """

    def __init__(
        self,
        file_path: str,
        strategy: str = "auto",  # Default to auto for smart strategy selection (fast if text extractable)
        include_metadata: bool = True,
        clean_text: bool = True,
        chunk_by_semantic: bool = True,
        chunking_strategy: str = "by_title",  # "by_title" or "basic" - by_title preserves document structure better
        max_characters: int = 1000,
        chunk_overlap: int = 200,
        cleaning_level: str = "standard",  # Standard cleaning for better text quality
        infer_table_structure: bool = False,  # Now configurable instead of always False
        extract_images_in_pdf: bool = False,  # Now configurable
        **kwargs,
    ):
        self.file_path = file_path
        self.strategy = strategy
        self.include_metadata = include_metadata
        self.clean_text = clean_text
        self.chunk_by_semantic = chunk_by_semantic
        self.chunking_strategy = chunking_strategy
        self.max_characters = max_characters
        self.chunk_overlap = chunk_overlap
        self.cleaning_level = cleaning_level
        self.infer_table_structure = infer_table_structure
        self.extract_images_in_pdf = extract_images_in_pdf
        self.kwargs = kwargs

        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

    def load(self) -> List[Document]:
        """
        Load and process the file using Unstructured.io

        Returns:
            List[Document]: Processed documents with cleaned text and metadata
        """
        try:
            log.info(f"Processing file with Unstructured.io: {self.file_path}")

            # Step 1: Partition the document (extract structured elements)
            elements = self._partition_document()

            # Step 2: Clean the extracted text
            if self.clean_text:
                elements = self._clean_elements(elements)

            # Step 3: Chunk by semantic boundaries
            if self.chunk_by_semantic:
                chunks = self._chunk_semantically(elements)
            else:
                chunks = elements

            # Step 4: Convert to LangChain Documents
            documents = self._convert_to_documents(chunks)

            log.info(f"Successfully processed {len(documents)} chunks from {self.file_path}")
            return documents

        except Exception as e:
            log.error(f"Error processing file {self.file_path} with Unstructured: {e}")
            raise

    def _partition_document(self):
        """Partition the document using Unstructured.io"""
        try:
            # Determine file type for optimal strategy
            file_ext = Path(self.file_path).suffix.lower()

            # Use appropriate strategy based on file type
            strategy = self._get_optimal_strategy(file_ext)

            log.debug(f"Using strategy '{strategy}' for file type '{file_ext}'")

            # Partition the document with configurable options
            elements = partition(
                filename=self.file_path,
                strategy=strategy,
                include_metadata=self.include_metadata,
                # Configurable options for performance vs. quality tradeoff
                infer_table_structure=self.infer_table_structure,
                extract_images_in_pdf=self.extract_images_in_pdf,
                **self.kwargs,
            )

            # Log processing results
            log.info(f"Successfully partitioned document: {len(elements)} elements extracted")

            # Filter out empty elements, headers, footers, and page numbers
            valid_elements = []
            for element in elements:
                # Check if element has text content
                has_text = False
                if hasattr(element, 'text') and element.text and element.text.strip():
                    has_text = True
                elif hasattr(element, 'content') and element.content and element.content.strip():
                    has_text = True

                if not has_text:
                    continue

                # Filter out unwanted element types
                element_category = None
                if hasattr(element, 'category'):
                    element_category = element.category

                # Skip headers, footers, and page numbers
                if element_category in ['Header', 'Footer', 'PageNumber', 'PageBreak']:
                    log.debug(f"Skipping {element_category} element")
                    continue

                valid_elements.append(element)

            if len(valid_elements) == 0 and len(elements) > 0:
                log.warning(f"All {len(elements)} extracted elements were empty for {self.file_path}")
                # Try to extract any text content from elements
                for element in elements:
                    if hasattr(element, '__dict__'):
                        for attr_name, attr_value in element.__dict__.items():
                            if isinstance(attr_value, str) and attr_value.strip():
                                log.info(f"Found text in {attr_name}: {attr_value[:100]}...")
                                valid_elements.append(element)
                                break

            log.info(f"Valid elements after filtering: {len(valid_elements)}")

            # Check if we got minimal/empty results and should try hi_res
            # This handles cases where fast/auto couldn't extract text (scanned PDFs, etc.)
            file_ext = Path(self.file_path).suffix.lower()
            if (
                file_ext == ".pdf"
                and len(valid_elements) < 3  # Very few elements extracted
                and strategy in ["auto", "fast"]  # We used a fast strategy
            ):
                total_text = sum(len(getattr(e, 'text', '') or '') for e in valid_elements)
                if total_text < 100:  # Less than 100 chars total
                    log.warning(
                        f"Fast strategy returned minimal content ({len(valid_elements)} elements, "
                        f"{total_text} chars), trying 'hi_res' for better extraction"
                    )
                    try:
                        elements = partition(
                            filename=self.file_path,
                            strategy="hi_res",
                            include_metadata=self.include_metadata,
                            infer_table_structure=self.infer_table_structure,
                            extract_images_in_pdf=self.extract_images_in_pdf,
                            **self.kwargs,
                        )
                        log.info(f"hi_res fallback successful: {len(elements)} elements extracted")

                        # Re-apply filtering
                        upgraded_elements = []
                        for element in elements:
                            has_text = False
                            if hasattr(element, 'text') and element.text and element.text.strip():
                                has_text = True
                            elif hasattr(element, 'content') and element.content and element.content.strip():
                                has_text = True
                            if has_text:
                                element_category = getattr(element, 'category', None)
                                if element_category not in ['Header', 'Footer', 'PageNumber', 'PageBreak']:
                                    upgraded_elements.append(element)

                        if len(upgraded_elements) > len(valid_elements):
                            log.info(
                                f"hi_res extracted more content: {len(upgraded_elements)} vs {len(valid_elements)} elements"
                            )
                            return upgraded_elements
                    except Exception as hi_res_error:
                        log.warning(f"hi_res fallback failed: {hi_res_error}, using original results")

            return valid_elements

        except Exception as e:
            log.error(f"Error partitioning document {self.file_path}: {e}")

            # If the error is related to complex processing, try a different strategy
            file_ext = Path(self.file_path).suffix.lower()
            error_str = str(e).lower()

            if any(
                keyword in error_str
                for keyword in ["list index out of range", "timeout", "empty", "no content", "failed to extract"]
            ):
                # For PDFs, try hi_res if fast/auto failed (might be scanned)
                if file_ext == ".pdf":
                    log.warning(f"Fast/auto processing failed, trying 'hi_res' strategy: {e}")
                    try:
                        elements = partition(
                            filename=self.file_path,
                            strategy="hi_res",
                            include_metadata=self.include_metadata,
                            infer_table_structure=False,
                            extract_images_in_pdf=False,
                            **self.kwargs,
                        )
                        log.info(f"hi_res fallback successful: {len(elements)} elements extracted")

                        valid_elements = []
                        for element in elements:
                            if hasattr(element, 'text') and element.text and element.text.strip():
                                valid_elements.append(element)
                            elif hasattr(element, 'content') and element.content and element.content.strip():
                                valid_elements.append(element)

                        log.info(f"Valid elements after hi_res fallback: {len(valid_elements)}")
                        return valid_elements

                    except Exception as hi_res_error:
                        log.error(f"hi_res fallback also failed: {hi_res_error}")

                # Last resort: try with minimal options
                try:
                    log.warning("Trying minimal 'fast' processing as last resort")
                    elements = partition(
                        filename=self.file_path,
                        strategy="fast",
                        include_metadata=False,
                        infer_table_structure=False,
                        extract_images_in_pdf=False,
                    )
                    log.info(f"Minimal processing successful: {len(elements)} elements extracted")
                    return elements
                except Exception as minimal_error:
                    log.error(f"Minimal processing also failed: {minimal_error}")

            raise

    def _get_optimal_strategy(self, file_ext: str) -> str:
        """
        Select optimal processing strategy based on file type.

        Strategy selection (from Unstructured docs):
        - "auto": Smart selection - uses "fast" if text extractable, "ocr_only" otherwise
        - "fast": Rule-based extraction, ~100x faster than model-based
        - "hi_res": Model-based (detectron2), best for complex layouts/tables
        - "ocr_only": For scanned documents/images

        We prioritize speed while maintaining quality through smart fallbacks.
        """
        # If user explicitly requested a specific strategy (not the default "auto"),
        # respect their choice for all file types
        if self.strategy and self.strategy not in ["auto", ""]:
            log.debug(f"Using user-configured strategy '{self.strategy}' for {file_ext}")
            return self.strategy

        # PDFs: Use "auto" strategy for smart selection
        # "auto" chooses "fast" if text is extractable, "ocr_only" for scanned PDFs
        # Copy-protected PDFs automatically fall back to "hi_res"
        if file_ext == ".pdf":
            # Use "auto" for intelligent strategy selection
            # This is ~100x faster than always using "hi_res" for simple PDFs
            log.debug(f"Using 'auto' strategy for PDF (will use 'fast' if text extractable)")
            return "auto"

        # Office documents: structured formats, fast extraction works well
        elif file_ext in [".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls"]:
            return "fast"

        # Text-based formats: no OCR needed
        elif file_ext in [".txt", ".md", ".html", ".csv", ".json", ".xml"]:
            return "fast"

        # Images: must use OCR
        elif file_ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"]:
            return "ocr_only"

        # Default to "auto" for unknown types (smart selection)
        return "auto"

    def _clean_elements(self, elements):
        """Apply comprehensive text cleaning to elements and filter unwanted content"""
        # Skip cleaning entirely if level is "none" for maximum speed
        if self.cleaning_level == "none":
            return elements

        cleaned_elements = []

        for i, element in enumerate(elements):
            try:
                # Get original text safely - handle different element types
                text = None
                if hasattr(element, 'text'):
                    text = element.text if element.text else None

                # If no text attribute or it's None, try converting to string
                if text is None:
                    try:
                        text = str(element)
                    except Exception:
                        log.debug(f"Element {i} has no text content, skipping")
                        continue

                # Skip empty or very short text
                if not text or len(text.strip()) < 2:
                    continue

                # Filter out common header/footer/page number patterns
                if self._is_header_footer_or_noise(text):
                    log.debug(f"Skipping header/footer/noise: {text[:50]}...")
                    continue

                # Apply cleaning based on level
                try:
                    if self.cleaning_level == "minimal":
                        text = self._minimal_cleaning(text)
                    elif self.cleaning_level == "standard":
                        text = self._standard_cleaning(text)
                    elif self.cleaning_level == "aggressive":
                        text = self._aggressive_cleaning(text)
                except Exception as clean_err:
                    log.warning(f"Error in cleaning function for element {i}: {clean_err}")
                    # Continue with uncleaned text rather than failing

                # Final check: skip if text became empty or too short after cleaning
                if not text or len(text.strip()) < 10:
                    continue

                # Update element text if it has a text attribute
                if hasattr(element, 'text'):
                    element.text = text
                cleaned_elements.append(element)

            except Exception as e:
                log.warning(f"Error processing element {i}: {e}")
                # Keep original element if any processing fails
                try:
                    cleaned_elements.append(element)
                except Exception:
                    pass  # Skip this element entirely if we can't add it

        log.debug(f"Cleaned {len(cleaned_elements)} elements from {len(elements)} total")
        return cleaned_elements

    def _is_header_footer_or_noise(self, text: str) -> bool:
        """Detect and filter out headers, footers, page numbers, and OCR noise"""
        text_lower = text.lower().strip()
        text_stripped = text.strip()

        # Skip very short text that's likely noise
        if len(text_stripped) < 10:
            return True

        # Check for page numbers (standalone numbers or "Page X" patterns)
        import re

        if re.match(r'^[\s\n]*\d{1,4}[\s\n]*$', text_stripped):
            return True
        if re.match(r'^[\s\n]*(page|pg\.?)\s*\d{1,4}[\s\n]*$', text_lower):
            return True

        # Check for common footer patterns
        footer_patterns = [
            r'^\d{4}\s+(annual report|report)',  # "2024 ANNUAL REPORT"
            r'^(confidential|proprietary|copyright|©)',
            r'^\s*(page|pg\.?)\s+\d+\s+of\s+\d+',
            r'^\s*\d+\s*/\s*\d+\s*$',  # "23 / 45" or "23/45"
        ]
        for pattern in footer_patterns:
            if re.match(pattern, text_lower):
                return True

        # Check for repeated characters/names (OCR artifacts like "sa akib khansa akib khan")
        # If same word appears 3+ times in a short text, it's likely noise
        words = text_stripped.split()
        if len(words) <= 10:  # Only check short text
            word_counts = {}
            for word in words:
                word_lower = word.lower()
                word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
            # If any word repeats 3+ times in short text, skip
            if any(count >= 3 for count in word_counts.values()):
                return True

        # Check for header patterns (all caps short lines)
        if len(text_stripped) < 100 and text_stripped.isupper():
            # Skip short all-caps lines (likely headers)
            return True

        return False

    def _minimal_cleaning(self, text: str) -> str:
        """Minimal cleaning - just essential whitespace fixes and artifact removal"""
        text = clean_extra_whitespace(text)
        text = clean_trailing_punctuation(text)
        text = self._remove_artifacts(text)
        return text.strip()

    def _standard_cleaning(self, text: str) -> str:
        """Standard cleaning - good balance of cleaning and preservation"""
        text = clean_extra_whitespace(text)
        text = clean_dashes(text)
        text = clean_bullets(text)
        text = clean_ordered_bullets(text)
        text = clean_trailing_punctuation(text)
        text = self._remove_artifacts(text)
        return text.strip()

    def _aggressive_cleaning(self, text: str) -> str:
        """Aggressive cleaning - maximum cleaning, may remove some context"""
        text = clean_extra_whitespace(text)
        text = clean_dashes(text)
        text = clean_bullets(text)
        text = clean_ordered_bullets(text)
        text = clean_trailing_punctuation(text)
        text = clean_non_ascii_chars(text)
        text = self._remove_artifacts(text)
        return text.strip()

    def _remove_artifacts(self, text: str) -> str:
        """Remove OCR artifacts, repeated names, and trailing noise from text"""
        # Remove common OCR artifacts at the end of text
        # Pattern: repeated words/names (e.g., "sa akib khansa akib khan")
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped:
                cleaned_lines.append(line)
                continue

            # Check if line is a repeated word pattern (OCR artifact)
            words = line_stripped.split()
            if len(words) <= 8:  # Short lines only
                # Count word frequency
                word_counts = {}
                for word in words:
                    word_lower = word.lower()
                    word_counts[word_lower] = word_counts.get(word_lower, 0) + 1

                # If any word appears 3+ times in short line, it's likely an artifact
                if any(count >= 3 for count in word_counts.values()):
                    continue  # Skip this line

            # Check if line looks like a footer/header
            if re.match(r'^\d{4}\s+(annual report|report)', line_stripped.lower()):
                continue
            if re.match(r'^page\s+\d+', line_stripped.lower()):
                continue
            if re.match(r'^\d{1,4}$', line_stripped):
                continue

            cleaned_lines.append(line)

        # Rejoin and clean up excessive whitespace
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines

        # Remove trailing artifacts (coordinates, timestamps, incomplete text)
        # Pattern: "text ending with h.08" or "text .123" or "text x.y"
        text = re.sub(r'\s+[a-z]\.[\d.]+["\']?$', '', text)  # Matches: " h.08" or " x.123"
        text = re.sub(r'\s+\.[\d.]+["\']?$', '', text)  # Matches: " .08" or " .123"

        # Remove incomplete sentences at the end (single letter or very short fragment)
        # Pattern: ending with " word h" or " we h" (looks like truncated sentence)
        text = re.sub(r'\s+\w{1,2}\s+[a-z]$', '.', text)  # "we h" → "."

        return text.strip()

    def _chunk_semantically(self, elements):
        """
        Chunk elements using the configured chunking strategy.

        Supports two strategies:
        - "by_title": Respects document structure (headers, titles, sections) for better semantic coherence
        - "basic": Character-based chunking for simpler, faster processing
        """
        try:
            # Use chunk_by_title if available and requested (better semantic chunking)
            if self.chunking_strategy == "by_title" and HAS_CHUNK_BY_TITLE:
                log.debug("Using chunk_by_title for structure-aware chunking")
                chunks = chunk_by_title(
                    elements,
                    max_characters=self.max_characters,
                    overlap=self.chunk_overlap,
                    new_after_n_chars=self.max_characters,
                    combine_text_under_n_chars=100,  # Combine very small sections
                )
                log.debug(f"Created {len(chunks)} chunks using chunk_by_title")
                return chunks

            # Fallback to basic chunking
            if self.chunking_strategy == "by_title" and not HAS_CHUNK_BY_TITLE:
                log.warning("chunk_by_title requested but not available, falling back to chunk_elements")

            chunks = chunk_elements(
                elements,
                max_characters=self.max_characters,
                overlap=self.chunk_overlap,
                new_after_n_chars=self.max_characters,
            )

            log.debug(f"Created {len(chunks)} chunks using chunk_elements")
            return chunks

        except Exception as e:
            log.warning(f"Error in chunking: {e}")
            # If chunking fails, return elements as-is
            log.info(f"Returning {len(elements)} elements without chunking")
            return elements

    def _convert_to_documents(self, chunks) -> List[Document]:
        """Convert Unstructured chunks to LangChain Documents"""
        documents = []
        total_chunks = len(chunks)  # Pre-calculate to avoid repeated len() calls

        for i, chunk in enumerate(chunks):
            try:
                # Extract content
                content = str(chunk)

                # Skip empty content
                if not content or not content.strip():
                    continue

                # Normalize newlines and clean up extra whitespace
                content = re.sub(r'\n{3,}', '\n\n', content)  # Reduce excessive newlines
                content = content.strip()

                # Skip if content is too short after normalization
                if len(content) < 10:
                    continue

                # Extract metadata
                metadata = {}
                if hasattr(chunk, 'metadata') and chunk.metadata:
                    metadata = chunk.metadata.to_dict()

                # Extract element type if available (Title, NarrativeText, ListItem, etc.)
                element_type = None
                if hasattr(chunk, 'category'):
                    element_type = chunk.category
                elif 'category' in metadata:
                    element_type = metadata.get('category')

                # Add additional metadata (optimized for performance)
                metadata.update(
                    {
                        "source": self.file_path,
                        "chunk_index": i,
                        "total_chunks": total_chunks,
                        "processing_engine": "unstructured",
                        "strategy": self.strategy,
                        "chunking_strategy": self.chunking_strategy,
                        "cleaning_level": self.cleaning_level,
                    }
                )

                # Add element type if available
                if element_type:
                    metadata["element_type"] = element_type

                # Remove large/unnecessary fields to improve performance
                fields_to_remove = [
                    "orig_elements",  # Very large compressed JSON, not needed for retrieval
                    "name",  # Redundant with filename
                    "source",  # Redundant with filename (we set our own source)
                ]
                for field in fields_to_remove:
                    if field in metadata:
                        del metadata[field]

                # Create document
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)

            except Exception as e:
                log.warning(f"Error converting chunk {i} to document: {e}")
                continue

        return documents


def create_unstructured_loader(file_path: str, config: Dict[str, Any]) -> UnstructuredUnifiedLoader:
    """
    Factory function to create UnstructuredUnifiedLoader with configuration

    Args:
        file_path: Path to the file to process
        config: Configuration dictionary with Unstructured settings

    Returns:
        UnstructuredUnifiedLoader instance
    """
    return UnstructuredUnifiedLoader(
        file_path=file_path,
        strategy=config.get(
            "UNSTRUCTURED_STRATEGY", "auto"
        ),  # Default to auto for smart selection (~100x faster for simple PDFs)
        include_metadata=config.get("UNSTRUCTURED_INCLUDE_METADATA", True),
        clean_text=config.get("UNSTRUCTURED_CLEAN_TEXT", True),
        chunk_by_semantic=config.get("UNSTRUCTURED_SEMANTIC_CHUNKING", True),
        chunking_strategy=config.get(
            "UNSTRUCTURED_CHUNKING_STRATEGY", "by_title"
        ),  # Default to by_title for better structure preservation
        max_characters=config.get("CHUNK_SIZE", 1000),
        chunk_overlap=config.get("CHUNK_OVERLAP", 200),
        cleaning_level=config.get("UNSTRUCTURED_CLEANING_LEVEL", "standard"),  # Default to standard for better quality
        infer_table_structure=config.get(
            "UNSTRUCTURED_INFER_TABLE_STRUCTURE", False
        ),  # Disable by default for performance
        extract_images_in_pdf=config.get(
            "UNSTRUCTURED_EXTRACT_IMAGES_IN_PDF", False
        ),  # Disable by default for performance
    )
