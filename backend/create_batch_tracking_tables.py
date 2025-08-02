"""
Database Migration: Create InfluxDB Batch Tracking Tables
Phase 2: Batch Consolidation - Summary Tables Strategy

This script creates the tables needed for tracking InfluxDB batch processing runs
and extended model usage summaries.
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from open_webui.utils.database import get_db_url
from open_webui.usage_tracking.models.batch_tracking import Base, InfluxDBBatchRunDB, ClientModelDailyUsageDB

logger = logging.getLogger(__name__)


def create_batch_tracking_tables():
    """
    Create InfluxDB batch tracking tables
    
    Tables created:
    1. influxdb_batch_runs - Track all batch processing runs
    2. client_model_daily_usage - Extended model usage summaries
    """
    try:
        # Get database URL
        database_url = get_db_url()
        logger.info(f"Connecting to database: {database_url}")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create tables
        logger.info("Creating InfluxDB batch tracking tables...")
        Base.metadata.create_all(engine)
        
        # Verify tables were created
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Test influxdb_batch_runs table
            result = session.execute(text("SELECT COUNT(*) FROM influxdb_batch_runs"))
            logger.info(f"✅ influxdb_batch_runs table created successfully (current count: {result.scalar()})")
            
            # Test client_model_daily_usage table  
            result = session.execute(text("SELECT COUNT(*) FROM client_model_daily_usage"))
            logger.info(f"✅ client_model_daily_usage table created successfully (current count: {result.scalar()})")
            
            # Create an initial batch run record for testing
            initial_batch_run = InfluxDBBatchRunDB(
                processing_date=datetime.now().date(),
                batch_start_time=datetime.now(),
                batch_end_time=datetime.now(),
                duration_seconds=0.0,
                success=True,
                data_source="migration_test",
                clients_processed=0,
                influxdb_records_processed=0,
                sqlite_summaries_created=0,
                data_corrections=0,
                error_message="Initial migration test record"
            )
            
            session.add(initial_batch_run)
            session.commit()
            
            logger.info("✅ Created initial test batch run record")
            
        except Exception as e:
            logger.error(f"Error testing tables: {e}")
            session.rollback()
            raise
        finally:
            session.close()
        
        logger.info("🎉 InfluxDB batch tracking tables created successfully!")
        
        # Print table schema information
        print("\n" + "="*70)
        print("INFLUXDB BATCH TRACKING TABLES CREATED")
        print("="*70)
        print("\n1. influxdb_batch_runs:")
        print("   - Tracks all batch processing runs")
        print("   - Monitors performance and success rates") 
        print("   - Provides audit trail for debugging")
        print("\n2. client_model_daily_usage:")
        print("   - Extended model-level usage summaries")
        print("   - Granular cost and token tracking")
        print("   - Supports advanced analytics")
        print("\nPhase 2: Batch Consolidation - Summary Tables Strategy")
        print("Data Flow: InfluxDB (raw) → SQLite (summaries)")
        print("="*70)
        
    except Exception as e:
        logger.error(f"❌ Failed to create batch tracking tables: {e}")
        raise


def show_existing_tables():
    """Show existing tables in the database for reference"""
    try:
        database_url = get_db_url()
        engine = create_engine(database_url)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Get all tables
            result = session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print("\n" + "="*50)
            print("EXISTING TABLES IN DATABASE")
            print("="*50)
            
            for table in tables:
                print(f"  - {table}")
                
            print(f"\nTotal tables: {len(tables)}")
            print("="*50)
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error showing existing tables: {e}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Creating InfluxDB Batch Tracking Tables...")
    print("Phase 2: Batch Consolidation - Summary Tables Strategy")
    print("-" * 60)
    
    try:
        # Show existing tables first
        show_existing_tables()
        
        # Create new batch tracking tables
        create_batch_tracking_tables()
        
        print("\n✅ Migration completed successfully!")
        print("The unified batch processor can now track batch runs and create extended summaries.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)