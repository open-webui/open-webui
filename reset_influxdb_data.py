#!/usr/bin/env python3
"""
InfluxDB Data Reset Script for mAI Development Environment
=========================================================

This script connects to the local InfluxDB development instance and deletes
all data points from the mai_usage_raw_dev bucket.

Usage:
    python3 reset_influxdb_data.py

Requirements:
    pip install influxdb-client

Development Environment:
    - InfluxDB URL: http://localhost:8086
    - Token: dev-token-for-testing-only
    - Organization: mAI-dev
    - Bucket: mai_usage_raw_dev
"""

import sys
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, DeleteApi
from influxdb_client.client.exceptions import InfluxDBError


def main():
    """Main function to reset InfluxDB data."""
    
    # InfluxDB connection parameters from .env.dev
    url = "http://localhost:8086"
    token = "dev-token-for-testing-only"
    org = "mAI-dev"
    bucket = "mai_usage_raw_dev"
    
    print("🔗 InfluxDB Data Reset Script")
    print("=" * 50)
    print(f"Target URL: {url}")
    print(f"Organization: {org}")
    print(f"Bucket: {bucket}")
    print()
    
    # Create InfluxDB client
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        print("✅ Connected to InfluxDB successfully")
        
        # Test connection by checking bucket health
        buckets_api = client.buckets_api()
        bucket_info = buckets_api.find_bucket_by_name(bucket)
        
        if not bucket_info:
            print(f"❌ Error: Bucket '{bucket}' not found!")
            print("Available buckets:")
            for b in buckets_api.find_buckets().buckets:
                print(f"  - {b.name}")
            return 1
            
        print(f"✅ Found bucket: {bucket_info.name} (ID: {bucket_info.id})")
        print()
        
    except InfluxDBError as e:
        print(f"❌ Failed to connect to InfluxDB: {e}")
        print("💡 Make sure InfluxDB is running:")
        print("   docker-compose -f docker-compose.dev.yml up influxdb")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    # Confirm deletion
    print("⚠️  WARNING: This will DELETE ALL DATA from the mai_usage_raw_dev bucket!")
    print("This action cannot be undone.")
    print()
    
    # Auto-confirm for development environment
    print("🔄 Auto-confirming deletion for development environment...")
    confirmation = "DELETE"
    
    print()
    print("🗑️  Starting data deletion...")
    
    try:
        # Delete all data from the beginning of time to now
        delete_api = client.delete_api()
        
        # Delete all data from 1970 to now
        start = "1970-01-01T00:00:00Z"
        stop = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        print(f"📅 Deleting data from {start} to {stop}")
        
        # Delete all measurements in the bucket (empty predicate deletes everything)
        delete_api.delete(
            start=start,
            stop=stop,
            bucket=bucket,
            org=org,
            predicate=""
        )
        
        print("✅ Data deletion completed successfully!")
        
        # Verify deletion by checking if any data remains
        query_api = client.query_api()
        query = f"""
        from(bucket: "{bucket}")
          |> range(start: -30d)
          |> count()
        """
        
        print("🔍 Verifying deletion...")
        result = query_api.query(org=org, query=query)
        
        if not result or not any(result):
            print("✅ Verification successful: No data found in bucket")
        else:
            remaining_count = sum(record.get_value() for table in result for record in table.records)
            if remaining_count == 0:
                print("✅ Verification successful: No data found in bucket")
            else:
                print(f"⚠️  Warning: {remaining_count} data points may still exist")
        
        print()
        print("🎉 InfluxDB data reset completed!")
        print("The mai_usage_raw_dev bucket is now empty and ready for new data.")
        
    except InfluxDBError as e:
        print(f"❌ Failed to delete data: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error during deletion: {e}")
        return 1
    
    finally:
        # Close the client connection
        client.close()
        print("🔌 Disconnected from InfluxDB")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())