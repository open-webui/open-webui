<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import Spinner from '../../common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let data: ArrayBuffer;

	let db: any = null;
	let loading = true;
	let error: string | null = null;

	let tables: string[] = [];
	let selectedTable = '';
	let columns: string[] = [];
	let rows: string[][] = [];
	let totalRows = 0;
	let page = 0;
	const pageSize = 100;

	// Custom query
	let queryMode = false;
	let queryText = '';
	let queryColumns: string[] = [];
	let queryRows: string[][] = [];
	let queryError: string | null = null;

	const init = async () => {
		try {
			const initSqlJs = (await import('sql.js')).default;
			const SQL = await initSqlJs({
				locateFile: () => '/sql.js/sql-wasm.wasm'
			});
			db = new SQL.Database(new Uint8Array(data));

			// Get table list
			const result = db.exec(
				"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
			);
			if (result.length > 0) {
				tables = result[0].values.map((r: string[]) => r[0]);
				if (tables.length > 0) {
					selectTable(tables[0]);
				}
			}
			loading = false;
		} catch (e) {
			loading = false;
			error = e instanceof Error ? e.message : 'Failed to open database';
		}
	};

	const selectTable = (table: string) => {
		if (!db) return;
		selectedTable = table;
		page = 0;
		queryMode = false;
		loadPage();
	};

	const loadPage = () => {
		if (!db || !selectedTable) return;
		try {
			// Get columns
			const info = db.exec(`PRAGMA table_info("${selectedTable}")`);
			if (info.length > 0) {
				columns = info[0].values.map((r: any[]) => r[1] as string);
			}

			// Get total count
			const countResult = db.exec(`SELECT COUNT(*) FROM "${selectedTable}"`);
			if (countResult.length > 0) {
				totalRows = countResult[0].values[0][0] as number;
			}

			// Get page data
			const offset = page * pageSize;
			const result = db.exec(
				`SELECT * FROM "${selectedTable}" LIMIT ${pageSize} OFFSET ${offset}`
			);
			if (result.length > 0) {
				rows = result[0].values.map((r: any[]) => r.map((v: any) => formatValue(v)));
			} else {
				rows = [];
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Query failed';
		}
	};

	const runQuery = () => {
		if (!db || !queryText.trim()) return;
		queryError = null;
		try {
			const result = db.exec(queryText);
			if (result.length > 0) {
				queryColumns = result[0].columns;
				queryRows = result[0].values.map((r: any[]) => r.map((v: any) => formatValue(v)));
			} else {
				queryColumns = [];
				queryRows = [];
			}
		} catch (e) {
			queryError = e instanceof Error ? e.message : 'Query failed';
			queryColumns = [];
			queryRows = [];
		}
	};

	const formatValue = (v: any): string => {
		if (v === null) return 'NULL';
		if (v instanceof Uint8Array) return `[BLOB ${v.length}B]`;
		return String(v);
	};

	$: totalPages = Math.ceil(totalRows / pageSize);

	$: data && init();

	onDestroy(() => {
		if (db) {
			try { db.close(); } catch {}
			db = null;
		}
	});
</script>

<div class="sqlite-view flex flex-col h-full">
	{#if loading}
		<div class="flex items-center justify-center h-full"><Spinner className="size-4" /></div>
	{:else if error}
		<div class="p-3 text-xs text-red-500">{error}</div>
	{:else}
		<!-- Table tabs + query toggle -->
		<div class="flex items-center gap-1 px-2 py-1.5 border-b border-gray-100 dark:border-gray-800 overflow-x-auto scrollbar-none shrink-0">
			{#each tables as table}
				<button
					class="shrink-0 px-2 py-1 text-xs rounded transition
						{table === selectedTable && !queryMode
						? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium'
						: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					on:click={() => selectTable(table)}
				>
					{table}
				</button>
			{/each}
			<div class="flex-1"></div>
			<button
				class="shrink-0 px-2 py-1 text-xs rounded transition
					{queryMode
					? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium'
					: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => { queryMode = !queryMode; }}
			>
				SQL
			</button>
		</div>

		{#if queryMode}
			<!-- Query editor -->
			<div class="p-2 border-b border-gray-100 dark:border-gray-800 shrink-0">
				<div class="flex gap-1.5">
					<textarea
						bind:value={queryText}
						placeholder="SELECT * FROM ..."
						class="flex-1 text-xs font-mono bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded px-2 py-1.5 outline-none resize-none min-h-[2.5rem]"
						rows="2"
						on:keydown={(e) => {
							if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
								e.preventDefault();
								runQuery();
							}
						}}
					></textarea>
					<button
						class="shrink-0 px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition"
						on:click={runQuery}
					>
						{$i18n.t('Run')}
					</button>
				</div>
				{#if queryError}
					<div class="mt-1 text-xs text-red-500">{queryError}</div>
				{/if}
			</div>

			{#if queryColumns.length > 0}
				<div class="flex-1 overflow-auto min-h-0">
					<table class="sqlite-table w-full text-xs font-mono border-collapse">
						<thead>
							<tr>
								<th class="sqlite-row-num">#</th>
								{#each queryColumns as col}
									<th>{col}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each queryRows as row, i}
								<tr>
									<td class="sqlite-row-num">{i + 1}</td>
									{#each row as cell}
										<td class:sqlite-null={cell === 'NULL'}>{cell}</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{:else}
			<!-- Table data -->
			<div class="flex-1 overflow-auto min-h-0">
				{#if columns.length > 0}
					<table class="sqlite-table w-full text-xs font-mono border-collapse">
						<thead>
							<tr>
								<th class="sqlite-row-num">#</th>
								{#each columns as col}
									<th>{col}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each rows as row, i}
								<tr>
									<td class="sqlite-row-num">{page * pageSize + i + 1}</td>
									{#each row as cell}
										<td class:sqlite-null={cell === 'NULL'}>{cell}</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="text-xs text-gray-400 text-center pt-6">{$i18n.t('No data')}</div>
				{/if}
			</div>

			<!-- Pagination -->
			{#if totalPages > 1}
				<div class="flex items-center justify-center gap-3 py-1.5 px-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-500 shrink-0">
					<button
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"
						disabled={page === 0}
						on:click={() => { page--; loadPage(); }}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
							<path fill-rule="evenodd" d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd" />
						</svg>
					</button>
					<span>{page + 1} / {totalPages} ({totalRows.toLocaleString()} rows)</span>
					<button
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"
						disabled={page >= totalPages - 1}
						on:click={() => { page++; loadPage(); }}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
							<path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
						</svg>
					</button>
				</div>
			{/if}
		{/if}
	{/if}
</div>

<style>
	.sqlite-table {
		font-size: 0.7rem;
		line-height: 1.4;
	}
	.sqlite-table th,
	.sqlite-table td {
		padding: 4px 8px;
		text-align: left;
		white-space: nowrap;
		border: 1px solid rgba(128, 128, 128, 0.15);
	}
	.sqlite-table thead th {
		position: sticky;
		top: 0;
		background: rgba(243, 244, 246, 0.95);
		backdrop-filter: blur(4px);
		font-weight: 600;
		color: #374151;
		border-bottom: 2px solid rgba(128, 128, 128, 0.25);
		z-index: 1;
	}
	:global(.dark) .sqlite-table thead th {
		background: rgba(31, 41, 55, 0.95);
		color: #d1d5db;
	}
	.sqlite-table tbody tr:nth-child(even) {
		background: rgba(128, 128, 128, 0.04);
	}
	.sqlite-table tbody tr:hover {
		background: rgba(59, 130, 246, 0.06);
	}
	:global(.dark) .sqlite-table tbody tr:hover {
		background: rgba(59, 130, 246, 0.1);
	}
	.sqlite-table td {
		color: #374151;
		max-width: 300px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	:global(.dark) .sqlite-table td {
		color: #d1d5db;
	}
	.sqlite-row-num {
		color: #9ca3af;
		font-size: 0.6rem;
		text-align: right !important;
		user-select: none;
		width: 1px;
		padding-right: 6px !important;
	}
	:global(.dark) .sqlite-row-num {
		color: #6b7280;
	}
	.sqlite-null {
		color: #9ca3af !important;
		font-style: italic;
	}
	:global(.dark) .sqlite-null {
		color: #6b7280 !important;
	}
</style>
