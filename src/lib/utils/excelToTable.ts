import type { CellObject, Range, WorkBook, WorkSheet } from 'xlsx';

export type PreviewSheet = WorkSheet & { '!previewStyles'?: Record<string, string> };

// SheetJS CE reads values and number formats, but not fonts, borders or alignment.
// Keep presentation metadata separate from the workbook's editable cell values.
export async function readExcelWorkbook(data: ArrayBuffer): Promise<WorkBook> {
	const XLSX = await import('xlsx');
	const workbook = XLSX.read(data, { type: 'array', cellStyles: true, cellNF: true });
	if (new Uint8Array(data)[0] !== 0x50 || new Uint8Array(data)[1] !== 0x4b) return workbook; // XLS / CSV have no OOXML styles.
	const { OfficePackage, elements, children, attr } = await import('./comments/package');
	const pkg = await OfficePackage.open(data);
	const main = await pkg.main();
	const rels = await pkg.relationships(main);
	const stylePart = rels.find((r) => r.type.endsWith('/styles'));
	if (!stylePart) return workbook;
	const styles = await pkg.xml(stylePart.path);
	if (!styles) return workbook;
	const themePart = rels.find((r) => r.type.endsWith('/theme'));
	const theme = themePart ? await pkg.xml(themePart.path) : null;
	const scheme = theme && elements(theme, 'clrScheme')[0];
	// OOXML theme indices use light/dark order, unlike the XML child order.
	const themeNames = [
		'lt1',
		'dk1',
		'lt2',
		'dk2',
		'accent1',
		'accent2',
		'accent3',
		'accent4',
		'accent5',
		'accent6',
		'hlink',
		'folHlink'
	];
	const palette = [
		'000000',
		'FFFFFF',
		'FF0000',
		'00FF00',
		'0000FF',
		'FFFF00',
		'FF00FF',
		'00FFFF',
		'000000',
		'FFFFFF',
		'FF0000',
		'00FF00',
		'0000FF',
		'FFFF00',
		'FF00FF',
		'00FFFF',
		'800000',
		'008000',
		'000080',
		'808000',
		'800080',
		'008080',
		'C0C0C0',
		'808080',
		'9999FF',
		'993366',
		'FFFFCC',
		'CCFFFF',
		'660066',
		'FF8080',
		'0066CC',
		'CCCCFF',
		'000080',
		'FF00FF',
		'FFFF00',
		'00FFFF',
		'800080',
		'800000',
		'008080',
		'0000FF',
		'00CCFF',
		'CCFFFF',
		'CCFFCC',
		'FFFF99',
		'99CCFF',
		'FF99CC',
		'CC99FF',
		'FFCC99',
		'3366FF',
		'33CCCC',
		'99CC00',
		'FFCC00',
		'FF9900',
		'FF6600',
		'666699',
		'969696',
		'003366',
		'339966',
		'003300',
		'333300',
		'993300',
		'993366',
		'333399',
		'333333'
	];
	const indexed = elements(styles, 'indexedColors')[0];
	if (indexed)
		children(indexed).forEach((c, i) => {
			palette[i] = attr(c, 'rgb').slice(-6);
		});
	const color = (node?: Element): string => {
		if (!node) return '';
		let rgb = attr(node, 'rgb');
		if (!rgb && attr(node, 'indexed')) rgb = palette[Number(attr(node, 'indexed'))] ?? '';
		if (!rgb && attr(node, 'theme') && scheme) {
			const entry = elements(scheme, themeNames[Number(attr(node, 'theme'))] ?? '')[0];
			const value = entry && children(entry)[0];
			if (value) rgb = attr(value, 'lastClr') || attr(value, 'val');
		}
		if (!/^(?:[\da-f]{8}|[\da-f]{6})$/i.test(rgb)) return '';
		const tint = Math.max(-1, Math.min(1, Number(attr(node, 'tint')) || 0));
		return (
			'#' +
			rgb
				.slice(-6)
				.match(/../g)!
				.map((part) => {
					const n = parseInt(part, 16);
					return Math.round(tint < 0 ? n * (1 + tint) : n + (255 - n) * tint)
						.toString(16)
						.padStart(2, '0');
				})
				.join('')
		);
	};
	const collection = (name: string) => {
		const node = elements(styles, name)[0];
		return node ? children(node) : [];
	};
	const fonts = collection('fonts'),
		fills = collection('fills'),
		borders = collection('borders');
	const baseStyles = collection('cellStyleXfs');
	const first = (node: Element | undefined, name: string) => node && elements(node, name)[0];
	const enabled = (node?: Element) => !!node && !['0', 'false'].includes(attr(node, 'val'));
	const css = collection('cellXfs').map((xf) => {
		const base = baseStyles[Number(attr(xf, 'xfId'))];
		const id = (name: string) => Number(attr(xf, name) || (base && attr(base, name)) || 0);
		const font = fonts[id('fontId')],
			fill = fills[id('fillId')],
			border = borders[id('borderId')];
		const rules: string[] = [];
		if (enabled(first(font, 'b'))) rules.push('font-weight:700');
		if (enabled(first(font, 'i'))) rules.push('font-style:italic');
		const decoration = [
			enabled(first(font, 'u')) ? 'underline' : '',
			enabled(first(font, 'strike')) ? 'line-through' : ''
		].filter(Boolean);
		if (decoration.length) rules.push(`text-decoration:${decoration.join(' ')}`);
		const size = first(font, 'sz');
		if (size && Number(attr(size, 'val')) > 0)
			rules.push(
				`font-size:calc(${Math.min(96, Number(attr(size, 'val')))}pt * var(--excel-font-scale, 1))`
			);
		const name = first(font, 'name');
		if (name) {
			const family = attr(name, 'val').replace(/[^\p{L}\p{N} _-]/gu, '');
			if (family) rules.push(`font-family:'${family}',sans-serif`);
		}
		const foreground = color(first(font, 'color'));
		if (foreground) rules.push(`color:${foreground}`);
		const pattern = first(fill, 'patternFill');
		const background =
			pattern && attr(pattern, 'patternType') === 'solid' ? color(first(pattern, 'fgColor')) : '';
		if (background) rules.push(`background-color:${background}`);
		for (const side of ['left', 'right', 'top', 'bottom']) {
			const edge = first(border, side);
			const style = edge && attr(edge, 'style');
			if (!style || style === 'none') continue;
			const width =
				style === 'thick' || style === 'double' ? 3 : style.startsWith('medium') ? 2 : 1;
			const line =
				style === 'double'
					? 'double'
					: /dash/i.test(style)
						? 'dashed'
						: style === 'dotted' || style === 'hair'
							? 'dotted'
							: 'solid';
			rules.push(`border-${side}:${width}px ${line} ${color(first(edge, 'color')) || '#000000'}`);
		}
		const alignment = first(xf, 'alignment') ?? first(base, 'alignment');
		if (alignment) {
			const horizontal = attr(alignment, 'horizontal'),
				vertical = attr(alignment, 'vertical');
			if (['left', 'center', 'right', 'justify'].includes(horizontal))
				rules.push(`text-align:${horizontal}`);
			if (['top', 'center', 'bottom'].includes(vertical))
				rules.push(`vertical-align:${vertical === 'center' ? 'middle' : vertical}`);
			if (['1', 'true'].includes(attr(alignment, 'wrapText')))
				rules.push('white-space:pre-wrap;overflow-wrap:anywhere');
			const indent = Math.min(20, Math.max(0, Number(attr(alignment, 'indent')) || 0));
			if (indent) rules.push(`padding-left:${indent * 10 + 8}px`);
		}
		return rules.join(';');
	});
	const doc = await pkg.xml(main);
	if (!doc) return workbook;
	for (const sheet of elements(doc, 'sheet')) {
		const worksheet = workbook.Sheets[attr(sheet, 'name')] as PreviewSheet;
		const rel = rels.find((r) => r.id === attr(sheet, 'id'));
		if (!worksheet || !rel) continue;
		const xml = await pkg.xml(rel.path);
		if (!xml) continue;
		const cellStyles: Record<string, string> = { '!default': css[0] ?? '' };
		for (const row of elements(xml, 'row')) {
			if (attr(row, 's'))
				cellStyles[`!row:${Number(attr(row, 'r')) - 1}`] = css[Number(attr(row, 's'))] ?? '';
		}
		for (const col of elements(xml, 'col')) {
			if (!attr(col, 'style')) continue;
			for (
				let c = Math.max(0, Number(attr(col, 'min')) - 1);
				c < Math.min(16384, Number(attr(col, 'max')));
				c++
			)
				cellStyles[`!col:${c}`] = css[Number(attr(col, 'style'))] ?? '';
		}
		for (const cell of elements(xml, 'c')) {
			const address = attr(cell, 'r');
			if (/^[A-Z]+[1-9]\d*$/.test(address) && attr(cell, 's'))
				cellStyles[address] = css[Number(attr(cell, 's'))] ?? '';
		}
		worksheet['!previewStyles'] = cellStyles;
	}
	return workbook;
}

