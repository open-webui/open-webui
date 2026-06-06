<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import { basicSetup, EditorView } from 'codemirror';
	import { keymap } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';
	import { json } from '@codemirror/lang-json';
	import { indentWithTab } from '@codemirror/commands';
	import { indentUnit } from '@codemirror/language';
	import { oneDark } from '@codemirror/theme-one-dark';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let output: any[] = [];
	export let onChange: (output: any[]) => void = () => {};

	let viewMode: 'visual' | 'json' = 'visual';
	let jsonError = '';

	// --- CodeMirror ---
	let cmContainer: HTMLDivElement;
	let cmEditor: EditorView | null = null;
	let editorTheme = new Compartment();

	function initCodeMirror() {
		if (cmEditor || !cmContainer) return;
		const isDark = document.documentElement.classList.contains('dark');
		cmEditor = new EditorView({
			state: EditorState.create({
				doc: JSON.stringify(output, null, 2),
				extensions: [
					basicSetup,
					keymap.of([indentWithTab]),
					indentUnit.of('  '),
					json(),
					editorTheme.of(isDark ? oneDark : []),
					EditorView.theme({
						'&': { fontSize: '13px' },
						'.cm-content': { fontFamily: 'ui-monospace, monospace' },
						'.cm-scroller': { maxHeight: '320px', overflow: 'auto' },
						'&.cm-focused': { outline: 'none' }
					}),
					EditorView.updateListener.of((e) => {
						if (e.docChanged) {
							try {
								const parsed = JSON.parse(e.state.doc.toString());
								if (Array.isArray(parsed)) {
									jsonError = '';
									output = parsed;
									onChange(output);
								} else {
									jsonError = 'Must be a JSON array';
								}
							} catch {
								jsonError = 'Invalid JSON';
							}
						}
					})
				]
			}),
			parent: cmContainer
		});
	}

	function destroyCodeMirror() {
		if (cmEditor) {
			cmEditor.destroy();
			cmEditor = null;
		}
	}

	async function switchToJson() {
		viewMode = 'json';
		await tick();
		initCodeMirror();
	}

	function switchToVisual() {
		if (jsonError) return;
		destroyCodeMirror();
		viewMode = 'visual';
	}

	onDestroy(() => destroyCodeMirror());

	// --- Display items ---

	interface DisplayItem {
		type: 'message' | 'reasoning' | 'function_call' | 'code_interpreter' | 'openai_tool';
		indices: number[];
		item: any;
		outputItem?: any;
	}

	function buildDisplayItems(items: any[]): DisplayItem[] {
		const result: DisplayItem[] = [];
		const outputByCallId: Record<string, { item: any; index: number }> = {};

		for (let i = 0; i < items.length; i++) {
			if (items[i]?.type === 'function_call_output') {
				outputByCallId[items[i].call_id] = { item: items[i], index: i };
			}
		}

		for (let i = 0; i < items.length; i++) {
			const item = items[i];
			const t = item?.type ?? '';
			if (t === 'message') {
				result.push({ type: 'message', indices: [i], item });
			} else if (t === 'reasoning') {
				result.push({ type: 'reasoning', indices: [i], item });
			} else if (t === 'function_call') {
				const paired = outputByCallId[item.call_id];
				result.push({
					type: 'function_call',
					indices: paired ? [i, paired.index] : [i],
					item,
					outputItem: paired?.item
				});
			} else if (t === 'function_call_output') {
				// grouped with function_call
			} else if (t === 'open_webui:code_interpreter') {
				result.push({ type: 'code_interpreter', indices: [i], item });
			} else if (['web_search_call', 'file_search_call', 'computer_call'].includes(t)) {
				result.push({ type: 'openai_tool', indices: [i], item });
			}
		}
		return result;
	}

	$: displayItems = buildDisplayItems(output);

	// --- Helpers ---

	function getMessageText(item: any): string {
		return (item.content ?? [])
			.filter((p: any) => p.type === 'output_text' || 'text' in p)
			.map((p: any) => p.text ?? '')
			.join('\n');
	}

	function updateMessageText(idx: number, text: string) {
		const next = [...output];
		const item = { ...next[idx] };
		const parts = (item.content ?? []).filter((p: any) => p.type === 'output_text' || 'text' in p);
		item.content = [{ ...(parts[0] ?? { type: 'output_text' }), text }];
		next[idx] = item;
		output = next;
		onChange(output);
	}

	function getReasoningText(item: any): string {
		return (item.summary ?? item.content ?? [])
			.filter((p: any) => 'text' in p)
			.map((p: any) => p.text ?? '')
			.join('');
	}

	function updateReasoningText(idx: number, text: string) {
		const next = [...output];
		const item = { ...next[idx] };
		const key = item.summary ? 'summary' : 'content';
		item[key] = [{ type: 'text', text }];
		next[idx] = item;
		output = next;
		onChange(output);
	}

	function deleteIndices(indices: number[]) {
		const rm = new Set(indices);
		output = output.filter((_, i) => !rm.has(i));
		onChange(output);
	}

	function formatArgs(args: any): string {
		if (!args) return '';
		try {
			return typeof args === 'string' ? args : JSON.stringify(args, null, 2);
		} catch {
			return String(args);
		}
	}

	function resizeEl(el: HTMLTextAreaElement) {
		const c = document.getElementById('messages-container');
		const s = c?.scrollTop;
		el.style.height = '';
		el.style.height = `${el.scrollHeight}px`;
		if (c && s !== undefined) c.scrollTop = s;
	}

	function autoResize(e: Event) {
		resizeEl(e.target as HTMLTextAreaElement);
	}

	/** Svelte action: auto-expand textarea to fit content on mount */
	function fitContent(el: HTMLTextAreaElement) {
		resizeEl(el);
	}

	function getItemLabel(di: DisplayItem): string {
		switch (di.type) {
			case 'message':
				return 'Text';
			case 'reasoning':
				return 'Thought';
			case 'function_call':
				return di.item.name ?? 'Tool';
			case 'code_interpreter':
				return 'Code';
			case 'openai_tool': {
				const names: Record<string, string> = {
					web_search_call: 'Search',
					file_search_call: 'Files',
					computer_call: 'Computer'
				};
				return names[di.item.type] ?? di.item.type;
			}
			default:
				return 'Item';
		}
	}
