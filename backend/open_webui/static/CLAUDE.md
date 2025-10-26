# Static Directory

This directory contains static assets served by the FastAPI backend, including branding assets (logos, favicons), fonts, custom styling, Swagger UI documentation, and sample files. These files are served directly via HTTP without processing.

## Purpose

This directory provides:
- **Branding Assets**: Logos, favicons, app icons for various devices
- **Web Fonts**: Custom fonts for consistent typography
- **API Documentation**: Swagger UI for exploring REST API
- **Custom Styling**: user-modifiable CSS for theming
- **Sample Files**: Example files for import features

## Directory Structure

### Root Files

**Branding & Icons:**
- `logo.png` - Main Open WebUI logo (used in UI)
- `favicon.ico` - Browser favicon (ICO format)
- `favicon.png` - Favicon (PNG format, 32x32)
- `favicon-dark.png` - Dark theme favicon
- `favicon.svg` - Scalable vector favicon
- `favicon-96x96.png` - High-resolution favicon
- `apple-touch-icon.png` - iOS home screen icon
- `splash.png` - Light theme splash screen
- `splash-dark.png` - Dark theme splash screen
- `web-app-manifest-192x192.png` - PWA icon (Android)
- `web-app-manifest-512x512.png` - PWA icon (Android, high-res)

**Configuration Files:**
- `site.webmanifest` - PWA manifest (app name, icons, theme color)
- `custom.css` - User-editable custom CSS (empty by default)

**Sample Data:**
- `user-import.csv` - CSV template for bulk user import

**Scripts:**
- `loader.js` - Frontend loading script (empty placeholder)

### assets/ - Build Artifacts
**Purpose:** Contains frontend build outputs (JavaScript, CSS bundles)

**Contents:**
- Vite/SvelteKit build artifacts
- Hashed filenames for cache busting
- Typically generated during `npm run build`

**Note:** Contents change with each frontend build.

### fonts/ - Web Fonts
**Purpose:** Custom fonts for consistent typography across browsers.

**Common Files:**
- `*.woff2` - Web Open Font Format 2 (compressed)
- `*.woff` - Web Open Font Format 1
- `*.ttf` - TrueType fonts (fallback)

**Typical Fonts:**
- Inter (UI font)
- Roboto Mono (code font)
- Or custom brand fonts

**Loading:**
```css
/* In global CSS */
@font-face {
  font-family: 'Inter';
  src: url('/static/fonts/Inter-Regular.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
}
```

### swagger-ui/ - API Documentation
**Purpose:** Swagger UI static files for interactive API documentation.

**Contents:**
- `swagger-ui.css` - Swagger UI styling
- `swagger-ui-bundle.js` - Swagger UI JavaScript
- `swagger-ui-standalone-preset.js` - Standalone preset
- `favicon-*.png` - Swagger UI favicons

**Access:** Served at `/docs` endpoint (FastAPI auto-generates API docs)

**Usage:**
```
Navigate to https://your-open-webui.com/docs
↓
FastAPI serves OpenAPI spec (auto-generated)
↓
Swagger UI renders interactive docs
↓
Test API endpoints directly in browser
```

## Integration Points

### main.py → static/
**Static File Serving:** FastAPI mounts static directory.

```python
# In main.py
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="open_webui/static"), name="static")
```

**Access Pattern:**
- URL: `https://your-domain.com/static/logo.png`
- Maps to: `backend/open_webui/static/logo.png`

### Frontend → static/
**Asset References:** Frontend references static assets in HTML/CSS.

```html
<!-- In frontend index.html -->
<link rel="icon" type="image/png" href="/static/favicon.png">
<link rel="manifest" href="/static/site.webmanifest">
<link rel="stylesheet" href="/static/custom.css">
```

### PWA Configuration → static/
**Progressive Web App:** site.webmanifest defines PWA behavior.

```json
{
  "name": "Open WebUI",
  "short_name": "OpenWebUI",
  "icons": [
    {
      "src": "/static/web-app-manifest-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/web-app-manifest-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#ffffff",
  "background_color": "#ffffff",
  "display": "standalone"
}
```

### Swagger UI → static/swagger-ui/
**API Documentation:** FastAPI serves Swagger UI from this directory.

```python
# FastAPI auto-configuration
app = FastAPI(
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # Alternative docs
)
```

## Customization

### Custom Branding

**Replace Logo:**
1. Replace `static/logo.png` with custom logo
2. Restart application
3. New logo appears in UI

**Replace Favicons:**
1. Generate favicon set (use favicon generator)
2. Replace all favicon-*.png files
3. Update `site.webmanifest` if needed
4. Clear browser cache

### Custom Styling

**Add Custom CSS:**
1. Edit `static/custom.css`:
   ```css
   /* Custom styles */
   :root {
     --primary-color: #your-brand-color;
   }

   .sidebar {
     background: linear-gradient(...);
   }
   ```
2. Save file
3. Frontend automatically loads `custom.css`
4. Styles override defaults

**Advantages:**
- No need to rebuild frontend
- Persists across updates
- User-specific theming

### Font Customization

**Add Custom Font:**
1. Place font files in `static/fonts/`
2. Add `@font-face` declaration in `custom.css`:
   ```css
   @font-face {
     font-family: 'MyCustomFont';
     src: url('/static/fonts/MyCustomFont.woff2') format('woff2');
   }

   body {
     font-family: 'MyCustomFont', sans-serif;
   }
   ```
3. Font available throughout app

## Important Notes

### Static vs Dynamic Content
- **Static files**: Served as-is, no processing
- **Dynamic content**: Generated by FastAPI (HTML templates, API responses)
- Assets in `static/` never change at runtime

### Caching
**Browser Caching:**
- Static assets typically cached by browsers
- Use cache busting for updates (rename file or add query param)
- `assets/` uses hashed filenames (automatic cache busting)

**Recommended Headers:**
```python
# In main.py for static files
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 year
    return response
```

### File Size Considerations
- Keep files small for fast loading
- Optimize images (compress PNGs)
- Use WOFF2 for fonts (best compression)
- Consider CDN for production

### Security
- No sensitive data in static/ (publicly accessible)
- User-uploaded files go to `data/uploads/`, not here
- Custom CSS could be XSS vector (sanitize if user-editable in UI)

### Version Control
- **Do commit**: Branding assets, fonts, sample files
- **Don't commit**: Build artifacts in `assets/` (generated)
- Add to `.gitignore`: `static/assets/*`

### Development vs Production
**Development:**
- Frontend dev server serves assets
- `static/` may not be used

**Production:**
- Frontend built and placed in `static/assets/`
- Backend serves everything from `static/`

### Troubleshooting

**Assets Not Loading:**
1. Check URL path (must start with `/static/`)
2. Verify file exists in `static/` directory
3. Check FastAPI logs for 404 errors
4. Ensure static mount configured in `main.py`

**Custom CSS Not Applied:**
1. Check browser console for CSS errors
2. Clear browser cache (hard refresh)
3. Verify `/static/custom.css` loads (Network tab)
4. Check CSS specificity (may need `!important`)

**PWA Not Installing:**
1. Check `site.webmanifest` valid JSON
2. Ensure HTTPS (PWAs require secure context)
3. Verify all referenced icons exist
4. Check browser console for manifest errors

### Future Improvements
Potential enhancements:
- Asset pipeline (minification, compression)
- CDN integration for static assets
- Automated favicon generation from single logo
- Theme builder UI (no manual CSS editing)
- Asset versioning system
