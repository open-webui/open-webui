import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
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

COMFYUI_DEFAULT_PROMPT = """
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
      "text": "Negative Prompt",
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

FLUX_DEFAULT_PROMPT = """
{
    "5": {
        "inputs": {
            "width": 1024,
            "height": 1024,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
            "text": "Input Text Here",
            "clip": [
                "11",
                0
            ]
        },
        "class_type": "CLIPTextEncode"
    },
    "8": {
        "inputs": {
            "samples": [
                "13",
                0
            ],
            "vae": [
                "10",
                0
            ]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "filename_prefix": "ComfyUI",
            "images": [
                "8",
                0
            ]
        },
        "class_type": "SaveImage"
    },
    "10": {
        "inputs": {
            "vae_name": "ae.sft"
        },
        "class_type": "VAELoader"
    },
    "11": {
        "inputs": {
            "clip_name1": "clip_l.safetensors",
            "clip_name2": "t5xxl_fp16.safetensors",
            "type": "flux"
        },
        "class_type": "DualCLIPLoader"
    },
    "12": {
        "inputs": {
            "unet_name": "flux1-dev.sft",
            "weight_dtype": "default"
        },
        "class_type": "UNETLoader"
    },
    "13": {
        "inputs": {
            "noise": [
                "25",
                0
            ],
            "guider": [
                "22",
                0
            ],
            "sampler": [
                "16",
                0
            ],
            "sigmas": [
                "17",
                0
            ],
            "latent_image": [
                "5",
                0
            ]
        },
        "class_type": "SamplerCustomAdvanced"
    },
    "16": {
        "inputs": {
            "sampler_name": "euler"
        },
        "class_type": "KSamplerSelect"
    },
    "17": {
        "inputs": {
            "scheduler": "simple",
            "steps": 20,
            "denoise": 1,
            "model": [
                "12",
                0
            ]
        },
        "class_type": "BasicScheduler"
    },
    "22": {
        "inputs": {
            "model": [
                "12",
                0
            ],
            "conditioning": [
                "6",
                0
            ]
        },
        "class_type": "BasicGuider"
    },
    "25": {
        "inputs": {
            "noise_seed": 778937779713005
        },
        "class_type": "RandomNoise"
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


class ImageGenerationPayload(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    steps: Optional[int] = None
    seed: Optional[int] = None
    width: int
    height: int
    n: int = 1
    cfg_scale: Optional[float] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    sd3: Optional[bool] = None
    flux: Optional[bool] = None
    flux_weight_dtype: Optional[str] = None
    flux_fp8_clip: Optional[bool] = None


def comfyui_generate_image(
    model: str, payload: ImageGenerationPayload, client_id, base_url
):
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")

    comfyui_prompt = json.loads(COMFYUI_DEFAULT_PROMPT)

    if payload.cfg_scale:
        comfyui_prompt["3"]["inputs"]["cfg"] = payload.cfg_scale

    if payload.sampler:
        comfyui_prompt["3"]["inputs"]["sampler"] = payload.sampler

    if payload.scheduler:
        comfyui_prompt["3"]["inputs"]["scheduler"] = payload.scheduler

    if payload.sd3:
        comfyui_prompt["5"]["class_type"] = "EmptySD3LatentImage"

    if payload.steps:
        comfyui_prompt["3"]["inputs"]["steps"] = payload.steps

    comfyui_prompt["4"]["inputs"]["ckpt_name"] = model
    comfyui_prompt["7"]["inputs"]["text"] = payload.negative_prompt
    comfyui_prompt["3"]["inputs"]["seed"] = (
        payload.seed if payload.seed else random.randint(0, 18446744073709551614)
    )

    # as Flux uses a completely different workflow, we must treat it specially
    if payload.flux:
        comfyui_prompt = json.loads(FLUX_DEFAULT_PROMPT)
        comfyui_prompt["12"]["inputs"]["unet_name"] = model
        comfyui_prompt["25"]["inputs"]["noise_seed"] = (
            payload.seed if payload.seed else random.randint(0, 18446744073709551614)
        )

        if payload.sampler:
            comfyui_prompt["16"]["inputs"]["sampler_name"] = payload.sampler

        if payload.steps:
            comfyui_prompt["17"]["inputs"]["steps"] = payload.steps

        if payload.scheduler:
            comfyui_prompt["17"]["inputs"]["scheduler"] = payload.scheduler

        if payload.flux_weight_dtype:
            comfyui_prompt["12"]["inputs"]["weight_dtype"] = payload.flux_weight_dtype

        if payload.flux_fp8_clip:
            comfyui_prompt["11"]["inputs"][
                "clip_name2"
            ] = "t5xxl_fp8_e4m3fn.safetensors"

    comfyui_prompt["5"]["inputs"]["batch_size"] = payload.n
    comfyui_prompt["5"]["inputs"]["width"] = payload.width
    comfyui_prompt["5"]["inputs"]["height"] = payload.height

    # set the text prompt for our positive CLIPTextEncode
    comfyui_prompt["6"]["inputs"]["text"] = payload.prompt

    try:
        ws = websocket.WebSocket()
        ws.connect(f"{ws_url}/ws?clientId={client_id}")
        log.info("WebSocket connection established.")
    except Exception as e:
        log.exception(f"Failed to connect to WebSocket server: {e}")
        return None

    try:
        images = get_images(ws, comfyui_prompt, client_id, base_url)
    except Exception as e:
        log.exception(f"Error while receiving images: {e}")
        images = None

    ws.close()

    return images
