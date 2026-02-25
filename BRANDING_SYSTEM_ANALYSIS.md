# Open WebUI Branding System Analysis

## Current Architecture

### 1. **Preset Schema** (`BrandingPreset` in `backend/open_webui/routers/configs.py`)

```python
class BrandingPreset(BaseModel):
    name: str                          # Preset identifier (e.g., "Foundations", "Magellan")
    accent_color: Optional[str]        # Hex color for accent (default: "#e3530f")
    accent_color_scale: Optional[dict] # Color scale mapping (50-950 shades)
    background_color: Optional[str]    # Background color (not used in frontend)
    logo_url: Optional[str]            # ✅ SUPPORTS per-preset
    logo_dark_url: Optional[str]       # ✅ SUPPORTS per-preset
    favicon_url: Optional[str]         # ✅ SUPPORTS per-preset
    login_background_url: Optional[str] # ✅ SUPPORTS per-preset
    login_background_color: Optional[str] # ✅ SUPPORTS per-preset
```

**Current State**: Presets have ALL logo/login asset fields defined. ✅ **Schema is ready.**

---

### 2. **Global Config Schema** (`BrandingConfig` in `src/lib/utils/branding.ts`)

```typescript
export interface BrandingConfig {
	app_name?: string;
	accent_color?: string;
	accent_color_scale?: Record<string, string>;
	logo_url?: string;
	logo_dark_url?: string;
	favicon_url?: string;
	login_background_url?: string;
	login_background_color?: string;
	presets?: BrandingPreset[];
	domain_mappings?: DomainMapping[];
}
```

**Current State**: Global config has all fields. ✅ **Schema is ready.**

---

### 3. **Domain Mapping Schema**

```typescript
export interface DomainMapping {
	domain: string; // e.g., "chat.fiwealth.com"
	preset_name: string; // e.g., "Foundations"
}
```

**Current State**: Maps domains to preset names. ✅ **Schema is ready.**

---

### 4. **getEffectiveBranding() Logic** (`src/lib/utils/branding.ts:183-203`)

```typescript
export function getEffectiveBranding(config: BrandingConfig): {
	accent_color: string;
	logo_url: string;
	logo_dark_url: string;
	favicon_url: string;
	login_background_url: string;
	login_background_color: string;
	app_name: string;
} {
	const preset = findPresetForDomain(config);

	return {
		accent_color: preset?.accent_color || config.accent_color || '#e3530f',
		logo_url: preset?.logo_url || config.logo_url || '',
		logo_dark_url: preset?.logo_dark_url || config.logo_dark_url || '',
		favicon_url: preset?.favicon_url || config.favicon_url || '',
		login_background_url: preset?.login_background_url || config.login_background_url || '',
		login_background_color: preset?.login_background_color || config.login_background_color || '',
		app_name: config.app_name || ''
	};
}
```

**Current State**: ✅ **Already merges preset values over global config!**

- Preset values take priority
- Falls back to global config
- Falls back to defaults

---

### 5. **findPresetForDomain() Logic** (`src/lib/utils/branding.ts:127-139`)

```typescript
export function findPresetForDomain(config: BrandingConfig): BrandingPreset | null {
	if (!config.domain_mappings || !config.presets) return null;

	const currentDomain = window.location.hostname;

	const mapping = config.domain_mappings.find(
		(m) => m.domain === currentDomain || currentDomain.endsWith('.' + m.domain)
	);

	if (!mapping) return null;

	return config.presets.find((p) => p.name === mapping.preset_name) || null;
}
```

**Current State**: ✅ **Already supports domain matching!**

- Exact domain match
- Subdomain match (e.g., `chat.fiwealth.com` matches `fiwealth.com`)

---

### 6. **Login Page Usage** (`src/routes/auth/+page.svelte`)

**Lines 212-223**: Fetches and applies branding

```typescript
try {
	brandingConfig = await getPublicBrandingConfig();
	if (brandingConfig) {
		applyBranding(brandingConfig);
		effectiveBranding = getEffectiveBranding(brandingConfig);
	}
} catch (e) {
	console.debug('Branding config not available:', e);
}
```

**Lines 156-190**: Sets logo image with fallback logic

```typescript
async function setLogoImage() {
	const logo = document.getElementById('logo') as HTMLImageElement | null;

	if (logo) {
		// Prefer colored logo (logo_url) for visibility on dark backgrounds
		if (effectiveBranding?.logo_url) {
			logo.src = effectiveBranding.logo_url;
			logo.style.filter = '';
			return;
		}

		// Fallback to dark logo
		if (effectiveBranding?.logo_dark_url) {
			logo.src = effectiveBranding.logo_dark_url;
			logo.style.filter = '';
			return;
		}

		// Fallback to default favicon with inversion
		const isDarkMode = document.documentElement.classList.contains('dark');
		if (isDarkMode) {
			// Try favicon-dark.png, invert if missing
		}
	}
}
```

**Lines 248-253**: Applies login background

```typescript
<div
    class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"
    style={effectiveBranding?.login_background_color || effectiveBranding?.login_background_url
        ? `${effectiveBranding.login_background_color ? `background-color: ${effectiveBranding.login_background_color};` : ''}${effectiveBranding.login_background_url ? ` background-image: url('${effectiveBranding.login_background_url}'); background-size: cover; background-position: center;` : ''}`
        : ''}
></div>
```

**Current State**: ✅ **Already uses effectiveBranding for logos and backgrounds!**

---

### 7. **Default Branding Config** (`backend/open_webui/config.py:1769-1809`)

