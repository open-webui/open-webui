import asyncio
import json
import logging
import random
import urllib.parse
import urllib.request
import uuid
from typing import Optional, List, Dict, Any, Set

import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["COMFYUI"])

default_headers = {"User-Agent": "Open-WebUI"}


# Function to queue a prompt execution
def queue_prompt(prompt: Dict[str, Any], client_id: str, base_url: str, api_key: Optional[str]):
    log.debug(f"Queueing prompt for client {client_id}")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")

    headers = {**default_headers, "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(f"{base_url}/prompt", data=data, headers=headers)
        response = urllib.request.urlopen(req)
        if response.status != 200:
            raise Exception(f"Failed to queue prompt: {response.reason} ({response.status})")
        response_data = response.read()
        log.debug(f"Queue prompt response: {response_data}")
        return json.loads(response_data)
    except urllib.error.HTTPError as e:
        log.error(f"HTTP Error {e.code} while queuing prompt: {e.reason}")
        try:
            log.error(f"Error details: {e.read().decode()}")
        except Exception:
            pass
        raise e
    except Exception as e:
        log.exception(f"Error while queuing prompt: {e}")
        raise e


# Function to get image URL (does not require API key usually)
def get_image_url(filename: str, subfolder: str, folder_type: str, base_url: str) -> str:
    log.debug(f"Getting image URL for {filename}")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    url = f"{base_url}/view?{url_values}"
    log.debug(f"Image URL: {url}")
    return url


# Function to get history of a prompt execution
def get_history(prompt_id: str, base_url: str, api_key: Optional[str]) -> Dict[str, Any]:
    log.debug(f"Getting history for prompt ID {prompt_id}")
    headers = {**default_headers}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(f"{base_url}/history/{prompt_id}", headers=headers)
        response = urllib.request.urlopen(req)
        if response.status != 200:
            raise Exception(
                f"Failed to get history: {response.reason} ({response.status})"
            )
        response_data = response.read()
        log.debug(f"Get history response: {response_data}")
        return json.loads(response_data)
    except urllib.error.HTTPError as e:
        log.error(f"HTTP Error {e.code} while getting history: {e.reason}")
        try:
            log.error(f"Error details: {e.read().decode()}")
        except Exception:
            pass
        raise e
    except Exception as e:
        log.exception(f"Error while getting history: {e}")
        raise e


# Function to get images from WebSocket messages
def get_images(
    ws: websocket.WebSocket,
    prompt: Dict[str, Any],
    client_id: str,
    base_url: str,
    api_key: Optional[str],
) -> Dict[str, List[Dict[str, str]]]:
    log.info("Attempting to queue prompt and get images via WebSocket")
    prompt_id = queue_prompt(prompt, client_id, base_url, api_key)["prompt_id"]
    log.info(f"Prompt queued with ID: {prompt_id}")

    output_images = []
    execution_done = False
    execution_error = None

    while not execution_done:
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                log.debug(f"Received WebSocket message: {message}")
                if message["type"] == "status":
                    data = message["data"]
                    if data["status"]["exec_info"]["queue_remaining"] == 0:
                        log.debug("Queue is empty, potentially done.")
                        # Optional: Add a small delay or further checks if needed
                        pass
                elif message["type"] == "executing":
                    data = message["data"]
                    # Check if execution is done for our prompt_id
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        log.info(f"Execution finished for prompt ID: {prompt_id}")
                        execution_done = True
                        break
                elif message["type"] == "execution_error":
                    data = message["data"]
                    if data.get("prompt_id") == prompt_id:
                        log.error(f"Execution error for prompt ID {prompt_id}: {data}")
                        execution_error = data
                        execution_done = True # Stop processing on error
                        break
                elif message["type"] == "executed":
                    data = message["data"]
                    if data.get("prompt_id") == prompt_id:
                        log.debug(f"Node executed for prompt ID {prompt_id}: {data.get('node')}")
                        # Process outputs if needed immediately, but history call is more reliable
                        pass

            else:
                # Binary data usually means previews, ignore for final output
                log.debug("Received binary data (likely preview), ignoring.")
                continue
        except websocket.WebSocketTimeoutException:
            log.warning("WebSocket receive timed out, continuing...")
            continue
        except websocket.WebSocketConnectionClosedException:
            log.error("WebSocket connection closed unexpectedly.")
            raise
        except json.JSONDecodeError:
            log.warning(f"Received non-JSON message: {out}")
            continue
        except Exception as e:
            log.exception(f"Error processing WebSocket message: {e}")
            raise # Re-raise unexpected errors

    if execution_error:
        raise Exception(f"ComfyUI execution failed: {execution_error}")

    log.info(f"Fetching history for completed prompt ID: {prompt_id}")
    history_data = get_history(prompt_id, base_url, api_key)

    if prompt_id not in history_data:
        log.error(f"Prompt ID {prompt_id} not found in history response.")
        return {"data": []}

    history = history_data[prompt_id]
    log.debug(f"History data: {history}")

    # Extract images from the history outputs
    if "outputs" in history:
        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "images" in node_output:
                log.debug(f"Found images in output node {node_id}")
                for image in node_output["images"]:
                    if (
                        "filename" in image
                        and "subfolder" in image
                        and "type" in image
                    ):
                        url = get_image_url(
                            image["filename"],
                            image["subfolder"],
                            image["type"],
                            base_url,
                        )
                        output_images.append({"url": url})
                    else:
                        log.warning(f"Skipping image data due to missing keys: {image}")
            # Add check for other potential output types if necessary
            # elif "gifs" in node_output: # Example for handling gifs if workflows produce them
            #     log.debug(f"Found gifs in output node {node_id}")
            #     for gif in node_output["gifs"]:
            #          if "filename" in gif and "subfolder" in gif and "type" in gif:
            #               url = get_image_url(gif["filename"], gif["subfolder"], gif["type"], base_url)
            #               # Decide how to handle gifs, maybe add a different key?
            #               output_images.append({"url": url, "format": "gif"})


    log.info(f"Found {len(output_images)} images for prompt ID {prompt_id}")
    return {"data": output_images}


# Pydantic model matching the structure from the frontend
class ComfyUINodeInput(BaseModel):
    type: str  # e.g., "KSampler::seed", "CLIPTextEncode::text"
    key: str  # e.g., "seed", "text"
    node_ids: List[str] = Field(default_factory=list) # List of node IDs as strings, e.g., ["6", "10"]

    # Make hashable for use in sets
    def __hash__(self):
        # Hash based on type, key, and sorted tuple of node_ids
        return hash((self.type, self.key, tuple(sorted(self.node_ids))))

    def __eq__(self, other):
        if not isinstance(other, ComfyUINodeInput):
            return NotImplemented
        return (self.type == other.type and
                self.key == other.key and
                set(self.node_ids) == set(other.node_ids))


# Pydantic model for the workflow structure
class ComfyUIWorkflow(BaseModel):
    workflow: str # The raw JSON string of the workflow
    nodes: List[ComfyUINodeInput] = Field(default_factory=list) # List of configured node inputs


# Pydantic model for the overall image generation request
class ComfyUIGenerateImageForm(BaseModel):
    workflow: ComfyUIWorkflow
    model: Optional[str] = None # The model name/ID selected by the user

    prompt: str
    negative_prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    n: int = 1 # Number of images to generate (batch size)

    steps: Optional[int] = None
    seed: Optional[int] = None # If None, a random seed will be used


# Main function to generate images using ComfyUI
async def comfyui_generate_image(
    payload: ComfyUIGenerateImageForm,
    client_id: str, # Unique client ID for WebSocket connection
    base_url: str,
    api_key: Optional[str],
) -> Optional[Dict[str, List[Dict[str, str]]]]:
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    log.info(f"Connecting to ComfyUI WebSocket: {ws_url}")

    try:
        # Load the base workflow from the JSON string
        workflow = json.loads(payload.workflow.workflow)
        log.debug("Successfully parsed base workflow JSON.")
    except json.JSONDecodeError as e:
        log.error(f"Invalid ComfyUI Workflow JSON provided: {e}")
        raise ValueError(f"Invalid ComfyUI Workflow JSON: {e}")

    # --- Apply standard parameters based on configured nodes ---
    parameters_to_apply = {
        "prompt": payload.prompt,
        "negative_prompt": payload.negative_prompt,
        "seed": payload.seed if payload.seed is not None else random.randint(0, 18446744073709551615),
        "steps": payload.steps,
        # "cfg": payload.cfg, # If CFG scale is added to payload later
        "model": payload.model,
        "width": payload.width,
        "height": payload.height,
        "batch_size": payload.n,
        # Add other potential parameters like sampler_name, scheduler if needed
    }

    # Map standard parameter names to expected keys and potentially types
    # This helps find the right node config from the frontend settings
    expected_node_signatures = {
        "prompt": {"key": "text", "common_types": ["CLIPTextEncode::text"]},
        "negative_prompt": {"key": "text", "common_types": ["CLIPTextEncode::text"]},
        "seed": {"key": "seed", "common_types": ["KSampler::seed", "KSamplerAdvanced::seed"]},
        "steps": {"key": "steps", "common_types": ["KSampler::steps", "KSamplerAdvanced::steps"]},
        "cfg": {"key": "cfg", "common_types": ["KSampler::cfg", "KSamplerAdvanced::cfg"]},
        "model": {"key": "ckpt_name", "common_types": ["CheckpointLoaderSimple::ckpt_name", "CheckpointLoader::ckpt_name"]},
        "width": {"key": "width", "common_types": ["EmptyLatentImage::width"]},
        "height": {"key": "height", "common_types": ["EmptyLatentImage::height"]},
        "batch_size": {"key": "batch_size", "common_types": ["EmptyLatentImage::batch_size"]},
        # Add more mappings as needed (sampler, scheduler, etc.)
    }

    applied_node_configs: Set[ComfyUINodeInput] = set() # Keep track of configs used to avoid double application

    for param_name, param_value in parameters_to_apply.items():
        if param_value is None:
            log.debug(f"Skipping parameter '{param_name}' because its value is None.")
            continue

        if param_name not in expected_node_signatures:
            log.warning(f"No expected node signature defined for parameter '{param_name}'. Cannot apply automatically.")
            continue

        signature = expected_node_signatures[param_name]
        target_key = signature["key"]
        target_types = signature.get("common_types", [])

        found_config = None

        # 1. Try to find a matching config based on type (most specific) that hasn't been used
        for node_config in payload.workflow.nodes:
            if node_config.type in target_types and node_config not in applied_node_configs:
                # Special handling for prompt/negative_prompt ambiguity using the same type
                if param_name == "negative_prompt" and "prompt" in expected_node_signatures:
                    prompt_sig = expected_node_signatures["prompt"]
                    # Check if this exact config object was already used for the positive prompt
                    if node_config in applied_node_configs:
                         # We need to check if the config that was applied for 'prompt' is this one
                         # This requires iterating applied_node_configs, which is less efficient.
                         # A simpler check: if a config with the same type was already applied, skip.
                         # This assumes the user configured separate nodes/configs for pos/neg.
                         already_applied_for_prompt = any(
                             applied_config.type == node_config.type
                             for applied_config in applied_node_configs
                         )
                         if already_applied_for_prompt:
                             continue # Skip if a config of this type was already used (likely for positive prompt)

                found_config = node_config
                break # Found best match by type

        # 2. If no type match, try to find matching config based on key (less specific) that hasn't been used
        if not found_config:
            for node_config in payload.workflow.nodes:
                if node_config.key == target_key and node_config not in applied_node_configs:
                    # Special handling for prompt/negative_prompt ambiguity using the same key
                    if param_name == "negative_prompt" and "prompt" in expected_node_signatures:
                        prompt_sig = expected_node_signatures["prompt"]
                        # Check if a config with the same key was already applied
                        already_applied_for_prompt = any(
                             applied_config.key == node_config.key
                             for applied_config in applied_node_configs
                         )
                        if already_applied_for_prompt:
                            continue # Skip if a config with this key was already used

                    found_config = node_config
                    break # Found first available match by key

        if found_config:
            log.info(f"Applying parameter '{param_name}' (value: {param_value}) using config: type='{found_config.type}', key='{found_config.key}', nodes={found_config.node_ids}")
            applied_node_configs.add(found_config) # Mark this config as used

            for node_id in found_config.node_ids:
                if node_id in workflow:
                    if "inputs" not in workflow[node_id]:
                        workflow[node_id]["inputs"] = {}
                    # Use the key from the found config, which should match the target_key
                    workflow[node_id]["inputs"][found_config.key] = param_value
                    log.debug(f"Set workflow[{node_id}]['inputs']['{found_config.key}'] = {param_value}")
                else:
                    log.warning(f"Node ID '{node_id}' configured for '{found_config.type}' not found in the workflow JSON.")
        else:
            log.warning(f"Could not find a suitable node configuration in frontend settings for parameter '{param_name}'. It will not be applied.")


    # --- WebSocket Connection and Execution ---
    ws = None
    try:
        ws = websocket.WebSocket()
        # Set timeout for blocking operations like recv
        ws.settimeout(60) # 60 seconds timeout for receiving messages

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Connect using the client ID
        ws_connect_url = f"{ws_url}/ws?clientId={client_id}"
        log.info(f"Connecting to WebSocket: {ws_connect_url}")
        ws.connect(ws_connect_url, header=headers)
        log.info("WebSocket connection established.")

        log.info("Sending modified workflow to ComfyUI.")
        log.debug(f"Final Workflow JSON: {json.dumps(workflow, indent=2)}")

        # Run the blocking WebSocket communication in a separate thread
        images = await asyncio.to_thread(
            get_images, ws, workflow, client_id, base_url, api_key
        )
        log.info("Image generation process completed.")

    except websocket.WebSocketException as e:
        log.exception(f"WebSocket error during ComfyUI communication: {e}")
        raise ConnectionError(f"ComfyUI WebSocket error: {e}")
    except urllib.error.URLError as e:
         log.exception(f"URL error connecting to ComfyUI: {e.reason}")
         raise ConnectionError(f"Could not connect to ComfyUI at {base_url}: {e.reason}")
    except ConnectionRefusedError:
        log.exception(f"Connection refused by ComfyUI server at {base_url}.")
        raise ConnectionError(f"Connection refused by ComfyUI server at {base_url}.")
    except Exception as e:
        log.exception(f"An unexpected error occurred during ComfyUI image generation: {e}")
        raise # Re-raise other exceptions
    finally:
        if ws and ws.connected:
            log.info("Closing WebSocket connection.")
            ws.close()

    return images


# Example usage (for testing purposes, replace with actual integration)
async def main_test():
    # --- Mock Payload ---
    mock_workflow_json = """
    {
      "3": {
        "inputs": {
          "seed": 8566257,
          "steps": 20,
          "cfg": 8,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 1,
          "model": [ "4", 0 ],
          "positive": [ "6", 0 ],
          "negative": [ "7", 0 ],
          "latent_image": [ "5", 0 ]
        },
        "class_type": "KSampler",
        "_meta": { "title": "KSampler" }
      },
      "4": {
        "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" },
        "class_type": "CheckpointLoaderSimple",
        "_meta": { "title": "Load Checkpoint" }
      },
      "5": {
        "inputs": { "width": 1024, "height": 1024, "batch_size": 1 },
        "class_type": "EmptyLatentImage",
        "_meta": { "title": "Empty Latent Image" }
      },
      "6": {
        "inputs": {
          "text": "masterpiece, best quality, a futuristic cityscape under a starry night",
          "clip": [ "4", 1 ]
        },
        "class_type": "CLIPTextEncode",
        "_meta": { "title": "CLIP Text Encode (Prompt)" }
      },
      "7": {
        "inputs": { "text": "worst quality, low quality, blurry", "clip": [ "4", 1 ] },
        "class_type": "CLIPTextEncode",
        "_meta": { "title": "CLIP Text Encode (Negative Prompt)" }
      },
      "8": {
        "inputs": { "samples": [ "3", 0 ], "vae": [ "4", 2 ] },
        "class_type": "VAEDecode",
        "_meta": { "title": "VAE Decode" }
      },
      "9": {
        "inputs": { "filename_prefix": "ComfyUI", "images": [ "8", 0 ] },
        "class_type": "SaveImage",
        "_meta": { "title": "Save Image" }
      }
    }
    """
    mock_payload = ComfyUIGenerateImageForm(
        workflow=ComfyUIWorkflow(
            workflow=mock_workflow_json,
            nodes=[
                ComfyUINodeInput(type="CheckpointLoaderSimple::ckpt_name", key="ckpt_name", node_ids=["4"]),
                ComfyUINodeInput(type="CLIPTextEncode::text", key="text", node_ids=["6"]), # Positive Prompt
                ComfyUINodeInput(type="CLIPTextEncode::text", key="text", node_ids=["7"]), # Negative Prompt
                ComfyUINodeInput(type="EmptyLatentImage::width", key="width", node_ids=["5"]),
                ComfyUINodeInput(type="EmptyLatentImage::height", key="height", node_ids=["5"]),
                ComfyUINodeInput(type="EmptyLatentImage::batch_size", key="batch_size", node_ids=["5"]),
                ComfyUINodeInput(type="KSampler::seed", key="seed", node_ids=["3"]),
                ComfyUINodeInput(type="KSampler::steps", key="steps", node_ids=["3"]),
            ]
        ),
        model="sd_xl_refiner_1.0.safetensors", # Example: Override model
        prompt="A beautiful painting of a sunset over mountains, fantasy art",
        negative_prompt="ugly, deformed, noisy, text, words",
        width=768,
        height=512,
        n=1,
        steps=25,
        seed=123456789
    )

    # --- Connection Details (Replace with your actual ComfyUI instance) ---
    comfyui_base_url = "http://127.0.0.1:8188" # Your ComfyUI URL
    comfyui_api_key = None # Your ComfyUI API Key if you use one
    client_id = str(uuid.uuid4()) # Generate a unique client ID

    logging.basicConfig(level=logging.DEBUG)
    log.info("Starting ComfyUI image generation test...")

    try:
        result = await comfyui_generate_image(
            payload=mock_payload,
            client_id=client_id,
            base_url=comfyui_base_url,
            api_key=comfyui_api_key,
        )
        log.info("ComfyUI generation finished.")
        if result:
            log.info(f"Generated images: {json.dumps(result, indent=2)}")
        else:
            log.warning("Image generation returned no result.")
    except Exception as e:
        log.exception(f"Test failed with error: {e}")

# To run the test:
# if __name__ == "__main__":
#     asyncio.run(main_test())