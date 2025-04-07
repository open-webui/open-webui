import json
from io import BufferedReader
from typing import Any, Dict, List
import httpx
from typing import Optional
from pydantic import BaseModel
import random




class ComfyUINodeInput(BaseModel):
    type: Optional[str] = None
    node_ids: list[str] = []
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

class FileOutput:
    def __init__(self, filename: str, content_type: str, data: str, size: int):
        self.filename = filename
        self.content_type = content_type
        self.data = data
        self.size = size


class PromptResult:
    def __init__(
        self,
        prompt_id: str,
        status: str,
        completed: bool,
        execution_time_seconds: float,
        prompt: Dict,
        outputs: List[Dict] | None = None,
    ):
        self.prompt_id = prompt_id
        self.status = status
        self.completed = completed
        self.execution_time_seconds = execution_time_seconds
        self.prompt = prompt

        # Initialize outputs as FileOutput objects
        self.outputs = []
        if outputs:
            for output_data in outputs:
                self.outputs.append(
                    FileOutput(
                        filename=output_data.get("filename", ""),
                        content_type=output_data.get("content_type", ""),
                        data=output_data.get("data", ""),
                        size=output_data.get("size", 0),
                    )
                )


class ComfyAPIClient:
    def __init__(
        self,
        *,
        infer_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        if infer_url is None:
            raise Exception("infer_url is required")
        self.infer_url = infer_url

        if client_id is None:
            raise Exception("client_id is required")

        if client_secret is None:
            raise Exception("client_secret is required")

        self.client_id = client_id
        self.client_secret = client_secret

    async def infer(
        self,
        *,
        data: Dict[str, Any],
        files: list[tuple[str, BufferedReader]] = [],
    ) -> Dict[str, Any]:

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.infer_url,
                    data=data,
                    files=files,
                    timeout=httpx.Timeout(2400.0),
                    follow_redirects=True,
                    headers={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )

                if response.status_code == 201:
                    return response.json()
                else:
                    error_text = response.text
                    raise Exception(
                        f"API request failed with status {response.status_code}: {error_text}"
                    )
            except httpx.HTTPError as e:
                raise Exception(f"Connection error: {str(e)}")
            except Exception as e:
                raise Exception(f"Error during API call: {str(e)}")

def initialize_parameters(model: str, payload: ComfyUIGenerateImageForm):
    params = {}
    for node in payload.workflow.nodes:
        if node.type:
            if node.type == "model":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = model
            elif node.type == "prompt":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = payload.prompt
            elif node.type == "negative_prompt":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = payload.negative_prompt
            elif node.type == "width":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = payload.width
            elif node.type == "height":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = payload.height
            elif node.type == "n":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = payload.n
            elif node.type == "steps":
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = payload.steps
            elif node.type == "seed":
                seed = (
                    payload.seed
                    if payload.seed is not None
                    else random.randint(0, 1125899906842624)
                )
                for node_id in node.node_ids:
                    params[f"{node_id}-inputs-{node.key}"] = seed
        else:
            for node_id in node.node_ids:
                params[f"{node_id}-inputs-{node.key}"] = node.value
    return params

def parse_parameters(params: dict):
    parsed_params = {}
    files = []
    for key, value in params.items():
        if isinstance(value, BufferedReader):
            files.append((key, value))
        else:
            parsed_params[key] = value
    return parsed_params, files

async def infer(
    model: str, 
    payload: ComfyUIGenerateImageForm,
    api_url: str,
    client_id: str,
    client_secret: str,
):

    client = ComfyAPIClient(
        infer_url=api_url,
        client_id=client_id,
        client_secret=client_secret,
    )


    override_workflow_api = json.loads(payload.workflow.workflow)

    params = initialize_parameters(model, payload)
    params_parsed, files = parse_parameters(params)
    data = {
        "logs": False,
        "params": json.dumps(params_parsed),
        "workflow_api": json.dumps(override_workflow_api)
        if override_workflow_api
        else None,
    }

    # Make the API call
    result = await client.infer(data=data, files=files)

    return PromptResult(**result)
