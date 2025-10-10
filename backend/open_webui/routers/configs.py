import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, ConfigDict
import aiohttp

from typing import Optional

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import get_config, save_config
from open_webui.config import BannerModel

from open_webui.utils.tools import (
    get_tool_server_data,
    get_tool_server_url,
    set_tool_servers,
)
from open_webui.utils.mcp.client import MCPClient

from open_webui.env import SRC_LOG_LEVELS

from open_webui.utils.oauth import (
    get_discovery_urls,
    get_oauth_client_info_with_dynamic_client_registration,
    encrypt_data,
    decrypt_data,
    OAuthClientInformationFull,
)
from mcp.shared.auth import OAuthMetadata

router = APIRouter()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


############################
# ImportConfig
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post("/import", response_model=dict)
async def import_config(request: Request, form_data: ImportConfigForm, user=Depends(get_admin_user)):
    save_config(form_data.config)
    
    # Check if embedding configuration was updated and re-initialize if needed
    embedding_keys = [
        'RAG_EMBEDDING_ENGINE', 'RAG_EMBEDDING_MODEL', 'RAG_EMBEDDING_BATCH_SIZE',
        'RAG_OPENAI_API_BASE_URL', 'RAG_OPENAI_API_KEY',
        'RAG_OLLAMA_BASE_URL', 'RAG_OLLAMA_API_KEY',
        'RAG_AZURE_OPENAI_BASE_URL', 'RAG_AZURE_OPENAI_API_KEY', 'RAG_AZURE_OPENAI_API_VERSION',
        'RAG_RERANKING_ENGINE', 'RAG_RERANKING_MODEL',
        'RAG_EXTERNAL_RERANKER_URL', 'RAG_EXTERNAL_RERANKER_API_KEY',
        'ENABLE_RAG_HYBRID_SEARCH', 'BYPASS_EMBEDDING_AND_RETRIEVAL'
    ]
    
    if any(key in form_data.config for key in embedding_keys):
        try:
            from open_webui.routers.retrieval import get_ef, get_rf, get_embedding_function, get_reranking_function
            from open_webui.config import RAG_EMBEDDING_MODEL_AUTO_UPDATE, RAG_RERANKING_MODEL_AUTO_UPDATE
            from open_webui.env import DEVICE_TYPE
            
            log.info("Re-initializing embedding functions after configuration import")
            
            # Clear existing embedding functions if switching from internal model
            if request.app.state.config.RAG_EMBEDDING_ENGINE == "":
                request.app.state.ef = None
                request.app.state.EMBEDDING_FUNCTION = None
                import gc
                gc.collect()
                if DEVICE_TYPE == "cuda":
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            # Re-initialize embedding function
            request.app.state.ef = get_ef(
                request.app.state.config.RAG_EMBEDDING_ENGINE,
                request.app.state.config.RAG_EMBEDDING_MODEL,
                RAG_EMBEDDING_MODEL_AUTO_UPDATE,
            )
            
            # Re-initialize reranking function if hybrid search is enabled
            if (
                request.app.state.config.ENABLE_RAG_HYBRID_SEARCH
                and not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
            ):
                request.app.state.rf = get_rf(
                    request.app.state.config.RAG_RERANKING_ENGINE,
                    request.app.state.config.RAG_RERANKING_MODEL,
                    request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
                    request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
                    RAG_RERANKING_MODEL_AUTO_UPDATE,
                )
            else:
                request.app.state.rf = None
            
            # Re-initialize embedding function wrapper
            request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
                request.app.state.config.RAG_EMBEDDING_ENGINE,
                request.app.state.config.RAG_EMBEDDING_MODEL,
                embedding_function=request.app.state.ef,
                url=(
                    request.app.state.config.RAG_OPENAI_API_BASE_URL
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                    else (
                        request.app.state.config.RAG_OLLAMA_BASE_URL
                        if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                        else request.app.state.config.RAG_AZURE_OPENAI_BASE_URL
                    )
                ),
                key=(
                    request.app.state.config.RAG_OPENAI_API_KEY
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                    else (
                        request.app.state.config.RAG_OLLAMA_API_KEY
                        if request.app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                        else request.app.state.config.RAG_AZURE_OPENAI_API_KEY
                    )
                ),
                embedding_batch_size=request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
                azure_api_version=(
                    request.app.state.config.RAG_AZURE_OPENAI_API_VERSION
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == "azure_openai"
                    else None
                ),
            )
            
            # Re-initialize reranking function wrapper
            request.app.state.RERANKING_FUNCTION = get_reranking_function(
                request.app.state.config.RAG_RERANKING_ENGINE,
                request.app.state.config.RAG_RERANKING_MODEL,
                reranking_function=request.app.state.rf,
            )
            
            log.info(f"Successfully re-initialized embedding functions with model: {request.app.state.config.RAG_EMBEDDING_MODEL}")
            
        except Exception as e:
            log.error(f"Error re-initializing embedding functions after config import: {e}")
            # Don't fail the import if embedding initialization fails
            pass
    
    return get_config()


