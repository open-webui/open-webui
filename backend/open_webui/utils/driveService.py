from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from open_webui.storage.provider import Storage
from open_webui.models.files import FileForm, Files
from open_webui.routers.retrieval import process_file, ProcessFileForm
import base64

import io
import uuid
import os
import traceback
from mimetypes import guess_type

# Define the path to your Google service account JSON file
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'Client_secret.json')

# Scopes required for Google Drive API
SCOPES = ["https://www.googleapis.com/auth/drive"]


def create_file_object(file_name, file_content, mime_type):
    """Create a file dictionary for uploadFileHandler."""
    return {
        "name": file_name,
        "size": len(file_content),
        "type": mime_type,
        "content": base64.b64encode(file_content).decode("utf-8"),
    }


def fetch_file_metadata(service, drive_id: str):
    """
    Fetch metadata for a given file or folder from Google Drive.
    Args:
        service: Google API service instance.
        drive_id: The unique ID of the file or folder.
    Returns:
        A dictionary with file or folder metadata.
    Raises:
        Exception if fetching metadata fails.
    """
    try:
        print(f"Fetching metadata for Drive ID: {drive_id}")
        file_metadata = service.files().get(fileId=drive_id, fields="id, name, mimeType, parents").execute()
        return file_metadata
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Unable to fetch metadata for Drive ID {drive_id}: {str(e)}")


def get_drive_files(drive_id: str):
    """
    Fetch and return files from Google Drive as Base64-encoded objects.
    """
    try:
        # Authenticate using the service account credentials
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build("drive", "v3", credentials=creds)

        # Fetch metadata of the given file/folder
        metadata = fetch_file_metadata(service, drive_id)

        files = []
        if metadata["mimeType"] == "application/vnd.google-apps.folder":
            # If it's a folder, fetch all files inside it
            #print(f"Fetching all files from folder: {metadata['name']} (ID: {drive_id})")
            query = f"'{drive_id}' in parents and trashed=false"
            results = service.files().list(q=query, fields="files(id, name, mimeType,md5Checksum)").execute()
            drive_files = results.get("files", [])
            print(drive_files, end="\n")
        else:
            # If it's a single file, process it directly
            #print(f"Processing individual file: {metadata['name']} (ID: {drive_id})")
            drive_files = [metadata]

        # Fetch content for each file
        for file in drive_files:
            #print(file.md5Checksum if "md5Checksum" in file else "N/A", end="")
            files.append(download_file(service, file))

        return files

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Error retrieving files from Google Drive: {str(e)}")


def download_file(service, file):
    """
    Download a single file from Google Drive and return its content as a dictionary.
    Args:
        service: Google API service instance.
        file: Dictionary containing file metadata (ID, name, MIME type).
    Returns:
        A dictionary containing file content and metadata.
    """
    try:
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]

        if mime_type == "application/vnd.google-apps.document":
            # Google Docs: Export to .docx
            export_mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            #print(f"Downloading Google Docs file '{file_name}' as .docx")
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)

        elif mime_type == "application/pdf":
            # PDF files
            #print(f"Downloading PDF file: {file_name}")
            request = service.files().get_media(fileId=file_id)

        else:
            # Handle unsupported MIME types
            print(f"Skipping unsupported file type: {mime_type}")
            return None

        # Perform the download
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        #print(f"File '{file_name}' downloaded successfully!")
        return create_file_object(file_name, file_stream.getvalue(), export_mime_type if mime_type == "application/vnd.google-apps.document" else "application/pdf")

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Failed to download file '{file['name']}': {str(e)}")


def convert_to_python_file_object(file_data):
    """
    Convert raw Google Drive file data into a Python-compatible file object.
    """
    name = file_data["name"]
    content = file_data.get("content", b"")  # Ensure binary content
    if isinstance(content, str):
        content = base64.b64decode(content)  # Decode Base64 content
    mime_type = file_data.get("type") or guess_type(name)[0] or "application/octet-stream"
    return {
        "name": name,
        "content": content,
        "mime_type": mime_type,
    }


async def upload_drive_file(request, file_data, user_id):
    """
    Upload a single Google Drive file and store its metadata.
    """
    try:
        name = file_data["name"]
        content = file_data["content"]
        mime_type = file_data["mime_type"]

        # Generate a UUID for the file and storage filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{os.path.basename(name)}"
        file_blob = io.BytesIO(content)
        contents, file_path = Storage.upload_file(file_blob, filename)

        # Insert metadata into the database using Files model
        print(f"Storing file '{name}' in database...")
        file_item = Files.insert_new_file(
            user_id,
            FileForm(
                id=file_id,
                filename=name,
                path=file_path,
                meta={"name": name, "content_type": mime_type, "size": len(contents)},
            ),
        )

        # Process the file (optional)
        process_file(request, ProcessFileForm(file_id=file_id))
        print(f"File '{name}' processed and stored successfully!")
        return Files.get_file_by_id(file_id)

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Failed to upload Google Drive file '{file_data['name']}': {str(e)}")


async def process_google_drive_link(drive_id, user_id, request):
    """
    Orchestrate the flow: fetch files, upload them, and return metadata.
    """
    try:
        print(f"Processing Google Drive link for Drive ID: {drive_id}")
        raw_files = get_drive_files(drive_id)
        converted_files = [convert_to_python_file_object(file) for file in raw_files if file is not None]
        uploaded_files = []

        for file_data in converted_files:
            uploaded_file = await upload_drive_file(request, file_data, user_id)
            uploaded_files.append({
                "id": uploaded_file.id,
                "name": uploaded_file.filename,
                "path": uploaded_file.path,
                "meta": uploaded_file.meta,
            })

        return uploaded_files

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Error processing Google Drive link: {str(e)}")