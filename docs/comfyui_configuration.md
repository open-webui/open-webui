# ComfyUI Configuration in OpenWebUI

This document outlines the configuration settings required to integrate ComfyUI with OpenWebUI.

## Environment Variables

To enable ComfyUI integration, you need to configure the following environment variables in your OpenWebUI setup:

- **`COMFYUI_BASE_URL`**: The base URL of your ComfyUI instance. For example, `http://localhost:8188`.
- **`COMFYUI_API_KEY`**: (Optional) The API key for your ComfyUI instance, if required.
- **`COMFYUI_WORKFLOW`**: A JSON string that defines the ComfyUI workflow graph. This graph represents the series of nodes and connections that will be executed to generate images.
- **`COMFYUI_WORKFLOW_NODES`**: A JSON string that maps OpenWebUI's generation parameters to specific inputs of nodes within the ComfyUI workflow defined in `COMFYUI_WORKFLOW`.

## `COMFYUI_WORKFLOW`

The `COMFYUI_WORKFLOW` environment variable stores the entire ComfyUI workflow as a JSON string. This JSON object represents the graph of nodes and their connections. You can obtain this JSON by:

1.  **Exporting from ComfyUI:** In the ComfyUI interface, build your desired workflow. Then, use the "Save (API Format)" option (or similar, depending on your ComfyUI version) to export the workflow as a JSON file.
2.  **Copying the JSON content:** Open the exported JSON file and copy its entire content. This content will be the value for your `COMFYUI_WORKFLOW` environment variable.

**Example:**

A simplified `COMFYUI_WORKFLOW` might look like this (actual workflows are typically much more complex):

```json
{
  "3": {
    "inputs": {
      "seed": 0,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "positive prompt",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "negative prompt",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Negative Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": ["3", 0],
      "vae": ["4", 2]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["8", 0]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}
```

**Note:** The node IDs (e.g., "3", "4", "5") are important as they are used in `COMFYUI_WORKFLOW_NODES` to target specific node inputs.

## `COMFYUI_WORKFLOW_NODES`

The `COMFYUI_WORKFLOW_NODES` environment variable is a JSON string that defines how OpenWebUI's image generation parameters (like prompt, negative prompt, seed, model, etc.) are mapped to the inputs of specific nodes within your `COMFYUI_WORKFLOW`.

This mapping allows OpenWebUI to dynamically control the ComfyUI workflow based on user input or application settings.

The basic structure of `COMFYUI_WORKFLOW_NODES` is a JSON object where each key is an OpenWebUI parameter name, and the value is an object specifying the target ComfyUI node ID and the input field within that node.

```json
{
  "OPENWEBUI_PARAMETER_NAME": {
    "node_id": "COMFYUI_NODE_ID",
    "input_field": "COMFYUI_NODE_INPUT_FIELD_NAME"
  },
  // ... more mappings
}
```

### Mapping OpenWebUI Parameters

Here's a detailed explanation of how to map common OpenWebUI parameters:

-   **`prompt` (Positive Prompt)**: Maps the user's positive prompt to a text input field, typically in a `CLIPTextEncode` node.
-   **`negative_prompt` (Negative Prompt)**: Maps the user's negative prompt to another text input field, also usually in a `CLIPTextEncode` node.
-   **`model` (Model Checkpoint)**: Maps the selected model name to the checkpoint name input of a `CheckpointLoaderSimple` node or similar.
-   **`width` (Image Width)**: Maps the desired image width to the width input of a node that defines latent image dimensions (e.g., `EmptyLatentImage`).
-   **`height` (Image Height)**: Maps the desired image height to the height input of the same latent image dimension node.
-   **`seed`**: Maps the generation seed to the seed input of a `KSampler` node or a node that initializes randomness.
-   **`steps`**: Maps the number of sampling steps to the steps input of a `KSampler` node.
-   **`n` (Batch Size)**: Maps the desired number of images to generate (batch size) to the `batch_size` input of a node like `EmptyLatentImage`.

### Examples for `COMFYUI_WORKFLOW_NODES`

Let's assume your `COMFYUI_WORKFLOW` has nodes with the following IDs and relevant input fields (referencing the example workflow above):

