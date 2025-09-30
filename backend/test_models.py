#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.utils.models import get_all_models
from open_webui.main import app
from fastapi import Request
from open_webui.models.users import UserModel

async def test_models():
    # Create a mock request with proper app state
    scope = {
        'type': 'http', 
        'method': 'GET', 
        'path': '/test',
        'app': app
    }
    request = Request(scope)
    
    try:
        # Get all models
        models = await get_all_models(request)
        
        print("All available model IDs:")
        for model in models:
            print(f"  {model.get('id', '<no id>')}")
        
        print(f"\nTotal models found: {len(models)}")
        
        # Also check the app state MODELS
        if hasattr(request.app.state, 'MODELS'):
            print(f"\nModels in app state: {len(request.app.state.MODELS)}")
            for model_id in request.app.state.MODELS.keys():
                print(f"  {model_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_models()) 