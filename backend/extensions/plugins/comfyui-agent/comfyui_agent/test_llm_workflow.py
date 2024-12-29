#!/usr/bin/env python3
"""
Test script to simulate LLM interactions with the ComfyUI Agent Plugin.
This helps users verify that their LLM can properly use the plugin functions.
"""

import json
from typing import Dict, Any
import argparse
from pathlib import Path

class LLMSimulator:
    def __init__(self):
        self.conversation_history = []
        self.available_functions = {
            "generate_image": self.generate_image,
            "analyze_image": self.analyze_image
        }

    def add_message(self, role: str, content: str, function_call: Dict[str, Any] = None):
        """Add a message to the conversation history"""
        message = {
            "role": role,
            "content": content
        }
        if function_call:
            message["function_call"] = function_call
        self.conversation_history.append(message)

    def generate_image(self, description: str, **kwargs):
        """Simulate generate_image function call"""
        try:
            from . import generate_image
            return generate_image(description=description, **kwargs)
        except ImportError:
            return {
                "success": False,
                "message": "Plugin not properly installed"
            }

    def analyze_image(self, image_path: str, description: str):
        """Simulate analyze_image function call"""
        try:
            from . import analyze_image
            return analyze_image(image_path=image_path, description=description)
        except ImportError:
            return {
                "success": False,
                "message": "Plugin not properly installed"
            }

    def simulate_conversation(self, save_path: str = None):
        """Simulate a conversation with function calls"""
        
        # Example conversation 1: Basic image generation
        self.add_message("user", 
                        "Generate an image of a beautiful sunset over mountains.")
        
        self.add_message("assistant",
                        "I'll help you generate an image of a beautiful sunset over mountains using ComfyUI.",
                        {
                            "name": "generate_image",
                            "parameters": {
                                "description": "A beautiful sunset over mountains with warm golden light, "
                                             "majestic peaks, and a peaceful atmosphere",
                                "max_attempts": 3
                            }
                        })
        
        # Execute function call
        result = self.generate_image(**self.conversation_history[-1]["function_call"]["parameters"])
        
        if result["success"]:
            self.add_message("assistant",
                           f"I've generated the image successfully! The image has been saved to: {result['image_path']}\n"
                           f"The generation process took {len(result['metadata']['generation_history'])} attempts to achieve "
                           f"a quality score of {result['metadata']['scores']['overall']:.2f}.")
            
            # Example conversation 2: Image analysis
            self.add_message("user",
                           "How well does this image match my description?")
            
            self.add_message("assistant",
                           "I'll analyze the image using CLIP to see how well it matches your description.",
                           {
                               "name": "analyze_image",
                               "parameters": {
                                   "image_path": result["image_path"],
                                   "description": "A beautiful sunset over mountains"
                               }
                           })
            
            # Execute analysis
            analysis = self.analyze_image(**self.conversation_history[-1]["function_call"]["parameters"])
            
            if analysis["success"]:
                self.add_message("assistant",
                               f"The image matches your description with a similarity score of {analysis['score']:.2f}.\n\n"
                               f"Detailed feedback:\n" + 
                               "\n".join(f"- {aspect}: {data['score']:.2f} - {data['suggestion']}"
                                       for aspect, data in analysis['feedback']['aspects'].items()))
        
        # Save conversation history
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(self.conversation_history, f, indent=2)
            print(f"\nConversation history saved to: {save_path}")
        
        return self.conversation_history

def main():
    parser = argparse.ArgumentParser(description='Test LLM interactions with ComfyUI Agent Plugin')
    parser.add_argument('--save', type=str, help='Path to save conversation history')
    args = parser.parse_args()
    
    print("Testing LLM interactions with ComfyUI Agent Plugin...")
    print("=" * 60)
    
    simulator = LLMSimulator()
    conversation = simulator.simulate_conversation(args.save)
    
    print("\nSimulated Conversation:")
    print("-" * 40)
    
    for message in conversation:
        print(f"\n{message['role'].upper()}: {message['content']}")
        if 'function_call' in message:
            print("\nFunction Call:")
            print(json.dumps(message['function_call'], indent=2))
    
    print("\nTest completed!")
    print("If all function calls succeeded, the plugin is working correctly with LLM interactions.")

if __name__ == "__main__":
    main()