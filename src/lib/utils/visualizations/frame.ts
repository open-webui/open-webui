import { javascriptLanguage } from '@codemirror/lang-javascript';
import { base } from '$app/paths';
import { injectCsp } from '$lib/utils/csp';
import { findSafeCut } from './safeCut';
import { visualizationRuntime } from './runtime';

export const VISUALIZATION_CSP =
	"default-src 'none'; script-src 'unsafe-inline'; script-src-attr 'none'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; font-src 'none'; media-src 'none'; frame-src 'none'; object-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'none'";

const styles = `
:root{color-scheme:light;--owui-background:#fff;--owui-surface:#f5f5f5;--owui-text:#171717;--owui-muted:#737373;--owui-border:#e5e5e5;--owui-accent:#2563eb;font:calc(1rem * var(--owui-text-scale,1))/1.4 system-ui,sans-serif;color:var(--owui-text);background:var(--owui-background)}
:root[data-theme=dark]{color-scheme:dark;--owui-background:#171717;--owui-surface:#262626;--owui-text:#f5f5f5;--owui-muted:#a3a3a3;--owui-border:#404040;--owui-accent:#60a5fa}
*{box-sizing:border-box}h1,h2,h3,h4,h5,h6,strong,b,th{font-weight:500}h1,h2,h3,h4,h5,h6,p,ul,ol,figure{margin:0.25rem 0}ul,ol{padding-inline-start:1.25rem}body{margin:0;padding:0;font-size:0.90625rem}#visualization-root{display:flow-root;min-width:0}svg{max-width:100%;height:auto}button,input,select,textarea{font:inherit;color:inherit}button,input,select,textarea,summary{accent-color:var(--owui-accent)}button,input,select,textarea{border:0.0625rem solid var(--owui-border);border-radius:0.375rem;padding:0.1875rem 0.375rem;background:var(--owui-surface)}button,summary{cursor:pointer}button:hover{filter:brightness(.95)}label{display:block;margin:0.25rem 0}input[type=range]{width:100%;padding:0}table{border-collapse:collapse;width:100%}th,td{text-align:start;border-bottom:0.0625rem solid var(--owui-border);padding:0.25rem 0.375rem}details{padding:0.25rem 0}:focus-visible{outline:0.125rem solid var(--owui-accent);outline-offset:0.1875rem}.chart-container{position:relative;width:100%;min-width:0;height:15rem}:root[data-reduced-motion=true] *{animation:none!important;transition:none!important}
`;

export function visualizationDocument(additionalCsp = '') {
	// Only trusted code is serialized here; generated content travels over the port.
	const code = `(${visualizationRuntime.toString()})(${findSafeCut.toString()});`;
	const safeCode = code.replace(/<\/script/gi, '<\\/script');
	let html = `<!doctype html><html><head><meta charset="utf-8"><style>${styles}</style></head><body><main id="visualization-root" inert></main><script>${safeCode}</script></body></html>`;
	html = injectCsp(html, VISUALIZATION_CSP);
	return additionalCsp ? injectCsp(html, additionalCsp) : html;
}

const sources = new Map<string, Promise<string>>();
export function getVisualizationVendor(name: 'purifier' | 'chartjs') {
	const file = name === 'purifier' ? 'purify.min.js' : 'chart.umd.min.js';
	if (!sources.has(file)) {
		const promise = fetch(`${base}/visualizations/${file}`)
			.then(async (response) => {
				if (!response.ok) throw new Error('Visualization library could not load.');
				return response.text();
			})
			.catch((error) => {
				sources.delete(file);
				throw error;
			});
		sources.set(file, promise);
	}
	return sources.get(file)!;
}

export function repairVisualizationScript(source: string) {
	// Models sometimes put Markdown fences inside a script element.
	let script = source.replace(/^\s*```(?:javascript|js)?[ \t]*\r?\n([\s\S]*?)\r?\n```\s*$/i, '$1');
	let tree = javascriptLanguage.parser.parse(script);
	let fixedCssValue = false;
	tree.iterate({
		enter(node) {
			if (!node.type.isError || node.node.parent?.name !== 'Property' || script[node.from] !== ')')
				return;
			const value = tree.resolveInner(node.from, -1);
			if (
				value.name !== 'String' ||
				!/^(['"])var\(--[\w-]+\1$/.test(script.slice(value.from, value.to))
			)
				return;
			// color: 'var(--muted') -> color: 'var(--muted)'
			script =
				script.slice(0, node.from - 1) + ')' + script[node.from - 1] + script.slice(node.from + 1);
			fixedCssValue = true;
		}
	});
	if (fixedCssValue) tree = javascriptLanguage.parser.parse(script);
	let firstError = Infinity;
	const closers: number[] = [];
	tree.iterate({
		enter(node) {
			if (node.type.isError) firstError = Math.min(firstError, node.from);
			if (['}', ')', ']'].includes(node.name)) closers.push(node.from);
		}
	});
	if (firstError === Infinity) return script;

	// Try one nearby stray delimiter, or one missing delimiter at the end.
	const candidates = closers
		.filter((position) => position <= firstError)
		.slice(-8)
		.reverse()
		.map((position) => script.slice(0, position) + script.slice(position + 1));
	if (firstError >= script.trimEnd().length)
		candidates.unshift(...['}', ')', ']'].map((closing) => script + '\n' + closing));
	for (const candidate of candidates) {
		let valid = true;
		javascriptLanguage.parser.parse(candidate).iterate({
			enter(node) {
				if (node.type.isError) valid = false;
			}
		});
		if (valid) return candidate;
	}
	return script;
}

export function repairVisualizationHtml(html: string) {
	return html
		.replace(/^\s*```(?:html)?[ \t]*\r?\n([\s\S]*?)\r?\n```\s*$/i, '$1')
		.replace(
			/(<script\b(?:[^>"']|"[^"]*"|'[^']*')*>)([\s\S]*?)(<\/script\s*>)/gi,
			(_, opening, script, closing) => opening + repairVisualizationScript(script) + closing
		);
}
