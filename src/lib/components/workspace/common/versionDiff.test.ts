import { describe, expect, it } from 'vitest';
import { versionDiffHunks } from './versionDiff';

describe('versionDiffHunks', () => {
	it('aligns a replacement followed by added lines, preserving missing newlines', () => {
		const [hunk] = versionDiffHunks(
			[
				'--- old',
				'+++ new',
				'@@ -1 +1,3 @@',
				'-Enterprise features.',
				'\\ No newline at end of file',
				'+Enterprise features.',
				'+',
				'+{{test}}',
				'\\ No newline at end of file',
				''
			].join('\n')
		);
		expect(hunk.rows).toHaveLength(3);
		expect(hunk.rows[0].before).toMatchObject({
			content: 'Enterprise features.',
			oldNumber: 1,
			noNewline: true
		});
		expect(hunk.rows[0].after).toMatchObject({ content: 'Enterprise features.', newNumber: 1 });
		expect(hunk.rows[1].before).toBeNull();
		expect(hunk.rows[2].after).toMatchObject({
			content: '{{test}}',
			newNumber: 3,
			noNewline: true
		});
	});
	it('renders an unchanged paragraph once with only the appended lines added', () => {
		const [hunk] = versionDiffHunks('@@ -1 +1,3 @@\n Enterprise features. \n+\n+{{test}}');
		expect(hunk.rows[0].before).toMatchObject({ type: 'context', oldNumber: 1, newNumber: 1 });
		expect(hunk.rows[0].before).toBe(hunk.rows[0].after);
		expect(hunk.rows.filter((row) => row.before?.type === 'deletion')).toHaveLength(0);
		expect(hunk.rows.filter((row) => row.after?.type === 'addition')).toHaveLength(2);
	});
	it('highlights changed text within aligned lines', () => {
		const [hunk] = versionDiffHunks('@@ -1 +1 @@\n-Use the old value\n+Use the new value\n');
		expect(hunk.rows[0].before?.segments.find((part) => part.changed)?.text).toBe('old');
		expect(hunk.rows[0].after?.segments.find((part) => part.changed)?.text).toBe('new');
	});
	it('keeps hunks separate, numbers context correctly, and drops patch headers', () => {
		const hunks = versionDiffHunks(
			'--- old\n+++ new\n@@ -2,2 +2 @@\n same\n-removed\n@@ -10 +9 @@\n-last\n+updated\n'
		);
		expect(hunks).toHaveLength(2);
		expect(hunks[0].rows[0].before?.oldNumber).toBe(2);
		expect(hunks[0].rows[0].after?.newNumber).toBe(2);
		expect(hunks[0].rows[1].after).toBeNull();
		expect(hunks[1].beforeStart).toBe(10);
		expect(hunks[1].afterStart).toBe(9);
		expect(hunks[1].rows).toHaveLength(1);
		expect(versionDiffHunks('')).toEqual([]);
	});
});
