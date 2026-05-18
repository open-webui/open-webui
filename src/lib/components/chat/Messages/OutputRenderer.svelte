<script lang="ts">
	import { getContext } from 'svelte';
	import { settings } from '$lib/stores';

	import Markdown from './Markdown.svelte';
	import ConsecutiveDetailsGroup from './Markdown/ConsecutiveDetailsGroup.svelte';
	import ToolCallDisplay from '$lib/components/common/ToolCallDisplay.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import FloatingButtons from '../ContentRenderer/FloatingButtons.svelte';

	import { onDestroy, tick } from 'svelte';
	import { mobile, chatId, showArtifacts, showControls, artifactCode, showEmbeds } from '$lib/stores';

	const i18n = getContext('i18n');

	export let id: string = '';
	export let output: any[] = [];
	export let done: boolean = true;
	export let model = null;
	export let sources = null;

	export let save = false;
	export let preview = false;
	export let editCodeBlock = true;
	export let topPadding = false;
	export let floatingButtons = true;

	export let onSave: Function = () => {};
	export let onSourceClick: Function = () => {};
	export let onTaskClick: Function = () => {};
	export let onSetInputText: Function = () => {};

	let contentContainerElement: HTMLDivElement;
	let floatingButtonsElement;

	// Build lookup map for function_call_output items by call_id
	$: toolOutputs = (() => {
		const map: Record<string, any> = {};
		for (const item of output) {
			if (item.type === 'function_call_output') {
				map[item.call_id] = item;
			}
		}
		return map;
	})();

	// Source IDs for citation linking (same logic as ContentRenderer)
	let sourceIds: string[] = [];
	$: getSourceIds(sources);
	const getSourceIds = (sources) => {
		const result: string[] = [];
		for (const source of sources ?? []) {
			for (let index = 0; index < (source.document ?? []).length; index++) {
				if (model?.info?.meta?.capabilities?.citations == false) {
					result.push('N/A');
					continue;
				}
				const metadata = source.metadata?.[index];
				const id = metadata?.source ?? 'N/A';
				if (metadata?.name) {
					result.push(metadata.name);
				} else if (id.startsWith('http://') || id.startsWith('https://')) {
					result.push(id);
				} else {
					result.push(source?.source?.name ?? id);
				}
			}
		}
		sourceIds = [...new Set(result)];
	};

	const GROUPABLE_TYPES = new Set(['reasoning', 'function_call', 'open_webui:code_interpreter']);

	// Convert an output item to the "detail token" shape that
	// ConsecutiveDetailsGroup / ToolCallDisplay / Collapsible expect.
	function toDetailToken(item: any): any {
		if (item.type === 'function_call') {
			const resultItem = toolOutputs[item.call_id];
			const isDone = item.status === 'completed' || !!resultItem;
			const resultParts =
				resultItem?.output
					?.filter((p: any) => p.type !== 'input_image')
					.map((p: any) => p.text ?? '') ?? [];
			const resultText = resultParts.join('');
			return {
				attributes: {
					type: 'tool_calls',
					name: item.name ?? '',
					done: isDone ? 'true' : 'false',
					arguments:
						typeof item.arguments === 'string'
							? item.arguments
							: JSON.stringify(item.arguments ?? ''),
					embeds: resultItem?.embeds ? JSON.stringify(resultItem.embeds) : '',
					files: resultItem?.files ? JSON.stringify(resultItem.files) : ''
				},
				summary: isDone ? 'Tool Executed' : 'Executing...',
				text: resultText
			};
		} else if (item.type === 'reasoning') {
			const sourceList = item.summary || item.content || [];
			const text = sourceList.map((p: any) => p.text ?? '').join('');
			const isDone = item.status === 'completed' || item.duration != null;
			return {
				attributes: {
					type: 'reasoning',
					done: isDone ? 'true' : 'false',
					duration: String(item.duration ?? '')
				},
				summary: isDone ? `Thought for ${item.duration ?? 0} seconds` : 'Thinking…',
				text: text
					.split('\n')
					.map((l) => (l.startsWith('>') ? l : `> ${l}`))
					.join('\n')
			};
		} else if (item.type === 'open_webui:code_interpreter') {
			const isDone = item.status === 'completed';
			const code = item.code ?? '';
			const lang = item.lang ?? 'python';
			const text = code ? `\`\`\`${lang}\n${code}\n\`\`\`` : '';
			return {
				attributes: {
					type: 'code_interpreter',
					done: isDone ? 'true' : 'false',
					duration: String(item.duration ?? ''),
					output: item.output ? JSON.stringify(item.output) : ''
				},
				summary: isDone ? 'Analyzed' : 'Analyzing…',
				text
			};
		}
		return null;
	}

	// Group output items into display items (message blocks and grouped details)
	$: displayItems = (() => {
		const items: any[] = [];
		let currentGroup: any[] = [];

		const flushGroup = () => {
			if (currentGroup.length > 1) {
				items.push({ type: 'detail_group', tokens: [...currentGroup] });
			} else if (currentGroup.length === 1) {
				items.push({ type: 'detail_single', token: currentGroup[0] });
			}
			currentGroup = [];
		};

		for (const item of output) {
			if (item.type === 'function_call_output') continue; // handled via function_call
			if (GROUPABLE_TYPES.has(item.type)) {
				const token = toDetailToken(item);
				if (token) currentGroup.push(token);
			} else if (item.type === 'message') {
				flushGroup();
				const text = (item.content ?? []).map((p: any) => p.text ?? '').join('');
				if (text.trim()) {
					items.push({ type: 'message', text });
				}
			} else {
				// Unknown type — render as plain text fallback so nothing is silently lost
				flushGroup();
				const fallbackText = (item.content ?? []).map((p: any) => p.text ?? '').join('');
				if (fallbackText.trim()) {
					items.push({ type: 'message', text: fallbackText });
				}
			}
		}
		flushGroup();
		return items;
	})();

	// Floating button positioning (same as ContentRenderer)
	const updateButtonPosition = (event: MouseEvent) => {
		const buttonsContainerElement = document.getElementById(`floating-buttons-${id}`);
		if (
			!contentContainerElement?.contains(event.target as Node) &&
			!buttonsContainerElement?.contains(event.target as Node)
		) {
			closeFloatingButtons();
			return;
		}

		setTimeout(async () => {
			await tick();
			if (!contentContainerElement?.contains(event.target as Node)) return;

			let selection = window.getSelection();
			if (selection && selection.toString().trim().length > 0) {
				const range = selection.getRangeAt(0);
				const rect = range.getBoundingClientRect();
				const parentRect = contentContainerElement.getBoundingClientRect();
				const top = rect.bottom - parentRect.top;
				const left = rect.left - parentRect.left;

				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'block';
					const spaceOnRight = parentRect.width - left;
					let halfScreenWidth = $mobile ? window.innerWidth / 2 : window.innerWidth / 3;

					if (spaceOnRight < halfScreenWidth) {
						const right = parentRect.right - rect.right;
						buttonsContainerElement.style.right = `${right}px`;
						buttonsContainerElement.style.left = 'auto';
					} else {
						buttonsContainerElement.style.left = `${left}px`;
						buttonsContainerElement.style.right = 'auto';
					}
					buttonsContainerElement.style.top = `${top + 5}px`;
				}
			} else {
				closeFloatingButtons();
			}
		}, 0);
	};

	const closeFloatingButtons = () => {
		const buttonsContainerElement = document.getElementById(`floating-buttons-${id}`);
		if (buttonsContainerElement) {
			buttonsContainerElement.style.display = 'none';
		}
		if (floatingButtonsElement && typeof floatingButtonsElement?.closeHandler === 'function') {
			floatingButtonsElement?.closeHandler();
		}
	};

	const keydownHandler = (e: KeyboardEvent) => {
		if (e.key === 'Escape') closeFloatingButtons();
	};

	let listenersAttached = false;

	function attachListeners() {
		if (!listenersAttached && contentContainerElement) {
			contentContainerElement.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('keydown', keydownHandler);
			listenersAttached = true;
		}
	}

	function detachListeners() {
		if (listenersAttached) {
			contentContainerElement?.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('keydown', keydownHandler);
			listenersAttached = false;
		}
	}

	$: if (floatingButtons && contentContainerElement) {
		attachListeners();
	} else {
		detachListeners();
	}

	onDestroy(() => {
		detachListeners();
	});
