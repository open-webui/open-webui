# XYNTHOR AI Favicon Setup

## Method 1: Using External URL (recommended)

The patch `001-xynthor-branding.patch` is already configured to use favicon from:
```
https://chatbot.xynthor.com/favicon.ico
```

## Method 2: Local Favicon Files

1. **Prepare favicon files:**
   - `xynthor-favicon.ico` - main favicon (16x16, 32x32, 48x48)
   - `xynthor-favicon.png` - PNG version (500x500)
   - `xynthor-favicon-96x96.png` - for high resolution displays
   - `xynthor-favicon.svg` - vector version
   - `xynthor-apple-touch-icon.png` - for iOS (180x180)

2. **Place the files:**
   ```bash
   cp your-favicon-files/* xynthorai-open-webui/static/
   ```

3. **Use alternative patch:**
   ```bash
   git apply patches/001-xynthor-branding-alt.patch
   ```

## Method 3: Via Dockerfile

Add to `Dockerfile.custom`:
```dockerfile
# Copy custom favicons
COPY custom-favicon/* /app/backend/static/
```

## Favicon Generation

Use online services:
- https://favicon.io/
- https://realfavicongenerator.net/

Or via ImageMagick:
```bash
# Create ICO from PNG logo
convert logo.png -resize 16x16 favicon-16.png
convert logo.png -resize 32x32 favicon-32.png
convert logo.png -resize 48x48 favicon-48.png
convert favicon-16.png favicon-32.png favicon-48.png favicon.ico

# Create different sizes
convert logo.png -resize 96x96 favicon-96x96.png
convert logo.png -resize 180x180 apple-touch-icon.png
```

## Verification

After build and launch:
1. Clear browser cache (Ctrl+F5)
2. Check in DevTools > Network that favicon is loading
3. Check on different devices (desktop, mobile, iOS)