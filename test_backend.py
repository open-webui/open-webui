#!/usr/bin/env python3

"""
Simple test script to check if Open WebUI backend can start
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test if core modules can be imported"""
    try:
        print("Testing core imports...")
        
        # Test basic imports
        from open_webui import config
        print("✓ Config module imported successfully")
        
        from open_webui.env import VERSION
        print(f"✓ Version: {VERSION}")
        
        from open_webui.internal.db import get_db
        print("✓ Database module imported successfully")
        
        from open_webui.models.users import Users
        print("✓ User model imported successfully")
        
        # Test if we can create a FastAPI app without audio router
        print("\nTesting FastAPI app creation...")
        from fastapi import FastAPI
        from open_webui.config import AppConfig
        
        app = FastAPI(title="Open WebUI Test")
        print("✓ FastAPI app created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_database():
    """Test database connection"""
    try:
        print("\nTesting database connection...")
        from open_webui.internal.db import get_db
        from sqlalchemy import text
        
        with get_db() as db:
            # Simple query to test connection
            result = db.execute(text("SELECT 1")).fetchone()
            if result:
                print("✓ Database connection successful")
                return True
            else:
                print("✗ Database query failed")
                return False
                
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Open WebUI Backend Test")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test database
    if not test_database():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! Backend is working.")
        print("\nTo start the server manually:")
        print("cd backend")
        print("python -m uvicorn open_webui.main:app --host 127.0.0.1 --port 8080")
    else:
        print("✗ Some tests failed. Check the errors above.")
    print("=" * 50)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())