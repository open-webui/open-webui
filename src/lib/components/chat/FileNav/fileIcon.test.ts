import { describe, expect, it } from 'vitest';
import { fileIconName } from './fileIcon';

describe('fileIconName document aliases', () => {
	it.each([
		['report.doc', 'docx-logo'],
		['report.docx', 'docx-logo'],
		['slides.ppt', 'pptx-logo'],
		['slides.pptx', 'pptx-logo'],
		['sheet.xls', 'xlsx-logo'],
		['sheet.xlsx', 'xlsx-logo']
	])('maps %s to %s', (name, icon) => {
		expect(fileIconName(name)).toBe(icon);
	});
});
