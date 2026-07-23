"""reshape config to per key rows

Revision ID: 3ff2c63645b8
Revises: 461111b60977
Create Date: 2026-06-17 00:50:51.477073

"""

import json
import time
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3ff2c63645b8'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Maps every dot-notation blob path to its legacy env/config key name.
# Built from the legacy persistent config declarations in config.py.
BLOB_PATH_TO_KEY = {
    'audio.stt.allowed_extensions': 'AUDIO_STT_ALLOWED_EXTENSIONS',
    'audio.stt.azure.api_key': 'AUDIO_STT_AZURE_API_KEY',
    'audio.stt.azure.base_url': 'AUDIO_STT_AZURE_BASE_URL',
    'audio.stt.azure.locales': 'AUDIO_STT_AZURE_LOCALES',
    'audio.stt.azure.max_speakers': 'AUDIO_STT_AZURE_MAX_SPEAKERS',
    'audio.stt.azure.region': 'AUDIO_STT_AZURE_REGION',
    'audio.stt.deepgram.api_key': 'DEEPGRAM_API_KEY',
    'audio.stt.engine': 'AUDIO_STT_ENGINE',
    'audio.stt.mistral.api_base_url': 'AUDIO_STT_MISTRAL_API_BASE_URL',
    'audio.stt.mistral.api_key': 'AUDIO_STT_MISTRAL_API_KEY',
    'audio.stt.mistral.use_chat_completions': 'AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS',
    'audio.stt.model': 'AUDIO_STT_MODEL',
    'audio.stt.openai.api_base_url': 'AUDIO_STT_OPENAI_API_BASE_URL',
    'audio.stt.openai.api_key': 'AUDIO_STT_OPENAI_API_KEY',
    'audio.stt.supported_content_types': 'AUDIO_STT_SUPPORTED_CONTENT_TYPES',
    'audio.stt.whisper_model': 'WHISPER_MODEL',
    'audio.tts.api_key': 'AUDIO_TTS_API_KEY',
    'audio.tts.azure.speech_base_url': 'AUDIO_TTS_AZURE_SPEECH_BASE_URL',
    'audio.tts.azure.speech_output_format': 'AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT',
    'audio.tts.azure.speech_region': 'AUDIO_TTS_AZURE_SPEECH_REGION',
    'audio.tts.engine': 'AUDIO_TTS_ENGINE',
    'audio.tts.mistral.api_base_url': 'AUDIO_TTS_MISTRAL_API_BASE_URL',
    'audio.tts.mistral.api_key': 'AUDIO_TTS_MISTRAL_API_KEY',
    'audio.tts.model': 'AUDIO_TTS_MODEL',
    'audio.tts.openai.api_base_url': 'AUDIO_TTS_OPENAI_API_BASE_URL',
    'audio.tts.openai.api_key': 'AUDIO_TTS_OPENAI_API_KEY',
    'audio.tts.openai.params': 'AUDIO_TTS_OPENAI_PARAMS',
    'audio.tts.split_on': 'AUDIO_TTS_SPLIT_ON',
    'audio.tts.voice': 'AUDIO_TTS_VOICE',
    'auth.admin.email': 'ADMIN_EMAIL',
    'auth.admin.show': 'SHOW_ADMIN_DETAILS',
    'auth.api_key.allowed_endpoints': 'API_KEYS_ALLOWED_ENDPOINTS',
    'auth.api_key.endpoint_restrictions': 'ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS',
    'auth.enable_api_keys': 'ENABLE_API_KEYS',
    'auth.jwt_expiry': 'JWT_EXPIRES_IN',
    'automations.enable': 'ENABLE_AUTOMATIONS',
    'automations.max_count': 'AUTOMATION_MAX_COUNT',
    'automations.min_interval': 'AUTOMATION_MIN_INTERVAL',
    'calendar.enable': 'ENABLE_CALENDAR',
    'channels.enable': 'ENABLE_CHANNELS',
    'code_execution.enable': 'ENABLE_CODE_EXECUTION',
    'code_execution.engine': 'CODE_EXECUTION_ENGINE',
    'code_execution.jupyter.auth': 'CODE_EXECUTION_JUPYTER_AUTH',
    'code_execution.jupyter.auth_password': 'CODE_EXECUTION_JUPYTER_AUTH_PASSWORD',
    'code_execution.jupyter.auth_token': 'CODE_EXECUTION_JUPYTER_AUTH_TOKEN',
    'code_execution.jupyter.timeout': 'CODE_EXECUTION_JUPYTER_TIMEOUT',
    'code_execution.jupyter.url': 'CODE_EXECUTION_JUPYTER_URL',
    'code_interpreter.enable': 'ENABLE_CODE_INTERPRETER',
    'code_interpreter.engine': 'CODE_INTERPRETER_ENGINE',
    'code_interpreter.jupyter.auth': 'CODE_INTERPRETER_JUPYTER_AUTH',
    'code_interpreter.jupyter.auth_password': 'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD',
    'code_interpreter.jupyter.auth_token': 'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN',
    'code_interpreter.jupyter.timeout': 'CODE_INTERPRETER_JUPYTER_TIMEOUT',
    'code_interpreter.jupyter.url': 'CODE_INTERPRETER_JUPYTER_URL',
    'code_interpreter.prompt_template': 'CODE_INTERPRETER_PROMPT_TEMPLATE',
    'direct.enable': 'ENABLE_DIRECT_CONNECTIONS',
    'evaluation.arena.enable': 'ENABLE_EVALUATION_ARENA_MODELS',
    'evaluation.arena.models': 'EVALUATION_ARENA_MODELS',
    'file.image_compression_height': 'FILE_IMAGE_COMPRESSION_HEIGHT',
    'file.image_compression_width': 'FILE_IMAGE_COMPRESSION_WIDTH',
    'folders.enable': 'ENABLE_FOLDERS',
    'folders.max_file_count': 'FOLDER_MAX_FILE_COUNT',
    'google_drive.api_key': 'GOOGLE_DRIVE_API_KEY',
    'google_drive.client_id': 'GOOGLE_DRIVE_CLIENT_ID',
    'google_drive.enable': 'ENABLE_GOOGLE_DRIVE_INTEGRATION',
    'image_generation.automatic1111.api_auth': 'AUTOMATIC1111_API_AUTH',
    'image_generation.automatic1111.api_params': 'AUTOMATIC1111_PARAMS',
    'image_generation.automatic1111.base_url': 'AUTOMATIC1111_BASE_URL',
    'image_generation.comfyui.api_key': 'COMFYUI_API_KEY',
    'image_generation.comfyui.base_url': 'COMFYUI_BASE_URL',
    'image_generation.comfyui.nodes': 'COMFYUI_WORKFLOW_NODES',
    'image_generation.comfyui.workflow': 'COMFYUI_WORKFLOW',
    'image_generation.enable': 'ENABLE_IMAGE_GENERATION',
    'image_generation.engine': 'IMAGE_GENERATION_ENGINE',
    'image_generation.gemini.api_base_url': 'IMAGES_GEMINI_API_BASE_URL',
    'image_generation.gemini.api_key': 'IMAGES_GEMINI_API_KEY',
    'image_generation.gemini.endpoint_method': 'IMAGES_GEMINI_ENDPOINT_METHOD',
    'image_generation.model': 'IMAGE_GENERATION_MODEL',
    'image_generation.openai.api_base_url': 'IMAGES_OPENAI_API_BASE_URL',
    'image_generation.openai.api_key': 'IMAGES_OPENAI_API_KEY',
    'image_generation.openai.api_version': 'IMAGES_OPENAI_API_VERSION',
    'image_generation.openai.params': 'IMAGES_OPENAI_API_PARAMS',
    'image_generation.prompt.enable': 'ENABLE_IMAGE_PROMPT_GENERATION',
    'image_generation.size': 'IMAGE_SIZE',
    'image_generation.steps': 'IMAGE_STEPS',
    'images.edit.comfyui.api_key': 'IMAGES_EDIT_COMFYUI_API_KEY',
    'images.edit.comfyui.base_url': 'IMAGES_EDIT_COMFYUI_BASE_URL',
    'images.edit.comfyui.nodes': 'IMAGES_EDIT_COMFYUI_WORKFLOW_NODES',
    'images.edit.comfyui.workflow': 'IMAGES_EDIT_COMFYUI_WORKFLOW',
    'images.edit.enable': 'ENABLE_IMAGE_EDIT',
    'images.edit.engine': 'IMAGE_EDIT_ENGINE',
    'images.edit.gemini.api_base_url': 'IMAGES_EDIT_GEMINI_API_BASE_URL',
    'images.edit.gemini.api_key': 'IMAGES_EDIT_GEMINI_API_KEY',
    'images.edit.model': 'IMAGE_EDIT_MODEL',
    'images.edit.openai.api_base_url': 'IMAGES_EDIT_OPENAI_API_BASE_URL',
    'images.edit.openai.api_key': 'IMAGES_EDIT_OPENAI_API_KEY',
    'images.edit.openai.api_version': 'IMAGES_EDIT_OPENAI_API_VERSION',
    'images.edit.size': 'IMAGE_EDIT_SIZE',
    'ldap.enable': 'ENABLE_LDAP',
    'ldap.group.enable_creation': 'ENABLE_LDAP_GROUP_CREATION',
    'ldap.group.enable_management': 'ENABLE_LDAP_GROUP_MANAGEMENT',
    'ldap.server.app_dn': 'LDAP_APP_DN',
    'ldap.server.app_password': 'LDAP_APP_PASSWORD',
    'ldap.server.attribute_for_groups': 'LDAP_ATTRIBUTE_FOR_GROUPS',
    'ldap.server.attribute_for_mail': 'LDAP_ATTRIBUTE_FOR_MAIL',
    'ldap.server.attribute_for_username': 'LDAP_ATTRIBUTE_FOR_USERNAME',
    'ldap.server.ca_cert_file': 'LDAP_CA_CERT_FILE',
    'ldap.server.ciphers': 'LDAP_CIPHERS',
    'ldap.server.host': 'LDAP_SERVER_HOST',
    'ldap.server.label': 'LDAP_SERVER_LABEL',
    'ldap.server.port': 'LDAP_SERVER_PORT',
    'ldap.server.search_filter': 'LDAP_SEARCH_FILTER',
    'ldap.server.use_tls': 'LDAP_USE_TLS',
    'ldap.server.users_dn': 'LDAP_SEARCH_BASE',
    'ldap.server.validate_cert': 'LDAP_VALIDATE_CERT',
    'memories.enable': 'ENABLE_MEMORIES',
    'models.base_models_cache': 'ENABLE_BASE_MODELS_CACHE',
    'models.default_metadata': 'DEFAULT_MODEL_METADATA',
    'models.default_params': 'DEFAULT_MODEL_PARAMS',
    'notes.enable': 'ENABLE_NOTES',
    # OAuth — direct paths
    'oauth.admin_roles': 'OAUTH_ADMIN_ROLES',
    'oauth.allowed_domains': 'OAUTH_ALLOWED_DOMAINS',
    'oauth.allowed_roles': 'OAUTH_ALLOWED_ROLES',
    'oauth.audience': 'OAUTH_AUDIENCE',
    'oauth.auto_redirect': 'OAUTH_AUTO_REDIRECT',
    'oauth.blocked_groups': 'OAUTH_BLOCKED_GROUPS',
    'oauth.client.timeout': 'OAUTH_CLIENT_TIMEOUT',
    'oauth.enable_group_creation': 'ENABLE_OAUTH_GROUP_CREATION',
    'oauth.enable_group_mapping': 'ENABLE_OAUTH_GROUP_MANAGEMENT',
    'oauth.enable_role_mapping': 'ENABLE_OAUTH_ROLE_MANAGEMENT',
    'oauth.enable_signup': 'ENABLE_OAUTH_SIGNUP',
    'oauth.group_default_share': 'OAUTH_GROUP_DEFAULT_SHARE',
    'oauth.merge_accounts_by_email': 'OAUTH_MERGE_ACCOUNTS_BY_EMAIL',
    'oauth.refresh_token_include_scope': 'OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE',
    'oauth.roles_claim': 'OAUTH_ROLES_CLAIM',
    'oauth.update_email_on_login': 'OAUTH_UPDATE_EMAIL_ON_LOGIN',
    'oauth.update_name_on_login': 'OAUTH_UPDATE_NAME_ON_LOGIN',
    'oauth.update_picture_on_login': 'OAUTH_UPDATE_PICTURE_ON_LOGIN',
    # OAuth — generic provider paths
    'oauth.client_id': 'OAUTH_CLIENT_ID',
    'oauth.client_secret': 'OAUTH_CLIENT_SECRET',
    'oauth.code_challenge_method': 'OAUTH_CODE_CHALLENGE_METHOD',
    'oauth.email_claim': 'OAUTH_EMAIL_CLAIM',
    'oauth.end_session_endpoint': 'OPENID_END_SESSION_ENDPOINT',
    'oauth.group_claim': 'OAUTH_GROUP_CLAIM',
    'oauth.picture_claim': 'OAUTH_PICTURE_CLAIM',
    'oauth.provider_name': 'OAUTH_PROVIDER_NAME',
    'oauth.provider_url': 'OPENID_PROVIDER_URL',
    'oauth.redirect_uri': 'OPENID_REDIRECT_URI',
    'oauth.scopes': 'OAUTH_SCOPES',
    'oauth.sub_claim': 'OAUTH_SUB_CLAIM',
    'oauth.timeout': 'OAUTH_TIMEOUT',
    'oauth.token_endpoint_auth_method': 'OAUTH_TOKEN_ENDPOINT_AUTH_METHOD',
    'oauth.username_claim': 'OAUTH_USERNAME_CLAIM',
    # OAuth — OIDC nested paths (flattened)
    'oauth.oidc.avatar_claim': 'OAUTH_PICTURE_CLAIM',
    'oauth.oidc.client_id': 'OAUTH_CLIENT_ID',
    'oauth.oidc.client_secret': 'OAUTH_CLIENT_SECRET',
    'oauth.oidc.code_challenge_method': 'OAUTH_CODE_CHALLENGE_METHOD',
    'oauth.oidc.email_claim': 'OAUTH_EMAIL_CLAIM',
    'oauth.oidc.end_session_endpoint': 'OPENID_END_SESSION_ENDPOINT',
    'oauth.oidc.group_claim': 'OAUTH_GROUP_CLAIM',  # renamed from OAUTH_GROUPS_CLAIM
    'oauth.oidc.oauth_timeout': 'OAUTH_TIMEOUT',
    'oauth.oidc.provider_name': 'OAUTH_PROVIDER_NAME',
    'oauth.oidc.provider_url': 'OPENID_PROVIDER_URL',
    'oauth.oidc.redirect_uri': 'OPENID_REDIRECT_URI',
    'oauth.oidc.scopes': 'OAUTH_SCOPES',
    'oauth.oidc.sub_claim': 'OAUTH_SUB_CLAIM',
    'oauth.oidc.token_endpoint_auth_method': 'OAUTH_TOKEN_ENDPOINT_AUTH_METHOD',
    'oauth.oidc.username_claim': 'OAUTH_USERNAME_CLAIM',
    # OAuth — provider-specific
    'oauth.feishu.client_id': 'FEISHU_CLIENT_ID',
    'oauth.feishu.client_secret': 'FEISHU_CLIENT_SECRET',
    'oauth.feishu.redirect_uri': 'FEISHU_REDIRECT_URI',
    'oauth.feishu.scope': 'FEISHU_OAUTH_SCOPE',
    'oauth.github.client_id': 'GITHUB_CLIENT_ID',
    'oauth.github.client_secret': 'GITHUB_CLIENT_SECRET',
    'oauth.github.redirect_uri': 'GITHUB_CLIENT_REDIRECT_URI',
    'oauth.github.scope': 'GITHUB_CLIENT_SCOPE',
    'oauth.google.client_id': 'GOOGLE_CLIENT_ID',
    'oauth.google.client_secret': 'GOOGLE_CLIENT_SECRET',
    'oauth.google.redirect_uri': 'GOOGLE_REDIRECT_URI',
    'oauth.google.scope': 'GOOGLE_OAUTH_SCOPE',
    'oauth.microsoft.client_id': 'MICROSOFT_CLIENT_ID',
    'oauth.microsoft.client_secret': 'MICROSOFT_CLIENT_SECRET',
    'oauth.microsoft.login_base_url': 'MICROSOFT_CLIENT_LOGIN_BASE_URL',
    'oauth.microsoft.picture_url': 'MICROSOFT_CLIENT_PICTURE_URL',
    'oauth.microsoft.redirect_uri': 'MICROSOFT_REDIRECT_URI',
    'oauth.microsoft.scope': 'MICROSOFT_OAUTH_SCOPE',
    'oauth.microsoft.tenant_id': 'MICROSOFT_CLIENT_TENANT_ID',
    # Ollama / OpenAI
    'ollama.api_configs': 'OLLAMA_API_CONFIGS',
    'ollama.base_urls': 'OLLAMA_BASE_URLS',
    'ollama.enable': 'ENABLE_OLLAMA_API',
    'onedrive.enable': 'ENABLE_ONEDRIVE_INTEGRATION',
    'onedrive.sharepoint_tenant_id': 'ONEDRIVE_SHAREPOINT_TENANT_ID',
    'onedrive.sharepoint_url': 'ONEDRIVE_SHAREPOINT_URL',
    'openai.api_base_urls': 'OPENAI_API_BASE_URLS',
    'openai.api_configs': 'OPENAI_API_CONFIGS',
    'openai.api_keys': 'OPENAI_API_KEYS',
    'openai.enable': 'ENABLE_OPENAI_API',
    # RAG
    'rag.content_extraction_engine': 'CONTENT_EXTRACTION_ENGINE',
    'rag.datalab_marker_use_llm': 'DATALAB_MARKER_USE_LLM',
    'rag.mistral_ocr_api_base_url': 'MISTRAL_OCR_API_BASE_URL',
    'rag.azure_openai.api_key': 'RAG_AZURE_OPENAI_API_KEY',
    'rag.azure_openai.api_version': 'RAG_AZURE_OPENAI_API_VERSION',
    'rag.azure_openai.base_url': 'RAG_AZURE_OPENAI_BASE_URL',
    'rag.bypass_embedding_and_retrieval': 'BYPASS_EMBEDDING_AND_RETRIEVAL',
    'rag.chunk_min_size_target': 'CHUNK_MIN_SIZE_TARGET',
    'rag.chunk_overlap': 'CHUNK_OVERLAP',
    'rag.chunk_size': 'CHUNK_SIZE',
    'rag.datalab_marker_additional_config': 'DATALAB_MARKER_ADDITIONAL_CONFIG',
    'rag.datalab_marker_api_base_url': 'DATALAB_MARKER_API_BASE_URL',
    'rag.datalab_marker_api_key': 'DATALAB_MARKER_API_KEY',
    'rag.datalab_marker_disable_image_extraction': 'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION',
    'rag.datalab_marker_force_ocr': 'DATALAB_MARKER_FORCE_OCR',
    'rag.datalab_marker_format_lines': 'DATALAB_MARKER_FORMAT_LINES',
    'rag.datalab_marker_output_format': 'DATALAB_MARKER_OUTPUT_FORMAT',
    'rag.datalab_marker_paginate': 'DATALAB_MARKER_PAGINATE',
    'rag.datalab_marker_skip_cache': 'DATALAB_MARKER_SKIP_CACHE',
    'rag.datalab_marker_strip_existing_ocr': 'DATALAB_MARKER_STRIP_EXISTING_OCR',
    'rag.docling_api_key': 'DOCLING_API_KEY',
    'rag.docling_params': 'DOCLING_PARAMS',
    'rag.docling_server_url': 'DOCLING_SERVER_URL',
    'rag.document_intelligence_endpoint': 'DOCUMENT_INTELLIGENCE_ENDPOINT',
    'rag.document_intelligence_key': 'DOCUMENT_INTELLIGENCE_KEY',
    'rag.document_intelligence_model': 'DOCUMENT_INTELLIGENCE_MODEL',
    'rag.embedding_batch_size': 'RAG_EMBEDDING_BATCH_SIZE',
    'rag.embedding_concurrent_requests': 'RAG_EMBEDDING_CONCURRENT_REQUESTS',
    'rag.embedding_engine': 'RAG_EMBEDDING_ENGINE',
    'rag.embedding_model': 'RAG_EMBEDDING_MODEL',
    'rag.enable_async_embedding': 'ENABLE_ASYNC_EMBEDDING',
    'rag.enable_hybrid_search': 'ENABLE_RAG_HYBRID_SEARCH',
    'rag.enable_hybrid_search_enriched_texts': 'ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS',
    'rag.enable_markdown_header_text_splitter': 'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER',
    'rag.external_document_loader_api_key': 'EXTERNAL_DOCUMENT_LOADER_API_KEY',
    'rag.external_document_loader_url': 'EXTERNAL_DOCUMENT_LOADER_URL',
    'rag.external_reranker_api_key': 'RAG_EXTERNAL_RERANKER_API_KEY',
    'rag.external_reranker_timeout': 'RAG_EXTERNAL_RERANKER_TIMEOUT',
    'rag.external_reranker_url': 'RAG_EXTERNAL_RERANKER_URL',
    'rag.file.allowed_extensions': 'RAG_ALLOWED_FILE_EXTENSIONS',
    'rag.file.max_count': 'RAG_FILE_MAX_COUNT',
    'rag.file.max_size': 'RAG_FILE_MAX_SIZE',
    'rag.full_context': 'RAG_FULL_CONTEXT',
    'rag.hybrid_bm25_weight': 'RAG_HYBRID_BM25_WEIGHT',
    'rag.mineru_api_key': 'MINERU_API_KEY',
    'rag.mineru_api_mode': 'MINERU_API_MODE',
    'rag.mineru_api_timeout': 'MINERU_API_TIMEOUT',
    'rag.mineru_api_url': 'MINERU_API_URL',
    'rag.mineru_file_extensions': 'MINERU_FILE_EXTENSIONS',
    'rag.mineru_params': 'MINERU_PARAMS',
    'rag.mistral_ocr_api_key': 'MISTRAL_OCR_API_KEY',
    'rag.ollama.key': 'RAG_OLLAMA_API_KEY',
    'rag.ollama.url': 'RAG_OLLAMA_BASE_URL',
    'rag.openai_api_base_url': 'RAG_OPENAI_API_BASE_URL',
    'rag.openai_api_key': 'RAG_OPENAI_API_KEY',
    'rag.paddleocr_vl_base_url': 'PADDLEOCR_VL_BASE_URL',
    'rag.paddleocr_vl_token': 'PADDLEOCR_VL_TOKEN',
    'rag.pdf_extract_images': 'PDF_EXTRACT_IMAGES',
    'rag.pdf_loader_mode': 'PDF_LOADER_MODE',
    'rag.relevance_threshold': 'RAG_RELEVANCE_THRESHOLD',
    'rag.reranking_batch_size': 'RAG_RERANKING_BATCH_SIZE',
    'rag.reranking_engine': 'RAG_RERANKING_ENGINE',
    'rag.reranking_model': 'RAG_RERANKING_MODEL',
    'rag.template': 'RAG_TEMPLATE',
    'rag.text_splitter': 'RAG_TEXT_SPLITTER',
    'rag.tika_server_url': 'TIKA_SERVER_URL',
    'rag.tiktoken_encoding_name': 'TIKTOKEN_ENCODING_NAME',
    'rag.top_k': 'RAG_TOP_K',
    'rag.top_k_reranker': 'RAG_TOP_K_RERANKER',
    # RAG — Web
    'rag.web.fetch.max_content_length': 'WEB_FETCH_MAX_CONTENT_LENGTH',
    'rag.web.loader.concurrent_requests': 'WEB_LOADER_CONCURRENT_REQUESTS',
    'rag.web.loader.engine': 'WEB_LOADER_ENGINE',
    'rag.web.loader.external_web_loader_api_key': 'EXTERNAL_WEB_LOADER_API_KEY',
    'rag.web.loader.external_web_loader_url': 'EXTERNAL_WEB_LOADER_URL',
    'rag.web.loader.firecrawl_api_key': 'FIRECRAWL_API_KEY',
    'rag.web.loader.firecrawl_api_url': 'FIRECRAWL_API_BASE_URL',
    'rag.web.loader.firecrawl_timeout': 'FIRECRAWL_TIMEOUT',
    'rag.web.loader.playwright_timeout': 'PLAYWRIGHT_TIMEOUT',
    'rag.web.loader.playwright_ws_url': 'PLAYWRIGHT_WS_URL',
    'rag.web.loader.ssl_verification': 'ENABLE_WEB_LOADER_SSL_VERIFICATION',
    'rag.web.loader.timeout': 'WEB_LOADER_TIMEOUT',
    'rag.web.search.azure_ai_search_api_key': 'AZURE_AI_SEARCH_API_KEY',
    'rag.web.search.azure_ai_search_endpoint': 'AZURE_AI_SEARCH_ENDPOINT',
    'rag.web.search.azure_ai_search_index_name': 'AZURE_AI_SEARCH_INDEX_NAME',
    'rag.web.search.bing_search_v7_endpoint': 'BING_SEARCH_V7_ENDPOINT',
    'rag.web.search.bing_search_v7_subscription_key': 'BING_SEARCH_V7_SUBSCRIPTION_KEY',
    'rag.web.search.bocha_search_api_key': 'BOCHA_SEARCH_API_KEY',
    'rag.web.search.brave_search_api_key': 'BRAVE_SEARCH_API_KEY',
    'rag.web.search.brave_search_context_tokens': 'BRAVE_SEARCH_CONTEXT_TOKENS',
    'rag.web.search.bypass_embedding_and_retrieval': 'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL',
    'rag.web.search.bypass_web_loader': 'BYPASS_WEB_SEARCH_WEB_LOADER',
    'rag.web.search.concurrent_requests': 'WEB_SEARCH_CONCURRENT_REQUESTS',
    'rag.web.search.ddgs_backend': 'DDGS_BACKEND',
    'rag.web.search.domain.filter_list': 'WEB_SEARCH_DOMAIN_FILTER_LIST',
    'rag.web.search.enable': 'ENABLE_WEB_SEARCH',
    'rag.web.search.engine': 'WEB_SEARCH_ENGINE',
    'rag.web.search.exa_api_key': 'EXA_API_KEY',
    'rag.web.search.external_web_search_api_key': 'EXTERNAL_WEB_SEARCH_API_KEY',
    'rag.web.search.external_web_search_url': 'EXTERNAL_WEB_SEARCH_URL',
    'rag.web.search.google_pse_api_key': 'GOOGLE_PSE_API_KEY',
    'rag.web.search.google_pse_engine_id': 'GOOGLE_PSE_ENGINE_ID',
    'rag.web.search.jina_api_base_url': 'JINA_API_BASE_URL',
    'rag.web.search.jina_api_key': 'JINA_API_KEY',
    'rag.web.search.kagi_search_api_key': 'KAGI_SEARCH_API_KEY',
    'rag.web.search.linkup_api_key': 'LINKUP_API_KEY',
    'rag.web.search.linkup_search_params': 'LINKUP_SEARCH_PARAMS',
    'rag.web.search.mojeek_search_api_key': 'MOJEEK_SEARCH_API_KEY',
    'rag.web.search.ollama_cloud_api_key': 'OLLAMA_CLOUD_WEB_SEARCH_API_KEY',
    'rag.web.search.perplexity_api_key': 'PERPLEXITY_API_KEY',
    'rag.web.search.perplexity_model': 'PERPLEXITY_MODEL',
    'rag.web.search.perplexity_search_api_url': 'PERPLEXITY_SEARCH_API_URL',
    'rag.web.search.perplexity_search_context_usage': 'PERPLEXITY_SEARCH_CONTEXT_USAGE',
    'rag.web.search.result_count': 'WEB_SEARCH_RESULT_COUNT',
    'rag.web.search.searchapi_api_key': 'SEARCHAPI_API_KEY',
    'rag.web.search.searchapi_engine': 'SEARCHAPI_ENGINE',
    'rag.web.search.searxng_language': 'SEARXNG_LANGUAGE',
    'rag.web.search.searxng_query_url': 'SEARXNG_QUERY_URL',
    'rag.web.search.serpapi_api_key': 'SERPAPI_API_KEY',
    'rag.web.search.serpapi_engine': 'SERPAPI_ENGINE',
    'rag.web.search.serper_api_key': 'SERPER_API_KEY',
    'rag.web.search.serply_api_key': 'SERPLY_API_KEY',
    'rag.web.search.serpstack_api_key': 'SERPSTACK_API_KEY',
    'rag.web.search.serpstack_https': 'SERPSTACK_HTTPS',
    'rag.web.search.sougou_api_sid': 'SOUGOU_API_SID',
    'rag.web.search.sougou_api_sk': 'SOUGOU_API_SK',
    'rag.web.search.tavily_api_key': 'TAVILY_API_KEY',
    'rag.web.search.tavily_extract_depth': 'TAVILY_EXTRACT_DEPTH',
    'rag.web.search.trust_env': 'WEB_SEARCH_TRUST_ENV',
    'rag.web.search.yacy_password': 'YACY_PASSWORD',
    'rag.web.search.yacy_query_url': 'YACY_QUERY_URL',
    'rag.web.search.yacy_username': 'YACY_USERNAME',
    'rag.web.search.yandex_web_search_api_key': 'YANDEX_WEB_SEARCH_API_KEY',
    'rag.web.search.yandex_web_search_config': 'YANDEX_WEB_SEARCH_CONFIG',
    'rag.web.search.yandex_web_search_url': 'YANDEX_WEB_SEARCH_URL',
    'rag.web.search.youcom_api_key': 'YOUCOM_API_KEY',
    'rag.youtube_loader_language': 'YOUTUBE_LOADER_LANGUAGE',
    'rag.youtube_loader_proxy_url': 'YOUTUBE_LOADER_PROXY_URL',
    # Tasks
    'task.autocomplete.enable': 'ENABLE_AUTOCOMPLETE_GENERATION',
    'task.autocomplete.input_max_length': 'AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH',
    'task.autocomplete.prompt_template': 'AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE',
    'task.follow_up.enable': 'ENABLE_FOLLOW_UP_GENERATION',
    'task.follow_up.prompt_template': 'FOLLOW_UP_GENERATION_PROMPT_TEMPLATE',
    'task.image.prompt_template': 'IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE',
    'task.model.default': 'TASK_MODEL',
    'task.model.external': 'TASK_MODEL_EXTERNAL',
    'task.query.prompt_template': 'QUERY_GENERATION_PROMPT_TEMPLATE',
    'task.query.retrieval.enable': 'ENABLE_RETRIEVAL_QUERY_GENERATION',
    'task.query.search.enable': 'ENABLE_SEARCH_QUERY_GENERATION',
    'task.tags.enable': 'ENABLE_TAGS_GENERATION',
    'task.tags.prompt_template': 'TAGS_GENERATION_PROMPT_TEMPLATE',
    'task.title.enable': 'ENABLE_TITLE_GENERATION',
    'task.title.prompt_template': 'TITLE_GENERATION_PROMPT_TEMPLATE',
    'task.tools.prompt_template': 'TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE',
    'task.voice.prompt.enable': 'ENABLE_VOICE_MODE_PROMPT',
    'task.voice.prompt_template': 'VOICE_MODE_PROMPT_TEMPLATE',
    # Misc
    'terminal_server.connections': 'TERMINAL_SERVER_CONNECTIONS',
    'tool_server.connections': 'TOOL_SERVER_CONNECTIONS',
    'ui.banners': 'WEBUI_BANNERS',
    'ui.default_group_id': 'DEFAULT_GROUP_ID',
    'ui.default_locale': 'DEFAULT_LOCALE',
    'ui.default_models': 'DEFAULT_MODELS',
    'ui.default_pinned_models': 'DEFAULT_PINNED_MODELS',
    'ui.default_user_role': 'DEFAULT_USER_ROLE',
    'ui.enable_community_sharing': 'ENABLE_COMMUNITY_SHARING',
    'ui.enable_login_form': 'ENABLE_LOGIN_FORM',
    'ui.enable_message_rating': 'ENABLE_MESSAGE_RATING',
    'ui.enable_password_change_form': 'ENABLE_PASSWORD_CHANGE_FORM',
    'ui.enable_signup': 'ENABLE_SIGNUP',
    'ui.enable_user_webhooks': 'ENABLE_USER_WEBHOOKS',
    'ui.model_order_list': 'MODEL_ORDER_LIST',
    'ui.pending_user_overlay_content': 'PENDING_USER_OVERLAY_CONTENT',
    'ui.pending_user_overlay_title': 'PENDING_USER_OVERLAY_TITLE',
    'ui.prompt_suggestions': 'DEFAULT_PROMPT_SUGGESTIONS',
    'ui.watermark': 'RESPONSE_WATERMARK',
    'user.permissions': 'USER_PERMISSIONS',
    'users.enable_status': 'ENABLE_USER_STATUS',
    'webhook_url': 'WEBHOOK_URL',
    'webui.url': 'WEBUI_URL',
}