############################
# ExportConfig
############################


@router.get("/export", response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return get_config()


############################
# Connections Config
############################


class ConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool
    ENABLE_BASE_MODELS_CACHE: bool


@router.get("/connections", response_model=ConnectionsConfigForm)
async def get_connections_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
        "ENABLE_BASE_MODELS_CACHE": request.app.state.config.ENABLE_BASE_MODELS_CACHE,
    }


@router.post("/connections", response_model=ConnectionsConfigForm)
async def set_connections_config(
    request: Request,
    form_data: ConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_DIRECT_CONNECTIONS = (
        form_data.ENABLE_DIRECT_CONNECTIONS
    )
    request.app.state.config.ENABLE_BASE_MODELS_CACHE = (
        form_data.ENABLE_BASE_MODELS_CACHE
    )

    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
        "ENABLE_BASE_MODELS_CACHE": request.app.state.config.ENABLE_BASE_MODELS_CACHE,
    }


class OAuthClientRegistrationForm(BaseModel):
    url: str
    client_id: str
    client_name: Optional[str] = None


@router.post("/oauth/clients/register")
async def register_oauth_client(
    request: Request,
    form_data: OAuthClientRegistrationForm,
    type: Optional[str] = None,
    user=Depends(get_admin_user),
):
    try:
        oauth_client_id = form_data.client_id
        if type:
            oauth_client_id = f"{type}:{form_data.client_id}"

        oauth_client_info = (
            await get_oauth_client_info_with_dynamic_client_registration(
                request, oauth_client_id, form_data.url
            )
        )
        return {
            "status": True,
            "oauth_client_info": encrypt_data(
                oauth_client_info.model_dump(mode="json")
            ),
        }
    except Exception as e:
        log.debug(f"Failed to register OAuth client: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to register OAuth client",
        )


############################
# ToolServers Config
############################


class ToolServerConnection(BaseModel):
    url: str
    path: str
    type: Optional[str] = "openapi"  # openapi, mcp
    auth_type: Optional[str]
    key: Optional[str]
    config: Optional[dict]

    model_config = ConfigDict(extra="allow")


class ToolServersConfigForm(BaseModel):
    TOOL_SERVER_CONNECTIONS: list[ToolServerConnection]


