import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { compile } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('sidebar accessibility markup', () => {
	const sidebar = source('src/lib/components/layout/Sidebar.svelte');
	const folder = source('src/lib/components/layout/Sidebar/RecursiveFolder.svelte');
	const folderMenu = source('src/lib/components/layout/Sidebar/Folders/FolderMenu.svelte');
	const section = source('src/lib/components/layout/Sidebar/Section.svelte');
	const rootLayout = source('src/routes/+layout.svelte');
	const appLayout = source('src/routes/(app)/+layout.svelte');
	const dropdown = source('src/lib/components/common/Dropdown.svelte');
	const richTextInput = source('src/lib/components/common/RichTextInput.svelte');
	const placeholder = source('src/lib/components/chat/Placeholder.svelte');
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

	it('names the folder menu and reveals it on keyboard focus', () => {
		expect(folderMenu).toContain("aria-label={$i18n.t('More')}");
		expect(folder).toContain('group-focus-within:opacity-100');
		expect(folder).not.toContain('invisible group-hover:visible');
	});

	it('uses an accessible default contrast for section actions', () => {
		expect(section).toContain('text-gray-500 hover:text-gray-700 dark:text-gray-400');
	});

	it('compiles the skip link and its programmatically focusable destination', () => {
		expect(() => compile(rootLayout, { generate: 'server' })).not.toThrow();
		expect(() => compile(appLayout, { generate: 'server' })).not.toThrow();
		expect(rootLayout).not.toContain('href="#main-content"');
		expect(appLayout).toMatch(
			/{#if loaded}[\s\S]*?href="#main-content"[\s\S]*?<main id="main-content" tabindex="-1"/
		);
		expect(appLayout.indexOf('href="#main-content"')).toBeLessThan(
			appLayout.indexOf('<Sidebar />')
		);
		expect(appLayout).toContain('focus:absolute focus:top-2 focus:left-2 focus:z-[9999]');
		expect(appLayout).toContain('<main id="main-content" tabindex="-1"');
	});

	it('keeps slotted dropdown triggers as the only interactive control with popup state', () => {
		const dropdownMarkup = dropdown.slice(dropdown.indexOf('</script>'));
		expect(dropdownMarkup).not.toContain('role="button"');
		expect(dropdown).toContain('use:trigger={show}');
		expect(dropdown).toContain("setAttribute('aria-haspopup', 'menu')");
		expect(dropdown).toContain("setAttribute('aria-expanded', String(expanded))");
	});

	it('does not name a rich text editor while it is non-editable', () => {
		expect(() => compile(richTextInput, { generate: 'server' })).not.toThrow();
		expect(richTextInput).toMatch(
			/attributes:\s*\(\)\s*=>\s*\(\{\s*id,\s*\.\.\.\(editable\s*\?\s*\{\s*'aria-label':\s*_placeholder\s*\}\s*:\s*\{\}\)\s*\}\)/
		);
	});

	it('keeps the single-model information control out of aria-hidden', () => {
		expect(() => compile(placeholder, { generate: 'server' })).not.toThrow();
		expect(placeholder).not.toContain('aria-hidden={models.length <= 1}');
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
