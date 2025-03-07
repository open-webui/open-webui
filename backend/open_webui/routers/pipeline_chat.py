import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from open_webui.models.auths import AuthsTable
from open_webui.models.chats import ChatTable
from open_webui.models.messages import MessageModel, MessageTable, MessageForm
from open_webui.models.users import UserModel
from open_webui.services.pipeline_connector import pipeline_connector
from open_webui.utils.auth import get_current_user
from pydantic import BaseModel


router = APIRouter()
log = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

class ChatMessage(BaseModel):
    content: str
    city: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    content: str
    user_id: str
    created_at: int
    activities: Optional[List[Dict[str, Any]]] = None

@router.websocket("/ws/chat/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time chat with the pipeline
    """
    await websocket.accept()
    
    # Store the connection
    active_connections[user_id] = websocket
    
    try:
        # Process messages
        while True:
            try:
                # Receive the message
                data = await websocket.receive_json()
                
                # Extract content and city
                content = data.get("content", "")
                city = data.get("city")
                
                if not content:
                    await websocket.send_json({"error": "Message content is required"})
                    continue
                
                # Generate a message ID
                message_id = str(uuid.uuid4())
                
                # Store the message in the database
                message_table = MessageTable()
                message_form = MessageForm(content=content)
                message = message_table.insert_new_message(
                    form_data=message_form,
                    channel_id="pipeline",
                    user_id=user_id
                )
                
                if not message:
                    await websocket.send_json({"error": "Failed to store message"})
                    continue
                
                # Send an acknowledgment to the client
                await websocket.send_json({
                    "type": "message_received",
                    "message_id": message.id,
                    "content": message.content,
                    "user_id": message.user_id,
                    "created_at": message.created_at
                })
                
                # Define a callback to handle the response
                async def handle_response(response_data: Dict[str, Any]):
                    try:
                        # Extract the response content
                        response_content = response_data.get("content", "")
                        activities = response_data.get("activities", [])
                        
                        # Store the response in the database
                        response_form = MessageForm(
                            content=response_content,
                            parent_id=message.id,
                            data={"activities": activities} if activities else None
                        )
                        response_message = message_table.insert_new_message(
                            form_data=response_form,
                            channel_id="pipeline",
                            user_id="system"  # Indicate this is from the system
                        )
                        
                        if not response_message:
                            await websocket.send_json({"error": "Failed to store response"})
                            return
                        
                        # Send the response to the client
                        await websocket.send_json({
                            "type": "message_response",
                            "message_id": response_message.id,
                            "content": response_message.content,
                            "user_id": response_message.user_id,
                            "created_at": response_message.created_at,
                            "activities": activities
                        })
                        
                        # If this is the final response, update the chat history
                        if response_data.get("final", False):
                            # Add any final processing here
                            pass
                            
                    except Exception as e:
                        log.error(f"Error handling response: {e}")
                        await websocket.send_json({"error": f"Error handling response: {str(e)}"})
                
                # Send the message to the pipeline
                await pipeline_connector.send_message(
                    message_type="activity_search" if city else "chat",
                    content=content,
                    user_id=user_id,
                    city=city,
                    callback=handle_response
                )
                
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                
            except Exception as e:
                log.error(f"Error processing message: {e}")
                await websocket.send_json({"error": f"Error: {str(e)}"})
                
    except WebSocketDisconnect:
        # Remove the connection when the client disconnects
        if user_id in active_connections:
            del active_connections[user_id]
            
@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(
    message: ChatMessage,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Send a chat message to the pipeline using HTTP
    """
    try:
        # Store the message in the database
        message_table = MessageTable()
        message_form = MessageForm(content=message.content)
        message_model = message_table.insert_new_message(
            form_data=message_form,
            channel_id="pipeline",
            user_id=current_user.id
        )
        
        if not message_model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store message"
            )
            
        # Create a future to wait for the response
        response_future = asyncio.Future()
        
        # Define a callback to handle the response
        async def handle_response(response_data: Dict[str, Any]):
            try:
                # Extract the response content
                response_content = response_data.get("content", "")
                activities = response_data.get("activities", [])
                
                # Store the response in the database
                response_form = MessageForm(
                    content=response_content,
                    parent_id=message_model.id,
                    data={"activities": activities} if activities else None
                )
                response_message = message_table.insert_new_message(
                    form_data=response_form,
                    channel_id="pipeline",
                    user_id="system"  # Indicate this is from the system
                )
                
                if not response_message:
                    response_future.set_exception(Exception("Failed to store response"))
                    return
                
                # Set the result of the future
                if not response_future.done():
                    response_future.set_result({
                        "id": response_message.id,
                        "content": response_message.content,
                        "user_id": response_message.user_id,
                        "created_at": response_message.created_at,
                        "activities": activities
                    })
                    
            except Exception as e:
                log.error(f"Error handling response: {e}")
                if not response_future.done():
                    response_future.set_exception(e)
        
        # Send the message to the pipeline
        await pipeline_connector.send_message(
            message_type="activity_search" if message.city else "chat",
            content=message.content,
            user_id=current_user.id,
            city=message.city,
            callback=handle_response
        )
        
        # Wait for the response with a timeout
        try:
            response_data = await asyncio.wait_for(response_future, timeout=30.0)
            return ChatResponse(**response_data)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request to pipeline timed out"
            )
            
    except Exception as e:
        log.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )

@router.get("/chat/history", response_model=List[ChatResponse])
async def get_chat_history(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get the chat history for the current user
    """
    try:
        message_table = MessageTable()
        messages = message_table.get_messages_by_channel_id(
            channel_id="pipeline",
            limit=50  # Limit to most recent 50 messages
        )
        
        # Filter to only include messages from the current user or system responses to them
        user_messages = {}
        system_responses = {}
        
        for message in messages:
            if message.user_id == current_user.id:
                user_messages[message.id] = message
            elif message.user_id == "system" and message.parent_id in user_messages:
                system_responses[message.parent_id] = message
                
        # Combine user messages with their responses
        history = []
        for msg_id, user_msg in user_messages.items():
            if msg_id in system_responses:
                system_msg = system_responses[msg_id]
                activities = system_msg.data.get("activities", []) if system_msg.data else None
                
                history.append(ChatResponse(
                    id=system_msg.id,
                    content=system_msg.content,
                    user_id=system_msg.user_id,
                    created_at=system_msg.created_at,
                    activities=activities
                ))
                
        # Sort by creation time
        history.sort(key=lambda x: x.created_at, reverse=True)
        
        return history
        
    except Exception as e:
        log.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        ) 