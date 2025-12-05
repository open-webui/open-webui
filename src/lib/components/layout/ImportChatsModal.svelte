<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Modal from '../common/Modal.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { extractChatsFromFile } from '$lib/utils/chatImport';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';

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
				throw new Error('文件为空，无法解析');
			}

			try {
				return lines.map((line) => JSON.parse(line));
			} catch (lineError) {
				throw new Error('纯文本/JSONL 文件需包含有效的 JSON 或逐行 JSON 对象');
			}
		}
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

			if (getImportOrigin(chats) === 'openai') {
				chats = convertOpenAIChats(chats);
			}

			if (!Array.isArray(chats)) {
				throw new Error('文件内容需为 JSON 数组');
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
			toast.error('请先上传对话记录文件');
			return;
		}
		const chatsToImport =
			selectedIndices.size > 0 ? rawChats.filter((_, idx) => selectedIndices.has(idx)) : rawChats;

		if (!chatsToImport.length) {
			toast.error('未选择任何记录');
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
			toast.success('开始导入筛选后的对话记录');
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
				'未命名对话';
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
				<div class="text-lg font-semibold text-gray-900 dark:text-white">对话记录导入中心</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					完成准备、筛选后再执行导入，提升成功率与速度。
				</div>
			</div>
			<button
				class="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
				on:click={() => (show = false)}
				aria-label="关闭导入中心"
			>
				✕
			</button>
		</div>

		<div class="space-y-4">
			<div class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-900/60 p-4">
				<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2">
					1. 准备您的对话记录
				</div>
				<div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed space-y-1">
					<p>请确保导出文件格式为 <strong>JSON (.json)</strong> 或 <strong>纯文本 (.txt)</strong>。</p>
					<p>
						请前往原平台导出历史对话，如 DeepSeek — 系统设置 — 数据管理 — 导出所有历史对话，
						ChatGPT — 设置 — 数据管理 — 导出数据。
					</p>
					<p>如果导出的文件内容过多或过大，建议使用下方的筛选功能生成新的导入文件，以加快导入速度。</p>
				</div>
			</div>

			<div class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-3">
				<div class="flex items-center justify-between">
					<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">2. 筛选记录</div>
					<button
						class="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850"
						on:click={() => (filterOpen = !filterOpen)}
					>
						{filterOpen ? '收起高级筛选器' : '高级筛选器'}
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
							{fileName ? `已选择：${fileName}` : '拖拽文件到此处，或点击上传'}
						</div>
						<div class="flex items-center gap-2">
							<button
								class="px-3 py-1.5 rounded-lg bg-gray-900 text-white text-xs hover:bg-gray-800 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
								on:click={() => fileInputEl.click()}
								type="button"
							>
								选择文件
							</button>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								支持 .json / .txt，OpenAI 导出支持自动转换
							</div>
						</div>
						{#if loading}
							<div class="flex items-center gap-2 text-blue-600 dark:text-blue-300">
								<Spinner className="size-4" />
								<span>正在解析文件...</span>
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
								总数：{rawChats.length} | 已选：{selectedIndices.size}
								{selectedIndices.size === 0 && rawChats.length > 0 ? '（未选则默认导入全部）' : ''}
							</div>
							<label class="flex items-center gap-2 cursor-pointer select-none">
								<input
									type="checkbox"
									class="accent-blue-600"
									checked={rawChats.length > 0 && selectedIndices.size === rawChats.length}
									indeterminate={selectedIndices.size > 0 && selectedIndices.size < rawChats.length}
									on:change={handleSelectAllChange}
								/>
								<span>全选 / 取消全选</span>
							</label>
						</div>

						<div class="max-h-64 overflow-auto rounded-xl border border-gray-100 dark:border-gray-800">
							<table class="w-full text-sm">
								<thead class="text-left bg-gray-50 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
									<tr>
										<th class="w-14 py-2 px-3">选择</th>
										<th class="py-2 px-3">标题 / 摘要</th>
										<th class="w-48 py-2 px-3">时间</th>
									</tr>
								</thead>
								<tbody>
									{#if !rawChats.length}
										<tr>
											<td colspan="3" class="py-4 text-center text-gray-500 dark:text-gray-400">
												请先上传文件以查看可筛选的记录
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
				<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">3. 导入记录</div>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					确认后将按筛选结果导入到当前账户的对话列表中。
				</div>
				<div class="flex items-center justify-end gap-3">
					<button
						class="px-4 py-2 text-sm rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850"
						on:click={() => (show = false)}
						type="button"
					>
						取消
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
						<span>{importing ? '正在导入...' : '确认导入'}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</Modal>
