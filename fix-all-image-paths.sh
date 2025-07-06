#!/bin/bash
# Fix all image paths to use /static/ prefix

echo "Fixing all image paths to use /static/ prefix..."

# Fix all references to images without /static/ prefix
find /app/build -name "*.js" -type f | while read file; do
    echo "Processing $file..."
    
    # Fix direct paths (favicon, logo, splash) to use /static/
    # Handle different quote styles and formats
    
    # Fix src="/favicon.png" and similar
    sed -i 's|src="/favicon\.png"|src="/static/favicon.png"|g' "$file"
    sed -i 's|src="/favicon\.ico"|src="/static/favicon.ico"|g' "$file"
    sed -i 's|src="/logo\.png"|src="/static/logo.png"|g' "$file"
    sed -i 's|src="/splash\.png"|src="/static/splash.png"|g' "$file"
    
    # Fix src='/favicon.png' and similar (single quotes)
    sed -i "s|src='/favicon\.png'|src='/static/favicon.png'|g" "$file"
    sed -i "s|src='/favicon\.ico'|src='/static/favicon.ico'|g" "$file"
    sed -i "s|src='/logo\.png'|src='/static/logo.png'|g" "$file"
    sed -i "s|src='/splash\.png'|src='/static/splash.png'|g" "$file"
    
    # Fix JSX format src:"/favicon.png" and similar
    sed -i 's|src:"/favicon\.png"|src:"/static/favicon.png"|g' "$file"
    sed -i 's|src:"/favicon\.ico"|src:"/static/favicon.ico"|g' "$file"
    sed -i 's|src:"/logo\.png"|src:"/static/logo.png"|g' "$file"
    sed -i 's|src:"/splash\.png"|src:"/static/splash.png"|g' "$file"
    
    # Fix JSX format with single quotes
    sed -i "s|src:'/favicon\.png'|src:'/static/favicon.png'|g" "$file"
    sed -i "s|src:'/favicon\.ico'|src:'/static/favicon.ico'|g" "$file"
    sed -i "s|src:'/logo\.png'|src:'/static/logo.png'|g" "$file"
    sed -i "s|src:'/splash\.png'|src:'/static/splash.png'|g" "$file"
    
    # Fix href paths
    sed -i 's|href="/favicon\.png"|href="/static/favicon.png"|g' "$file"
    sed -i 's|href="/favicon\.ico"|href="/static/favicon.ico"|g' "$file"
    sed -i 's|href="/logo\.png"|href="/static/logo.png"|g' "$file"
    
    # Fix concatenated paths
    sed -i 's|="/favicon\.png"|="/static/favicon.png"|g' "$file"
    sed -i 's|="/favicon\.ico"|="/static/favicon.ico"|g' "$file"
    sed -i 's|="/logo\.png"|="/static/logo.png"|g' "$file"
    sed -i 's|="/splash\.png"|="/static/splash.png"|g' "$file"
    
    # Fix path construction
    sed -i 's|+"/favicon\.png"|+"/static/favicon.png"|g' "$file"
    sed -i 's|+"/favicon\.ico"|+"/static/favicon.ico"|g' "$file"
    sed -i 's|+"/logo\.png"|+"/static/logo.png"|g' "$file"
    sed -i 's|+"/splash\.png"|+"/static/splash.png"|g' "$file"
    
    # Fix template literals
    sed -i 's|`/favicon\.png`|`/static/favicon.png`|g' "$file"
    sed -i 's|`/favicon\.ico`|`/static/favicon.ico`|g' "$file"
    sed -i 's|`/logo\.png`|`/static/logo.png`|g' "$file"
    sed -i 's|`/splash\.png`|`/static/splash.png`|g' "$file"
done

# Also check HTML files
if [ -f /app/build/index.html ]; then
    echo "Fixing paths in index.html..."
    sed -i 's|href="/favicon\.png"|href="/static/favicon.png"|g' /app/build/index.html
    sed -i 's|href="/favicon\.ico"|href="/static/favicon.ico"|g' /app/build/index.html
    sed -i 's|src="/favicon\.png"|src="/static/favicon.png"|g' /app/build/index.html
    sed -i 's|src="/logo\.png"|src="/static/logo.png"|g' /app/build/index.html
fi

# Fix CSS files
find /app/build -name "*.css" -type f | while read file; do
    echo "Fixing CSS $file..."
    sed -i 's|url("/favicon\.png"|url("/static/favicon.png"|g' "$file"
    sed -i 's|url("/logo\.png"|url("/static/logo.png"|g' "$file"
    sed -i 's|url(/favicon\.png|url(/static/favicon.png|g' "$file"
    sed -i 's|url(/logo\.png|url(/static/logo.png|g' "$file"
done

echo "All image paths fixed!"