-   Node `4` (`CheckpointLoaderSimple`): input `ckpt_name`
-   Node `5` (`EmptyLatentImage`): inputs `width`, `height`, `batch_size`
-   Node `6` (`CLIPTextEncode` for positive prompt): input `text`
-   Node `7` (`CLIPTextEncode` for negative prompt): input `text`
-   Node `3` (`KSampler`): inputs `seed`, `steps`

Here’s how you would configure `COMFYUI_WORKFLOW_NODES` for this scenario:

```json
{
  "prompt": {
    "node_id": "6",
    "input_field": "text"
  },
  "negative_prompt": {
    "node_id": "7",
    "input_field": "text"
  },
  "model": {
    "node_id": "4",
    "input_field": "ckpt_name"
  },
  "width": {
    "node_id": "5",
    "input_field": "width"
  },
  "height": {
    "node_id": "5",
    "input_field": "height"
  },
  "seed": {
    "node_id": "3",
    "input_field": "seed"
  },
  "steps": {
    "node_id": "3",
    "input_field": "steps"
  },
  "n": {
    "node_id": "5",
    "input_field": "batch_size"
  }
}
```

**Explanation:**

-   When a user enters a "prompt" in OpenWebUI, its value will be sent to the `text` input of node `6` in your ComfyUI workflow.
-   If the user selects a "model" in OpenWebUI, that model's name (e.g., "sd_xl_base_1.0.safetensors") will be sent to the `ckpt_name` input of node `4`.
-   If the user sets the image "width" to 512, this value will update the `width` input of node `5`.
-   And so on for all other mapped parameters.

By configuring these environment variables correctly, OpenWebUI can effectively leverage ComfyUI as a powerful backend for image generation, allowing for complex and customizable workflows.

## Image Generation Workflow Outline

This section outlines the steps involved when OpenWebUI generates an image using ComfyUI as the backend.

1.  **User Request:** The process begins when a user initiates an image generation request from the OpenWebUI interface. This request is sent to the `/images/generations` API endpoint in the OpenWebUI backend. The request payload includes parameters such as the positive prompt, negative prompt, desired image dimensions (width and height), selected model, seed, steps, etc.

2.  **Request Handling in `routers/images.py`:**
    The `/images/generations` endpoint is handled by the `routers.images.generations_router`. When ComfyUI is configured as the image generation engine (i.e., `COMFYUI_BASE_URL` is set), this router identifies that the request should be processed by the ComfyUI integration.

3.  **Invoking `comfyui_generate_image`:**
    The core logic for ComfyUI integration resides in the `utils.images.comfyui.comfyui_generate_image` function. The request handler in `routers/images.py` calls this function, passing along the user's generation parameters and the application's ComfyUI configuration (workflow and node mappings).

4.  **Dynamic Workflow Modification in `comfyui_generate_image`:**
    The `comfyui_generate_image` function performs the crucial step of preparing the ComfyUI workflow for execution:
    *   **Load Base Workflow:** It starts by loading the base ComfyUI workflow defined in the `COMFYUI_WORKFLOW` environment variable. This workflow is a JSON string representing the graph of nodes and their default connections.
    *   **Apply Dynamic Parameters:** It then iterates through the `COMFYUI_WORKFLOW_NODES` mappings. For each parameter defined in `COMFYUI_WORKFLOW_NODES` (e.g., "prompt", "model", "width", "seed"), it checks if the user's request contains a corresponding value.
    *   If a value is present in the user's request (e.g., the user provided a specific prompt or selected a model), `comfyui_generate_image` updates the input field of the target ComfyUI node (specified in `COMFYUI_WORKFLOW_NODES`) with this new value. For instance, if `COMFYUI_WORKFLOW_NODES` maps "prompt" to node "6", input "text", the `text` input of node "6" in the workflow JSON will be updated with the user's prompt.
    *   This dynamic modification ensures that the ComfyUI workflow is tailored for each specific image generation request, reflecting the user's exact requirements.

5.  **ComfyUI API Interaction:**
    Once the workflow JSON is dynamically updated, `comfyui_generate_image` sends this modified workflow to the ComfyUI server via its API (using the `COMFYUI_BASE_URL`). ComfyUI then executes this workflow.

6.  **Image Retrieval and Response:**
    ComfyUI processes the workflow, generates the image(s), and returns them. The `comfyui_generate_image` function receives the generated image data from ComfyUI, saves it appropriately (e.g., to a temporary file or in-memory), and then returns the image path or data back to the `routers/images.py` handler.

