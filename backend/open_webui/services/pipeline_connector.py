import asyncio
import json
import logging
import aio_pika
from typing import Dict, Any, Optional, List, Callable, Awaitable
import httpx
from open_webui.config import RABBIT_MQ_URL

log = logging.getLogger(__name__)

class PipelineConnector:
    """
    Connector service to communicate with the Pandemonium LLM pipeline
    """
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.callback_map = {}  # Maps correlation IDs to callbacks
        self.response_queues = {}  # Maps correlation IDs to response queues
        
        # Define the pipeline processing queues
        self.processing_queues = {
            'activity_search': 'activity_search_queue',
            'response_generation': 'response_generation_queue',
            'client_response': 'client_response_queue'
        }
        
    async def initialize(self):
        """Initialize the connection to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            try:
                # Use the RabbitMQ URL from the app pipeline configuration
                self.connection = await aio_pika.connect_robust(
                    RABBIT_MQ_URL or "amqp://guest:guest@rabbitmq/"
                )
                log.info("✅ Connected to RabbitMQ for pipeline communication")
                
                # Create a channel
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=1)
                
                # Declare the exchange
                self.exchange = await self.channel.declare_exchange(
                    "pandemonium_pipeline", 
                    aio_pika.ExchangeType.TOPIC
                )
                
                # Declare the processing queues
                for queue_name in self.processing_queues.values():
                    await self.channel.declare_queue(queue_name, durable=True)
                    
                log.info("✅ Initialized RabbitMQ pipeline connector")
                
            except Exception as e:
                log.error(f"Failed to initialize RabbitMQ connection: {e}")
                # Try to fall back to HTTP connection if RabbitMQ is not available
                log.info("⚠️ Falling back to HTTP connection for pipeline communication")
                
    async def send_message(self, 
                          message_type: str, 
                          content: str, 
                          user_id: str, 
                          city: Optional[str] = None, 
                          callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None) -> str:
        """
        Send a message to the pipeline for processing
        
        Args:
            message_type: Type of message (e.g., 'chat', 'search')
            content: Message content
            user_id: User ID
            city: Optional city filter for activities
            callback: Optional callback function to handle the response
            
        Returns:
            correlation_id: ID to track the message
        """
        correlation_id = f"{user_id}_{asyncio.get_event_loop().time()}"
        
        message_data = {
            "type": message_type,
            "content": content,
            "user_id": user_id,
            "correlation_id": correlation_id
        }
        
        if city:
            message_data["city"] = city
            
        try:
            if self.connection and not self.connection.is_closed:
                # Register callback if provided
                if callback:
                    self.callback_map[correlation_id] = callback
                    
                    # Create a response queue for this request
                    response_queue = await self.channel.declare_queue(
                        f"response_{correlation_id}", 
                        exclusive=True,
                        auto_delete=True
                    )
                    
                    # Bind the queue to the exchange with the correlation ID as routing key
                    await response_queue.bind(
                        self.exchange,
                        routing_key=f"response.{correlation_id}"
                    )
                    
                    # Start consuming from the response queue
                    await response_queue.consume(
                        self._process_response,
                        no_ack=True
                    )
                    
                    # Store the queue reference
                    self.response_queues[correlation_id] = response_queue
                
                # Publish the message
                await self.exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(message_data).encode(),
                        correlation_id=correlation_id,
                        content_type="application/json",
                        reply_to=f"response.{correlation_id}" if callback else None
                    ),
                    routing_key=self.processing_queues.get(message_type, "activity_search_queue")
                )
                
                log.info(f"✅ Message sent to pipeline: {message_type} (correlation_id: {correlation_id})")
                
            else:
                # Fall back to HTTP if RabbitMQ is not available
                log.warning("⚠️ RabbitMQ not available, using HTTP fallback")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://app:8000/api/chat/process",
                        json=message_data,
                        timeout=60.0
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if callback:
                            await callback(response_data)
                    else:
                        log.error(f"HTTP request to pipeline failed: {response.text}")
                
        except Exception as e:
            log.error(f"Error sending message to pipeline: {e}")
            
        return correlation_id
        
    async def _process_response(self, message: aio_pika.IncomingMessage):
        """Process response messages from the pipeline"""
        try:
            # Parse the message
            correlation_id = message.correlation_id
            data = json.loads(message.body.decode())
            
            # Look up the callback for this correlation ID
            callback = self.callback_map.get(correlation_id)
            if callback:
                await callback(data)
                
                # Clean up if this is the final message
                if data.get("final", False):
                    del self.callback_map[correlation_id]
                    if correlation_id in self.response_queues:
                        # Queue will be auto-deleted when it's closed
                        del self.response_queues[correlation_id]
                        
        except Exception as e:
            log.error(f"Error processing pipeline response: {e}")
            
    async def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            log.info("✅ Closed RabbitMQ pipeline connection")
            
pipeline_connector = PipelineConnector() 