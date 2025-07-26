#!/usr/bin/env python3
"""
Test the automatic database initialization
"""

import os
import time

def test_automatic_initialization():
    """Test that the container automatically initializes the database"""
    print("🧪 Testing Automatic Database Initialization")
    print("=" * 60)
    
    # Step 1: Verify environment variables are set
    print("\n1️⃣ Checking environment variables...")
    env_file_exists = os.path.exists('.env')
    print(f"   .env file exists: {'✅' if env_file_exists else '❌'}")
    
    if env_file_exists:
        # Read key values from .env
        with open('.env', 'r') as f:
            env_content = f.read()
        
        has_org_name = 'ORGANIZATION_NAME=' in env_content
        has_external_user = 'OPENROUTER_EXTERNAL_USER=' in env_content
        has_api_key = 'OPENROUTER_API_KEY=' in env_content
        
        print(f"   ORGANIZATION_NAME present: {'✅' if has_org_name else '❌'}")
        print(f"   OPENROUTER_EXTERNAL_USER present: {'✅' if has_external_user else '❌'}")
        print(f"   OPENROUTER_API_KEY present: {'✅' if has_api_key else '❌'}")
    
    # Step 2: Instructions for Docker restart
    print("\n2️⃣ Docker Container Restart Required:")
    print("   Run these commands to test automatic initialization:")
    print()
    print("   # Stop the container")
    print("   docker-compose -f docker-compose-customization.yaml down")
    print()
    print("   # Optional: Clean the database volume to test fresh initialization")
    print("   # docker volume rm mai_customization_data")
    print()
    print("   # Start the container (will trigger automatic initialization)")
    print("   docker-compose -f docker-compose-customization.yaml up -d")
    print()
    print("   # Wait for container to fully start")
    print("   sleep 15")
    print()
    print("   # Check the logs for initialization")
    print("   docker logs open-webui-customization 2>&1 | grep -E '(Usage tracking|Client organization)'")
    print()
    
    # Step 3: Verification commands
    print("3️⃣ Verification Commands:")
    print("   After restart, run these to verify initialization:")
    print()
    print("   # Check if client organization was created")
    print("   docker exec open-webui-customization python3 -c \"")
    print("   import sqlite3")
    print("   conn = sqlite3.connect('/app/backend/data/webui.db')")
    print("   cursor = conn.cursor()")
    print("   cursor.execute('SELECT id, name, is_active FROM client_organizations')")
    print("   orgs = cursor.fetchall()")
    print("   print('Client organizations:', len(orgs))")
    print("   for org in orgs:")
    print("       print(f'  - {org[0]} | {org[1]} | Active: {org[2]}')")
    print("   conn.close()\"")
    print()
    
    # Step 4: Expected results
    print("4️⃣ Expected Results:")
    print("   ✅ Log message: '✅ Usage tracking initialized for Company_A'")
    print("   ✅ Database contains: mai_client_63a4eb6d | Company_A | Active: 1")
    print("   ✅ Usage Settings tabs should show data after browser refresh")
    print()
    
    print("🎯 IMPORTANT: The automatic initialization runs on container startup!")
    print("   You must restart the Docker container to test this feature.")

if __name__ == "__main__":
    test_automatic_initialization()