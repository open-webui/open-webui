"""
Gmail Attachment Processor

Processes email attachments using unstructured.io for content extraction.
Integrates with Gmail sync to make attachments searchable.
"""

import logging
import tempfile
import os
import asyncio
import concurrent.futures
from typing import Optional, List, Dict
from pathlib import Path

from open_webui.utils.temp_cleanup import ensure_cache_space

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Thread pool for CPU-bound attachment processing (prevents blocking event loop)
_ATTACHMENT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="gmail_att")


class GmailAttachmentProcessor:
    """
    Process email attachments using unstructured.io.

    Supports:
    - PDFs (with OCR)
    - Office documents (Word, Excel, PowerPoint)
    - Text files, CSV, Markdown
    - Images (with OCR)
    - And more via unstructured.io
    """

    def __init__(
        self,
        max_size_mb: int = 10,
        allowed_extensions: str = ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.csv,.md,.html,.eml",
    ):
        """
        Initialize attachment processor.

        Args:
            max_size_mb: Maximum attachment size to process (in MB)
            allowed_extensions: Comma-separated list of allowed file extensions
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = [ext.strip().lower() for ext in allowed_extensions.split(",")]

        logger.info(f"GmailAttachmentProcessor initialized: max_size={max_size_mb}MB")
        logger.info(f"Allowed types: {', '.join(self.allowed_extensions)}")

    def is_processable(self, filename: str, size: int) -> bool:
        """
        Check if attachment should be processed.

        Args:
            filename: Attachment filename
            size: Attachment size in bytes

        Returns:
            True if attachment meets criteria for processing
        """
        # Check size
        if size > self.max_size_bytes:
            logger.debug(f"Skipping '{filename}': too large ({size} bytes > {self.max_size_bytes})")
            return False

        # Check extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            logger.debug(f"Skipping '{filename}': extension '{file_ext}' not in allowed list")
            return False

        return True

    async def process_attachment(
        self, attachment_data: bytes, filename: str, email_id: str
    ) -> Optional[Dict[str, any]]:
        """
        Extract text content from attachment using unstructured.io.

        Args:
            attachment_data: Raw attachment bytes
            filename: Attachment filename
            email_id: Email ID (for logging/tracking)

        Returns:
            Dict with extracted text and metadata, or None if processing failed
        """
        try:
            # Import unstructured loader
            from open_webui.retrieval.loaders.unstructured_loader import UnstructuredUnifiedLoader

            # Ensure cache space before creating temp files (prevents /tmp overflow on Render)
            # Estimate needed space: attachment size + some processing overhead
            needed_mb = max(10, len(attachment_data) // (1024 * 1024) + 5)
            ensure_cache_space(required_mb=needed_mb)

            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(filename).suffix, prefix=f"gmail_att_{email_id[:8]}_"
            ) as temp_file:
                temp_file.write(attachment_data)
                temp_path = temp_file.name

            try:
                # Process with unstructured.io
                logger.info(f"Processing attachment '{filename}' ({len(attachment_data)} bytes) with unstructured.io")

                # Run synchronous document loading in thread executor to prevent blocking event loop
                # This is critical for keeping the server responsive during large attachment processing
                def _load_document_sync():
                    loader = UnstructuredUnifiedLoader(
                        file_path=temp_path,
                        # Use fast strategy for attachments (performance over quality)
                        strategy="fast",
                        # Use basic chunking for attachments
                        chunking_strategy="basic",
                        max_characters=1000,  # Smaller chunks for attachments
                        chunk_overlap=100,
                        cleaning_level="standard",  # Standard cleaning
                    )
                    return loader.load()

                # Extract documents in thread pool (non-blocking)
                loop = asyncio.get_running_loop()
                documents = await loop.run_in_executor(_ATTACHMENT_EXECUTOR, _load_document_sync)

                # Yield to event loop after heavy processing
                await asyncio.sleep(0)

                if not documents:
                    logger.warning(f"No content extracted from '{filename}'")
                    return None

                # Combine all chunks into single text
                extracted_text = "\n\n".join([doc.page_content for doc in documents])

                # Extract metadata from first document
                metadata = documents[0].metadata if documents else {}

                logger.info(f"Extracted {len(extracted_text)} chars from '{filename}'")

                return {
                    "filename": filename,
                    "text": extracted_text,
                    "char_count": len(extracted_text),
                    "chunk_count": len(documents),
                    "file_type": Path(filename).suffix.lower(),
                    "metadata": metadata,
                }

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_path}: {e}")

        except Exception as e:
            logger.error(f"Error processing attachment '{filename}': {e}")
            return None

    async def process_attachments_batch(self, attachments_info: List[Dict], fetcher, email_id: str) -> List[Dict]:
        """
        Process multiple attachments in batch.

        Args:
            attachments_info: List of attachment metadata from gmail_processor
            fetcher: GmailFetcher instance for downloading
            email_id: Email ID

        Returns:
            List of processed attachment results
        """
        processed = []

        for att_info in attachments_info:
            filename = att_info.get("filename", "")
            size = att_info.get("size", 0)
            attachment_id = att_info.get("attachmentId")

            # Check if should process
            if not self.is_processable(filename, size):
                continue

            # Download attachment
            logger.info(f"Downloading attachment '{filename}' from email {email_id[:8]}...")
            attachment_data = await fetcher.fetch_attachment(email_id, attachment_id, filename)

            if not attachment_data:
                logger.warning(f"Failed to download '{filename}'")
                continue

            # Process attachment
            result = await self.process_attachment(attachment_data, filename, email_id)

            if result:
                processed.append(result)
            else:
                logger.warning(f"Failed to process '{filename}'")

        logger.info(f"Processed {len(processed)}/{len(attachments_info)} attachments for email {email_id[:8]}")
        return processed
