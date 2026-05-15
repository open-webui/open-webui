// Shared serialization for cross-site Swept cookies (theme, sidebar collapse,
// etc.). Centralizes the Domain= computation so all Swept apps can read each
// other's cookies when deployed under a common parent domain.
//
// Add new envs/domains here when the apps gain a new parent.
const KNOWN_PARENTS = ['swept.ai', 'sweptai.psmic.com'];

export const DEFAULT_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export function getCookieDomain(): string | null {
	const host = window.location.hostname;
	if (!host || host === 'localhost') return null;
	if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) return null;
	if (host.includes(':')) return null;

	let matched: string | null = null;
	for (const parent of KNOWN_PARENTS) {
		if (
			(host === parent || host.endsWith('.' + parent)) &&
			(!matched || parent.length > matched.length)
		) {
			matched = parent;
		}
	}
	if (!matched) return null;

	// Apex case: someone landed on the registrable parent itself
	// (e.g. `swept.ai`, no subdomain). Stripping the leftmost label would
	// yield `.ai`, a public suffix the browser rejects — use the parent.
	if (host === matched) return '.' + matched;

	const labels = host.split('.');
	return '.' + labels.slice(1).join('.');
}

export function buildCookie(nameValue: string, maxAge: number): string {
	const parts = [nameValue, 'Path=/', `Max-Age=${maxAge}`, 'SameSite=Lax'];
	const domain = getCookieDomain();
	if (domain) parts.push(`Domain=${domain}`);
	if (window.location.protocol === 'https:') parts.push('Secure');
	return parts.join('; ');
}
