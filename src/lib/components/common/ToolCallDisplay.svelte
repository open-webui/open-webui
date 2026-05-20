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
	import WrenchSolid from '../icons/WrenchSolid.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import Image from './Image.svelte';
	import FullHeightIframe from './FullHeightIframe.svelte';
	import { settings } from '$lib/stores';

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
	const TOOL_NAME_PLACEHOLDER = '__OPEN_WEBUI_TOOL_NAME__';
	let expandedResult = false;

	$: if (!open) expandedResult = false;
	export let buttonClassName =
		'w-fit text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition';

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

	function getToolLabelParts(label: string) {
		const normalized = label.replaceAll(`**${TOOL_NAME_PLACEHOLDER}**`, TOOL_NAME_PLACEHOLDER);
		const placeholderIndex = normalized.indexOf(TOOL_NAME_PLACEHOLDER);

		if (placeholderIndex === -1) {
			return { before: `${normalized} `, after: '' };
		}

		return {
			before: normalized.slice(0, placeholderIndex),
			after: normalized.slice(placeholderIndex + TOOL_NAME_PLACEHOLDER.length)
		};
	}

	export let resultContent: string = '';

	$: isDone = attributes?.done === 'true';
	$: isExecuting = attributes?.done && attributes?.done !== 'true';

	let args = '';
	let parsedArgs: Record<string, unknown> | null = null;
	let files: any = null;
	let embeds: any = null;
	let result = '';
	let parsedResult: unknown = '';

	let lastArguments = '';
	let lastFiles = '';
	let lastEmbeds = '';
	let lastResultContent = '';
	let lastAttributeResult = '';

	const updateArgs = (nextArguments: string) => {
		if (nextArguments === lastArguments) return;

		lastArguments = nextArguments;
		args = decode(nextArguments);
		parsedArgs = parseArguments(args);
	};

	const updateFiles = (nextFiles: string) => {
		if (nextFiles === lastFiles) return;

		lastFiles = nextFiles;
		files = nextFiles ? parseJSONString(decode(nextFiles)) : null;
	};

	const updateEmbeds = (nextEmbeds: string) => {
		if (nextEmbeds === lastEmbeds) return;

		lastEmbeds = nextEmbeds;
		embeds = nextEmbeds ? parseJSONString(decode(nextEmbeds)) : null;
	};

	const updateResult = (nextResultContent: string, nextAttributeResult: string) => {
		if (nextResultContent === lastResultContent && nextAttributeResult === lastAttributeResult) {
			return;
		}

		lastResultContent = nextResultContent;
		lastAttributeResult = nextAttributeResult;

		result = nextResultContent ? decode(nextResultContent) : decode(nextAttributeResult);
		parsedResult = parseJSONString(result);
	};

	$: updateArgs(attributes?.arguments ?? '');
	$: updateFiles(isDone ? (attributes?.files ?? '') : '');
	$: updateEmbeds(!grouped ? (attributes?.embeds ?? '') : '');
	$: if (open && isDone) {
		updateResult(resultContent ?? '', attributes?.result ?? '');
	}
</script>

<div {id} class={className}>
	{#if !grouped && embeds && Array.isArray(embeds) && embeds.length > 0}
		<!-- Embed Mode: Show iframes without collapsible behavior -->
		<div class="py-1 w-full cursor-pointer">
			<div class="w-full text-xs text-gray-500">
				{attributes.name}
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
			class="{buttonClassName} cursor-pointer"
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
						<WrenchSolid className="size-3.5" />
					</div>
				{/if}

				<!-- Label -->
				<div class="flex-1 line-clamp-1">
					<!-- Short label (below md) -->
					<span class="@md:hidden text-black dark:text-white">{attributes.name}</span>
					<!-- Full label (md and above) -->
					<span class="hidden @md:inline font-normal">
						{#if isDone}
							{@const label = getToolLabelParts(
								$i18n.t('View Result from **{{NAME}}**', { NAME: TOOL_NAME_PLACEHOLDER })
							)}
							{label.before}<strong>{attributes.name}</strong>{label.after}
						{:else}
							{@const label = getToolLabelParts(
								$i18n.t('Executing **{{NAME}}**...', { NAME: TOOL_NAME_PLACEHOLDER })
							)}
							{label.before}<strong>{attributes.name}</strong>{label.after}
						{/if}
					</span>
				</div>

				<!-- Chevron -->
				<div class="flex shrink-0 self-center translate-y-[1px]">
					{#if open}
						<ChevronUp strokeWidth="3.5" className="size-3.5" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3.5" />
					{/if}
				</div>
			</div>
		</div>

		{#if open}
			<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
				<div class="border border-gray-50 dark:border-gray-850/30 rounded-2xl my-1.5 p-3 space-y-3">
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
									<pre
										class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre font-mono bg-gray-50 dark:bg-gray-900 rounded-lg p-2.5 overflow-x-auto">{formatJSONString(
											args
										)}</pre>
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
									<pre
										class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre font-mono bg-gray-50 dark:bg-gray-900 rounded-lg p-2.5 overflow-x-auto">{JSON.stringify(
											parsedResult,
											null,
											2
										)}</pre>
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