</script>

<div bind:this={contentContainerElement}>
	{#each displayItems as displayItem, idx (displayItem.type + '_' + idx)}
		{#if displayItem.type === 'message'}
			<Markdown
				id={`${id}-msg-${idx}`}
				content={model?.info?.meta?.capabilities?.citations == false
					? displayItem.text.replace(
							/\s*(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+/g,
							''
						)
					: displayItem.text}
				{model}
				{save}
				{preview}
				{done}
				{editCodeBlock}
				{topPadding}
				{sourceIds}
				{onSourceClick}
				{onTaskClick}
				{onSave}
				onUpdate={async (token) => {
					const { lang, text: code } = token;
					if (
						($settings?.detectArtifacts ?? true) &&
						(['html', 'svg'].includes(lang) || (lang === 'xml' && code.includes('svg'))) &&
						!$mobile &&
						$chatId
					) {
						await tick();
						showArtifacts.set(true);
						showControls.set(true);
					}
				}}
				onPreview={async (value) => {
					await artifactCode.set(value);
					await showControls.set(true);
					await showArtifacts.set(true);
					await showEmbeds.set(false);
				}}
			/>
		{:else if displayItem.type === 'detail_group'}
			<ConsecutiveDetailsGroup
				id={`${id}-group-${idx}`}
				tokens={displayItem.tokens}
				messageDone={done}
			>
				<div slot="content" class="space-y-1">
					{#each displayItem.tokens as detailToken, detailIdx}
						{#if detailToken.attributes?.type === 'tool_calls'}
							<ToolCallDisplay
								id={`${id}-group-${idx}-${detailIdx}-tc`}
								attributes={detailToken.attributes}
								resultContent={detailToken.text}
								grouped={true}
								open={$settings?.expandDetails ?? false}
								className="w-full space-y-1"
							/>
						{:else if detailToken.text?.length > 0}
							<Collapsible
								title={detailToken.summary}
								open={$settings?.expandDetails ?? false}
								attributes={detailToken.attributes}
								messageDone={done}
								className="w-full space-y-1"
								dir="auto"
							>
								<div class="mb-1.5" slot="content">
									<Markdown
										id={`${id}-group-${idx}-${detailIdx}-d`}
										content={detailToken.text}
										{done}
										{editCodeBlock}
									/>
								</div>
							</Collapsible>
						{:else}
							<Collapsible
								title={detailToken.summary}
								open={false}
								disabled={true}
								attributes={detailToken.attributes}
								messageDone={done}
								className="w-full space-y-1"
								dir="auto"
							/>
						{/if}
					{/each}
				</div>
			</ConsecutiveDetailsGroup>
		{:else if displayItem.type === 'detail_single'}
			{@const detailToken = displayItem.token}
			{#if detailToken.attributes?.type === 'tool_calls'}
				<ToolCallDisplay
					id={`${id}-single-${idx}-tc`}
					attributes={detailToken.attributes}
					resultContent={detailToken.text}
					open={$settings?.expandDetails ?? false}
					className="w-full space-y-1"
				/>
			{:else if detailToken.text?.length > 0}
				<Collapsible
					title={detailToken.summary}
					open={$settings?.expandDetails ?? false}
					attributes={detailToken.attributes}
					messageDone={done}
					className="w-full space-y-1"
					dir="auto"
				>
					<div class="mb-1.5" slot="content">
						<Markdown
							id={`${id}-single-${idx}-d`}
							content={detailToken.text}
							{done}
							{editCodeBlock}
						/>
					</div>
				</Collapsible>
			{:else}
				<Collapsible
					title={detailToken.summary}
					open={false}
					disabled={true}
					attributes={detailToken.attributes}
					messageDone={done}
					className="w-full space-y-1"
					dir="auto"
				/>
			{/if}
		{/if}
	{/each}
</div>

{#if floatingButtons}
	<FloatingButtons
		bind:this={floatingButtonsElement}
		{id}
		actions={$settings?.floatingActionButtons ?? []}
		onSetInputText={(text) => {
			onSetInputText(text);
			closeFloatingButtons();
		}}
	/>
{/if}
