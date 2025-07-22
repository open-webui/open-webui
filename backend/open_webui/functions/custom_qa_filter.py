"""
Custom QA Filter Function

This filter integrates an external QA API into the chat pipeline.
When enabled, it will call the external API for document-based queries
and enhance the user message with the response.

Configuration:
- Enable/disable the filter via the custom QA API endpoints
- External API URL: http://40.119.184.8:8102/query
- Timeout: 30 seconds

Usage:
- This filter automatically activates when files are present in the chat
- It calls the external API and enhances the user message with the response
- The enhanced message is then processed by the regular chat completion flow
"""

import logging
import json
import aiohttp
from typing import Dict, Any, List
from open_webui.routers.custom_document_qa import (
    get_custom_qa_enabled,
    call_custom_qa_api,
    get_document_content_from_files,
    get_last_user_message
)

log = logging.getLogger(__name__)


class Filter:
    def __init__(self):
        self.name = "GovGPT File Search Filter"
        self.description = "Integrates govGpt-file-search-service for document-based queries"
        self.version = "1.0.0"
        self.author = "Open WebUI"
        self.type = "filter"
        
        # Configuration
        self.enabled = True
        self.priority = 100  # High priority to run early in the pipeline
        
        # External API configuration
        self.api_url = "http://40.119.184.8:8102/query"
        self.timeout = 30
        
    async def inlet(self, body: Dict[str, Any], __user__: Dict[str, Any], __request__: Any, **kwargs) -> Dict[str, Any]:
        """
        Inlet filter function that processes the request before chat completion
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
            
            if not document_text.strip():
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
            api_response = call_custom_qa_api(
                user_query=user_message,
                document_text=document_text,
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
                
                log.info(f"govGpt-file-search-service response integrated for user {__user__['id']}")
            
            return body
            
        except Exception as e:
            log.error(f"Error in govGpt-file-search-service filter: {e}")
            # Return the original body if there's an error
            return body
    
    async def outlet(self, body: Dict[str, Any], __user__: Dict[str, Any], __request__: Any, **kwargs) -> Dict[str, Any]:
        """
        Outlet filter function that processes the response after chat completion
        """
        # For now, just return the body as-is
        # You can add post-processing logic here if needed
        return body
    
    async def stream(self, event: Dict[str, Any], __user__: Dict[str, Any], __request__: Any, **kwargs) -> Dict[str, Any]:
        """
        Stream filter function that processes streaming events
        """
        # For now, just return the event as-is
        # You can add streaming processing logic here if needed
        return event


# Create the filter instance
filter_instance = Filter() 