from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, ConfigDict

from typing import Optional
from datetime import datetime, timedelta
import secrets
import string

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import get_config, save_config
from open_webui.config import BannerModel
from open_webui.models.users import Users
from open_webui.models.groups import Groups
from open_webui.env import WEBUI_AUTH

from open_webui.utils.tools import get_tool_server_data, get_tool_servers_data


router = APIRouter()


############################
# ImportConfig
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post("/import", response_model=dict)
async def import_config(form_data: ImportConfigForm, user=Depends(get_admin_user)):
    save_config(form_data.config)
    return get_config()


############################
# ExportConfig
############################


@router.get("/export", response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return get_config()


############################
# Direct Connections Config
############################


class DirectConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool


@router.get("/direct_connections", response_model=DirectConnectionsConfigForm)
async def get_direct_connections_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
    }


@router.post("/direct_connections", response_model=DirectConnectionsConfigForm)
async def set_direct_connections_config(
    request: Request,
    form_data: DirectConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_DIRECT_CONNECTIONS = (
        form_data.ENABLE_DIRECT_CONNECTIONS
    )
    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
    }


############################
# ToolServers Config
############################


class ToolServerConnection(BaseModel):
    url: str
    path: str
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

    request.app.state.TOOL_SERVERS = await get_tool_servers_data(
        request.app.state.config.TOOL_SERVER_CONNECTIONS
    )

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

        token = None
        if form_data.auth_type == "bearer":
            token = form_data.key
        elif form_data.auth_type == "session":
            token = request.state.token.credentials

        url = f"{form_data.url}/{form_data.path}"
        return await get_tool_server_data(token, url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to the tool server: {str(e)}",
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


############################
# SCIM Configuration
############################


class SCIMConfigForm(BaseModel):
    enabled: bool
    token: Optional[str] = None
    token_created_at: Optional[str] = None
    token_expires_at: Optional[str] = None


class SCIMTokenRequest(BaseModel):
    expires_in: Optional[int] = None  # seconds until expiration, None = never


class SCIMTokenResponse(BaseModel):
    token: str
    created_at: str
    expires_at: Optional[str] = None


class SCIMStats(BaseModel):
    total_users: int
    total_groups: int
    last_sync: Optional[str] = None


# In-memory storage for SCIM tokens (in production, use database)
scim_tokens = {}


def generate_scim_token(length: int = 48) -> str:
    """Generate a secure random token for SCIM authentication"""
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("/scim", response_model=SCIMConfigForm)
async def get_scim_config(request: Request, user=Depends(get_admin_user)):
    """Get current SCIM configuration"""
    # Get token info from storage
    token_info = None
    scim_token = getattr(request.app.state.config, "SCIM_TOKEN", None)
    # Handle both PersistentConfig and direct value
    if hasattr(scim_token, 'value'):
        scim_token = scim_token.value
    
    if scim_token and scim_token in scim_tokens:
        token_info = scim_tokens[scim_token]
    
    scim_enabled = getattr(request.app.state.config, "SCIM_ENABLED", False)
    print(f"Getting SCIM config - raw SCIM_ENABLED: {scim_enabled}, type: {type(scim_enabled)}")
    # Handle both PersistentConfig and direct value
    if hasattr(scim_enabled, 'value'):
        scim_enabled = scim_enabled.value
    
    print(f"Returning SCIM config: enabled={scim_enabled}, token={'set' if scim_token else 'not set'}")
    
    return SCIMConfigForm(
        enabled=scim_enabled,
        token="***" if scim_token else None,  # Don't expose actual token
        token_created_at=token_info.get("created_at") if token_info else None,
        token_expires_at=token_info.get("expires_at") if token_info else None,
    )


@router.post("/scim", response_model=SCIMConfigForm)
async def update_scim_config(request: Request, config: SCIMConfigForm, user=Depends(get_admin_user)):
    """Update SCIM configuration"""
    if not WEBUI_AUTH:
        raise HTTPException(400, detail="Authentication must be enabled for SCIM")
    
    print(f"Updating SCIM config: enabled={config.enabled}")
    
    # Import here to avoid circular import
    from open_webui.config import save_config, get_config
    
    # Get current config data
    config_data = get_config()
    
    # Update SCIM settings in config data
    if "scim" not in config_data:
        config_data["scim"] = {}
    
    config_data["scim"]["enabled"] = config.enabled
    
    # Save config to database
    save_config(config_data)
    
    # Also update the runtime config
    scim_enabled_attr = getattr(request.app.state.config, "SCIM_ENABLED", None)
    if scim_enabled_attr:
        if hasattr(scim_enabled_attr, 'value'):
            # It's a PersistentConfig object
            print(f"Updating PersistentConfig SCIM_ENABLED from {scim_enabled_attr.value} to {config.enabled}")
            scim_enabled_attr.value = config.enabled
        else:
            # Direct assignment
            print(f"Direct assignment SCIM_ENABLED to {config.enabled}")
            request.app.state.config.SCIM_ENABLED = config.enabled
    else:
        # Create if doesn't exist
        print(f"Creating SCIM_ENABLED with value {config.enabled}")
        request.app.state.config.SCIM_ENABLED = config.enabled
    
    # Return updated config
    return await get_scim_config(request=request, user=user)


@router.post("/scim/token", response_model=SCIMTokenResponse)
async def generate_scim_token_endpoint(
    request: Request, token_request: SCIMTokenRequest, user=Depends(get_admin_user)
):
    """Generate a new SCIM bearer token"""
    token = generate_scim_token()
    created_at = datetime.utcnow()
    expires_at = None
    
    if token_request.expires_in:
        expires_at = created_at + timedelta(seconds=token_request.expires_in)
    
    # Store token info
    token_info = {
        "token": token,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }
    scim_tokens[token] = token_info
    
    # Import here to avoid circular import
    from open_webui.config import save_config, get_config
    
    # Get current config data
    config_data = get_config()
    
    # Update SCIM token in config data
    if "scim" not in config_data:
        config_data["scim"] = {}
    
    config_data["scim"]["token"] = token
    
    # Save config to database
    save_config(config_data)
    
    # Also update the runtime config
    scim_token_attr = getattr(request.app.state.config, "SCIM_TOKEN", None)
    if scim_token_attr:
        if hasattr(scim_token_attr, 'value'):
            # It's a PersistentConfig object
            scim_token_attr.value = token
        else:
            # Direct assignment
            request.app.state.config.SCIM_TOKEN = token
    else:
        # Create if doesn't exist
        request.app.state.config.SCIM_TOKEN = token
    
    return SCIMTokenResponse(
        token=token,
        created_at=token_info["created_at"],
        expires_at=token_info["expires_at"],
    )


@router.delete("/scim/token")
async def revoke_scim_token(request: Request, user=Depends(get_admin_user)):
    """Revoke the current SCIM token"""
    # Get current token
    scim_token = getattr(request.app.state.config, "SCIM_TOKEN", None)
    if hasattr(scim_token, 'value'):
        scim_token = scim_token.value
    
    # Remove from storage
    if scim_token and scim_token in scim_tokens:
        del scim_tokens[scim_token]
    
    # Import here to avoid circular import
    from open_webui.config import save_config, get_config
    
    # Get current config data
    config_data = get_config()
    
    # Remove SCIM token from config data
    if "scim" in config_data:
        config_data["scim"]["token"] = None
    
    # Save config to database
    save_config(config_data)
    
    # Also update the runtime config
    scim_token_attr = getattr(request.app.state.config, "SCIM_TOKEN", None)
    if scim_token_attr:
        if hasattr(scim_token_attr, 'value'):
            # It's a PersistentConfig object
            scim_token_attr.value = None
        else:
            # Direct assignment
            request.app.state.config.SCIM_TOKEN = None
    
    return {"detail": "SCIM token revoked successfully"}


@router.get("/scim/stats", response_model=SCIMStats)
async def get_scim_stats(request: Request, user=Depends(get_admin_user)):
    """Get SCIM statistics"""
    users = Users.get_users()
    groups = Groups.get_groups()
    
    # Get last sync time (in production, track this properly)
    last_sync = None
    
    return SCIMStats(
        total_users=len(users),
        total_groups=len(groups) if groups else 0,
        last_sync=last_sync,
    )
