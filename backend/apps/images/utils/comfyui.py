import asyncio
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import json
import urllib.request
import urllib.parse
import random
import logging

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["COMFYUI"])

from pydantic import BaseModel

from typing import Optional

COMFYUI_DEFAULT_WORKFLOW = """
{
  "3": {
    "inputs": {
      "seed": 0,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "model.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "Prompt",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}
"""


def queue_prompt(prompt, client_id, base_url):
    log.info("queue_prompt")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type, base_url):
    log.info("get_image")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"{base_url}/view?{url_values}") as response:
        return response.read()


def get_image_url(filename, subfolder, folder_type, base_url):
    log.info("get_image")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    return f"{base_url}/view?{url_values}"


def get_history(prompt_id, base_url):
    log.info("get_history")
    with urllib.request.urlopen(f"{base_url}/history/{prompt_id}") as response:
        return json.loads(response.read())


def get_images(ws, prompt, client_id, base_url):
    prompt_id = queue_prompt(prompt, client_id, base_url)["prompt_id"]
    output_images = []
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    break  # Execution is done
        else:
            continue  # previews are binary data

    history = get_history(prompt_id, base_url)[prompt_id]
    for o in history["outputs"]:
        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "images" in node_output:
                for image in node_output["images"]:
                    url = get_image_url(
                        image["filename"], image["subfolder"], image["type"], base_url
                    )
                    output_images.append({"url": url})
    return {"data": output_images}


class ComfyUINodeInput(BaseModel):
    field: Optional[str] = None
    node_id: str
    key: Optional[str] = "text"
    value: Optional[str] = None


class ComfyUIWorkflow(BaseModel):
    workflow: str
    nodes: list[ComfyUINodeInput]


class ComfyUIGenerateImageForm(BaseModel):
    workflow: ComfyUIWorkflow

    prompt: str
    negative_prompt: Optional[str] = None
    width: int
    height: int
    n: int = 1

    steps: Optional[int] = None
    seed: Optional[int] = None


async def comfyui_generate_image(
    model: str, payload: ComfyUIGenerateImageForm, client_id, base_url
):
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    workflow = json.loads(payload.workflow.workflow)

    for node in payload.workflow.nodes:
        if node.field:
            if node.field == "model":
                workflow[node.node_id]["inputs"][node.key] = model
            elif node.field == "prompt":
                workflow[node.node_id]["inputs"]["text"] = payload.prompt
            elif node.field == "negative_prompt":
                workflow[node.node_id]["inputs"]["text"] = payload.negative_prompt
            elif node.field == "width":
                workflow[node.node_id]["inputs"]["width"] = payload.width
            elif node.field == "height":
                workflow[node.node_id]["inputs"]["height"] = payload.height
            elif node.field == "n":
                workflow[node.node_id]["inputs"]["batch_size"] = payload.n
            elif node.field == "steps":
                workflow[node.node_id]["inputs"]["steps"] = payload.steps
            elif node.field == "seed":
                workflow[node.node_id]["inputs"]["seed"] = (
                    payload.seed
                    if payload.seed
                    else random.randint(0, 18446744073709551614)
                )
        else:
            workflow[node.node_id]["inputs"][node.key] = node.value

    try:
        ws = websocket.WebSocket()
        ws.connect(f"{ws_url}/ws?clientId={client_id}")
        log.info("WebSocket connection established.")
    except Exception as e:
        log.exception(f"Failed to connect to WebSocket server: {e}")
        return None

    try:
        images = await asyncio.to_thread(get_images, ws, workflow, client_id, base_url)
    except Exception as e:
        log.exception(f"Error while receiving images: {e}")
        images = None

    ws.close()

    return images
