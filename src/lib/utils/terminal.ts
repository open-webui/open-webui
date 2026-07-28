// Tracks the top-level names under src/routes and static/, plus the backend's mounts
const APP_ROUTES = [
	'_app',
	'admin',
	'api',
	'assets',
	'audio',
	'auth',
	'automations',
	'c',
	'cache',
	'calendar',
	'channels',
	'error',
	'folders',
	'notes',
	'oauth',
	'ollama',
	'openai',
	'playground',
	'pyodide',
	's',
	'static',
	'watch',
	'workspace',
	'ws'
];

/**
 * Models link files on the terminal with an invented scheme (file://, sandbox:/…)
 * or a bare filesystem path. Returns the path such a link points at, or null if it
 * is a normal web or in-app link. A `file://` authority is read as a directory,
 * since models write `file://home/user/…` for `/home/user/…`.
 */
export const terminalPath = (href: string): string | null => {
	const scheme = href.match(/^([a-z][a-z0-9+.-]*):/i)?.[1]?.toLowerCase();
	if (href.startsWith('//') || (scheme && scheme !== 'file' && scheme !== 'sandbox')) {
		return null;
	}

	const raw = (scheme ? href.slice(scheme.length + 1) : href).split(/[?#]/)[0];

	// A schemeless host is a web link the model forgot to write in full
	if (!scheme && !raw.startsWith('/') && /^[^/.][^/]*\.[a-z]{2,}(\/|$)/i.test(raw)) {
		return null;
	}

	// Malformed escapes throw; fall back to the encoded form
	let decoded: string;
	try {
		decoded = decodeURIComponent(raw);
	} catch {
		decoded = raw;
	}

	const segments: string[] = [];
	for (const segment of decoded.split('/')) {
		if (!segment || segment === '.') {
			continue;
		}
		if (segment === '..') {
			segments.pop();
		} else {
			segments.push(segment);
		}
	}

	// '/home' is an Open WebUI route, but '/home/user/…' is the terminal's home directory
	if (
		!segments.length ||
		(segments.length === 1 && segments[0] === 'home') ||
		APP_ROUTES.includes(segments[0])
	) {
		return null;
	}

	return '/' + segments.join('/');
};
