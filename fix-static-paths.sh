#!/bin/bash
# Fix static file paths in JavaScript

echo "Fixing static file paths..."

# Fix all references to /logo.png to use /static/logo.png
find /app/build -name "*.js" -type f | while read file; do
    echo "Processing $file..."
    
    # Fix model profile images specifically
    # Handle JSX format: {src:"/logo.png",alt:"model profile"}
    sed -i 's|{src:"/logo\.png",alt:"model profile"|{src:"/static/logo.png",alt:"model profile"|g' "$file"
    
    # Handle HTML attribute format: src="/logo.png" alt="model profile"
    sed -i 's|src="/logo\.png" alt="model profile"|src="/static/logo.png" alt="model profile"|g' "$file"
    
    # Handle reverse order: alt="model profile" src="/logo.png"
    sed -i 's|alt="model profile" src="/logo\.png"|alt="model profile" src="/static/logo.png"|g' "$file"
    
    # General replacements for all /logo.png references
    sed -i 's|src="/logo\.png"|src="/static/logo.png"|g' "$file"
    sed -i 's|src:"/logo\.png"|src:"/static/logo.png"|g' "$file"
    sed -i "s|src='/logo\.png'|src='/static/logo.png'|g" "$file"
    sed -i "s|src:'/logo\.png'|src:'/static/logo.png'|g" "$file"
    
    # Fix concatenated paths
    sed -i 's|="/logo\.png"|="/static/logo.png"|g' "$file"
    sed -i 's|="/favicon\.png"|="/static/favicon.png"|g' "$file"
    sed -i 's|="/splash\.png"|="/static/splash.png"|g' "$file"
    
    # Fix any path construction patterns
    sed -i 's|+"/logo\.png"|+"/static/logo.png"|g' "$file"
    sed -i 's|`/logo\.png`|`/static/logo.png`|g' "$file"
done

# Copy logo.png to static directory to ensure it exists
if [ -f /tmp/logo.png ]; then
    echo "Copying logo.png to static directory..."
    mkdir -p /app/backend/open_webui/static
    cp /tmp/logo.png /app/backend/open_webui/static/logo.png
fi

# Also check HTML files
if [ -f /app/build/index.html ]; then
    echo "Fixing paths in index.html..."
    sed -i 's|href="/logo\.png"|href="/static/logo.png"|g' /app/build/index.html
    sed -i 's|src="/logo\.png"|src="/static/logo.png"|g' /app/build/index.html
fi

echo "Static paths fixed!"