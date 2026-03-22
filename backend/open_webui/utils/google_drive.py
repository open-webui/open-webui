"""
Google Drive Service for Open WebUI.

This module provides functionality to interact with Google Drive API,
including authentication, file listing, and file downloading.

Security Notes:
- OAuth credentials should be stored securely using environment variables
- Never commit client_secret.json or credentials to version control
- Use service accounts for server-to-server authentication when possible
"""

import io
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class GoogleDriveError(Exception):
    """Base exception for Google Drive operations."""

    pass


class GoogleDriveAuthError(GoogleDriveError):
    """Authentication-related errors."""

    pass


class GoogleDrivePermissionError(GoogleDriveError):
    """Permission-related errors."""

    pass


class GoogleDriveNotFoundError(GoogleDriveError):
    """Resource not found errors."""

    pass


class GoogleDriveRateLimitError(GoogleDriveError):
    """Rate limit exceeded errors."""

    pass


class FileType(str, Enum):
    """Supported file types for import."""

    PDF = 'application/pdf'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    DOC = 'application/msword'
    TXT = 'text/plain'
    MD = 'text/markdown'
    CSV = 'text/csv'
    XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

    # Google Docs types (need export)
    GOOGLE_DOC = 'application/vnd.google-apps.document'
    GOOGLE_SHEET = 'application/vnd.google-apps.spreadsheet'
    GOOGLE_SLIDES = 'application/vnd.google-apps.presentation'


# Export formats for Google Docs types
GOOGLE_EXPORT_FORMATS = {
    FileType.GOOGLE_DOC.value: 'application/pdf',
    FileType.GOOGLE_SHEET.value: 'text/csv',
    FileType.GOOGLE_SLIDES.value: 'application/pdf',
}

# All supported MIME types
SUPPORTED_MIME_TYPES = [ft.value for ft in FileType]


@dataclass
class DriveFile:
    """Represents a file from Google Drive."""

    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None


@dataclass
class DriveFolder:
    """Represents a folder from Google Drive."""

    id: str
    name: str
    files: list[DriveFile]
    total_files: int


