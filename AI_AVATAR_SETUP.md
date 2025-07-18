# mAI Avatar Setup Documentation

## Current Status
- Robot avatar has been removed
- Chat messages now display default favicon (OI logo)
- System is prepared for future mAI logo integration

## Files to Update When Adding mAI Logo

### 1. Create Logo Files
Place your mAI logo files in these locations:
- **Frontend**: `/static/static/mai-logo.png` (or .svg)
- **Backend**: `/backend/open_webui/static/mai-logo.png` (or .svg)

### 2. Update Avatar Display
Edit `/src/lib/components/chat/Messages/ResponseMessage.svelte`:
- Line 610: Change `favicon.png` to `mai-logo.png`

### 3. Update Default ProfileImage
Edit `/src/lib/components/chat/Messages/ProfileImage.svelte`:
- Line 5: Change default src to your logo
- Line 11: Change fallback src to your logo

## Example Update
```svelte
// Change this:
src={model?.info?.meta?.profile_image_url ??
    `${WEBUI_BASE_URL}/static/favicon.png`}

// To this:
src={model?.info?.meta?.profile_image_url ??
    `${WEBUI_BASE_URL}/static/mai-logo.png`}
```

## Logo Specifications
- **Size**: 32x32px minimum (SVG preferred for scalability)
- **Format**: PNG or SVG
- **Colors**: Should work on both light and dark themes
- **Style**: Circular or square (will be displayed as rounded circle)

## Quick Setup Command
When you have your logo ready:
1. Copy logo to both static folders
2. Update the 3 files mentioned above
3. Restart dev servers to see changes