7.  **Response to User:** Finally, `routers/images.py` sends the generated image(s) back to the OpenWebUI frontend, where it is displayed to the user.

This dynamic workflow modification is key to the flexibility of the ComfyUI integration, allowing a single base workflow to be adapted for a wide variety of image generation tasks based on user input.

## Interaction with the ComfyUI Server

Once the ComfyUI workflow has been dynamically prepared by `utils.images.comfyui.comfyui_generate_image`, OpenWebUI interacts with the ComfyUI server to execute it and retrieve the generated images. This interaction primarily involves an HTTP request to queue the prompt and a WebSocket connection to monitor its progress.

1.  **Establishing WebSocket Connection:**
    OpenWebUI establishes a WebSocket connection to the ComfyUI server to receive real-time updates about the workflow execution.
    *   **URL Derivation:** The WebSocket URL is typically derived from the `COMFYUI_BASE_URL`. If `COMFYUI_BASE_URL` is `http://localhost:8188`, the WebSocket URL will be `ws://localhost:8188/ws`.
    *   **Client ID:** A unique `client_id` (generated by OpenWebUI) is usually passed as a query parameter to the WebSocket URL (e.g., `ws://localhost:8188/ws?clientId=YOUR_UNIQUE_CLIENT_ID`). This helps ComfyUI associate the WebSocket connection with subsequent API requests.
    *   **API Key:** If `COMFYUI_API_KEY` is configured, it might be used for authentication, potentially as part of the WebSocket handshake or in other API requests, depending on the ComfyUI server's security setup.

2.  **Queueing the Workflow (Prompt Submission):**
    To initiate the image generation, OpenWebUI sends the dynamically modified workflow to the ComfyUI server.
    *   **HTTP POST Request:** This is done by making an HTTP POST request to ComfyUI's `/prompt` endpoint (e.g., `http://localhost:8188/prompt`).
    *   **JSON Payload:** The payload of this POST request is a JSON object containing:
        *   `prompt`: This key holds the entire dynamically modified ComfyUI workflow graph (the JSON object prepared in the previous steps).
        *   `client_id`: The same unique `client_id` that was used for the WebSocket connection. This allows ComfyUI to link the HTTP request to the specific client's WebSocket session.
        *   Optionally, `front`: A boolean flag (typically `true`) indicating that this prompt originated from a user-facing interface.

    **Example Payload to `/prompt`:**
    ```json
    {
      "prompt": { /* ... entire modified workflow graph ... */ },
      "client_id": "YOUR_UNIQUE_CLIENT_ID",
      "front": true
    }
    ```

3.  **Receiving `prompt_id`:**
    If the workflow is successfully queued, ComfyUI's `/prompt` endpoint responds with a JSON object containing:
    *   `prompt_id`: A unique identifier for the queued workflow execution instance. This ID is crucial for tracking the progress of this specific job.
    *   `number`: The position of the prompt in the queue.
    *   `node_errors`: Any errors detected in the workflow structure before execution.

4.  **Monitoring Execution via WebSocket:**
    OpenWebUI uses the established WebSocket connection to listen for messages from the ComfyUI server. These messages provide real-time status updates about the queued prompts.
    *   **Message Structure:** ComfyUI sends various types of messages over WebSocket. Key messages include:
        *   `status`: Indicates the overall server status, including the current queue size.
        *   `execution_start`: Signals that a specific `prompt_id` has started processing.
        *   `executing`: Indicates that a specific node within the workflow for a given `prompt_id` is currently executing. This message often includes the `node_id` of the currently running node.
        *   `executed`: Signals that the workflow associated with a `prompt_id` has finished execution. This message typically contains `output` data, which includes information about the generated images (e.g., filenames, subfolder).
        *   `progress`: Provides progress updates for long-running nodes (e.g., KSampler), showing `value` (current step) and `max` (total steps).
    *   **Tracking Completion:** OpenWebUI listens for messages related to its submitted `prompt_id`. When a message arrives indicating that this `prompt_id` has been `executed` (or if errors occur), OpenWebUI knows that the image generation process for that request is complete. The output data from the `executed` message is then used to retrieve the actual image files.

This combination of HTTP requests for job submission and WebSocket communication for real-time feedback allows OpenWebUI to effectively manage and monitor image generation tasks delegated to a ComfyUI server.

## ComfyUI Response and Image Retrieval