class GoogleDriveService:
    """
    Service for interacting with Google Drive API.

    This service requires Google API credentials to be configured via
    environment variables or a credentials file.

    Environment Variables:
        GOOGLE_DRIVE_CLIENT_ID: OAuth 2.0 client ID
        GOOGLE_DRIVE_CLIENT_SECRET: OAuth 2.0 client secret
        GOOGLE_DRIVE_CREDENTIALS_PATH: Path to service account JSON (optional)
    """

    def __init__(self):
        self._service = None
        self._credentials = None

    @staticmethod
    def is_configured() -> bool:
        """Check if Google Drive integration is configured."""
        client_id = os.environ.get('GOOGLE_DRIVE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET')
        credentials_path = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH')

        return bool(credentials_path) or (bool(client_id) and bool(client_secret))

    @staticmethod
    def extract_folder_id(url_or_id: str) -> Optional[str]:
        """
        Extract folder ID from a Google Drive URL or return the ID if already provided.

        Supported URL formats:
        - https://drive.google.com/drive/folders/{folder_id}
        - https://drive.google.com/drive/u/0/folders/{folder_id}
        - https://drive.google.com/drive/folders/{folder_id}?usp=sharing
        - Direct folder ID

        Args:
            url_or_id: Google Drive folder URL or ID

        Returns:
            Folder ID or None if invalid
        """
        if not url_or_id:
            return None

        url_or_id = url_or_id.strip()

        # Check if it's already a folder ID (alphanumeric with dashes/underscores)
        if re.match(r'^[\w-]+$', url_or_id) and len(url_or_id) > 20:
            return url_or_id

        # Extract from URL
        patterns = [
            r'drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/folderview\?id=([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        return None

    def _get_service(self):
        """
        Get or create the Google Drive service instance.

        Uses lazy initialization to avoid loading credentials until needed.
        """
        if self._service is not None:
            return self._service

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as e:
            raise GoogleDriveError(
                'Google API libraries not installed. '
                'Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'
            ) from e

        credentials_path = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH')

        if credentials_path and os.path.exists(credentials_path):
            try:
                self._credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly'],
                )
                self._service = build('drive', 'v3', credentials=self._credentials)
                return self._service
            except Exception as e:
                log.error(f'Failed to load service account credentials: {e}')
                raise GoogleDriveAuthError(f'Failed to authenticate with service account: {e}') from e
        else:
            raise GoogleDriveAuthError(
                'Google Drive credentials not configured. '
                'Set GOOGLE_DRIVE_CREDENTIALS_PATH environment variable.'
            )

    def validate_folder_access(self, folder_id: str) -> DriveFolder:
        """
        Validate that the folder exists and is accessible.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            DriveFolder with basic folder info

        Raises:
            GoogleDriveNotFoundError: Folder not found
            GoogleDrivePermissionError: No access to folder
            GoogleDriveError: Other errors
        """
        try:
            from googleapiclient.errors import HttpError
        except ImportError:
            raise GoogleDriveError('Google API libraries not installed')

        service = self._get_service()

        try:
            # Get folder metadata
            folder = service.files().get(fileId=folder_id, fields='id, name, mimeType').execute()

            if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                raise GoogleDriveError(f'The provided ID is not a folder: {folder_id}')

            return DriveFolder(
                id=folder['id'],
                name=folder['name'],
                files=[],
                total_files=0,
            )

        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleDriveNotFoundError(f'Folder not found: {folder_id}') from e
            elif e.resp.status == 403:
                raise GoogleDrivePermissionError(f'No access to folder: {folder_id}. Make sure the folder is shared.') from e
            elif e.resp.status == 429:
                raise GoogleDriveRateLimitError('Google Drive API rate limit exceeded. Please try again later.') from e
            else:
                raise GoogleDriveError(f'Google Drive API error: {e}') from e
        except Exception as e:
            raise GoogleDriveError(f'Unexpected error accessing folder: {e}') from e

    def list_files(
        self,
        folder_id: str,
        page_token: Optional[str] = None,
        page_size: int = 100,
        supported_types_only: bool = True,
    ) -> tuple[list[DriveFile], Optional[str]]:
        """
        List files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID
            page_token: Token for pagination
            page_size: Number of files per page
            supported_types_only: Only return files with supported MIME types

        Returns:
            Tuple of (list of files, next page token or None)
        """
        try:
            from googleapiclient.errors import HttpError
        except ImportError:
            raise GoogleDriveError('Google API libraries not installed')

        service = self._get_service()

        try:
            # Build query
            query = f"'{folder_id}' in parents and trashed = false"

            if supported_types_only:
                mime_conditions = ' or '.join([f"mimeType = '{mt}'" for mt in SUPPORTED_MIME_TYPES])
                query += f' and ({mime_conditions})'

            # Execute request
            results = (
                service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    pageToken=page_token,
                    fields='nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink)',
                    orderBy='modifiedTime desc',
                )
                .execute()
            )

            files = [
                DriveFile(
                    id=f['id'],
                    name=f['name'],
                    mime_type=f['mimeType'],
                    size=int(f.get('size', 0)) if f.get('size') else None,
                    modified_time=f.get('modifiedTime'),
                    web_view_link=f.get('webViewLink'),
                )
                for f in results.get('files', [])
            ]

            return files, results.get('nextPageToken')

        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleDriveNotFoundError(f'Folder not found: {folder_id}') from e
            elif e.resp.status == 403:
                raise GoogleDrivePermissionError(f'No access to folder: {folder_id}') from e
            elif e.resp.status == 429:
                raise GoogleDriveRateLimitError('Rate limit exceeded') from e
            else:
                raise GoogleDriveError(f'Failed to list files: {e}') from e

    def download_file(self, file_id: str, mime_type: str) -> tuple[bytes, str]:
        """
        Download a file from Google Drive.

        For Google Docs types, exports to a compatible format.

        Args:
            file_id: Google Drive file ID
            mime_type: MIME type of the file

        Returns:
            Tuple of (file content as bytes, actual mime type)
        """
        try:
            from googleapiclient.errors import HttpError
            from googleapiclient.http import MediaIoBaseDownload
        except ImportError:
            raise GoogleDriveError('Google API libraries not installed')

        service = self._get_service()

        try:
            # Check if this is a Google Docs type that needs export
            if mime_type in GOOGLE_EXPORT_FORMATS:
                export_mime = GOOGLE_EXPORT_FORMATS[mime_type]
                request = service.files().export_media(fileId=file_id, mimeType=export_mime)
                actual_mime = export_mime
            else:
                request = service.files().get_media(fileId=file_id)
                actual_mime = mime_type

            # Download file
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            return buffer.getvalue(), actual_mime

        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleDriveNotFoundError(f'File not found: {file_id}') from e
            elif e.resp.status == 403:
                raise GoogleDrivePermissionError(f'No access to file: {file_id}') from e
            elif e.resp.status == 429:
                raise GoogleDriveRateLimitError('Rate limit exceeded') from e
            else:
                raise GoogleDriveError(f'Failed to download file: {e}') from e

    def get_changes(
        self,
        folder_id: str,
        page_token: Optional[str] = None,
    ) -> tuple[list[DriveFile], list[str], str]:
        """
        Get changes in a folder since the last sync.

        Args:
            folder_id: Google Drive folder ID
            page_token: Start page token from previous sync

        Returns:
            Tuple of (new/modified files, deleted file IDs, new page token)
        """
        try:
            from googleapiclient.errors import HttpError
        except ImportError:
            raise GoogleDriveError('Google API libraries not installed')

        service = self._get_service()

        try:
            # If no page token, get the start token
            if not page_token:
                response = service.changes().getStartPageToken().execute()
                page_token = response.get('startPageToken')

            # Get changes
            new_files = []
            deleted_ids = []
            new_page_token = page_token

            while True:
                response = (
                    service.changes()
                    .list(
                        pageToken=new_page_token,
                        spaces='drive',
                        fields='nextPageToken, newStartPageToken, changes(fileId, removed, file(id, name, mimeType, size, modifiedTime, parents))',
                    )
                    .execute()
                )

                for change in response.get('changes', []):
                    if change.get('removed'):
                        deleted_ids.append(change['fileId'])
                    elif change.get('file'):
                        file_data = change['file']
                        # Check if file is in the target folder
                        parents = file_data.get('parents', [])
                        if folder_id in parents and file_data.get('mimeType') in SUPPORTED_MIME_TYPES:
                            new_files.append(
                                DriveFile(
                                    id=file_data['id'],
                                    name=file_data['name'],
                                    mime_type=file_data['mimeType'],
                                    size=int(file_data.get('size', 0)) if file_data.get('size') else None,
                                    modified_time=file_data.get('modifiedTime'),
                                )
                            )

                if 'newStartPageToken' in response:
                    new_page_token = response['newStartPageToken']
                    break
                elif 'nextPageToken' in response:
                    new_page_token = response['nextPageToken']
                else:
                    break

            return new_files, deleted_ids, new_page_token

        except HttpError as e:
            if e.resp.status == 429:
                raise GoogleDriveRateLimitError('Rate limit exceeded') from e
            else:
                raise GoogleDriveError(f'Failed to get changes: {e}') from e


# Global service instance
google_drive_service = GoogleDriveService()
