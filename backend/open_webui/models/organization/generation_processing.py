import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Integer, Float, Date, Index, Boolean, func

log = logging.getLogger(__name__)


class ProcessedGeneration(Base):
    """Track processed OpenRouter generations to prevent duplicates"""
    __tablename__ = "processed_generations"

    id = Column(String, primary_key=True)  # OpenRouter generation ID
    client_org_id = Column(String, nullable=False)
    generation_date = Column(Date, nullable=False)
    processed_at = Column(BigInteger, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    __table_args__ = (
        Index('idx_client_date', 'client_org_id', 'generation_date'),
        Index('idx_processed_at', 'processed_at'),
    )


class ProcessedGenerationCleanupLog(Base):
    """Track cleanup operations for audit and monitoring"""
    __tablename__ = "processed_generation_cleanup_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cleanup_date = Column(Date, nullable=False)  # Date when cleanup was performed
    cutoff_date = Column(Date, nullable=False)   # Records older than this were deleted
    days_retained = Column(Integer, nullable=False)  # Retention period used
    records_before = Column(Integer, nullable=False)
    records_deleted = Column(Integer, nullable=False)
    records_remaining = Column(Integer, nullable=False)
    old_tokens_removed = Column(BigInteger, nullable=False)
    old_cost_removed = Column(Float, nullable=False)
    storage_saved_kb = Column(Float, nullable=False)
    cleanup_duration_seconds = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('idx_cleanup_date', 'cleanup_date'),
        Index('idx_success', 'success'),
    )


class ProcessedGenerationTable:
    """Service class for ProcessedGeneration operations"""
    
    def add_generation(self, generation_id: str, client_org_id: str, generation_date: date, 
                      total_cost: float, total_tokens: int) -> bool:
        try:
            with get_db() as db:
                existing = db.query(ProcessedGeneration).filter_by(id=generation_id).first()
                if existing:
                    return False
                
                generation = ProcessedGeneration(
                    id=generation_id,
                    client_org_id=client_org_id,
                    generation_date=generation_date,
                    processed_at=int(time.time()),
                    total_cost=total_cost,
                    total_tokens=total_tokens
                )
                db.add(generation)
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error adding generation {generation_id}: {e}")
            return False

    def is_processed(self, generation_id: str) -> bool:
        with get_db() as db:
            return db.query(ProcessedGeneration).filter_by(id=generation_id).count() > 0

    def get_processed_generations_for_date(self, client_org_id: str, target_date: date) -> List[ProcessedGeneration]:
        with get_db() as db:
            return db.query(ProcessedGeneration).filter(
                ProcessedGeneration.client_org_id == client_org_id,
                ProcessedGeneration.generation_date == target_date
            ).all()

    def cleanup_old_generations(self, days_to_retain: int = 90) -> Dict[str, Any]:
        """Delete processed generations older than specified days"""
        start_time = time.time()
        cutoff_date = date.today() - timedelta(days=days_to_retain)
        
        with get_db() as db:
            try:
                # Get initial stats
                total_before = db.query(func.count(ProcessedGeneration.id)).scalar()
                
                # Get stats for records to be deleted
                old_records = db.query(
                    func.count(ProcessedGeneration.id),
                    func.sum(ProcessedGeneration.total_tokens),
                    func.sum(ProcessedGeneration.total_cost)
                ).filter(ProcessedGeneration.generation_date < cutoff_date).first()
                
                records_to_delete, tokens_to_remove, cost_to_remove = old_records
                records_to_delete = records_to_delete or 0
                tokens_to_remove = tokens_to_remove or 0
                cost_to_remove = cost_to_remove or 0.0
                
                # Delete old records
                if records_to_delete > 0:
                    db.query(ProcessedGeneration).filter(
                        ProcessedGeneration.generation_date < cutoff_date
                    ).delete(synchronize_session=False)
                
                # Log the cleanup operation
                cleanup_log = ProcessedGenerationCleanupLog(
                    cleanup_date=date.today(),
                    cutoff_date=cutoff_date,
                    days_retained=days_to_retain,
                    records_before=total_before,
                    records_deleted=records_to_delete,
                    records_remaining=total_before - records_to_delete,
                    old_tokens_removed=tokens_to_remove,
                    old_cost_removed=cost_to_remove,
                    storage_saved_kb=records_to_delete * 0.1,  # Estimate ~100 bytes per record
                    cleanup_duration_seconds=time.time() - start_time,
                    success=True,
                    created_at=int(time.time())
                )
                db.add(cleanup_log)
                db.commit()
                
                return {
                    "success": True,
                    "records_deleted": records_to_delete,
                    "records_remaining": total_before - records_to_delete,
                    "tokens_removed": tokens_to_remove,
                    "cost_removed": cost_to_remove,
                    "duration_seconds": time.time() - start_time
                }
                
            except Exception as e:
                # Log the failed cleanup attempt
                cleanup_log = ProcessedGenerationCleanupLog(
                    cleanup_date=date.today(),
                    cutoff_date=cutoff_date,
                    days_retained=days_to_retain,
                    records_before=0,
                    records_deleted=0,
                    records_remaining=0,
                    old_tokens_removed=0,
                    old_cost_removed=0.0,
                    storage_saved_kb=0.0,
                    cleanup_duration_seconds=time.time() - start_time,
                    success=False,
                    error_message=str(e),
                    created_at=int(time.time())
                )
                db.add(cleanup_log)
                db.commit()
                
                log.error(f"Failed to cleanup old generations: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "duration_seconds": time.time() - start_time
                }