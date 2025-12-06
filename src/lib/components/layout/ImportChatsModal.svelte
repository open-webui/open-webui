<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Modal from '../common/Modal.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { extractChatsFromFile } from '$lib/utils/chatImport';
	import { getImportOrigin, convertOpenAIChats, convertDeepseekChats } from '$lib/utils';

	export let show = false;
	export let onImport: (chats: any[]) => Promise<void>;

	let dropActive = false;
	let loading = false;
	let importing = false;
	let filterOpen = true;
	let errorMsg = '';
	let fileName = '';
	let rawChats: any[] = [];
	let selectedIndices: Set<number> = new Set();

	const resetState = () => {
		errorMsg = '';
		fileName = '';
		rawChats = [];
		selectedIndices = new Set();
		filterOpen = true;
	};

	$: if (!show) {
		resetState();
	}

	const parseJsonOrJsonlText = async (file: File) => {
		const text = await file.text();
		try {
			const parsed = JSON.parse(text);
			return Array.isArray(parsed) ? parsed : [parsed];
		} catch (jsonError) {
			const lines = text
				.split('\n')
				.map((l) => l.trim())
				.filter((l) => l.length > 0);

			if (lines.length === 0) {
				throw new Error('File is empty, nothing to parse');
			}

			try {
				return lines.map((line) => JSON.parse(line));
			} catch (lineError) {
				throw new Error('Plain text JSONL must contain one valid JSON object per line');
			}
		}
	};

	const normalizeChats = (chats: any) => {
		if (Array.isArray(chats)) return chats;

		if (chats && typeof chats === 'object') {
			if (Array.isArray((chats as any).conversations)) {
				return (chats as any).conversations;
			}
		}

		throw new Error('File content must be a JSON array of chats');
	};

	const handleFiles = async (files: FileList | File[]) => {
		if (!files || files.length === 0) return;
		const file = files[0];
		loading = true;
		errorMsg = '';
		fileName = file.name;
		try {
			const ext = file.name.split('.').pop()?.toLowerCase();
			let chats: any = null;

			if (ext === 'txt' || ext === 'jsonl') {
				chats = await parseJsonOrJsonlText(file);
			} else {
				chats = await extractChatsFromFile(file);
			}

			chats = normalizeChats(chats);

			if (chats.length === 0) {
				throw new Error('File contained zero chat records');
			}

			const origin = getImportOrigin(chats);

			if (origin === 'openai') {
				chats = convertOpenAIChats(chats);
			} else if (origin === 'deepseek') {
				chats = convertDeepseekChats(chats);
			}

			rawChats = chats;
			selectedIndices = new Set(rawChats.map((_, idx) => idx));
			filterOpen = true;
		} catch (error) {
			console.error(error);
			errorMsg = error instanceof Error ? error.message : `${error}`;
			rawChats = [];
			selectedIndices = new Set();
		} finally {
			loading = false;
		}
	};

	const toggleRow = (idx: number) => {
		const next = new Set(selectedIndices);
		if (next.has(idx)) {
			next.delete(idx);
		} else {
			next.add(idx);
		}
		selectedIndices = next;
	};

	const toggleSelectAll = (checked: boolean) => {
		selectedIndices = checked ? new Set(rawChats.map((_, idx) => idx)) : new Set();
	};

	const confirmImport = async () => {
		if (!rawChats.length) {
			toast.error('Please upload a chat history file first');
			return;
		}
		const chatsToImport =
			selectedIndices.size > 0 ? rawChats.filter((_, idx) => selectedIndices.has(idx)) : rawChats;

		if (!chatsToImport.length) {
			toast.error('No records selected');
			return;
		}

		try {
			importing = true;
			const jsonlString = chatsToImport.map((item) => JSON.stringify(item)).join('\n');
			const blob = new Blob([jsonlString], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `filtered_chats_${new Date().toISOString().slice(0, 10)}.jsonl`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);

			await onImport(chatsToImport);
			show = false;
			toast.success('Starting import for the filtered chats');
		} catch (error) {
			console.error(error);
			toast.error(error instanceof Error ? error.message : `${error}`);
		} finally {
			importing = false;
		}
	};

	const displayRows = () =>
		rawChats.map((chat, idx) => {
			const meta = chat?.meta ?? chat?.chat?.meta ?? chat;
			const title =
				meta?.title ??
				chat?.title ??
				chat?.chat?.title ??
				meta?.subject ??
				'Untitled chat';
			const date =
				meta?.inserted_at ??
				meta?.created_at ??
				meta?.updated_at ??
				chat?.inserted_at ??
				chat?.created_at ??
				chat?.updated_at ??
				'-';

			return { idx, title, date };
		});

	let fileInputEl: HTMLInputElement;

	const handleFileInputChange = (event: Event) => {
		const input = event.currentTarget as HTMLInputElement;
		handleFiles(input.files ?? []);
	};

	const handleSelectAllChange = (event: Event) => {
		const input = event.currentTarget as HTMLInputElement;
		toggleSelectAll(input.checked);
	};
</script>