</script>

<div class="w-full relative">
	<!-- Mode toggle -->
	<div class="absolute -top-0.5 right-0.5 z-10">
		<Tooltip
			content={viewMode === 'visual'
				? $i18n.t('Switch to JSON editor')
				: $i18n.t('Switch to visual editor')}
		>
			<button
				class="text-xs px-2 py-0.5 rounded-full transition-all text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200/50 dark:hover:bg-gray-700/50"
				on:click={() => (viewMode === 'visual' ? switchToJson() : switchToVisual())}
			>
				{viewMode === 'visual' ? $i18n.t('Visual') : 'JSON'}
			</button>
		</Tooltip>
	</div>

	{#if viewMode === 'json'}
		<div
			bind:this={cmContainer}
			class="w-full rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-800"
		/>
		{#if jsonError}
			<div class="text-xs text-red-500 mt-1.5 px-1">{jsonError}</div>
		{/if}
	{:else}
		<!-- Visual editor: playground-style rows -->
		<div class="space-y-2 p-2 pt-3">
			{#each displayItems as di, idx}
				<div class="flex gap-2 group">
					<!-- Role label -->
					<div class="flex items-start pt-1.5">
						<div
							class="text-[11px] font-semibold uppercase tracking-wide min-w-[4.5rem] text-gray-400 dark:text-gray-500"
						>
							{getItemLabel(di)}
						</div>
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						{#if di.type === 'message'}
							<textarea
								use:fitContent
								class="w-full bg-transparent outline-hidden resize-none overflow-hidden text-sm p-1.5 rounded-lg"
								value={getMessageText(di.item)}
								on:input={(e) => {
									updateMessageText(di.indices[0], e.target.value);
									autoResize(e);
								}}
								placeholder={$i18n.t('Message text...')}
								rows="1"
							/>
						{:else if di.type === 'reasoning'}
							<textarea
								use:fitContent
								class="w-full bg-transparent outline-hidden resize-none overflow-hidden text-sm text-gray-500 dark:text-gray-400 p-1.5 rounded-lg"
								value={getReasoningText(di.item)}
								on:input={(e) => {
									updateReasoningText(di.indices[0], e.target.value);
									autoResize(e);
								}}
								placeholder={$i18n.t('Reasoning text...')}
								rows="1"
							/>
						{:else if di.type === 'function_call'}
							<div class="text-sm p-1.5 text-gray-500 dark:text-gray-400">
								{#if di.item.arguments}
									<pre
										class="text-xs font-mono whitespace-pre-wrap overflow-x-auto pb-0.5">{formatArgs(
											di.item.arguments
										)}</pre>
								{/if}
								{#if di.outputItem}
									<pre
										class="text-xs font-mono whitespace-pre-wrap overflow-x-auto mt-1 max-h-32 overflow-y-auto">{JSON.stringify(
											di.outputItem.output,
											null,
											2
										)}</pre>
								{/if}
							</div>
						{:else if di.type === 'code_interpreter'}
							<div class="text-sm p-1.5 text-gray-500 dark:text-gray-400">
								{#if di.item.code}
									<pre class="text-xs font-mono whitespace-pre overflow-x-auto">{di.item.code}</pre>
								{/if}
								{#if di.item.output}
									<pre
										class="text-xs font-mono whitespace-pre-wrap overflow-x-auto mt-1 max-h-32 overflow-y-auto">{typeof di
											.item.output === 'object'
											? JSON.stringify(di.item.output, null, 2)
											: di.item.output}</pre>
								{/if}
							</div>
						{:else if di.type === 'openai_tool'}
							<div class="text-sm p-1.5 text-gray-500 dark:text-gray-400">
								{#if di.item.action?.queries || di.item.queries}
									<span class="text-xs"
										>{(di.item.action?.queries ?? di.item.queries ?? []).join(', ')}</span
									>
								{/if}
							</div>
						{/if}
					</div>

					<!-- Delete -->
					<div class="pt-1.5">
						<button
							class="invisible group-hover:visible p-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition rounded-lg"
							on:click={() => deleteIndices(di.indices)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
								/>
							</svg>
						</button>
					</div>
				</div>
			{/each}

			{#if displayItems.length === 0}
				<div class="text-sm text-gray-400 dark:text-gray-500 italic px-1">
					{$i18n.t('No output items')}
				</div>
			{/if}
		</div>
	{/if}
</div>
