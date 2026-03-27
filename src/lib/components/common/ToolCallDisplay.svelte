<script lang="ts">
	import { decode } from 'html-entities';
	import { v4 as uuidv4 } from 'uuid';

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Spinner from './Spinner.svelte';
	import Markdown from '../chat/Messages/Markdown.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import Image from './Image.svelte';
	import FullHeightIframe from './FullHeightIframe.svelte';
	import { settings } from '$lib/stores';
	import { getToolPresentation } from '$lib/utils/toolPresentation';

	export let id: string = '';
	export let attributes: {
		type?: string;
		id?: string;
		name?: string;
		arguments?: string;
		result?: string;
		files?: string;
		embeds?: string;
		done?: string;
	} = {};

	export let open = false;
	export let grouped = false;
	export let className = '';

	const RESULT_PREVIEW_LIMIT = 10000;
	let expandedResult = false;

	$: if (!open) expandedResult = false;
	export let buttonClassName =
		'w-full text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition';

	const componentId = id || uuidv4();

	function parseJSONString(str: string) {
		try {
			return parseJSONString(JSON.parse(str));
		} catch (e) {
			return str;
		}
	}

	function formatJSONString(str: string) {
		try {
			const parsed = parseJSONString(str);
			if (typeof parsed === 'object') {
				return JSON.stringify(parsed, null, 2);
			} else {
				return String(parsed);
			}
		} catch (e) {
			return str;
		}
	}

	function parseArguments(str: string): Record<string, unknown> | null {
		try {
			const parsed = parseJSONString(str);
			if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
				return parsed as Record<string, unknown>;
			}
			return null;
		} catch {
			return null;
		}
	}

	function handleFaviconError(event: Event) {
		const image = event.currentTarget as HTMLImageElement | null;
		if (image) {
			image.src = '/favicon.png';
		}
	}

	function scrollToSources() {
		const el = document.getElementById(id) ?? document.getElementById(componentId);
		if (el) {
			el.dispatchEvent(new CustomEvent('scroll-to-sources', { bubbles: true, composed: true }));
		}
	}

	$: args = decode(attributes?.arguments ?? '');
	$: result = decode(attributes?.result ?? '');
	$: files = parseJSONString(decode(attributes?.files ?? ''));
	$: embeds = parseJSONString(decode(attributes?.embeds ?? ''));
	$: isDone = attributes?.done === 'true';
	$: isExecuting = attributes?.done && attributes?.done !== 'true';

	$: parsedArgs = parseArguments(args);
	$: parsedResult = parseJSONString(result);
	$: presentation = getToolPresentation({
		toolName: attributes?.name ?? 'tool',
		args: parsedArgs ?? undefined,
		result: parsedResult,
		translate: $i18n.t.bind($i18n)
	});
	$: headerLabel = isDone ? presentation.doneLabel : presentation.pendingLabel;
</script>

