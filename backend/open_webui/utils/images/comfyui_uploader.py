"""
ComfyUI Image Uploader
从 Open-WebUI files system, read uploading imgs to ComfyUI
"""

import logging
from pathlib import Path
from typing import Optional, List

import requests

from open_webui.models.files import Files
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)


class ComfyUIUploadError(Exception):
    """ComfyUI error"""
    pass


def upload_image_to_comfyui(
    file_id: str,
    comfyui_base_url: str,
    api_key: Optional[str] = None
) -> str:
    """
    1 image to ComfyUI
    
    Args:
        file_id: Open-WebUI file ID
        comfyui_base_url: ComfyUI server address (http://127.0.0.1:8188)
        api_key: API Key
    
    Returns:
        ComfyUI back files (e.g. "abc123_photo.jpg")
    
    Raises:
        ComfyUIUploadError: uploading error
    """
    log.info(f"📤 Uploading image {file_id} to ComfyUI")
    
    try:
        # 1. Open-WebUI files path log
        file = Files.get_file_by_id(file_id)
        if not file:
            raise ComfyUIUploadError(f"File not found: {file_id}")
        
        log.debug(f"Found file: {file.filename}")
        
        # 2. actual path
        file_path = Storage.get_file(file.path)
        file_path = Path(file_path)
        
        if not file_path.is_file():
            raise ComfyUIUploadError(f"File does not exist: {file_path}")
        
        log.debug(f"File path: {file_path}")
        
        # 3. read content
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        log.debug(f"Read {len(image_data)} bytes")
        
        # 4. preparation files
        # using original name or expansion name
        original_filename = file.meta.get("name", file.filename)
        
        files = {
            'image': (original_filename, image_data, file.meta.get("content_type", "image/jpeg"))
        }
        
        data = {
            'overwrite': 'true'  # permit cover same name
        }
        
        # preparation
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 5. upload to ComfyUI
        upload_url = f"{comfyui_base_url}/upload/image"
        log.debug(f"Uploading to: {upload_url}")
        
        response = requests.post(
            upload_url,
            files=files,
            data=data,
            headers=headers,
            timeout=30  # 30 timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 6. obtain ComfyUI file name
        comfyui_filename = result.get('name')
        if not comfyui_filename:
            raise ComfyUIUploadError(f"ComfyUI did not return filename: {result}")
        
        log.info(f"✅ Image uploaded successfully: {comfyui_filename}")
        return comfyui_filename
        
    except requests.RequestException as e:
        log.exception(f"❌ Failed to upload image to ComfyUI: {e}")
        raise ComfyUIUploadError(f"Network error: {str(e)}") from e
    
    except Exception as e:
        log.exception(f"❌ Unexpected error uploading image: {e}")
        raise ComfyUIUploadError(f"Upload failed: {str(e)}") from e


def upload_images_to_comfyui(
    file_ids: List[str],
    comfyui_base_url: str,
    api_key: Optional[str] = None,
    max_images: int = 2
) -> List[str]:
    """
    batch uploading ComfyUI
    
    Args:
        file_ids: Open-WebUI files id list
        comfyui_base_url: ComfyUI webserver
        api_key: API Key 
        max_images: 2 for fusion
    
    Returns:
        ComfyUI files name list
    
    Raises:
        ComfyUIUploadError: any one img uploading error
    """
    if not file_ids:
        log.warning("⚠️ No images to upload")
        return []
    
    # number limitation
    file_ids_to_upload = file_ids[:max_images]
    
    if len(file_ids) > max_images:
        log.warning(
            f"⚠️ Too many images ({len(file_ids)}), only uploading first {max_images}"
        )
    
    log.info(f"📤 Uploading {len(file_ids_to_upload)} images to ComfyUI")
    
    uploaded_filenames = []
    
    for i, file_id in enumerate(file_ids_to_upload, 1):
        try:
            log.info(f"Uploading image {i}/{len(file_ids_to_upload)}: {file_id}")
            
            filename = upload_image_to_comfyui(
                file_id,
                comfyui_base_url,
                api_key
            )
            
            uploaded_filenames.append(filename)
            log.info(f"✅ Image {i} uploaded: {filename}")
            
        except ComfyUIUploadError as e:
            log.error(f"❌ Failed to upload image {i}: {e}")
            raise  
    
    log.info(f"✅ All {len(uploaded_filenames)} images uploaded successfully")
    return uploaded_filenames