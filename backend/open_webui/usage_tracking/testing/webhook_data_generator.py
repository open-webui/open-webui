"""
Webhook Data Generator for Testing
Generates realistic OpenRouter webhook payloads for testing InfluxDB integration
"""

import random
import json
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal
import uuid

class WebhookDataGenerator:
    """Generate realistic OpenRouter webhook data for testing"""
    
    # Model configurations with realistic token/cost ratios
    MODELS = {
        "gpt-4": {
            "input_token_price": 0.00003,  # $0.03 per 1K tokens
            "output_token_price": 0.00006,  # $0.06 per 1K tokens
            "avg_input_tokens": (100, 2000),
            "avg_output_tokens": (200, 1500),
        },
        "gpt-4-turbo": {
            "input_token_price": 0.00001,  # $0.01 per 1K tokens
            "output_token_price": 0.00003,  # $0.03 per 1K tokens
            "avg_input_tokens": (100, 2000),
            "avg_output_tokens": (200, 1500),
        },
        "gpt-3.5-turbo": {
            "input_token_price": 0.0000005,  # $0.0005 per 1K tokens
            "output_token_price": 0.0000015,  # $0.0015 per 1K tokens
            "avg_input_tokens": (50, 1000),
            "avg_output_tokens": (100, 800),
        },
        "claude-3-opus": {
            "input_token_price": 0.000015,  # $0.015 per 1K tokens
            "output_token_price": 0.000075,  # $0.075 per 1K tokens
            "avg_input_tokens": (100, 3000),
            "avg_output_tokens": (200, 2000),
        },
        "claude-3-sonnet": {
            "input_token_price": 0.000003,  # $0.003 per 1K tokens
            "output_token_price": 0.000015,  # $0.015 per 1K tokens
            "avg_input_tokens": (100, 2000),
            "avg_output_tokens": (200, 1500),
        },
        "claude-3-haiku": {
            "input_token_price": 0.00000025,  # $0.00025 per 1K tokens
            "output_token_price": 0.00000125,  # $0.00125 per 1K tokens
            "avg_input_tokens": (50, 1000),
            "avg_output_tokens": (100, 800),
        },
        "gemini-pro": {
            "input_token_price": 0.000001,  # $0.001 per 1K tokens
            "output_token_price": 0.000002,  # $0.002 per 1K tokens
            "avg_input_tokens": (100, 1500),
            "avg_output_tokens": (150, 1200),
        },
        "mixtral-8x7b": {
            "input_token_price": 0.0000007,  # $0.0007 per 1K tokens
            "output_token_price": 0.0000007,  # $0.0007 per 1K tokens
            "avg_input_tokens": (100, 1000),
            "avg_output_tokens": (150, 800),
        }
    }
    
    # Sample user emails for testing
    USER_EMAILS = [
        "john.doe@company.com",
        "jane.smith@company.com",
        "alice.johnson@company.com",
        "bob.wilson@company.com",
        "charlie.brown@company.com",
        "diana.prince@company.com",
        "edward.norton@company.com",
        "fiona.apple@company.com",
        "george.martin@company.com",
        "helen.mirren@company.com",
        "admin@company.com",
        "test.user@company.com"
    ]
    
    # API keys for different organizations
    API_KEYS = {
        "test-org-001": "sk-or-test-001-" + "x" * 40,
        "test-org-002": "sk-or-test-002-" + "x" * 40,
        "test-org-003": "sk-or-test-003-" + "x" * 40,
        "demo-client": "sk-or-demo-" + "x" * 44,
    }
    
    def __init__(self, webhook_secret: str = "test-webhook-secret"):
        self.webhook_secret = webhook_secret
        
    def generate_webhook_payload(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        user_email: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a single webhook payload
        
        Args:
            model: Specific model to use (random if None)
            api_key: Specific API key (random if None)
            user_email: Specific user email (random if None)
            timestamp: Specific timestamp (current if None)
            request_id: Specific request ID (generated if None)
            
        Returns:
            Complete webhook payload
        """
        # Select random values if not provided
        if not model:
            model = random.choice(list(self.MODELS.keys()))
        
        if not api_key:
            api_key = random.choice(list(self.API_KEYS.values()))
            
        if not user_email:
            user_email = random.choice(self.USER_EMAILS)
            
        if not timestamp:
            timestamp = datetime.now(timezone.utc)
            
        if not request_id:
            request_id = f"req-{uuid.uuid4()}"
        
        # Get model configuration
        model_config = self.MODELS[model]
        
        # Generate token counts
        input_tokens = random.randint(*model_config["avg_input_tokens"])
        output_tokens = random.randint(*model_config["avg_output_tokens"])
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        input_cost = (input_tokens / 1000) * model_config["input_token_price"]
        output_cost = (output_tokens / 1000) * model_config["output_token_price"]
        total_cost = round(input_cost + output_cost, 6)
        
        # Generate latency (realistic range: 500ms - 5000ms)
        latency_ms = random.randint(500, 5000)
        
        # Create payload
        payload = {
            "api_key": api_key,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_used": total_tokens,  # Legacy field for compatibility
            "cost": total_cost,
            "timestamp": timestamp.isoformat(),
            "external_user": user_email,
            "request_id": request_id,
            "latency_ms": latency_ms,
            "status": "success",
            "metadata": {
                "source": "webhook_generator",
                "version": "1.0",
                "test_mode": True
            }
        }
        
        return payload
    
    def generate_webhook_signature(self, payload: Dict[str, Any]) -> str:
        """
        Generate OpenRouter webhook signature
        
        Args:
            payload: Webhook payload
            
        Returns:
            HMAC-SHA256 signature
        """
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def generate_batch(
        self,
        count: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        models: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        user_pattern: str = "random"
    ) -> List[Dict[str, Any]]:
        """
        Generate a batch of webhook payloads
        
        Args:
            count: Number of payloads to generate
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            models: List of models to use (default: all)
            api_key: Specific API key to use
            user_pattern: User selection pattern ('random', 'sequential', 'weighted')
            
        Returns:
            List of webhook payloads
        """
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        if not end_time:
            end_time = datetime.now(timezone.utc)
            
        if not models:
            models = list(self.MODELS.keys())
        
        payloads = []
        time_range = (end_time - start_time).total_seconds()
        
        # User selection based on pattern
        if user_pattern == "weighted":
            # Some users are more active than others
            user_weights = [10, 8, 6, 5, 4, 3, 2, 2, 1, 1, 1, 1]
            weighted_users = random.choices(
                self.USER_EMAILS,
                weights=user_weights[:len(self.USER_EMAILS)],
                k=count
            )
        
        for i in range(count):
            # Distribute timestamps evenly across the time range
            offset_seconds = random.uniform(0, time_range)
            timestamp = start_time + timedelta(seconds=offset_seconds)
            
            # Select model (can be weighted for realism)
            if random.random() < 0.6:  # 60% chance of popular models
                model = random.choice(["gpt-4-turbo", "gpt-3.5-turbo", "claude-3-sonnet"])
            else:
                model = random.choice(models)
            
            # Select user based on pattern
            if user_pattern == "sequential":
                user_email = self.USER_EMAILS[i % len(self.USER_EMAILS)]
            elif user_pattern == "weighted":
                user_email = weighted_users[i]
            else:  # random
                user_email = random.choice(self.USER_EMAILS)
            
            payload = self.generate_webhook_payload(
                model=model,
                api_key=api_key,
                user_email=user_email,
                timestamp=timestamp
            )
            
            payloads.append(payload)
        
        # Sort by timestamp for realistic ordering
        payloads.sort(key=lambda x: x["timestamp"])
        
        return payloads
    
    def generate_burst_traffic(
        self,
        burst_size: int = 50,
        burst_duration_seconds: int = 60,
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate burst traffic pattern (simulating high load)
        
        Args:
            burst_size: Number of requests in burst
            burst_duration_seconds: Duration of burst
            api_key: Specific API key
            
        Returns:
            List of webhook payloads
        """
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(seconds=burst_duration_seconds)
        
        # Use fewer users during burst (simulating specific workload)
        burst_users = random.sample(self.USER_EMAILS, min(3, len(self.USER_EMAILS)))
        
        payloads = []
        for i in range(burst_size):
            # Exponential distribution for burst timing
            offset_seconds = random.expovariate(burst_size / burst_duration_seconds)
            offset_seconds = min(offset_seconds, burst_duration_seconds)
            
            timestamp = start_time + timedelta(seconds=offset_seconds)
            
            payload = self.generate_webhook_payload(
                model=random.choice(["gpt-4-turbo", "gpt-3.5-turbo"]),  # Fast models for burst
                api_key=api_key,
                user_email=random.choice(burst_users),
                timestamp=timestamp
            )
            
            payloads.append(payload)
        
        return sorted(payloads, key=lambda x: x["timestamp"])
    
    def generate_error_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate webhook payloads with various error scenarios
        
        Returns:
            List of error scenario payloads
        """
        scenarios = []
        
        # Scenario 1: Missing required fields
        scenarios.append({
            "model": "gpt-4",
            "tokens_used": 1000,
            "cost": 0.03,
            "timestamp": datetime.now(timezone.utc).isoformat()
            # Missing api_key
        })
        
        # Scenario 2: Invalid cost (negative)
        scenarios.append({
            "api_key": "sk-test-invalid",
            "model": "gpt-4",
            "tokens_used": 1000,
            "cost": -0.03,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Scenario 3: Extremely high token count
        scenarios.append({
            "api_key": "sk-test-high",
            "model": "gpt-4",
            "tokens_used": 1000000,  # 1M tokens
            "cost": 30.0,  # $30
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Scenario 4: Invalid timestamp format
        scenarios.append({
            "api_key": "sk-test-time",
            "model": "gpt-3.5-turbo",
            "tokens_used": 500,
            "cost": 0.001,
            "timestamp": "2024-01-30 10:30:00"  # Missing timezone
        })
        
        # Scenario 5: Unknown model
        scenarios.append({
            "api_key": "sk-test-model",
            "model": "gpt-5-ultra",  # Doesn't exist
            "tokens_used": 1000,
            "cost": 0.05,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return scenarios
    
    def export_to_file(
        self,
        payloads: List[Dict[str, Any]],
        filename: str,
        include_signatures: bool = True
    ):
        """
        Export payloads to JSON file
        
        Args:
            payloads: List of webhook payloads
            filename: Output filename
            include_signatures: Whether to include signatures
        """
        export_data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(payloads),
                "generator_version": "1.0"
            },
            "payloads": []
        }
        
        for payload in payloads:
            entry = {"payload": payload}
            if include_signatures:
                entry["signature"] = self.generate_webhook_signature(payload)
            export_data["payloads"].append(entry)
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported {len(payloads)} payloads to {filename}")


# Convenience functions for common scenarios
def generate_test_data_for_today(count: int = 100) -> List[Dict[str, Any]]:
    """Generate test data for today"""
    generator = WebhookDataGenerator()
    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    return generator.generate_batch(count=count, start_time=start_time)


def generate_test_data_for_date_range(
    start_date: str,
    end_date: str,
    daily_count: int = 100
) -> List[Dict[str, Any]]:
    """
    Generate test data for a date range
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        daily_count: Approximate number of webhooks per day
    """
    generator = WebhookDataGenerator()
    
    start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    
    days = (end - start).days + 1
    total_count = daily_count * days
    
    return generator.generate_batch(
        count=total_count,
        start_time=start,
        end_time=end + timedelta(days=1)
    )


if __name__ == "__main__":
    # Example usage
    generator = WebhookDataGenerator()
    
    # Generate various test scenarios
    print("Generating test webhook data...")
    
    # 1. Normal daily traffic
    daily_data = generator.generate_batch(count=50)
    generator.export_to_file(daily_data, "webhook_test_daily.json")
    
    # 2. Burst traffic
    burst_data = generator.generate_burst_traffic(burst_size=30)
    generator.export_to_file(burst_data, "webhook_test_burst.json")
    
    # 3. Error scenarios
    error_data = generator.generate_error_scenarios()
    generator.export_to_file(error_data, "webhook_test_errors.json")
    
    # 4. Multi-day data for batch testing
    multiday_data = generate_test_data_for_date_range(
        "2024-01-25",
        "2024-01-30",
        daily_count=100
    )
    generator.export_to_file(multiday_data, "webhook_test_multiday.json")
    
    print("\nTest data generation complete!")