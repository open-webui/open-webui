<script lang="ts">
	import { getContext, tick } from 'svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import {
		excelToTable,
		parseSpreadsheetPaste,
		type ExcelWorkbookEditor,
		type CellEdit,
		cellAddress,
		intersects,
		selectionBounds,
		selectionTSV,
		type GridCell
	} from '$lib/utils/excelToTable';

	export let html: string;
	export let sheetNames: string[] = [];
	export let selectedSheet = '';
	export let onSheetChange: ((sheet: string) => void) | null = null;
	export let editor: ExcelWorkbookEditor | null = null;
	export let onDirtyChange: (dirty: boolean) => void = () => {};
	export let onSave: (() => Promise<void>) | null = null;
	export let saving = false;
	let changed = false,
		canUndo = false,
		canRedo = false;
	let input: HTMLTextAreaElement | null = null;
	let editingCell: Cell | null = null;
	let editStart = '';
	let renderedSheet = '';
	let restoreAddress = '';
	let renderVersion = 0;
	const i18n: any = getContext('i18n');
	const t = (value: string) => $i18n.t(value);
	type Cell = GridCell & { element: HTMLTableCellElement };
	let viewport: HTMLDivElement;
	let searchInput: HTMLInputElement;
	let searchOpen = false;
	async function openSearch() {
		searchOpen = true;
		await tick();
		searchInput?.focus();
		searchInput?.select();
	}
	function closeSearch() {
		searchOpen = false;
		query = '';
		focus?.element.focus();
	}
	function shortcuts(node: HTMLDivElement) {
		const handler = (event: KeyboardEvent) => {
			if (editor && (event.ctrlKey || event.metaKey)) {
				const key = event.key.toLowerCase();
				if (key === 's') {
					event.preventDefault();
					event.stopPropagation();
					void saveWorkbook();
					return;
				}
				if (!input && ['z', 'y'].includes(key) && !(event.target instanceof HTMLInputElement)) {
					event.preventDefault();
					event.stopPropagation();
					history(key === 'y' || event.shiftKey);
					return;
				}
			}
			if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {
				event.preventDefault();
				void openSearch();
			}
		};
		node.addEventListener('keydown', handler);
		return { destroy: () => node.removeEventListener('keydown', handler) };
	}
	let cells: Cell[] = [];
	let rows: number[] = [],
		cols: number[] = [];
	let anchor: Cell | null = null,
		focus: Cell | null = null;
	let address = '',
		formula = '',
		query = '',
		status = '';
	let matches: Cell[] = [],
		matchIndex = -1;
	let dragging = false;
	let resizing: { col: number; x: number; width: number } | null = null;
	let pendingLink = '';
	let usedRange = '';
	let lastUsedRow = 0,
		lastUsedCol = 0;
	const widths = new Map<string, Map<number, number>>();
	$: matches = query.trim()
		? cells.filter((cell) =>
				`${cell.value}\n${cell.formula}`
					.toLocaleLowerCase()
					.includes(query.trim().toLocaleLowerCase())
			)
		: [];
	$: if (query) matchIndex = -1;

	$: (editor, saving, notifyChange());
	export const captureEdit = () =>
		input && editingCell ? { address: editingCell.address, text: input.value } : null;
	export async function restoreEdit(draft: { address: string; text: string } | null) {
		await tick();
		if (!draft) return;
		const cell = cells.find((cell) => cell.address === draft.address);
		if (cell) startEdit(cell, draft.text);
	}
	function notifyChange() {
		changed = !!editor?.dirty || (!!input && input.value !== editStart);
		canUndo = !!editor?.canUndo;
		canRedo = !!editor?.canRedo;
		onDirtyChange(changed);
	}
	async function renderEdits() {
		if (!editor) return;
		const version = ++renderVersion;
		const sheet = selectedSheet;
		let result;
		try {
			result = await excelToTable(editor.workbook.Sheets[sheet]);
		} catch (error) {
			status = String(error);
			return;
		}
		if (version !== renderVersion || sheet !== selectedSheet) return;
		restoreAddress = focus?.address ?? '';
		html = result.html;
	}
	function applyEdits(edits: CellEdit[]) {
		if (!editor || saving) return false;
		try {
			editor.apply(selectedSheet, edits);
			notifyChange();
			void renderEdits();
			return true;
		} catch (error) {
			status = String(error).replace(/^Error: /, '');
			return false;
		}
	}
	export function flushEdit() {
		if (!input || !editingCell) return true;
		const cell = editingCell,
			text = input.value;
		if (text !== editStart && !applyEdits([{ address: cell.address, text }])) return false;
		const removed = input;
		input = null;
		editingCell = null;
		removed.remove();
		notifyChange();
		return true;
	}
	export function cancelEdit() {
		const removed = input;
		input = null;
		editingCell = null;
		removed?.remove();
		notifyChange();
		focus?.element.focus();
	}
	function startEdit(cell: Cell, replacement?: string) {
		if (!editor || saving || !flushEdit()) return;
		if (!editor.canEdit(selectedSheet, cell.address)) {
			status = t('Formula cells, table headers, and protected sheets are read-only.');
			return;
		}
		select(cell);
		editingCell = cell;
		editStart = editor.input(selectedSheet, cell.address);
		input = document.createElement('textarea');
		input.className = 'excel-cell-input';
		input.setAttribute('aria-label', `${t('Edit cell')} ${cell.address}`);
		input.spellcheck = false;
		input.value = replacement ?? editStart;
		input.addEventListener('input', notifyChange);
		input.addEventListener('blur', () => {
			flushEdit();
		});
		input.addEventListener('keydown', (event) => {
			if (event.isComposing) return;
			if (event.key === 'Escape') {
				event.preventDefault();
				event.stopPropagation();
				cancelEdit();
			}
			if ((event.key === 'Enter' && !event.altKey) || event.key === 'Tab') {
				event.preventDefault();
				event.stopPropagation();
				if (!flushEdit()) return;
				const target =
					event.key === 'Tab'
						? at(cell.row, cell.col + (event.shiftKey ? -1 : 1))
						: at(cell.row + (event.shiftKey ? -1 : 1), cell.col);
				if (target) select(target);
			}
		});
		cell.element.append(input);
		input.focus();
		input.setSelectionRange(input.value.length, input.value.length);
		notifyChange();
	}
	function paste(event: ClipboardEvent) {
		if (!editor || saving || input || !focus || !fromTarget(event.target)) return;
		event.preventDefault();
		try {
			const matrix = parseSpreadsheetPaste(event.clipboardData?.getData('text/plain') ?? '');
			if (matrix.length * matrix[0].length > 10000)
				throw new Error('Paste up to 10,000 cells at a time.');
			const start = anchor ? selectionBounds(anchor, focus, cells) : focus;
			applyEdits(
				matrix.flatMap((row, r) =>
					row.map((text, c) => ({ address: cellAddress(start.row + r, start.col + c), text }))
				)
			);
		} catch (error) {
			status = String(error).replace(/^Error: /, '');
		}
	}
	function history(redo: boolean) {
		if (!editor || saving || !flushEdit()) return;
		if (redo) editor.redo();
		else editor.undo();
		notifyChange();
		void renderEdits();
	}
	async function saveWorkbook() {
		if (!flushEdit() || !onSave || saving) return;
		try {
			await onSave();
			notifyChange();
			status = t('Saved');
		} catch (error) {
			status = String(error).replace(/^Error: /, '');
		}
	}

	function select(cell: Cell, extend = false, moveFocus = true) {
		if (!extend || !anchor) anchor = cell;
		focus = cell;
		const range = selectionBounds(anchor, cell, cells);
		address = cellAddress(range.row, range.col);
		const end = cellAddress(range.endRow, range.endCol);
		if (address !== end) address += `:${end}`;
		formula = cell.formula || cell.value;
		for (const candidate of cells) {
			candidate.element.setAttribute('aria-selected', String(intersects(candidate, range)));
			candidate.element.classList.toggle('excel-active', candidate === cell);
			candidate.element.tabIndex = candidate === cell ? 0 : -1;
		}
		if (moveFocus) {
			cell.element.focus({ preventScroll: true });
			cell.element.scrollIntoView({ block: 'nearest', inline: 'nearest' });
			const anchor = document.createRange();
			anchor.selectNodeContents(cell.element);
			viewport.dispatchEvent(
				new CustomEvent('spreadsheetselection', {
					bubbles: true,
					detail: {
						text: selectionTSV(cells, rows, cols, range),
						location: `${selectedSheet}!${address}`,
						anchor
					}
				})
			);
		}
		status = '';
	}
	const fromTarget = (target: EventTarget | null) => {
		const element = target instanceof Element ? target.closest('[data-cell]') : null;
		return cells.find((cell) => cell.element === element);
	};
	const at = (row: number, col: number) =>
		cells.find(
			(cell) => row >= cell.row && row <= cell.endRow && col >= cell.col && col <= cell.endCol
		);
	function setWidth(col: number, width: number) {
		const element = viewport.querySelector<HTMLTableColElement>(`col[data-col="${col}"]`);
		const table = viewport.querySelector('table');
		if (!element || !table) return;
		width = Math.max(24, Math.min(1200, width));
		table.style.width = `${parseFloat(table.style.width) + width - parseFloat(element.style.width)}px`;
		element.style.width = `${width}px`;
		if (!widths.has(selectedSheet)) widths.set(selectedSheet, new Map());
		widths.get(selectedSheet)!.set(col, width);
	}
	function fitColumn(col: number) {
		const context = document.createElement('canvas').getContext('2d');
		if (!context) return;
		let width = 24;
		let hasContent = false;
		for (const cell of cells) {
			// A title spanning several columns should not widen a single column.
			if (cell.col !== col || cell.element.colSpan > 1 || !cell.value) continue;
			hasContent = true;
			const style = getComputedStyle(cell.element);
			context.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
			const spacing = parseFloat(style.letterSpacing) || 0;
			const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
			const border = parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
			const comment = cell.element.querySelector('.excel-comment') ? 8 : 0;
			for (const line of cell.value.split(/\r\n|\r|\n/)) {
				width = Math.max(
					width,
					context.measureText(line).width +
						Math.max(0, Array.from(line).length - 1) * spacing +
						padding +
						border +
						comment +
						2
				);
			}
			if (width >= 1200) break;
		}
		setWidth(col, hasContent ? Math.ceil(width) : 112);
	}
	function doubleClick(event: MouseEvent) {
		const handle = (event.target as Element).closest<HTMLElement>('[data-resize]');
		if (!handle) {
			const cell = fromTarget(event.target);
			if (cell && !(event.target as Element).closest('a')) startEdit(cell);
			return;
		}
		event.preventDefault();
		fitColumn(Number(handle.dataset.resize));
	}
	function pointerDown(event: PointerEvent) {
		if (event.button !== 0 || event.target === input) return;
		if (!flushEdit()) {
			event.preventDefault();
			input?.focus();
			return;
		}
		const handle = (event.target as Element).closest<HTMLElement>('[data-resize]');
		if (handle) {
			const col = Number(handle.dataset.resize);
			const element = viewport.querySelector<HTMLTableColElement>(`col[data-col="${col}"]`)!;
			resizing = { col, x: event.clientX, width: parseFloat(element.style.width) };
			event.preventDefault();
			return;
		}
		const cell = fromTarget(event.target);
		if (!cell) return;
		select(cell, event.shiftKey);
		if ((event.target as Element).closest('a') || event.pointerType === 'touch') return;
		dragging = true;
		event.preventDefault();
	}
	function pointerMove(event: PointerEvent) {
		if (resizing) {
			setWidth(resizing.col, resizing.width + event.clientX - resizing.x);
			return;
		}
		if (!dragging) return;
		const cell = fromTarget(document.elementFromPoint(event.clientX, event.clientY));
		if (cell && cell !== focus) select(cell, true);
		const rect = viewport.getBoundingClientRect();
		if (event.clientY > rect.bottom - 24) viewport.scrollTop += 24;
		if (event.clientY < rect.top + 48) viewport.scrollTop -= 24;
		if (event.clientX > rect.right - 24) viewport.scrollLeft += 24;
		if (event.clientX < rect.left + 48) viewport.scrollLeft -= 24;
	}
	const pointerUp = () => {
		dragging = false;
		resizing = null;
	};
	function keydown(event: KeyboardEvent) {
		if (event.target === input || event.isComposing) return;
		const command = event.ctrlKey || event.metaKey;

		const handle = (event.target as Element).closest<HTMLElement>('[data-resize]');
		if (handle && ['Enter', ' '].includes(event.key)) {
			event.preventDefault();
			fitColumn(Number(handle.dataset.resize));
			return;
		}
		if (handle && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
			event.preventDefault();
			const col = Number(handle.dataset.resize);
			const element = viewport.querySelector<HTMLTableColElement>(`col[data-col="${col}"]`)!;
			setWidth(col, parseFloat(element.style.width) + (event.key === 'ArrowRight' ? 16 : -16));
			return;
		}
		if (!fromTarget(event.target) || !focus) return;
		if (editor && !saving) {
			if (event.key === 'F2' || (!command && !event.altKey && event.key.length === 1)) {
				event.preventDefault();
				startEdit(focus, event.key === 'F2' ? undefined : event.key);
				return;
			}
			if (['Backspace', 'Delete'].includes(event.key)) {
				event.preventDefault();
				const range = selectionBounds(anchor ?? focus, focus, cells);
				applyEdits(
					cells
						.filter((cell) => intersects(cell, range))
						.map((cell) => ({ address: cell.address, text: '' }))
				);
				return;
			}
		}
		if (command && event.key.toLowerCase() === 'a') {
			event.preventDefault();
			anchor = cells[0];
			select(cells[cells.length - 1], true);
			return;
		}
		if (event.key === 'Escape') {
			select(focus);
			return;
		}
		if (event.key === 'Enter' && (command || event.altKey)) {
			focus.element.querySelector('a')?.click();
			return;
		}
		if (
			['ArrowDown', 'Enter', 'PageDown'].includes(event.key) &&
			focus.endRow >= rows[rows.length - 1] - 1
		)
			extendGrid(40, 0);
		if (['ArrowRight', 'Tab'].includes(event.key) && focus.endCol >= cols[cols.length - 1] - 1)
			extendGrid(0, 8);
		let r = focus.row,
			c = focus.col;
		const next = (values: number[], current: number, end: number, direction: number) =>
			direction > 0
				? (values.find((v) => v > end) ?? end)
				: ([...values].reverse().find((v) => v < current) ?? current);
		switch (event.key) {
			case 'ArrowRight':
				c = command ? cols[cols.length - 1] : next(cols, c, focus.endCol, 1);
				break;
			case 'ArrowLeft':
				c = command ? cols[0] : next(cols, c, focus.endCol, -1);
				break;
			case 'ArrowDown':
				r = command ? rows[rows.length - 1] : next(rows, r, focus.endRow, 1);
				break;
			case 'ArrowUp':
				r = command ? rows[0] : next(rows, r, focus.endRow, -1);
				break;
			case 'Home':
				c = cols[0];
				if (command) r = rows[0];
				break;
			case 'End':
				c = command ? lastUsedCol : cols[cols.length - 1];
				if (command) r = lastUsedRow;
				break;
			case 'PageDown':
			case 'PageUp':
				r =
					rows[
						Math.max(
							0,
							Math.min(
								rows.length - 1,
								rows.indexOf(r) +
									(event.key === 'PageDown' ? 1 : -1) *
										Math.max(1, Math.floor(viewport.clientHeight / 28) - 1)
							)
						)
					];
				break;
			case 'Tab': {
				const index = cells.indexOf(focus) + (event.shiftKey ? -1 : 1);
				if (!cells[index]) return; // Let Tab leave the grid at either end.
				event.preventDefault();
				select(cells[index]);
				return;
			}
			case 'Enter':
				r = next(rows, r, focus.endRow, event.shiftKey ? -1 : 1);
				break;
			default:
				return;
		}
		event.preventDefault();
		const cell = at(r, c);
		if (cell) select(cell, event.shiftKey && event.key !== 'Enter');
	}
	const copiedText = () =>
		anchor && focus ? selectionTSV(cells, rows, cols, selectionBounds(anchor, focus, cells)) : '';
	function copy(event: ClipboardEvent) {
		if (input || !anchor || !focus || !fromTarget(event.target)) return;
		event.preventDefault();
		event.clipboardData?.setData('text/plain', copiedText());
		status = t('Copied to clipboard');
	}
	async function copySelection() {
		try {
			await navigator.clipboard.writeText(copiedText());
			status = t('Copied to clipboard');
		} catch {
			status = t('Could not copy. Select a cell and press Ctrl+C or ⌘C.');
		}
	}
	function findNext(direction = 1) {
		if (!matches.length) return;
		matchIndex =
			matchIndex < 0
				? direction > 0
					? 0
					: matches.length - 1
				: (matchIndex + direction + matches.length) % matches.length;
		select(matches[matchIndex]);
	}
	function followLink(event: MouseEvent) {
		const link = (event.target as Element).closest<HTMLElement>('[data-sheet-link]');
		if (!link) return;
		event.preventDefault();
		const match = /^(?:(?:'((?:[^']|'')+)'|([^!]+))!)?\$?([A-Z]+)\$?([1-9]\d*)$/i.exec(
			link.dataset.sheetLink ?? ''
		);
		if (!match) {
			status = t('This workbook link cannot be opened in the preview.');
			return;
		}
		const sheet = (match[1]?.replace(/''/g, "'") ?? match[2]) || selectedSheet;
		const target = `${match[3].toUpperCase()}${match[4]}`;
		if (sheet !== selectedSheet && sheetNames.includes(sheet)) {
			pendingLink = target;
			onSheetChange?.(sheet);
		} else {
			const cell = cells.find((c) => c.address === target);
			if (cell) select(cell);
			else status = t('This workbook link cannot be opened in the preview.');
		}
	}
	function extendGrid(extraRows: number, extraCols: number) {
		if (!extraRows && !extraCols) return;
		const table = viewport.querySelector('table');
		if (!table || !rows.length || !cols.length) return;
		const added: Cell[] = [];
		const blank = (row: number, col: number) => {
			const element = document.createElement('td');
			const address = cellAddress(row, col);
			Object.assign(element.dataset, {
				cell: address,
				row,
				col,
				endRow: row,
				endCol: col,
				value: '',
				formula: ''
			});
			element.setAttribute('role', 'gridcell');
			element.setAttribute('aria-selected', 'false');
			element.tabIndex = -1;
			added.push({ element, address, row, col, endRow: row, endCol: col, value: '', formula: '' });
			return element;
		};
		const newCols = Array.from(
			{ length: Math.min(extraCols, 16383 - cols[cols.length - 1]) },
			(_, i) => cols[cols.length - 1] + i + 1
		);
		for (const col of newCols) {
			const column = document.createElement('col');
			column.dataset.col = String(col);
			column.style.width = '112px';
			table.querySelector('colgroup')!.append(column);
			const header = document.createElement('th');
			header.className = 'excel-col-hdr';
			header.scope = 'col';
			header.setAttribute('role', 'columnheader');
			header.dataset.col = String(col);
			header.textContent = cellAddress(0, col).slice(0, -1);
			const handle = document.createElement('button');
			handle.type = 'button';
			handle.className = 'excel-resize';
			handle.dataset.resize = String(col);
			handle.setAttribute('aria-label', `${t('Resize column')} ${header.textContent}`);
			handle.title = t(
				'Drag or use arrow keys to resize. Double-click or press Enter to fit contents.'
			);
			header.append(handle);
			table.querySelector('thead tr')!.append(header);
			for (const row of table.querySelectorAll<HTMLTableRowElement>('tbody tr'))
				row.append(blank(Number(row.dataset.row), col));
		}
		cols = [...cols, ...newCols];
		table.style.width = `${parseFloat(table.style.width) + newCols.length * 112}px`;
		const newRows = Array.from(
			{ length: Math.min(extraRows, 1048575 - rows[rows.length - 1]) },
			(_, i) => rows[rows.length - 1] + i + 1
		);
		const fragment = document.createDocumentFragment();
		for (const row of newRows) {
			const tr = document.createElement('tr');
			tr.dataset.row = String(row);
			tr.style.height = '28px';
			tr.setAttribute('role', 'row');
			const header = document.createElement('th');
			header.className = 'excel-row-num';
			header.scope = 'row';
			header.setAttribute('role', 'rowheader');
			header.textContent = String(row + 1);
			tr.append(header);
			for (const col of cols) tr.append(blank(row, col));
			fragment.append(tr);
		}
		table.querySelector('tbody')!.append(fragment);
		rows = [...rows, ...newRows];
		cells = [...cells, ...added].sort((a, b) => a.row - b.row || a.col - b.col);
	}

	function grid(node: HTMLDivElement, _html: string) {
		let generation = 0;
		let scrollFrame = 0;
		let scrollTop = 0,
			scrollLeft = 0;
		const scroll = () => {
			if (scrollFrame) return;
			scrollFrame = requestAnimationFrame(() => {
				scrollFrame = 0;
				const down = node.scrollTop > scrollTop,
					right = node.scrollLeft > scrollLeft;
				scrollTop = node.scrollTop;
				scrollLeft = node.scrollLeft;
				extendGrid(
					down && node.scrollHeight - node.scrollTop - node.clientHeight < 350 ? 40 : 0,
					right && node.scrollWidth - node.scrollLeft - node.clientWidth < 250 ? 8 : 0
				);
			});
		};
		async function refresh() {
			const sameSheet = renderedSheet === selectedSheet;
			const previousAnchor = sameSheet ? anchor?.address : '';
			const previousFocus = sameSheet ? restoreAddress || focus?.address : '';
			const focusGrid = !!restoreAddress || node.contains(document.activeElement);
			const previousRows = sameSheet ? rows[rows.length - 1] : 0,
				previousCols = sameSheet ? cols[cols.length - 1] : 0;
			const version = ++generation;
			await tick();
			if (version !== generation) return;
			cells = Array.from(node.querySelectorAll<HTMLTableCellElement>('[data-cell]')).map(
				(element) => ({
					element,
					row: Number(element.dataset.row),
					col: Number(element.dataset.col),
					endRow: Number(element.dataset.endRow),
					endCol: Number(element.dataset.endCol),
					address: element.dataset.cell!,
					value: element.dataset.value ?? '',
					formula: element.dataset.formula ?? ''
				})
			);
			rows = Array.from(node.querySelectorAll('tbody tr'))
				.map((row) => Number(row.getAttribute('data-row')))
				.filter(Number.isFinite);
			cols = Array.from(node.querySelectorAll('col[data-col]')).map((col) =>
				Number(col.getAttribute('data-col'))
			);
			const table = node.querySelector('table');
			table?.setAttribute('aria-readonly', String(!editor || saving));
			extendGrid(
				Math.max(0, (previousRows ?? 0) - rows[rows.length - 1]),
				Math.max(0, (previousCols ?? 0) - cols[cols.length - 1])
			);
			usedRange = table?.dataset.usedRange ?? '';
			lastUsedRow = Number(table?.dataset.lastRow ?? 0);
			lastUsedCol = Number(table?.dataset.lastCol ?? 0);
			anchor = null;
			focus = null;
			address = '';
			formula = '';
			matchIndex = -1;
			for (const [col, width] of widths.get(selectedSheet) ?? []) setWidth(col, width);
			const target = cells.find((c) => c.address === (pendingLink || previousFocus)) ?? cells[0];
			anchor = cells.find((c) => c.address === previousAnchor) ?? null;
			if (target) select(target, !!anchor, !!pendingLink || focusGrid);
			pendingLink = '';
			restoreAddress = '';
			renderedSheet = selectedSheet;
			notifyChange();
		}
		node.addEventListener('scroll', scroll, { passive: true });
		node.addEventListener('pointerdown', pointerDown);
		node.addEventListener('keydown', keydown);
		node.addEventListener('copy', copy);
		node.addEventListener('paste', paste);
		node.addEventListener('click', followLink);
		node.addEventListener('dblclick', doubleClick);
		window.addEventListener('pointermove', pointerMove);
		window.addEventListener('pointerup', pointerUp);
		window.addEventListener('pointercancel', pointerUp);
		window.addEventListener('blur', pointerUp);
		void refresh();
		return {
			update: refresh,
			destroy() {
				generation++;
				cancelAnimationFrame(scrollFrame);
				node.removeEventListener('scroll', scroll);
				node.removeEventListener('pointerdown', pointerDown);
				node.removeEventListener('keydown', keydown);
				node.removeEventListener('copy', copy);
				node.removeEventListener('paste', paste);
				node.removeEventListener('click', followLink);
				node.removeEventListener('dblclick', doubleClick);
				window.removeEventListener('pointermove', pointerMove);
				window.removeEventListener('pointerup', pointerUp);
				window.removeEventListener('pointercancel', pointerUp);
				window.removeEventListener('blur', pointerUp);
			}
		};
	}
