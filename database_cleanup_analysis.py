#!/usr/bin/env python3
"""
Database cleanup analysis script for mAI Usage Settings
Verifies client prefix format and identifies non-conforming data
"""

import sys
import os
sys.path.append('backend')

import sqlite3
from typing import List, Dict, Any
from datetime import date

def analyze_database() -> Dict[str, Any]:
    """Analyze the database and identify cleanup targets"""
    
    db_path = "backend/data/webui.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return {"error": "Database not found"}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    analysis = {
        "client_organizations": [],
        "user_daily_usage": [],
        "model_daily_usage": [],
        "processed_generations": [],
        "non_conforming_records": [],
        "summary": {}
    }
    
    try:
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%client%' OR name LIKE '%usage%' OR name LIKE '%generation%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Found usage-related tables: {tables}")
        
        # 1. Analyze Client Organizations
        if 'client_organizations' in tables:
            cursor.execute("SELECT * FROM client_organizations")
            client_orgs = cursor.fetchall()
            
            # Get column names
            cursor.execute("PRAGMA table_info(client_organizations)")
            columns = [row[1] for row in cursor.fetchall()]
            
            for org in client_orgs:
                org_dict = dict(zip(columns, org))
                analysis["client_organizations"].append(org_dict)
                
                # Check if ID follows mai_client_ format
                org_id = org_dict.get('id', '')
                if not org_id.startswith('mai_client_'):
                    analysis["non_conforming_records"].append({
                        "table": "client_organizations",
                        "record_id": org_id,
                        "issue": f"ID doesn't start with 'mai_client_': {org_id}",
                        "record": org_dict
                    })
        
        # 2. Analyze Client User Daily Usage
        if 'client_user_daily_usage' in tables:
            cursor.execute("SELECT DISTINCT client_org_id FROM client_user_daily_usage")
            user_usage_clients = [row[0] for row in cursor.fetchall()]
            
            for client_id in user_usage_clients:
                if not client_id.startswith('mai_client_'):
                    cursor.execute("""
                        SELECT COUNT(*) FROM client_user_daily_usage 
                        WHERE client_org_id = ?
                    """, (client_id,))
                    count = cursor.fetchone()[0]
                    
                    analysis["non_conforming_records"].append({
                        "table": "client_user_daily_usage",
                        "record_id": client_id,
                        "issue": f"client_org_id doesn't start with 'mai_client_': {client_id}",
                        "record_count": count
                    })
            
            analysis["user_daily_usage"] = user_usage_clients
        
        # 3. Analyze Client Model Daily Usage
        if 'client_model_daily_usage' in tables:
            cursor.execute("SELECT DISTINCT client_org_id FROM client_model_daily_usage")
            model_usage_clients = [row[0] for row in cursor.fetchall()]
            
            for client_id in model_usage_clients:
                if not client_id.startswith('mai_client_'):
                    cursor.execute("""
                        SELECT COUNT(*) FROM client_model_daily_usage 
                        WHERE client_org_id = ?
                    """, (client_id,))
                    count = cursor.fetchone()[0]
                    
                    analysis["non_conforming_records"].append({
                        "table": "client_model_daily_usage",
                        "record_id": client_id,
                        "issue": f"client_org_id doesn't start with 'mai_client_': {client_id}",
                        "record_count": count
                    })
            
            analysis["model_daily_usage"] = model_usage_clients
        
        # 4. Analyze Processed Generations
        if 'processed_generations' in tables:
            cursor.execute("SELECT DISTINCT client_org_id FROM processed_generations")
            generation_clients = [row[0] for row in cursor.fetchall()]
            
            for client_id in generation_clients:
                if not client_id.startswith('mai_client_'):
                    cursor.execute("""
                        SELECT COUNT(*) FROM processed_generations 
                        WHERE client_org_id = ?
                    """, (client_id,))
                    count = cursor.fetchone()[0]
                    
                    analysis["non_conforming_records"].append({
                        "table": "processed_generations",
                        "record_id": client_id,
                        "issue": f"client_org_id doesn't start with 'mai_client_': {client_id}",
                        "record_count": count
                    })
            
            analysis["processed_generations"] = generation_clients
        
        # Summary
        analysis["summary"] = {
            "total_client_orgs": len(analysis["client_organizations"]),
            "total_non_conforming": len(analysis["non_conforming_records"]),
            "tables_analyzed": len(tables),
            "correct_prefix_expected": "mai_client_"
        }
        
    except Exception as e:
        analysis["error"] = str(e)
        print(f"❌ Analysis error: {e}")
    
    finally:
        conn.close()
    
    return analysis

def print_analysis_report(analysis: Dict[str, Any]):
    """Print detailed analysis report"""
    
    print("\n" + "="*80)
    print("🔍 mAI DATABASE CLEANUP ANALYSIS REPORT")
    print("="*80)
    
    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        return
    
    summary = analysis.get("summary", {})
    print(f"\n📊 SUMMARY:")
    print(f"   • Total Client Organizations: {summary.get('total_client_orgs', 0)}")
    print(f"   • Non-conforming Records: {summary.get('total_non_conforming', 0)}")
    print(f"   • Expected Prefix: {summary.get('correct_prefix_expected', 'mai_client_')}")
    
    # Client Organizations
    print(f"\n🏢 CLIENT ORGANIZATIONS:")
    if analysis["client_organizations"]:
        for i, org in enumerate(analysis["client_organizations"], 1):
            org_id = org.get('id', 'unknown')
            name = org.get('name', 'unknown')
            is_active = org.get('is_active', 'unknown')
            status = "✅" if org_id.startswith('mai_client_') else "❌"
            print(f"   {i}. {status} {org_id} | {name} | Active: {is_active}")
    else:
        print("   No client organizations found")
    
    # Non-conforming records
    print(f"\n⚠️  NON-CONFORMING RECORDS:")
    if analysis["non_conforming_records"]:
        for i, record in enumerate(analysis["non_conforming_records"], 1):
            table = record.get('table', 'unknown')
            issue = record.get('issue', 'unknown')
            count = record.get('record_count', 'N/A')
            print(f"   {i}. Table: {table}")
            print(f"      Issue: {issue}")
            if count != 'N/A':
                print(f"      Affected Records: {count}")
            print()
    else:
        print("   ✅ No non-conforming records found!")
    
    # Usage data summary
    print(f"\n📈 USAGE DATA SUMMARY:")
    print(f"   • User Daily Usage Clients: {len(analysis.get('user_daily_usage', []))}")
    print(f"   • Model Daily Usage Clients: {len(analysis.get('model_daily_usage', []))}")
    print(f"   • Processed Generation Clients: {len(analysis.get('processed_generations', []))}")

if __name__ == "__main__":
    print("🔍 Starting mAI database cleanup analysis...")
    
    analysis = analyze_database()
    print_analysis_report(analysis)
    
    # Save analysis to file for reference
    import json
    with open('database_cleanup_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f"\n💾 Analysis saved to: database_cleanup_analysis.json")
    print("="*80)