STORAGE_KEY_REWRITES = {
    'oauth.refresh_token_include_scope': 'oauth.refresh_token.include_scope',
    'rag.openai_api_base_url': 'rag.openai.api_base_url',
    'rag.openai_api_key': 'rag.openai.api_key',
    'rag.ollama.url': 'rag.ollama.base_url',
    'rag.ollama.key': 'rag.ollama.api_key',
    'oauth.oidc.avatar_claim': 'oauth.picture_claim',
    'oauth.oidc.client_id': 'oauth.client_id',
    'oauth.oidc.client_secret': 'oauth.client_secret',
    'oauth.oidc.code_challenge_method': 'oauth.code_challenge_method',
    'oauth.oidc.email_claim': 'oauth.email_claim',
    'oauth.oidc.end_session_endpoint': 'oauth.end_session_endpoint',
    'oauth.oidc.group_claim': 'oauth.group_claim',
    'oauth.oidc.oauth_timeout': 'oauth.timeout',
    'oauth.oidc.provider_name': 'oauth.provider_name',
    'oauth.oidc.provider_url': 'oauth.provider_url',
    'oauth.oidc.redirect_uri': 'oauth.redirect_uri',
    'oauth.oidc.scopes': 'oauth.scopes',
    'oauth.oidc.sub_claim': 'oauth.sub_claim',
    'oauth.oidc.token_endpoint_auth_method': 'oauth.token_endpoint_auth_method',
    'oauth.oidc.username_claim': 'oauth.username_claim',
}


