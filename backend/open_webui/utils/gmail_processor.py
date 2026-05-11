"""
Gmail Email Processor

This module provides email parsing and metadata extraction from Gmail API responses.
It's designed to work standalone without external dependencies (no Pinecone, no embeddings).

Purpose: Transform Gmail API JSON into clean, structured data ready for indexing.
"""

import base64
import hashlib
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple
from html import unescape

from open_webui.utils.email_cleaner import EmailCleaner

# Set up logger with INFO level for visibility
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GmailProcessor:
    """
    Processes Gmail API responses into structured email data.

    This is a pure data transformation class - no external API calls,
    no database operations, just parsing and cleaning.
    """

    def __init__(self):
        """Initialize the processor"""
        pass

    def parse_email(self, email_data: dict, user_id: str) -> Dict:
        """
        Parse a Gmail API message response into structured data.

        Args:
            email_data: Full Gmail API message response (format='full')
            user_id: User ID for metadata isolation

        Returns:
            Dict with parsed email data and metadata

        Example:
            >>> processor = GmailProcessor()
            >>> result = processor.parse_email(gmail_api_response, "user_123")
            >>> print(result["subject"])
            "Q4 Budget Discussion"
        """

        try:
            # Extract basic identifiers
            email_id = email_data.get("id", "")
            thread_id = email_data.get("threadId", "")

            if not email_id:
                raise ValueError("Email data missing 'id' field")

            # Extract headers
            headers_dict = self._extract_headers(email_data)

            # Extract core email fields
            subject = headers_dict.get("Subject", "(No Subject)")
            from_addr = headers_dict.get("From", "")
            to_addr = headers_dict.get("To", "")
            cc_addr = headers_dict.get("Cc", "")
            date_str = headers_dict.get("Date", "")

            # Parse date
            date_timestamp, date_readable = self._parse_date(date_str, email_data.get("internalDate"))

            # Extract email body
            payload = email_data.get("payload", {})
            body_raw = self._extract_body(payload)
            snippet = email_data.get("snippet", "")

            # Clean email body with advanced cleaning
            body_full_clean, body_original_only = EmailCleaner.clean_email_body(body_raw)

            # Use original message (no quotes/signatures) for primary content
            body_clean = body_original_only if body_original_only else body_full_clean

            # Extract labels
            labels = email_data.get("labelIds", [])

            # Extract attachment information
            attachments = self._get_attachments(payload)
            has_attachments = len(attachments) > 0

            # Parse email addresses
            from_name, from_email = EmailCleaner.parse_email_address(from_addr)
            to_name, to_email = EmailCleaner.parse_email_address(to_addr)

            # Detect if this is a reply
            is_reply = "RE:" in subject.upper() or "Re:" in subject or any(label == "SENT" for label in labels)

            # Create document text (what will be embedded) - cleaner format
            document_text = self._create_document_text(
                subject=subject,
                from_name=from_name,
                from_email=from_email,
                to_email=to_email,
                date_readable=date_readable,
                body=body_clean,
                snippet=snippet,
            )

            # Build metadata (improved structure for better search)
            metadata = {
                # Core identification
                "type": "email",
                "email_id": email_id,
                "thread_id": thread_id,
                "user_id": user_id,
                # Email fields (structured)
                "subject": subject,
                "from_name": from_name,
                "from_email": from_email,
                "from_raw": from_addr,  # Keep original for reference
                "to_name": to_name,
                "to_email": to_email,
                "to_raw": to_addr,
                "cc": cc_addr,
                "date": date_readable,
                "date_timestamp": date_timestamp,
                "labels": labels,  # Keep as array, not comma-separated string
                # Content metadata
                "has_attachments": has_attachments,
                "attachment_count": len(attachments),
                "is_reply": is_reply,
                "word_count": len(body_clean.split()),
                "body_length": len(body_clean),
                "original_body_length": len(body_raw),
                # Cleaned text fields
                "body_full_clean": body_full_clean,  # Full email with cleaned quotes
                "body_original": body_clean,  # Just the original message
                # Categorization
                "source": "gmail",
                "doc_type": "email",
                # Hash for deduplication
                "hash": hashlib.sha256(f"{email_id}{user_id}".encode()).hexdigest(),
            }

            return {
                "email_id": email_id,
                "thread_id": thread_id,
                "document_text": document_text,
                "metadata": metadata,
                "raw_body": body_raw,
                "cleaned_body": body_clean,
                "snippet": snippet,
                "attachments": attachments,  # List of attachment metadata
            }

        except Exception as e:
            logger.error(f"Error parsing email {email_data.get('id', 'unknown')}: {e}")
            raise

    def _extract_headers(self, email_data: dict) -> Dict[str, str]:
        """Extract email headers from Gmail API response"""

        payload = email_data.get("payload", {})
        headers_list = payload.get("headers", [])

        # Convert list of {name, value} to dict
        headers_dict = {}
        for header in headers_list:
            name = header.get("name", "")
            value = header.get("value", "")
            headers_dict[name] = value

        return headers_dict

    def _parse_date(self, date_str: str, internal_date: Optional[str] = None) -> Tuple[int, str]:
        """
        Parse email date into timestamp and readable format.

        Args:
            date_str: Date header from email (e.g., "Mon, 15 Nov 2020 14:30:00 +0000")
            internal_date: Gmail internal date (milliseconds since epoch)

        Returns:
            Tuple of (unix_timestamp, readable_date_string)
        """

        # Try to parse the Date header
        try:
            date_obj = parsedate_to_datetime(date_str)
            timestamp = int(date_obj.timestamp())
            readable = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            return timestamp, readable
        except Exception as e:
            logger.debug(f"Could not parse date '{date_str}': {e}")

        # Fallback to internal date
        if internal_date:
            try:
                timestamp = int(internal_date) // 1000  # Convert ms to seconds
                date_obj = datetime.fromtimestamp(timestamp)
                readable = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                return timestamp, readable
            except Exception as e:
                logger.debug(f"Could not parse internal date '{internal_date}': {e}")

        # Final fallback: current time
        now = int(datetime.now().timestamp())
        return now, "Unknown Date"

    def _extract_body(self, payload: dict) -> str:
        """
        Recursively extract email body from Gmail API payload.

        Handles:
        - Plain text emails
        - HTML emails (strips tags)
        - Multipart emails (multipart/alternative, multipart/mixed)
        - Nested MIME structures

        Args:
            payload: Gmail API message payload

        Returns:
            Extracted email body as plain text
        """

        # Handle multipart emails (most common)
        if "parts" in payload:
            return self._extract_from_parts(payload["parts"])

        # Handle single-part emails
        elif "body" in payload and "data" in payload["body"]:
            mime_type = payload.get("mimeType", "")
            data = payload["body"]["data"]
            return self._decode_body_data(data, mime_type)

        return ""

    def _extract_from_parts(self, parts: list) -> str:
        """
        Extract body from multipart email structure.

        Priority:
        1. text/plain (preferred)
        2. text/html (strip tags)
        3. Nested parts (recurse)
        """

        # First pass: look for text/plain
        for part in parts:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = self._decode_body_data(data, mime_type)
                    if body:
                        return body

        # Second pass: look for text/html
        for part in parts:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = self._decode_body_data(data, mime_type)
                    if body:
                        return body

        # Third pass: recurse into nested parts
        for part in parts:
            if "parts" in part:
                body = self._extract_from_parts(part["parts"])
                if body:
                    return body

        return ""

    def _decode_body_data(self, data: str, mime_type: str) -> str:
        """
        Decode base64-encoded email body data.

        Args:
            data: Base64-encoded body data
            mime_type: MIME type (text/plain or text/html)

        Returns:
            Decoded and cleaned text
        """

        if not data:
            return ""

        try:
            # Gmail API uses URL-safe base64 encoding
            decoded_bytes = base64.urlsafe_b64decode(data)
            decoded_text = decoded_bytes.decode("utf-8", errors="ignore")

            # Clean based on MIME type
            if mime_type == "text/html":
                decoded_text = self._strip_html_tags(decoded_text)

            return decoded_text.strip()

        except Exception as e:
            logger.error(f"Error decoding body data: {e}")
            return ""

    def _strip_html_tags(self, html_text: str) -> str:
        """
        Strip HTML tags and extract plain text.

        Comprehensive implementation handles:
        - DOCTYPE and XML declarations
        - Script and style blocks
        - HTML comments and CDATA
        - MSO (Microsoft Office) conditional comments
        - Inline styles
        - All HTML tags
        """

        if not html_text:
            return ""

        text = html_text

        # Remove DOCTYPE declarations (<!DOCTYPE...>)
        text = re.sub(r"<![^>]*>", "", text, flags=re.IGNORECASE)
        # Remove XML declarations (<?xml...?>)
        text = re.sub(r"<\?[^>]*\?>", "", text, flags=re.IGNORECASE)
        # Remove CDATA sections
        text = re.sub(r"<!\[CDATA\[.*?\]\]>", "", text, flags=re.DOTALL)
        # Remove HTML comments (<!--...-->)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        # Remove MSO (Microsoft Office) conditional comments
        text = re.sub(r"\[if[^\]]*\].*?\[endif\]", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Remove script and style tags with their content
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Remove inline styles (before removing tags to prevent garbage)
        text = re.sub(r'\s*style\s*=\s*["\'][^"\']*["\']', "", text, flags=re.IGNORECASE)

        # Replace common block elements with newlines
        text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = unescape(text)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _has_attachments(self, payload: dict) -> bool:
        """Check if email has attachments (returns boolean only)."""
        attachments = self._get_attachments(payload)
        return len(attachments) > 0

    def _get_attachments(self, payload: dict, attachments: list = None) -> list:
        """
        Extract attachment metadata from email payload.

        Args:
            payload: Gmail API message payload
            attachments: List to accumulate attachments (for recursion)

        Returns:
            List of attachment dicts with: filename, mimeType, size, attachmentId
        """
        if attachments is None:
            attachments = []

        if "parts" in payload:
            for part in payload["parts"]:
                filename = part.get("filename", "")

                # Part has a filename and body.attachmentId - it's an attachment
                if filename and part.get("body", {}).get("attachmentId"):
                    attachment_info = {
                        "filename": filename,
                        "mimeType": part.get("mimeType", "application/octet-stream"),
                        "size": part.get("body", {}).get("size", 0),
                        "attachmentId": part.get("body", {}).get("attachmentId"),
                    }
                    attachments.append(attachment_info)

                # Recursively check nested parts
                if "parts" in part:
                    self._get_attachments(part, attachments)

        return attachments

    def _create_document_text(
        self,
        subject: str,
        from_name: str,
        from_email: str,
        to_email: str,
        date_readable: str,
        body: str,
        snippet: str,
    ) -> str:
        """
        Create clean document text for embedding.

        Simple, clean format without headers (better for semantic search).
        """

        # Use cleaned body if available, otherwise snippet
        content = body if body else snippet

        # Build clean document - just subject and content (no "Email Subject:" labels)
        if subject and subject != "(No Subject)":
            document_text = f"{subject}\n\n{content}"
        else:
            document_text = content

        return document_text.strip()


# ============================================================================
# HELPER FUNCTIONS FOR TESTING
# ============================================================================


def create_sample_gmail_response() -> dict:
    """
    Create a sample Gmail API response for testing.

    This is useful for unit tests and development.
    """

    return {
        "id": "msg_18c2a3b4d5e6f7g8",
        "threadId": "thread_12345",
        "labelIds": ["INBOX", "IMPORTANT"],
        "snippet": "This is a test email about Q4 budget planning...",
        "internalDate": "1605451800000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "john@company.com"},
                {"name": "To", "value": "user@company.com"},
                {"name": "Subject", "value": "Q4 Budget Discussion"},
                {"name": "Date", "value": "Sun, 15 Nov 2020 14:30:00 +0000"},
            ],
            "body": {
                "data": base64.urlsafe_b64encode(
                    b"Hi team,\n\nI wanted to discuss our Q4 budget allocation.\n\nBest,\nJohn"
                ).decode()
            },
        },
    }


def test_processor():
    """Quick test function to verify processor works"""

    processor = GmailProcessor()
    sample_data = create_sample_gmail_response()

    try:
        result = processor.parse_email(sample_data, "test_user_123")

        print("✅ GmailProcessor Test Results:")
        print(f"  Email ID: {result['email_id']}")
        print(f"  Subject: {result['metadata']['subject']}")
        print(f"  From: {result['metadata']['from']}")
        print(f"  Date: {result['metadata']['date']}")
        print(f"  Body length: {result['metadata']['body_length']} chars")
        print(f"  Has attachments: {result['metadata']['has_attachments']}")
        print(f"\n  Document text preview:")
        print(f"  {result['document_text'][:200]}...")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test when executed directly
    test_processor()
