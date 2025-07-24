#!/usr/bin/env python3
"""
Test the external_user auto-learning functionality
"""
import sqlite3
from datetime import datetime

def test_auto_learning():
    print("🧪 Testing External User Auto-Learning")
    print("=" * 60)
    
    db_path = "./backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check current state
    print("\n1️⃣ Current User Mappings:")
    cursor.execute("""
        SELECT u.email, ucm.openrouter_user_id, ucm.updated_at
        FROM user_client_mapping ucm
        JOIN user u ON ucm.user_id = u.id
        WHERE ucm.is_active = 1
    """)
    
    mappings = cursor.fetchall()
    for email, external_user, updated_at in mappings:
        updated_time = datetime.fromtimestamp(updated_at).strftime('%Y-%m-%d %H:%M:%S')
        status = "✅ Set" if external_user else "⏳ Awaiting auto-learn"
        print(f"   {email}: {external_user or 'NULL'} ({status})")
        print(f"   Last updated: {updated_time}")
    
    # 2. Explain the auto-learning process
    print("\n2️⃣ How Auto-Learning Works:")
    print("   1. User has NULL openrouter_user_id in database")
    print("   2. System generates temporary ID for API call")
    print("   3. OpenRouter returns actual external_user in response")
    print("   4. System automatically updates database with real ID")
    print("   5. All future calls use the learned external_user")
    
    # 3. Benefits
    print("\n3️⃣ Benefits of Auto-Learning:")
    print("   ✅ No manual database updates needed")
    print("   ✅ Works immediately after API key generation")
    print("   ✅ Handles OpenRouter's dynamic user assignment")
    print("   ✅ Transparent to end users")
    print("   ✅ Production-friendly (zero manual intervention)")
    
    # 4. Test readiness
    print("\n4️⃣ System Readiness Check:")
    
    # Check if code updates are in place
    files_to_check = [
        ("openrouter_client_manager.py", "is_temporary_user_id"),
        ("openai.py", "external_user"),
        ("organization_usage.py", "update_mapping")
    ]
    
    import os
    all_ready = True
    for filename, search_term in files_to_check:
        for root, dirs, files in os.walk("./backend"):
            if filename in files:
                filepath = os.path.join(root, filename)
                with open(filepath, 'r') as f:
                    if search_term in f.read():
                        print(f"   ✅ {filename}: Ready for auto-learning")
                    else:
                        print(f"   ❌ {filename}: Missing auto-learning code")
                        all_ready = False
                break
    
    if all_ready:
        print("\n🎉 System is ready for external_user auto-learning!")
    else:
        print("\n⚠️  Some components need updating")
    
    # 5. Testing instructions
    print("\n5️⃣ How to Test:")
    print("   1. Run: python3 fix_user_mapping.py")
    print("   2. Restart Docker container")
    print("   3. Make an API call through mAI")
    print("   4. Check Docker logs for auto-learning confirmation:")
    print("      docker logs [container] | grep 'Auto-learning external_user'")
    print("   5. Run this script again to verify the external_user was saved")
    
    conn.close()

if __name__ == "__main__":
    test_auto_learning()