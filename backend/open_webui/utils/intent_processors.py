import logging
import re
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException
import httpx # For making async HTTP requests

log = logging.getLogger(__name__)

# Keywords to detect image generation intent
IMAGE_GEN_KEYWORDS = [
    "generate image", "create image", "draw image", "show image", "make image",
    "generate a picture", "create a picture", "draw a picture", "show a picture", "make a picture",
    "generate poster", "create poster", "design poster", "make poster",
    "generate photo", "create photo", "show photo", "make photo",
    "generate drawing", "create drawing", "draw drawing", "make drawing",
    "generate design", "create design", "design a", "make design",
    "generate art", "create art", "show art", "make art",
    "draw a", "generate a", "create a", "design a", "make a", "show a"
]

# Keywords that might indicate a refinement, but need context
REFINEMENT_KEYWORDS = [
    "change", "modify", "update", "add", "remove", "make it", "make them",
    "more", "less", "bigger", "smaller", "brighter", "darker",
    "another one", "different version", "try again with"
]


async def image_generation_intent_detector(
    user_message: str,
    chat_history: List[Dict[str, Any]],
    request: Request,
    current_chat_id: Optional[str] = None, # Added for context if needed
) -> Optional[Dict[str, Any]]:
    """
    Detects intent for image generation in a user message, calls an image generation service,
    and formats the response.

    Args:
        user_message: The current message from the user.
        chat_history: The history of the conversation.
        request: The FastAPI request object, used for making internal API calls.
        current_chat_id: The ID of the current chat.

    Returns:
        A dictionary containing the assistant's response message if image generation
        is successful, or None if no image generation intent is detected or an error occurs.
        The dict structure for a successful generation:
        {
            "role": "assistant",
            "content": "Here is the image you requested: ![image](image_url)",
            "metadata": {
                "is_generated_design": True,
                "original_prompt": "extracted_prompt",
                "image_url": "image_url",
                "engine_used": "engine_name", // Or None if not available
                "chat_id": current_chat_id, // For potential UI use
            }
        }
        If intent is detected but generation fails, it might return a message indicating failure.
        If no intent, returns None.
    """
    log.debug(f"ImageGenDetector: Processing message: '{user_message}'")
    user_message_lower = user_message.lower()
    
    detected_intent = False
    extracted_prompt = user_message # Default to full message
    is_refinement = False
    base_prompt_from_history = None
    previous_image_url = None

    # 1. Check for refinement intent first
    # Look for the last assistant message that was a generated design
    last_assistant_design_message = None
    for i in range(len(chat_history) - 1, -1, -1):
        msg = chat_history[i]
        if msg.get("role") == "assistant" and msg.get("metadata", {}).get("is_generated_design"):
            last_assistant_design_message = msg
            break

    if last_assistant_design_message:
        log.debug(f"ImageGenDetector: Found previous design: {last_assistant_design_message}")
        # Basic check if current message sounds like a refinement
        if any(keyword in user_message_lower for keyword in REFINEMENT_KEYWORDS) or \
           not any(gen_keyword in user_message_lower for gen_keyword in IMAGE_GEN_KEYWORDS): # if no explicit "generate"
            is_refinement = True
            base_prompt_from_history = last_assistant_design_message["metadata"]["original_prompt"]
            previous_image_url = last_assistant_design_message["metadata"]["image_url"]
            # For now, refinement means modifying the previous prompt
            # A more sophisticated approach would use NLP to understand the modification
            extracted_prompt = f"{base_prompt_from_history}, {user_message}" # Simple concatenation for now
            log.info(f"ImageGenDetector: Refinement detected. New combined prompt: '{extracted_prompt}'")
            detected_intent = True

    # 2. If not a refinement, check for new image generation intent
    if not detected_intent:
        for keyword in IMAGE_GEN_KEYWORDS:
            if keyword in user_message_lower:
                detected_intent = True
                # Attempt to extract a cleaner prompt by removing the keyword phrase
                # This is a basic approach and can be improved.
                # Example: "generate an image of a cat" -> "a cat"
                # Example: "a cat" (if keyword was "draw a")
                match = re.search(re.escape(keyword) + r"(?: of)?(?: an)?(?: a)?\s*(.*)", user_message, re.IGNORECASE)
                if match and match.group(1):
                    extracted_prompt = match.group(1).strip()
                elif user_message_lower.startswith(keyword): # "draw a cat"
                     extracted_prompt = user_message[len(keyword):].strip()
                else: # Fallback if regex fails but keyword is present
                    extracted_prompt = user_message
                
                if not extracted_prompt: # If keyword was at the end e.g. "generate an image"
                    log.warning("ImageGenDetector: Keyword detected but no prompt extracted. Needs more input.")
                    # Ask for more specific prompt, or handle as no intent for now
                    return { # Or return None and let LLM handle it
                        "role": "assistant",
                        "content": "It looks like you want to generate an image, but I need a description. What would you like me to create?",
                         "metadata": {"requires_clarification": True}
                    }

                log.info(f"ImageGenDetector: New image intent detected. Extracted prompt: '{extracted_prompt}'")
                break
    
    if not detected_intent:
        log.debug("ImageGenDetector: No image generation intent detected.")
        return None

    # 3. Call Image Generation Service
    # Construct the correct base URL for internal API calls
    # The /api/v1 prefix is usually handled by the app's router
    image_gen_url = f"{request.base_url}api/v1/images/generations"
    
    # Default payload structure - this might need adjustment based on actual /images/generations endpoint
    # We assume it takes a 'prompt' and might take 'model' (engine) or other params.
    # For now, we let the image generation service use its default model/engine.
    payload = {
        "prompt": extracted_prompt,
        # "model": "default_image_model_id", # If we need to specify or can get from config
        # Add other parameters like n, size, quality if supported and desired
    }

    # If it's a refinement, and the API supports image-to-image or editing:
    # This part is speculative as we don't know the API's capabilities for refinement.
    # For this subtask, we are just re-prompting for refinements.
    # if is_refinement and previous_image_url and some_condition_for_img2img:
    #     payload["image_url_to_edit"] = previous_image_url # Or image data
    #     payload["original_prompt"] = base_prompt_from_history # If API uses it

    log.debug(f"ImageGenDetector: Calling image generation service at {image_gen_url} with payload: {payload}")

    try:
        # Need an async HTTP client. If OpenWebUI uses a shared client, use that.
        # For now, creating a new one.
        async with httpx.AsyncClient(app=request.app, trust_env=False) as client:
            # We need to ensure cookies/auth are passed if the internal API requires them.
            # This might involve forwarding headers from the original `request` object.
            headers = {"Cookie": request.headers.get("cookie")} if request.headers.get("cookie") else {}
            
            response = await client.post(image_gen_url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()  # Raises an exception for 4XX/5XX responses
            
            response_data = response.json()
            log.debug(f"ImageGenDetector: Response from image service: {response_data}")

            # Assuming the response_data is a list of generated images,
            # and each image object has a 'url' and potentially 'engine' or 'model_id'
            # Taking the first image if multiple are returned.
            if isinstance(response_data, list) and len(response_data) > 0:
                image_info = response_data[0]
                image_url = image_info.get("url") # Adjust key if necessary
                engine_used = image_info.get("engine") or image_info.get("model_id") # Adjust key
            elif isinstance(response_data, dict) and response_data.get("url"): # Single image response
                image_url = response_data.get("url")
                engine_used = response_data.get("engine") or response_data.get("model_id")
            else:
                log.error(f"ImageGenDetector: Unexpected response format from image service: {response_data}")
                return {
                    "role": "assistant",
                    "content": "I tried to generate the image, but I received an unexpected response from the image service.",
                    "metadata": {"error": True, "details": "Unexpected response format"}
                }

            if not image_url:
                log.error(f"ImageGenDetector: No image URL found in response: {response_data}")
                return {
                    "role": "assistant",
                    "content": "I tried to generate the image, but couldn't find the image URL in the response.",
                     "metadata": {"error": True, "details": "No image URL in response"}
                }

            # 4. Format Response
            assistant_message_content = f"Here is the image you requested: ![image]({image_url})"
            if is_refinement:
                assistant_message_content = f"Okay, I've updated the image: ![image]({image_url})"
            
            chat_message = {
                "role": "assistant",
                "content": assistant_message_content,
                "metadata": {
                    "is_generated_design": True,
                    "original_prompt": extracted_prompt, # The prompt used for *this* generation
                    "base_prompt_if_refinement": base_prompt_from_history if is_refinement else None,
                    "image_url": image_url,
                    "engine_used": engine_used,
                    "chat_id": current_chat_id,
                }
            }
            log.info(f"ImageGenDetector: Successfully generated image. Response: {chat_message}")
            return chat_message

    except httpx.HTTPStatusError as e:
        log.error(f"ImageGenDetector: HTTP error from image service: {e.response.status_code} - {e.response.text}")
        error_detail = f"Image service returned error {e.response.status_code}."
        try:
            error_content = e.response.json()
            if error_content.get("detail"):
                 error_detail = error_content.get("detail")
        except:
            pass # Keep generic error_detail

        return {
            "role": "assistant",
            "content": f"Sorry, I couldn't generate the image. {error_detail}",
            "metadata": {"error": True, "details": str(e)}
        }
    except httpx.RequestError as e:
        log.error(f"ImageGenDetector: Request error calling image service: {e}")
        return {
            "role": "assistant",
            "content": "Sorry, I couldn't reach the image generation service. Please try again later.",
            "metadata": {"error": True, "details": str(e)}
        }
    except Exception as e:
        log.exception("ImageGenDetector: An unexpected error occurred.")
        return {
            "role": "assistant",
            "content": "An unexpected error occurred while trying to generate the image.",
            "metadata": {"error": True, "details": str(e)}
        }

async def example_usage():
    # This is a mock request object for testing purposes
    class MockApp:
        async def __call__(self, scope, receive, send):
            if scope["path"] == "/api/v1/images/generations" and scope["method"] == "POST":
                # Simulate a successful image generation response
                response_body = json.dumps([{
                    "url": "http://example.com/generated_image.png",
                    "engine": "mock_engine_v1",
                    "prompt": json.loads(await receive()["body"].decode())["prompt"]
                }])
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": response_body.encode("utf-8"),
                })
                return
            # Simulate an error response for a specific prompt
            if scope["path"] == "/api/v1/images/generations" and \
               json.loads(await receive()["body"].decode())["prompt"] == "error_prompt":
                response_body = json.dumps({"detail": "Simulated error from image service"})
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": response_body.encode("utf-8"),
                })
                return

            # Default not found
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b""})


    class MockRequest:
        def __init__(self, base_url="http://localhost:8080/", app=None, headers=None):
            self.base_url = base_url
            self.app = app or MockApp()
            self.headers = headers or {}


    # Test cases
    chat_history_1 = []
    user_message_1 = "Can you generate an image of a happy cat?"
    
    print(f"\n--- Test Case 1: New Image ---")
    print(f"User: {user_message_1}")
    response_1 = await image_generation_intent_detector(user_message_1, chat_history_1, MockRequest(), "chat1")
    print(f"Assistant: {response_1}")

    chat_history_2 = [
        {"role": "user", "content": "Generate a poster for a rock concert"},
        {
            "role": "assistant",
            "content": "Here is the image you requested: ![image](http://example.com/rock_poster_v1.png)",
            "metadata": {
                "is_generated_design": True,
                "original_prompt": "a poster for a rock concert",
                "image_url": "http://example.com/rock_poster_v1.png",
                "engine_used": "mock_engine_v1",
                "chat_id": "chat2",
            }
        }
    ]
    user_message_2 = "Make the font psychedelic."
    print(f"\n--- Test Case 2: Refinement ---")
    print(f"User: {user_message_2}")
    response_2 = await image_generation_intent_detector(user_message_2, chat_history_2, MockRequest(), "chat2")
    print(f"Assistant: {response_2}")

    user_message_3 = "What is the capital of France?"
    print(f"\n--- Test Case 3: No Intent ---")
    print(f"User: {user_message_3}")
    response_3 = await image_generation_intent_detector(user_message_3, chat_history_1, MockRequest(), "chat3")
    print(f"Assistant: {response_3}")

    user_message_4 = "Generate an image" # Needs clarification
    print(f"\n--- Test Case 4: Needs Clarification ---")
    print(f"User: {user_message_4}")
    response_4 = await image_generation_intent_detector(user_message_4, chat_history_1, MockRequest(), "chat4")
    print(f"Assistant: {response_4}")

    user_message_5 = "Please draw a picture of error_prompt"
    print(f"\n--- Test Case 5: Image Service Error ---")
    print(f"User: {user_message_5}")
    response_5 = await image_generation_intent_detector(user_message_5, chat_history_1, MockRequest(app=MockApp()), "chat5")
    print(f"Assistant: {response_5}")

if __name__ == "__main__":
    import asyncio
    import json # for MockApp
    # Setup basic logging for the example
    logging.basicConfig(level=logging.DEBUG)
    # asyncio.run(example_usage()) # Commented out for tool environment
    pass
