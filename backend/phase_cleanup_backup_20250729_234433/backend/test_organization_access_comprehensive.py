#!/usr/bin/env python3
"""
Comprehensive test suite for organization-based model access.
Tests multi-organization scenarios, user isolation, and edge cases.
"""

import sqlite3
import unittest
import tempfile
import shutil
import os
import time
import threading
import random
from typing import List, Dict, Any
from datetime import datetime


class TestOrganizationModelAccess(unittest.TestCase):
    """Comprehensive test suite for organization model access"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.test_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.test_dir, "test_webui.db")
        cls.setup_test_database()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        shutil.rmtree(cls.test_dir)
    
    @classmethod
    def setup_test_database(cls):
        """Create test database with schema"""
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        
        # Create user table
        cursor.execute("""
            CREATE TABLE user (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'user',
                last_active_at INTEGER
            )
        """)
        
        # Create model table
        cursor.execute("""
            CREATE TABLE model (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                base_model_id TEXT,
                name TEXT,
                params TEXT,
                meta TEXT,
                access_control TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at INTEGER,
                created_at INTEGER
            )
        """)
        
        # Create organization tables
        cursor.execute("""
            CREATE TABLE organization_models (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(organization_id, model_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                is_active INTEGER DEFAULT 1,
                joined_at INTEGER,
                UNIQUE(organization_id, user_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_org_members_user_active ON organization_members(user_id, is_active)")
        cursor.execute("CREATE INDEX idx_org_members_org_active ON organization_members(organization_id, is_active)")
        cursor.execute("CREATE INDEX idx_org_models_org_active ON organization_models(organization_id, is_active)")
        cursor.execute("CREATE UNIQUE INDEX idx_org_models_org_model ON organization_models(organization_id, model_id)")
        
        # Create view
        cursor.execute("""
            CREATE VIEW user_available_models AS
            SELECT DISTINCT
                om.user_id,
                orgmod.model_id,
                orgmod.organization_id,
                m.name as model_name,
                orgmod.is_active as model_active,
                om.is_active as member_active
            FROM organization_members om
            JOIN organization_models orgmod ON om.organization_id = orgmod.organization_id
            JOIN model m ON orgmod.model_id = m.id
            WHERE om.is_active = 1 AND orgmod.is_active = 1
        """)
        
        conn.commit()
        conn.close()
    
    def setUp(self):
        """Set up for each test"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.clear_test_data()
    
    def tearDown(self):
        """Clean up after each test"""
        self.conn.close()
    
    def clear_test_data(self):
        """Clear all test data"""
        tables = ["organization_members", "organization_models", "model", "user"]
        for table in tables:
            self.cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()
    
    def create_test_user(self, user_id: str, email: str, role: str = "user") -> str:
        """Create a test user"""
        self.cursor.execute("""
            INSERT INTO user (id, email, name, role, last_active_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, email, f"Test User {user_id}", role, int(time.time())))
        return user_id
    
    def create_test_model(self, model_id: str, name: str) -> str:
        """Create a test model"""
        self.cursor.execute("""
            INSERT INTO model (id, user_id, base_model_id, name, params, meta, 
                             access_control, is_active, created_at, updated_at)
            VALUES (?, ?, NULL, ?, '{}', '{}', NULL, 1, ?, ?)
        """, (model_id, "system", name, int(time.time()), int(time.time())))
        return model_id
    
    def add_user_to_organization(self, user_id: str, org_id: str, role: str = "member"):
        """Add user to organization"""
        member_id = f"om_{user_id}_{org_id}"
        self.cursor.execute("""
            INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (member_id, org_id, user_id, role, int(time.time())))
    
    def add_model_to_organization(self, model_id: str, org_id: str, is_active: int = 1):
        """Add model to organization"""
        org_model_id = f"orgmod_{org_id}_{model_id}"
        self.cursor.execute("""
            INSERT INTO organization_models (id, organization_id, model_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (org_model_id, org_id, model_id, is_active, int(time.time()), int(time.time())))
    
    def get_user_accessible_models(self, user_id: str) -> List[str]:
        """Get models accessible to a user"""
        # Simulate the get_models_by_user_id logic
        user_orgs = self.cursor.execute("""
            SELECT DISTINCT organization_id 
            FROM organization_members 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,)).fetchall()
        
        if not user_orgs:
            return []
        
        org_ids = [org[0] for org in user_orgs]
        
        # Get models for these organizations
        placeholders = ','.join(['?' for _ in org_ids])
        org_models = self.cursor.execute(f"""
            SELECT DISTINCT model_id 
            FROM organization_models 
            WHERE organization_id IN ({placeholders}) AND is_active = 1
        """, org_ids).fetchall()
        
        return [model[0] for model in org_models]
    
    def test_single_organization_access(self):
        """Test basic single organization model access"""
        # Create test data
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        model2 = self.create_test_model("model2", "Claude-3")
        
        # Create organization and add user/models
        org_id = "org1"
        self.add_user_to_organization(user1, org_id)
        self.add_model_to_organization(model1, org_id)
        self.add_model_to_organization(model2, org_id)
        self.conn.commit()
        
        # Test access
        accessible_models = self.get_user_accessible_models(user1)
        self.assertEqual(len(accessible_models), 2)
        self.assertIn(model1, accessible_models)
        self.assertIn(model2, accessible_models)
    
    def test_multi_organization_access(self):
        """Test user access across multiple organizations"""
        # Create users and models
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        model2 = self.create_test_model("model2", "Claude-3")
        model3 = self.create_test_model("model3", "Gemini")
        
        # Create organizations
        org1 = "org1"
        org2 = "org2"
        
        # User belongs to both organizations
        self.add_user_to_organization(user1, org1)
        self.add_user_to_organization(user1, org2)
        
        # Different models in each organization
        self.add_model_to_organization(model1, org1)
        self.add_model_to_organization(model2, org1)
        self.add_model_to_organization(model3, org2)
        self.conn.commit()
        
        # Test access - should see all models
        accessible_models = self.get_user_accessible_models(user1)
        self.assertEqual(len(accessible_models), 3)
        self.assertIn(model1, accessible_models)
        self.assertIn(model2, accessible_models)
        self.assertIn(model3, accessible_models)
    
    def test_user_isolation_between_organizations(self):
        """Test that users only see models from their organizations"""
        # Create users
        user1 = self.create_test_user("user1", "user1@test.com")
        user2 = self.create_test_user("user2", "user2@test.com")
        
        # Create models
        model1 = self.create_test_model("model1", "GPT-4")
        model2 = self.create_test_model("model2", "Claude-3")
        
        # Create organizations
        org1 = "org1"
        org2 = "org2"
        
        # User1 in org1, User2 in org2
        self.add_user_to_organization(user1, org1)
        self.add_user_to_organization(user2, org2)
        
        # Different models in each organization
        self.add_model_to_organization(model1, org1)
        self.add_model_to_organization(model2, org2)
        self.conn.commit()
        
        # Test isolation
        user1_models = self.get_user_accessible_models(user1)
        user2_models = self.get_user_accessible_models(user2)
        
        # User1 should only see model1
        self.assertEqual(len(user1_models), 1)
        self.assertIn(model1, user1_models)
        self.assertNotIn(model2, user1_models)
        
        # User2 should only see model2
        self.assertEqual(len(user2_models), 1)
        self.assertIn(model2, user2_models)
        self.assertNotIn(model1, user2_models)
    
    def test_inactive_membership_handling(self):
        """Test that inactive memberships don't grant access"""
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        
        org_id = "org1"
        self.add_model_to_organization(model1, org_id)
        
        # Add user with inactive membership
        member_id = f"om_{user1}_{org_id}"
        self.cursor.execute("""
            INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (member_id, org_id, user1, "member", int(time.time())))
        self.conn.commit()
        
        # Test access - should be empty
        accessible_models = self.get_user_accessible_models(user1)
        self.assertEqual(len(accessible_models), 0)
    
    def test_inactive_model_handling(self):
        """Test that inactive models are not accessible"""
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        model2 = self.create_test_model("model2", "Claude-3")
        
        org_id = "org1"
        self.add_user_to_organization(user1, org_id)
        self.add_model_to_organization(model1, org_id, is_active=1)
        self.add_model_to_organization(model2, org_id, is_active=0)  # Inactive
        self.conn.commit()
        
        # Test access - should only see active model
        accessible_models = self.get_user_accessible_models(user1)
        self.assertEqual(len(accessible_models), 1)
        self.assertIn(model1, accessible_models)
        self.assertNotIn(model2, accessible_models)
    
    def test_no_organization_membership(self):
        """Test users with no organization membership"""
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        
        # Create organization with model but don't add user
        org_id = "org1"
        self.add_model_to_organization(model1, org_id)
        self.conn.commit()
        
        # Test access - should be empty
        accessible_models = self.get_user_accessible_models(user1)
        self.assertEqual(len(accessible_models), 0)
    
    def test_organization_role_types(self):
        """Test different organization roles"""
        admin_user = self.create_test_user("admin", "admin@test.com", role="admin")
        member_user = self.create_test_user("member", "member@test.com", role="user")
        model1 = self.create_test_model("model1", "GPT-4")
        
        org_id = "org1"
        self.add_user_to_organization(admin_user, org_id, role="admin")
        self.add_user_to_organization(member_user, org_id, role="member")
        self.add_model_to_organization(model1, org_id)
        self.conn.commit()
        
        # Both should have access regardless of role
        admin_models = self.get_user_accessible_models(admin_user)
        member_models = self.get_user_accessible_models(member_user)
        
        self.assertEqual(admin_models, member_models)
        self.assertIn(model1, admin_models)
    
    def test_duplicate_model_assignments(self):
        """Test handling of duplicate model assignments"""
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        
        org1 = "org1"
        org2 = "org2"
        
        # User belongs to both organizations
        self.add_user_to_organization(user1, org1)
        self.add_user_to_organization(user1, org2)
        
        # Same model in both organizations
        self.add_model_to_organization(model1, org1)
        self.add_model_to_organization(model1, org2)
        self.conn.commit()
        
        # Should still only see model once (DISTINCT)
        accessible_models = self.get_user_accessible_models(user1)
        self.assertEqual(len(accessible_models), 1)
        self.assertEqual(accessible_models.count(model1), 1)
    
    def test_view_functionality(self):
        """Test the user_available_models view"""
        user1 = self.create_test_user("user1", "user1@test.com")
        model1 = self.create_test_model("model1", "GPT-4")
        
        org_id = "org1"
        self.add_user_to_organization(user1, org_id)
        self.add_model_to_organization(model1, org_id)
        self.conn.commit()
        
        # Query the view
        view_results = self.cursor.execute("""
            SELECT user_id, model_id, model_name, organization_id
            FROM user_available_models
            WHERE user_id = ?
        """, (user1,)).fetchall()
        
        self.assertEqual(len(view_results), 1)
        self.assertEqual(view_results[0][0], user1)
        self.assertEqual(view_results[0][1], model1)
        self.assertEqual(view_results[0][2], "GPT-4")
        self.assertEqual(view_results[0][3], org_id)
    
    def test_concurrent_access_safety(self):
        """Test concurrent access to organization data"""
        user_count = 10
        model_count = 5
        org_count = 3
        
        # Create test data
        users = [self.create_test_user(f"user{i}", f"user{i}@test.com") for i in range(user_count)]
        models = [self.create_test_model(f"model{i}", f"Model-{i}") for i in range(model_count)]
        orgs = [f"org{i}" for i in range(org_count)]
        
        # Randomly assign users to organizations and models to organizations
        for user in users:
            for org in random.sample(orgs, random.randint(1, org_count)):
                self.add_user_to_organization(user, org)
        
        for org in orgs:
            for model in random.sample(models, random.randint(1, model_count)):
                self.add_model_to_organization(model, org)
        
        self.conn.commit()
        
        # Test concurrent reads
        results = {}
        errors = []
        
        def concurrent_read(user_id):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Simulate the secure query pattern
                user_orgs = cursor.execute("""
                    SELECT DISTINCT organization_id 
                    FROM organization_members 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,)).fetchall()
                
                if user_orgs:
                    org_ids = [org[0] for org in user_orgs]
                    
                    # Build parameterized query
                    params = {}
                    param_names = []
                    for i, org_id in enumerate(org_ids):
                        param_name = f":org_{i}"
                        params[param_name] = org_id
                        param_names.append(param_name)
                    
                    # This simulates the secure query (SQLite doesn't support named params directly)
                    placeholders = ','.join(['?' for _ in org_ids])
                    models = cursor.execute(f"""
                        SELECT DISTINCT model_id 
                        FROM organization_models 
                        WHERE organization_id IN ({placeholders}) AND is_active = 1
                    """, org_ids).fetchall()
                    
                    results[user_id] = [m[0] for m in models]
                else:
                    results[user_id] = []
                
                conn.close()
            except Exception as e:
                errors.append((user_id, str(e)))
        
        # Run concurrent threads
        threads = []
        for user in users:
            t = threading.Thread(target=concurrent_read, args=(user,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        
        # Verify all users got results
        self.assertEqual(len(results), user_count)
    
    def test_performance_with_indexes(self):
        """Test query performance with indexes"""
        # Create larger dataset
        user_count = 100
        model_count = 50
        org_count = 20
        
        # Bulk insert users
        users = [(f"user{i}", f"user{i}@test.com", f"User {i}", "user", int(time.time())) 
                 for i in range(user_count)]
        self.cursor.executemany("""
            INSERT INTO user (id, email, name, role, last_active_at)
            VALUES (?, ?, ?, ?, ?)
        """, users)
        
        # Bulk insert models
        models = [(f"model{i}", "system", None, f"Model-{i}", "{}", "{}", None, 1, 
                   int(time.time()), int(time.time())) for i in range(model_count)]
        self.cursor.executemany("""
            INSERT INTO model (id, user_id, base_model_id, name, params, meta, 
                             access_control, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, models)
        
        # Create organization memberships and model assignments
        memberships = []
        assignments = []
        
        for i in range(user_count):
            user_id = f"user{i}"
            # Each user in 1-3 organizations
            for org_idx in random.sample(range(org_count), random.randint(1, 3)):
                org_id = f"org{org_idx}"
                member_id = f"om_{user_id}_{org_id}"
                memberships.append((member_id, org_id, user_id, "member", 1, int(time.time())))
        
        for org_idx in range(org_count):
            org_id = f"org{org_idx}"
            # Each organization has 10-30 models
            for model_idx in random.sample(range(model_count), random.randint(10, 30)):
                model_id = f"model{model_idx}"
                org_model_id = f"orgmod_{org_id}_{model_id}"
                assignments.append((org_model_id, org_id, model_id, 1, int(time.time()), int(time.time())))
        
        self.cursor.executemany("""
            INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, memberships)
        
        self.cursor.executemany("""
            INSERT INTO organization_models (id, organization_id, model_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, assignments)
        
        self.conn.commit()
        
        # Test query performance
        import time
        
        test_user = "user50"
        
        # Warm up
        for _ in range(5):
            self.get_user_accessible_models(test_user)
        
        # Measure performance
        times = []
        for _ in range(100):
            start = time.perf_counter()
            models = self.get_user_accessible_models(test_user)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance assertions
        self.assertLess(avg_time, 5.0, f"Average query time {avg_time:.2f}ms exceeds 5ms threshold")
        self.assertLess(max_time, 10.0, f"Max query time {max_time:.2f}ms exceeds 10ms threshold")
        
        # Verify index usage
        plan = self.cursor.execute("""
            EXPLAIN QUERY PLAN
            SELECT DISTINCT organization_id 
            FROM organization_members 
            WHERE user_id = ? AND is_active = 1
        """, (test_user,)).fetchall()
        
        plan_text = " ".join([str(row) for row in plan])
        self.assertIn("USING INDEX", plan_text, "Query not using index")


class TestOrganizationEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up test database"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_edge_cases.db")
        TestOrganizationModelAccess.setup_test_database.__func__(self)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        """Clean up"""
        self.conn.close()
        shutil.rmtree(self.test_dir)
    
    def test_empty_organization(self):
        """Test organization with no models"""
        user_id = "user1"
        org_id = "empty_org"
        
        # Create user and add to empty organization
        self.cursor.execute("""
            INSERT INTO user (id, email, name, role) VALUES (?, ?, ?, ?)
        """, (user_id, "user@test.com", "Test User", "user"))
        
        self.cursor.execute("""
            INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"om_{user_id}_{org_id}", org_id, user_id, "member", 1, int(time.time())))
        
        self.conn.commit()
        
        # Should return empty list, not error
        cursor = self.conn.cursor()
        user_orgs = cursor.execute("""
            SELECT DISTINCT organization_id FROM organization_members 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,)).fetchall()
        
        self.assertEqual(len(user_orgs), 1)
        
        org_models = cursor.execute("""
            SELECT DISTINCT model_id FROM organization_models 
            WHERE organization_id = ? AND is_active = 1
        """, (org_id,)).fetchall()
        
        self.assertEqual(len(org_models), 0)
    
    def test_malicious_organization_id(self):
        """Test SQL injection attempt via organization ID"""
        malicious_org_id = "'; DROP TABLE organization_models; --"
        user_id = "user1"
        
        # Create user
        self.cursor.execute("""
            INSERT INTO user (id, email, name, role) VALUES (?, ?, ?, ?)
        """, (user_id, "user@test.com", "Test User", "user"))
        
        # Add user to organization with malicious ID
        self.cursor.execute("""
            INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"om_test", malicious_org_id, user_id, "member", 1, int(time.time())))
        
        self.conn.commit()
        
        # Verify table still exists after query
        cursor = self.conn.cursor()
        
        # Get user organizations (should handle malicious ID safely)
        user_orgs = cursor.execute("""
            SELECT DISTINCT organization_id FROM organization_members 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,)).fetchall()
        
        # Try to query with the malicious org_id using parameterization
        try:
            cursor.execute("""
                SELECT DISTINCT model_id FROM organization_models 
                WHERE organization_id = ? AND is_active = 1
            """, (malicious_org_id,))
        except:
            pass
        
        # Verify table still exists
        tables = cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='organization_models'
        """).fetchall()
        
        self.assertEqual(len(tables), 1, "Table was dropped - SQL injection succeeded!")
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        special_chars = [
            ("user_emoji", "test@😀.com", "😀 User"),
            ("user_chinese", "测试@test.com", "测试用户"),
            ("user_quotes", "test'quotes@test.com", "User'with'quotes"),
            ("user_unicode", "tëst@test.com", "Tëst Üsér")
        ]
        
        org_id = "org_unicode"
        model_id = "model_special"
        
        # Create model
        self.cursor.execute("""
            INSERT INTO model (id, user_id, base_model_id, name, params, meta, 
                             access_control, is_active, created_at, updated_at)
            VALUES (?, ?, NULL, ?, '{}', '{}', NULL, 1, ?, ?)
        """, (model_id, "system", "Model with 特殊字符", int(time.time()), int(time.time())))
        
        # Add model to organization
        self.cursor.execute("""
            INSERT INTO organization_models (id, organization_id, model_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"orgmod_{org_id}_{model_id}", org_id, model_id, 1, int(time.time()), int(time.time())))
        
        # Create users with special characters
        for user_id, email, name in special_chars:
            self.cursor.execute("""
                INSERT INTO user (id, email, name, role) VALUES (?, ?, ?, ?)
            """, (user_id, email, name, "user"))
            
            self.cursor.execute("""
                INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"om_{user_id}_{org_id}", org_id, user_id, "member", 1, int(time.time())))
        
        self.conn.commit()
        
        # Verify all users can access the model
        for user_id, _, _ in special_chars:
            user_orgs = self.cursor.execute("""
                SELECT organization_id FROM organization_members 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,)).fetchall()
            
            self.assertEqual(len(user_orgs), 1)
            
            # Verify model access
            models = self.cursor.execute("""
                SELECT model_id FROM organization_models 
                WHERE organization_id = ? AND is_active = 1
            """, (org_id,)).fetchall()
            
            self.assertEqual(len(models), 1)


def run_test_suite():
    """Run the complete test suite"""
    print("🧪 Running Comprehensive Organization Access Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOrganizationModelAccess))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOrganizationEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Total Tests: {result.testsRun}")
    print(f"   Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   Failed: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_test_suite())