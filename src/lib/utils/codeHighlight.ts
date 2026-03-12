/**
 * Map file extensions to Shiki language identifiers.
 * Only extensions whose Shiki lang id differs from the extension itself need explicit entries.
 */
const EXT_OVERRIDE: Record<string, string> = {
	py: 'python',
	js: 'javascript',
	ts: 'typescript',
	jsx: 'jsx',
	tsx: 'tsx',
	rb: 'ruby',
	rs: 'rust',
	kt: 'kotlin',
	cs: 'csharp',
	fs: 'fsharp',
	sh: 'bash',
	bash: 'bash',
	zsh: 'bash',
	yml: 'yaml',
	md: 'markdown',
	mdx: 'mdx',
	dockerfile: 'dockerfile',
	tf: 'terraform',
	hcl: 'hcl',
	ex: 'elixir',
	exs: 'elixir',
	erl: 'erlang',
	hs: 'haskell',
	ml: 'ocaml',
	mli: 'ocaml',
	pl: 'perl',
	pm: 'perl',
	r: 'r',
	m: 'objective-c',
	mm: 'objective-cpp',
	h: 'c',
	hpp: 'cpp',
	cc: 'cpp',
	cxx: 'cpp',
	proto: 'proto',
	nim: 'nim',
	zig: 'zig',
	v: 'v',
	svelte: 'svelte',
	vue: 'vue',
	astro: 'astro',
	prisma: 'prisma',
	graphql: 'graphql',
	gql: 'graphql',
	jsonc: 'jsonc',
	jsonl: 'jsonl'
};

// Common extensions that exactly match their Shiki language ID.
// This replaces the runtime `bundledLanguages` import from shiki, which
// pulled ~5-10MB of JavaScript into the initial page load just so
// isCodeFile() could check extension support.
const KNOWN_LANG_IDS = new Set([
	'ada',
	'awk',
	'bat',
	'c',
	'cmake',
	'clojure',
	'cpp',
	'crystal',
	'css',
	'd',
	'dart',
	'diff',
	'elixir',
	'elm',
	'erlang',
	'fish',
	'gleam',
	'glsl',
	'go',
	'groovy',
	'haml',
	'haskell',
	'hlsl',
	'html',
	'ini',
	'java',
	'javascript',
	'json',
	'json5',
	'jsonc',
	'jsx',
	'julia',
	'kotlin',
	'latex',
	'less',
	'lisp',
	'log',
	'lua',
	'make',
	'markdown',
	'matlab',
	'mdx',
	'mojo',
	'nim',
	'nix',
	'nushell',
	'ocaml',
	'pascal',
	'perl',
	'php',
	'postcss',
	'powershell',
	'prisma',
	'prolog',
	'proto',
	'pug',
	'python',
	'r',
	'ruby',
	'rust',
	'sass',
	'scala',
	'scheme',
	'scss',
	'solidity',
	'sql',
	'svelte',
	'swift',
	'tcl',
	'terraform',
	'tex',
	'toml',
	'tsx',
	'typescript',
	'typst',
	'v',
	'vb',
	'verilog',
	'vhdl',
	'vue',
	'wasm',
	'wgsl',
	'xml',
	'yaml',
	'zig'
]);

/**
 * Resolve a file extension to a Shiki language id, or null if not supported.
 */
export function extToLang(ext: string): string | null {
	const lower = ext.toLowerCase();
	// explicit override first
	if (EXT_OVERRIDE[lower]) return EXT_OVERRIDE[lower];
	// if the extension itself is a known language id (e.g. 'go', 'rust', 'sql', 'toml', ...)
	if (KNOWN_LANG_IDS.has(lower)) return lower;
	return null;
}

/**
 * Returns true if the given file path has a code-file extension that Shiki can highlight.
 */
export function isCodeFile(path: string | null): boolean {
	if (!path) return false;
	const ext = path.split('.').pop()?.toLowerCase() ?? '';
	return extToLang(ext) !== null;
}

/**
 * Highlight code using Shiki with dual light/dark themes via CSS variables.
 * Returns an HTML string. Throws on failure.
 *
 * Shiki is loaded on demand (dynamic import) to avoid pulling ~5-10MB of
 * JavaScript into the initial page bundle. Since this function is already
 * async, callers are completely unaffected by the change.
 */
export async function highlightCode(code: string, filePath: string): Promise<string> {
	const ext = filePath.split('.').pop()?.toLowerCase() ?? '';
	const lang = extToLang(ext) ?? 'text';

	const { codeToHtml } = await import('shiki');
	return await codeToHtml(code, {
		lang,
		themes: {
			light: 'github-light',
			dark: 'github-dark'
		},
		defaultColor: 'light'
	});
}
