/**
 * Shared file icon name resolver.
 * Maps file names/extensions to Icon component names.
 */

export function fileIconName(name: string, type: string = 'file'): string {
	if (type === 'directory') return 'folder';
	const base = name.split('/').pop() ?? name;
	const lower = base.toLowerCase();
	const ext = base.includes('.') ? (base.split('.').pop()?.toLowerCase() ?? '') : '';

	if (lower === 'dockerfile' || lower === 'containerfile') return 'docker';
	if (lower === 'license' || lower === 'license.md') return 'page-text';
	if (lower === 'package.json' || lower === 'npm-shrinkwrap.json' || lower === 'bunfig.toml') {
		return 'npm';
	}
	if (
		lower.endsWith('.lock') ||
		lower === 'package-lock.json' ||
		lower === 'pnpm-lock.yaml' ||
		lower === 'yarn.lock'
	) {
		return 'package-lock';
	}

	switch (ext) {
		case 'md':
		case 'mdx':
		case 'markdown':
			return 'markdown-logo';
		case 'ts':
			return 'typescript-logo';
		case 'tsx':
			return 'react';
		case 'js':
		case 'mjs':
		case 'cjs':
			return 'javascript-logo';
		case 'jsx':
			return 'react';
		case 'py':
		case 'pyw':
			return 'python';
		case 'rs':
			return 'rust';
		case 'go':
			return 'go-logo';
		case 'java':
			return 'java-logo';
		case 'c':
		case 'h':
			return 'c-logo';
		case 'cpp':
		case 'cc':
		case 'cxx':
		case 'hpp':
		case 'hh':
		case 'hxx':
			return 'cpp-logo';
		case 'cs':
			return 'c-sharp-logo';
		case 'rb':
			return 'ruby-logo';
		case 'php':
			return 'php-logo';
		case 'swift':
			return 'apple-swift';
		case 'kt':
		case 'kts':
			return 'kotlin-logo';
		case 'svelte':
			return 'svelte-logo';
		case 'vue':
			return 'vue-js';
		case 'json':
		case 'jsonc':
		case 'json5':
			return 'json-logo';
		case 'yaml':
		case 'yml':
			return 'yaml-logo';
		case 'toml':
		case 'ini':
		case 'cfg':
		case 'conf':
		case 'env':
			return 'settings';
		case 'sh':
		case 'bash':
		case 'zsh':
		case 'fish':
			return 'shell-logo';
		case 'html':
		case 'htm':
			return 'html5';
		case 'css':
		case 'scss':
		case 'sass':
		case 'less':
			return 'css3';
		case 'xml':
			return 'xml-logo';
		case 'svg':
			return 'svg-format';
		case 'sql':
		case 'sqlite':
		case 'sqlite3':
		case 'db':
		case 'db3':
			return 'database-script';
		case 'csv':
		case 'tsv':
			return 'csv-logo';
		case 'pdf':
			return 'pdf-logo';
		case 'jpg':
		case 'jpeg':
		case 'png':
		case 'gif':
		case 'webp':
		case 'bmp':
		case 'ico':
		case 'avif':
		case 'tiff':
			return 'image';
		case 'mp4':
		case 'webm':
		case 'mov':
		case 'ogv':
		case 'avi':
		case 'mkv':
			return 'play';
		case 'mp3':
		case 'wav':
		case 'ogg':
		case 'flac':
		case 'm4a':
		case 'aac':
		case 'opus':
		case 'wma':
			return 'speaker';
		case 'zip':
		case 'tar':
		case 'gz':
		case 'tgz':
		case 'bz2':
		case 'xz':
		case '7z':
		case 'rar':
			return 'archive';
		case 'docx':
		case 'txt':
			return 'page-text';
		case 'xlsx':
		case 'xls':
			return 'table';
		case 'pptx':
			return 'page';
		default:
			return 'empty-page';
	}
}
