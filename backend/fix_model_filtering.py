#!/usr/bin/env python3
"""
Fix model filtering to use organization-based access control.
This patch updates the get_filtered_models functions to respect organization model access.
"""

import os
import sys

def create_patch():
    """Create the patch for model filtering"""
    
    # Patch for main.py
    main_py_patch = '''
    def get_filtered_models(models, user):
        """Filter models based on user's organization access"""
        # If user is admin, return all models
        if user.role == "admin":
            return models
            
        # Get models accessible through organizations
        from open_webui.models.models import Models
        org_accessible_models = Models.get_models_by_user_id(user.id)
        org_model_ids = {m.id for m in org_accessible_models}
        
        filtered_models = []
        for model in models:
            model_id = model.get("id", "")
            
            # Check if model is in user's organization models
            if model_id in org_model_ids:
                filtered_models.append(model)
                continue
                
            # Legacy check for arena models
            if model.get("arena"):
                if has_access(
                    user.id,
                    type="read",
                    access_control=model.get("info", {})
                    .get("meta", {})
                    .get("access_control", {}),
                ):
                    filtered_models.append(model)
                continue
            
            # Legacy check for individual model access
            model_info = Models.get_model_by_id(model_id)
            if model_info:
                if user.id == model_info.user_id or has_access(
                    user.id, type="read", access_control=model_info.access_control
                ):
                    filtered_models.append(model)
        
        return filtered_models
'''

    # Patch for openai.py router
    openai_py_patch = '''
async def get_filtered_models(models, user):
    """Filter models based on user's organization access"""
    # If user is admin, return all models
    if user.role == "admin":
        return models.get("data", [])
        
    # Get models accessible through organizations
    from open_webui.models.models import Models
    org_accessible_models = Models.get_models_by_user_id(user.id)
    org_model_ids = {m.id for m in org_accessible_models}
    
    filtered_models = []
    for model in models.get("data", []):
        model_id = model.get("id", "")
        
        # Check if model is in user's organization models
        if model_id in org_model_ids:
            filtered_models.append(model)
            continue
            
        # Legacy check for individual model access
        model_info = Models.get_model_by_id(model_id)
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    
    return filtered_models
'''

    # Patch for ollama.py router  
    ollama_py_patch = '''
async def get_filtered_models(models, user):
    """Filter models based on user's organization access"""
    # If user is admin, return all models
    if user.role == "admin":
        return models
        
    # Get models accessible through organizations
    from open_webui.models.models import Models
    org_accessible_models = Models.get_models_by_user_id(user.id)
    org_model_ids = {m.id for m in org_accessible_models}
    
    if "models" in models:
        # Ollama format
        filtered_list = []
        for model in models.get("models", []):
            model_name = model.get("model", model.get("name", ""))
            if model_name in org_model_ids:
                filtered_list.append(model)
                continue
                
            # Legacy check
            model_info = Models.get_model_by_id(model_name)
            if model_info:
                if user.id == model_info.user_id or has_access(
                    user.id, type="read", access_control=model_info.access_control
                ):
                    filtered_list.append(model)
        
        models["models"] = filtered_list
        return models
    else:
        # OpenAI format
        return {"data": [m for m in models.get("data", []) if m.get("id") in org_model_ids]}
'''

    return {
        "main.py": main_py_patch,
        "openai.py": openai_py_patch,
        "ollama.py": ollama_py_patch
    }

if __name__ == "__main__":
    print("Model Filtering Fix")
    print("=" * 50)
    print("\nThis script contains the patches needed to fix model filtering.")
    print("\nThe issue: Users see all OpenRouter models instead of just their organization's models.")
    print("\nThe fix: Update get_filtered_models functions to use organization-based access control.")
    print("\nFiles to patch:")
    print("1. backend/open_webui/main.py")
    print("2. backend/open_webui/routers/openai.py") 
    print("3. backend/open_webui/routers/ollama.py")
    
    patches = create_patch()
    
    print("\n" + "="*50)
    print("IMPORTANT: Apply these patches manually to the respective files.")
    print("Look for the 'def get_filtered_models' function in each file and replace it.")