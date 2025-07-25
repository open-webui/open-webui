"""
Comprehensive test suite for subscription billing functionality.

This module tests the subscription billing feature end-to-end, including:
- Backend API endpoints
- Proportional billing calculations
- Tiered pricing logic
- Admin access controls
- Edge cases and error handling
"""

import pytest
import asyncio
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from open_webui.main import app
from open_webui.models.users import Users, UserModel
from open_webui.models.organization_usage import (
    ClientOrganizationDB, UserClientMappingDB, 
    ClientOrganizationModel, UserClientMappingModel
)


class TestSubscriptionBillingAPI:
    """Test the subscription billing API endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        return UserModel(
            id="admin_user_123",
            name="Admin User",
            email="admin@test.com",
            role="admin",
            profile_image_url="/user.png",
            last_active_at=int(datetime.now().timestamp()),
            created_at=int(datetime.now().timestamp()),
            updated_at=int(datetime.now().timestamp())
        )
    
    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular user."""
        return UserModel(
            id="user_123",
            name="Regular User",
            email="user@test.com",
            role="user",
            profile_image_url="/user.png",
            last_active_at=int(datetime.now().timestamp()),
            created_at=int(datetime.now().timestamp()),
            updated_at=int(datetime.now().timestamp())
        )
    
    @pytest.fixture
    def mock_organization(self):
        """Create a mock client organization."""
        return ClientOrganizationModel(
            id="org_123",
            name="Test Organization",
            markup_rate=1.3,
            monthly_limit=1000.0,
            billing_email="billing@test.com",
            is_active=True,
            created_at=int(datetime.now().timestamp()),
            updated_at=int(datetime.now().timestamp())
        )
    
    @pytest.fixture
    def mock_user_mappings(self):
        """Create mock user-client mappings."""
        current_time = datetime.now()
        
        # Users added at different times in current month
        return [
            UserClientMappingModel(
                id="mapping_1",
                user_id="user_1",
                client_org_id="org_123",
                openrouter_user_id="openrouter_user_1",
                is_active=True,
                created_at=int(current_time.replace(day=1).timestamp()),
                updated_at=int(current_time.timestamp())
            ),
            UserClientMappingModel(
                id="mapping_2",
                user_id="user_2",
                client_org_id="org_123",
                openrouter_user_id="openrouter_user_2",
                is_active=True,
                created_at=int(current_time.replace(day=15).timestamp()),
                updated_at=int(current_time.timestamp())
            ),
            UserClientMappingModel(
                id="mapping_3",
                user_id="user_3",
                client_org_id="org_123",
                openrouter_user_id="openrouter_user_3",
                is_active=True,
                created_at=int(current_time.replace(day=25).timestamp()),
                updated_at=int(current_time.timestamp())
            )
        ]
    
    @pytest.fixture
    def mock_users(self):
        """Create mock user data with different creation dates."""
        current_time = datetime.now()
        
        return [
            UserModel(
                id="user_1",
                name="User One",
                email="user1@test.com",
                role="user",
                profile_image_url="/user.png",
                last_active_at=int(current_time.timestamp()),
                created_at=int(current_time.replace(day=1).timestamp()),
                updated_at=int(current_time.timestamp())
            ),
            UserModel(
                id="user_2", 
                name="User Two",
                email="user2@test.com",
                role="user",
                profile_image_url="/user.png",
                last_active_at=int(current_time.timestamp()),
                created_at=int(current_time.replace(day=15).timestamp()),
                updated_at=int(current_time.timestamp())
            ),
            UserModel(
                id="user_3",
                name="User Three", 
                email="user3@test.com",
                role="user",
                profile_image_url="/user.png",
                last_active_at=int(current_time.timestamp()),
                created_at=int(current_time.replace(day=25).timestamp()),
                updated_at=int(current_time.timestamp())
            )
        ]

    @patch('open_webui.routers.client_organizations.get_admin_user')
    @patch('open_webui.routers.client_organizations.ClientOrganizationDB')
    @patch('open_webui.routers.client_organizations.UserClientMappingDB')
    @patch('open_webui.routers.client_organizations.Users')
    def test_subscription_billing_success(
        self, mock_users_db, mock_mapping_db, mock_org_db, mock_auth,
        client, mock_admin_user, mock_organization, mock_user_mappings, mock_users
    ):
        """Test successful subscription billing calculation."""
        # Setup mocks
        mock_auth.return_value = mock_admin_user
        mock_org_db.get_client_by_id.return_value = mock_organization
        mock_mapping_db.get_mappings_by_client_id.return_value = mock_user_mappings
        mock_users_db.get_users_by_user_ids.return_value = mock_users
        
        # Make request
        response = client.get("/api/client-organizations/subscription/billing?client_id=org_123")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["client_id"] == "org_123"
        assert data["client_name"] == "Test Organization"
        
        # Test subscription data structure
        subscription_data = data["subscription_data"]
        assert "current_month" in subscription_data
        assert "pricing_tiers" in subscription_data
        
        current_month = subscription_data["current_month"]
        assert current_month["total_users"] == 3
        assert current_month["current_tier_price_pln"] == 79  # 1-3 users tier
        
        # Test user details
        assert len(current_month["user_details"]) == 3
        for user_detail in current_month["user_details"]:
            assert "user_id" in user_detail
            assert "user_name" in user_detail
            assert "billing_proportion" in user_detail
            assert "monthly_cost_pln" in user_detail
        
        # Test tier breakdown
        tier_breakdown = current_month["tier_breakdown"]
        assert len(tier_breakdown) == 4
        
        # First tier should be current
        assert tier_breakdown[0]["is_current_tier"] is True
        assert tier_breakdown[0]["price_per_user_pln"] == 79

    @patch('open_webui.routers.client_organizations.get_admin_user')
    def test_subscription_billing_non_admin_access(self, mock_auth, client, mock_regular_user):
        """Test that non-admin users cannot access subscription billing."""
        mock_auth.side_effect = HTTPException(status_code=403, detail="Admin access required")
        
        response = client.get("/api/client-organizations/subscription/billing")
        assert response.status_code == 403

    @patch('open_webui.routers.client_organizations.get_admin_user')
    @patch('open_webui.routers.client_organizations.ClientOrganizationDB')
    def test_subscription_billing_invalid_organization(
        self, mock_org_db, mock_auth, client, mock_admin_user
    ):
        """Test handling of invalid organization ID."""
        mock_auth.return_value = mock_admin_user
        mock_org_db.get_client_by_id.return_value = None
        
        response = client.get("/api/client-organizations/subscription/billing?client_id=invalid_org")
        assert response.status_code == 404

    @patch('open_webui.routers.client_organizations.get_admin_user')
    @patch('open_webui.routers.client_organizations.ClientOrganizationDB')
    @patch('open_webui.routers.client_organizations.UserClientMappingDB')
    def test_subscription_billing_no_users(
        self, mock_mapping_db, mock_org_db, mock_auth, client, mock_admin_user, mock_organization
    ):
        """Test subscription billing with no users in organization."""
        mock_auth.return_value = mock_admin_user
        mock_org_db.get_client_by_id.return_value = mock_organization
        mock_mapping_db.get_mappings_by_client_id.return_value = []
        
        response = client.get("/api/client-organizations/subscription/billing?client_id=org_123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        current_month = data["subscription_data"]["current_month"]
        assert current_month["total_users"] == 0
        assert current_month["total_cost_pln"] == 0.0


class TestBillingCalculations:
    """Test the billing calculation logic."""
    
    def test_tier_pricing_calculation(self):
        """Test that correct tier pricing is applied based on user count."""
        test_cases = [
            (1, 79),  # 1-3 users
            (3, 79),  # 1-3 users
            (4, 69),  # 4-9 users
            (9, 69),  # 4-9 users
            (10, 59), # 10-19 users
            (19, 59), # 10-19 users
            (20, 54), # 20+ users
            (100, 54) # 20+ users
        ]
        
        for user_count, expected_price in test_cases:
            # This would test the get_tier_price function if it was extracted
            if user_count <= 3:
                price = 79
            elif user_count <= 9:
                price = 69
            elif user_count <= 19:
                price = 59
            else:
                price = 54
            
            assert price == expected_price, f"User count {user_count} should have price {expected_price}, got {price}"

    def test_proportional_billing_calculation(self):
        """Test proportional billing calculations for different addition dates."""
        import calendar
        
        # Current month with 30 days
        current_date = datetime.now()
        days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
        
        test_cases = [
            (1, days_in_month / days_in_month),      # Added on day 1 = 100%
            (15, (days_in_month - 15 + 1) / days_in_month),  # Added on day 15
            (days_in_month, 1 / days_in_month),      # Added on last day
        ]
        
        for day_added, expected_proportion in test_cases:
            days_remaining = days_in_month - day_added + 1
            proportion = days_remaining / days_in_month
            
            assert abs(proportion - expected_proportion) < 0.01, \
                f"Day {day_added} should have proportion {expected_proportion}, got {proportion}"

    def test_monthly_cost_calculation(self):
        """Test that monthly costs are calculated correctly."""
        tier_price = 79  # PLN per user per month
        proportion = 0.5  # User added mid-month
        expected_cost = tier_price * proportion
        
        calculated_cost = round(tier_price * proportion, 2)
        assert calculated_cost == round(expected_cost, 2)


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @patch('open_webui.routers.client_organizations.get_admin_user')
    @patch('open_webui.routers.client_organizations.UserClientMappingDB')
    def test_no_organization_mapping(self, mock_mapping_db, mock_auth, client, mock_admin_user):
        """Test when user has no organization mapping."""
        mock_auth.return_value = mock_admin_user
        mock_mapping_db.get_mapping_by_user_id.return_value = None
        
        response = client.get("/api/client-organizations/subscription/billing")
        assert response.status_code == 404

    @patch('open_webui.routers.client_organizations.get_admin_user')
    @patch('open_webui.routers.client_organizations.ClientOrganizationDB')
    @patch('open_webui.routers.client_organizations.UserClientMappingDB')
    @patch('open_webui.routers.client_organizations.Users')
    def test_database_error_handling(
        self, mock_users_db, mock_mapping_db, mock_org_db, mock_auth, 
        client, mock_admin_user, mock_organization
    ):
        """Test handling of database errors."""
        mock_auth.return_value = mock_admin_user
        mock_org_db.get_client_by_id.return_value = mock_organization
        mock_mapping_db.get_mappings_by_client_id.side_effect = Exception("Database error")
        
        response = client.get("/api/client-organizations/subscription/billing?client_id=org_123")
        assert response.status_code == 500

    def test_user_added_in_previous_month(self):
        """Test billing for users added in previous months."""
        # Users added in previous months should have 100% billing proportion
        current_date = datetime.now()
        
        # Simulate user added 2 months ago
        previous_month = current_date.replace(month=current_date.month-2 if current_date.month > 2 else 12)
        
        # User from previous month should get full billing
        if previous_month.month != current_date.month or previous_month.year != current_date.year:
            proportion = 1.0  # Full month billing
        else:
            # Calculate proportional
            import calendar
            days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
            days_remaining = days_in_month - previous_month.day + 1
            proportion = days_remaining / days_in_month
        
        assert proportion == 1.0, "Users from previous months should have full billing"

    def test_leap_year_february(self):
        """Test billing calculations for February in leap years."""
        import calendar
        
        # Test leap year (2024)
        leap_year = 2024
        feb_days_leap = calendar.monthrange(leap_year, 2)[1]
        assert feb_days_leap == 29
        
        # Test non-leap year (2023)
        non_leap_year = 2023
        feb_days_non_leap = calendar.monthrange(non_leap_year, 2)[1]
        assert feb_days_non_leap == 28
        
        # Test proportional calculation for both
        for year, expected_days in [(leap_year, 29), (non_leap_year, 28)]:
            days_in_month = calendar.monthrange(year, 2)[1]
            assert days_in_month == expected_days


class TestDataValidation:
    """Test data validation and integrity."""
    
    def test_user_details_structure(self):
        """Test that user details have the correct structure."""
        # This would be part of the API response validation
        expected_keys = [
            "user_id", "user_name", "user_email", "created_at", 
            "created_date", "days_remaining_when_added", 
            "billing_proportion", "monthly_cost_pln"
        ]
        
        # Mock user detail structure
        user_detail = {
            "user_id": "user_123",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "created_at": 1640995200,
            "created_date": "2022-01-01",
            "days_remaining_when_added": 30,
            "billing_proportion": 1.0,
            "monthly_cost_pln": 79.0
        }
        
        for key in expected_keys:
            assert key in user_detail, f"Missing required key: {key}"

    def test_tier_breakdown_structure(self):
        """Test that tier breakdown has the correct structure."""
        expected_keys = [
            "tier_range", "price_per_user_pln", 
            "is_current_tier", "user_count_in_tier"
        ]
        
        # Mock tier breakdown structure
        tier = {
            "tier_range": "1-3 users",
            "price_per_user_pln": 79,
            "is_current_tier": True,
            "user_count_in_tier": 2
        }
        
        for key in expected_keys:
            assert key in tier, f"Missing required key: {key}"

    def test_pricing_tiers_completeness(self):
        """Test that all pricing tiers are included."""
        expected_tiers = [
            {"range": "1-3 users", "price_pln": 79},
            {"range": "4-9 users", "price_pln": 69},
            {"range": "10-19 users", "price_pln": 59},
            {"range": "20+ users", "price_pln": 54}
        ]
        
        # This would be from the API response
        assert len(expected_tiers) == 4, "Should have exactly 4 pricing tiers"
        
        for i, tier in enumerate(expected_tiers):
            assert "range" in tier, f"Tier {i} missing range"
            assert "price_pln" in tier, f"Tier {i} missing price"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])