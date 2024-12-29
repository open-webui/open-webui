import os
import sys
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path to import our agent modules
sys.path.append(str(Path(__file__).parent.parent.parent))
from image_generation_agent import ComfyUIAgent
from clip_scorer import CLIPScorer

class ComfyUIAgentPlugin:
    def __init__(self):
        self.agent = None
        self.clip_scorer = None
        self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)

    def _ensure_initialized(self):
        """Ensure agent and CLIP scorer are initialized"""
        if self.agent is None:
            self.agent = ComfyUIAgent()
        if self.clip_scorer is None:
            self.clip_scorer = CLIPScorer()

    def _save_image_metadata(self, image_path: str, metadata: Dict[str, Any]):
        """Save generation metadata"""
        metadata_path = Path(image_path).with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image as base64 for web display"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def generate_image(self, 
                      description: str,
                      max_attempts: int = 5,
                      cfg_scale: float = 7.0,
                      steps: int = 20,
                      width: int = 512,
                      height: int = 512) -> Dict[str, Any]:
        """
        Generate an image using ComfyUI with CLIP-guided refinement.
        
        Args:
            description: Text description of the desired image
            max_attempts: Maximum number of generation attempts
            cfg_scale: Initial CFG scale
            steps: Initial number of steps
            width: Image width
            height: Image height
            
        Returns:
            Dict containing:
            - success: Boolean indicating success
            - image_path: Path to generated image
            - image_base64: Base64 encoded image for display
            - metadata: Generation metadata and history
            - message: Status or error message
        """
        try:
            self._ensure_initialized()
            
            # Generate timestamp for unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = str(self.output_dir / f"generated_{timestamp}.png")
            
            # Set up generation parameters
            params = {
                "prompt": description,
                "negative_prompt": "ugly, blurry, low quality, distorted, disfigured, bad anatomy, watermark",
                "seed": None,  # Let agent choose random seed
                "steps": steps,
                "cfg": cfg_scale,
                "width": width,
                "height": height
            }
            
            # Generate image
            image, metadata = self.agent.generate_matching_image(
                description=description,
                max_attempts=max_attempts,
                **params
            )
            
            # Save image and metadata
            image.save(image_path)
            self._save_image_metadata(image_path, metadata)
            
            return {
                "success": True,
                "image_path": image_path,
                "image_base64": self._encode_image_base64(image_path),
                "metadata": metadata,
                "message": "Image generated successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error generating image: {str(e)}",
                "metadata": {"error": str(e)}
            }

    def analyze_image(self, 
                     image_path: str, 
                     description: str) -> Dict[str, Any]:
        """
        Analyze how well an image matches a description using CLIP.
        
        Args:
            image_path: Path to the image file
            description: Description to compare against
            
        Returns:
            Dict containing:
            - success: Boolean indicating success
            - score: Overall similarity score
            - feedback: Detailed feedback for each aspect
            - message: Status or error message
        """
        try:
            self._ensure_initialized()
            
            # Load image
            from PIL import Image
            image = Image.open(image_path)
            
            # Get CLIP analysis
            score, feedback = self.clip_scorer.analyze_image_similarity(image, description)
            
            return {
                "success": True,
                "score": score,
                "feedback": feedback,
                "message": "Analysis completed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error analyzing image: {str(e)}",
                "metadata": {"error": str(e)}
            }

# Create plugin instance
plugin = ComfyUIAgentPlugin()

# Export functions for Open WebUI
generate_image = plugin.generate_image
analyze_image = plugin.analyze_image