After the ComfyUI server indicates via WebSocket that the execution for a specific `prompt_id` is complete, OpenWebUI needs to retrieve the details of the generated output, particularly the images.

1.  **Fetching Execution History:**
    Once OpenWebUI knows that a prompt has finished (e.g., by receiving an `executed` message over WebSocket for the relevant `prompt_id`), it makes an HTTP GET request to ComfyUI's `/history/{prompt_id}` endpoint.
    *   The `{prompt_id}` in the URL is the specific ID received when the prompt was initially queued.
    *   For example, if `COMFYUI_BASE_URL` is `http://localhost:8188` and the `prompt_id` is `abc-123-xyz`, the request URL would be `http://localhost:8188/history/abc-123-xyz`.
    *   An API key (`COMFYUI_API_KEY`) might be included in the request headers if ComfyUI is configured to require it.

2.  **Understanding the `/history` JSON Response:**
    The ComfyUI server responds to the `/history/{prompt_id}` request with a JSON object. This object contains a detailed record of the executed workflow, including all inputs, outputs, and timing information for each node.
    *   The top-level key in this response is the `prompt_id` itself.
    *   Inside this, the most crucial parts for image retrieval are the `outputs` and `status` objects.
    *   The `status` object provides the execution status of the prompt, including success or failure and any error messages.
    *   The `outputs` object contains the results produced by each node in the workflow. The keys of the `outputs` object are the node IDs from the workflow.

    **Locating Image Data:**
    To find the generated images, OpenWebUI looks for the output of nodes that typically save images, such as a `SaveImage` node.
    *   Each entry in the `outputs` object (keyed by node ID) will contain an `images` array if that node produced image files.
    *   Each object within the `images` array provides details about a single generated image:
        *   `filename`: The name of the image file (e.g., `ComfyUI_00001_.png`).
        *   `subfolder`: The subfolder within ComfyUI's output directory where the image is stored (e.g., `YYYY-MM-DD/`). If empty, the image is in the main output directory.
        *   `type`: The type of output, typically `output` for final images or `temp` for previews/intermediate images. OpenWebUI is usually interested in `output` images.

    **Example Snippet of `/history/{prompt_id}` JSON Response:**

    ```json
    {
      "abc-123-xyz": { // This is the prompt_id
        "prompt": [
          // ... details of the prompt request ...
        ],
        "status": {
          "status_str": "success",
          "completed": true,
          "messages": [
            ["execution_start", {"prompt_id": "abc-123-xyz"}],
            // ... other status messages ...
            ["executed", {"node": "9", "output": {"images": [{"filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output"}]}, "prompt_id": "abc-123-xyz"}]
          ]
        },
        "outputs": {
          "9": { // Node ID (e.g., of a SaveImage node)
            "images": [
              {
                "filename": "ComfyUI_00001_.png",
                "subfolder": "", // Can be empty or contain a path like "YYYY-MM-DD/"
                "type": "output"
              },
              // Potentially more images if batch size > 1
            ]
          }
          // ... outputs of other nodes ...
        }
      }
    }
    ```

3.  **Constructing Image URLs:**
    Using the `filename`, `subfolder`, and `type` from the history response, OpenWebUI constructs direct URLs to view or download the generated images. These URLs point to ComfyUI's `/view` endpoint.
    *   The URL is formed as: `{COMFYUI_BASE_URL}/view?filename={filename}&subfolder={subfolder}&type={type}`.
    *   For example, using the snippet above and `COMFYUI_BASE_URL=http://localhost:8188`:
        `http://localhost:8188/view?filename=ComfyUI_00001_.png&subfolder=&type=output`

4.  **Return Value of `comfyui_generate_image`:**
    The `utils.images.comfyui.comfyui_generate_image` function in OpenWebUI's backend is responsible for this entire process. After successfully retrieving the image information from the `/history/{prompt_id}` endpoint, it typically returns a list of these constructed ComfyUI image URLs. These URLs are then further processed by OpenWebUI (e.g., to be displayed in the interface or stored).

By following this process, OpenWebUI can reliably retrieve the images generated by ComfyUI and make them accessible to the user.

## Image Handling within OpenWebUI

