import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';

const componentSource = readFileSync(
	fileURLToPath(new URL('./ChatItem.svelte', import.meta.url)),
	'utf8'
);

describe('Sidebar ChatItem timestamp', () => {
	test('uses updatedAt before falling back to createdAt for the relative time indicator', () => {
		expect(componentSource).toContain('{#if (updatedAt ?? createdAt) && !mouseOver}');
		expect(componentSource).toContain('{formatTimeAgo(updatedAt ?? createdAt)}');
	});
});
