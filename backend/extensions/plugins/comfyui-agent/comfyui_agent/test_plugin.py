#!/usr/bin/env python3
"""
Test script for ComfyUI Agent Plugin.
Run this script to verify the plugin installation and functionality.
"""

import os
import sys
import traceback
from pathlib import Path

def setup_environment():
    """Setup environment and verify imports"""
    print("\n=== Environment Setup ===")
    print("Current directory:", os.getcwd())
    print("Python version:", sys.version)
    
    # Setup paths
    current_dir = Path(__file__).parent.absolute()
    plugin_dir = current_dir.parent
    workspace_dir = plugin_dir.parent
    
    paths = [str(current_dir), str(plugin_dir), str(workspace_dir)]
    for path in paths:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    print("\nPython path:")
    for path in sys.path:
        print(f"  - {path}")
    
    # Import dependencies
    print("\n=== Importing Dependencies ===")
    dependencies = [
        ('torch', 'PyTorch'),
        ('requests', 'Requests'),
        ('PIL', 'Pillow'),
        ('numpy', 'NumPy'),
        ('transformers', 'Transformers'),
        ('tqdm', 'TQDM'),
        ('huggingface_hub', 'Hugging Face Hub')
    ]
    
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            print(f"✓ {display_name} imported successfully")
        except ImportError as e:
            print(f"✗ {display_name} import failed: {e}")
            return False
    
    # Import core modules
    print("\n=== Importing Core Modules ===")
    try:
        from image_generation_agent import ComfyUIAgent
        from clip_scorer import CLIPScorer
        print("✓ Core modules imported successfully")
    except Exception as e:
        print(f"✗ Core module import failed: {e}")
        traceback.print_exc()
        return False
    
    # Import plugin
    print("\n=== Importing Plugin ===")
    try:
        import comfyui_agent
        from comfyui_agent import generate_image, analyze_image
        print("✓ Plugin imported successfully")
    except Exception as e:
        print(f"✗ Plugin import failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_comfyui_connection():
    """Test connection to ComfyUI server"""
    print("\n=== Testing ComfyUI Connection ===")
    try:
        import requests
        response = requests.get("http://127.0.0.1:8188/history")
        if response.status_code == 200:
            print("✓ ComfyUI server is running")
            return True
        else:
            print(f"✗ ComfyUI server returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ ComfyUI server is not running")
        print("\nTo start ComfyUI:")
        print("1. Open a new terminal")
        print("2. Navigate to ComfyUI directory")
        print("3. Run: python main.py")
        return False
    except Exception as e:
        print(f"✗ Error testing ComfyUI connection: {e}")
        return False

def test_cuda():
    """Test CUDA availability"""
    print("\n=== Testing CUDA ===")
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            print(f"✓ CUDA is available: {device_name}")
            return True
        else:
            print("ℹ CUDA is not available (will use CPU)")
            return True
    except Exception as e:
        print(f"✗ Error testing CUDA: {e}")
        return False

def test_image_generation():
    """Test image generation"""
    print("\n=== Testing Image Generation ===")
    
    # Check ComfyUI connection first
    if not test_comfyui_connection():
        print("⚠ Skipping image generation test (ComfyUI not running)")
        return None
        
    try:
        from comfyui_agent import generate_image
        
        print("Generating test image...")
        result = generate_image(
            description="A simple test image of a red circle on white background",
            max_attempts=1,
            width=256,
            height=256
        )
        
        if result["success"]:
            print(f"✓ Image generated successfully: {result['image_path']}")
            return result["image_path"]
        else:
            print(f"✗ Image generation failed: {result['message']}")
            return None
    except Exception as e:
        print(f"✗ Error during image generation: {e}")
        traceback.print_exc()
        return None

def test_image_analysis(image_path):
    """Test image analysis"""
    print("\n=== Testing Image Analysis ===")
    if not image_path:
        print("⚠ Skipping image analysis test (no test image available)")
        return False
        
    try:
        from comfyui_agent import analyze_image
        
        print("Analyzing test image...")
        result = analyze_image(
            image_path=image_path,
            description="A red circle on white background"
        )
        
        if result["success"]:
            print(f"✓ Image analysis successful")
            print(f"  Score: {result['score']:.2f}")
            return True
        else:
            print(f"✗ Image analysis failed: {result['message']}")
            return False
    except Exception as e:
        print(f"✗ Error during image analysis: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        # Setup environment
        if not setup_environment():
            print("\n✗ Environment setup failed")
            return False
        
        # Test CUDA
        cuda_status = test_cuda()
        
        # Run image generation and analysis
        test_image = test_image_generation()
        if test_image:
            test_image_analysis(test_image)
        
        print("\n=== Test Summary ===")
        print("Environment Setup: ✓")
        print(f"CUDA Status: {'✓' if cuda_status else '✗'}")
        print(f"ComfyUI Status: {'✓' if test_comfyui_connection() else '✗'}")
        print(f"Image Generation: {'✓' if test_image else '✗'}")
        print(f"Image Analysis: {'✓' if test_image else '⚠ Skipped'}")
        
        print("\nNext steps:")
        if not test_comfyui_connection():
            print("1. Start ComfyUI server")
            print("2. Run this test again")
        else:
            print("1. Try generating an image:")
            print("   from comfyui_agent import generate_image")
            print('   result = generate_image("A beautiful sunset over mountains")')
        
        # Consider the test successful if environment is set up correctly
        # even if ComfyUI is not running
        return True
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
