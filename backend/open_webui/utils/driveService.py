from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import io
import uuid
import os
import base64
import traceback
from mimetypes import guess_type
from open_webui.storage.provider import Storage
from open_webui.models.files import FileForm, Files
from open_webui.routers.retrieval import process_file, ProcessFileForm

SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'Client_secret.json')
SCOPES = ["https://www.googleapis.com/auth/drive"]

def create_file_object(file_name, file_content, mime_type):
    return {
        "name": file_name,
        "size": len(file_content),
        "type": mime_type,
        "content": base64.b64encode(file_content).decode("utf-8"),
    }

def fetch_file_metadata(service, drive_id: str):
    try:
        return service.files().get(fileId=drive_id, fields="id, name, mimeType, parents").execute()
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Metadata fetch failed: {str(e)}")

def get_drive_files(drive_id: str):
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build("drive", "v3", credentials=creds)
        metadata = fetch_file_metadata(service, drive_id)
        files = []

        if metadata["mimeType"] == "application/vnd.google-apps.folder":
            drive_files = []
            page_token = None
            query = f"'{drive_id}' in parents and trashed=false"
            while True:
                results = service.files().list(
                    q=query,
                    fields="files(id, name, mimeType, md5Checksum), nextPageToken",
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                drive_files.extend(results.get("files", []))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
        else:
            drive_files = [metadata]

        # Parallel download with ThreadPool
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(download_file, creds, file): file for file in drive_files}
            for future in as_completed(future_to_file):
                file_result = future.result()
                if file_result:
                    files.append(file_result)
        return files
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Drive retrieval error: {str(e)}")

def download_file(creds, file):
    try:
        service = build("drive", "v3", credentials=creds)
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]

        if mime_type == "application/vnd.google-apps.document":
            export_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        elif mime_type == "application/pdf":
            request = service.files().get_media(fileId=file_id)
        else:
            return None

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return create_file_object(file_name, fh.getvalue(), export_mime if mime_type == "application/vnd.google-apps.document" else "application/pdf")
    except Exception as e:
        traceback.print_exc()
        print(f"Download failed: {str(e)}")
        return None

def convert_to_python_file_object(file_data):
    content = file_data.get("content", b"")
    if isinstance(content, str):
        content = base64.b64decode(content)
    return {
        "name": file_data["name"],
        "content": content,
        "mime_type": file_data.get("type") or guess_type(file_data["name"])[0] or "application/octet-stream",
    }

async def upload_drive_file(request, file_data, user_id):
    try:
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file_data['name']}"
        file_blob = io.BytesIO(file_data["content"])
        contents, file_path = await asyncio.to_thread(Storage.upload_file, file_blob, filename)
        file_item = Files.insert_new_file(
            user_id,
            FileForm(
                id=file_id,
                filename=file_data["name"],
                path=file_path,
                meta={
                    "name": file_data["name"],
                    "content_type": file_data["mime_type"],
                    "size": len(contents),
                },
            ),
        )
        await asyncio.to_thread(process_file, request, ProcessFileForm(file_id=file_id))
        return Files.get_file_by_id(file_id)
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Upload failed: {str(e)}")

async def process_google_drive_link(drive_id, user_id, request):
    try:
        raw_files = await asyncio.to_thread(get_drive_files, drive_id)
        converted_files = [convert_to_python_file_object(f) for f in raw_files if f]
        uploaded_files = await asyncio.gather(*[
            upload_drive_file(request, file_data, user_id)
            for file_data in converted_files
        ])
        return [{
            "id": uf.id,
            "name": uf.filename,
            "path": uf.path,
            "meta": uf.meta,
        } for uf in uploaded_files]
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Processing error: {str(e)}")