Once the `utils.images.comfyui.comfyui_generate_image` function returns a list of direct ComfyUI image URLs (pointing to ComfyUI's `/view` endpoint), the `routers/images.py` module in OpenWebUI takes over to process and store these images.

1.  **Receiving Image URLs:**
    The `generations_router` in `routers/images.py` receives the list of ComfyUI image URLs. Each URL in this list corresponds to a generated image that is currently stored on the ComfyUI server.

2.  **Fetching Image Binary Data:**
    For each ComfyUI image URL received, OpenWebUI's backend makes an HTTP GET request to that URL to download the actual image binary data.
    *   **Request Target:** The request is made to the ComfyUI server's `/view` endpoint (e.g., `http://{COMFYUI_BASE_URL}/view?filename=ComfyUI_00001_.png&subfolder=&type=output`).
    *   **Authentication:** If `COMFYUI_API_KEY` is configured in OpenWebUI's environment variables, this API key is included in the headers of the request to ComfyUI. This ensures that OpenWebUI is authorized to fetch the image, especially if the ComfyUI instance is secured.

3.  **Internal Storage:**
    After successfully downloading the image binary data from ComfyUI, OpenWebUI saves this data into its own internal file storage system.
    *   This storage is managed by OpenWebUI and is typically located within the `/data/uploads` directory (or a configured equivalent) inside the OpenWebUI Docker container or file system.
    *   Storing the image internally ensures that OpenWebUI does not rely on the ComfyUI server for long-term image availability. It also allows OpenWebUI to manage access control and serve images efficiently through its own backend.

4.  **Generating Internal OpenWebUI URLs:**
    For each image saved to its internal storage, OpenWebUI generates a new, internal URL. This URL points to an OpenWebUI API endpoint that serves the stored image.
    *   These internal URLs are typically relative to the OpenWebUI application's base URL (e.g., `/v1/images/uploads/xxxx-xxxx-xxxx.png` or similar).
    *   Using internal URLs decouples the client application from the ComfyUI server's storage and URL structure.

5.  **Final Response to Client:**
    The `generations_router` in `routers/images.py` then constructs the final JSON response that is sent back to the user's client application (e.g., the web browser).
    *   This JSON response contains the list of *internal OpenWebUI image URLs* generated in the previous step.
    *   Crucially, the client application receives these OpenWebUI-specific URLs, not the direct ComfyUI `/view` URLs. This means the client will request images directly from the OpenWebUI server, which then serves the internally stored copies.

This process ensures that images generated via ComfyUI are seamlessly integrated into the OpenWebUI environment, providing a consistent experience for the user and better control over image data for the OpenWebUI application.

## Key Data Structures and JSON Payloads Summary

This section provides a consolidated view of the key JSON structures and payloads involved in the OpenWebUI to ComfyUI integration.

1.  **`COMFYUI_WORKFLOW` (Environment Variable - JSON String):**
    This environment variable holds the base ComfyUI workflow as a JSON string.
    *Content is user-defined and exported from ComfyUI.*

    ```json
    {
      "3": {
        "inputs": {
          "seed": 1234567890,
          "steps": 25,
          "cfg": 7.5,
          "sampler_name": "dpmpp_2m_sde_gpu",
          "scheduler": "karras",
          "denoise": 1,
          "model": ["4", 0],
          "positive": ["6", 0],
          "negative": ["7", 0],
          "latent_image": ["5", 0]
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"}
      },
      "4": {
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load Checkpoint"}
      },
      "5": {
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        "class_type": "EmptyLatentImage",
        "_meta": {"title": "Empty Latent Image"}
      },
      "6": {
        "inputs": {"text": "A beautiful landscape painting", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt"}
      },
      "7": {
        "inputs": {"text": "ugly, blurry, low quality", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt"}
      },
      "9": {
        "inputs": {"filename_prefix": "OpenWebUI_Comfy", "images": ["3", 0]},
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"}
      }
    }
    ```
    *(Note: This is a simplified example. Actual workflows can be much more complex.)*

2.  **`COMFYUI_WORKFLOW_NODES` (Environment Variable - JSON String / Python Dict in `config.py`):**
    This configuration maps OpenWebUI parameters to specific inputs within the `COMFYUI_WORKFLOW`.
    *Content is user-defined based on their workflow.*

    As an environment variable (JSON string):
    ```json
    {
      "prompt": {"node_id": "6", "input_field": "text"},
      "negative_prompt": {"node_id": "7", "input_field": "text"},
      "model": {"node_id": "4", "input_field": "ckpt_name"},
      "width": {"node_id": "5", "input_field": "width"},
      "height": {"node_id": "5", "input_field": "height"},
      "seed": {"node_id": "3", "input_field": "seed"},
      "steps": {"node_id": "3", "input_field": "steps"},
      "n": {"node_id": "5", "input_field": "batch_size"}
    }
    ```
    How it might be represented if parsed into Python in `config.py`:
    ```python
    COMFYUI_WORKFLOW_NODES = {
      "prompt": {"node_id": "6", "input_field": "text"},
      "negative_prompt": {"node_id": "7", "input_field": "text"},
      "model": {"node_id": "4", "input_field": "ckpt_name"},
      # ... other mappings
    }
    ```

3.  **JSON Payload to ComfyUI's `/prompt` Endpoint:**
    This is the JSON object sent by OpenWebUI (`utils.images.comfyui.py`) to ComfyUI to queue a generation job. The `prompt` field contains the `COMFYUI_WORKFLOW` dynamically modified with user inputs.

    ```json
    {
      "client_id": "some_unique_client_id_generated_by_openwebui",
      "prompt": {
        "3": {
          "inputs": {
            "seed": 9876543210, // Dynamically updated
            "steps": 30,         // Dynamically updated
            "cfg": 8.0,
            "sampler_name": "dpmpp_2m_sde_gpu",
            "scheduler": "karras",
            "denoise": 1,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
          },
          "class_type": "KSampler",
          "_meta": {"title": "KSampler"}
        },
        "4": {
          "inputs": {"ckpt_name": "another_model.safetensors"}, // Dynamically updated
          "class_type": "CheckpointLoaderSimple",
          "_meta": {"title": "Load Checkpoint"}
        },
        "5": {
          "inputs": {
            "width": 512,    // Dynamically updated
            "height": 768,   // Dynamically updated
            "batch_size": 2  // Dynamically updated
            },
          "class_type": "EmptyLatentImage",
          "_meta": {"title": "Empty Latent Image"}
        },
        "6": {
          "inputs": {"text": "A futuristic city skyline at dusk", "clip": ["4", 1]}, // Dynamically updated
          "class_type": "CLIPTextEncode",
          "_meta": {"title": "Positive Prompt"}
        },
        "7": {
          "inputs": {"text": "cartoon, painting, illustration", "clip": ["4", 1]}, // Dynamically updated
          "class_type": "CLIPTextEncode",
          "_meta": {"title": "Negative Prompt"}
        },
        "9": {
          "inputs": {"filename_prefix": "OpenWebUI_Comfy", "images": ["3", 0]},
          "class_type": "SaveImage",
          "_meta": {"title": "Save Image"}
        }
      },
      "front": true
    }
    ```

4.  **JSON Response from ComfyUI's `/history/{prompt_id}` Endpoint (Snippet):**
    After execution, OpenWebUI fetches results from this endpoint. The key part is the `outputs` object, which contains data for each node that produced an output.

    ```json
    {
      "a_specific_prompt_id_value": { // The prompt_id
        // ... other fields like "status", "prompt" request details ...
        "outputs": {
          "9": { // Assuming node "9" is the SaveImage node
            "images": [
              {
                "filename": "OpenWebUI_Comfy_00001_.png",
                "subfolder": "2023-10-27/", // Example subfolder
                "type": "output"
              },
              {
                "filename": "OpenWebUI_Comfy_00002_.png",
                "subfolder": "2023-10-27/",
                "type": "output"
              }
              // More images if batch_size (n) was > 1
            ]
          },
          "3": { // Example KSampler output (might include latent, not typically used by OpenWebUI)
             "latent": [ /* ... latent data ... */ ]
          }
          // ... outputs of other nodes ...
        }
      }
    }
    ```

5.  **Final JSON Response from OpenWebUI to Client (`/images/generations` endpoint):**
    After fetching, storing, and creating internal URLs for the images, OpenWebUI sends this back to the client.

    ```json
    [
      {
        "url": "/v1/images/uploads/generated_image_unique_id_1.png"
      },
      {
        "url": "/v1/images/uploads/generated_image_unique_id_2.png"
      }
      // More objects if multiple images were generated
    ]
    ```
    *(Note: The exact URL format `/v1/images/uploads/...` might vary based on OpenWebUI's API versioning and static file serving configuration.)*
