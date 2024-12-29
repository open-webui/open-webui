"""
ComfyUI Agent Plugin for Open WebUI
"""

from .comfyui_agent import plugin, generate_image, analyze_image

__version__ = "1.0.0"
__all__ = ["plugin", "generate_image", "analyze_image"]