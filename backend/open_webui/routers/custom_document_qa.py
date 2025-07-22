import logging
import json
import aiohttp
import os
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.models.users import Users
from open_webui.models.files import Files
from open_webui.retrieval.utils import get_sources_from_files
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

# Configuration for the external API
CUSTOM_QA_API_URL = os.environ.get("GOVGPT_FILE_SEARCH_API_URL", "http://40.119.184.8:8102/query")
CUSTOM_QA_TIMEOUT = int(os.environ.get("GOVGPT_FILE_SEARCH_TIMEOUT", "30"))
SERVICE_NAME = "govGpt-file-search-service"

# Global configuration flag - can be set via environment variable
USE_CUSTOM_QA_API = os.environ.get("ENABLE_GOVGPT_FILE_SEARCH", "false").lower() == "true"


class CustomQARequest(BaseModel):
    user_query: str
    file_ids: Optional[List[str]] = None
    collection_names: Optional[List[str]] = None
    session_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, str]]] = None


class CustomQAResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class CustomQAConfig(BaseModel):
    enabled: bool


@router.get("/config", response_model=CustomQAConfig)
async def get_custom_qa_config(user=Depends(get_admin_user)):
    """
    Get the current custom QA API configuration
    """
    return CustomQAConfig(enabled=USE_CUSTOM_QA_API)


@router.post("/config", response_model=CustomQAConfig)
async def update_custom_qa_config(
    config: CustomQAConfig,
    user=Depends(get_admin_user)
):
    """
    Update the custom QA API configuration
    """
    global USE_CUSTOM_QA_API
    USE_CUSTOM_QA_API = config.enabled
    
    log.info(f"Custom QA API {'enabled' if USE_CUSTOM_QA_API else 'disabled'} by user {user.id}")
    
    return CustomQAConfig(enabled=USE_CUSTOM_QA_API)


def get_custom_qa_enabled() -> bool:
    """
    Get the current custom QA API enabled status
    """
    return USE_CUSTOM_QA_API


