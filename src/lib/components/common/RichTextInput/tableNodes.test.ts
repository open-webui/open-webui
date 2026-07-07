import { describe, expect, it } from 'vitest';

import { getDirectTableCells, getDirectTableRows } from './tableNodes';

type FakeElement = {
	tagName: string;
	children: FakeElement[];
	matches: (selector: string) => boolean;
};

const node = (tagName: string, children: FakeElement[] = []): FakeElement => ({
	tagName,
	children,
	matches: (selector) => {
		const selectors = selector.split(',').map((part) => part.trim().toLowerCase());
		return selectors.includes(tagName.toLowerCase());
	}
});

describe('table node helpers', () => {
	it('ignores rows and cells from nested tables', () => {
		const nestedTable = node('table', [
			node('tbody', [node('tr', [node('td', [node('p')]), node('td')])])
		]);
		const table = node('table', [
			node('tbody', [node('tr', [node('td', [nestedTable]), node('td')])])
		]);

		const rows = getDirectTableRows(table);
		const cells = getDirectTableCells(rows[0]);

		expect(rows).toHaveLength(1);
		expect(cells).toHaveLength(2);
	});

	it('keeps rows that are direct table children', () => {
		const table = node('table', [node('tr', [node('th'), node('td')])]);

		const rows = getDirectTableRows(table);
		const cells = getDirectTableCells(rows[0]);

		expect(rows).toHaveLength(1);
		expect(cells.map((cell) => cell.tagName)).toEqual(['th', 'td']);
	});
});
