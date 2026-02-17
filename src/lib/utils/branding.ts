/**
 * Branding / Theme Utilities
 *
 * Handles dynamic CSS variable injection for accent colors,
 * domain-based theme detection, and favicon/logo overrides.
 */

export interface BrandingPreset {
	name: string;
	app_name?: string;
	accent_color?: string;
	accent_color_scale?: Record<string, string>;
	background_color?: string;
	logo_url?: string;
	logo_dark_url?: string;
	favicon_url?: string;
	login_background_url?: string;
	login_background_color?: string;
}

export interface DomainMapping {
	domain: string;
	preset_name: string;
}

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

// Default accent color scale (matches the original tailwind config)
const DEFAULT_ACCENT_SCALE: Record<string, string> = {
	'50': '#fef3ed',
	'100': '#fde4d4',
	'200': '#fac5a8',
	'300': '#f6a071',
	'400': '#f17038',
	'500': '#e3530f',
	'600': '#d44409',
	'700': '#b0330a',
	'800': '#8c2a10',
	'900': '#722610',
	'950': '#3e1006'
};

/**
 * Generate a color scale from a single hex color.
 */
function generateColorScale(hex: string): Record<string, string> {
	const r = parseInt(hex.slice(1, 3), 16);
	const g = parseInt(hex.slice(3, 5), 16);
	const b = parseInt(hex.slice(5, 7), 16);

	function mix(c1: number, c2: number, weight: number): number {
		return Math.round(c1 * weight + c2 * (1 - weight));
	}

	function toHex(rv: number, gv: number, bv: number): string {
		return (
			'#' +
			[rv, gv, bv]
				.map((c) => {
					const h = Math.max(0, Math.min(255, c)).toString(16);
					return h.length === 1 ? '0' + h : h;
				})
				.join('')
		);
	}

	return {
		'50': toHex(mix(r, 255, 0.05), mix(g, 255, 0.05), mix(b, 255, 0.05)),
		'100': toHex(mix(r, 255, 0.15), mix(g, 255, 0.15), mix(b, 255, 0.15)),
		'200': toHex(mix(r, 255, 0.3), mix(g, 255, 0.3), mix(b, 255, 0.3)),
		'300': toHex(mix(r, 255, 0.5), mix(g, 255, 0.5), mix(b, 255, 0.5)),
		'400': toHex(mix(r, 255, 0.7), mix(g, 255, 0.7), mix(b, 255, 0.7)),
		'500': hex,
		'600': toHex(mix(r, 0, 0.85), mix(g, 0, 0.85), mix(b, 0, 0.85)),
		'700': toHex(mix(r, 0, 0.7), mix(g, 0, 0.7), mix(b, 0, 0.7)),
		'800': toHex(mix(r, 0, 0.55), mix(g, 0, 0.55), mix(b, 0, 0.55)),
		'900': toHex(mix(r, 0, 0.45), mix(g, 0, 0.45), mix(b, 0, 0.45)),
		'950': toHex(mix(r, 0, 0.25), mix(g, 0, 0.25), mix(b, 0, 0.25))
	};
}

/**
 * Apply accent color CSS variables to the document root.
 */
export function applyAccentColors(scale: Record<string, string>): void {
	const root = document.documentElement;
	for (const [shade, color] of Object.entries(scale)) {
		root.style.setProperty(`--accent-${shade}`, color);
	}
}

/**
 * Reset accent colors to defaults.
 */
export function resetAccentColors(): void {
	applyAccentColors(DEFAULT_ACCENT_SCALE);
}

/**
 * Apply a favicon override.
 */
export function applyFavicon(url: string): void {
	if (!url) return;

	let link: HTMLLinkElement | null = document.querySelector("link[rel~='icon']");
	if (!link) {
		link = document.createElement('link');
		link.rel = 'icon';
		document.head.appendChild(link);
	}
	link.href = url;
}

/**
 * Find the matching preset for the current domain.
 */
export function findPresetForDomain(config: BrandingConfig): BrandingPreset | null {
	if (!config.domain_mappings || !config.presets) return null;

	const currentDomain = window.location.hostname;

	const mapping = config.domain_mappings.find(
		(m) => m.domain === currentDomain || currentDomain.endsWith('.' + m.domain)
	);

	if (!mapping) return null;

	return config.presets.find((p) => p.name === mapping.preset_name) || null;
}

/**
 * Apply branding configuration.
 * If a domain mapping matches, the preset overrides the base config.
 */
export function applyBranding(config: BrandingConfig): void {
	if (!config) return;

	// Check for domain-specific preset
	const preset = findPresetForDomain(config);

	// Determine which accent color + scale to use
	const accentColor = preset?.accent_color || config.accent_color || '#e3530f';
	let accentScale = preset?.accent_color_scale || config.accent_color_scale;

	// Always apply accent colors - CSS variables must be explicitly set for tailwind classes to work
	if (!accentScale || Object.keys(accentScale).length === 0) {
		// Use pre-defined default scale for default color, otherwise generate from accent
		accentScale =
			accentColor === '#e3530f' ? DEFAULT_ACCENT_SCALE : generateColorScale(accentColor);
	}
	applyAccentColors(accentScale);

	// Apply favicon
	const faviconUrl = preset?.favicon_url || config.favicon_url;
	if (faviconUrl) {
		applyFavicon(faviconUrl);
	}

	// Apply app name to document title if set
	const appName = config.app_name;
	if (appName) {
		// Only update if the title still contains the default
		if (document.title.includes('Open WebUI')) {
			document.title = document.title.replace('Open WebUI', appName);
		}
	}
}

/**
 * Get the effective branding values for the current domain.
 * Returns merged config (preset overrides base).
 */
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
		app_name: preset?.app_name || config.app_name || ''
	};
}
