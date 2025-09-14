import os
from open_webui.config.core.base import PersistentConfig

####################################
# USER PERMISSIONS CONFIGURATION
####################################

# Workspace permissions
USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS", "False").lower() == "true"
)

# Public sharing permissions
USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

# Chat permissions
USER_PERMISSIONS_CHAT_CONTROLS = (
    os.environ.get("USER_PERMISSIONS_CHAT_CONTROLS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_VALVES = (
    os.environ.get("USER_PERMISSIONS_CHAT_VALVES", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_SYSTEM_PROMPT = (
    os.environ.get("USER_PERMISSIONS_CHAT_SYSTEM_PROMPT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_PARAMS = (
    os.environ.get("USER_PERMISSIONS_CHAT_PARAMS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_FILE_UPLOAD = (
    os.environ.get("USER_PERMISSIONS_CHAT_FILE_UPLOAD", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_DELETE = (
    os.environ.get("USER_PERMISSIONS_CHAT_DELETE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_DELETE_MESSAGE = (
    os.environ.get("USER_PERMISSIONS_CHAT_DELETE_MESSAGE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_CONTINUE_RESPONSE = (
    os.environ.get("USER_PERMISSIONS_CHAT_CONTINUE_RESPONSE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_REGENERATE_RESPONSE = (
    os.environ.get("USER_PERMISSIONS_CHAT_REGENERATE_RESPONSE", "True").lower()
    == "true"
)

USER_PERMISSIONS_CHAT_RATE_RESPONSE = (
    os.environ.get("USER_PERMISSIONS_CHAT_RATE_RESPONSE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_EDIT = (
    os.environ.get("USER_PERMISSIONS_CHAT_EDIT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_SHARE = (
    os.environ.get("USER_PERMISSIONS_CHAT_SHARE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_EXPORT = (
    os.environ.get("USER_PERMISSIONS_CHAT_EXPORT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_STT = (
    os.environ.get("USER_PERMISSIONS_CHAT_STT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TTS = (
    os.environ.get("USER_PERMISSIONS_CHAT_TTS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_CALL = (
    os.environ.get("USER_PERMISSIONS_CHAT_CALL", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_MULTIPLE_MODELS = (
    os.environ.get("USER_PERMISSIONS_CHAT_MULTIPLE_MODELS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED", "False").lower()
    == "true"
)

# Feature permissions
USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS = (
    os.environ.get("USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS", "False").lower()
    == "true"
)

USER_PERMISSIONS_FEATURES_WEB_SEARCH = (
    os.environ.get("USER_PERMISSIONS_FEATURES_WEB_SEARCH", "True").lower() == "true"
)

USER_PERMISSIONS_FEATURES_IMAGE_GENERATION = (
    os.environ.get("USER_PERMISSIONS_FEATURES_IMAGE_GENERATION", "True").lower()
    == "true"
)

USER_PERMISSIONS_FEATURES_CODE_INTERPRETER = (
    os.environ.get("USER_PERMISSIONS_FEATURES_CODE_INTERPRETER", "True").lower()
    == "true"
)

USER_PERMISSIONS_FEATURES_NOTES = (
    os.environ.get("USER_PERMISSIONS_FEATURES_NOTES", "True").lower() == "true"
)

####################################
# DEFAULT USER PERMISSIONS AGGREGATION
####################################

DEFAULT_USER_PERMISSIONS = {
    "workspace": {
        "models": USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS,
        "knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS,
        "prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS,
        "tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS,
    },
    "sharing": {
        "public_models": USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING,
        "public_knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING,
        "public_prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING,
        "public_tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING,
    },
    "chat": {
        "controls": USER_PERMISSIONS_CHAT_CONTROLS,
        "valves": USER_PERMISSIONS_CHAT_VALVES,
        "system_prompt": USER_PERMISSIONS_CHAT_SYSTEM_PROMPT,
        "params": USER_PERMISSIONS_CHAT_PARAMS,
        "file_upload": USER_PERMISSIONS_CHAT_FILE_UPLOAD,
        "delete": USER_PERMISSIONS_CHAT_DELETE,
        "delete_message": USER_PERMISSIONS_CHAT_DELETE_MESSAGE,
        "continue_response": USER_PERMISSIONS_CHAT_CONTINUE_RESPONSE,
        "regenerate_response": USER_PERMISSIONS_CHAT_REGENERATE_RESPONSE,
        "rate_response": USER_PERMISSIONS_CHAT_RATE_RESPONSE,
        "edit": USER_PERMISSIONS_CHAT_EDIT,
        "share": USER_PERMISSIONS_CHAT_SHARE,
        "export": USER_PERMISSIONS_CHAT_EXPORT,
        "stt": USER_PERMISSIONS_CHAT_STT,
        "tts": USER_PERMISSIONS_CHAT_TTS,
        "call": USER_PERMISSIONS_CHAT_CALL,
        "multiple_models": USER_PERMISSIONS_CHAT_MULTIPLE_MODELS,
        "temporary": USER_PERMISSIONS_CHAT_TEMPORARY,
        "temporary_enforced": USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED,
    },
    "features": {
        "direct_tool_servers": USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS,
        "web_search": USER_PERMISSIONS_FEATURES_WEB_SEARCH,
        "image_generation": USER_PERMISSIONS_FEATURES_IMAGE_GENERATION,
        "code_interpreter": USER_PERMISSIONS_FEATURES_CODE_INTERPRETER,
        "notes": USER_PERMISSIONS_FEATURES_NOTES,
    },
}

USER_PERMISSIONS = PersistentConfig(
    "USER_PERMISSIONS",
    "user.permissions",
    DEFAULT_USER_PERMISSIONS,
)