@router.get("/tool_servers", response_model=ToolServersConfigForm)
async def get_tool_servers_config(request: Request, user=Depends(get_admin_user)):
    return {
        "TOOL_SERVER_CONNECTIONS": request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post("/tool_servers", response_model=ToolServersConfigForm)
async def set_tool_servers_config(
    request: Request,
    form_data: ToolServersConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.TOOL_SERVER_CONNECTIONS = [
        connection.model_dump() for connection in form_data.TOOL_SERVER_CONNECTIONS
    ]

    await set_tool_servers(request)

    for connection in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        server_type = connection.get("type", "openapi")
        if server_type == "mcp":
            server_id = connection.get("info", {}).get("id")
            auth_type = connection.get("auth_type", "none")
            if auth_type == "oauth_2.1" and server_id:
                try:
                    oauth_client_info = connection.get("info", {}).get(
                        "oauth_client_info", ""
                    )
                    oauth_client_info = decrypt_data(oauth_client_info)

                    await request.app.state.oauth_client_manager.add_client(
                        f"{server_type}:{server_id}",
                        OAuthClientInformationFull(**oauth_client_info),
                    )
                except Exception as e:
                    log.debug(f"Failed to add OAuth client for MCP tool server: {e}")
                    continue

    return {
        "TOOL_SERVER_CONNECTIONS": request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post("/tool_servers/verify")
async def verify_tool_servers_config(
    request: Request, form_data: ToolServerConnection, user=Depends(get_admin_user)
):
    """
    Verify the connection to the tool server.
    """
    try:
        if form_data.type == "mcp":
            if form_data.auth_type == "oauth_2.1":
                discovery_urls = get_discovery_urls(form_data.url)
                for discovery_url in discovery_urls:
                    log.debug(
                        f"Trying to fetch OAuth 2.1 discovery document from {discovery_url}"
                    )
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            discovery_url
                        ) as oauth_server_metadata_response:
                            if oauth_server_metadata_response.status == 200:
                                try:
                                    oauth_server_metadata = (
                                        OAuthMetadata.model_validate(
                                            await oauth_server_metadata_response.json()
                                        )
                                    )
                                    return {
                                        "status": True,
                                        "oauth_server_metadata": oauth_server_metadata.model_dump(
                                            mode="json"
                                        ),
                                    }
                                except Exception as e:
                                    log.info(
                                        f"Failed to parse OAuth 2.1 discovery document: {e}"
                                    )
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Failed to parse OAuth 2.1 discovery document from {discovery_url}",
                                    )

                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch OAuth 2.1 discovery document from {discovery_urls}",
                )
            else:
                try:
                    client = MCPClient()
                    headers = None

                    token = None
                    if form_data.auth_type == "bearer":
                        token = form_data.key
                    elif form_data.auth_type == "session":
                        token = request.state.token.credentials
                    elif form_data.auth_type == "system_oauth":
                        try:
                            if request.cookies.get("oauth_session_id", None):
                                token = await request.app.state.oauth_manager.get_oauth_token(
                                    user.id,
                                    request.cookies.get("oauth_session_id", None),
                                )
                        except Exception as e:
                            pass

                    if token:
                        headers = {"Authorization": f"Bearer {token}"}

                    await client.connect(form_data.url, headers=headers)
                    specs = await client.list_tool_specs()
                    return {
                        "status": True,
                        "specs": specs,
                    }
                except Exception as e:
                    log.debug(f"Failed to create MCP client: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to create MCP client",
                    )
                finally:
                    if client:
                        await client.disconnect()
        else:  # openapi
            token = None
            if form_data.auth_type == "bearer":
                token = form_data.key
            elif form_data.auth_type == "session":
                token = request.state.token.credentials
            elif form_data.auth_type == "system_oauth":
                try:
                    if request.cookies.get("oauth_session_id", None):
                        token = await request.app.state.oauth_manager.get_oauth_token(
                            user.id,
                            request.cookies.get("oauth_session_id", None),
                        )
                except Exception as e:
                    pass

            url = get_tool_server_url(form_data.url, form_data.path)
            return await get_tool_server_data(token, url)
    except HTTPException as e:
        raise e
    except Exception as e:
        log.debug(f"Failed to connect to the tool server: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to the tool server",
        )


############################
# CodeInterpreterConfig
############################
class CodeInterpreterConfigForm(BaseModel):
    ENABLE_CODE_EXECUTION: bool
    CODE_EXECUTION_ENGINE: str
    CODE_EXECUTION_JUPYTER_URL: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_EXECUTION_JUPYTER_TIMEOUT: Optional[int]
    ENABLE_CODE_INTERPRETER: bool
    CODE_INTERPRETER_ENGINE: str
    CODE_INTERPRETER_PROMPT_TEMPLATE: Optional[str]
    CODE_INTERPRETER_JUPYTER_URL: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_INTERPRETER_JUPYTER_TIMEOUT: Optional[int]


