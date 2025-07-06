#!/bin/bash
# Apply XYNTHOR branding to built files

echo "Applying XYNTHOR branding..."

# Replace in index.html
if [ -f /app/build/index.html ]; then
    echo "Patching index.html..."
    sed -i 's|<link rel="icon" type="image/png" href="/static/favicon.png" />|<link rel="icon" type="image/png" href="https://chatbot.xynthor.com/favicon.ico" />|g' /app/build/index.html
    sed -i 's|<link rel="icon" type="image/png" href="/static/favicon-96x96.png" sizes="96x96" />|<link rel="icon" type="image/png" href="https://chatbot.xynthor.com/favicon.ico" sizes="96x96" />|g' /app/build/index.html
    sed -i 's|<link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />|<link rel="icon" type="image/svg+xml" href="https://chatbot.xynthor.com/favicon.ico" />|g' /app/build/index.html
    sed -i 's|<link rel="shortcut icon" href="/static/favicon.ico" />|<link rel="shortcut icon" href="https://chatbot.xynthor.com/favicon.ico" />|g' /app/build/index.html
    sed -i 's|<link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png" />|<link rel="apple-touch-icon" sizes="180x180" href="https://chatbot.xynthor.com/favicon.ico" />|g' /app/build/index.html
    sed -i 's|content="Open WebUI"|content="XYNTHOR AI"|g' /app/build/index.html
    sed -i 's|title="Open WebUI"|title="XYNTHOR AI"|g' /app/build/index.html
    sed -i 's|<title>Open WebUI</title>|<title>XYNTHOR AI</title>|g' /app/build/index.html
fi

# Replace in JavaScript bundles (carefully)
find /app/build -name "*.js" -type f -exec grep -l "Open WebUI" {} \; | while read file; do
    echo "Patching $file..."
    # Only replace specific instances to avoid breaking code
    sed -i 's/"Open WebUI"/"XYNTHOR AI"/g' "$file"
    sed -i "s/'Open WebUI'/'XYNTHOR AI'/g" "$file"
done

# Replace logo references
find /app/build -name "*.js" -type f -exec grep -l "/static/logo.svg" {} \; | while read file; do
    echo "Patching logo in $file..."
    sed -i 's|/static/logo.svg|https://chatbot.xynthor.com/_next/image?url=%2F_next%2Fstatic%2Fmedia%2Flogo-grey-4.24c43a6d.png\&w=640\&q=75|g' "$file"
done

echo "Branding applied successfully!"