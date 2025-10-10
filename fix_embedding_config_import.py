#!/usr/bin/env python3
"""
Fix for embedding and reranker models not working after importing JSON configuration.

Issue: When JSON configuration is imported, embedding model settings are updated in the config
but the actual embedding functions (app.state.ef and app.state.EMBEDDING_FUNCTION) are not
re-initialized, causing vector dimension mismatches.

This script provides the fix by adding a function to re-initialize embedding functions
when configuration is imported.
"""

import logging

def reinitialize_embedding_functions(app):
    """
    Re-initialize embedding and reranking functions after configuration import.
    
    This function should be called whenever embedding configuration is updated
    via JSON import or other configuration changes.
    """
    from open_webui.routers.retrieval import get_ef, get_rf, get_embedding_function, get_reranking_function
    from open_webui.config import RAG_EMBEDDING_MODEL_AUTO_UPDATE, RAG_RERANKING_MODEL_AUTO_UPDATE
    from open_webui.env import DEVICE_TYPE
    
    log = logging.getLogger(__name__)
    
    try:
        # Clear existing embedding functions
        if app.state.config.RAG_EMBEDDING_ENGINE == "":
            # unloads current internal embedding model and clears VRAM cache
            app.state.ef = None
            app.state.EMBEDDING_FUNCTION = None
            import gc
            gc.collect()
            if DEVICE_TYPE == "cuda":
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        
        # Re-initialize embedding function
        app.state.ef = get_ef(
            app.state.config.RAG_EMBEDDING_ENGINE,
            app.state.config.RAG_EMBEDDING_MODEL,
            RAG_EMBEDDING_MODEL_AUTO_UPDATE,
        )
        
        # Re-initialize reranking function if hybrid search is enabled
        if (
            app.state.config.ENABLE_RAG_HYBRID_SEARCH
            and not app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
        ):
            app.state.rf = get_rf(
                app.state.config.RAG_RERANKING_ENGINE,
                app.state.config.RAG_RERANKING_MODEL,
                app.state.config.RAG_EXTERNAL_RERANKER_URL,
                app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
                RAG_RERANKING_MODEL_AUTO_UPDATE,
            )
        else:
            app.state.rf = None
        
        # Re-initialize embedding function wrapper
        app.state.EMBEDDING_FUNCTION = get_embedding_function(
            app.state.config.RAG_EMBEDDING_ENGINE,
            app.state.config.RAG_EMBEDDING_MODEL,
            embedding_function=app.state.ef,
            url=(
                app.state.config.RAG_OPENAI_API_BASE_URL
                if app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else (
                    app.state.config.RAG_OLLAMA_BASE_URL
                    if app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                    else app.state.config.RAG_AZURE_OPENAI_BASE_URL
                )
            ),
            key=(
                app.state.config.RAG_OPENAI_API_KEY
                if app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else (
                    app.state.config.RAG_OLLAMA_API_KEY
                    if app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
                    else app.state.config.RAG_AZURE_OPENAI_API_KEY
                )
            ),
            embedding_batch_size=app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            azure_api_version=(
                app.state.config.RAG_AZURE_OPENAI_API_VERSION
                if app.state.config.RAG_EMBEDDING_ENGINE == "azure_openai"
                else None
            ),
        )
        
        # Re-initialize reranking function wrapper
        app.state.RERANKING_FUNCTION = get_reranking_function(
            app.state.config.RAG_RERANKING_ENGINE,
            app.state.config.RAG_RERANKING_MODEL,
            reranking_function=app.state.rf,
        )
        
        log.info(f"Successfully re-initialized embedding functions with model: {app.state.config.RAG_EMBEDDING_MODEL}")
        return True
        
    except Exception as e:
        log.error(f"Error re-initializing embedding functions: {e}")
        return False


# Example usage in configuration import endpoint:
"""
@router.post("/config/import")
async def import_config(request: Request, config_data: dict, user=Depends(get_admin_user)):
    try:
        # Update configuration values
        for key, value in config_data.items():
            if hasattr(request.app.state.config, key):
                setattr(request.app.state.config, key, value)
        
        # Re-initialize embedding functions if embedding config was updated
        embedding_keys = [
            'RAG_EMBEDDING_ENGINE', 'RAG_EMBEDDING_MODEL', 'RAG_EMBEDDING_BATCH_SIZE',
            'RAG_OPENAI_API_BASE_URL', 'RAG_OPENAI_API_KEY',
            'RAG_OLLAMA_BASE_URL', 'RAG_OLLAMA_API_KEY',
            'RAG_AZURE_OPENAI_BASE_URL', 'RAG_AZURE_OPENAI_API_KEY', 'RAG_AZURE_OPENAI_API_VERSION',
            'RAG_RERANKING_ENGINE', 'RAG_RERANKING_MODEL',
            'RAG_EXTERNAL_RERANKER_URL', 'RAG_EXTERNAL_RERANKER_API_KEY'
        ]
        
        if any(key in config_data for key in embedding_keys):
            reinitialize_embedding_functions(request.app)
        
        return {"status": "success", "message": "Configuration imported successfully"}
        
    except Exception as e:
        log.error(f"Error importing configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""