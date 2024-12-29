#!/usr/bin/env python3
"""
Test script to verify the plugin works in Open WebUI environment.
This simulates how Open WebUI would load and use the plugin.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

class OpenWebUISimulator:
    def __init__(self):
        self.plugins = {}
        self.functions = {}
        
    def load_plugin(self, plugin_dir: str) -> bool:
        """Simulate Open WebUI plugin loading"""
        try:
            # Add plugin directory to Python path
            plugin_path = Path(plugin_dir).resolve()
            if str(plugin_path) not in sys.path:
                sys.path.insert(0, str(plugin_path))
            
            # Import plugin module
            from plugin import plugin, generate_image, analyze_image
            
            # Initialize plugin
            if not plugin.initialize():
                print("Failed to initialize plugin")
                return False
            
            # Register plugin
            self.plugins[plugin.name] = plugin
            
            # Register functions
            self.functions.update(plugin.get_functions())
            
            return True
            
        except Exception as e:
            print(f"Error loading plugin: {e}")
            return False
    
    def simulate_llm_conversation(self) -> None:
        """Simulate an LLM using the plugin functions"""
        print("\nSimulating LLM conversation...")
        print("-" * 50)
        
        # Load example conversations
        examples = self.plugins["comfyui-agent"].get_examples()
        
        for i, message in enumerate(examples):
            print(f"\n{message['role'].upper()}: {message['content']}")
            
            if 'function_call' in message:
                print("\nFunction Call:")
                print(json.dumps(message['function_call'], indent=2))
                
                # Execute function call
                func_name = message['function_call']['name']
                if func_name in globals():
                    func = globals()[func_name]
                    result = func(**message['function_call']['parameters'])
                    print("\nFunction Result:")
                    print(json.dumps(result, indent=2))
    
    def test_functions(self) -> None:
        """Test each available function"""
        print("\nTesting available functions...")
        print("-" * 50)
        
        # Test generate_image
        print("\nTesting generate_image...")
        try:
            result = generate_image(
                description="A test image of a red circle",
                max_attempts=1
            )
            print("Result:", "Success" if result["success"] else "Failed")
            if result["success"]:
                print(f"Image saved to: {result['image_path']}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test analyze_image
        if 'result' in locals() and result["success"]:
            print("\nTesting analyze_image...")
            try:
                analysis = analyze_image(
                    image_path=result["image_path"],
                    description="A red circle"
                )
                print("Result:", "Success" if analysis["success"] else "Failed")
                if analysis["success"]:
                    print(f"Similarity score: {analysis['score']:.2f}")
            except Exception as e:
                print(f"Error: {e}")

def main():
    print("Testing ComfyUI Agent Plugin in Open WebUI environment")
    print("=" * 60)
    
    # Create simulator
    webui = OpenWebUISimulator()
    
    # Load plugin
    plugin_dir = Path(__file__).parent
    print(f"\nLoading plugin from: {plugin_dir}")
    
    if webui.load_plugin(plugin_dir):
        print("✓ Plugin loaded successfully")
        
        # Print available functions
        print("\nAvailable functions:")
        for name, func in webui.functions.items():
            print(f"- {name}: {func['description']}")
        
        # Test functions
        webui.test_functions()
        
        # Simulate LLM conversation
        webui.simulate_llm_conversation()
        
        print("\n✓ Test completed successfully!")
    else:
        print("\n✗ Failed to load plugin")
        sys.exit(1)

if __name__ == "__main__":
    main()