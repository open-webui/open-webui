#!/bin/bash
# Fix all dynamic image paths in JavaScript

echo "Fixing all dynamic image paths..."

# Function to fix paths in a file
fix_file() {
    local file=$1
    echo "Processing $file..."
    
    # Fix all variations of image paths
    # Direct replacements
    sed -i 's|="/logo\.png"|="/static/logo.png"|g' "$file"
    sed -i 's|="/favicon\.png"|="/static/favicon.png"|g' "$file"
    sed -i 's|="/splash\.png"|="/static/splash.png"|g' "$file"
    
    # With quotes escaped
    sed -i 's|=\\"/logo\.png\\"|=\\"/static/logo.png\\"|g' "$file"
    sed -i 's|=\\"/favicon\.png\\"|=\\"/static/favicon.png\\"|g' "$file"
    
    # Object properties
    sed -i 's|src:"/logo\.png"|src:"/static/logo.png"|g' "$file"
    sed -i 's|src:"/favicon\.png"|src:"/static/favicon.png"|g' "$file"
    
    # With spaces
    sed -i 's|src: "/logo\.png"|src: "/static/logo.png"|g' "$file"
    sed -i 's|src: "/favicon\.png"|src: "/static/favicon.png"|g' "$file"
    
    # Template literals
    sed -i 's|`/logo\.png`|`/static/logo.png`|g' "$file"
    sed -i 's|`/favicon\.png`|`/static/favicon.png`|g' "$file"
    
    # Concatenation
    sed -i 's|+"/logo\.png"|+"/static/logo.png"|g' "$file"
    sed -i 's|+"/favicon\.png"|+"/static/favicon.png"|g' "$file"
    
    # Array elements
    sed -i 's|\["/logo\.png"\]|["/static/logo.png"]|g' "$file"
    sed -i 's|\["/favicon\.png"\]|["/static/favicon.png"]|g' "$file"
    
    # Function arguments
    sed -i 's|("/logo\.png"|("/static/logo.png"|g' "$file"
    sed -i 's|("/favicon\.png"|("/static/favicon.png"|g' "$file"
    
    # With single quotes
    sed -i "s|='/logo\.png'|='/static/logo.png'|g" "$file"
    sed -i "s|='/favicon\.png'|='/static/favicon.png'|g" "$file"
    sed -i "s|src:'/logo\.png'|src:'/static/logo.png'|g" "$file"
    sed -i "s|src:'/favicon\.png'|src:'/static/favicon.png'|g" "$file"
    
    # JSX properties
    sed -i 's|logo\.png"|static/logo.png"|g' "$file"
    sed -i 's|favicon\.png"|static/favicon.png"|g' "$file"
}

# Process all JavaScript files
find /app/build -name "*.js" -type f | while read file; do
    fix_file "$file"
done

# Also fix CSS files
find /app/build -name "*.css" -type f | while read file; do
    echo "Processing CSS $file..."
    sed -i 's|url("/logo\.png"|url("/static/logo.png"|g' "$file"
    sed -i 's|url("/favicon\.png"|url("/static/favicon.png"|g' "$file"
    sed -i 's|url(/logo\.png|url(/static/logo.png|g' "$file"
    sed -i 's|url(/favicon\.png|url(/static/favicon.png|g' "$file"
done

# Fix HTML files
if [ -f /app/build/index.html ]; then
    echo "Fixing index.html..."
    sed -i 's|src="/logo\.png"|src="/static/logo.png"|g' /app/build/index.html
    sed -i 's|src="/favicon\.png"|src="/static/favicon.png"|g' /app/build/index.html
    sed -i 's|href="/logo\.png"|href="/static/logo.png"|g' /app/build/index.html
    sed -i 's|href="/favicon\.png"|href="/static/favicon.png"|g' /app/build/index.html
fi

echo "Dynamic paths fixed!"