<div {id} class="{className} overflow-hidden">
	{#if !grouped && embeds && Array.isArray(embeds) && embeds.length > 0}
		<!-- Embed Mode: Show iframes without collapsible behavior -->
		<div class="py-1 w-full cursor-pointer">
			<div class="w-full text-xs text-gray-500 dark:text-gray-400">
				{presentation.doneLabel}
			</div>
			{#each embeds as embed, idx}
				<div class="my-2" id={`${componentId}-tool-call-embed-${idx}`}>
					<FullHeightIframe
						src={embed}
						{args}
						allowScripts={true}
						allowForms={$settings?.iframeSandboxAllowForms ?? false}
						allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
						allowPopups={true}
					/>
				</div>
			{/each}
		</div>
	{:else}
		<!-- Tool call display -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="{buttonClassName} cursor-pointer overflow-hidden"
			on:pointerup={() => {
				open = !open;
			}}
		>
			<div
				class="w-full max-w-full font-medium flex items-center gap-1.5 {isExecuting
					? 'shimmer'
					: ''}"
			>
				<!-- Status icon -->
				{#if isExecuting}
					<div>
						<Spinner className="size-4" />
					</div>
				{:else if isDone}
					<div class="text-emerald-500 dark:text-emerald-400">
						<CheckCircle className="size-4" strokeWidth="2" />
					</div>
				{:else}
					<div class="text-gray-400 dark:text-gray-500">
						<svelte:component this={presentation.icon} className="size-4" />
					</div>
				{/if}

				<!-- Label + inline source capsule / chips -->
				<div class="flex-1 min-w-0 flex items-center gap-1.5">
					<span class="font-normal text-sm text-black dark:text-white truncate min-w-0">
						{headerLabel}
					</span>

					{#if presentation.sourceGroup && presentation.sourceGroup.totalCount > 0}
						<!-- Grouped source capsule (stacked favicons) -->
						<button
							class="inline-flex items-center gap-1.5 rounded-full border border-gray-100 bg-gray-50 pl-1 pr-2 py-0.5 text-[11px] font-normal text-gray-600 transition hover:bg-gray-100 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-850"
							on:click|stopPropagation={scrollToSources}
							on:pointerup|stopPropagation={() => {}}
						>
							<div class="flex -space-x-1 items-center">
								{#each presentation.sourceGroup.favicons.slice(0, 3) as fav}
									<img
										src={fav.faviconUrl}
										alt={`${fav.hostname} favicon`}
										class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-white dark:bg-gray-900"
										on:error={handleFaviconError}
									/>
								{/each}
								{#if presentation.sourceGroup.totalCount > 3}
									<div
										class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-[8px] font-semibold text-gray-500 dark:text-gray-400"
									>
										+{presentation.sourceGroup.totalCount - 3}
									</div>
								{/if}
							</div>
						</button>
					{/if}

					{#each presentation.chips as chip}
						{#if chip.url}
							<a
								href={chip.url}
								target="_blank"
								rel="noopener noreferrer"
								class="max-w-[160px] inline-flex items-center gap-1 rounded-full border border-gray-100 bg-gray-50 px-1.5 py-0.5 text-[11px] font-normal text-gray-600 no-underline transition hover:bg-gray-100 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-850"
								on:click|stopPropagation={() => {}}
								on:pointerup|stopPropagation={() => {}}
							>
								<img
									src={chip.faviconUrl}
									alt={`${chip.label} favicon`}
									class="size-3 shrink-0 rounded-sm"
									on:error={handleFaviconError}
								/>
								<span class="truncate">{chip.label}</span>
							</a>
						{:else}
							<div
								class="max-w-[160px] inline-flex items-center rounded-full border border-gray-100 bg-gray-50 px-1.5 py-0.5 text-[11px] font-normal text-gray-600 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300"
							>
								<span class="truncate">{chip.label}</span>
							</div>
						{/if}
					{/each}
				</div>

				<!-- Chevron -->
				<div class="flex shrink-0 self-center text-gray-400 dark:text-gray-500">
					{#if open}
						<ChevronUp strokeWidth="3.5" className="size-3" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3" />
					{/if}
				</div>
			</div>
		</div>

		{#if open}
			<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
				<div class="border border-gray-50 dark:border-gray-850/30 rounded-2xl my-1.5 p-3 space-y-3">
					<div>
						<div
							class="text-[10px] uppercase tracking-wider font-medium text-gray-400 dark:text-gray-500 mb-1.5 px-1"
						>
							{$i18n.t('Tool')}
						</div>
						<div class="px-1">
							<code
								class="text-[11px] text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 rounded-md px-1.5 py-0.5"
								>{presentation.debugName}</code
							>
						</div>
					</div>

					<!-- Input -->
					{#if args}
						<div>
							<div
								class="text-[10px] uppercase tracking-wider font-medium text-gray-400 dark:text-gray-500 mb-1.5 px-1"
							>
								{$i18n.t('Input')}
							</div>

							{#if parsedArgs}
								<div class="px-1 space-y-0.5">
									{#each Object.entries(parsedArgs) as [key, value]}
										<div class="flex gap-2 text-xs py-0.5">
											<span class="font-medium text-gray-600 dark:text-gray-400 shrink-0"
												>{key}</span
											>
											<span class="text-gray-800 dark:text-gray-200 break-all"
												>{typeof value === 'object' ? JSON.stringify(value) : value}</span
											>
										</div>
									{/each}
								</div>
							{:else}
								<div class="tool-call-body w-full max-w-none!">
									<Markdown
										id={`${componentId}-tool-call-args`}
										content={`\`\`\`json\n${formatJSONString(args)}\n\`\`\``}
									/>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Output -->
					{#if isDone && result}
						<div>
							<div
								class="text-[10px] uppercase tracking-wider font-medium text-gray-400 dark:text-gray-500 mb-1.5 px-1"
							>
								{$i18n.t('Output')}
							</div>
							<div class="w-full max-w-none!">
								{#if typeof parsedResult === 'object' && parsedResult !== null}
									<Markdown
										id={`${componentId}-tool-call-result`}
										content={`\`\`\`json\n${JSON.stringify(parsedResult, null, 2)}\n\`\`\``}
									/>
								{:else}
									{@const resultStr = String(parsedResult)}
									{@const isTruncated = resultStr.length > RESULT_PREVIEW_LIMIT && !expandedResult}
									<pre
										class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap break-words font-mono">{isTruncated
											? resultStr.slice(0, RESULT_PREVIEW_LIMIT)
											: resultStr}</pre>
									{#if isTruncated}
										<button
											class="mt-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
											on:click|stopPropagation={() => {
												expandedResult = true;
											}}
										>
											{$i18n.t('Show all ({{COUNT}} characters)', {
												COUNT: resultStr.length.toLocaleString()
											})}
										</button>
									{/if}
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}

	<!-- Files display (images etc.) when done -->
	{#if isDone}
		{#if typeof files === 'object'}
			{#each files ?? [] as file, idx}
				{#if typeof file === 'string'}
					{#if file.startsWith('data:image/')}
						<Image id={`${componentId}-tool-call-result-${idx}`} src={file} alt="Image" />
					{/if}
				{:else if typeof file === 'object'}
					{#if (file.type === 'image' || (file?.content_type ?? '').startsWith('image/')) && file.url}
						<Image id={`${componentId}-tool-call-result-${idx}`} src={file.url} alt="Image" />
					{/if}
				{/if}
			{/each}
		{/if}
	{/if}
</div>