<Modal bind:show size="xl" className="bg-white/95 dark:bg-gray-900/95 rounded-4xl p-1">
	<div class="p-6 space-y-6 font-primary">
		<div class="flex items-start justify-between gap-4">
			<div>
				<div class="text-lg font-semibold text-gray-900 dark:text-white">Chat Import Center</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Upload your exported history, filter the records you need, then import.
				</div>
			</div>
			<button
				class="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
				on:click={() => (show = false)}
				aria-label="Close import modal"
			>
				✕
			</button>
		</div>

		<div class="space-y-4">
			<div class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-900/60 p-4">
				<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2">1. Prepare file</div>
				<div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed space-y-1">
					<p>
						Supported formats: <strong>JSON (.json)</strong>, <strong>JSONL (.jsonl/.txt)</strong>, or
						OpenAI ZIP export (auto-converted).
					</p>
					<p>Large exports can be filtered below to speed up the import.</p>
				</div>
			</div>

			<div class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-3">
				<div class="flex items-center justify-between">
					<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">2. Filter records</div>
					<button
						class="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850"
						on:click={() => (filterOpen = !filterOpen)}
						type="button"
					>
						{filterOpen ? 'Hide filters' : 'Show filters'}
					</button>
				</div>

				<div
					class={`border-2 border-dashed rounded-xl p-4 transition ${
						dropActive
							? 'border-blue-400 bg-blue-50/70 dark:border-blue-400/80 dark:bg-blue-950/40'
							: 'border-gray-200 dark:border-gray-800 bg-gray-50/40 dark:bg-gray-900'
					}`}
					on:dragover|preventDefault={() => (dropActive = true)}
					on:dragleave|preventDefault={() => (dropActive = false)}
					on:drop|preventDefault={(e) => {
						dropActive = false;
						handleFiles(e.dataTransfer?.files ?? []);
					}}
				>
					<div class="flex flex-col items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
						<div class="font-medium text-gray-900 dark:text-white">
							{fileName ? `Selected: ${fileName}` : 'Drag a file here or click to upload'}
						</div>
						<div class="flex items-center gap-2">
							<button
								class="px-3 py-1.5 rounded-lg bg-gray-900 text-white text-xs hover:bg-gray-800 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
								on:click={() => fileInputEl.click()}
								type="button"
							>
								Choose file
							</button>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								Supports .json / .jsonl / .txt / .zip exports
							</div>
						</div>
						{#if loading}
							<div class="flex items-center gap-2 text-blue-600 dark:text-blue-300">
								<Spinner className="size-4" />
								<span>Parsing file...</span>
							</div>
						{/if}
						{#if errorMsg}
							<div class="text-xs text-red-500">{errorMsg}</div>
						{/if}
					</div>
					<input
						bind:this={fileInputEl}
						type="file"
						accept=".json,.jsonl,.zip,.txt,application/json"
						hidden
						on:change={handleFileInputChange}
					/>
				</div>

				{#if filterOpen}
					<div class="space-y-3">
						<div class="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
							<div>
								Total: {rawChats.length} | Selected: {selectedIndices.size}
								{selectedIndices.size === 0 && rawChats.length > 0
									? ' (none selected will import all)'
									: ''}
							</div>
							<label class="flex items-center gap-2 cursor-pointer select-none">
								<input
									type="checkbox"
									class="accent-blue-600"
									checked={rawChats.length > 0 && selectedIndices.size === rawChats.length}
									indeterminate={selectedIndices.size > 0 && selectedIndices.size < rawChats.length}
									on:change={handleSelectAllChange}
								/>
								<span>Select / Deselect all</span>
							</label>
						</div>

						<div class="max-h-64 overflow-auto rounded-xl border border-gray-100 dark:border-gray-800">
							<table class="w-full text-sm">
								<thead class="text-left bg-gray-50 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
									<tr>
										<th class="w-14 py-2 px-3">Pick</th>
										<th class="py-2 px-3">Title / Summary</th>
										<th class="w-48 py-2 px-3">Timestamp</th>
									</tr>
								</thead>
								<tbody>
									{#if !rawChats.length}
										<tr>
											<td colspan="3" class="py-4 text-center text-gray-500 dark:text-gray-400">
												Upload a file to see filterable records
											</td>
										</tr>
									{:else}
										{#each displayRows() as row}
											<tr class="border-t border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-900/60">
												<td class="py-2 px-3">
													<input
														type="checkbox"
														checked={selectedIndices.has(row.idx)}
														on:change={() => toggleRow(row.idx)}
													/>
												</td>
												<td class="py-2 px-3">
													<div class="text-sm text-gray-900 dark:text-white line-clamp-2">
														{row.title}
													</div>
												</td>
												<td class="py-2 px-3 text-xs text-gray-500 dark:text-gray-400">
													{row.date}
												</td>
											</tr>
										{/each}
									{/if}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>

			<div class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-2">
				<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">3. Import</div>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					Confirmed records will be imported into your current account.
				</div>
				<div class="flex items-center justify-end gap-3">
					<button
						class="px-4 py-2 text-sm rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850"
						on:click={() => (show = false)}
						type="button"
					>
						Cancel
					</button>
					<button
						class="px-4 py-2 text-sm rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
						on:click={confirmImport}
						disabled={loading || importing || (!rawChats.length && !loading)}
						type="button"
					>
						{#if importing}
							<Spinner className="size-4" />
						{/if}
						<span>{importing ? 'Importing...' : 'Confirm import'}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</Modal>
