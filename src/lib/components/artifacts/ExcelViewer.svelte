<script lang="ts">
	import { onMount, tick } from 'svelte';
	import * as XLSX from 'xlsx';
	import fileSaver from 'file-saver';
	import type { ExcelArtifact } from '$lib/types';

	const { saveAs } = fileSaver;

	export let file: ExcelArtifact;

	// Constants for virtual scrolling
	const ROW_HEIGHT = 36; // pixels per row
	const BUFFER_ROWS = 5; // extra rows to render above/below viewport
	const COL_WIDTH = 120; // default column width

	let sheetNames: string[] = [];
	let activeSheet: string = '';
	let rows: any[][] = [];
	let workbook: XLSX.WorkBook | null = null;
	let loading = true;
	let error: string | null = null;

	// Track changed cells
	type CellKey = string; // 'r,c'
	const changedCells = new Map<CellKey, { row: number; col: number; value: any }>();

	let saving = false;
	let saveMessage = '';

	// Store original cell data including formulas
	let cellData: Map<string, { value: any; formula?: string }> = new Map();

	// Track if file might contain charts (show info message)
	let hasChartWarning = false;

	// Virtual scrolling state
	let containerElement: HTMLDivElement;
	let scrollTop = 0;
	let containerHeight = 0;
	let visibleStartIndex = 0;
	let visibleEndIndex = 0;
	let visibleRows: { index: number; data: any[] }[] = [];

	// Column count for header
	let colCount = 0;

	// Calculate visible rows based on scroll position
	function updateVisibleRows() {
		if (!rows.length || !containerHeight) return;

		const headerHeight = ROW_HEIGHT; // Account for header row
		const availableHeight = containerHeight - headerHeight;

		// Calculate visible range
		visibleStartIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_ROWS);
		const visibleCount = Math.ceil(availableHeight / ROW_HEIGHT) + BUFFER_ROWS * 2;
		visibleEndIndex = Math.min(rows.length, visibleStartIndex + visibleCount);

		// Build visible rows array with original indices
		visibleRows = [];
		for (let i = visibleStartIndex; i < visibleEndIndex; i++) {
			visibleRows.push({ index: i, data: rows[i] });
		}
	}

	// Handle scroll events
	function onScroll(e: Event) {
		const target = e.target as HTMLDivElement;
		scrollTop = target.scrollTop;
		updateVisibleRows();
	}

	// Observe container size changes
	function setupResizeObserver() {
		if (!containerElement) return;

		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				containerHeight = entry.contentRect.height;
				updateVisibleRows();
			}
		});

		observer.observe(containerElement);
		return () => observer.disconnect();
	}

	// Get Excel-style column letter (A, B, ... Z, AA, AB, etc.)
	function getColumnLetter(colIndex: number): string {
		let letter = '';
		let temp = colIndex;
		while (temp >= 0) {
			letter = String.fromCharCode(65 + (temp % 26)) + letter;
			temp = Math.floor(temp / 26) - 1;
		}
		return letter;
	}

	async function loadWorkbook() {
		try {
			loading = true;
			error = null;

			const resp = await fetch(file.url);
			if (!resp.ok) {
				throw new Error(`Failed to fetch file: ${resp.statusText}`);
			}

			const arrayBuffer = await resp.arrayBuffer();
			workbook = XLSX.read(arrayBuffer, { type: 'array' });

			sheetNames = workbook.SheetNames;

			// Check for chart-related content
			hasChartWarning = false;
			for (const name of sheetNames) {
				const ws = workbook.Sheets[name];
				if (
					ws['!type'] === 'chart' ||
					name.toLowerCase().includes('chart') ||
					name.toLowerCase().includes('graph')
				) {
					hasChartWarning = true;
					break;
				}
				if (ws['!drawings'] || ws['!charts']) {
					hasChartWarning = true;
					break;
				}
			}

			// Set active sheet
			if (file.meta?.activeSheet && sheetNames.includes(file.meta.activeSheet)) {
				activeSheet = file.meta.activeSheet;
			} else {
				activeSheet = sheetNames[0] || '';
			}

			loadSheet(activeSheet);
			loading = false;

			// Wait for DOM update then setup observers
			await tick();
			setupResizeObserver();
		} catch (e) {
			console.error('Error loading workbook:', e);
			error = e instanceof Error ? e.message : 'Failed to load Excel file';
			loading = false;
		}
	}

	function loadSheet(sheetName: string) {
		if (!workbook || !sheetName) return;

		try {
			const ws = workbook.Sheets[sheetName];
			if (!ws) {
				error = `Sheet "${sheetName}" not found`;
				return;
			}

			const range = XLSX.utils.decode_range(ws['!ref'] || 'A1');
			const numRows = range.e.r - range.s.r + 1;
			const numCols = range.e.c - range.s.c + 1;

			cellData.clear();
			rows = [];

			for (let r = 0; r < numRows; r++) {
				const row: any[] = [];
				for (let c = 0; c < numCols; c++) {
					const cellAddress = XLSX.utils.encode_cell({ r: range.s.r + r, c: range.s.c + c });
					const cell = ws[cellAddress];

					if (cell) {
						const key = `${r},${c}`;
						cellData.set(key, {
							value: cell.v !== undefined ? cell.v : '',
							formula: cell.f
						});
						row.push(cell.v !== undefined ? cell.v : '');
					} else {
						row.push('');
					}
				}
				rows.push(row);
			}

			// Ensure all rows have the same length
			const maxCols = Math.max(...rows.map((r) => r.length), 1);
			colCount = maxCols;
			rows = rows.map((row) => {
				const paddedRow = [...row];
				while (paddedRow.length < maxCols) {
					paddedRow.push('');
				}
				return paddedRow;
			});

			// Reset scroll and update visible rows
			scrollTop = 0;
			if (containerElement) {
				containerElement.scrollTop = 0;
			}
			changedCells.clear();
			saveMessage = '';

			updateVisibleRows();
		} catch (e) {
			console.error('Error loading sheet:', e);
			error = e instanceof Error ? e.message : 'Failed to load sheet';
		}
	}

	function onSheetChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		activeSheet = target.value;
		loadSheet(activeSheet);
	}

	function markCellChanged(r: number, c: number, value: any) {
		const key = `${r},${c}`;
		changedCells.set(key, { row: r + 1, col: c + 1, value });
		changedCells = changedCells; // Trigger reactivity
		saveMessage = '';
	}

	function onCellChange(r: number, c: number, e: Event) {
		const target = e.target as HTMLInputElement;
		const value = target.value;
		rows[r][c] = value;
		markCellChanged(r, c, value);
	}

	async function saveChanges() {
		if (!changedCells.size || !file.fileId) {
			saveMessage = 'No changes to save';
			return;
		}

		try {
			saving = true;
			saveMessage = '';

			const changes = Array.from(changedCells.values()).map((change) => {
				const value = change.value;
				const isFormula = typeof value === 'string' && value.startsWith('=');
				return {
					row: change.row,
					col: change.col,
					value: value,
					isFormula: isFormula
				};
			});

			const response = await fetch('/api/v1/excel/update', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					fileId: file.fileId,
					sheet: activeSheet,
					changes
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'Failed to save changes');
			}

			const result = await response.json();
			changedCells.clear();
			changedCells = changedCells;
			saveMessage = result.message || 'Changes saved successfully';
			saving = false;

			setTimeout(async () => {
				const originalUrl = file.url;
				const separator = file.url.includes('?') ? '&' : '?';
				file.url = `${originalUrl}${separator}_t=${Date.now()}`;
				await loadWorkbook();
				file.url = originalUrl;
			}, 300);
		} catch (e) {
			console.error('Error saving changes:', e);
			saveMessage = e instanceof Error ? e.message : 'Failed to save changes';
			saving = false;
		}
	}

	function downloadExcel() {
		if (!workbook) {
			saveMessage = 'No workbook loaded to download';
			return;
		}

		try {
			if (changedCells.size > 0 && activeSheet) {
				const ws = workbook.Sheets[activeSheet];
				if (ws) {
					for (const [, change] of changedCells) {
						const cellAddress = XLSX.utils.encode_cell({ r: change.row - 1, c: change.col - 1 });
						if (!ws[cellAddress]) {
							ws[cellAddress] = { t: 's', v: change.value };
						} else {
							ws[cellAddress].v = change.value;
						}
					}
				}
			}

			const wbout = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
			const blob = new Blob([wbout], {
				type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
			});

			const filename = file.name || 'download.xlsx';
			saveAs(blob, filename);
		} catch (e) {
			console.error('Error downloading Excel file:', e);
			saveMessage = e instanceof Error ? e.message : 'Failed to download file';
		}
	}

	onMount(() => {
		if (file?.url) {
			loadWorkbook();
		}
	});

	$: if (file?.url) {
		loadWorkbook();
	}

	// Reactive: update visible rows when rows change
	$: if (rows.length) {
		updateVisibleRows();
	}

	// Calculate total height for scroll area
	$: totalHeight = rows.length * ROW_HEIGHT;
	$: paddingTop = visibleStartIndex * ROW_HEIGHT;