const esc = (value: unknown): string =>
	String(value ?? '').replace(
		/[&<>"']/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!
	);

export interface ExcelTableResult {
	html: string;
	rowCount: number;
	colCount: number;
}

/** Render from cells, not sheet_to_json: formatted text, formulas and coordinates matter. */
export async function excelToTable(worksheet: PreviewSheet): Promise<ExcelTableResult> {
	const XLSX = await import('xlsx');
	const range = XLSX.utils.decode_range(worksheet['!ref'] ?? 'A1');
	const merges = worksheet['!merges'] ?? [];
	for (const merge of merges) {
		range.s.r = Math.min(range.s.r, merge.s.r);
		range.s.c = Math.min(range.s.c, merge.s.c);
		range.e.r = Math.max(range.e.r, merge.e.r);
		range.e.c = Math.max(range.e.c, merge.e.c);
	}
	const rowCount = worksheet['!ref'] ? range.e.r - range.s.r + 1 : 0,
		colCount = worksheet['!ref'] ? range.e.c - range.s.c + 1 : 0;
	const usedRange = worksheet['!ref'] ? XLSX.utils.encode_range(range) : '';
	const lastRow = range.e.r,
		lastCol = range.e.c;
	// shortcut: bounded HTML grid; use virtualization before supporting larger used ranges.
	if (rowCount * colCount > 200000)
		throw new Error('This sheet is too large to preview. Download it to view all cells.');
	// A worksheet continues past its populated range; the viewer grows these blank margins on scroll.
	range.e.r = Math.min(1048575, Math.max(59, range.e.r + 20));
	range.e.c = Math.min(16383, Math.max(19, range.e.c + 4));
	const rows = Array.from({ length: range.e.r - range.s.r + 1 }, (_, i) => i + range.s.r).filter(
		(r) => !worksheet['!rows']?.[r]?.hidden
	);
	const cols = Array.from({ length: range.e.c - range.s.c + 1 }, (_, i) => i + range.s.c).filter(
		(c) => !worksheet['!cols']?.[c]?.hidden
	);
	const merged = new Map<
		string,
		{ merge: Range; first: string; rowSpan: number; colSpan: number }
	>();
	for (const merge of merges) {
		const rs = rows.filter((r) => r >= merge.s.r && r <= merge.e.r);
		const cs = cols.filter((c) => c >= merge.s.c && c <= merge.e.c);
		const first = `${rs[0]},${cs[0]}`;
		for (const r of rs)
			for (const c of cs)
				merged.set(`${r},${c}`, { merge, first, rowSpan: rs.length, colSpan: cs.length });
	}
	const widths = cols.map((c) => {
		const col = worksheet['!cols']?.[c];
		return Math.max(
			24,
			Math.min(
				1200,
				col?.wpx ?? (col?.wch != null ? col.wch * 7 + 5 : col?.width != null ? col.width * 7 : 112)
			)
		);
	});
	const parts = [
		`<table role="grid" aria-label="Worksheet" aria-readonly="true" data-used-range="${usedRange}" data-last-row="${lastRow}" data-last-col="${lastCol}" style="width:${48 + widths.reduce((a, b) => a + b, 0)}px"><colgroup><col style="width:48px">`
	];
	cols.forEach((c, i) => parts.push(`<col data-col="${c}" style="width:${widths[i]}px">`));
	parts.push('</colgroup><thead><tr role="row"><th class="excel-row-num" scope="col"></th>');
	cols.forEach((c) => {
		const label = XLSX.utils.encode_col(c);
		parts.push(
			`<th role="columnheader" scope="col" data-col="${c}" class="excel-col-hdr">${label}<button type="button" class="excel-resize" data-resize="${c}" aria-label="Resize column ${label}" title="Drag or use arrow keys to resize. Double-click or press Enter to fit contents."></button></th>`
		);
	});
	parts.push('</tr></thead><tbody>');
	for (const r of rows) {
		const row = worksheet['!rows']?.[r];
		const height = row?.hpx ?? (row?.hpt != null ? (row.hpt * 4) / 3 : 28);
		parts.push(
			`<tr role="row" data-row="${r}" style="height:${Math.max(1, Math.min(600, height))}px"><th role="rowheader" scope="row" class="excel-row-num">${r + 1}</th>`
		);
		for (const c of cols) {
			const merge = merged.get(`${r},${c}`);
			if (merge && merge.first !== `${r},${c}`) continue;
			const address = XLSX.utils.encode_cell(merge?.merge.s ?? { r, c });
			const cell: CellObject | undefined = worksheet[address];
			const value = cell ? (cell.w ?? (cell.v == null ? '' : XLSX.utils.format_cell(cell))) : '';
			const formula = cell?.f ? `=${cell.f}` : '';
			const styles = worksheet['!previewStyles'];
			const style =
				styles?.[address] ??
				styles?.[`!row:${r}`] ??
				styles?.[`!col:${c}`] ??
				styles?.['!default'] ??
				'';
			const target = cell?.l?.Target ?? '';
			const external = /^(https?:\/\/|mailto:)/i.test(target) && !/[\u0000-\u0020]/.test(target);
			const internal = target.startsWith('#');
			const content = external
				? `<a href="${esc(target)}" target="_blank" rel="noopener noreferrer" tabindex="-1">${esc(value || target)}</a>`
				: internal
					? `<a href="#" data-sheet-link="${esc(target.slice(1))}" tabindex="-1">${esc(value || target.slice(1))}</a>`
					: esc(value);
			parts.push(
				`<td role="gridcell" aria-selected="false" data-cell="${address}" data-row="${r}" data-col="${c}" data-end-row="${merge?.merge.e.r ?? r}" data-end-col="${merge?.merge.e.c ?? c}" data-value="${esc(value)}" data-formula="${esc(formula)}" tabindex="-1"${merge ? ` rowspan="${merge.rowSpan}" colspan="${merge.colSpan}"` : ''} style="text-align:${cell?.t === 'n' ? 'right' : 'left'};${esc(style)}">${content}${cell?.c?.length ? '<span class="excel-comment" aria-label="Has comment">◥</span>' : ''}</td>`
			);
		}
		parts.push('</tr>');
	}
	parts.push('</tbody></table>');
	const DOMPurify = (await import('dompurify')).default;
	return { html: DOMPurify.sanitize(parts.join(''), { ADD_ATTR: ['target'] }), rowCount, colCount };
}

export interface GridCell {
	row: number;
	col: number;
	endRow: number;
	endCol: number;
	address: string;
	value: string;
	formula: string;
}

export function cellAddress(row: number, col: number): string {
	let letters = '';
	for (let n = col + 1; n > 0; n = Math.floor((n - 1) / 26))
		letters = String.fromCharCode(65 + ((n - 1) % 26)) + letters;
	return letters + (row + 1);
}

export function selectionBounds(anchor: GridCell, focus: GridCell, cells: GridCell[] = []) {
	const range = {
		row: Math.min(anchor.row, focus.row),
		col: Math.min(anchor.col, focus.col),
		endRow: Math.max(anchor.endRow, focus.endRow),
		endCol: Math.max(anchor.endCol, focus.endCol)
	};
	const merges = cells.filter((cell) => cell.row !== cell.endRow || cell.col !== cell.endCol);
	let expanded = true;
	while (expanded) {
		expanded = false;
		for (const cell of merges) {
			if (!intersects(cell, range)) continue;
			const next = {
				row: Math.min(range.row, cell.row),
				col: Math.min(range.col, cell.col),
				endRow: Math.max(range.endRow, cell.endRow),
				endCol: Math.max(range.endCol, cell.endCol)
			};
			if (
				next.row !== range.row ||
				next.col !== range.col ||
				next.endRow !== range.endRow ||
				next.endCol !== range.endCol
			) {
				Object.assign(range, next);
				expanded = true;
			}
		}
	}
	return range;
}

export function intersects(cell: GridCell, range: ReturnType<typeof selectionBounds>) {
	return (
		cell.row <= range.endRow &&
		cell.endRow >= range.row &&
		cell.col <= range.endCol &&
		cell.endCol >= range.col
	);
}

/** Quote tabs/newlines as spreadsheet TSV; covered cells in merged ranges stay empty. */
export function selectionTSV(
	cells: GridCell[],
	rows: number[],
	cols: number[],
	range: ReturnType<typeof selectionBounds>
) {
	const values = new Map(cells.map((cell) => [`${cell.row},${cell.col}`, cell.value]));
	const quote = (value: string) =>
		/[\t\r\n"]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
	return rows
		.filter((r) => r >= range.row && r <= range.endRow)
		.map((r) =>
			cols
				.filter((c) => c >= range.col && c <= range.endCol)
				.map((c) => quote(values.get(`${r},${c}`) ?? ''))
				.join('\t')
		)
		.join('\n');
}
