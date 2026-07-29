import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('sidebar accessibility markup', () => {
	const sidebar = source('src/lib/components/layout/Sidebar.svelte');
	const folder = source('src/lib/components/layout/Sidebar/RecursiveFolder.svelte');
	const section = source('src/lib/components/layout/Sidebar/Section.svelte');
	const appLayout = source('src/routes/(app)/+layout.svelte');

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
	});

	it('does not expose folder controls through a parent button role', () => {
		expect(folder).not.toMatch(/role="button"[\s\S]*?<button/);
	});

	it('uses an accessible default contrast for section actions', () => {
		expect(section).toContain('text-gray-500 hover:text-gray-700 dark:text-gray-400');
	});

	it('keeps the skip-link destination programmatically focusable', () => {
		expect(appLayout).toContain('<main id="main-content" tabindex="-1"');
	});
});
