#!/usr/bin/env python3
"""
Set up usage tracking for the mAI system to capture OpenRouter queries
"""

import sys
import os
sys.path.append('backend')

import sqlite3
import hashlib
import time
from datetime import datetime, date

def setup_client_organization():
    """Create a client organization with proper mai_client_ prefix"""
    print("🏢 Setting up client organization...")
    
    db_path = "backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create client organization based on the external_user pattern
        client_id = "mai_client_63a4eb6d"
        current_time = int(time.time())
        
        # Check if already exists
        cursor.execute("SELECT id FROM client_organizations WHERE id = ?", (client_id,))
        if cursor.fetchone():
            print(f"   ✅ Client organization already exists: {client_id}")
            conn.close()
            return client_id
        
        # Create new client organization
        cursor.execute("""
            INSERT INTO client_organizations 
            (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id,
            "mAI Default Organization",
            "your_openrouter_api_key_here",  # Placeholder - needs actual key
            1.3,  # 30% markup
            1,    # Active
            current_time,
            current_time
        ))
        
        conn.commit()
        print(f"   ✅ Created client organization: {client_id}")
        
    except Exception as e:
        print(f"   ❌ Error creating client organization: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()
    
    return client_id

def setup_user_mapping(client_id):
    """Create user mapping for the external_user_id"""
    print("👤 Setting up user mapping...")
    
    db_path = "backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Extract user hash from external_user
        external_user = "mai_client_63a4eb6d_user_d0789b57"
        user_hash = "d0789b57"  # Extracted from external_user
        
        # Create a mapping entry
        mapping_id = f"user_{user_hash}_{client_id}"
        current_time = int(time.time())
        
        # Check if already exists
        cursor.execute("SELECT id FROM user_client_mapping WHERE id = ?", (mapping_id,))
        if cursor.fetchone():
            print(f"   ✅ User mapping already exists: {mapping_id}")
            conn.close()
            return mapping_id
        
        cursor.execute("""
            INSERT INTO user_client_mapping 
            (id, user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mapping_id,
            user_hash,  # Internal user ID
            client_id,
            external_user,  # OpenRouter external_user
            1,  # Active
            current_time,
            current_time
        ))
        
        conn.commit()
        print(f"   ✅ Created user mapping: {mapping_id}")
        
    except Exception as e:
        print(f"   ❌ Error creating user mapping: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()
    
    return mapping_id

def simulate_usage_recording(client_id):
    """Simulate recording the recent usage data"""
    print("📊 Simulating usage recording for recent queries...")
    
    # Query data from the user
    queries = [
        {
            "generation_id": "gen-1753473140-nGp5E5fmE4fZRwapci2P",
            "model": "google/gemini-2.5-flash-lite-preview-06-17",
            "external_user": "mai_client_63a4eb6d_user_d0789b57",
            "tokens_prompt": 1544,
            "tokens_completion": 25,
            "raw_cost": 0.0001724,
            "created_at": "2025-07-25T19:52:22.364378+00:00"
        },
        {
            "generation_id": "gen-1753473182-d6QqpxBsaRV6c3A3Pj2U",
            "model": "openai/gpt-4o-mini",
            "external_user": "mai_client_63a4eb6d_user_d0789b57",
            "tokens_prompt": 2590,
            "tokens_completion": 69,
            "raw_cost": 0.0004266,
            "created_at": "2025-07-25T19:53:04.690798+00:00"
        }
    ]
    
    db_path = "backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        today = date.today()
        current_time = int(time.time())
        
        for query in queries:
            print(f"   📝 Recording: {query['model']}")
            
            # 1. Record in processed_generations
            cursor.execute("""
                INSERT OR REPLACE INTO processed_generations 
                (id, client_org_id, generation_date, processed_at, total_cost, total_tokens)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                query['generation_id'],
                client_id,
                today,
                current_time,
                query['raw_cost'],
                query['tokens_prompt'] + query['tokens_completion']
            ))
            
            # 2. Record in client_user_daily_usage
            user_id = "d0789b57"  # From external_user
            markup_cost = query['raw_cost'] * 1.3  # Apply markup
            
            cursor.execute("""
                INSERT OR REPLACE INTO client_user_daily_usage 
                (id, client_org_id, user_id, openrouter_user_id, usage_date, 
                 total_tokens, total_requests, raw_cost, markup_cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{client_id}_{user_id}_{today}",
                client_id,
                user_id,
                query['external_user'],
                today,
                query['tokens_prompt'] + query['tokens_completion'],
                1,  # One request
                query['raw_cost'],
                markup_cost,
                current_time,
                current_time
            ))
            
            # 3. Record in client_model_daily_usage
            provider = query['model'].split('/')[0]
            
            cursor.execute("""
                INSERT OR REPLACE INTO client_model_daily_usage 
                (id, client_org_id, model_name, usage_date, total_tokens, total_requests, 
                 raw_cost, markup_cost, provider, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{client_id}_{query['model'].replace('/', '_')}_{today}",
                client_id,
                query['model'],
                today,
                query['tokens_prompt'] + query['tokens_completion'],
                1,  # One request
                query['raw_cost'],
                markup_cost,
                provider,
                current_time,
                current_time
            ))
        
        conn.commit()
        print(f"   ✅ Recorded {len(queries)} usage entries successfully")
        
    except Exception as e:
        print(f"   ❌ Error recording usage: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

def verify_setup():
    """Verify the setup worked"""
    print("🔍 Verifying setup...")
    
    db_path = "backend/data/webui.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        today = date.today()
        
        # Check client organization
        cursor.execute("SELECT COUNT(*) FROM client_organizations WHERE id LIKE 'mai_client_%'")
        client_count = cursor.fetchone()[0]
        print(f"   • Client organizations: {client_count}")
        
        # Check user mappings
        cursor.execute("SELECT COUNT(*) FROM user_client_mapping")
        mapping_count = cursor.fetchone()[0]
        print(f"   • User mappings: {mapping_count}")
        
        # Check processed generations
        cursor.execute("SELECT COUNT(*) FROM processed_generations")
        gen_count = cursor.fetchone()[0]
        print(f"   • Processed generations: {gen_count}")
        
        # Check today's usage
        cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage WHERE usage_date = ?", (today,))
        user_usage_count = cursor.fetchone()[0]
        print(f"   • Today's user usage records: {user_usage_count}")
        
        cursor.execute("SELECT COUNT(*) FROM client_model_daily_usage WHERE usage_date = ?", (today,))
        model_usage_count = cursor.fetchone()[0]
        print(f"   • Today's model usage records: {model_usage_count}")
        
        # Show total costs
        cursor.execute("""
            SELECT SUM(markup_cost) FROM client_user_daily_usage WHERE usage_date = ?
        """, (today,))
        total_cost = cursor.fetchone()[0] or 0
        print(f"   • Today's total cost: ${total_cost:.6f}")
        
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        return False
    finally:
        conn.close()
    
    return True

def main():
    print("🚀 Setting up mAI Usage Tracking System")
    print("=" * 60)
    
    # Step 1: Create client organization
    client_id = setup_client_organization()
    if not client_id:
        print("❌ Failed to set up client organization")
        return False
    
    # Step 2: Create user mapping
    mapping_id = setup_user_mapping(client_id)
    if not mapping_id:
        print("❌ Failed to set up user mapping")
        return False
    
    # Step 3: Record the recent usage
    if not simulate_usage_recording(client_id):
        print("❌ Failed to record usage data")
        return False
    
    # Step 4: Verify everything works
    if not verify_setup():
        print("❌ Setup verification failed")
        return False
    
    print()
    print("✅ Usage tracking setup completed successfully!")
    print("📊 Your recent queries should now be visible in the Usage Settings.")
    print()
    print("Next steps:")
    print("1. Update the OpenRouter API key in the client organization")
    print("2. Set up automatic sync or webhook for real-time tracking")
    print("3. Check the Usage by User and Usage by Model tabs")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup failed! Check the errors above.")
        sys.exit(1)