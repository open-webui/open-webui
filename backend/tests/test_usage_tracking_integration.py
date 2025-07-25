"""
Integration Tests for Usage Tracking System
Tests the end-to-end data flow for "Today's Tokens (live)" functionality
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
import time

from open_webui.models.organization_usage import (
    ClientOrganizationDB, ClientUsageDB, UserClientMappingDB,
    ClientDailyUsage, ClientLiveCounters, ClientOrganizationForm,
    UserClientMappingForm, get_db
)
from open_webui.utils.background_sync import OpenRouterUsageSync
from open_webui.routers.usage_tracking import record_usage_to_db


class TestUsageTrackingIntegration:
    """Integration tests for usage tracking system"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test data for each test"""
        with get_db() as db:
            # Clean up any existing test data
            db.query(ClientLiveCounters).filter(
                ClientLiveCounters.client_org_id.like('test_%')
            ).delete()
            db.query(ClientDailyUsage).filter(
                ClientDailyUsage.client_org_id.like('test_%')
            ).delete()
            db.commit()
            
        # Create test organization
        org_form = ClientOrganizationForm(
            name="Test Organization",
            markup_rate=1.3,
            monthly_limit=1000.0,
            billing_email="test@example.com"
        )
        
        self.test_client = ClientOrganizationDB.create_client(
            client_form=org_form,
            api_key="sk-test-key-12345",
            key_hash="test_hash"
        )
        
        # Create test user mapping
        mapping_form = UserClientMappingForm(
            user_id="test_user_123",
            client_org_id=self.test_client.id,
            openrouter_user_id="openrouter_test_user"
        )
        
        self.test_mapping = UserClientMappingDB.create_mapping(mapping_form)
        
        yield
        
        # Cleanup after test
        with get_db() as db:
            db.query(ClientLiveCounters).filter(
                ClientLiveCounters.client_org_id == self.test_client.id
            ).delete()
            db.query(ClientDailyUsage).filter(
                ClientDailyUsage.client_org_id == self.test_client.id
            ).delete()
            db.commit()

    def test_background_sync_updates_live_counters(self):
        """Test that background sync properly updates live counters for today's data"""
        sync_manager = OpenRouterUsageSync()
        
        # Mock OpenRouter generation data for today
        mock_generations = [
            {
                "id": "gen_test_001",
                "created_at": datetime.now().isoformat() + "Z",
                "model": "anthropic/claude-3.5-sonnet",
                "total_tokens": 1500,
                "total_cost": 0.045  # $0.045
            },
            {
                "id": "gen_test_002", 
                "created_at": datetime.now().isoformat() + "Z",
                "model": "openai/gpt-4",
                "total_tokens": 800,
                "total_cost": 0.024  # $0.024
            }
        ]
        
        # Record usage via background sync
        result = sync_manager.record_usage_batch_to_db(
            client_org_id=self.test_client.id,
            generations=mock_generations
        )
        
        # Verify batch recording succeeded
        assert result["processed"] == 2
        assert result["total_tokens"] == 2300
        assert result["total_cost"] == (0.045 + 0.024) * 1.3  # With markup
        
        # Verify live counter was updated
        stats = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        assert stats.today["tokens"] == 2300
        assert stats.today["requests"] == 2
        assert abs(stats.today["cost"] - ((0.045 + 0.024) * 1.3)) < 0.001
        assert "Created from daily summary" in stats.today["last_updated"] or ":" in stats.today["last_updated"]

    def test_fallback_logic_restores_from_daily_summary(self):
        """Test that live counters are restored from daily summaries when stale/missing"""
        
        # First, create a daily summary for today (simulating background sync)
        today = date.today()
        
        with get_db() as db:
            daily_summary = ClientDailyUsage(
                id=f"{self.test_client.id}_{today.isoformat()}",
                client_org_id=self.test_client.id,
                usage_date=today,
                total_tokens=3500,
                total_requests=5,
                raw_cost=0.105,
                markup_cost=0.1365,  # 0.105 * 1.3
                primary_model="anthropic/claude-3.5-sonnet",
                unique_users=1,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            db.add(daily_summary)
            
            # Create a stale live counter (yesterday's date)
            yesterday = today - timedelta(days=1)
            stale_counter = ClientLiveCounters(
                client_org_id=self.test_client.id,
                current_date=yesterday,
                today_tokens=1000,
                today_requests=2,
                today_raw_cost=0.03,
                today_markup_cost=0.039,
                last_updated=int(time.time()) - 86400  # 24 hours ago
            )
            db.add(stale_counter)
            db.commit()
        
        # Now get usage stats - should trigger fallback logic
        stats = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        # Verify fallback restored today's data from daily summary
        assert stats.today["tokens"] == 3500
        assert stats.today["requests"] == 5
        assert abs(stats.today["cost"] - 0.1365) < 0.001
        assert "Restored from daily summary" in stats.today["last_updated"]
        
        # Verify live counter was updated to today
        with get_db() as db:
            updated_counter = db.query(ClientLiveCounters).filter_by(
                client_org_id=self.test_client.id
            ).first()
            
            assert updated_counter.current_date == today
            assert updated_counter.today_tokens == 3500

    def test_consolidated_manual_recording(self):
        """Test that manual recording uses consolidated ORM approach and updates live counters"""
        
        # Test the consolidated record_usage_to_db function
        usage_data = {
            "model": "google/gemini-pro",
            "total_tokens": 2000,
            "total_cost": 0.06
        }
        
        record_usage_to_db(
            client_org_id=self.test_client.id,
            usage_data=usage_data,
            external_user="manual_test"
        )
        
        # Verify data was recorded correctly
        stats = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        assert stats.today["tokens"] == 2000
        assert stats.today["requests"] == 1
        assert abs(stats.today["cost"] - (0.06 * 1.3)) < 0.001
        
        # Verify both daily summary and live counter were created
        with get_db() as db:
            daily_summary = db.query(ClientDailyUsage).filter_by(
                client_org_id=self.test_client.id,
                usage_date=date.today()
            ).first()
            
            live_counter = db.query(ClientLiveCounters).filter_by(
                client_org_id=self.test_client.id
            ).first()
            
            assert daily_summary is not None
            assert daily_summary.total_tokens == 2000
            
            assert live_counter is not None
            assert live_counter.today_tokens == 2000
            assert live_counter.current_date == date.today()

    def test_missing_live_counter_creation(self):
        """Test that missing live counters are created from daily summaries"""
        
        # Create only a daily summary, no live counter
        today = date.today()
        
        with get_db() as db:
            daily_summary = ClientDailyUsage(
                id=f"{self.test_client.id}_{today.isoformat()}",
                client_org_id=self.test_client.id,
                usage_date=today,
                total_tokens=1200,
                total_requests=3,
                raw_cost=0.036,
                markup_cost=0.0468,
                primary_model="openai/gpt-4",
                unique_users=1,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            db.add(daily_summary)
            db.commit()
        
        # Get usage stats - should create live counter from daily summary
        stats = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        # Verify live counter was created with correct data
        assert stats.today["tokens"] == 1200
        assert stats.today["requests"] == 3
        assert abs(stats.today["cost"] - 0.0468) < 0.001
        assert "Created from daily summary" in stats.today["last_updated"]
        
        # Verify live counter exists in database
        with get_db() as db:
            live_counter = db.query(ClientLiveCounters).filter_by(
                client_org_id=self.test_client.id
            ).first()
            
            assert live_counter is not None
            assert live_counter.today_tokens == 1200
            assert live_counter.current_date == today

    def test_real_time_refresh_accuracy(self):
        """Test that 30-second refresh returns accurate data"""
        
        # Record some initial usage
        ClientUsageDB.record_usage(
            client_org_id=self.test_client.id,
            user_id="test_user_123",
            openrouter_user_id="openrouter_test_user",
            model_name="anthropic/claude-3.5-sonnet",
            usage_date=date.today(),
            input_tokens=1000,
            output_tokens=500,
            raw_cost=0.045,
            markup_cost=0.0585,
            provider="anthropic"
        )
        
        # Get stats (simulating frontend API call)
        stats_1 = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        initial_tokens = stats_1.today["tokens"]
        initial_cost = stats_1.today["cost"]
        
        # Record additional usage (simulating new API call)
        ClientUsageDB.record_usage(
            client_org_id=self.test_client.id,
            user_id="test_user_123",
            openrouter_user_id="openrouter_test_user", 
            model_name="openai/gpt-4",
            usage_date=date.today(),
            input_tokens=800,
            output_tokens=200,
            raw_cost=0.030,
            markup_cost=0.039,
            provider="openai"
        )
        
        # Get updated stats (simulating next 30-second refresh)
        stats_2 = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        # Verify incremental updates work correctly
        assert stats_2.today["tokens"] == initial_tokens + 1000  # 800 + 200
        assert abs(stats_2.today["cost"] - (initial_cost + 0.039)) < 0.001
        assert stats_2.today["requests"] == 2

    def test_month_totals_include_today(self):
        """Test that monthly totals correctly include today's live data"""
        
        # Create some historical data for this month
        current_month = date.today().replace(day=1)
        yesterday = date.today() - timedelta(days=1)
        
        with get_db() as db:
            # Historical daily summary
            historical_summary = ClientDailyUsage(
                id=f"{self.test_client.id}_{yesterday.isoformat()}",
                client_org_id=self.test_client.id,
                usage_date=yesterday,
                total_tokens=5000,
                total_requests=8,
                raw_cost=0.15,
                markup_cost=0.195,
                primary_model="anthropic/claude-3.5-sonnet",
                unique_users=1,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            db.add(historical_summary)
            db.commit()
        
        # Record today's usage
        ClientUsageDB.record_usage(
            client_org_id=self.test_client.id,
            user_id="test_user_123",
            openrouter_user_id="openrouter_test_user",
            model_name="google/gemini-pro",
            usage_date=date.today(),
            input_tokens=1500,
            output_tokens=500,
            raw_cost=0.06,
            markup_cost=0.078,
            provider="google"
        )
        
        # Get usage stats
        stats = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        # Verify monthly totals include both historical and today's data
        expected_month_tokens = 5000 + 2000  # Historical + today
        expected_month_cost = 0.195 + 0.078  # Historical + today
        expected_requests = 8 + 1  # Historical + today
        
        assert stats.this_month["tokens"] == expected_month_tokens
        assert abs(stats.this_month["cost"] - expected_month_cost) < 0.001
        assert stats.this_month["requests"] == expected_requests
        assert stats.this_month["days_active"] == 2  # Yesterday + today

    @pytest.mark.asyncio
    async def test_background_sync_concurrent_safety(self):
        """Test that concurrent background sync operations are handled safely"""
        
        sync_manager = OpenRouterUsageSync()
        
        # Create multiple concurrent sync operations
        mock_generations_1 = [
            {
                "id": "gen_concurrent_001",
                "created_at": datetime.now().isoformat() + "Z",
                "model": "anthropic/claude-3.5-sonnet",
                "total_tokens": 1000,
                "total_cost": 0.03
            }
        ]
        
        mock_generations_2 = [
            {
                "id": "gen_concurrent_002", 
                "created_at": datetime.now().isoformat() + "Z",
                "model": "openai/gpt-4",
                "total_tokens": 1500,
                "total_cost": 0.045
            }
        ]
        
        # Run concurrent operations
        tasks = [
            asyncio.create_task(asyncio.get_event_loop().run_in_executor(
                None, sync_manager.record_usage_batch_to_db, 
                self.test_client.id, mock_generations_1
            )),
            asyncio.create_task(asyncio.get_event_loop().run_in_executor(
                None, sync_manager.record_usage_batch_to_db,
                self.test_client.id, mock_generations_2  
            ))
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify both operations succeeded
        assert all(r["processed"] == 1 for r in results)
        
        # Verify final state is consistent
        stats = ClientUsageDB.get_usage_stats_by_client(self.test_client.id)
        
        assert stats.today["tokens"] == 2500  # 1000 + 1500
        assert stats.today["requests"] == 2
        assert abs(stats.today["cost"] - ((0.03 + 0.045) * 1.3)) < 0.001


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])