```python
DEFAULT_BRANDING_CONFIG = {
    "app_name": "",
    "accent_color": "#e3530f",
    "accent_color_scale": {},
    "logo_url": "",
    "logo_dark_url": "",
    "favicon_url": "",
    "login_background_url": "",
    "login_background_color": "",
    "presets": [
        {
            "name": "Foundations",
            "accent_color": "#e3530f",
            "accent_color_scale": {},
            "background_color": "#1a2744",
            "logo_url": "",
            "logo_dark_url": "",
            "favicon_url": "",
            "login_background_url": "",
            "login_background_color": "#1a2744",
            "microsoft_client_id": "",
            "microsoft_client_secret": "",
            "microsoft_client_tenant_id": "",
        },
        {
            "name": "Magellan",
            "accent_color": "#e3530f",
            "accent_color_scale": {},
            "background_color": "#000000",
            "logo_url": "",
            "logo_dark_url": "",
            "favicon_url": "",
            "login_background_url": "",
            "login_background_color": "#000000",
            "microsoft_client_id": "",
            "microsoft_client_secret": "",
            "microsoft_tenant_id": "",
        },
    ],
    "domain_mappings": [],
}
```

**Current State**: ✅ **Presets already have all logo/asset fields!**

---

## Summary: What's Missing?

### ✅ **GOOD NEWS: The system is 95% ready!**

**What's already implemented:**

1. ✅ Preset schema includes `logo_url`, `logo_dark_url`, `favicon_url`, `login_background_url`, `login_background_color`
2. ✅ `getEffectiveBranding()` merges preset values over global config
3. ✅ `findPresetForDomain()` matches domains to presets
4. ✅ Login page uses `effectiveBranding` for logos and backgrounds
5. ✅ Domain mappings are stored and processed

### ❌ **What's Missing:**

1. **No domain mappings configured** - `domain_mappings` array is empty in `DEFAULT_BRANDING_CONFIG`
   - Need to add mappings like:
     ```json
     {
         "domain": "chat.fiwealth.com",
         "preset_name": "Foundations"
     },
     {
         "domain": "chat.magellanfinancial.com",
         "preset_name": "Magellan"
     }
     ```

2. **No logo/asset URLs populated** - All preset logo fields are empty strings
   - Need to populate:
     - `presets[0].logo_url` (Foundations logo)
     - `presets[0].logo_dark_url` (Foundations dark logo)
     - `presets[0].favicon_url` (Foundations favicon)
     - `presets[0].login_background_url` (Foundations login background)
     - `presets[1].logo_url` (Magellan logo)
     - etc.

3. **No app_name per preset** - `app_name` is only global
   - Could add `app_name` to `BrandingPreset` if needed
   - Currently only `config.app_name` is used (line 201 in branding.ts)

---

## Files That Need Modification

### **Backend (Python)**

1. **`backend/open_webui/config.py`** (lines 1769-1809)
   - Update `DEFAULT_BRANDING_CONFIG` with:
     - Domain mappings for each tenant
     - Logo/asset URLs for each preset

2. **`backend/open_webui/routers/configs.py`** (lines 550-560)
   - Optional: Add `app_name` field to `BrandingPreset` if per-preset app names needed
   - Current schema already supports all logo fields ✅

### **Frontend (TypeScript/Svelte)**

1. **`src/lib/utils/branding.ts`** (lines 183-203)
   - Optional: Update `getEffectiveBranding()` return type to include `app_name` from preset
   - Current logic already handles preset merging ✅

2. **`src/routes/auth/+page.svelte`** (lines 156-190, 248-253)
   - Already uses `effectiveBranding` correctly ✅
   - No changes needed

---

## Configuration Example

To enable multi-tenant branding, populate the config like this:

```json
{
	"app_name": "Open WebUI",
	"accent_color": "#e3530f",
	"logo_url": "",
	"logo_dark_url": "",
	"favicon_url": "",
	"login_background_url": "",
	"login_background_color": "",
	"presets": [
		{
			"name": "Foundations",
			"accent_color": "#1a2744",
			"logo_url": "https://cdn.example.com/foundations-logo.png",
			"logo_dark_url": "https://cdn.example.com/foundations-logo-dark.png",
			"favicon_url": "https://cdn.example.com/foundations-favicon.ico",
			"login_background_url": "https://cdn.example.com/foundations-bg.jpg",
			"login_background_color": "#1a2744"
		},
		{
			"name": "Magellan",
			"accent_color": "#2563eb",
			"logo_url": "https://cdn.example.com/magellan-logo.png",
			"logo_dark_url": "https://cdn.example.com/magellan-logo-dark.png",
			"favicon_url": "https://cdn.example.com/magellan-favicon.ico",
			"login_background_url": "https://cdn.example.com/magellan-bg.jpg",
			"login_background_color": "#000000"
		}
	],
	"domain_mappings": [
		{
			"domain": "chat.fiwealth.com",
			"preset_name": "Foundations"
		},
		{
			"domain": "chat.magellanfinancial.com",
			"preset_name": "Magellan"
		}
	]
}
```

---

## Verification Checklist

- [x] Preset schema supports per-preset logos ✅
- [x] Global config schema supports presets and domain mappings ✅
- [x] `getEffectiveBranding()` merges preset over global ✅
- [x] `findPresetForDomain()` matches domains correctly ✅
- [x] Login page uses effective branding ✅
- [ ] Domain mappings configured (NEEDS SETUP)
- [ ] Logo URLs populated (NEEDS SETUP)
- [ ] Favicon URLs populated (NEEDS SETUP)
- [ ] Login background URLs populated (NEEDS SETUP)