LEGACY_KEY_TO_STORAGE_KEY = {
    legacy_key: STORAGE_KEY_REWRITES.get(blob_path, blob_path) for blob_path, legacy_key in BLOB_PATH_TO_KEY.items()
}


def _walk_blob(data: dict, prefix: str = '') -> dict:
    """Recursively walk a nested config blob, preserving known config values.

    Some config values are intentionally dictionaries, e.g. OPENAI_API_CONFIGS
    and OLLAMA_API_CONFIGS. Once the current path is a known config key, keep
    that value intact instead of flattening its internals into orphaned rows.
    """
    result = {}
    for key, value in data.items():
        path = f'{prefix}{key}' if not prefix else f'{prefix}.{key}'
        if path in BLOB_PATH_TO_KEY or path in LEGACY_KEY_TO_STORAGE_KEY:
            result[path] = value
        elif isinstance(value, dict):
            result.update(_walk_blob(value, path))
        else:
            result[path] = value
    return result


def upgrade() -> None:
    """Reshape config from single-row JSON blob to per-key rows."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = set(inspector.get_table_names())
    config_columns = (
        {column['name'] for column in inspector.get_columns('config')} if 'config' in table_names else set()
    )
    has_old_config = {'id', 'data'}.issubset(config_columns)
    has_new_config = {'key', 'value'}.issubset(config_columns)

    # Ad-hoc table reference for reading the old schema
    old_config = sa.table(
        'config',
        sa.column('id', sa.Integer),
        sa.column('data', sa.JSON),
    )

    # 1. Read existing blob
    blob_data = {}
    if has_old_config:
        try:
            result = conn.execute(sa.select(old_config.c.data).order_by(old_config.c.id.desc()).limit(1))
            row = result.fetchone()
            if row and row[0]:
                raw = row[0]
                blob_data = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass  # Table might be partially migrated or empty

    # 2. Preserve old blob table for rollback/inspection, then create per-key table.
    if has_old_config:
        if 'config_old' in table_names:
            op.drop_table('config_old')
        op.rename_table('config', 'config_old')

    # 3. Create new per-key table
    new_config = (
        sa.table(
            'config',
            sa.column('key', sa.Text),
            sa.column('value', sa.JSON()),
            sa.column('updated_at', sa.BigInteger),
        )
        if has_new_config
        else op.create_table(
            'config',
            sa.Column('key', sa.Text(), primary_key=True),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )
    )

    # 4. Flatten blob and insert per-key rows
    if blob_data:
        flat = _walk_blob(blob_data)

        # Keep stable dot-notation paths as the database keys.
        # Known legacy env-style keys are rewritten to their dotted keys; unknown
        # keys are still copied so custom/future config is not silently lost.
        rows = {}
        for blob_path, value in flat.items():
            if blob_path in BLOB_PATH_TO_KEY:
                storage_key = STORAGE_KEY_REWRITES.get(blob_path, blob_path)
            elif blob_path in LEGACY_KEY_TO_STORAGE_KEY:
                storage_key = LEGACY_KEY_TO_STORAGE_KEY[blob_path]
            else:
                storage_key = STORAGE_KEY_REWRITES.get(blob_path, blob_path)

            if storage_key not in rows:
                rows[storage_key] = value

        # Batch insert via SQLAlchemy table reference
        if rows:
            now = int(time.time())
            op.bulk_insert(
                new_config,
                [{'key': k, 'value': v, 'updated_at': now} for k, v in rows.items()],
            )


def downgrade() -> None:
    """Restore preserved old single-row config table when available."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = set(inspector.get_table_names())

    if 'config_old' in table_names:
        if 'config' in table_names:
            op.drop_table('config')
        op.rename_table('config_old', 'config')
        return

    config_columns = (
        {column['name'] for column in inspector.get_columns('config')} if 'config' in table_names else set()
    )
    has_per_key_config = {'key', 'value'}.issubset(config_columns)

    blob_data = {}
    if has_per_key_config:
        config = sa.table(
            'config',
            sa.column('key', sa.Text),
            sa.column('value', sa.JSON),
        )
        for key, value in conn.execute(sa.select(config.c.key, config.c.value)):
            blob_data[key] = json.loads(value) if isinstance(value, str) else value
        op.drop_table('config')

    if 'config' in table_names and not has_per_key_config:
        return

    old_config = op.create_table(
        'config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    if blob_data:
        op.bulk_insert(old_config, [{'data': blob_data, 'version': 0}])
