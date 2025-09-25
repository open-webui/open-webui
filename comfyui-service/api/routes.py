"""
ComfyUI API Routes
Handles all image generation requests using Fal.ai API
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import base64
import io
from PIL import Image
import aiofiles
import os
import time
import requests
import json

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Pydantic models for request/response
class TextToImageRequest(BaseModel):
    """Text to image generation request"""
    prompt: str = Field(..., description="Text description for image generation")
    negative_prompt: Optional[str] = Field(default="", description="What to avoid in the image")
    width: int = Field(default=1024, ge=256, le=2048, description="Image width")
    height: int = Field(default=1024, ge=256, le=2048, description="Image height")
    num_images: int = Field(default=1, ge=1, le=4, description="Number of images to generate")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="How closely to follow the prompt")
    num_inference_steps: int = Field(default=28, ge=10, le=50, description="Generation steps (more = higher quality)")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible results")

class ImageToImageRequest(BaseModel):
    """Image to image generation request"""
    prompt: str = Field(..., description="Text description for transformation")
    negative_prompt: Optional[str] = Field(default="", description="What to avoid in the image")
    width: int = Field(default=1024, ge=256, le=2048, description="Output width")
    height: int = Field(default=1024, ge=256, le=2048, description="Output height")
    strength: float = Field(default=0.8, ge=0.1, le=1.0, description="Transformation strength")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="How closely to follow the prompt")
    num_inference_steps: int = Field(default=28, ge=10, le=50, description="Generation steps")
    seed: Optional[int] = Field(default=None, description="Random seed")

class MultimodalRequest(BaseModel):
    """Multimodal generation request (text + reference image)"""
    prompt: str = Field(..., description="Main text description")
    style_prompt: Optional[str] = Field(default="", description="Style description from reference image")
    negative_prompt: Optional[str] = Field(default="", description="What to avoid")
    width: int = Field(default=1024, ge=256, le=2048, description="Output width")
    height: int = Field(default=1024, ge=256, le=2048, description="Output height")
    style_strength: float = Field(default=0.6, ge=0.1, le=1.0, description="How much style to apply")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="Prompt adherence")
    num_inference_steps: int = Field(default=28, ge=10, le=50, description="Generation steps")
    seed: Optional[int] = Field(default=None, description="Random seed")

class ImageResponse(BaseModel):
    """Standard image generation response"""
    success: bool
    message: str
    images: List[str]  # Base64 encoded images
    generation_time: float
    parameters: dict

# Helper functions
async def process_uploaded_image(image: UploadFile) -> str:
    """Process uploaded image and return base64 string"""
    try:
        # Read image data
        contents = await image.read()
        
        # Open with PIL to validate and potentially resize
        pil_image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Resize if too large (optional, for efficiency)
        max_size = 1024
        if pil_image.width > max_size or pil_image.height > max_size:
            pil_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffered = io.BytesIO()
        pil_image.save(buffered, format="JPEG", quality=90)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{img_base64}"
    
    except Exception as e:
        logger.error(f"Error processing uploaded image: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

async def call_huggingface_api(model_name: str, inputs: dict) -> dict:
    """Call Hugging Face API with error handling"""
    try:
        start_time = time.time()
        
        # Hugging Face API endpoint
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        # Get API token from environment (you'll need to set this)
        api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # For development, we'll simulate the API call
        logger.info(f"Calling Hugging Face API: {model_name} with inputs: {inputs}")
        
        # TODO: Replace this simulation with actual Hugging Face API call
        # response = requests.post(api_url, headers=headers, json=inputs)
        
        # Simulated response for development
        result = {
            "images": [
                {
                    "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD...",  # Placeholder
                    "width": inputs.get("image_size", {}).get("width", 1024),
                    "height": inputs.get("image_size", {}).get("height", 1024)
                }
            ]
        }
        
        generation_time = time.time() - start_time
        logger.info(f"Hugging Face API call completed in {generation_time:.2f}s")
        
        return {
            "result": result,
            "generation_time": generation_time
        }
    
    except Exception as e:
        logger.error(f"Hugging Face API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

# Temporary alias to avoid errors
call_fal_api = call_huggingface_api



# API Endpoints

@router.post("/generate/text-to-image", response_model=ImageResponse)
async def generate_text_to_image(request: TextToImageRequest):
    """
    Generate images from text description
    
    This endpoint creates images based on text prompts using Flux model
    """
    logger.info(f"Text-to-image request: {request.prompt}")
    
    try:
        # Prepare inputs for Fal.ai API
        inputs = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "image_size": {
                "width": request.width,
                "height": request.height
            },
            "num_images": request.num_images,
            "guidance_scale": request.guidance_scale,
            "num_inference_steps": request.num_inference_steps,
            "enable_safety_checker": True
        }
        
        if request.seed:
            inputs["seed"] = request.seed
        
        # Call Hugging Face API
        api_response = await call_huggingface_api("stabilityai/stable-diffusion-xl-base-1.0", inputs)
        
        # Process response
        images = []
        for img_data in api_response["result"]["images"]:
            # In real implementation, you'd download the image from URL and convert to base64
            # For now, return placeholder
            images.append("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD...")  # Placeholder
        
        return ImageResponse(
            success=True,
            message="Images generated successfully",
            images=images,
            generation_time=api_response["generation_time"],
            parameters=inputs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text-to-image generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/image-to-image", response_model=ImageResponse)
async def generate_image_to_image(
    image: UploadFile = File(..., description="Input image file"),
    prompt: str = Form(..., description="Transformation prompt"),
    negative_prompt: str = Form("", description="Negative prompt"),
    width: int = Form(1024, description="Output width"),
    height: int = Form(1024, description="Output height"),
    strength: float = Form(0.8, description="Transformation strength"),
    guidance_scale: float = Form(7.5, description="Guidance scale"),
    num_inference_steps: int = Form(28, description="Number of steps"),
    seed: Optional[int] = Form(None, description="Random seed")
):
    """
    Transform existing images based on text prompts
    
    Upload an image and provide a prompt to transform it
    """
    logger.info(f"Image-to-image request: {prompt}")
    
    try:
        # Process uploaded image
        image_base64 = await process_uploaded_image(image)
        
        # Prepare inputs for Fal.ai API
        inputs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_url": image_base64,  # Fal.ai can accept base64 data URLs
            "image_size": {
                "width": width,
                "height": height
            },
            "strength": strength,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "enable_safety_checker": True
        }
        
        if seed:
            inputs["seed"] = seed
        
        # Call Fal.ai API
        api_response = await call_fal_api("flux-pro/image-to-image", inputs)
        
        # Process response
        images = []
        for img_data in api_response["result"]["images"]:
            images.append("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD...")  # Placeholder
        
        return ImageResponse(
            success=True,
            message="Image transformation completed successfully",
            images=images,
            generation_time=api_response["generation_time"],
            parameters=inputs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image-to-image generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/multimodal", response_model=ImageResponse)
async def generate_multimodal(
    subject_image: UploadFile = File(..., description="Main subject image"),
    style_image: Optional[UploadFile] = File(None, description="Style reference image"),
    prompt: str = Form(..., description="Generation prompt"),
    style_prompt: str = Form("", description="Style description"),
    negative_prompt: str = Form("", description="Negative prompt"),
    width: int = Form(1024, description="Output width"),
    height: int = Form(1024, description="Output height"),
    style_strength: float = Form(0.6, description="Style application strength"),
    guidance_scale: float = Form(7.5, description="Guidance scale"),
    num_inference_steps: int = Form(28, description="Number of steps"),
    seed: Optional[int] = Form(None, description="Random seed")
):
    """
    Generate images using multiple inputs (text + images)
    
    Example: Apply clothing from one image to a person in another image
    """
    logger.info(f"Multimodal request: {prompt}")
    
    try:
        # Process main subject image
        subject_base64 = await process_uploaded_image(subject_image)
        
        # Process style image if provided
        style_base64 = None
        if style_image:
            style_base64 = await process_uploaded_image(style_image)
        
        # Prepare inputs for Fal.ai API
        inputs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "subject_image": subject_base64,
            "image_size": {
                "width": width,
                "height": height
            },
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "enable_safety_checker": True
        }
        
        # Add style inputs if style image provided
        if style_base64:
            inputs["style_image"] = style_base64
            inputs["style_prompt"] = style_prompt
            inputs["style_strength"] = style_strength
        
        if seed:
            inputs["seed"] = seed
        
        # Call Fal.ai API
        api_response = await call_fal_api("flux-pro/multimodal", inputs)
        
        # Process response
        images = []
        for img_data in api_response["result"]["images"]:
            images.append("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD...")  # Placeholder
        
        return ImageResponse(
            success=True,
            message="Multimodal generation completed successfully",
            images=images,
            generation_time=api_response["generation_time"],
            parameters=inputs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multimodal generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/multimodal-advanced", response_model=ImageResponse)
async def generate_multimodal_advanced(
    primary_image: UploadFile = File(..., description="Main subject image (e.g., person, object)"),
    secondary_image: Optional[UploadFile] = File(None, description="Second reference image (e.g., clothing, style)"),
    tertiary_image: Optional[UploadFile] = File(None, description="Third reference image (e.g., background, scene)"),
    prompt: str = Form(..., description="Main generation prompt"),
    primary_prompt: str = Form("", description="Specific instructions for primary image"),
    secondary_prompt: str = Form("", description="Specific instructions for secondary image"),
    tertiary_prompt: str = Form("", description="Specific instructions for tertiary image"),
    composition_prompt: str = Form("", description="How to combine all elements"),
    negative_prompt: str = Form("", description="What to avoid"),
    width: int = Form(1024, description="Output width"),
    height: int = Form(1024, description="Output height"),
    primary_weight: float = Form(0.6, description="Influence of primary image (0.0-1.0)"),
    secondary_weight: float = Form(0.3, description="Influence of secondary image (0.0-1.0)"),
    tertiary_weight: float = Form(0.1, description="Influence of tertiary image (0.0-1.0)"),
    guidance_scale: float = Form(7.5, description="Guidance scale"),
    num_inference_steps: int = Form(28, description="Number of steps"),
    seed: Optional[int] = Form(None, description="Random seed")
):
    """
    Advanced multimodal generation with up to 3 images and complex instructions
    
    Examples:
    - Fashion: Person + Clothing + Background scene
    - Interior: Furniture + Color scheme + Room layout  
    - Character: Base character + Outfit + Environment
    """
    logger.info(f"Advanced multimodal request: {prompt}")
    
    try:
        # Process primary image (required)
        primary_base64 = await process_uploaded_image(primary_image)
        
        # Process secondary image if provided
        secondary_base64 = None
        if secondary_image:
            secondary_base64 = await process_uploaded_image(secondary_image)
        
        # Process tertiary image if provided  
        tertiary_base64 = None
        if tertiary_image:
            tertiary_base64 = await process_uploaded_image(tertiary_image)
        
        # Build comprehensive prompt
        full_prompt_parts = [prompt]
        
        if primary_prompt:
            full_prompt_parts.append(f"Primary element: {primary_prompt}")
        if secondary_prompt and secondary_image:
            full_prompt_parts.append(f"Secondary element: {secondary_prompt}")
        if tertiary_prompt and tertiary_image:
            full_prompt_parts.append(f"Background/Environment: {tertiary_prompt}")
        if composition_prompt:
            full_prompt_parts.append(f"Composition: {composition_prompt}")
        
        combined_prompt = ". ".join(full_prompt_parts)
        
        # Prepare inputs for Fal.ai API
        inputs = {
            "prompt": combined_prompt,
            "negative_prompt": negative_prompt,
            "primary_image": primary_base64,
            "primary_weight": primary_weight,
            "image_size": {
                "width": width,
                "height": height
            },
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "enable_safety_checker": True
        }
        
        # Add secondary image inputs
        if secondary_base64:
            inputs["secondary_image"] = secondary_base64
            inputs["secondary_weight"] = secondary_weight
        
        # Add tertiary image inputs
        if tertiary_base64:
            inputs["tertiary_image"] = tertiary_base64
            inputs["tertiary_weight"] = tertiary_weight
        
        if seed:
            inputs["seed"] = seed
        
        # Call Fal.ai API
        api_response = await call_fal_api("flux-pro/multimodal-advanced", inputs)
        
        # Process response
        images = []
        for img_data in api_response["result"]["images"]:
            images.append("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD...")  # Placeholder
        
        return ImageResponse(
            success=True,
            message="Advanced multimodal generation completed successfully",
            images=images,
            generation_time=api_response["generation_time"],
            parameters=inputs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Advanced multimodal generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/fashion-transfer", response_model=ImageResponse)  
async def generate_fashion_transfer(
    person_image: UploadFile = File(..., description="Photo of the person"),
    clothing_image: UploadFile = File(..., description="Clothing item to transfer"),
    scene_image: Optional[UploadFile] = File(None, description="Background scene (optional)"),
    prompt: str = Form("high quality fashion photo", description="Style description"),
    clothing_type: str = Form("clothing", description="Type of clothing (shirt, dress, pants, etc.)"),
    fit_adjustment: str = Form("well-fitted", description="How the clothing should fit"),
    lighting: str = Form("natural lighting", description="Lighting preference"), 
    pose_instruction: str = Form("maintain original pose", description="Pose adjustments"),
    negative_prompt: str = Form("blurry, distorted, unrealistic", description="What to avoid"),
    width: int = Form(1024, description="Output width"),
    height: int = Form(1024, description="Output height"),
    clothing_strength: float = Form(0.8, description="How strongly to apply clothing (0.0-1.0)"),
    scene_strength: float = Form(0.3, description="Background influence (0.0-1.0)"),
    guidance_scale: float = Form(7.5, description="Guidance scale"),
    num_inference_steps: int = Form(30, description="Number of steps"),
    seed: Optional[int] = Form(None, description="Random seed")
):
    """
    Specialized fashion transfer endpoint
    
    Perfect for: "Put the shirt from image 1 on the person in image 2, in the scene from image 3"
    """
    logger.info(f"Fashion transfer request: {clothing_type} transfer")
    
    try:
        # Process images
        person_base64 = await process_uploaded_image(person_image)
        clothing_base64 = await process_uploaded_image(clothing_image)
        
        scene_base64 = None
        if scene_image:
            scene_base64 = await process_uploaded_image(scene_image)
        
        # Build specialized fashion prompt
        fashion_prompt = f"""
        {prompt}, person wearing {clothing_type}, {fit_adjustment}, {lighting}, {pose_instruction}.
        Transfer the {clothing_type} from the reference image onto the person while maintaining their pose and appearance.
        High quality, realistic, detailed clothing texture, proper fit and draping.
        """
        
        inputs = {
            "prompt": fashion_prompt.strip(),
            "negative_prompt": f"{negative_prompt}, wrong size, floating clothes, disconnected parts",
            "person_image": person_base64,
            "clothing_reference": clothing_base64,
            "clothing_strength": clothing_strength,
            "image_size": {"width": width, "height": height},
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "enable_safety_checker": True
        }
        
        if scene_base64:
            inputs["background_image"] = scene_base64
            inputs["background_strength"] = scene_strength
        
        if seed:
            inputs["seed"] = seed
        
        # Call specialized fashion API
        api_response = await call_fal_api("flux-pro/fashion-transfer", inputs)
        
        images = []
        for img_data in api_response["result"]["images"]:
            images.append("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD...")
        
        return ImageResponse(
            success=True,
            message=f"Fashion transfer completed: {clothing_type} successfully applied",
            images=images,
            generation_time=api_response["generation_time"],
            parameters=inputs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fashion transfer failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_available_models():
    """List available models and their capabilities"""
    return {
        "models": {
            "flux-pro": {
                "description": "High-quality image generation",
                "features": ["text-to-image", "image-to-image"],
                "max_resolution": "2048x2048"
            },
            "flux-pro/image-to-image": {
                "description": "Image transformation",
                "features": ["image-to-image"],
                "max_resolution": "2048x2048"
            },
            "flux-pro/multimodal": {
                "description": "Multi-input generation",
                "features": ["text + image", "style transfer"],
                "max_resolution": "2048x2048"
            },
            "flux-pro/multimodal-advanced": {
                "description": "Advanced multi-input generation",
                "features": ["text + 3 images", "complex composition"],
                "max_resolution": "2048x2048"
            },
            "flux-pro/fashion-transfer": {
                "description": "Specialized fashion and clothing transfer",
                "features": ["clothing transfer", "fashion styling"],
                "max_resolution": "2048x2048"
            }
        }
    }

@router.get("/generate/status/{request_id}")
async def get_generation_status(request_id: str):
    """Get the status of a generation request (for async operations)"""
    # This would be used for long-running generations
    return {
        "request_id": request_id,
        "status": "completed",  # completed, processing, failed
        "message": "Generation completed successfully"
    }