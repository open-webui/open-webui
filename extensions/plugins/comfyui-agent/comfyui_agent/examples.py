#!/usr/bin/env python3
"""
Example usage of ComfyUI Agent Plugin in Open WebUI conversations.
This script demonstrates how LLMs can use the plugin for image generation and analysis.
"""

import json
from typing import Dict, Any
from . import generate_image, analyze_image

def format_llm_response(result: Dict[str, Any]) -> str:
    """Format plugin results for LLM response"""
    if not result["success"]:
        return f"Error: {result['message']}"
    
    if "image_base64" in result:
        return (
            f"Image generated successfully!\n\n"
            f"Generation details:\n"
            f"- Overall quality score: {result['metadata']['scores']['overall']:.2f}\n"
            f"- Attempts made: {len(result['metadata']['generation_history'])}\n"
            f"- Final parameters: {json.dumps(result['metadata']['parameters'], indent=2)}\n\n"
            f"The image has been saved to: {result['image_path']}"
        )
    else:
        return (
            f"Image analysis results:\n"
            f"- Overall similarity score: {result['score']:.2f}\n"
            f"Detailed feedback:\n"
            + "\n".join(f"- {aspect}: {data['score']:.2f} - {data['suggestion']}"
                       for aspect, data in result['feedback']['aspects'].items())
        )

def example_conversation():
    """Example conversation demonstrating plugin usage"""
    
    # Example 1: Basic image generation
    print("User: Generate an image of a cute cat playing with a ball of yarn.")
    
    generation_result = generate_image(
        description="A cute cat playing with a ball of yarn, "
                   "playful expression, soft lighting, warm colors",
        max_attempts=3
    )
    
    print("\nAssistant: " + format_llm_response(generation_result))
    
    # Example 2: Image analysis
    print("\nUser: How well does this image match my description?")
    
    analysis_result = analyze_image(
        image_path=generation_result["image_path"],
        description="A cute cat playing with a ball of yarn"
    )
    
    print("\nAssistant: " + format_llm_response(analysis_result))
    
    # Example 3: Advanced image generation with specific parameters
    print("\nUser: Generate a high-quality landscape image, take your time to make it perfect.")
    
    detailed_result = generate_image(
        description="A breathtaking mountain landscape at sunset, "
                   "with a crystal-clear lake reflecting the golden sky, "
                   "surrounded by pine trees and snow-capped peaks",
        max_attempts=5,
        cfg_scale=8.0,
        steps=30,
        width=768,
        height=512
    )
    
    print("\nAssistant: " + format_llm_response(detailed_result))

def example_function_calls():
    """Example of how LLMs should format function calls"""
    
    examples = {
        "basic_generation": {
            "function": "generate_image",
            "parameters": {
                "description": "A beautiful sunset over mountains"
            }
        },
        
        "advanced_generation": {
            "function": "generate_image",
            "parameters": {
                "description": "A professional portrait photo of a person",
                "max_attempts": 5,
                "cfg_scale": 7.5,
                "steps": 30,
                "width": 512,
                "height": 768
            }
        },
        
        "image_analysis": {
            "function": "analyze_image",
            "parameters": {
                "image_path": "/path/to/image.png",
                "description": "A beautiful sunset over mountains"
            }
        }
    }
    
    print("Example Function Calls:")
    print(json.dumps(examples, indent=2))

def example_error_handling():
    """Example of handling various error cases"""
    
    # Example 1: Invalid image path
    print("\nTrying to analyze non-existent image:")
    result = analyze_image(
        image_path="/nonexistent/image.png",
        description="test"
    )
    print(format_llm_response(result))
    
    # Example 2: Empty description
    print("\nTrying to generate with empty description:")
    result = generate_image(description="")
    print(format_llm_response(result))
    
    # Example 3: Invalid parameters
    print("\nTrying to generate with invalid parameters:")
    result = generate_image(
        description="test",
        width=-100  # Invalid width
    )
    print(format_llm_response(result))

if __name__ == "__main__":
    print("=== ComfyUI Agent Plugin Examples ===\n")
    
    print("1. Example Conversation")
    print("-" * 50)
    example_conversation()
    
    print("\n2. Function Call Examples")
    print("-" * 50)
    example_function_calls()
    
    print("\n3. Error Handling Examples")
    print("-" * 50)
    example_error_handling()