<script lang="ts">
	import { onMount } from 'svelte';
	import * as XLSX from 'xlsx';
	import type { ExcelArtifact } from '$lib/types';

	export let file: ExcelArtifact;

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

	async function loadWorkbook() {
		try {
			loading = true;
			error = null;

			// Fetch the file
			const resp = await fetch(file.url);
			if (!resp.ok) {
				throw new Error(`Failed to fetch file: ${resp.statusText}`);
			}

			const arrayBuffer = await resp.arrayBuffer();
			workbook = XLSX.read(arrayBuffer, { type: 'array' });

			sheetNames = workbook.SheetNames;

			// Set active sheet
			if (file.meta?.activeSheet && sheetNames.includes(file.meta.activeSheet)) {
				activeSheet = file.meta.activeSheet;
			} else {
				activeSheet = sheetNames[0] || '';
			}

			loadSheet(activeSheet);
			loading = false;
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

			// Convert to 2D array
			rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' }) as any[][];

			// Ensure all rows have the same length (pad shorter rows)
			const maxCols = Math.max(...rows.map((r) => r.length));
			rows = rows.map((row) => {
				const paddedRow = [...row];
				while (paddedRow.length < maxCols) {
					paddedRow.push('');
				}
				return paddedRow;
			});

			// Clear changed cells when switching sheets
			changedCells.clear();
			saveMessage = '';
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
		changedCells.set(key, { row: r + 1, col: c + 1, value }); // Excel is 1-based
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

			const changes = Array.from(changedCells.values());

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
			saveMessage = result.message || 'Changes saved successfully';
			saving = false;

			// Reload the workbook to reflect saved changes
			setTimeout(() => {
				loadWorkbook();
			}, 500);
		} catch (e) {
			console.error('Error saving changes:', e);
			saveMessage = e instanceof Error ? e.message : 'Failed to save changes';
			saving = false;
		}
	}

	onMount(() => {
		if (file?.url) {
			loadWorkbook();
		}
	});

	// Reload when file URL changes
	$: if (file?.url) {
		loadWorkbook();
	}
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
		</div>
		<div class="excel-header-right">
			{#if changedCells.size > 0}
				<span class="excel-changes-badge">{changedCells.size} changes</span>
			{/if}
			<button
				class="excel-save-button"
				on:click={saveChanges}
				disabled={saving || changedCells.size === 0}
			>
				{saving ? 'Saving...' : 'Save'}
			</button>
		</div>
	</div>

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
		<div class="excel-grid-container">
			<table class="excel-grid">
				<thead>
					<tr>
						<th class="excel-row-header">#</th>
						{#each rows[0] as _, colIndex}
							<th class="excel-col-header">{String.fromCharCode(65 + colIndex)}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each rows as row, rowIndex}
						<tr>
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
		color: var(--color-gray-900);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
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

	.excel-save-button {
		padding: 0.375rem 0.75rem;
		background: var(--color-blue-600);
		color: white;
		border: none;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.2s;
	}

	.excel-save-button:hover:not(:disabled) {
		background: var(--color-blue-700);
	}

	.excel-save-button:disabled {
		background: var(--color-gray-300);
		color: var(--color-gray-500);
		cursor: not-allowed;
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
	}

	.excel-grid {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	.excel-row-header,
	.excel-col-header {
		position: sticky;
		background: var(--color-gray-100);
		color: var(--color-gray-700);
		font-weight: 600;
		text-align: center;
		padding: 0.375rem 0.5rem;
		border: 1px solid var(--color-gray-300);
		min-width: 3rem;
		font-size: 0.75rem;
	}

	.excel-row-header {
		left: 0;
		z-index: 2;
	}

	.excel-col-header {
		top: 0;
		z-index: 1;
	}

	.excel-cell {
		padding: 0;
		border: 1px solid var(--color-gray-200);
		background: white;
	}

	.excel-cell-input {
		width: 100%;
		min-width: 100px;
		padding: 0.375rem 0.5rem;
		border: none;
		background: transparent;
		font-family: inherit;
		font-size: inherit;
		color: var(--color-gray-900);
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
