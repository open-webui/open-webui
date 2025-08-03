"""
Webhook Sender for Testing
Sends generated webhook data to mAI endpoints for testing
"""

import asyncio
import json
import time
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from webhook_data_generator import WebhookDataGenerator


class WebhookSender:
    """Send webhook payloads to mAI endpoints"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        webhook_secret: str = "test-webhook-secret",
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.webhook_endpoint = f"{self.base_url}/api/webhooks/openrouter"
        self.webhook_secret = webhook_secret
        self.timeout = timeout
        self.stats = {
            "sent": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }
    
    def generate_signature(self, payload: Dict[str, Any]) -> str:
        """Generate OpenRouter webhook signature"""
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def send_webhook(
        self,
        payload: Dict[str, Any],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """
        Send a single webhook payload
        
        Args:
            payload: Webhook payload
            client: HTTP client instance
            
        Returns:
            Response data
        """
        # Generate signature
        signature = self.generate_signature(payload)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-OpenRouter-Signature": signature,
            "X-OpenRouter-Timestamp": str(int(time.time())),
            "User-Agent": "OpenRouter-Webhook-Test/1.0"
        }
        
        try:
            response = await client.post(
                self.webhook_endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            self.stats["sent"] += 1
            
            if response.status_code == 200:
                self.stats["success"] += 1
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.json() if response.text else {}
                }
            else:
                self.stats["failed"] += 1
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.stats["errors"].append(error_msg)
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": error_msg
                }
                
        except Exception as e:
            self.stats["failed"] += 1
            error_msg = f"Request failed: {str(e)}"
            self.stats["errors"].append(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def send_batch(
        self,
        payloads: List[Dict[str, Any]],
        rate_limit: Optional[int] = None,
        concurrent_limit: int = 10,
        progress: bool = True
    ) -> Dict[str, Any]:
        """
        Send a batch of webhook payloads
        
        Args:
            payloads: List of webhook payloads
            rate_limit: Max requests per second (None = no limit)
            concurrent_limit: Max concurrent requests
            progress: Show progress updates
            
        Returns:
            Batch results
        """
        self.stats = {
            "sent": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            if rate_limit:
                # Send with rate limiting
                results = []
                for i, payload in enumerate(payloads):
                    if progress and i % 10 == 0:
                        print(f"Progress: {i}/{len(payloads)} sent...")
                    
                    result = await self.send_webhook(payload, client)
                    results.append(result)
                    
                    # Rate limiting
                    if rate_limit and i < len(payloads) - 1:
                        await asyncio.sleep(1.0 / rate_limit)
                
            else:
                # Send concurrently with semaphore
                semaphore = asyncio.Semaphore(concurrent_limit)
                
                async def send_with_semaphore(payload):
                    async with semaphore:
                        return await self.send_webhook(payload, client)
                
                # Create tasks
                tasks = [send_with_semaphore(payload) for payload in payloads]
                
                # Execute with progress updates
                if progress:
                    results = []
                    for i, task in enumerate(asyncio.as_completed(tasks)):
                        result = await task
                        results.append(result)
                        if i % 10 == 0:
                            print(f"Progress: {i+1}/{len(payloads)} completed...")
                else:
                    results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        # Final statistics
        final_stats = {
            **self.stats,
            "duration_seconds": round(duration, 2),
            "requests_per_second": round(len(payloads) / duration, 2) if duration > 0 else 0,
            "success_rate": round(self.stats["success"] / self.stats["sent"] * 100, 2) if self.stats["sent"] > 0 else 0
        }
        
        if progress:
            print("\n=== Batch Send Complete ===")
            print(f"Total sent: {final_stats['sent']}")
            print(f"Successful: {final_stats['success']}")
            print(f"Failed: {final_stats['failed']}")
            print(f"Success rate: {final_stats['success_rate']}%")
            print(f"Duration: {final_stats['duration_seconds']}s")
            print(f"Rate: {final_stats['requests_per_second']} req/s")
            
            if final_stats['errors']:
                print(f"\nFirst 5 errors:")
                for error in final_stats['errors'][:5]:
                    print(f"  - {error}")
        
        return final_stats
    
    async def send_continuous(
        self,
        generator: WebhookDataGenerator,
        rate: int = 1,
        duration_seconds: Optional[int] = None,
        models: Optional[List[str]] = None
    ):
        """
        Send continuous stream of webhooks
        
        Args:
            generator: Webhook data generator
            rate: Webhooks per second
            duration_seconds: How long to run (None = forever)
            models: List of models to use
        """
        print(f"Starting continuous webhook stream at {rate} req/s...")
        if duration_seconds:
            print(f"Will run for {duration_seconds} seconds")
        else:
            print("Press Ctrl+C to stop")
        
        start_time = time.time()
        interval = 1.0 / rate
        
        async with httpx.AsyncClient() as client:
            try:
                while True:
                    # Check duration
                    if duration_seconds and (time.time() - start_time) > duration_seconds:
                        break
                    
                    # Generate and send webhook
                    payload = generator.generate_webhook_payload(
                        model=models[0] if models else None
                    )
                    
                    asyncio.create_task(self.send_webhook(payload, client))
                    
                    # Rate limiting
                    await asyncio.sleep(interval)
                    
            except KeyboardInterrupt:
                print("\nStopping continuous stream...")
        
        print(f"\nSent {self.stats['sent']} webhooks")
        print(f"Success rate: {self.stats['success_rate']}%")
    
    async def test_endpoint_health(self) -> bool:
        """Test if the webhook endpoint is accessible"""
        try:
            async with httpx.AsyncClient() as client:
                # Try a simple GET to the base URL
                response = await client.get(
                    self.base_url,
                    timeout=5.0
                )
                
                if response.status_code < 500:
                    print(f"✅ Endpoint is accessible: {self.base_url}")
                    return True
                else:
                    print(f"❌ Endpoint returned error: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Cannot reach endpoint: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Send test webhooks to mAI")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of mAI instance"
    )
    parser.add_argument(
        "--secret",
        default="test-webhook-secret",
        help="Webhook secret for signature"
    )
    parser.add_argument(
        "--mode",
        choices=["batch", "continuous", "burst", "file"],
        default="batch",
        help="Sending mode"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of webhooks to send (batch mode)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=1,
        help="Webhooks per second (continuous mode)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Duration in seconds (continuous mode)"
    )
    parser.add_argument(
        "--file",
        help="JSON file with webhook payloads (file mode)"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="Max concurrent requests"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Specific models to use"
    )
    parser.add_argument(
        "--api-key",
        help="Specific API key to use"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress output"
    )
    
    args = parser.parse_args()
    
    # Initialize sender
    sender = WebhookSender(
        base_url=args.url,
        webhook_secret=args.secret
    )
    
    # Test endpoint first
    if not await sender.test_endpoint_health():
        print("\n⚠️  Warning: Endpoint may not be accessible!")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Initialize generator
    generator = WebhookDataGenerator(webhook_secret=args.secret)
    
    # Execute based on mode
    if args.mode == "batch":
        print(f"\nGenerating {args.count} webhook payloads...")
        payloads = generator.generate_batch(
            count=args.count,
            models=args.models,
            api_key=args.api_key
        )
        
        print(f"Sending batch of {len(payloads)} webhooks...")
        await sender.send_batch(
            payloads,
            concurrent_limit=args.concurrent,
            progress=not args.no_progress
        )
        
    elif args.mode == "continuous":
        await sender.send_continuous(
            generator,
            rate=args.rate,
            duration_seconds=args.duration,
            models=args.models
        )
        
    elif args.mode == "burst":
        print(f"\nGenerating burst traffic...")
        payloads = generator.generate_burst_traffic(
            burst_size=args.count,
            api_key=args.api_key
        )
        
        print(f"Sending burst of {len(payloads)} webhooks...")
        await sender.send_batch(
            payloads,
            concurrent_limit=args.concurrent,
            progress=not args.no_progress
        )
        
    elif args.mode == "file":
        if not args.file:
            print("Error: --file required for file mode")
            return
            
        print(f"\nLoading webhooks from {args.file}...")
        with open(args.file, 'r') as f:
            data = json.load(f)
            
        payloads = [entry["payload"] for entry in data["payloads"]]
        print(f"Loaded {len(payloads)} webhooks")
        
        await sender.send_batch(
            payloads,
            concurrent_limit=args.concurrent,
            progress=not args.no_progress
        )


if __name__ == "__main__":
    asyncio.run(main())