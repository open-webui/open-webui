// Fix for model avatars showing broken /logo.png
// This script generates abbreviations from model names

// Function to generate abbreviation from model name
function getModelAbbreviation(modelName) {
    if (!modelName) return 'M';
    
    // Handle common patterns
    if (modelName.toLowerCase().includes('gpt')) return 'GPT';
    if (modelName.toLowerCase().includes('claude')) return 'CL';
    if (modelName.toLowerCase().includes('llama')) return 'LL';
    if (modelName.toLowerCase().includes('mistral')) return 'MS';
    if (modelName.toLowerCase().includes('gemini')) return 'GM';
    
    // Generate from first letters of words
    const words = modelName.split(/[\s-_]/);
    if (words.length >= 2) {
        return words.slice(0, 2).map(w => w[0].toUpperCase()).join('');
    }
    
    // Default to first 2 characters
    return modelName.slice(0, 2).toUpperCase();
}

// Replace broken model images with abbreviations
document.addEventListener('DOMContentLoaded', function() {
    // Monitor for dynamic content
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            // Find all model profile images
            const modelImages = document.querySelectorAll('img[alt="model profile"][src="/logo.png"]');
            
            modelImages.forEach(img => {
                // Get model name from parent context
                const modelNameEl = img.closest('[data-model-name]') || 
                                   img.closest('.model-item')?.querySelector('.model-name') ||
                                   img.parentElement?.parentElement?.querySelector('[class*="font-semibold"]');
                
                const modelName = modelNameEl?.textContent || 'Model';
                const abbr = getModelAbbreviation(modelName);
                
                // Create replacement div
                const avatarDiv = document.createElement('div');
                avatarDiv.className = 'rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center shrink-0';
                avatarDiv.style.cssText = img.className.includes('size-72') 
                    ? 'width: 18rem; height: 18rem;' 
                    : 'width: 15rem; height: 15rem;';
                
                const abbrevSpan = document.createElement('span');
                abbrevSpan.className = 'text-4xl font-bold text-gray-600 dark:text-gray-400';
                abbrevSpan.textContent = abbr;
                
                avatarDiv.appendChild(abbrevSpan);
                
                // Replace image with div
                img.replaceWith(avatarDiv);
            });
        });
    });
    
    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Initial run
    setTimeout(() => {
        document.querySelectorAll('img[alt="model profile"][src="/logo.png"]').forEach(img => {
            const event = new Event('DOMNodeInserted', { bubbles: true });
            img.dispatchEvent(event);
        });
    }, 100);
});