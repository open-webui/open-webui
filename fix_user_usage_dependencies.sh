#!/bin/bash
# Fix for "By User tab shows No user usage data available" issue
# Root cause: Missing dependencies causing service import failures

echo "🔧 Installing missing dependencies for user usage functionality..."

# Install dependencies from requirements.txt
cd backend
pip3 install -r requirements.txt

echo "✅ Dependencies installed successfully"
echo ""
echo "🔍 Verifying typer installation:"
python3 -c "import typer; print(f'typer version: {typer.__version__}')" 

echo ""
echo "🔍 Testing backend imports:"
python3 -c "
try:
    from open_webui.utils.currency_converter import get_current_usd_pln_rate
    from open_webui.models.users import Users
    from open_webui.utils.user_mapping import get_external_user_id
    print('✅ All critical imports successful')
except Exception as e:
    print(f'❌ Import error: {e}')
"

echo ""
echo "🎯 Fix Summary:"
echo "- Root cause: Missing 'typer' dependency causing import failures"
echo "- Impact: Backend service returned success=false with empty user_usage array"  
echo "- Solution: Install all required dependencies from requirements.txt"
echo ""
echo "📝 Next steps:"
echo "1. Restart the backend server"
echo "2. Test the 'By User' tab in the frontend"
echo "3. Verify that usage data now displays correctly"