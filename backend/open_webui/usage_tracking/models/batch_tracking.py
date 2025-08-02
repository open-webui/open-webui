"""
Database models for tracking InfluxDB batch processing runs
Part of Phase 2: Batch Consolidation
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date

Base = declarative_base()


class InfluxDBBatchRunDB(Base):
    """
    Track InfluxDB batch processing runs for monitoring and debugging
    
    This table provides audit trail and performance monitoring for
    the unified batch processor operations.
    """
    __tablename__ = "influxdb_batch_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Processing details
    processing_date = Column(Date, nullable=False, index=True, 
                           comment="Date being processed (usually yesterday)")
    batch_start_time = Column(DateTime, nullable=False, 
                            comment="When batch processing started")
    batch_end_time = Column(DateTime, nullable=True, 
                          comment="When batch processing completed")
    duration_seconds = Column(Float, nullable=True, 
                            comment="Total processing duration")
    
    # Processing results
    success = Column(Boolean, nullable=False, default=False, 
                   comment="Overall batch success status")
    data_source = Column(String(50), nullable=False, default="influxdb_first", 
                       comment="Data source used (influxdb_first/legacy_sqlite)")
    
    # Performance metrics
    clients_processed = Column(Integer, nullable=False, default=0,
                             comment="Number of client organizations processed")
    influxdb_records_processed = Column(Integer, nullable=False, default=0,
                                      comment="Raw InfluxDB records read and processed")
    sqlite_summaries_created = Column(Integer, nullable=False, default=0,
                                    comment="SQLite summary records created/updated")
    data_corrections = Column(Integer, nullable=False, default=0,
                            comment="Number of data corrections applied")
    
    # Exchange rate used
    exchange_rate_usd_pln = Column(Float, nullable=True, 
                                 comment="USD/PLN exchange rate used for calculations")
    
    # Error tracking
    error_message = Column(Text, nullable=True, 
                         comment="Error message if batch failed")
    error_count = Column(Integer, nullable=False, default=0,
                       comment="Number of errors encountered during processing")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                      comment="When this record was created")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                      onupdate=datetime.utcnow, comment="When this record was last updated")
    
    def __repr__(self):
        return (
            f"<InfluxDBBatchRun(id={self.id}, "
            f"processing_date={self.processing_date}, "
            f"success={self.success}, "
            f"clients_processed={self.clients_processed}, "
            f"data_source='{self.data_source}')>"
        )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "processing_date": self.processing_date.isoformat() if self.processing_date else None,
            "batch_start_time": self.batch_start_time.isoformat() if self.batch_start_time else None,
            "batch_end_time": self.batch_end_time.isoformat() if self.batch_end_time else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "data_source": self.data_source,
            "clients_processed": self.clients_processed,
            "influxdb_records_processed": self.influxdb_records_processed,
            "sqlite_summaries_created": self.sqlite_summaries_created,
            "data_corrections": self.data_corrections,
            "exchange_rate_usd_pln": self.exchange_rate_usd_pln,
            "error_message": self.error_message,
            "error_count": self.error_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ClientModelDailyUsageDB(Base):
    """
    Extended model for tracking client model usage
    
    This provides additional granularity for the summary tables
    strategy in Phase 2.
    """
    __tablename__ = "client_model_daily_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Client and date information
    client_org_id = Column(String(255), nullable=False, index=True,
                         comment="Client organization identifier")
    usage_date = Column(Date, nullable=False, index=True,
                      comment="Date of usage")
    model = Column(String(255), nullable=False, index=True,
                 comment="AI model used")
    
    # Usage metrics
    total_tokens = Column(Integer, nullable=False, default=0,
                        comment="Total tokens processed")
    input_tokens = Column(Integer, nullable=False, default=0,
                        comment="Input tokens processed")
    output_tokens = Column(Integer, nullable=False, default=0,
                         comment="Output tokens processed")
    request_count = Column(Integer, nullable=False, default=0,
                         comment="Number of API requests")
    
    # Cost metrics
    raw_cost_usd = Column(Float, nullable=False, default=0.0,
                        comment="Raw cost in USD (before markup)")
    markup_cost_usd = Column(Float, nullable=False, default=0.0,
                           comment="Cost in USD after markup")
    markup_cost_pln = Column(Float, nullable=False, default=0.0,
                           comment="Cost in PLN after markup and currency conversion")
    markup_rate = Column(Float, nullable=False, default=1.3,
                       comment="Markup rate applied (e.g., 1.3 = 30% markup)")
    
    # Data source tracking
    source = Column(String(50), nullable=False, default="influxdb_first",
                  comment="Source of the data (influxdb_first/webhook/batch)")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                      onupdate=datetime.utcnow)
    
    def __repr__(self):
        return (
            f"<ClientModelDailyUsage(client_org_id='{self.client_org_id}', "
            f"usage_date={self.usage_date}, model='{self.model}', "
            f"total_tokens={self.total_tokens}, "
            f"markup_cost_usd={self.markup_cost_usd})>"
        )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "client_org_id": self.client_org_id,
            "usage_date": self.usage_date.isoformat() if self.usage_date else None,
            "model": self.model,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "request_count": self.request_count,
            "raw_cost_usd": self.raw_cost_usd,
            "markup_cost_usd": self.markup_cost_usd,
            "markup_cost_pln": self.markup_cost_pln,
            "markup_rate": self.markup_rate,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }