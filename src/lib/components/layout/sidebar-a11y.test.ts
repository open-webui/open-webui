import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { compile } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('sidebar accessibility markup', () => {
	const sidebar = source('src/lib/components/layout/Sidebar.svelte');
	const folder = source('src/lib/components/layout/Sidebar/RecursiveFolder.svelte');
	const section = source('src/lib/components/layout/Sidebar/Section.svelte');
	const rootLayout = source('src/routes/+layout.svelte');
	const appLayout = source('src/routes/(app)/+layout.svelte');
	const dropdown = source('src/lib/components/common/Dropdown.svelte');
	const suggestions = source('src/lib/components/chat/Suggestions.svelte');

	it('does not wrap sidebar controls in an interactive container', () => {
		expect(sidebar).not.toContain('class="flex flex-col flex-1 {isWindows');
	});

	it('keeps the collapsed sidebar toggle actionable', () => {
		const collapsedRail = sidebar.slice(
			sidebar.indexOf('{#if !$mobile && !$showSidebar}'),
			sidebar.indexOf("<!-- {$i18n.t('New Folder')} -->")
		);
		expect(collapsedRail).toMatch(
			/<button[^>]*aria-label=\{\$showSidebar \? \$i18n\.t\('Close Sidebar'\) : \$i18n\.t\('Open Sidebar'\)\}[^>]*on:click/
		);
		expect(collapsedRail).not.toContain('aria-hidden');
	});

	it('does not expose folder controls through a parent button role', () => {
		expect(folder).not.toMatch(/role="button"[\s\S]*?<button/);
		expect(folder).toContain('on:pointerup|stopPropagation');
	});

	it('uses an accessible default contrast for section actions', () => {
		expect(section).toContain('text-gray-500 hover:text-gray-700 dark:text-gray-400');
	});

	it('compiles the skip link and its programmatically focusable destination', () => {
		expect(() => compile(rootLayout, { generate: 'server' })).not.toThrow();
		expect(() => compile(appLayout, { generate: 'server' })).not.toThrow();
		expect(rootLayout).toContain('href="#main-content"');
		expect(appLayout).toContain('<main id="main-content" tabindex="-1"');
	});

	it('keeps slotted dropdown triggers as the only interactive control', () => {
		expect(dropdown).not.toContain('role="button"');
		expect(dropdown).not.toContain('aria-haspopup="true"');
	});

	it('uses native list semantics without changing suggestion buttons into list items', () => {
		expect(suggestions).toContain('<ul');
		expect(suggestions).toContain('<li');
		expect(suggestions).not.toContain('role="listitem"');
	});

	it('names the favicon home link and keeps More above the contrast floor', () => {
		expect(sidebar).toContain("aria-label={$i18n.t('New Chat')}");
		expect(sidebar).toContain('text-gray-500 hover:text-gray-700 dark:text-gray-400');
	});
});
