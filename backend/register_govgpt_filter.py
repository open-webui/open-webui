#!/usr/bin/env python3
"""
Script to register the govGpt-file-search-service filter function
"""

import sys
import os
import time
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from open_webui.models.functions import Functions, FunctionForm
from open_webui.utils.auth import get_admin_user
from open_webui.env import SRC_LOG_LEVELS
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

def register_govgpt_filter():
    """
    Register the govGpt-file-search-service filter function
    """
    
    # Read the filter function content
    filter_file = backend_dir / "open_webui" / "functions" / "custom_qa_filter.py"
    
    if not filter_file.exists():
        print(f"❌ Filter file not found: {filter_file}")
        return False
    
    with open(filter_file, 'r') as f:
        filter_content = f.read()
    
    # Create the function form
    function_form = FunctionForm(
        id="govgpt_file_search_filter",
        name="GovGPT File Search Filter",
        type="filter",
        content=filter_content,
        meta={
            "description": "Integrates govGpt-file-search-service for document-based queries",
            "version": "1.0.0",
            "author": "Open WebUI",
            "manifest": {
                "name": "GovGPT File Search Filter",
                "description": "Integrates govGpt-file-search-service for document-based queries",
                "version": "1.0.0",
                "author": "Open WebUI",
                "type": "filter"
            }
        },
        valves={
            "priority": 100,
            "enabled": True
        },
        is_active=True,
        is_global=True
    )
    
    # Check if function already exists
    existing_function = Functions.get_function_by_id("govgpt_file_search_filter")
    
    if existing_function:
        print("🔄 Updating existing govGpt-file-search-service filter...")
        try:
            # Update the existing function
            Functions.update_function_by_id("govgpt_file_search_filter", {
                "name": function_form.name,
                "content": function_form.content,
                "meta": function_form.meta,
                "valves": function_form.valves,
                "is_active": function_form.is_active,
                "is_global": function_form.is_global,
                "updated_at": int(time.time())
            })
            print("✅ GovGPT File Search Filter updated successfully!")
            return True
        except Exception as e:
            print(f"❌ Error updating filter: {e}")
            return False
    else:
        print("🆕 Creating new govGpt-file-search-service filter...")
        try:
            # Create a dummy admin user for the function creation
            class DummyAdminUser:
                def __init__(self):
                    self.id = "admin"
                    self.email = "admin@example.com"
                    self.name = "Admin"
                    self.role = "admin"
            
            # Insert the new function
            function = Functions.insert_new_function(
                user_id="admin",
                type="filter",
                form_data=function_form
            )
            
            if function:
                print("✅ GovGPT File Search Filter created successfully!")
                return True
            else:
                print("❌ Failed to create filter")
                return False
        except Exception as e:
            print(f"❌ Error creating filter: {e}")
            return False

def check_filter_status():
    """
    Check if the filter is properly registered
    """
    function = Functions.get_function_by_id("govgpt_file_search_filter")
    
    if function:
        print(f"✅ Filter found:")
        print(f"   ID: {function.id}")
        print(f"   Name: {function.name}")
        print(f"   Type: {function.type}")
        print(f"   Active: {function.is_active}")
        print(f"   Global: {function.is_global}")
        print(f"   Updated: {function.updated_at}")
        return True
    else:
        print("❌ Filter not found in database")
        return False

def main():
    """
    Main function to register the filter
    """
    print("🔧 GovGPT File Search Service Filter Registration")
    print("=" * 50)
    
    # Register the filter
    if register_govgpt_filter():
        print("\n📋 Checking filter status...")
        check_filter_status()
        
        print("\n🎉 Setup complete!")
        print("\nNext steps:")
        print("1. Make sure ENABLE_GOVGPT_FILE_SEARCH=true in your .env file")
        print("2. Restart the Open WebUI backend")
        print("3. Test with a file upload and question")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 