@router.get("/code_execution", response_model=CodeInterpreterConfigForm)
async def get_code_execution_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_CODE_EXECUTION": request.app.state.config.ENABLE_CODE_EXECUTION,
        "CODE_EXECUTION_ENGINE": request.app.state.config.CODE_EXECUTION_ENGINE,
        "CODE_EXECUTION_JUPYTER_URL": request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        "CODE_EXECUTION_JUPYTER_AUTH": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        "CODE_EXECUTION_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        "CODE_EXECUTION_JUPYTER_TIMEOUT": request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        "ENABLE_CODE_INTERPRETER": request.app.state.config.ENABLE_CODE_INTERPRETER,
        "CODE_INTERPRETER_ENGINE": request.app.state.config.CODE_INTERPRETER_ENGINE,
        "CODE_INTERPRETER_PROMPT_TEMPLATE": request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        "CODE_INTERPRETER_JUPYTER_URL": request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        "CODE_INTERPRETER_JUPYTER_AUTH": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        "CODE_INTERPRETER_JUPYTER_TIMEOUT": request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


@router.post("/code_execution", response_model=CodeInterpreterConfigForm)
async def set_code_execution_config(
    request: Request, form_data: CodeInterpreterConfigForm, user=Depends(get_admin_user)
):

    request.app.state.config.ENABLE_CODE_EXECUTION = form_data.ENABLE_CODE_EXECUTION

    request.app.state.config.CODE_EXECUTION_ENGINE = form_data.CODE_EXECUTION_ENGINE
    request.app.state.config.CODE_EXECUTION_JUPYTER_URL = (
        form_data.CODE_EXECUTION_JUPYTER_URL
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT = (
        form_data.CODE_EXECUTION_JUPYTER_TIMEOUT
    )

    request.app.state.config.ENABLE_CODE_INTERPRETER = form_data.ENABLE_CODE_INTERPRETER
    request.app.state.config.CODE_INTERPRETER_ENGINE = form_data.CODE_INTERPRETER_ENGINE
    request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE = (
        form_data.CODE_INTERPRETER_PROMPT_TEMPLATE
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_URL = (
        form_data.CODE_INTERPRETER_JUPYTER_URL
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
    )
    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
    )
    request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT = (
        form_data.CODE_INTERPRETER_JUPYTER_TIMEOUT
    )

    return {
        "ENABLE_CODE_EXECUTION": request.app.state.config.ENABLE_CODE_EXECUTION,
        "CODE_EXECUTION_ENGINE": request.app.state.config.CODE_EXECUTION_ENGINE,
        "CODE_EXECUTION_JUPYTER_URL": request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        "CODE_EXECUTION_JUPYTER_AUTH": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        "CODE_EXECUTION_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        "CODE_EXECUTION_JUPYTER_TIMEOUT": request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        "ENABLE_CODE_INTERPRETER": request.app.state.config.ENABLE_CODE_INTERPRETER,
        "CODE_INTERPRETER_ENGINE": request.app.state.config.CODE_INTERPRETER_ENGINE,
        "CODE_INTERPRETER_PROMPT_TEMPLATE": request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        "CODE_INTERPRETER_JUPYTER_URL": request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        "CODE_INTERPRETER_JUPYTER_AUTH": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        "CODE_INTERPRETER_JUPYTER_TIMEOUT": request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


############################
# SetDefaultModels
############################
class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: Optional[str]
    MODEL_ORDER_LIST: Optional[list[str]]


@router.get("/models", response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


@router.post("/models", response_model=ModelsConfigForm)
async def set_models_config(
    request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post("/suggestions", response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS = data["suggestions"]
    return request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS


############################
# SetBanners
############################


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post("/banners", response_model=list[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.BANNERS = data["banners"]
    return request.app.state.config.BANNERS


@router.get("/banners", response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return request.app.state.config.BANNERS
