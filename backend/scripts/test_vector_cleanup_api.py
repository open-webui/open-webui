#!/usr/bin/env python3
"""
Test script for vector cleanup API endpoints.
Run this script to verify the cleanup endpoints are working correctly.
(testing only)
"""

import requests
import json
import sys
import os
from typing import Dict, Any

# Configuration
CANCHAT_URL = os.getenv("CANCHAT_URL", "http://localhost:8080")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@localhost")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


def get_admin_token() -> str:
    """Get admin authentication token."""
    try:
        response = requests.post(
            f"{CANCHAT_URL}/api/v1/auths/signin",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()["token"]
    except Exception as e:
        print(f"❌ Failed to get admin token: {e}")
        sys.exit(1)


def test_endpoint(
    endpoint: str, method: str = "GET", data: Dict[Any, Any] = None
) -> Dict[Any, Any]:
    """Test a specific endpoint."""
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(f"{CANCHAT_URL}{endpoint}", headers=headers)
        elif method == "POST":
            response = requests.post(
                f"{CANCHAT_URL}{endpoint}", headers=headers, json=data
            )
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed for {endpoint}: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error detail: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Response text: {e.response.text}")
        return {"error": str(e)}


def main():
    """Run all endpoint tests."""
    print("🔧 Testing CANChat Vector Cleanup API Endpoints")
    print("=" * 50)

    endpoints = [
        {
            "name": "Health Check",
            "endpoint": "/api/v1/retrieval/maintenance/health/vector-db",
            "method": "GET",
        },
        {
            "name": "Cleanup Orphaned Vectors",
            "endpoint": "/api/v1/retrieval/maintenance/cleanup/orphaned",
            "method": "POST",
        },
        {
            "name": "Cleanup Web Search (7 days)",
            "endpoint": "/api/v1/retrieval/maintenance/cleanup/web-search",
            "method": "POST",
            "data": {"max_age_days": 7},
        },
        {
            "name": "Comprehensive Cleanup",
            "endpoint": "/api/v1/retrieval/maintenance/cleanup/comprehensive",
            "method": "POST",
        },
    ]

    results = {}

    for test in endpoints:
        print(f"\n🧪 Testing: {test['name']}")
        print(f"   Endpoint: {test['endpoint']}")

        result = test_endpoint(test["endpoint"], test["method"], test.get("data"))

        if "error" in result:
            print(f"   ❌ Failed")
            results[test["name"]] = "FAILED"
        else:
            print(f"   ✅ Success")
            results[test["name"]] = "PASSED"

            # Print relevant stats
            if "vector_db" in result:
                vdb = result["vector_db"]
                print(f"   📊 Collections: {vdb.get('total_collections', 'N/A')}")

            if "cleanup_result" in result:
                cleanup = result["cleanup_result"]
                print(
                    f"   🧹 Cleaned: {cleanup.get('collections_cleaned', 0)} collections, "
                    f"{cleanup.get('vectors_cleaned', 0)} vectors"
                )

            if "cleanup_results" in result:
                cleanup = result["cleanup_results"]
                orphaned = cleanup.get("orphaned_vectors", {})
                web_search = cleanup.get("web_search_vectors", {})
                print(
                    f"   🧹 Orphaned: {orphaned.get('collections_cleaned', 0)} collections"
                )
                print(
                    f"   🧹 Web Search: {web_search.get('collections_cleaned', 0)} collections"
                )

    print("\n" + "=" * 50)
    print("📋 Test Summary:")

    all_passed = True
    for test_name, status in results.items():
        status_icon = "✅" if status == "PASSED" else "❌"
        print(f"   {status_icon} {test_name}: {status}")
        if status != "PASSED":
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! Vector cleanup API is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
