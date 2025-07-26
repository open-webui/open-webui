#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime

# Test the subscription billing calculations
cmd = '''docker exec open-webui-customization python -c "
import sys
sys.path.append('/app/backend')
from open_webui.models.users import Users
from datetime import datetime
import calendar

# Get all users
users = Users.get_users()
print(f'Total users: {len(users)}')

# Get current month info
now = datetime.now()
current_month = now.month
current_year = now.year
days_in_month = calendar.monthrange(current_year, current_month)[1]
print(f'Current month: {current_month}/{current_year}, Days in month: {days_in_month}')

# Define pricing tiers
pricing_tiers = [
    {'min': 1, 'max': 5, 'price': 49},
    {'min': 6, 'max': 10, 'price': 39},
    {'min': 11, 'max': 15, 'price': 29},
    {'min': 16, 'max': float('inf'), 'price': 19}
]

# Determine current tier
total_users = len(users)
current_tier_price = 49
for tier in pricing_tiers:
    if tier['min'] <= total_users <= tier['max']:
        current_tier_price = tier['price']
        print(f'Current tier: {tier[\"min\"]}-{tier[\"max\"]} users @ {tier[\"price\"]} PLN/user')
        break

# Calculate billing for each user
print('\\nUser billing details:')
total_cost = 0.0
for i, user_id in enumerate(users):
    user = Users.get_user_by_id(user_id)
    if user:
        created_date = datetime.fromtimestamp(user.created_at)
        
        # Calculate proportional billing
        if created_date.year == current_year and created_date.month == current_month:
            days_remaining = days_in_month - created_date.day + 1
            billing_proportion = days_remaining / days_in_month
        else:
            days_remaining = days_in_month
            billing_proportion = 1.0
        
        user_cost = current_tier_price * billing_proportion
        total_cost += user_cost
        
        print(f'  User {i+1}: {user.name} ({user.email})')
        print(f'    - Created: {created_date.strftime(\\'%Y-%m-%d\\')}')
        print(f'    - Days in month: {days_remaining}/{days_in_month}')
        print(f'    - Billing proportion: {billing_proportion:.2%}')
        print(f'    - Monthly cost: {user_cost:.2f} PLN')

print(f'\\nTotal monthly subscription cost: {total_cost:.2f} PLN')
print(f'With {total_users} users, using tier: {current_tier_price} PLN/user')
"'''

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)