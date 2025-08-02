"""
Test Helpers for E2E Usage Processing Tests
Provides utilities for webhook generation, database verification, and API testing
"""
import sys
import os

# Dodaj główny folder 'backend' do ścieżki Pythona, aby importy działały.
# To jest bezpośrednie rozwiązanie problemu z 'No module named open_webui'.
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import asyncio
import json
import hmac
import hashlib
import httpx
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal
import uuid
import logging
from pathlib import Path
from fastapi.testclient import TestClient
import sys

# Add the backend directory to Python path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)

# Delay FastAPI app import to avoid early database initialization
app = None

def get_test_app():
    """Lazy load the FastAPI app for testing"""
    global app
    if app is None:
        try:
            import os
            from pathlib import Path
            from unittest.mock import patch
            
            # Set test database before importing app
            os.environ.setdefault("DATABASE_URL", "sqlite:///test_usage_e2e.db")
            os.environ.setdefault("ENVIRONMENT", "test")
            os.environ.setdefault("WEBUI_AUTH", "false")  # Disable auth for testing
            
            # Mock database initialization to avoid peewee migration issues
            with patch('open_webui.internal.db.handle_peewee_migration'):
                from open_webui.main import app as _app
                app = _app
        except ImportError as e:
            logger.error(f"Could not import FastAPI app: {e}")
            raise
    return app


