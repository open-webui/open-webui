#!/bin/bash
# Apply XYNTHOR branding with local assets

echo "Applying XYNTHOR branding with local assets..."

# Replace in index.html
if [ -f /app/build/index.html ]; then
    echo "Patching index.html..."
    # Replace favicon references with local files
    sed -i 's|href="/static/favicon.png"|href="/favicon.ico"|g' /app/build/index.html
    sed -i 's|href="/static/favicon-96x96.png"|href="/favicon.ico"|g' /app/build/index.html
    sed -i 's|href="/static/favicon.svg"|href="/favicon.ico"|g' /app/build/index.html
    sed -i 's|href="/static/favicon.ico"|href="/favicon.ico"|g' /app/build/index.html
    sed -i 's|href="/static/apple-touch-icon.png"|href="/favicon.ico"|g' /app/build/index.html
    
    # Replace text
    sed -i 's|content="Open WebUI"|content="XYNTHOR AI"|g' /app/build/index.html
    sed -i 's|title="Open WebUI"|title="XYNTHOR AI"|g' /app/build/index.html
    sed -i 's|<title>Open WebUI</title>|<title>XYNTHOR AI</title>|g' /app/build/index.html
    # Remove "(Open WebUI)" from title tag
    sed -i 's|<title>XYNTHOR AI (Open WebUI)</title>|<title>XYNTHOR AI</title>|g' /app/build/index.html
    sed -i 's|<title>XYNTHOR AI \((Open WebUI)\)</title>|<title>XYNTHOR AI</title>|g' /app/build/index.html
fi

# Replace in JavaScript bundles
find /app/build -name "*.js" -type f -exec grep -l "Open WebUI\|favicon\.png\|splash\.png" {} \; | while read file; do
    echo "Patching $file..."
    # Replace Open WebUI text
    sed -i 's/"Open WebUI"/"XYNTHOR AI"/g' "$file"
    sed -i "s/'Open WebUI'/'XYNTHOR AI'/g" "$file"
    sed -i 's/Open WebUI/XYNTHOR AI/g' "$file"
    # Remove (Open WebUI) suffix in all formats
    sed -i 's/"XYNTHOR AI (Open WebUI)"/"XYNTHOR AI"/g' "$file"
    sed -i "s/'XYNTHOR AI (Open WebUI)'/'XYNTHOR AI'/g" "$file"
    sed -i 's/XYNTHOR AI (Open WebUI)/XYNTHOR AI/g' "$file"
    sed -i 's/XYNTHOR AI \((Open WebUI)\)/XYNTHOR AI/g' "$file"
    sed -i 's/ (Open WebUI)//g' "$file"
    sed -i 's/ \((Open WebUI)\)//g' "$file"
    sed -i 's/(Open WebUI)//g' "$file"
    sed -i 's/\(Open WebUI\)//g' "$file"
done

# Replace logo references with local file
find /app/build -name "*.js" -type f -exec grep -l "/static/logo" {} \; | while read file; do
    echo "Patching logo in $file..."
    sed -i 's|/static/logo.svg|/logo.png|g' "$file"
    sed -i 's|/static/logo-dark.svg|/logo.png|g' "$file"
    sed -i 's|static/logo.svg|/logo.png|g' "$file"
done

# Replace favicon references
find /app/build -name "*.js" -type f -exec grep -l "favicon" {} \; | while read file; do
    echo "Patching favicon in $file..."
    sed -i 's|/static/favicon.ico|/favicon.ico|g' "$file"
    sed -i 's|/static/favicon.png|/logo.png|g' "$file"
    sed -i 's|"/static/favicon.png"|"/logo.png"|g' "$file"
    sed -i "s|'/static/favicon.png'|'/logo.png'|g" "$file"
    sed -i 's|static/favicon.png|logo.png|g' "$file"
done

# Replace splash screen logo
find /app/build -name "*.js" -type f -exec grep -l "splash.png" {} \; | while read file; do
    echo "Patching splash in $file..."
    sed -i 's|/static/splash.png|/logo.png|g' "$file"
    sed -i 's|"/static/splash.png"|"/logo.png"|g' "$file"
    sed -i "s|'/static/splash.png'|'/logo.png'|g" "$file"
    sed -i 's|static/splash.png|logo.png|g' "$file"
done

# Additional aggressive replacements for any remaining references
echo "Applying additional replacements..."
find /app/build -name "*.js" -type f | while read file; do
    # Replace any remaining logo references
    sed -i 's|/static/logo\.[a-zA-Z]*|/logo.png|g' "$file"
    sed -i 's|static/logo\.[a-zA-Z]*|logo.png|g' "$file"
    
    # Make sure all branding text is replaced
    sed -i 's|\bOpen WebUI\b|XYNTHOR AI|g' "$file"
    sed -i 's|\bopen webui\b|xynthor ai|g' "$file"
    sed -i 's|\bOPEN WEBUI\b|XYNTHOR AI|g' "$file"
done

# Replace in CSS files too
find /app/build -name "*.css" -type f | while read file; do
    echo "Patching CSS $file..."
    sed -i 's|/static/favicon.png|/logo.png|g' "$file"
    sed -i 's|/static/splash.png|/logo.png|g' "$file"
    sed -i 's|/static/logo\.[a-zA-Z]*|/logo.png|g' "$file"
done

# Copy assets to root for easy access
cp /app/static/logo.png /app/build/logo.png 2>/dev/null || true
cp /app/static/favicon.ico /app/build/favicon.ico 2>/dev/null || true

# Also copy to static directory in build
mkdir -p /app/build/static
cp /app/static/logo.png /app/build/static/favicon.png 2>/dev/null || true
cp /app/static/logo.png /app/build/static/splash.png 2>/dev/null || true
cp /app/static/logo.png /app/build/static/logo.png 2>/dev/null || true
cp /app/static/favicon.ico /app/build/static/favicon.ico 2>/dev/null || true

# Fix ALL image paths to use /static/ prefix
echo "Fixing all image paths to use /static/ prefix..."
find /app/build -name "*.js" -type f | while read file; do
    # Fix all variations of image paths without /static/
    # Fix src="/favicon.png" and similar
    sed -i 's|src="/favicon\.png"|src="/static/favicon.png"|g' "$file"
    sed -i 's|src="/favicon\.ico"|src="/static/favicon.ico"|g' "$file"
    sed -i 's|src="/logo\.png"|src="/static/logo.png"|g' "$file"
    sed -i 's|src="/splash\.png"|src="/static/splash.png"|g' "$file"
    
    # Fix single quotes
    sed -i "s|src='/favicon\.png'|src='/static/favicon.png'|g" "$file"
    sed -i "s|src='/logo\.png'|src='/static/logo.png'|g" "$file"
    
    # Fix JSX format
    sed -i 's|src:"/favicon\.png"|src:"/static/favicon.png"|g' "$file"
    sed -i 's|src:"/logo\.png"|src:"/static/logo.png"|g' "$file"
    
    # Fix any remaining paths
    sed -i 's|="/favicon\.png"|="/static/favicon.png"|g' "$file"
    sed -i 's|="/logo\.png"|="/static/logo.png"|g' "$file"
done

echo "Branding with local assets applied successfully!"