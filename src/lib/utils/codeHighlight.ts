import { codeToHtml, bundledLanguages } from 'shiki';

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

const _langSet = new Set(Object.keys(bundledLanguages));

/**
 * Resolve a file extension to a Shiki language id, or null if not supported.
 */
export function extToLang(ext: string): string | null {
	const lower = ext.toLowerCase();
	// explicit override first
	if (EXT_OVERRIDE[lower]) return EXT_OVERRIDE[lower];
	// if the extension itself is a bundled language id (e.g. 'go', 'rust', 'sql', 'toml', ...)
	if (_langSet.has(lower)) return lower;
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
 */
export async function highlightCode(code: string, filePath: string): Promise<string> {
	const ext = filePath.split('.').pop()?.toLowerCase() ?? '';
	const lang = extToLang(ext) ?? 'text';

	return await codeToHtml(code, {
		lang,
		themes: {
			light: 'github-light',
			dark: 'github-dark'
		},
		defaultColor: 'light'
	});
}
