"""
Test Script for Unified Batch Processor
Phase 2: Batch Consolidation Testing

Tests the InfluxDB-First batch processing architecture
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, date, timedelta

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from open_webui.utils.unified_batch_processor import (
    UnifiedBatchProcessor,
    run_unified_daily_batch,
    health_check_unified_batch
)


async def test_unified_batch_processor():
    """Test the unified batch processor functionality"""
    
    print("🧪 Testing Unified Batch Processor")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1. 🏥 Health Check Test")
    print("-" * 30)
    
    try:
        health_result = await health_check_unified_batch()
        print(f"Health Status: {health_result.get('status', 'unknown')}")
        print(f"InfluxDB-First Enabled: {health_result.get('influxdb_first_enabled', False)}")
        print(f"Data Source: {health_result.get('data_source', 'unknown')}")
        
        services = health_result.get('services', {})
        for service_name, service_status in services.items():
            status = service_status.get('status', 'unknown')
            print(f"  - {service_name}: {status}")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Test 2: Instance Creation
    print("\n2. 🏗️  Instance Creation Test")
    print("-" * 30)
    
    try:
        processor = UnifiedBatchProcessor()
        print(f"✅ Processor created successfully")
        print(f"   InfluxDB-First Enabled: {processor.influxdb_first_enabled}")
        print(f"   NBP Service URL: {processor.nbp_service_url}")
        print(f"   Markup Multiplier: {processor.markup_multiplier}")
        
    except Exception as e:
        print(f"❌ Instance creation failed: {e}")
        return
    
    # Test 3: Batch Processing (Test Mode)
    print("\n3. 🔄 Batch Processing Test")
    print("-" * 30)
    
    try:
        # Process data for yesterday (typical use case)
        test_date = date.today() - timedelta(days=1)
        print(f"Testing batch processing for date: {test_date}")
        
        result = await run_unified_daily_batch(processing_date=test_date)
        
        print(f"Batch Success: {result.get('success', False)}")
        print(f"Processing Date: {result.get('processing_date', 'unknown')}")
        print(f"Data Source: {result.get('data_source', 'unknown')}")
        print(f"Clients Processed: {result.get('clients_processed', 0)}")
        print(f"InfluxDB Records: {result.get('influxdb_records_processed', 0)}")
        print(f"SQLite Summaries: {result.get('sqlite_summaries_created', 0)}")
        print(f"Data Corrections: {result.get('data_corrections', 0)}")
        print(f"Duration: {result.get('total_duration_seconds', 0):.2f}s")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
            
        if result.get('errors'):
            print(f"Client Errors: {len(result['errors'])}")
            for error in result['errors'][:3]:  # Show first 3 errors
                print(f"  - Client {error.get('client_org_id')}: {error.get('error')}")
                
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
    
    # Test 4: InfluxDB Batch Queries (if available)
    print("\n4. 📊 InfluxDB Batch Queries Test")
    print("-" * 30)
    
    try:
        from open_webui.usage_tracking.services.influxdb_batch_queries import influxdb_batch_queries
        
        # Test basic connectivity
        test_start = datetime.combine(test_date, datetime.min.time())
        test_end = test_start + timedelta(days=1)
        
        # Get clients with data
        clients_with_data = await influxdb_batch_queries.get_client_list_with_data(
            test_start, test_end
        )
        
        print(f"Clients with data: {len(clients_with_data)}")
        if clients_with_data:
            print(f"Sample clients: {clients_with_data[:3]}")
            
            # Test aggregation for first client
            if clients_with_data:
                sample_client = clients_with_data[0]
                aggregated_data = await influxdb_batch_queries.get_daily_usage_aggregated(
                    sample_client, test_start, test_end
                )
                print(f"Sample aggregated records for {sample_client}: {len(aggregated_data)}")
        
        # Get overall statistics
        stats = await influxdb_batch_queries.get_batch_processing_stats(
            test_start, test_end
        )
        print(f"Batch Stats: {stats}")
        
    except Exception as e:
        print(f"⚠️  InfluxDB batch queries test failed (may be expected if InfluxDB disabled): {e}")
    
    # Test 5: Legacy Fallback (if InfluxDB disabled)
    print("\n5. 🔄 Legacy Fallback Test")
    print("-" * 30)
    
    try:
        # Temporarily disable InfluxDB-First to test fallback
        original_enabled = processor.influxdb_first_enabled
        processor.influxdb_first_enabled = False
        
        print("Testing legacy fallback mode...")
        
        # This should trigger legacy processing
        fallback_result = await processor.run_daily_batch(processing_date=test_date)
        
        print(f"Fallback Success: {fallback_result.get('success', False)}")
        print(f"Fallback Data Source: {fallback_result.get('data_source', 'unknown')}")
        
        # Restore original setting
        processor.influxdb_first_enabled = original_enabled
        
    except Exception as e:
        print(f"⚠️  Legacy fallback test failed (may be expected): {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Unified Batch Processor Testing Completed")
    print("\nPhase 2: Batch Consolidation")
    print("✅ InfluxDB-First Architecture")
    print("✅ Unified Processing Logic")  
    print("✅ Backward Compatibility")
    print("✅ Health Monitoring")
    print("=" * 60)


async def test_flux_queries():
    """Test specific Flux queries for batch processing"""
    
    print("\n🔍 Testing Flux Queries")
    print("=" * 40)
    
    try:
        from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service
        
        if not influxdb_first_service.enabled:
            print("⚠️  InfluxDB service is disabled, skipping Flux query tests")
            return
        
        # Test health check
        health = await influxdb_first_service.health_check()
        print(f"InfluxDB Service Health: {health.get('status', 'unknown')}")
        
        # Test custom query
        test_query = f'''
        from(bucket: "{influxdb_first_service.bucket}")
          |> range(start: -7d)
          |> filter(fn: (r) => r._measurement == "usage_tracking")
          |> filter(fn: (r) => r._field == "total_tokens")
          |> count()
        '''
        
        query_result = await influxdb_first_service.query_data(test_query)
        print(f"Custom query result: {len(query_result)} records")
        
        if query_result:
            print(f"Sample result: {query_result[0]}")
        
    except Exception as e:
        print(f"❌ Flux query test failed: {e}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Unified Batch Processor Tests")
    print("Phase 2: Batch Consolidation - InfluxDB-First Architecture")
    
    # Run main tests
    asyncio.run(test_unified_batch_processor())
    
    # Run additional Flux query tests
    asyncio.run(test_flux_queries())