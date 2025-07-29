#!/usr/bin/env python3
"""
Debug script to investigate why user Olaf cannot see any models.
This script checks user permissions, model configurations, and database state.
"""

import sqlite3
import json
from datetime import datetime
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_user_info(db_path="backend/data/webui.db"):
    """Check user Olaf's information and permissions."""
    print("=== Checking User Info ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find user by email
        cursor.execute(
            "SELECT id, name, email, role, created_at FROM user WHERE email = ?",
            ("krokodylek1981@gmail.com",)
        )
        user = cursor.fetchone()
        
        if user:
            print(f"✓ User found:")
            print(f"  ID: {user[0]}")
            print(f"  Name: {user[1]}")
            print(f"  Email: {user[2]}")
            print(f"  Role: {user[3]}")
            print(f"  Created: {user[4]}")
            
            # Check if role is 'pending'
            if user[3] == "pending":
                print("\n⚠️  WARNING: User role is 'pending' - this might restrict access!")
                print("   Users with 'pending' role may not have access to models.")
            
            return user[0], user[3]  # Return user_id and role
        else:
            print("✗ User not found with email: krokodylek1981@gmail.com")
            return None, None
            
        conn.close()
    except Exception as e:
        print(f"✗ Error checking user: {e}")
        return None, None

def check_models_in_db(db_path="backend/data/webui.db"):
    """Check what models exist in the Models table."""
    print("\n=== Checking Models in Database ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count total models
        cursor.execute("SELECT COUNT(*) FROM model")
        total = cursor.fetchone()[0]
        print(f"Total models in database: {total}")
        
        # List all models with their access control
        cursor.execute(
            "SELECT id, name, user_id, access_control, is_active FROM model"
        )
        models = cursor.fetchall()
        
        if models:
            print("\nModels found:")
            for model in models:
                access_control = json.loads(model[3]) if model[3] else None
                print(f"\n  Model ID: {model[0]}")
                print(f"  Name: {model[1]}")
                print(f"  Owner: {model[2]}")
                print(f"  Active: {model[4]}")
                print(f"  Access Control: {access_control}")
        else:
            print("\n⚠️  WARNING: No models found in the database!")
            print("   This explains why users cannot see any models.")
            
        conn.close()
        return total
    except Exception as e:
        print(f"✗ Error checking models: {e}")
        return 0

def check_openai_config(db_path="backend/data/webui.db"):
    """Check OpenAI/OpenRouter configuration."""
    print("\n=== Checking OpenAI/OpenRouter Configuration ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM config ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        if result:
            config_data = json.loads(result[0])
            
            # Check OpenAI configuration
            if 'openai' in config_data:
                openai_config = config_data['openai']
                print("✓ OpenAI configuration found")
                
                # Check API configs
                if 'api_configs' in openai_config:
                    api_configs = openai_config['api_configs']
                    if '0' in api_configs:
                        model_ids = api_configs['0'].get('model_ids', [])
                        print(f"✓ Model filtering configured with {len(model_ids)} models:")
                        for i, model_id in enumerate(model_ids, 1):
                            print(f"    {i}. {model_id}")
                    else:
                        print("✗ No API configuration at index '0'")
                else:
                    print("✗ No API configs found")
                    
                # Check if BYPASS_MODEL_ACCESS_CONTROL is set
                bypass = config_data.get('features', {}).get('bypass_model_access_control', False)
                print(f"\nBYPASS_MODEL_ACCESS_CONTROL: {bypass}")
                if not bypass:
                    print("  ⚠️  Model access control is ENABLED - users need proper permissions")
            else:
                print("✗ No OpenAI configuration found")
                
        conn.close()
    except Exception as e:
        print(f"✗ Error checking config: {e}")

def suggest_solutions(user_role, model_count):
    """Suggest solutions based on findings."""
    print("\n=== Suggested Solutions ===")
    
    if user_role == "pending":
        print("\n1. Update user role from 'pending' to 'user':")
        print("   UPDATE user SET role = 'user' WHERE email = 'krokodylek1981@gmail.com';")
    
    if model_count == 0:
        print("\n2. The main issue: No models are registered in the Models table!")
        print("   OpenRouter models need to be registered for users to access them.")
        print("   Create a script to populate the Models table with OpenRouter models.")
    
    print("\n3. Alternative: Enable BYPASS_MODEL_ACCESS_CONTROL")
    print("   This would allow all users to see all available models without restrictions.")
    
    print("\n4. Register OpenRouter models with public access (access_control = NULL)")
    print("   This makes them available to all users with 'user' role.")

def main():
    """Run all debug checks."""
    print("🔍 Debugging User Model Access Issue")
    print("=" * 50)
    
    # Parse command line arguments
    db_path = "backend/data/webui.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    print(f"Using database: {db_path}")
    
    # Run checks
    user_id, user_role = check_user_info(db_path)
    model_count = check_models_in_db(db_path)
    check_openai_config(db_path)
    
    # Provide solutions
    suggest_solutions(user_role, model_count)
    
    print("\n" + "=" * 50)
    print("Debug complete!")

if __name__ == "__main__":
    main()