class WebhookTestGenerator:
    """Generate test webhook payloads for E2E testing"""
    
    def __init__(self, webhook_secret: str = "test-webhook-secret"):
        self.webhook_secret = webhook_secret
        self.default_api_key = "sk-or-test-e2e-" + "x" * 40
        self.default_user = "test.user@company.com"
    
    def generate_usage_payload(
        self,
        tokens: int,
        cost: float,
        model: str = "gpt-4-turbo",
        api_key: Optional[str] = None,
        user_email: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate a single webhook payload for testing"""
        
        return {
            "api_key": api_key or self.default_api_key,
            "model": model,
            "tokens_used": tokens,
            "cost": cost,
            "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
            "external_user": user_email or self.default_user,
            "request_id": f"test-req-{uuid.uuid4()}"
        }
    
    def generate_batch_for_total(
        self,
        total_tokens: int,
        total_cost: float,
        num_requests: int = 5,
        model: str = "gpt-4-turbo",
        api_key: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Generate multiple webhook payloads that sum to specific totals"""
        
        payloads = []
        base_timestamp = timestamp or datetime.now(timezone.utc)
        
        # Distribute tokens and cost across requests
        tokens_per_request = total_tokens // num_requests
        cost_per_request = total_cost / num_requests
        
        for i in range(num_requests):
            # Add remainder to last request to ensure exact totals
            if i == num_requests - 1:
                final_tokens = total_tokens - (tokens_per_request * (num_requests - 1))
                final_cost = total_cost - (cost_per_request * (num_requests - 1))
            else:
                final_tokens = tokens_per_request
                final_cost = cost_per_request
            
            # Slight time offset for each request
            request_timestamp = base_timestamp.replace(
                second=base_timestamp.second + i,
                microsecond=i * 100000
            )
            
            payload = self.generate_usage_payload(
                tokens=final_tokens,
                cost=round(final_cost, 6),
                model=model,
                api_key=api_key,
                timestamp=request_timestamp
            )
            
            payloads.append(payload)
        
        return payloads
    
    def generate_signature(self, payload: Dict[str, Any]) -> str:
        """Generate OpenRouter webhook signature"""
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def create_webhook_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Create complete webhook headers with signature"""
        return {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": self.generate_signature(payload),
            "X-OpenRouter-Timestamp": str(int(datetime.now().timestamp()))
        }


class DatabaseVerifier:
    """Utilities for verifying database state during tests"""
    
    def __init__(self):
        pass
    
    async def verify_sqlite_usage_data(
        self,
        client_org_id: str,
        expected_date: date,
        expected_tokens: int,
        expected_cost_usd: float,
        expected_cost_pln: Optional[float] = None
    ) -> Dict[str, Any]:
        """Verify usage data in SQLite database"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.usage_tracking.models.database import ClientDailyUsageDB
            
            db = next(get_db())
            
            # Query for the specific date and client
            records = db.query(ClientDailyUsageDB).filter_by(
                client_org_id=client_org_id,
                usage_date=expected_date
            ).all()
            
            if not records:
                return {
                    "success": False,
                    "error": "No records found in SQLite",
                    "expected_date": expected_date.isoformat(),
                    "client_org_id": client_org_id
                }
            
            # Aggregate totals
            total_tokens = sum(record.total_tokens for record in records)
            total_cost_usd = sum(float(record.total_cost) for record in records)
            total_cost_pln = None
            
            if any(record.total_cost_pln for record in records):
                total_cost_pln = sum(
                    float(record.total_cost_pln) 
                    for record in records 
                    if record.total_cost_pln
                )
            
            # Verify expectations
            verification = {
                "success": True,
                "found_records": len(records),
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost_usd,
                "total_cost_pln": total_cost_pln,
                "tokens_match": total_tokens == expected_tokens,
                "cost_usd_match": abs(total_cost_usd - expected_cost_usd) < 0.01,
                "cost_pln_match": None
            }
            
            if expected_cost_pln is not None and total_cost_pln is not None:
                verification["cost_pln_match"] = abs(total_cost_pln - expected_cost_pln) < 0.01
            
            return verification
            
        except Exception as e:
            logger.error(f"SQLite verification error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            try:
                db.close()
            except:
                pass
    
    async def verify_exchange_rate_stored(
        self,
        rate_date: date,
        expected_rate: float
    ) -> Dict[str, Any]:
        """Verify exchange rate is stored in database"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.usage_tracking.models.database import DailyExchangeRateDB
            
            db = next(get_db())
            
            rate_record = db.query(DailyExchangeRateDB).filter_by(
                date=rate_date,
                currency_from="USD",
                currency_to="PLN"
            ).first()
            
            if not rate_record:
                return {
                    "success": False,
                    "error": "Exchange rate not found in database",
                    "date": rate_date.isoformat()
                }
            
            stored_rate = float(rate_record.rate)
            rate_match = abs(stored_rate - expected_rate) < 0.01
            
            return {
                "success": True,
                "stored_rate": stored_rate,
                "expected_rate": expected_rate,
                "rate_match": rate_match,
                "source": rate_record.source,
                "created_at": rate_record.created_at.isoformat() if rate_record.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Exchange rate verification error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            try:
                db.close()
            except:
                pass
    
    async def clean_test_data(self, client_org_id: str):
        """Clean up test data from database"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.usage_tracking.models.database import (
                ClientDailyUsageDB, 
                ClientUserDailyUsageDB,
                DailyExchangeRateDB
            )
            
            db = next(get_db())
            
            # Delete usage records
            db.query(ClientDailyUsageDB).filter_by(client_org_id=client_org_id).delete()
            db.query(ClientUserDailyUsageDB).filter_by(client_org_id=client_org_id).delete()
            
            # Delete test exchange rates (be careful not to delete production data)
            test_dates = [
                date(2025, 7, 31),
                date(2025, 8, 1),
                date(2025, 8, 2)
            ]
            
            for test_date in test_dates:
                db.query(DailyExchangeRateDB).filter_by(
                    date=test_date,
                    currency_from="USD",
                    currency_to="PLN"
                ).delete()
            
            db.commit()
            logger.info(f"Cleaned test data for client {client_org_id}")
            
        except Exception as e:
            logger.error(f"Test data cleanup error: {e}")
            try:
                db.rollback()
            except:
                pass
        finally:
            try:
                db.close()
            except:
                pass


class APITestClient:
    """HTTP client for testing API endpoints using FastAPI TestClient"""
    
    def __init__(self):
        from unittest.mock import patch, AsyncMock
        
        test_app = get_test_app()
        if test_app is None:
            raise RuntimeError("FastAPI app not available for testing")
        
        # Mock webhook service to avoid database dependencies
        self.webhook_service_patcher = patch('open_webui.usage_tracking.services.webhook_service.WebhookService')
        mock_service_class = self.webhook_service_patcher.start()
        mock_instance = AsyncMock()
        mock_instance.process_webhook = AsyncMock(return_value={"status": "success"})
        mock_service_class.return_value = mock_instance
        
        self.client = TestClient(test_app)
    
    def cleanup(self):
        """Clean up mocks"""
        try:
            self.webhook_service_patcher.stop()
        except:
            pass
    
    def send_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send webhook to the API endpoint"""
        try:
            logger.debug(f"Sending webhook to /api/v1/usage-tracking/webhook/openrouter-usage with payload: {payload}")
            response = self.client.post(
                "/api/v1/usage-tracking/webhook/openrouter-usage",
                json=payload,
                headers=headers
            )
            
            logger.debug(f"Response status: {response.status_code}, headers: {response.headers}")
            
            return {
                "status_code": response.status_code,
                "response": response.json() if response.status_code < 500 else {"error": response.text},
                "success": response.status_code == 200
            }
            
        except Exception as e:
            logger.error(f"Webhook send error: {e}")
            return {
                "status_code": 0,
                "response": {"error": str(e)},
                "success": False
            }
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get organization usage summary"""
        try:
            response = self.client.get("/api/v1/usage-tracking/my-organization/usage-summary")
            
            return {
                "status_code": response.status_code,
                "response": response.json() if response.status_code < 500 else {"error": response.text},
                "success": response.status_code == 200
            }
            
        except Exception as e:
            return {
                "status_code": 0,
                "response": {"error": str(e)},
                "success": False
            }
    
    def trigger_manual_batch(self, processing_date: str) -> Dict[str, Any]:
        """Trigger manual batch processing (if endpoint exists)"""
        try:
            # This endpoint might need to be created for testing
            response = self.client.post(
                "/api/v1/usage-tracking/admin/trigger-batch",
                json={"processing_date": processing_date}
            )
            
            return {
                "status_code": response.status_code,
                "response": response.json() if response.status_code < 500 else {"error": response.text},
                "success": response.status_code == 200
            }
            
        except Exception as e:
            return {
                "status_code": 0,
                "response": {"error": str(e)},
                "success": False
            }


class TestDatabaseSetup:
    """Setup test database and client organizations"""
    
    def __init__(self):
        self.test_client_id = "test-e2e-client-001"
        self.test_api_key = "sk-or-test-e2e-" + "x" * 40
    
    async def setup_test_client(self) -> Dict[str, Any]:
        """Create test client organization"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            db = next(get_db())
            
            # Check if test client already exists
            existing_client = db.query(ClientOrganizationDB).filter_by(
                id=self.test_client_id
            ).first()
            
            if existing_client:
                logger.info(f"Test client {self.test_client_id} already exists")
                return {
                    "success": True,
                    "client_id": self.test_client_id,
                    "api_key": self.test_api_key,
                    "exists": True
                }
            
            # Create new test client
            test_client = ClientOrganizationDB(
                id=self.test_client_id,
                name="E2E Test Organization",
                api_key=self.test_api_key,
                markup_rate=1.3,  # 30% markup
                is_active=True
            )
            
            db.add(test_client)
            db.commit()
            
            logger.info(f"Created test client {self.test_client_id}")
            
            return {
                "success": True,
                "client_id": self.test_client_id,
                "api_key": self.test_api_key,
                "exists": False
            }
            
        except Exception as e:
            logger.error(f"Test client setup error: {e}")
            try:
                db.rollback()
            except:
                pass
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            try:
                db.close()
            except:
                pass
    
    async def cleanup_test_client(self):
        """Remove test client organization"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            db = next(get_db())
            
            # Delete test client
            db.query(ClientOrganizationDB).filter_by(
                id=self.test_client_id
            ).delete()
            
            db.commit()
            logger.info(f"Cleaned up test client {self.test_client_id}")
            
        except Exception as e:
            logger.error(f"Test client cleanup error: {e}")
            try:
                db.rollback()
            except:
                pass
        finally:
            try:
                db.close()
            except:
                pass
    
    def cleanup_all_data(self):
        """Synchronous cleanup of all test data for setup_method use"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.usage_tracking.models.database import (
                ClientDailyUsageDB, 
                ClientUserDailyUsageDB,
                DailyExchangeRateDB
            )
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            db = next(get_db())
            
            # Delete test usage records
            db.query(ClientDailyUsageDB).filter_by(client_org_id=self.test_client_id).delete()
            db.query(ClientUserDailyUsageDB).filter_by(client_org_id=self.test_client_id).delete()
            
            # Delete test exchange rates (dates from 2025 are probably test data)
            from datetime import date
            test_dates = [
                date(2025, 7, 31),
                date(2025, 8, 1),
                date(2025, 8, 2)
            ]
            
            for test_date in test_dates:
                db.query(DailyExchangeRateDB).filter_by(
                    date=test_date,
                    currency_from="USD",
                    currency_to="PLN"
                ).delete()
            
            # Delete test client
            db.query(ClientOrganizationDB).filter_by(
                id=self.test_client_id
            ).delete()
            
            db.commit()
            logger.info(f"Cleaned all test data for client {self.test_client_id}")
            
        except ImportError as e:
            # Fallback for test environments without full backend
            logger.warning(f"Database modules not available for cleanup, using fallback: {e}")
            logger.info("Test data cleanup skipped (no database available)")
            
        except Exception as e:
            logger.error(f"Test data cleanup error: {e}")
            try:
                db.rollback()
            except:
                pass
        finally:
            try:
                db.close()
            except:
                pass
    
    def create_test_organization(self, name: str = "E2E Test Org", api_key_prefix: str = "test_e2e") -> Dict[str, Any]:
        """Synchronous creation of test organization for setup_method use"""
        try:
            from open_webui.utils.database import get_db
            from open_webui.models.organization_usage import ClientOrganizationDB
            import uuid
            
            db = next(get_db())
            
            # Generate unique IDs for this test run
            unique_suffix = str(uuid.uuid4())[:8]
            client_id = f"{api_key_prefix}-client-{unique_suffix}"
            api_key = f"sk-or-{api_key_prefix}-{unique_suffix}-" + "x" * 20
            
            # Create new test client
            test_client = ClientOrganizationDB(
                id=client_id,
                name=name,
                api_key=api_key,
                markup_rate=1.3,  # 30% markup
                is_active=True
            )
            
            db.add(test_client)
            db.commit()
            
            # Update instance variables for later cleanup
            self.test_client_id = client_id
            self.test_api_key = api_key
            
            logger.info(f"Created test organization: {name} (ID: {client_id})")
            
            return {
                "success": True,
                "client_id": client_id,
                "api_key": api_key,
                "name": name
            }
            
        except ImportError as e:
            # Fallback for test environments without full backend
            logger.warning(f"Database modules not available, using fallback: {e}")
            import uuid
            
            unique_suffix = str(uuid.uuid4())[:8]
            client_id = f"{api_key_prefix}-client-{unique_suffix}"
            api_key = f"sk-or-{api_key_prefix}-{unique_suffix}-" + "x" * 20
            
            # Update instance variables for later cleanup
            self.test_client_id = client_id
            self.test_api_key = api_key
            
            logger.info(f"Created fallback test organization: {name} (ID: {client_id})")
            
            return {
                "success": True,
                "client_id": client_id,
                "api_key": api_key,
                "name": name,
                "fallback": True
            }
            
        except Exception as e:
            logger.error(f"Test organization creation error: {e}")
            try:
                db.rollback()
            except:
                pass
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            try:
                db.close()
            except:
                pass


if __name__ == "__main__":
    # Test the helper utilities
    async def test_helpers():
        print("Testing E2E helpers...")
        
        # Test webhook generation
        generator = WebhookTestGenerator()
        payloads = generator.generate_batch_for_total(
            total_tokens=100000,
            total_cost=0.15,
            num_requests=3
        )
        
        print(f"Generated {len(payloads)} payloads")
        print(f"Total tokens: {sum(p['tokens_used'] for p in payloads)}")
        print(f"Total cost: {sum(p['cost'] for p in payloads):.6f}")
        
        # Test signature generation
        signature = generator.generate_signature(payloads[0])
        print(f"Signature length: {len(signature)}")
        
        print("E2E helpers test completed!")
    
    asyncio.run(test_helpers())