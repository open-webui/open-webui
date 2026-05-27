/**
 * Prepend a Content-Security-Policy <meta> tag to HTML.
 * First CSP meta tag wins per spec, so any existing CSP
 * in the HTML is effectively overridden.
 */
export function injectCsp(html: string, csp: string): string {
	if (!csp) return html;
	const escaped = csp.replace(/"/g, '&quot;');
	const tag = `<meta http-equiv="Content-Security-Policy" content="${escaped}">`;
	const idx = html.indexOf('<head>');
	return idx !== -1 ? html.slice(0, idx + 6) + tag + html.slice(idx + 6) : tag + html;
}
