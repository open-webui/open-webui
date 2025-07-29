"""
Health check endpoints for monitoring organization model access.
Provides detailed health status and performance metrics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import psutil
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from open_webui.internal.db import get_db
from open_webui.config import WEBUI_AUTH
from open_webui.utils.auth import get_admin_user

router = APIRouter()


class HealthChecker:
    """Health check utilities for organization model access"""
    
    @staticmethod
    def check_database_connection(db: Session) -> Dict[str, Any]:
        """Check database connectivity and basic operations"""
        try:
            start = time.perf_counter()
            result = db.execute(text("SELECT 1")).scalar()
            query_time = (time.perf_counter() - start) * 1000
            
            return {
                "status": "healthy" if result == 1 else "unhealthy",
                "query_time_ms": round(query_time, 3),
                "message": "Database connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "query_time_ms": None,
                "message": f"Database connection failed: {str(e)}"
            }
    
    @staticmethod
    def check_organization_tables(db: Session) -> Dict[str, Any]:
        """Check organization tables exist and have proper indexes"""
        try:
            tables_check = {
                "organization_models": False,
                "organization_members": False,
                "user_available_models": False
            }
            
            # Check tables exist
            for table in tables_check.keys():
                try:
                    if table == "user_available_models":
                        # It's a view, not a table
                        db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                    else:
                        db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    tables_check[table] = True
                except:
                    pass
            
            # Check indexes
            indexes = db.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' 
                AND name LIKE 'idx_org_%'
            """)).fetchall()
            
            index_count = len(indexes)
            expected_indexes = 4  # Based on Phase 1 implementation
            
            all_healthy = all(tables_check.values()) and index_count >= expected_indexes
            
            return {
                "status": "healthy" if all_healthy else "degraded",
                "tables": tables_check,
                "index_count": index_count,
                "expected_indexes": expected_indexes,
                "message": "Organization structure healthy" if all_healthy else "Missing tables or indexes"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Failed to check organization tables: {str(e)}"
            }
    
    @staticmethod
    def check_model_access_performance(db: Session) -> Dict[str, Any]:
        """Test model access query performance"""
        try:
            # Test query performance
            queries = {
                "user_organizations": {
                    "query": """
                        SELECT COUNT(*) FROM organization_members 
                        WHERE user_id = :user_id AND is_active = 1
                    """,
                    "params": {"user_id": "test_user"}
                },
                "organization_models": {
                    "query": """
                        SELECT COUNT(*) FROM organization_models 
                        WHERE organization_id = :org_id AND is_active = 1
                    """,
                    "params": {"org_id": "test_org"}
                }
            }
            
            performance_results = {}
            total_time = 0
            
            for query_name, query_info in queries.items():
                start = time.perf_counter()
                try:
                    db.execute(text(query_info["query"]), query_info["params"]).scalar()
                    query_time = (time.perf_counter() - start) * 1000
                    performance_results[query_name] = {
                        "time_ms": round(query_time, 3),
                        "status": "fast" if query_time < 1 else "slow"
                    }
                    total_time += query_time
                except Exception as e:
                    performance_results[query_name] = {
                        "time_ms": None,
                        "status": "error",
                        "error": str(e)
                    }
            
            # Overall health based on performance
            avg_time = total_time / len(queries) if len(queries) > 0 else 0
            
            return {
                "status": "healthy" if avg_time < 1 else "degraded",
                "average_query_time_ms": round(avg_time, 3),
                "queries": performance_results,
                "message": "Query performance optimal" if avg_time < 1 else "Queries running slow"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Performance check failed: {str(e)}"
            }
    
    @staticmethod
    def check_organization_statistics(db: Session) -> Dict[str, Any]:
        """Get organization usage statistics"""
        try:
            stats = {}
            
            # Total organizations
            org_count = db.execute(text("""
                SELECT COUNT(DISTINCT organization_id) 
                FROM organization_members
            """)).scalar()
            
            # Total users in organizations
            user_count = db.execute(text("""
                SELECT COUNT(DISTINCT user_id) 
                FROM organization_members 
                WHERE is_active = 1
            """)).scalar()
            
            # Total model assignments
            model_assignments = db.execute(text("""
                SELECT COUNT(*) 
                FROM organization_models 
                WHERE is_active = 1
            """)).scalar()
            
            # Active users in last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            active_users = db.execute(text("""
                SELECT COUNT(DISTINCT u.id) 
                FROM user u
                JOIN organization_members om ON u.id = om.user_id
                WHERE u.last_active_at > :yesterday
            """), {"yesterday": int(yesterday.timestamp())}).scalar()
            
            return {
                "status": "healthy",
                "statistics": {
                    "total_organizations": org_count or 0,
                    "total_users": user_count or 0,
                    "model_assignments": model_assignments or 0,
                    "active_users_24h": active_users or 0
                },
                "message": "Statistics collected successfully"
            }
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"Failed to collect statistics: {str(e)}"
            }


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Basic health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
    
    # Quick database check
    db_check = HealthChecker.check_database_connection(db)
    if db_check["status"] != "healthy":
        health_status["status"] = "unhealthy"
        health_status["database"] = db_check
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/health/detailed")
async def detailed_health_check(
    db: Session = Depends(get_db),
    user=Depends(get_admin_user)
):
    """Detailed health check with all subsystem statuses (admin only)"""
    
    checker = HealthChecker()
    
    # Run all health checks
    health_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {
            "database": checker.check_database_connection(db),
            "organization_structure": checker.check_organization_tables(db),
            "query_performance": checker.check_model_access_performance(db),
            "usage_statistics": checker.check_organization_statistics(db)
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
    }
    
    # Determine overall health
    statuses = [check.get("status", "unknown") for check in health_report["checks"].values()]
    if "unhealthy" in statuses:
        health_report["status"] = "unhealthy"
    elif "degraded" in statuses:
        health_report["status"] = "degraded"
    
    # Add system warnings
    warnings = []
    if health_report["system"]["cpu_percent"] > 80:
        warnings.append("High CPU usage")
    if health_report["system"]["memory_percent"] > 80:
        warnings.append("High memory usage")
    if health_report["system"]["disk_usage_percent"] > 80:
        warnings.append("Low disk space")
    
    if warnings:
        health_report["warnings"] = warnings
    
    return health_report


@router.get("/metrics")
async def metrics_endpoint(db: Session = Depends(get_db)):
    """Prometheus-compatible metrics endpoint"""
    
    try:
        # Collect metrics
        org_count = db.execute(text("""
            SELECT COUNT(DISTINCT organization_id) FROM organization_members
        """)).scalar() or 0
        
        user_count = db.execute(text("""
            SELECT COUNT(DISTINCT user_id) FROM organization_members WHERE is_active = 1
        """)).scalar() or 0
        
        model_count = db.execute(text("""
            SELECT COUNT(DISTINCT model_id) FROM organization_models WHERE is_active = 1
        """)).scalar() or 0
        
        # Test query performance
        start = time.perf_counter()
        db.execute(text("""
            SELECT COUNT(*) FROM organization_members WHERE is_active = 1
        """)).scalar()
        query_time = (time.perf_counter() - start) * 1000
        
        # Format as Prometheus metrics
        metrics = []
        metrics.append("# HELP mai_organizations_total Total number of organizations")
        metrics.append("# TYPE mai_organizations_total gauge")
        metrics.append(f"mai_organizations_total {org_count}")
        
        metrics.append("# HELP mai_organization_users_total Total users in organizations")
        metrics.append("# TYPE mai_organization_users_total gauge")
        metrics.append(f"mai_organization_users_total {user_count}")
        
        metrics.append("# HELP mai_organization_models_total Total model assignments")
        metrics.append("# TYPE mai_organization_models_total gauge")
        metrics.append(f"mai_organization_models_total {model_count}")
        
        metrics.append("# HELP mai_query_duration_ms Query execution time in milliseconds")
        metrics.append("# TYPE mai_query_duration_ms histogram")
        metrics.append(f"mai_query_duration_ms {{query=\"organization_members_count\"}} {query_time:.3f}")
        
        # System metrics
        metrics.append("# HELP mai_cpu_usage_percent CPU usage percentage")
        metrics.append("# TYPE mai_cpu_usage_percent gauge")
        metrics.append(f"mai_cpu_usage_percent {psutil.cpu_percent()}")
        
        metrics.append("# HELP mai_memory_usage_percent Memory usage percentage")
        metrics.append("# TYPE mai_memory_usage_percent gauge")
        metrics.append(f"mai_memory_usage_percent {psutil.virtual_memory().percent}")
        
        return "\n".join(metrics)
        
    except Exception as e:
        # Return minimal metrics on error
        return f"# Error collecting metrics: {str(e)}\nmai_health_status 0"


@router.get("/health/model-access/{user_id}")
async def check_user_model_access(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user=Depends(get_admin_user)
):
    """Check specific user's model access (admin only)"""
    
    try:
        # Get user's organizations
        user_orgs = db.execute(text("""
            SELECT om.organization_id, om.role, om.is_active
            FROM organization_members om
            WHERE om.user_id = :user_id
        """), {"user_id": user_id}).fetchall()
        
        if not user_orgs:
            return {
                "user_id": user_id,
                "status": "no_organization",
                "organizations": [],
                "accessible_models": [],
                "message": "User is not member of any organization"
            }
        
        # Get accessible models
        org_ids = [org[0] for org in user_orgs if org[2] == 1]  # Only active memberships
        
        if not org_ids:
            return {
                "user_id": user_id,
                "status": "inactive",
                "organizations": [{"id": org[0], "role": org[1], "active": bool(org[2])} for org in user_orgs],
                "accessible_models": [],
                "message": "User has no active organization memberships"
            }
        
        # Get models for active organizations
        models = []
        for org_id in org_ids:
            org_models = db.execute(text("""
                SELECT m.id, m.name, om.is_active
                FROM organization_models om
                JOIN model m ON om.model_id = m.id
                WHERE om.organization_id = :org_id
                ORDER BY m.name
            """), {"org_id": org_id}).fetchall()
            
            models.extend([{
                "id": model[0],
                "name": model[1],
                "organization_id": org_id,
                "active": bool(model[2])
            } for model in org_models])
        
        active_models = [m for m in models if m["active"]]
        
        return {
            "user_id": user_id,
            "status": "healthy" if active_models else "no_models",
            "organizations": [{"id": org[0], "role": org[1], "active": bool(org[2])} for org in user_orgs],
            "accessible_models": active_models,
            "total_models": len(active_models),
            "message": f"User has access to {len(active_models)} models"
        }
        
    except Exception as e:
        return {
            "user_id": user_id,
            "status": "error",
            "message": f"Failed to check user access: {str(e)}"
        }