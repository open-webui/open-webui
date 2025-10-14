"""
ComfyUI Integration
Integeration workflow selector and image uploader，completely workflow progress
"""

import asyncio
import json
import logging
import urllib.parse
import urllib.request
from typing import Optional

import websocket
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.images.workflow_selector import prepare_workflow
from open_webui.utils.images.comfyui_uploader import (
    upload_images_to_comfyui,
    ComfyUIUploadError
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["COMFYUI"])

default_headers = {"User-Agent": "Mozilla/5.0"}


# ========================================
# ComfyUI API 
# ========================================

def queue_prompt(prompt, client_id, base_url, api_key):
    """将 workflow submit to queue"""
    log.info("queue_prompt")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    log.debug(f"queue_prompt data: {data}")
    try:
        headers = {**default_headers}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        req = urllib.request.Request(
            f"{base_url}/prompt",
            data=data,
            headers=headers,
        )
        response = urllib.request.urlopen(req).read()
        return json.loads(response)
    except Exception as e:
        log.exception(f"Error while queuing prompt: {e}")
        raise e


def get_image_url(filename, subfolder, folder_type, base_url):
    """generate img URL"""
    log.debug(f"get_image_url: {filename}")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    return f"{base_url}/view?{url_values}"


def get_history(prompt_id, base_url, api_key):
    """obtain generation history"""
    log.info(f"get_history: {prompt_id}")
    
    headers = {**default_headers}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    req = urllib.request.Request(
        f"{base_url}/history/{prompt_id}",
        headers=headers,
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def get_images(ws, workflow, client_id, base_url, api_key):
    """
    sent workflow through WebSocket and waiting for img generation
    
    Args:
        ws: WebSocket connection
        workflow: workflow dict
        client_id: user ID
        base_url: ComfyUI server address
        api_key: API Key
    
    Returns:
        {"data": [{"url": "..."}, ...]}
    """
    # queue submission
    prompt_id = queue_prompt(workflow, client_id, base_url, api_key)["prompt_id"]
    log.info(f"Prompt queued: {prompt_id}")
    
    output_images = []
    
    # waiting for execution
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    log.info("Execution completed")
                    break  # execution completed
        else:
            continue  
    
    # output
    history = get_history(prompt_id, base_url, api_key)[prompt_id]
    
    for node_id in history["outputs"]:
        node_output = history["outputs"][node_id]
        if "images" in node_output:
            for image in node_output["images"]:
                url = get_image_url(
                    image["filename"], 
                    image["subfolder"], 
                    image["type"], 
                    base_url
                )
                
                node_class = workflow.get(node_id, {}).get("class_type", "")
                
                
                if "Preview" in node_class:
                    image_type = "preview"
                elif "Save" in node_class:
                    image_type = "output"
                else:
                    image_type = "unknown"
                
                image_info = {
                    "url": url,
                    "type": image_type, 
                    "filename": image["filename"],
                    "node_id": node_id 
                }
                output_images.append(image_info)
                log.info(f"Generated image: {url} (type: {image_type}, class: {node_class})")
    
    return {
            "data": [
                {
                "url": "/api/v1/files/abc...",
                "type": "temp",
                "filename": "ComfyUI_temp_00002_.png",
                "node_id": "2"
                },
                {
                "url": "/api/v1/files/def...",
                "type": "output",
                "filename": "fal_flux_simple_00007_.png",
                "node_id": "3"
                }
                ]
            }


# ========================================
# data base model (simple)
# ========================================

class ComfyUIGenerateImageForm(BaseModel):
    """
    ComfyUI image generation request

    """
    prompt: str
    width: int
    height: int
    # image input (optional)
    input_images: Optional[list[str]] = None  


# ========================================
# MAIN FUNCTION
# ========================================

async def comfyui_generate_image(
    model: str,
    payload: ComfyUIGenerateImageForm,
    client_id: str,
    base_url: str,
    api_key: Optional[str] = None
):
    """
    ComfyUI img generation
    
    Args:
        model: model(for Fal.ai nodes dont needed)
        payload: generation param
        client_id: user.id
        base_url: ComfyUI server address
        api_key: API Key
    
    Returns:
        {"data": [{"url": "..."}, ...]} or None(failure)
    """
    log.info("=" * 60)
    log.info("🎨 Starting ComfyUI image generation")
    log.info(f"Prompt: {payload.prompt[:50]}...")
    log.info(f"Size: {payload.width}x{payload.height}")
    log.info(f"Input images: {len(payload.input_images) if payload.input_images else 0}")
    log.info("=" * 60)
    
    try:
        # ========================================
        # Step 1: upload img,is we have
        # ========================================
        uploaded_filenames = []
        
        if payload.input_images:
            log.info(f"📤 Uploading {len(payload.input_images)} input images to ComfyUI")
            
            try:
                uploaded_filenames = await asyncio.to_thread(
                    upload_images_to_comfyui,
                    file_ids=payload.input_images,
                    comfyui_base_url=base_url,
                    api_key=api_key,
                    max_images=2  # fusion limitation 2
                )
                
                log.info(f"✅ Uploaded {len(uploaded_filenames)} images: {uploaded_filenames}")
                
            except ComfyUIUploadError as e:
                log.error(f"❌ Failed to upload images: {e}")
                return None
        
        # ========================================
        # Step 2: workflow
        # ========================================
        log.info("🔧 Preparing workflow")
        
        workflow, workflow_type = prepare_workflow(
            input_images=payload.input_images,
            prompt=payload.prompt,
            width=payload.width,
            height=payload.height,
            uploaded_filenames=uploaded_filenames
        )
        
        log.info(f"✅ Workflow prepared: {workflow_type}")
        log.debug(f"Workflow JSON: {json.dumps(workflow, indent=2)}")
        
        # ========================================
        # Step 3 web socket
        # ========================================
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        log.info(f"Connecting to WebSocket: {ws_url}")
        
        try:
            ws = websocket.WebSocket()
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            ws.connect(f"{ws_url}/ws?clientId={client_id}", header=headers)
            log.info("✅ WebSocket connection established")
            
        except Exception as e:
            log.exception(f"❌ Failed to connect to WebSocket: {e}")
            return None
        
        # ========================================
        # Step 4: Workflow and waiting
        # ========================================
        try:
            log.info("🚀 Sending workflow to ComfyUI")
            
            images = await asyncio.to_thread(
                get_images,
                ws,
                workflow,  # sent dix not json
                client_id,
                base_url,
                api_key
            )
            
            if images and images.get("data"):
                log.info(f"✅ Generated {len(images['data'])} images successfully")
            else:
                log.warning("⚠️ No images generated")
            
            return images
            
        except Exception as e:
            log.exception(f"❌ Error during image generation: {e}")
            return None
        
        finally:
            ws.close()
            log.info("🔌 WebSocket connection closed")
    
    except Exception as e:
        log.exception(f"❌ Unexpected error in comfyui_generate_image: {e}")
        return None