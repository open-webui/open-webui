#!/usr/bin/env python3
"""
Setup Organization-Based Model Access for mAI

This script ensures that all users within an organization have automatic access
to the models configured for that organization. It creates the necessary database
structures and links models to organizations.
"""

import sqlite3
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional


class OrganizationModelAccessManager:
    """Manages model access for organizations"""
    
    def __init__(self, db_path: str = "/app/backend/data/webui.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()
    
    def create_organization_models_table(self):
        """Create table to link organizations with their available models"""
        print("📦 Creating organization_models table...")
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_models (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(organization_id, model_id),
                FOREIGN KEY (organization_id) REFERENCES client_organizations(id),
                FOREIGN KEY (model_id) REFERENCES model(id)
            )
        """)
        print("✅ Table created or already exists")
    
    def create_organization_members_table(self):
        """Create table to track organization members"""
        print("📦 Creating organization_members table...")
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                is_active INTEGER DEFAULT 1,
                joined_at INTEGER NOT NULL,
                UNIQUE(organization_id, user_id),
                FOREIGN KEY (organization_id) REFERENCES client_organizations(id),
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """)
        print("✅ Table created or already exists")
    
    def get_openrouter_models(self) -> List[Dict[str, str]]:
        """Get configured OpenRouter models from config"""
        self.cursor.execute("SELECT data FROM config ORDER BY id DESC LIMIT 1")
        config_data = self.cursor.fetchone()
        
        if not config_data:
            return []
            
        config = json.loads(config_data[0])
        openai_config = config.get('openai', {}).get('api_configs', {}).get('0', {})
        model_ids = openai_config.get('model_ids', [])
        
        # Map model IDs to display names
        model_map = {
            'anthropic/claude-sonnet-4': 'Claude 3.5 Sonnet v2',
            'google/gemini-2.5-flash': 'Gemini 2.0 Flash',
            'google/gemini-2.5-pro': 'Gemini 2.0 Pro',
            'deepseek/deepseek-chat-v3-0324': 'DeepSeek Chat V3',
            'anthropic/claude-3.7-sonnet': 'Claude 3 Sonnet',
            'google/gemini-2.5-flash-lite-preview-06-17': 'Gemini 2.0 Flash Lite Preview',
            'openai/gpt-4.1': 'GPT-4 Turbo',
            'x-ai/grok-4': 'Grok 2',
            'openai/gpt-4o-mini': 'GPT-4o Mini',
            'openai/o4-mini-high': 'O1 Mini',
            'openai/o3': 'O1',
            'openai/chatgpt-4o-latest': 'ChatGPT-4o'
        }
        
        return [{'id': model_id, 'name': model_map.get(model_id, model_id)} 
                for model_id in model_ids]
    
    def link_models_to_organization(self, org_id: str, model_ids: List[str]):
        """Link models to an organization"""
        timestamp = int(time.time())
        
        for model_id in model_ids:
            unique_id = f"{org_id}_{model_id}_{timestamp}"
            try:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO organization_models 
                    (id, organization_id, model_id, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (unique_id, org_id, model_id, timestamp, timestamp))
            except sqlite3.IntegrityError:
                # Model already linked
                pass
    
    def link_users_to_organization(self, org_id: str):
        """Link users to organization based on email domain"""
        # Get organization details
        self.cursor.execute("SELECT name FROM client_organizations WHERE id = ?", (org_id,))
        org_data = self.cursor.fetchone()
        if not org_data:
            return
            
        org_name = org_data[0]
        
        # For development environment, link all non-system users
        if 'DEV' in org_name or 'dev' in org_name:
            print(f"🔧 Development organization detected: {org_name}")
            self.cursor.execute("""
                SELECT id, name, email FROM user 
                WHERE email != 'system@mai.local' AND role != 'pending'
            """)
        else:
            # For production, match by email domain
            # This would need to be implemented based on your domain matching logic
            return
            
        users = self.cursor.fetchall()
        timestamp = int(time.time())
        
        for user_id, user_name, user_email in users:
            unique_id = f"{org_id}_{user_id}_{timestamp}"
            try:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO organization_members
                    (id, organization_id, user_id, role, is_active, joined_at)
                    VALUES (?, ?, ?, 'member', 1, ?)
                """, (unique_id, org_id, user_id, timestamp))
                print(f"  ✅ Linked user: {user_name} ({user_email})")
            except sqlite3.IntegrityError:
                pass
    
    def update_model_access_control(self):
        """Update model access control to check organization membership"""
        print("\n🔧 Updating model access control...")
        
        # Remove all existing access control to make models organization-aware
        self.cursor.execute("UPDATE model SET access_control = NULL")
        print("✅ Cleared direct model access control")
        
        # The actual access control will be handled by checking organization_models
        # and organization_members tables in the application logic
    
    def create_view_for_user_models(self):
        """Create a view that shows which models each user can access"""
        print("\n📊 Creating user_available_models view...")
        
        self.cursor.execute("""
            CREATE VIEW IF NOT EXISTS user_available_models AS
            SELECT DISTINCT
                om.user_id,
                u.name as user_name,
                u.email as user_email,
                orgm.model_id,
                m.name as model_name,
                org.name as organization_name
            FROM organization_members om
            JOIN organization_models orgm ON om.organization_id = orgm.organization_id
            JOIN user u ON om.user_id = u.id
            JOIN model m ON orgm.model_id = m.id
            JOIN client_organizations org ON om.organization_id = org.id
            WHERE om.is_active = 1 AND orgm.is_active = 1
        """)
        print("✅ View created")
    
    def display_summary(self):
        """Display summary of the setup"""
        print("\n📊 Setup Summary:")
        
        # Organizations
        self.cursor.execute("SELECT COUNT(*) FROM client_organizations")
        org_count = self.cursor.fetchone()[0]
        print(f"  • Organizations: {org_count}")
        
        # Models
        self.cursor.execute("SELECT COUNT(*) FROM model")
        model_count = self.cursor.fetchone()[0]
        print(f"  • Models registered: {model_count}")
        
        # Organization-Model links
        try:
            self.cursor.execute("SELECT COUNT(*) FROM organization_models")
            org_model_count = self.cursor.fetchone()[0]
            print(f"  • Organization-Model links: {org_model_count}")
        except:
            print(f"  • Organization-Model links: 0")
        
        # Organization members
        try:
            self.cursor.execute("SELECT COUNT(*) FROM organization_members")
            member_count = self.cursor.fetchone()[0]
            print(f"  • Organization members: {member_count}")
        except:
            print(f"  • Organization members: 0")
        
        # Show user access
        print("\n👥 User Model Access:")
        try:
            self.cursor.execute("""
                SELECT user_email, COUNT(DISTINCT model_id) as model_count
                FROM user_available_models
                GROUP BY user_email
            """)
            for email, count in self.cursor.fetchall():
                print(f"  • {email}: {count} models")
        except:
            print("  • View not yet created")


def main():
    """Main setup function"""
    print("🚀 Organization-Based Model Access Setup")
    print("=" * 50)
    
    with OrganizationModelAccessManager() as manager:
        # Create necessary tables
        manager.create_organization_models_table()
        manager.create_organization_members_table()
        
        # Get organizations
        manager.cursor.execute("SELECT id, name FROM client_organizations")
        organizations = manager.cursor.fetchall()
        
        if not organizations:
            print("❌ No organizations found!")
            return
        
        # Get available models
        models = manager.get_openrouter_models()
        model_ids = [m['id'] for m in models]
        
        print(f"\n📋 Found {len(organizations)} organization(s)")
        print(f"📋 Found {len(models)} configured model(s)")
        
        # Link models to each organization
        for org_id, org_name in organizations:
            print(f"\n🏢 Processing organization: {org_name}")
            
            # Link all models to the organization
            manager.link_models_to_organization(org_id, model_ids)
            print(f"  ✅ Linked {len(model_ids)} models")
            
            # Link users to the organization
            manager.link_users_to_organization(org_id)
        
        # Update access control
        manager.update_model_access_control()
        
        # Create helper view
        manager.create_view_for_user_models()
        
        # Display summary
        manager.display_summary()
        
    print("\n✅ Setup complete!")
    print("\n⚠️  IMPORTANT: The application needs to be updated to check")
    print("   organization_models and organization_members tables")
    print("   when determining model access for users.")


if __name__ == "__main__":
    main()