import json
import logging
from typing import List, Dict, Optional, Tuple, TypedDict, NotRequired
from datetime import datetime
import io

from google.oauth2 import service_account  # type: ignore
from googleapiclient.discovery import build, Resource  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from googleapiclient.http import MediaIoBaseDownload  # type: ignore

from open_webui.config import GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON


# Type definitions for Google Drive API responses
class GoogleDriveFile(TypedDict):
    """Type definition for Google Drive file information."""

    id: str
    name: str
    mimeType: str
    modifiedTime: str
    size: NotRequired[str]  # Optional field, not present for some files
    parents: NotRequired[List[str]]  # Optional, may not be present
    path: str  # Custom field added by our service


class GoogleDriveFolder(TypedDict):
    """Type definition for Google Drive folder information."""

    id: str
    name: str


class GoogleDriveAPIResponse(TypedDict):
    """Type definition for Google Drive API list response."""

    files: List[Dict[str, str]]  # Raw API response uses generic dict
    nextPageToken: NotRequired[str]


class FileDownloadResult(TypedDict):
    """Type definition for file download result."""

    content: bytes
    filename: str


class GoogleDriveSyncConfig(TypedDict):
    """Type definition for Google Drive sync configuration stored in knowledge base data."""

    google_drive_folder_id: str
    google_drive_include_nested: bool
    google_drive_sync_interval_days: float  # Float to support fractional days
    google_drive_last_sync: int  # Unix timestamp
    file_ids: List[str]  # List of file IDs in the knowledge base


class GoogleDriveFileMetadata(TypedDict):
    """Type definition for Google Drive file metadata stored in file records."""

    name: str
    content_type: str
    size: int
    google_drive_id: str
    google_drive_modified: str  # ISO timestamp from Google Drive API
    google_drive_path: str
    collection_name: str
    # Additional standard file metadata fields that may be present
    source: NotRequired[str]  # Usually "google_drive"
    original_filename: NotRequired[str]  # May differ from processed filename


log = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for interacting with Google Drive using service account authentication."""

    def __init__(self) -> None:
        self.service: Optional[Resource] = None
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize Google Drive service with service account credentials."""
        try:
            if not GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON.value:
                log.warning("Google Drive service account JSON not configured")
                return

            # Parse service account JSON
            service_account_info = json.loads(GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON.value)

            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )

            # Build service
            self.service = build("drive", "v3", credentials=credentials)
            log.info("Google Drive service initialized successfully")

        except json.JSONDecodeError as e:
            log.error(f"Invalid service account JSON: {e}")
        except Exception as e:
            log.error(f"Failed to initialize Google Drive service: {e}")

    def is_configured(self) -> bool:
        """Check if Google Drive service is properly configured."""
        return self.service is not None

    def refresh_configuration(self) -> None:
        """Refresh the service configuration. Call this when config is updated."""
        self._initialize_service()

    def get_service_account_email(self) -> Optional[str]:
        """Get the service account email address."""
        try:
            if not GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON.value:
                return None

            service_account_info = json.loads(GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON.value)
            return service_account_info.get("client_email")
        except Exception as e:
            log.error(f"Failed to get service account email: {e}")
            return None

    def list_folder_files(
        self, folder_id: str, include_nested: bool = True
    ) -> List[GoogleDriveFile]:
        """
        List all files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID
            include_nested: Whether to include files from nested folders

        Returns:
            List of file information dictionaries
        """
        if not self.service:
            raise Exception("Google Drive service not configured")

        try:
            files = []

            if include_nested:
                # Get all files recursively
                files = self._get_files_recursive(folder_id)
            else:
                # Get files only from the specified folder
                files = self._get_files_in_folder(folder_id)

            # Filter supported file types
            log.info(f"Google Drive: Found {len(files)} total files before filtering")
            for file_info in files:
                log.info(
                    f"Google Drive file found: '{file_info.get('name', 'Unknown')}' (Type: {file_info.get('mimeType', 'Unknown')})"
                )

            supported_files = []
            for file_info in files:
                if self._is_supported_file(file_info):
                    supported_files.append(file_info)
                    log.info(
                        f"Google Drive: File '{file_info.get('name', 'Unknown')}' is SUPPORTED"
                    )
                else:
                    log.info(
                        f"Google Drive: File '{file_info.get('name', 'Unknown')}' is NOT SUPPORTED (Type: {file_info.get('mimeType', 'Unknown')})"
                    )

            log.info(f"Google Drive: {len(supported_files)} files passed filtering")
            return supported_files

        except HttpError as e:
            log.error(f"HTTP error listing folder files: {e}")
            raise Exception(f"Failed to access Google Drive folder: {e}")
        except Exception as e:
            log.error(f"Error listing folder files: {e}")
            raise

    def _get_files_recursive(
        self, folder_id: str, path: str = ""
    ) -> List[GoogleDriveFile]:
        """Recursively get all files from a folder and its subfolders."""
        files = []

        # Get files in current folder
        files.extend(self._get_files_in_folder(folder_id, path))

        # Get subfolders and process them recursively
        subfolders = self._get_subfolders(folder_id)
        for subfolder in subfolders:
            subfolder_path = (
                f"{path}/{subfolder['name']}" if path else subfolder["name"]
            )
            files.extend(self._get_files_recursive(subfolder["id"], subfolder_path))

        return files

    def _get_files_in_folder(
        self, folder_id: str, path: str = ""
    ) -> List[GoogleDriveFile]:
        """Get files directly in a specific folder."""
        files = []
        page_token = None

        log.info(f"Google Drive: Querying folder {folder_id} for files")

        # Debug: Test if we can access any files at all
        try:
            assert self.service is not None  # Type guard for mypy
            test_response = (
                self.service.files()
                .list(
                    q="", spaces="drive", pageSize=5, fields="files(id, name, mimeType)"
                )
                .execute()
            )
            log.info(
                f"Google Drive: Test query found {len(test_response.get('files', []))} total accessible files"
            )
        except Exception as e:
            log.error(f"Google Drive: Test query failed: {e}")

        while True:
            # Use official Google Drive API query syntax
            query = f"'{folder_id}' in parents"
            log.info(f"Google Drive API query: {query}")

            try:
                # Follow official Google Drive API example pattern with Shared Drive support
                assert self.service is not None  # Type guard for mypy
                response = (
                    self.service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        corpora="allDrives",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        pageSize=100,
                        pageToken=page_token,
                        fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)",
                    )
                    .execute()
                )

                log.info(
                    f"Google Drive API response: {len(response.get('files', []))} items returned"
                )

                # Log all items found (including folders)
                all_items = response.get("files", [])
                for item in all_items:
                    log.info(
                        f"Google Drive item: '{item.get('name', 'Unknown')}' (Type: {item.get('mimeType', 'Unknown')})"
                    )

                results = response  # Keep compatibility with existing code

            except Exception as e:
                log.error(f"Google Drive API error: {e}")
                return []

            items = results.get("files", [])

            # Filter out folders and only keep files
            for item in items:
                if item.get("mimeType") != "application/vnd.google-apps.folder":
                    file_info: GoogleDriveFile = {
                        "id": item["id"],
                        "name": item["name"],
                        "mimeType": item["mimeType"],
                        "modifiedTime": item["modifiedTime"],
                        "path": f"{path}/{item['name']}" if path else item["name"],
                    }
                    # Add optional fields if present
                    if "size" in item:
                        file_info["size"] = item["size"]
                    if "parents" in item:
                        file_info["parents"] = item["parents"]
                    files.append(file_info)
                    log.info(f"Google Drive: Added file '{item['name']}' to results")

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return files

    def _get_subfolders(self, folder_id: str) -> List[Dict[str, str]]:
        """Get subfolders in a specific folder."""
        subfolders = []
        page_token = None

        while True:
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

            assert self.service is not None  # Type guard for mypy
            results = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    corpora="allDrives",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageSize=100,
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name)",
                )
                .execute()
            )

            items = results.get("files", [])
            subfolders.extend(items)

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return subfolders

    def _is_supported_file(self, file_info: GoogleDriveFile) -> bool:
        """Check if a file type is supported by the knowledge base."""
        mime_type = file_info.get("mimeType", "")
        file_name = file_info.get("name", "")

        # Supported document file extensions for knowledge base
        # Focus on actual document types rather than code files
        supported_extensions = [
            # Text and markdown documents
            "txt",
            "md",
            "markdown",
            "rst",
            
            # Microsoft Office documents
            "doc",
            "docx",
            "xls",
            "xlsx",
            "ppt",
            "pptx",
            "msg",
            
            # OpenDocument formats
            "odt",
            "ods",
            "odp",
            
            # PDF documents
            "pdf",
            
            # Data files
            "csv",
            "tsv",
            "json",
            "xml",
            
            # Web documents
            "html",
            "htm",
            
            # Rich text
            "rtf",
            
            # eBooks
            "epub",
            "mobi",
            
            # Other document formats
            "pages",  # Apple Pages
            "numbers",  # Apple Numbers
            "key",  # Apple Keynote
        ]

        # Check file extension
        if "." in file_name:
            extension = file_name.split(".")[-1].lower()
            if extension in supported_extensions:
                return True

        # Check Google Workspace files
        google_workspace_types = [
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
        ]

        if mime_type in google_workspace_types:
            return True

        # Check other supported MIME types for documents
        supported_mime_types = [
            # Text documents
            "text/plain",
            "text/markdown",
            "text/x-markdown",
            "text/csv",
            "text/tab-separated-values",
            "text/xml",
            "text/html",
            "text/rtf",
            
            # Microsoft Office documents
            "application/msword",  # .doc
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/vnd.ms-excel",  # .xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
            "application/vnd.ms-powerpoint",  # .ppt
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
            "application/vnd.ms-outlook",  # .msg
            
            # OpenDocument formats
            "application/vnd.oasis.opendocument.text",  # .odt
            "application/vnd.oasis.opendocument.spreadsheet",  # .ods
            "application/vnd.oasis.opendocument.presentation",  # .odp
            
            # PDF
            "application/pdf",
            
            # eBooks
            "application/epub+zip",
            "application/x-mobipocket-ebook",
            
            # Data formats
            "application/json",
            
            # Apple iWork formats (when exported)
            "application/x-iwork-pages-sffpages",  # .pages
            "application/x-iwork-numbers-sffnumbers",  # .numbers
            "application/x-iwork-keynote-sffkey",  # .key
        ]

        return mime_type in supported_mime_types

    def download_file(
        self, file_id: str, file_info: GoogleDriveFile
    ) -> Tuple[bytes, str]:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            file_info: File information dictionary

        Returns:
            Tuple of (file_content_bytes, filename)
        """
        if not self.service:
            raise Exception("Google Drive service not configured")

        try:
            mime_type = file_info.get("mimeType", "")
            file_name = file_info.get("name", "")

            # Handle Google Workspace files (export)
            if mime_type.startswith("application/vnd.google-apps"):
                return self._export_google_workspace_file(file_id, mime_type, file_name)
            else:
                # Handle regular files (download)
                return self._download_regular_file(file_id, file_name)

        except HttpError as e:
            log.error(f"HTTP error downloading file {file_id}: {e}")
            raise Exception(f"Failed to download file: {e}")
        except Exception as e:
            log.error(f"Error downloading file {file_id}: {e}")
            raise

    def _export_google_workspace_file(
        self, file_id: str, mime_type: str, file_name: str
    ) -> Tuple[bytes, str]:
        """Export Google Workspace files to supported formats."""
        export_mime_type = None
        export_extension = None

        if "document" in mime_type:
            export_mime_type = "text/plain"
            export_extension = ".txt"
        elif "spreadsheet" in mime_type:
            export_mime_type = "text/csv"
            export_extension = ".csv"
        elif "presentation" in mime_type:
            export_mime_type = "text/plain"
            export_extension = ".txt"
        else:
            export_mime_type = "application/pdf"
            export_extension = ".pdf"

        assert self.service is not None  # Type guard for mypy
        request = self.service.files().export_media(
            fileId=file_id, mimeType=export_mime_type
        )
        file_content = request.execute()

        # Update filename with appropriate extension
        if not file_name.endswith(export_extension):
            file_name = f"{file_name}{export_extension}"

        return file_content, file_name

    def _download_regular_file(self, file_id: str, file_name: str) -> Tuple[bytes, str]:
        """Download regular files."""
        assert self.service is not None  # Type guard for mypy
        request = self.service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)

        done = False
        while done is False:
            _, done = downloader.next_chunk()

        file_content = file_io.getvalue()
        return file_content, file_name


# Global instance
google_drive_service = GoogleDriveService()
