#!/usr/bin/env python3
"""
Database cleanup script for mAI Usage Settings
Removes all non-conforming client organizations and related usage data
Keeps only records that follow the mai_client_ prefix format
"""

import sys
import os
sys.path.append('backend')

import sqlite3
import json
from typing import List, Dict, Any
from datetime import datetime

class DatabaseCleanup:
    def __init__(self, db_path: str = "backend/data/webui.db"):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.cleanup_log = []
        
    def create_backup(self) -> bool:
        """Create a backup of the database before cleanup"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            print(f"✅ Database backup created: {self.backup_path}")
            self.cleanup_log.append(f"Backup created: {self.backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
    
    def get_non_conforming_client_ids(self) -> List[str]:
        """Get list of client IDs that don't follow mai_client_ format"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        non_conforming_ids = []
        
        try:
            # Get all client organization IDs
            cursor.execute("SELECT id FROM client_organizations")
            client_ids = [row[0] for row in cursor.fetchall()]
            
            for client_id in client_ids:
                if not client_id.startswith('mai_client_'):
                    non_conforming_ids.append(client_id)
            
        except Exception as e:
            print(f"❌ Error getting client IDs: {e}")
        finally:
            conn.close()
        
        return non_conforming_ids
    
    def cleanup_client_organizations(self, non_conforming_ids: List[str]) -> int:
        """Remove non-conforming client organizations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        deleted_count = 0
        
        try:
            for client_id in non_conforming_ids:
                cursor.execute("DELETE FROM client_organizations WHERE id = ?", (client_id,))
                if cursor.rowcount > 0:
                    deleted_count += cursor.rowcount
                    print(f"🗑️  Deleted client organization: {client_id}")
                    self.cleanup_log.append(f"Deleted client_organizations: {client_id}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error cleaning client organizations: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return deleted_count
    
    def cleanup_user_daily_usage(self, non_conforming_ids: List[str]) -> int:
        """Remove user daily usage records for non-conforming clients"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        deleted_count = 0
        
        try:
            for client_id in non_conforming_ids:
                cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage WHERE client_org_id = ?", (client_id,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    cursor.execute("DELETE FROM client_user_daily_usage WHERE client_org_id = ?", (client_id,))
                    deleted_count += cursor.rowcount
                    print(f"🗑️  Deleted {cursor.rowcount} user daily usage records for: {client_id}")
                    self.cleanup_log.append(f"Deleted {cursor.rowcount} client_user_daily_usage records for: {client_id}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error cleaning user daily usage: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return deleted_count
    
    def cleanup_model_daily_usage(self, non_conforming_ids: List[str]) -> int:
        """Remove model daily usage records for non-conforming clients"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        deleted_count = 0
        
        try:
            for client_id in non_conforming_ids:
                cursor.execute("SELECT COUNT(*) FROM client_model_daily_usage WHERE client_org_id = ?", (client_id,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    cursor.execute("DELETE FROM client_model_daily_usage WHERE client_org_id = ?", (client_id,))
                    deleted_count += cursor.rowcount
                    print(f"🗑️  Deleted {cursor.rowcount} model daily usage records for: {client_id}")
                    self.cleanup_log.append(f"Deleted {cursor.rowcount} client_model_daily_usage records for: {client_id}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error cleaning model daily usage: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return deleted_count
    
    def cleanup_processed_generations(self) -> int:
        """Remove all processed generations with non-conforming client_org_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        deleted_count = 0
        
        try:
            # Get all distinct client_org_ids from processed_generations
            cursor.execute("SELECT DISTINCT client_org_id FROM processed_generations")
            generation_clients = [row[0] for row in cursor.fetchall()]
            
            for client_id in generation_clients:
                if not client_id.startswith('mai_client_'):
                    cursor.execute("SELECT COUNT(*) FROM processed_generations WHERE client_org_id = ?", (client_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute("DELETE FROM processed_generations WHERE client_org_id = ?", (client_id,))
                        deleted_count += cursor.rowcount
                        print(f"🗑️  Deleted {cursor.rowcount} processed generation records for: {client_id}")
                        self.cleanup_log.append(f"Deleted {cursor.rowcount} processed_generations records for: {client_id}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error cleaning processed generations: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return deleted_count
    
    def cleanup_other_tables(self, non_conforming_ids: List[str]) -> int:
        """Clean up other tables that might reference non-conforming client IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        deleted_count = 0
        
        try:
            # Clean up client_daily_usage if it exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_daily_usage'")
            if cursor.fetchone():
                for client_id in non_conforming_ids:
                    cursor.execute("SELECT COUNT(*) FROM client_daily_usage WHERE client_org_id = ?", (client_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute("DELETE FROM client_daily_usage WHERE client_org_id = ?", (client_id,))
                        deleted_count += cursor.rowcount
                        print(f"🗑️  Deleted {cursor.rowcount} daily usage records for: {client_id}")
                        self.cleanup_log.append(f"Deleted {cursor.rowcount} client_daily_usage records for: {client_id}")
            
            # Clean up client_live_counters if it exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_live_counters'")
            if cursor.fetchone():
                for client_id in non_conforming_ids:
                    cursor.execute("SELECT COUNT(*) FROM client_live_counters WHERE client_org_id = ?", (client_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute("DELETE FROM client_live_counters WHERE client_org_id = ?", (client_id,))
                        deleted_count += cursor.rowcount
                        print(f"🗑️  Deleted {cursor.rowcount} live counter records for: {client_id}")
                        self.cleanup_log.append(f"Deleted {cursor.rowcount} client_live_counters records for: {client_id}")
            
            # Clean up user_client_mapping if it exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_client_mapping'")
            if cursor.fetchone():
                for client_id in non_conforming_ids:
                    cursor.execute("SELECT COUNT(*) FROM user_client_mapping WHERE client_org_id = ?", (client_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute("DELETE FROM user_client_mapping WHERE client_org_id = ?", (client_id,))
                        deleted_count += cursor.rowcount
                        print(f"🗑️  Deleted {cursor.rowcount} user mapping records for: {client_id}")
                        self.cleanup_log.append(f"Deleted {cursor.rowcount} user_client_mapping records for: {client_id}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error cleaning other tables: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return deleted_count
    
    def verify_cleanup(self) -> Dict[str, Any]:
        """Verify the cleanup was successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        verification = {
            "client_organizations": 0,
            "user_daily_usage": 0,
            "model_daily_usage": 0,
            "processed_generations": 0,
            "conforming_clients": [],
            "remaining_non_conforming": []
        }
        
        try:
            # Check remaining client organizations
            cursor.execute("SELECT id, name FROM client_organizations")
            clients = cursor.fetchall()
            
            for client_id, name in clients:
                if client_id.startswith('mai_client_'):
                    verification["conforming_clients"].append({"id": client_id, "name": name})
                else:
                    verification["remaining_non_conforming"].append({"id": client_id, "name": name})
            
            verification["client_organizations"] = len(clients)
            
            # Check remaining usage records
            cursor.execute("SELECT COUNT(*) FROM client_user_daily_usage")
            verification["user_daily_usage"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM client_model_daily_usage")
            verification["model_daily_usage"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM processed_generations")
            verification["processed_generations"] = cursor.fetchone()[0]
            
        except Exception as e:
            verification["error"] = str(e)
        finally:
            conn.close()
        
        return verification
    
    def run_cleanup(self) -> Dict[str, Any]:
        """Execute the complete cleanup process"""
        print("🧹 Starting mAI database cleanup process...")
        print("="*80)
        
        # Create backup
        if not self.create_backup():
            return {"success": False, "error": "Failed to create backup"}
        
        # Get non-conforming client IDs
        non_conforming_ids = self.get_non_conforming_client_ids()
        print(f"\n📋 Found {len(non_conforming_ids)} non-conforming client IDs:")
        for client_id in non_conforming_ids:
            print(f"   • {client_id}")
        
        if not non_conforming_ids:
            print("✅ No cleanup needed - all client IDs are conforming!")
            return {"success": True, "message": "No cleanup needed"}
        
        print(f"\n🗑️  Starting cleanup process...")
        
        # Cleanup statistics
        stats = {
            "client_organizations": 0,
            "user_daily_usage": 0,
            "model_daily_usage": 0,
            "processed_generations": 0,
            "other_tables": 0
        }
        
        # Cleanup each table
        stats["client_organizations"] = self.cleanup_client_organizations(non_conforming_ids)
        stats["user_daily_usage"] = self.cleanup_user_daily_usage(non_conforming_ids)
        stats["model_daily_usage"] = self.cleanup_model_daily_usage(non_conforming_ids)
        stats["processed_generations"] = self.cleanup_processed_generations()
        stats["other_tables"] = self.cleanup_other_tables(non_conforming_ids)
        
        # Verify cleanup
        verification = self.verify_cleanup()
        
        # Save cleanup log
        cleanup_report = {
            "timestamp": datetime.now().isoformat(),
            "backup_path": self.backup_path,
            "non_conforming_ids_removed": non_conforming_ids,
            "cleanup_stats": stats,
            "verification": verification,
            "cleanup_log": self.cleanup_log
        }
        
        with open('database_cleanup_report.json', 'w') as f:
            json.dump(cleanup_report, f, indent=2, default=str)
        
        return {
            "success": True,
            "stats": stats,
            "verification": verification,
            "backup_path": self.backup_path,
            "report_path": "database_cleanup_report.json"
        }

def print_cleanup_report(result: Dict[str, Any]):
    """Print the cleanup report"""
    print("\n" + "="*80)
    print("🧹 mAI DATABASE CLEANUP RESULTS")
    print("="*80)
    
    if not result.get("success"):
        print(f"❌ Cleanup failed: {result.get('error', 'Unknown error')}")
        return
    
    if "message" in result:
        print(f"ℹ️  {result['message']}")
        return
    
    stats = result.get("stats", {})
    verification = result.get("verification", {})
    
    print(f"\n📊 CLEANUP STATISTICS:")
    print(f"   • Client Organizations Deleted: {stats.get('client_organizations', 0)}")
    print(f"   • User Daily Usage Records Deleted: {stats.get('user_daily_usage', 0)}")
    print(f"   • Model Daily Usage Records Deleted: {stats.get('model_daily_usage', 0)}")
    print(f"   • Processed Generation Records Deleted: {stats.get('processed_generations', 0)}")
    print(f"   • Other Table Records Deleted: {stats.get('other_tables', 0)}")
    
    print(f"\n✅ POST-CLEANUP VERIFICATION:")
    print(f"   • Client Organizations Remaining: {verification.get('client_organizations', 0)}")
    print(f"   • User Daily Usage Records Remaining: {verification.get('user_daily_usage', 0)}")
    print(f"   • Model Daily Usage Records Remaining: {verification.get('model_daily_usage', 0)}")
    print(f"   • Processed Generation Records Remaining: {verification.get('processed_generations', 0)}")
    
    conforming_clients = verification.get("conforming_clients", [])
    remaining_non_conforming = verification.get("remaining_non_conforming", [])
    
    if conforming_clients:
        print(f"\n✅ CONFORMING CLIENTS (mai_client_ prefix):")
        for client in conforming_clients:
            print(f"   • {client['id']} | {client['name']}")
    else:
        print(f"\n📝 No conforming clients found (database is clean)")
    
    if remaining_non_conforming:
        print(f"\n⚠️  REMAINING NON-CONFORMING CLIENTS:")
        for client in remaining_non_conforming:
            print(f"   • {client['id']} | {client['name']}")
    else:
        print(f"\n✅ All non-conforming clients successfully removed!")
    
    print(f"\n💾 Backup saved to: {result.get('backup_path', 'Unknown')}")
    print(f"📋 Report saved to: {result.get('report_path', 'Unknown')}")

if __name__ == "__main__":
    cleanup = DatabaseCleanup()
    result = cleanup.run_cleanup()
    print_cleanup_report(result)