#!/usr/bin/env python3
import subprocess

# Test the subscription calculations
cmd = [
    "docker", "exec", "open-webui-customization", "python", "-c",
    """
import sys
sys.path.append('/app/backend')
from open_webui.models.users import Users
from datetime import datetime
import calendar

# Get all users - handle the dict format
users_response = Users.get_users()
if isinstance(users_response, dict) and 'users' in users_response:
    users = users_response['users']
else:
    users = users_response
print(f'Total users: {len(users)}')

# Get current month info
now = datetime.now()
current_month = now.month
current_year = now.year
days_in_month = calendar.monthrange(current_year, current_month)[1]
print(f'Current month: {current_month}/{current_year}, Days in month: {days_in_month}')

# Pricing tiers
total_users = len(users)
if total_users <= 5:
    tier_price = 49
    tier_name = "1-5 users"
elif total_users <= 10:
    tier_price = 39
    tier_name = "6-10 users"
elif total_users <= 15:
    tier_price = 29
    tier_name = "11-15 users"
else:
    tier_price = 19
    tier_name = "16+ users"

print(f'\\nPricing tier: {tier_name} @ {tier_price} PLN per user/month')

# Calculate total
total_cost = 0.0
print('\\nUser details:')
for i, user in enumerate(users):
    created_date = datetime.fromtimestamp(user.created_at)
    date_str = created_date.strftime('%Y-%m-%d')
    
    # Calculate proportional billing
    if created_date.year == current_year and created_date.month == current_month:
        days_remaining = days_in_month - created_date.day + 1
        billing_proportion = days_remaining / days_in_month
    else:
        days_remaining = days_in_month
        billing_proportion = 1.0
    
    user_cost = tier_price * billing_proportion
    total_cost += user_cost
    
    print(f'  User {i+1}: {user.name} ({user.email})')
    print(f'    Created: {date_str}')
    print(f'    Billing: {days_remaining}/{days_in_month} days = {billing_proportion:.1%}')
    print(f'    Cost: {user_cost:.2f} PLN')

print(f'\\nTotal monthly cost: {total_cost:.2f} PLN')
"""
]

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)