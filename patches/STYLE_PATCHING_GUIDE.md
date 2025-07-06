# Style Patching Guide for Open WebUI

## Overview
This guide explains how to create patches for styling changes in Open WebUI, including themes, colors, fonts, and layouts.

## Finding Style Files

### 1. Main Style Locations
- **Tailwind Config**: `tailwind.config.js` - Main theme configuration
- **Global CSS**: `static/custom.css` - Custom global styles
- **Component Styles**: `src/lib/components/*.svelte` - Inline Svelte styles
- **Theme Variables**: `src/lib/constants/themes.js` - Theme definitions

### 2. Common Style Elements
```bash
# Find all style-related files
find . -name "*.css" -o -name "*.scss" -o -name "tailwind.config.js"

# Search for specific color values
grep -r "#171717" src/  # Dark theme background
grep -r "text-white" src/  # Text colors
```

## Creating Style Patches

### Step 1: Identify Files to Modify
```bash
# Example: Change primary color
grep -r "primary" src/lib/components/
grep -r "blue-600" src/
```

### Step 2: Make Changes
```bash
# Edit the files
vim tailwind.config.js
vim src/lib/components/layout/Navbar.svelte
```

### Step 3: Create Patch
```bash
# Stage your changes
git add tailwind.config.js src/lib/components/layout/Navbar.svelte

# Create patch
git diff --cached > patches/004-custom-theme.patch
```

## Common Style Customizations

### 1. Brand Colors
Create `patches/004-brand-colors.patch`:
```diff
diff --git a/tailwind.config.js b/tailwind.config.js
index abc123..def456 100644
--- a/tailwind.config.js
+++ b/tailwind.config.js
@@ -10,7 +10,11 @@ export default {
     extend: {
       colors: {
         primary: {
-          DEFAULT: '#3b82f6', // blue-500
+          DEFAULT: '#f97316', // orange-500 for XYNTHOR
+          50: '#fff7ed',
+          500: '#f97316',
+          600: '#ea580c',
+          700: '#c2410c',
         }
       }
     }
```

### 2. Dark Theme Background
Create `patches/005-dark-theme.patch`:
```diff
diff --git a/src/app.css b/src/app.css
index abc123..def456 100644
--- a/src/app.css
+++ b/src/app.css
@@ -5,7 +5,7 @@
 :root {
   --color-bg-primary: #ffffff;
   --color-bg-secondary: #f3f4f6;
-  --color-bg-dark: #171717;
+  --color-bg-dark: #1a1a2e; /* XYNTHOR dark blue */
 }
```

### 3. Font Family
Create `patches/006-custom-fonts.patch`:
```diff
diff --git a/src/app.html b/src/app.html
index abc123..def456 100644
--- a/src/app.html
+++ b/src/app.html
@@ -20,6 +20,8 @@
   <link rel="stylesheet" href="/static/custom.css" />
+  <link rel="preconnect" href="https://fonts.googleapis.com">
+  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
 </head>
```

### 4. Component Styles
For Svelte components with scoped styles:
```diff
diff --git a/src/lib/components/layout/Navbar.svelte b/src/lib/components/layout/Navbar.svelte
index abc123..def456 100644
--- a/src/lib/components/layout/Navbar.svelte
+++ b/src/lib/components/layout/Navbar.svelte
@@ -100,4 +100,15 @@
+<style>
+  :global(.navbar-custom) {
+    background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
+    border-bottom: 2px solid #f97316;
+  }
+  
+  :global(.navbar-logo) {
+    filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.5));
+  }
+</style>
```

## Testing Style Changes

### 1. Local Development
```bash
# Run development server
npm run dev

# Hot reload will show changes immediately
```

### 2. Build and Test
```bash
# Build the application
npm run build

# Test in Docker
docker build -f Dockerfile.custom -t test-styles .
docker run -p 8080:8080 test-styles
```

## Best Practices

### 1. Use CSS Variables
Instead of hardcoding colors, use CSS variables:
```css
/* Define in root */
:root {
  --brand-primary: #f97316;
  --brand-secondary: #1a1a2e;
}

/* Use throughout */
.button-primary {
  background-color: var(--brand-primary);
}
```

### 2. Maintain Dark/Light Theme Support
Always provide both theme variants:
```css
/* Light theme */
[data-theme="light"] {
  --bg-primary: #ffffff;
  --text-primary: #171717;
}

/* Dark theme */
[data-theme="dark"] {
  --bg-primary: #171717;
  --text-primary: #ffffff;
}
```

### 3. Keep Patches Small
Create separate patches for:
- Colors (`004-brand-colors.patch`)
- Typography (`005-typography.patch`)
- Layout (`006-layout-adjustments.patch`)
- Components (`007-component-styles.patch`)

### 4. Document Changes
Add comments in your patches:
```css
/* XYNTHOR: Custom brand color */
--color-primary: #f97316;
```

## Advanced Styling

### 1. Custom Tailwind Plugins
Create `patches/008-tailwind-plugin.patch`:
```javascript
// tailwind.config.js
plugins: [
  function({ addUtilities }) {
    addUtilities({
      '.text-gradient': {
        'background-image': 'linear-gradient(45deg, #f97316, #dc2626)',
        '-webkit-background-clip': 'text',
        '-webkit-text-fill-color': 'transparent',
      }
    })
  }
]
```

### 2. Animation and Transitions
```css
/* Custom animations */
@keyframes pulse-orange {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(249, 115, 22, 0);
  }
}

.btn-primary {
  animation: pulse-orange 2s infinite;
}
```

## Troubleshooting

### Styles Not Applying
1. Clear browser cache
2. Check CSS specificity
3. Verify patch was applied correctly
4. Check for CSS purging in production

### Build Issues
1. Run `npm run build` to check for errors
2. Verify Tailwind classes are not purged
3. Check PostCSS configuration

### Performance
1. Minimize custom CSS
2. Use Tailwind utilities when possible
3. Avoid deep CSS nesting