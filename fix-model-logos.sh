#!/bin/bash
# Fix model logo display by replacing with abbreviations

echo "Fixing model logo display..."

# Find and replace model image display with abbreviations
find /app/build -name "*.js" -type f -exec grep -l 'size-72 md:size-60.*logo\.png' {} \; | while read file; do
    echo "Patching model logos in $file..."
    
    # Replace the img tag with a div showing model abbreviation
    # This targets the specific pattern for model profile images
    sed -i 's|<img[^>]*src="\/logo\.png"[^>]*alt="model profile"[^>]*class="[^"]*size-72 md:size-60[^"]*"[^>]*>|<div class="rounded-xl size-72 md:size-60 bg-gray-100 dark:bg-gray-800 flex items-center justify-center shrink-0"><span class="text-4xl font-bold text-gray-600 dark:text-gray-400">{{MODEL_ABBR}}</span></div>|g' "$file"
    
    # Also try to replace the pattern with different quote styles
    sed -i "s|<img[^>]*src='/logo\.png'[^>]*alt='model profile'[^>]*class='[^']*size-72 md:size-60[^']*'[^>]*>|<div class='rounded-xl size-72 md:size-60 bg-gray-100 dark:bg-gray-800 flex items-center justify-center shrink-0'><span class='text-4xl font-bold text-gray-600 dark:text-gray-400'>{{MODEL_ABBR}}</span></div>|g" "$file"
done

# Alternative approach - replace the specific function that renders model images
find /app/build -name "*.js" -type f | while read file; do
    # Look for the pattern that creates model profile images
    if grep -q 'alt:"model profile".*class:".*size-72 md:size-60' "$file"; then
        echo "Found model profile image in $file"
        
        # Replace with a function that generates abbreviations
        sed -i 's/m(e,"src",t="\/logo\.png")/m(e,"style","display:none")/g' "$file"
        sed -i 's/m(e,"alt","model profile")/m(e,"data-model","true")/g' "$file"
    fi
done

echo "Model logo fix applied!"