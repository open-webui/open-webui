#!/usr/bin/env python3
"""
Test script to verify organization-based model access is working correctly
"""

import sqlite3
import json

def test_user_model_access():
    """Test that users can see models through their organizations"""
    db_path = "/app/backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🧪 Testing Organization-Based Model Access")
    print("=" * 50)
    
    # Test users
    test_users = [
        ("hello@patrykpilat.pl", "Pat"),
        ("krokodylek1981@gmail.com", "Olaf")
    ]
    
    for email, name in test_users:
        print(f"\n📧 Testing user: {name} ({email})")
        
        # Get user ID
        cursor.execute("SELECT id FROM user WHERE email = ?", (email,))
        user_result = cursor.fetchone()
        
        if not user_result:
            print(f"  ❌ User not found!")
            continue
            
        user_id = user_result[0]
        print(f"  ✅ User ID: {user_id}")
        
        # Check organization membership
        cursor.execute("""
            SELECT om.organization_id, co.name
            FROM organization_members om
            JOIN client_organizations co ON om.organization_id = co.id
            WHERE om.user_id = ? AND om.is_active = 1
        """, (user_id,))
        
        orgs = cursor.fetchall()
        if orgs:
            for org_id, org_name in orgs:
                print(f"  ✅ Member of: {org_name}")
                
                # Check models available to organization
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM organization_models
                    WHERE organization_id = ? AND is_active = 1
                """, (org_id,))
                
                model_count = cursor.fetchone()[0]
                print(f"     • Organization has {model_count} models")
        else:
            print(f"  ❌ Not a member of any organization")
        
        # Check what models user should see
        cursor.execute("""
            SELECT COUNT(DISTINCT model_id)
            FROM organization_models om
            JOIN organization_members omem ON om.organization_id = omem.organization_id
            WHERE omem.user_id = ? AND om.is_active = 1 AND omem.is_active = 1
        """, (user_id,))
        
        expected_models = cursor.fetchone()[0]
        print(f"  📊 Should see {expected_models} models through organizations")
        
        # Check actual model table
        cursor.execute("SELECT COUNT(*) FROM model")
        total_models = cursor.fetchone()[0]
        print(f"  📊 Total models in database: {total_models}")
    
    # Show organization-model mappings
    print("\n🔗 Organization-Model Mappings:")
    cursor.execute("""
        SELECT co.name, COUNT(om.model_id) as model_count
        FROM client_organizations co
        LEFT JOIN organization_models om ON co.id = om.organization_id AND om.is_active = 1
        GROUP BY co.id, co.name
    """)
    
    for org_name, count in cursor.fetchall():
        print(f"  • {org_name}: {count} models")
    
    # Show summary view
    print("\n📊 User Available Models View:")
    try:
        cursor.execute("""
            SELECT user_email, COUNT(DISTINCT model_id) as model_count
            FROM user_available_models
            GROUP BY user_email
        """)
        
        for email, count in cursor.fetchall():
            print(f"  • {email}: {count} models")
    except sqlite3.OperationalError:
        print("  ❌ View not created yet")
    
    conn.close()
    
    print("\n✅ Test complete!")
    print("\n💡 If users still can't see models, ensure:")
    print("   1. The backend has been restarted")
    print("   2. Users have logged out and back in")
    print("   3. The BYPASS_MODEL_ACCESS_CONTROL is not set to true")

if __name__ == "__main__":
    test_user_model_access()