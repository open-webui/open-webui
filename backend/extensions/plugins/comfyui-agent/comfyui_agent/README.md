# ComfyUI Agent Plugin for Open WebUI

This plugin provides intelligent image generation capabilities using ComfyUI with CLIP-guided refinement. It allows any LLM to generate and analyze images through function calls.

## Features

- 🎨 Intelligent image generation with automatic refinement
- 📊 CLIP-based image-text similarity scoring
- 🔄 Progressive parameter adjustment
- 📝 Detailed generation feedback

## Installation

1. **Prerequisites**
   - Open WebUI installed and running
   - ComfyUI installed and running on port 8188
   - CUDA-capable GPU (recommended)

2. **Install the Plugin**
   ```bash
   cd /path/to/open-webui/extensions
   git clone https://github.com/yourusername/comfyui-agent.git
   cd comfyui-agent
   pip install -r requirements.txt
   ```

3. **Restart Open WebUI**
   The plugin will be automatically detected and loaded.

## Usage in LLM Conversations

### Generate Image

```python
# Example function call in LLM conversation
{
    "function": "generate_image",
    "parameters": {
        "description": "A beautiful sunset over mountains with a calm lake in the foreground",
        "max_attempts": 5,
        "cfg_scale": 7.0,
        "steps": 20,
        "width": 512,
        "height": 512
    }
}
```

Response:
```python
{
    "success": true,
    "image_path": "/path/to/generated_20231229_123456.png",
    "image_base64": "base64_encoded_image_data...",
    "metadata": {
        "generation_history": [...],
        "parameters": {...},
        "scores": {...}
    },
    "message": "Image generated successfully"
}
```

### Analyze Image

```python
# Example function call
{
    "function": "analyze_image",
    "parameters": {
        "image_path": "/path/to/image.png",
        "description": "A beautiful sunset over mountains"
    }
}
```

Response:
```python
{
    "success": true,
    "score": 0.85,
    "feedback": {
        "overall_score": 0.85,
        "aspects": {
            "color_scheme": {
                "score": 0.88,
                "suggestion": "Colors match well"
            },
            "composition": {
                "score": 0.82,
                "suggestion": "Composition is good"
            }
        }
    },
    "message": "Analysis completed successfully"
}
```

## Example Conversations

1. **Basic Image Generation**
   ```
   User: Generate an image of a serene mountain landscape at sunset.
   Assistant: I'll help you generate that image using the ComfyUI agent.
   
   {
       "function": "generate_image",
       "parameters": {
           "description": "A serene mountain landscape at sunset with warm golden light, majestic peaks, and a peaceful atmosphere"
       }
   }
   
   Here's your generated image! The agent made several refinements to ensure the best quality:
   1. Adjusted the lighting to enhance the sunset atmosphere
   2. Fine-tuned the composition for better mountain placement
   3. Enhanced the color palette for more dramatic effects
   ```

2. **Image Analysis**
   ```
   User: How well does this image match my description?
   Assistant: Let me analyze the image using CLIP.
   
   {
       "function": "analyze_image",
       "parameters": {
           "image_path": "generated_20231229_123456.png",
           "description": "A serene mountain landscape at sunset"
       }
   }
   
   The image matches your description quite well:
   - Overall similarity score: 0.85
   - Color scheme is particularly strong (0.88)
   - Composition is well-balanced (0.82)
   - Lighting captures the sunset mood effectively
   ```

## Function Parameters

### generate_image
- `description` (required): Text description of the desired image
- `max_attempts` (optional): Maximum generation attempts (default: 5)
- `cfg_scale` (optional): Initial CFG scale (default: 7.0)
- `steps` (optional): Initial number of steps (default: 20)
- `width` (optional): Image width (default: 512)
- `height` (optional): Image height (default: 512)

### analyze_image
- `image_path` (required): Path to the image file
- `description` (required): Description to compare against

## Integration Examples

### Python
```python
from open_webui.plugins import comfyui_agent

# Generate image
result = comfyui_agent.generate_image(
    description="A beautiful sunset",
    max_attempts=5
)

# Analyze image
analysis = comfyui_agent.analyze_image(
    image_path=result["image_path"],
    description="A beautiful sunset"
)
```

### API
```bash
curl -X POST "http://localhost:8080/api/plugins/comfyui-agent/generate_image" \
     -H "Content-Type: application/json" \
     -d '{"description": "A beautiful sunset"}'
```

## Troubleshooting

1. **ComfyUI Connection**
   - Ensure ComfyUI is running on port 8188
   - Check ComfyUI logs for errors

2. **GPU Issues**
   - Verify CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
   - Check GPU memory usage

3. **Image Generation**
   - If generation fails, try:
     - Reducing image size
     - Simplifying the description
     - Checking ComfyUI model availability

## Support

- GitHub Issues: [Report Issues](https://github.com/yourusername/comfyui-agent/issues)
- Documentation: See [ARCHITECTURE.md](../ARCHITECTURE.md) for technical details