</script>

<div class="excel-viewer">
	<div class="excel-header">
		<div class="excel-header-left">
			<span class="excel-filename">{file.name}</span>
			{#if sheetNames.length > 0}
				<select
					bind:value={activeSheet}
					on:change={onSheetChange}
					class="excel-sheet-selector"
					disabled={loading}
				>
					{#each sheetNames as name}
						<option value={name}>{name}</option>
					{/each}
				</select>
			{/if}
			{#if rows.length > 0}
				<span class="excel-row-count">{rows.length.toLocaleString()} rows</span>
			{/if}
		</div>
		<div class="excel-header-right">
			{#if changedCells.size > 0}
				<span class="excel-changes-badge">{changedCells.size} changes</span>
			{/if}
			<button
				class="excel-download-button"
				on:click={downloadExcel}
				disabled={!workbook || loading}
				title="Download Excel file"
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
					<polyline points="7 10 12 15 17 10"/>
					<line x1="12" y1="15" x2="12" y2="3"/>
				</svg>
				Download
			</button>
			<button
				class="excel-save-button"
				on:click={saveChanges}
				disabled={saving || changedCells.size === 0}
			>
				{saving ? 'Saving...' : 'Save'}
			</button>
		</div>
	</div>

	{#if hasChartWarning}
		<div class="excel-chart-notice">
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="12" cy="12" r="10"/>
				<line x1="12" y1="16" x2="12" y2="12"/>
				<line x1="12" y1="8" x2="12.01" y2="8"/>
			</svg>
			<span>Charts and graphs are displayed as data tables. Download the file to view charts in Excel.</span>
		</div>
	{/if}

	{#if saveMessage}
		<div class="excel-message" class:excel-message-success={!saveMessage.includes('Failed')}>
			{saveMessage}
		</div>
	{/if}

	{#if loading}
		<div class="excel-loading">Loading Excel file...</div>
	{:else if error}
		<div class="excel-error">
			<strong>Error:</strong>
			{error}
		</div>
	{:else if rows.length > 0}
		<div
			class="excel-grid-container"
			bind:this={containerElement}
			on:scroll={onScroll}
		>
			<div class="excel-virtual-scroll" style="height: {totalHeight + ROW_HEIGHT}px;">
				<table class="excel-grid" style="transform: translateY({paddingTop}px);">
					<thead>
						<tr style="height: {ROW_HEIGHT}px;">
							<th class="excel-row-header excel-corner-header">#</th>
							{#each Array(colCount) as _, colIndex}
								<th class="excel-col-header">{getColumnLetter(colIndex)}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each visibleRows as { index: rowIndex, data: row } (rowIndex)}
							<tr style="height: {ROW_HEIGHT}px;">
								<td class="excel-row-header">{rowIndex + 1}</td>
								{#each row as cell, colIndex}
									<td class="excel-cell">
										<input
											type="text"
											value={cell}
											on:change={(e) => onCellChange(rowIndex, colIndex, e)}
											class="excel-cell-input"
											class:excel-cell-changed={changedCells.has(`${rowIndex},${colIndex}`)}
										/>
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<div class="excel-empty">No data to display</div>
	{/if}
</div>

<style>
	.excel-viewer {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--color-gray-50);
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.excel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background: white;
		border-bottom: 1px solid var(--color-gray-200);
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.excel-header-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
		min-width: 0;
	}

	.excel-header-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.excel-filename {
		font-weight: 600;
		color: #000;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.excel-row-count {
		font-size: 0.75rem;
		color: var(--color-gray-500);
		white-space: nowrap;
	}

	.excel-sheet-selector {
		padding: 0.25rem 0.5rem;
		border: 1px solid var(--color-gray-300);
		border-radius: 0.25rem;
		background: white;
		font-size: 0.875rem;
		color: var(--color-gray-700);
		cursor: pointer;
	}

	.excel-sheet-selector:hover {
		border-color: var(--color-gray-400);
	}

	.excel-changes-badge {
		padding: 0.25rem 0.5rem;
		background: var(--color-orange-100);
		color: var(--color-orange-700);
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.excel-download-button,
	.excel-save-button {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.375rem 0.75rem;
		border: none;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.2s;
	}

	.excel-download-button {
		background: var(--color-gray-600);
		color: white;
	}

	.excel-download-button:hover:not(:disabled) {
		background: var(--color-gray-700);
	}

	.excel-save-button {
		background: var(--color-blue-600);
		color: white;
	}

	.excel-save-button:hover:not(:disabled) {
		background: var(--color-blue-700);
	}

	.excel-download-button:disabled,
	.excel-save-button:disabled {
		background: var(--color-gray-300);
		color: var(--color-gray-500);
		cursor: not-allowed;
	}

	.excel-chart-notice {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: var(--color-blue-50);
		color: var(--color-blue-700);
		border-bottom: 1px solid var(--color-blue-200);
		font-size: 0.875rem;
	}

	.excel-chart-notice svg {
		flex-shrink: 0;
	}

	.excel-message {
		padding: 0.5rem 1rem;
		background: var(--color-red-100);
		color: var(--color-red-700);
		border-bottom: 1px solid var(--color-red-200);
		font-size: 0.875rem;
	}

	.excel-message-success {
		background: var(--color-green-100);
		color: var(--color-green-700);
		border-bottom-color: var(--color-green-200);
	}

	.excel-loading,
	.excel-error,
	.excel-empty {
		padding: 2rem;
		text-align: center;
		color: var(--color-gray-600);
	}

	.excel-error {
		color: var(--color-red-600);
	}

	.excel-grid-container {
		flex: 1;
		overflow: auto;
		background: white;
		position: relative;
	}

	.excel-virtual-scroll {
		position: relative;
		width: fit-content;
		min-width: 100%;
	}

	.excel-grid {
		width: fit-content;
		min-width: 100%;
		border-collapse: collapse;
		font-size: 1rem;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
		font-variant-numeric: tabular-nums;
		position: sticky;
		top: 0;
	}

	.excel-grid thead {
		position: sticky;
		top: 0;
		z-index: 10;
	}

	.excel-row-header,
	.excel-col-header {
		background: var(--color-gray-100);
		color: var(--color-gray-800);
		font-weight: 600;
		text-align: center;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--color-gray-300);
		min-width: 3rem;
		font-size: 0.875rem;
		white-space: nowrap;
	}

	.excel-corner-header {
		position: sticky;
		left: 0;
		z-index: 11;
	}

	.excel-row-header {
		position: sticky;
		left: 0;
		z-index: 2;
	}

	.excel-col-header {
		min-width: 120px;
	}

	.excel-cell {
		padding: 0;
		border: 1px solid var(--color-gray-200);
		background: white;
	}

	.excel-cell-input {
		width: 100%;
		min-width: 120px;
		height: 100%;
		padding: 0.5rem 0.75rem;
		border: none;
		background: transparent;
		font-family: inherit;
		font-size: inherit;
		color: #000;
		line-height: 1.4;
		box-sizing: border-box;
	}

	.excel-cell-input:focus {
		outline: 2px solid var(--color-blue-500);
		outline-offset: -2px;
		background: var(--color-blue-50);
	}

	.excel-cell-changed {
		background: var(--color-yellow-50);
		border-color: var(--color-yellow-300);
	}

	.excel-cell-changed:focus {
		background: var(--color-yellow-100);
	}
</style>
