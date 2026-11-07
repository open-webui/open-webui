import * as XLSX from 'xlsx';
import { OfficePackage, attr, children, elements } from './comments/package';
import type { CellObject, Range, WorkBook, WorkSheet } from 'xlsx';

export type PreviewSheet = WorkSheet & { '!previewStyles'?: Record<string, string> };

// SheetJS CE reads values and number formats, but not fonts, borders or alignment.
// Keep presentation metadata separate from the workbook's editable cell values.
export async function readExcelWorkbook(data: ArrayBuffer): Promise<WorkBook> {
	const workbook = XLSX.read(data, { type: 'array', cellStyles: true, cellNF: true });
	if (new Uint8Array(data)[0] !== 0x50 || new Uint8Array(data)[1] !== 0x4b) return workbook; // XLS / CSV have no OOXML styles.
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

export type CellEdit = { address: string; text: string };
type Change = { sheet: string; address: string; before?: CellObject; after?: CellObject };
type Transaction = Change[];
const signature = (cell?: CellObject) =>
	JSON.stringify([cell?.t === 'z' ? undefined : cell?.t, cell?.v, cell?.f]);
const key = (sheet: string, address: string) => `${sheet}\0${address}`;

/** Spreadsheet clipboard text, including quoted tabs, newlines and doubled quotes. */
export function parseSpreadsheetPaste(text: string): string[][] {
	if (text.length > 4 * 1024 * 1024) throw new Error('Paste up to 4 MiB of text at a time.');
	const rows: string[][] = [[]];
	let value = '',
		quoted = false;
	for (let i = 0; i < text.length; i++) {
		const c = text[i];
		if (c === '"' && (quoted || !value)) {
			if (quoted && text[i + 1] === '"') {
				value += '"';
				i++;
			} else quoted = !quoted;
		} else if (!quoted && (c === '\t' || c === '\n' || c === '\r')) {
			if (rows.length > 10000 || rows[rows.length - 1].length >= 10000)
				throw new Error('Paste up to 10,000 cells at a time.');
			rows[rows.length - 1].push(value);
			value = '';
			if (c !== '\t') {
				if (c === '\r' && text[i + 1] === '\n') i++;
				rows.push([]);
			}
		} else value += c;
	}
	if (quoted) throw new Error('The pasted text has an unclosed quote.');
	rows[rows.length - 1].push(value);
	if (rows.length > 1 && /[\r\n]$/.test(text)) rows.pop();
	const width = Math.max(...rows.map((row) => row.length));
	if (rows.length * width > 10000) throw new Error('Paste up to 10,000 cells at a time.');
	return rows.map((row) => [...row, ...Array(width - row.length).fill('')]);
}

export class ExcelWorkbookEditor {
	private history: Transaction[] = [];
	private position = 0;
	private changes = new Map<string, Change>();
	private savedState = '[]';
	private protectedSheets = new Set<string>();
	private readOnlyRanges = new Map<string, XLSX.Range[]>();
	private sheetPaths = new Map<string, string>();
	private original: ArrayBuffer;
	private expected: ArrayBuffer;
	private constructor(
		readonly workbook: WorkBook,
		bytes: ArrayBuffer
	) {
		this.original = this.expected = bytes;
	}
	static async open(workbook: WorkBook, bytes: ArrayBuffer) {
		const editor = new ExcelWorkbookEditor(workbook, bytes);
		const pkg = await OfficePackage.open(bytes);
		if (Object.keys(pkg.zip.files).some((path) => path.startsWith('_xmlsignatures/')))
			throw new Error('Signed workbooks are read-only.');
		const main = await pkg.main(),
			doc = await pkg.xml(main);
		if (!doc) throw new Error('Could not read workbook.');
		const rels = await pkg.relationships(main);
		for (const sheet of elements(doc, 'sheet')) {
			const path = rels.find((r) => r.id === attr(sheet, 'id'))?.path;
			if (!path) continue;
			const xml = await pkg.xml(path);
			const name = attr(sheet, 'name');
			if (!xml) continue;
			editor.sheetPaths.set(name, path);
			editor.readOnlyRanges.set(
				name,
				elements(xml, 'f')
					.filter((f) => attr(f, 'ref'))
					.map((f) => XLSX.utils.decode_range(attr(f, 'ref')))
			);
			// Table header names also live in table definitions and structured formula references.
			for (const rel of (await pkg.relationships(path)).filter((r) => r.type.endsWith('/table'))) {
				const table = (await pkg.xml(rel.path))?.documentElement;
				if (!table || attr(table, 'headerRowCount') === '0') continue;
				const range = XLSX.utils.decode_range(attr(table, 'ref'));
				range.e.r = range.s.r;
				editor.readOnlyRanges.get(name)!.push(range);
			}
			if (elements(xml, 'sheetProtection').length) editor.protectedSheets.add(name);
		}
		return editor;
	}
	canEdit(sheet: string, address: string) {
		const ws = this.workbook.Sheets[sheet];
		if (!ws || !this.sheetPaths.has(sheet) || this.protectedSheets.has(sheet)) return false;
		const { r, c } = XLSX.utils.decode_cell(address);
		if (
			this.readOnlyRanges
				.get(sheet)
				?.some((range) => r >= range.s.r && r <= range.e.r && c >= range.s.c && c <= range.e.c)
		)
			return false;
		const cell = ws[address];
		return !cell?.f && !cell?.F;
	}
	input(sheet: string, address: string) {
		const cell = this.workbook.Sheets[sheet]?.[address];
		return cell?.f ? `=${cell.f}` : cell?.v == null ? '' : String(cell.v);
	}
	get canUndo() {
		return this.position > 0;
	}
	get canRedo() {
		return this.position < this.history.length;
	}
	private state() {
		return JSON.stringify(
			[...this.changes]
				.filter(([, c]) => signature(c.before) !== signature(c.after))
				.map(([id, c]) => [id, signature(c.after)])
				.sort(([a], [b]) => a.localeCompare(b))
		);
	}
	get dirty() {
		return this.state() !== this.savedState;
	}
	apply(sheet: string, edits: CellEdit[]) {
		const ws = this.workbook.Sheets[sheet];
		if (edits.length > 10000) throw new Error('Paste up to 10,000 cells at a time.');
		const transaction: Transaction = [];
		const bounds = XLSX.utils.decode_range(ws?.['!ref'] ?? edits[0]?.address ?? 'A1');
		for (const { address, text } of edits) {
			if (!/^[A-Z]{1,3}[1-9]\d{0,6}$/.test(address)) throw new Error('Invalid cell address.');
			const { r, c } = XLSX.utils.decode_cell(address);
			if (r > 1048575 || c > 16383) throw new Error('The paste exceeds the worksheet boundary.');
			if (!this.canEdit(sheet, address))
				throw new Error('Formula cells, table headers, and protected sheets are read-only.');
			if (text.length > 32767 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(text))
				throw new Error('Cell text is too long or contains unsupported control characters.');
			const merge = ws['!merges']?.find(
				(m) => r >= m.s.r && r <= m.e.r && c >= m.s.c && c <= m.e.c
			);
			if (merge && (r !== merge.s.r || c !== merge.s.c || edits.length > 1))
				throw new Error('Paste into unmerged cells.');
			bounds.s.r = Math.min(bounds.s.r, r);
			bounds.s.c = Math.min(bounds.s.c, c);
			bounds.e.r = Math.max(bounds.e.r, r);
			bounds.e.c = Math.max(bounds.e.c, c);
			if ((bounds.e.r - bounds.s.r + 1) * (bounds.e.c - bounds.s.c + 1) > 200000)
				throw new Error('This edit would exceed the preview size limit.');
			const before: CellObject | undefined = ws[address];
			if (text === this.input(sheet, address)) continue;
			const after = { ...before } as CellObject;
			delete after.w;
			delete after.h;
			delete after.r;
			if (text.startsWith('='))
				throw new Error(
					'Formula editing is not supported yet. Start with an apostrophe to enter literal text.'
				);
			if (text === '') {
				after.t = 'z';
				delete after.v;
			} else if (text.startsWith("'")) {
				after.t = 's';
				after.v = text.slice(1);
			} else if (/^(true|false)$/i.test(text)) {
				after.t = 'b';
				after.v = text.toLowerCase() === 'true';
			} else if (
				/^[+-]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?%?$/.test(text) &&
				Number.isFinite(Number(text.replace(/%$/, ''))) &&
				text
					.replace(/[eE].*|%$/g, '')
					.replace(/[^0-9]/g, '')
					.replace(/^0+/, '').length <= 15
			) {
				after.t = 'n';
				after.v = Number(text.replace(/%$/, '')) / (text.endsWith('%') ? 100 : 1);
			} else {
				after.t = 's';
				after.v = text;
			}
			if (signature(before) !== signature(after))
				transaction.push({ sheet, address, before, after });
		}
		// Validate the entire transaction before touching any cells.
		if (!transaction.length) return;
		this.history.splice(this.position);
		this.history.push(transaction);
		this.position++;
		this.applyChanges(transaction, false);
	}
	private applyChanges(transaction: Transaction, undo: boolean) {
		for (const change of transaction) {
			const cell = undo ? change.before : change.after;
			const ws = this.workbook.Sheets[change.sheet];
			if (cell) ws[change.address] = cell;
			else delete ws[change.address];
			const id = key(change.sheet, change.address);
			const first = this.changes.get(id) ?? change;
			this.changes.set(id, { ...first, after: cell });
			const range = XLSX.utils.decode_range(ws['!ref'] ?? change.address);
			const { r, c } = XLSX.utils.decode_cell(change.address);
			range.s.r = Math.min(range.s.r, r);
			range.s.c = Math.min(range.s.c, c);
			range.e.r = Math.max(range.e.r, r);
			range.e.c = Math.max(range.e.c, c);
			ws['!ref'] = XLSX.utils.encode_range(range);
		}
	}
	undo() {
		if (this.canUndo) this.applyChanges(this.history[--this.position], true);
	}
	redo() {
		if (this.canRedo) this.applyChanges(this.history[this.position++], false);
	}
	matches(bytes: ArrayBuffer) {
		const a = new Uint8Array(this.expected),
			b = new Uint8Array(bytes);
		return a.length === b.length && a.every((v, i) => v === b[i]);
	}
	markSaved(bytes: ArrayBuffer) {
		this.expected = bytes;
		this.savedState = this.state();
	}
	capture() {
		return {
			kind: 'xlsx',
			original: this.original,
			expected: this.expected,
			history: this.history.slice(),
			position: this.position,
			savedState: this.savedState,
			changes: [...this.changes]
		};
	}
	restore(view: ReturnType<ExcelWorkbookEditor['capture']>) {
		this.original = view.original;
		this.expected = view.expected;
		this.history = view.history;
		this.position = view.position;
		this.savedState = view.savedState;
		this.changes = new Map(view.changes);
		this.applyChanges([...this.changes.values()], false);
	}
	async bytes(): Promise<ArrayBuffer> {
		const pkg = await OfficePackage.open(this.original);
		const changed = [...this.changes.values()].filter(
			(c) => signature(c.before) !== signature(c.after)
		);
		for (const sheet of new Set(changed.map((c) => c.sheet))) {
			const path = this.sheetPaths.get(sheet)!;
			const doc = await pkg.xml(path);
			if (!doc) throw new Error('Could not read worksheet.');
			const data = elements(doc, 'sheetData')[0];
			if (!data) throw new Error('Could not read worksheet cells.');
			const create = (name: string) =>
				doc.createElementNS(data.namespaceURI, `${data.prefix ? data.prefix + ':' : ''}${name}`);
			for (const change of changed.filter((c) => c.sheet === sheet)) {
				const { r, c } = XLSX.utils.decode_cell(change.address);
				let row = children(data).find((row) => Number(attr(row, 'r')) === r + 1);
				if (!row) {
					row = create('row');
					row.setAttribute('r', String(r + 1));
					data.insertBefore(row, children(data).find((n) => Number(attr(n, 'r')) > r + 1) ?? null);
				}
				row.removeAttribute('spans');
				let cell = children(row).find((cell) => attr(cell, 'r') === change.address);
				if (!cell) {
					cell = create('c');
					cell.setAttribute('r', change.address);
					row.insertBefore(
						cell,
						children(row).find((n) => XLSX.utils.decode_cell(attr(n, 'r')).c > c) ?? null
					);
				}
				for (const n of children(cell).filter((n) => ['v', 'is', 'f'].includes(n.localName)))
					cell.removeChild(n);
				cell.removeAttribute('t');
				const value = change.after;
				if (value?.v != null) {
					const node = create(value.t === 's' ? 'is' : 'v');
					if (value.t === 's') {
						cell.setAttribute('t', 'inlineStr');
						const text = create('t');
						text.setAttributeNS('http://www.w3.org/XML/1998/namespace', 'xml:space', 'preserve');
						text.textContent = String(value.v).replace(
							/_x[0-9a-f]{4}_/gi,
							(value) => '_x005F_' + value.slice(1)
						);
						node.appendChild(text);
					} else {
						cell.setAttribute('t', value.t === 'b' ? 'b' : 'n');
						node.textContent = value.t === 'b' ? (value.v ? '1' : '0') : String(value.v);
					}
					cell.insertBefore(node, cell.firstChild);
				}
			}
			const dimension = elements(doc, 'dimension')[0];
			if (dimension) dimension.setAttribute('ref', this.workbook.Sheets[sheet]['!ref'] ?? 'A1');
			pkg.zip.file(path, new XMLSerializer().serializeToString(doc), { createFolders: false });
		}
		// Excel recalculates dependent formulas on open; no browser formula engine is involved.
		if (changed.length) {
			const main = await pkg.main(),
				doc = await pkg.xml(main);
			if (!doc) throw new Error('Could not read workbook.');
			let calc = elements(doc, 'calcPr')[0];
			if (!calc) {
				const root = doc.documentElement;
				calc = doc.createElementNS(
					root.namespaceURI,
					`${root.prefix ? root.prefix + ':' : ''}calcPr`
				);
				const following = [
					'oleSize',
					'customWorkbookViews',
					'pivotCaches',
					'smartTagPr',
					'smartTagTypes',
					'webPublishing',
					'fileRecoveryPr',
					'webPublishObjects',
					'extLst'
				];
				root.insertBefore(
					calc,
					children(root).find((n) => following.includes(n.localName)) ?? null
				);
			}
			calc.setAttribute('fullCalcOnLoad', '1');
			calc.setAttribute('forceFullCalc', '1');
			calc.setAttribute('calcMode', 'auto');
			pkg.zip.file(main, new XMLSerializer().serializeToString(doc), { createFolders: false });
		}
		return pkg.zip.generateAsync({ type: 'arraybuffer', compression: 'DEFLATE' });
	}
}