async def call_custom_qa_api(
    user_query: str,
    document_texts: list[str],
    user_id: str,
    user_name: str,
    session_id: str = None,
    chat_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Call the external custom QA API
    """
    payload = {
        "user_query": user_query,
        "user_id": user_id,
        "user_name": user_name,
        "session_id": session_id or f"session_{user_id}",
        "chat_history": chat_history or [],
        "document_texts": document_texts
    }
    
    # Log the request details
    log.info(f"{SERVICE_NAME} REQUEST to {CUSTOM_QA_API_URL}")
    log.info(f"{SERVICE_NAME} REQUEST payload: {json.dumps(payload, indent=2)}")
    log.info(f"{SERVICE_NAME} REQUEST user_query: '{user_query}'")
    log.info(f"{SERVICE_NAME} REQUEST document_texts size: {len(document_texts)} ")
    log.info(f"{SERVICE_NAME} REQUEST chat_history length: {len(chat_history or [])} messages")
    
    try:
        log.info(f"{SERVICE_NAME} REQUEST starting API call to {CUSTOM_QA_API_URL}")
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=CUSTOM_QA_TIMEOUT)) as session:
            async with session.post(
                CUSTOM_QA_API_URL,
                headers={"Content-Type": "application/json"},
                json=payload
            ) as response:
                response_text = await response.text()
                
                # Log the response details
                log.info(f"{SERVICE_NAME} RESPONSE status: {response.status}")
                log.info(f"{SERVICE_NAME} RESPONSE headers: {dict(response.headers)}")
                log.info(f"{SERVICE_NAME} RESPONSE body length: {len(response_text)} characters")
                log.info(f"{SERVICE_NAME} RESPONSE body: {response_text}")
                
                # Log response timing (aiohttp doesn't have elapsed attribute)
                log.info(f"{SERVICE_NAME} RESPONSE received successfully")
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        log.info(f"{SERVICE_NAME} RESPONSE parsed successfully for user {user_id}")
                        log.info(f"{SERVICE_NAME} RESPONSE keys: {list(result.keys())}")
                        
                        # Log specific response fields if they exist
                        if "response" in result:
                            response_length = len(result["response"])
                            log.info(f"{SERVICE_NAME} RESPONSE response length: {response_length} characters")
                            log.info(f"{SERVICE_NAME} RESPONSE response preview: '{result['response'][:200]}...'")
                        
                        if "sources" in result:
                            log.info(f"{SERVICE_NAME} RESPONSE sources count: {len(result['sources'])}")
                        
                        if "metadata" in result:
                            log.info(f"{SERVICE_NAME} RESPONSE metadata: {result['metadata']}")
                        
                        # Log final summary
                        total_time = time.time() - start_time
                        log.info(f"{SERVICE_NAME} REQUEST completed successfully in {total_time:.3f} seconds for user {user_id}")
                        
                        return result
                    except json.JSONDecodeError as e:
                        log.error(f"{SERVICE_NAME} RESPONSE JSON decode error: {e}")
                        log.error(f"{SERVICE_NAME} RESPONSE raw text: {response_text}")
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"{SERVICE_NAME} invalid JSON response"
                        )
                else:
                    log.error(f"{SERVICE_NAME} RESPONSE error: {response.status} - {response_text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"{SERVICE_NAME} error: {response.status}"
                    )
    except aiohttp.ClientError as e:
        log.error(f"{SERVICE_NAME} REQUEST connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{SERVICE_NAME} unavailable"
        )
    except Exception as e:
        log.error(f"{SERVICE_NAME} REQUEST unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


def get_document_content_from_files(request: Request, file_ids: List[str], user) -> str:
    """
    Retrieve document content from uploaded files
    """
    try:
        # Get files from database
        files = []
        for file_id in file_ids:
            file = Files.get_file_by_id(file_id)
            if file and (file.user_id == user.id or user.role == "admin"):
                # Convert FileModel to dictionary format expected by get_sources_from_files
                file_dict = {
                    "id": file.id,
                    "name": file.filename,
                    "type": "file",
                    "legacy": False
                }
                files.append(file_dict)
            else:
                log.warning(f"File {file_id} not found or access denied for user {user.id}")
        
        if not files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No accessible files found"
            )
        
        # Get document content directly from files
        document_texts = []
        
        for file_dict in files:
            file_id = file_dict["id"]
            file = Files.get_file_by_id(file_id)
            
            if file and file.data and file.data.get("content"):
                content = file.data.get("content", "")
                if content.strip():
                    document_texts.append(content)
                    log.info(f"Retrieved content from file {file_id}: {len(content)} characters")
                else:
                    log.warning(f"File {file_id} has empty content")
            else:
                log.warning(f"File {file_id} not found or has no content")
        
        # Combine all text with proper spacing
        # combined_text = "\n\n".join(document_texts)
        
        log.info(f"Retrieved {len(document_texts)} document files, for user {user.id}")
        return document_texts #return list
        
    except Exception as e:
        log.error(f"Error retrieving document content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving document content"
        )


def get_document_content_from_collections(request: Request, collection_names: List[str], user) -> str:
    """
    Retrieve document content from knowledge base collections
    """
    try:
        from open_webui.retrieval.utils import get_all_items_from_collections
        
        # Get all documents from the specified collections
        result = get_all_items_from_collections(collection_names)
        
        if not result or not result.get("documents"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No documents found in specified collections"
            )
        
        # Combine all document content
        document_texts = result["documents"][0]  # First element contains the list of documents
        combined_text = "\n\n".join(document_texts)
        
        log.info(f"Retrieved {len(document_texts)} documents from collections for user {user.id}")
        return combined_text
        
    except Exception as e:
        log.error(f"Error retrieving collection content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving collection content"
        )


def get_last_user_message(messages: List[Dict[str, str]]) -> str:
    """
    Get the last user message from the messages list
    """
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


async def custom_qa_filter_inlet(body: dict, __user__: dict, __request__: Request, **kwargs) -> dict:
    """
    Filter function that integrates custom QA API into the pipeline
    This function is called during the inlet phase of the chat pipeline
    """
    try:
        # Check if custom QA is enabled
        if not get_custom_qa_enabled():
            return body
        
        # Check if there are files in the request
        files = body.get("metadata", {}).get("files", [])
        if not files:
            return body
        
        # Get the last user message
        messages = body.get("messages", [])
        user_message = get_last_user_message(messages)
        if not user_message.strip():
            return body
        
        # Extract file IDs
        file_ids = []
        for file_item in files:
            if isinstance(file_item, dict):
                if "id" in file_item:
                    file_ids.append(file_item["id"])
                elif "file_id" in file_item:
                    file_ids.append(file_item["file_id"])
            elif isinstance(file_item, str):
                file_ids.append(file_item)
        
        if not file_ids:
            return body
        
        # Get document content
        document_text = get_document_content_from_files(__request__, file_ids, __user__)
        
        if not any(doc.strip() for doc in document_text):
            return body
        
        # Get chat history for context
        chat_history = []
        for i in range(0, len(messages) - 1, 2):  # Skip the last user message
            if i + 1 < len(messages):
                chat_history.append({
                    "role": "user",
                    "content": messages[i].get("content", "")
                })
                chat_history.append({
                    "role": "assistant", 
                    "content": messages[i + 1].get("content", "")
                })
        
        # Call the custom QA API
        api_response = await call_custom_qa_api(
            user_query=user_message,
            document_texts=document_text,
            user_id=__user__["id"],
            user_name=__user__["name"],
            session_id=body.get("metadata", {}).get("session_id"),
            chat_history=chat_history
        )
        
        # Extract the response and enhance the user message
        custom_response = api_response.get("response", "")
        
        if custom_response.strip():
            # Add the custom response as context to the user message
            enhanced_message = f"{user_message}\n\nContext from documents:\n{custom_response}"
            
            # Update the last user message with the enhanced content
            for message in reversed(messages):
                if message.get("role") == "user":
                    message["content"] = enhanced_message
                    break
            
            log.info(f"{SERVICE_NAME} response integrated for user {__user__['id']}")
        
        return body
        
    except Exception as e:
        log.error(f"Error in {SERVICE_NAME} filter: {e}")
        # Return the original body if there's an error
        return body


@router.post("/query", response_model=CustomQAResponse)
async def custom_document_qa(
    request: Request,
    form_data: CustomQARequest,
    user=Depends(get_verified_user),
):
    """
    Query documents using the custom external QA API
    """
    try:
        # Validate input
        if not form_data.user_query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User query is required"
            )
        
        if not form_data.file_ids and not form_data.collection_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either file_ids or collection_names must be provided"
            )
        
        # Get document content
        document_text = []
        
        if form_data.file_ids:
            # Get content from uploaded files
            file_content = get_document_content_from_files(request, form_data.file_ids, user)
            document_text.extend(file_content)
        
        if form_data.collection_names:
            # Get content from knowledge base collections
            collection_content = get_document_content_from_collections(request, form_data.collection_names, user)
            # if document_text:
            #     document_text += "\n\n" + collection_content
            # else:
            #     document_text = collection_content
            document_text.append(collection_content)

        #if all documents are empty
        if not any(doc.strip() for doc in document_text):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No document content found"
            )

        log.info(f"Processing {SERVICE_NAME} query for user {user.id} with {len(document_text)} doc of content")
        
        # Call the external QA API
        api_response = await call_custom_qa_api(
            user_query=form_data.user_query,
            document_texts=document_text,
            user_id=user.id,
            user_name=user.name,
            session_id=form_data.session_id,
            chat_history=form_data.chat_history
        )
        
        # Format the response
        response = CustomQAResponse(
            response=api_response.get("response", ""),
            sources=api_response.get("sources"),
            metadata={
                "query": form_data.user_query,
                "file_ids": form_data.file_ids,
                "collection_names": form_data.collection_names,
                "session_id": form_data.session_id,
                "content_length": len(document_text)
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error in {SERVICE_NAME} document QA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/query/files/{file_id}", response_model=CustomQAResponse)
async def custom_qa_single_file(
    request: Request,
    file_id: str,
    form_data: CustomQARequest,
    user=Depends(get_verified_user),
):
    """
    Query a single file using the custom external QA API
    """
    # Override file_ids with the single file
    form_data.file_ids = [file_id]
    return await custom_document_qa(request, form_data, user)


@router.post("/query/collection/{collection_name}", response_model=CustomQAResponse)
async def custom_qa_single_collection(
    request: Request,
    collection_name: str,
    form_data: CustomQARequest,
    user=Depends(get_verified_user),
):
    """
    Query a single knowledge base collection using the custom external QA API
    """
    # Override collection_names with the single collection
    form_data.collection_names = [collection_name]
    return await custom_document_qa(request, form_data, user) 