</script>

<div use:shortcuts class="excel-viewer text-gray-600 dark:text-gray-300">
	<div class="excel-formula-bar border-b border-gray-100/40 dark:border-gray-800/25">
		<output
			class="text-gray-500 dark:text-gray-400 border-r border-gray-100/40 dark:border-gray-800/25"
			aria-label={t('Selected range')}>{address || '—'}</output
		>
		<span class="text-gray-400 dark:text-gray-500" aria-hidden="true">ƒx</span>
		<input
			aria-label={t('Formula or value')}
			readonly
			value={formula}
			placeholder={t('Select a cell to inspect its value or formula')}
		/>
	</div>
	{#if searchOpen}
		<div
			class="excel-find flex items-center gap-1 rounded-lg border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-sm"
			role="search"
			aria-label={t('Find in sheet')}
		>
			<span class="text-gray-400 dark:text-gray-500 px-1"><Icon name="search" size={13} /></span>
			<input
				bind:this={searchInput}
				bind:value={query}
				aria-label={t('Find in sheet')}
				placeholder={t('Find in sheet')}
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						event.preventDefault();
						findNext(event.shiftKey ? -1 : 1);
					}
					if (event.key === 'Escape') closeSearch();
				}}
			/>
			{#if query}<span class="excel-match-count text-gray-400 dark:text-gray-500" aria-live="polite"
					>{matches.length ? `${matchIndex + 1} / ${matches.length}` : t('No matches')}</span
				>{/if}
			<button
				class="excel-control"
				type="button"
				aria-label={t('Previous match')}
				title={t('Previous match')}
				disabled={!matches.length}
				on:click={() => findNext(-1)}><Icon name="chevron-up" size={13} /></button
			>
			<button
				class="excel-control"
				type="button"
				aria-label={t('Next match')}
				title={t('Next match')}
				disabled={!matches.length}
				on:click={() => findNext()}><Icon name="chevron-down" size={13} /></button
			>
			<button
				class="excel-control"
				type="button"
				aria-label={t('Close search')}
				title={t('Close search')}
				on:click={closeSearch}><Icon name="xmark" size={12} /></button
			>
		</div>
	{/if}
	<div bind:this={viewport} use:grid={html} class="excel-viewport">{@html html}</div>
	<div class="excel-footer border-t border-gray-100/40 dark:border-gray-800/25">
		<div class="excel-tabs scrollbar-none" role="tablist" aria-label={t('Worksheets')}>
			{#each sheetNames as name}<button
					type="button"
					role="tab"
					aria-selected={selectedSheet === name}
					class="shrink-0 px-2 py-1 text-xs rounded-md transition-colors {selectedSheet === name
						? 'bg-gray-100/40 dark:bg-gray-800/25 text-gray-700 dark:text-gray-200 font-normal'
						: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20 hover:text-gray-600 dark:hover:text-gray-300'}"
					disabled={saving}
					on:click={() => {
						if (flushEdit()) onSheetChange?.(name);
					}}>{name}</button
				>{/each}
		</div>
		<span
			class="excel-status text-gray-400 dark:text-gray-500"
			role="status"
			title={status}
			aria-live="polite"
			>{status || (usedRange ? `${t('Used range')}: ${usedRange}` : t('Empty sheet'))}</span
		>
		<div class="flex shrink-0 items-center gap-0.5 text-gray-500 dark:text-gray-400">
			{#if editor}
				<button
					type="button"
					class="excel-control"
					aria-label={t('Undo')}
					title={t('Undo')}
					disabled={!canUndo || saving}
					on:click={() => history(false)}><Icon name="undo" size={13} /></button
				>
				<button
					type="button"
					class="excel-control"
					aria-label={t('Redo')}
					title={t('Redo')}
					disabled={!canRedo || saving}
					on:click={() => history(true)}><Icon name="redo" size={13} /></button
				>
			{/if}
			<button
				class="excel-control"
				type="button"
				aria-label={t('Find in sheet')}
				title={`${t('Find in sheet')} (Ctrl/⌘F)`}
				on:click={openSearch}><Icon name="search" size={13} /></button
			>
			<button
				class="excel-control"
				type="button"
				aria-label={t('Copy')}
				title={`${t('Copy')} (Ctrl/⌘C)`}
				disabled={!focus}
				on:click={copySelection}><Icon name="copy" size={13} /></button
			>
		</div>
	</div>
</div>

<style>
	.excel-viewer {
		--excel-font-scale: 0.875;
		display: flex;
		flex-direction: column;
		position: relative;
		height: 100%;
		min-height: 0;
		min-width: 0;
		font-size: 0.75rem;
		background: transparent;
	}
	.excel-control {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 1.5rem;
		min-width: 1.5rem;
		border-radius: 0.25rem;
		transition:
			color 100ms,
			background-color 100ms;
	}
	.excel-control:hover:not(:disabled) {
		color: var(--color-gray-800);
		background: color-mix(in srgb, var(--color-gray-100) 40%, transparent);
	}
	:global(.dark) .excel-control:hover:not(:disabled) {
		color: var(--color-gray-200);
		background: color-mix(in srgb, var(--color-gray-800) 25%, transparent);
	}
	button:disabled {
		opacity: 0.3;
	}
	input:focus {
		outline: none;
		box-shadow: none;
	}
	.excel-formula-bar:focus-within,
	.excel-find:focus-within {
		border-color: var(--color-gray-600);
	}
	:global(.dark) .excel-formula-bar:focus-within,
	:global(.dark) .excel-find:focus-within {
		border-color: var(--color-gray-400);
	}
	.excel-formula-bar {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		min-height: 1.875rem;
	}
	.excel-formula-bar output {
		min-width: 5rem;
		max-width: 11.25rem;
		padding: 0.375rem 0.5rem;
		text-align: center;
		font-size: 0.6875rem;
		font-variant-numeric: tabular-nums;
	}
	.excel-formula-bar span {
		padding: 0 0.625rem;
		font-family: serif;
		font-style: italic;
	}
	.excel-formula-bar input {
		flex: 1;
		min-width: 0;
		padding: 0.375rem 0.5rem 0.375rem 0;
		background: transparent;
		border: 0;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 0.6875rem;
	}
	.excel-formula-bar input::placeholder {
		color: var(--color-gray-400);
	}
	:global(.dark) .excel-formula-bar input::placeholder {
		color: var(--color-gray-500);
	}
	.excel-find {
		position: absolute;
		z-index: 5;
		top: 2.125rem;
		right: 0.5rem;
		max-width: calc(100% - 1rem);
		padding: 0.25rem;
	}
	.excel-find input {
		width: 9rem;
		min-width: 0;
		flex: 1;
		background: transparent;
		border: 0;
		padding: 0.25rem;
		font-size: 0.75rem;
	}
	.excel-match-count {
		font-size: 0.625rem;
		white-space: nowrap;
		padding: 0 0.25rem;
	}
	.excel-viewport {
		flex: 1;
		min-height: 0;
		overflow: auto;
		position: relative;
		background: #fff;
		color: var(--color-gray-800, #202124);
	}
	.excel-viewport :global(table) {
		table-layout: fixed;
		border-collapse: separate;
		border-spacing: 0;
		font-family: inherit;
		font-size: 0.75rem;
		line-height: 1.3;
	}
	.excel-viewport :global(td),
	.excel-viewport :global(th) {
		border-right: 1px solid var(--color-gray-200, #e5e7eb);
		border-bottom: 1px solid var(--color-gray-200, #e5e7eb);
		padding: 4px 8px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: pre;
		vertical-align: bottom;
		position: relative;
	}
	.excel-viewport :global(td) {
		cursor: cell;
		scroll-margin: 30px 0 0 48px;
		user-select: none;
	}
	.excel-viewport :global(th) {
		background: var(--color-gray-50, #f9fafb);
		color: var(--color-gray-400, #9ca3af);
		font-family: inherit;
		font-size: 0.625rem;
		font-weight: 400;
		user-select: none;
	}
	:global(.dark) .excel-viewport :global(th) {
		background: var(--color-gray-850);
		color: var(--color-gray-500);
		border-color: var(--color-gray-800);
	}
	.excel-viewport :global(thead th) {
		position: sticky;
		top: 0;
		z-index: 2;
		height: 24px;
		text-align: center;
		vertical-align: middle;
	}
	.excel-viewport :global(.excel-row-num) {
		position: sticky;
		left: 0;
		z-index: 1;
		text-align: right;
	}
	.excel-viewport :global(thead .excel-row-num) {
		z-index: 3;
	}
	.excel-viewport :global(td[aria-selected='true']) {
		background-image: linear-gradient(
			color-mix(in srgb, var(--color-blue-500, #3b82f6) 10%, transparent),
			color-mix(in srgb, var(--color-blue-500, #3b82f6) 10%, transparent)
		);
	}
	.excel-viewport :global(td.excel-active),
	.excel-viewport :global(td:focus) {
		outline: 2px solid var(--color-blue-500, #3b82f6);
		outline-offset: -2px;
	}
	.excel-viewport :global(a) {
		color: var(--color-blue-600, #2563eb);
		text-decoration: underline;
	}
	.excel-viewport :global(.excel-comment) {
		position: absolute;
		right: 1px;
		top: 0;
		font-size: 9px;
		color: var(--color-amber-600, #d97706);
	}
	.excel-viewport :global(.excel-resize) {
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		width: 7px;
		cursor: col-resize;
		touch-action: none;
	}
	.excel-viewport :global(.excel-resize:hover),
	.excel-viewport :global(.excel-resize:focus-visible) {
		outline: none;
		background: linear-gradient(to left, var(--color-gray-600) 1px, transparent 1px);
	}
	:global(.dark) .excel-viewport :global(.excel-resize:hover),
	:global(.dark) .excel-viewport :global(.excel-resize:focus-visible) {
		background: linear-gradient(to left, var(--color-gray-400) 1px, transparent 1px);
	}
	.excel-viewport :global(.excel-cell-input) {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		min-height: 26px;
		padding: 4px 7px;
		margin: 0;
		resize: none;
		border: 1px solid var(--color-gray-600, #4b5563);
		outline: none;
		box-shadow: none;
		border-radius: 0;
		background: white;
		color: #111827;
		font: inherit;
		line-height: inherit;
		text-align: inherit;
	}
	.excel-footer {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
		padding: 0.375rem;
	}
	.excel-tabs {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		overflow: auto;
		flex: 1;
		min-width: 0;
	}
	.excel-status {
		font-size: 0.625rem;
		white-space: nowrap;
		max-width: 40%;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	@media (max-width: 600px) {
		.excel-status {
			max-width: 5.5rem;
		}
		.excel-footer {
			gap: 0.25rem;
		}
		.excel-formula-bar output {
			min-width: 4.5rem;
		}
	}
</style>
