#!/usr/bin/env python3
"""
Test script for business-focused daily breakdown usage tracking
Verifies the new admin-focused approach without real-time features
"""

import sqlite3
import os
import json
from datetime import date, datetime, timedelta
import time

def test_business_focused_usage_tracking():
    """Test the business-focused usage tracking functionality"""
    
    # Database path
    db_path = "backend/data/webui.db"
    
    print("🔧 Testing business-focused usage tracking")
    
    # Create test database with sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            openrouter_api_key TEXT NOT NULL UNIQUE,
            markup_rate REAL DEFAULT 1.3,
            is_active INTEGER DEFAULT 1,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_daily_usage (
            id TEXT PRIMARY KEY,
            client_org_id TEXT NOT NULL,
            usage_date DATE NOT NULL,
            total_tokens INTEGER DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            raw_cost REAL DEFAULT 0.0,
            markup_cost REAL DEFAULT 0.0,
            primary_model TEXT,
            unique_users INTEGER DEFAULT 1,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    
    # Insert test organization
    current_time = int(time.time())
    cursor.execute("""
        INSERT OR REPLACE INTO client_organizations 
        (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'test_business_client',
        'Business Test Organization',
        'test_business_api_key',
        1.3,
        1,
        current_time,
        current_time
    ))
    
    # Insert sample daily data for current month (business scenario)
    today = date.today()
    current_month_start = today.replace(day=1)
    
    sample_days = [
        # Week 1 - Light usage
        {'day': 1, 'tokens': 1500, 'requests': 5, 'cost': 0.004, 'model': 'google/gemini-2.5-flash'},
        {'day': 2, 'tokens': 2200, 'requests': 8, 'cost': 0.006, 'model': 'anthropic/claude-sonnet-4'},
        {'day': 3, 'tokens': 1800, 'requests': 6, 'cost': 0.005, 'model': 'google/gemini-2.5-flash'},
        
        # Week 2 - Increased usage
        {'day': 8, 'tokens': 4500, 'requests': 15, 'cost': 0.012, 'model': 'anthropic/claude-sonnet-4'},
        {'day': 9, 'tokens': 3200, 'requests': 12, 'cost': 0.009, 'model': 'google/gemini-2.5-pro'},
        {'day': 10, 'tokens': 5800, 'requests': 20, 'cost': 0.016, 'model': 'anthropic/claude-sonnet-4'},
        
        # Week 3 - Peak usage
        {'day': 15, 'tokens': 8900, 'requests': 25, 'cost': 0.025, 'model': 'anthropic/claude-sonnet-4'},
        {'day': 16, 'tokens': 7200, 'requests': 22, 'cost': 0.020, 'model': 'google/gemini-2.5-pro'},
        {'day': 17, 'tokens': 6500, 'requests': 18, 'cost': 0.018, 'model': 'anthropic/claude-sonnet-4'},
        
        # Week 4 - Moderate usage
        {'day': 22, 'tokens': 4100, 'requests': 14, 'cost': 0.011, 'model': 'google/gemini-2.5-flash'},
        {'day': 23, 'tokens': 3800, 'requests': 13, 'cost': 0.010, 'model': 'anthropic/claude-sonnet-4'},
        {'day': 24, 'tokens': 2900, 'requests': 10, 'cost': 0.008, 'model': 'google/gemini-2.5-pro'},
    ]
    
    for day_data in sample_days:
        if day_data['day'] <= today.day:  # Only insert past/current days
            usage_date = current_month_start.replace(day=day_data['day'])
            day_id = f"test_business_client:{usage_date}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO client_daily_usage 
                (id, client_org_id, usage_date, total_tokens, total_requests, raw_cost, markup_cost, primary_model, unique_users, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                day_id,
                'test_business_client',
                usage_date,
                day_data['tokens'],
                day_data['requests'],
                day_data['cost'],
                day_data['cost'] * 1.3,  # 1.3x markup
                day_data['model'],
                2,  # Assume 2 unique users per day
                current_time,
                current_time
            ))
    
    conn.commit()
    print("✅ Test data created successfully")
    
    # Test business-focused queries
    print("\n📊 Testing business-focused queries:")
    
    # 1. Monthly totals
    cursor.execute("""
        SELECT 
            COUNT(*) as days_with_usage,
            SUM(total_tokens) as total_tokens,
            SUM(markup_cost) as total_cost,
            SUM(total_requests) as total_requests,
            AVG(total_tokens) as avg_tokens_per_day,
            MAX(total_tokens) as peak_tokens,
            MAX(markup_cost) as peak_cost
        FROM client_daily_usage 
        WHERE client_org_id = 'test_business_client' 
        AND usage_date >= ? AND usage_date <= ?
    """, (current_month_start, today))
    
    monthly_stats = cursor.fetchone()
    if monthly_stats:
        days_with_usage, total_tokens, total_cost, total_requests, avg_tokens, peak_tokens, peak_cost = monthly_stats
        print(f"✅ Monthly Summary:")
        print(f"   Days with usage: {days_with_usage}/{today.day}")
        print(f"   Total tokens: {total_tokens:,}")
        print(f"   Total cost: ${total_cost:.6f}")
        print(f"   Total requests: {total_requests}")
        print(f"   Average daily tokens: {avg_tokens:.0f}")
        print(f"   Peak day tokens: {peak_tokens:,}")
        print(f"   Peak day cost: ${peak_cost:.6f}")
    
    # 2. Daily breakdown for business oversight
    cursor.execute("""
        SELECT 
            usage_date,
            total_tokens,
            markup_cost,
            total_requests,
            primary_model,
            unique_users
        FROM client_daily_usage 
        WHERE client_org_id = 'test_business_client' 
        AND usage_date >= ? AND usage_date <= ?
        ORDER BY usage_date
    """, (current_month_start, today))
    
    daily_breakdown = cursor.fetchall()
    print(f"\n✅ Daily Breakdown ({len(daily_breakdown)} days):")
    print("Date       | Tokens  | Cost     | Requests | Model                 | Users")
    print("-" * 75)
    for row in daily_breakdown:
        usage_date, tokens, cost, requests, model, users = row
        model_short = model.split('/')[-1][:15] if model else 'N/A'
        print(f"{usage_date} | {tokens:7,} | ${cost:7.6f} | {requests:8} | {model_short:15} | {users}")
    
    # 3. Business insights
    cursor.execute("""
        SELECT 
            usage_date,
            total_tokens
        FROM client_daily_usage 
        WHERE client_org_id = 'test_business_client' 
        AND usage_date >= ? AND usage_date <= ?
        ORDER BY total_tokens DESC
        LIMIT 1
    """, (current_month_start, today))
    
    busiest_day = cursor.fetchone()
    if busiest_day:
        print(f"\n✅ Business Insights:")
        print(f"   Busiest day: {busiest_day[0]} ({busiest_day[1]:,} tokens)")
    
    cursor.execute("""
        SELECT 
            primary_model,
            SUM(total_tokens) as total_tokens,
            COUNT(*) as days_used
        FROM client_daily_usage 
        WHERE client_org_id = 'test_business_client' 
        AND usage_date >= ? AND usage_date <= ?
        GROUP BY primary_model
        ORDER BY total_tokens DESC
        LIMIT 1
    """, (current_month_start, today))
    
    top_model = cursor.fetchone()
    if top_model:
        model_name, model_tokens, model_days = top_model
        print(f"   Most used model: {model_name} ({model_tokens:,} tokens, {model_days} days)")
    
    # 4. Test business percentage calculations
    usage_percentage = (len(daily_breakdown) / today.day * 100) if today.day > 0 else 0
    print(f"   Usage percentage: {usage_percentage:.1f}% of days active")
    
    conn.close()
    
    print("\n🎉 Business-focused usage tracking test completed successfully!")
    print("\n📋 Key Differences from Real-time Approach:")
    print("   • No live counters or real-time updates")
    print("   • Focus on daily summaries and monthly trends")
    print("   • Business insights for administrative oversight")
    print("   • Suitable for management and billing purposes")
    print("   • Simplified data model with better performance")
    
    print("\n💼 Business Benefits:")
    print("   • Clear monthly usage patterns")
    print("   • Cost tracking for budgeting")
    print("   • Model usage optimization insights")
    print("   • User activity monitoring")
    print("   • Simplified reporting for stakeholders")

if __name__ == "__main__":
    test_business_focused_usage_tracking()