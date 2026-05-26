<script lang="ts" context="module">
	let toolCallResultModulePromise: Promise<any> | null = null;
	const loadToolCallResultModule = () =>
		(toolCallResultModulePromise ??= import('../chat/Messages/ToolCallResult.svelte'));
</script>

<script lang="ts">
	import { decode } from 'html-entities';
	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	const i18n = getContext<Writable<i18nType>>('i18n');

	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	async function loadLocale(locales) {
		if (!locales || !Array.isArray(locales)) {
			return;
		}
		for (const locale of locales) {
			try {
				dayjs.locale(locale);
				break; // Stop after successfully loading the first available locale
			} catch (error) {
				console.error(`Could not load locale '${locale}':`, error);
			}
		}
	}

	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Spinner from './Spinner.svelte';
	import CodeBlock from '../chat/Messages/CodeBlock.svelte';
	import Markdown from '../chat/Messages/Markdown.svelte';
	import SubagentBlock from '../chat/Messages/Markdown/SubagentBlock.svelte';
	import Image from './Image.svelte';
	import FullHeightIframe from './FullHeightIframe.svelte';
	import { settings } from '$lib/stores';
	import { getToolCallSummary, isWebToolName } from '$lib/utils/toolResults';

	export let open = false;

	export let className = '';
	export let buttonClassName =
		'w-fit text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition';

	export let id = '';
	export let title = null;
	export let attributes: Record<string, any> | null = null;

	export let chevron = false;
	export let grow = false;

	export let disabled = false;
	export let hide = false;

	export let onChange: Function = () => {};

	$: onChange(open);

	// Auto-expand reasoning blocks during streaming when setting is enabled
	$: if (attributes?.type === 'reasoning' && $settings?.autoExpandReasoningDuringStreaming) {
		// Expand while streaming, collapse when done
		open = attributes?.done !== 'true';
	}

	const collapsibleId = uuidv4();
	const loadToolCallResult = loadToolCallResultModule;

	function preloadToolCallResult() {
		if (isWebToolName(attributes?.name)) {
			void loadToolCallResult();
		}
	}

	onMount(() => {
		if (!isWebToolName(attributes?.name)) return;

		const idleWindow = window as any;
		if (typeof idleWindow.requestIdleCallback === 'function') {
			const idleId = idleWindow.requestIdleCallback(preloadToolCallResult, { timeout: 2000 });
			return () => idleWindow.cancelIdleCallback?.(idleId);
		}

		const timeout = window.setTimeout(preloadToolCallResult, 1200);
		return () => window.clearTimeout(timeout);
	});

	function parseJSONString(str) {
		try {
			return parseJSONString(JSON.parse(str));
		} catch (e) {
			return str;
		}
	}

	function formatJSONString(str) {
		try {
			const parsed = parseJSONString(str);
			// If parsed is an object/array, then it's valid JSON
			if (typeof parsed === 'object') {
				return JSON.stringify(parsed, null, 2);
			} else {
				// It's a primitive value like a number, boolean, etc.
				return `${JSON.stringify(String(parsed))}`;
			}
		} catch (e) {
			// Not valid JSON, return as-is
			return str;
		}
	}
</script>

<div {id} class={className}>
	{#if attributes?.type === 'subagent_launch'}
		<!-- Subagent block: rendered as a self-contained card with its own
			collapsible chrome (own header/spinner/caret + recursive markdown
			body for the inner content_blocks). Bypasses the generic
			tool_calls / reasoning branches below — the SubagentBlock component
			reads its state live from `$subagentLiveStates` keyed on the
			tool_call_id attribute that `serialize_content_blocks` stamps. -->
		<SubagentBlock attributes={attributes ?? {}} />
	{:else if attributes?.type === 'tool_calls'}
		{@const args = decode(attributes?.arguments)}
		{@const rawResult = attributes?.result ?? ''}
		{@const rawFiles = attributes?.files ?? ''}
		{@const embeds = parseJSONString(decode(attributes?.embeds ?? ''))}
		{@const toolDone = attributes?.done === 'true'}
		{@const toolSummary = getToolCallSummary(attributes?.name ?? '', args, rawResult, toolDone)}

		{#if embeds && Array.isArray(embeds) && embeds.length > 0}
			<div class="py-1 w-full cursor-pointer">
				<div class=" w-full text-xs text-gray-500">
					<div class="">
						{attributes.name}
					</div>
				</div>

				{#each embeds as embed, idx}
					<div class="my-2" id={`${collapsibleId}-tool-calls-${attributes?.id}-embed-${idx}`}>
						<FullHeightIframe
							src={embed}
							{args}
							allowScripts={true}
							allowForms={true}
							allowSameOrigin={true}
							allowPopups={true}
						/>
					</div>
				{/each}
			</div>
		{:else}
			<div
				class="{buttonClassName} cursor-pointer"
				on:pointerenter={preloadToolCallResult}
				on:pointerdown={preloadToolCallResult}
				on:pointerup={() => {
					if (!disabled) {
						open = !open;
					}
				}}
			>
				<div
					class=" w-full font-medium flex items-center justify-between gap-2 {attributes?.done &&
					attributes?.done !== 'true'
						? 'shimmer'
						: ''}
			"
				>
					{#if attributes?.done && attributes?.done !== 'true'}
						<div>
							<Spinner className="size-4" />
						</div>
					{/if}

					<div class="min-w-0">
						{#if isWebToolName(attributes?.name)}
							<div class="min-w-0 text-left">
								<div class="flex min-w-0 items-center gap-1.5">
									<span class="truncate text-gray-700 dark:text-gray-300">{toolSummary.title}</span>
								</div>
								{#if toolSummary.subtitle}
									<div class="mt-0.5 truncate text-xs font-normal text-gray-500 dark:text-gray-500">
										{toolSummary.subtitle}
									</div>
								{/if}
							</div>
						{:else if attributes?.done === 'true'}
							<Markdown
								id={`${collapsibleId}-tool-calls-${attributes?.id}`}
								content={$i18n.t('View Result from **{{NAME}}**', {
									NAME: attributes.name
								})}
							/>
						{:else}
							<Markdown
								id={`${collapsibleId}-tool-calls-${attributes?.id}-executing`}
								content={$i18n.t('Executing **{{NAME}}**...', {
									NAME: attributes.name
								})}
							/>
						{/if}
					</div>

					<div class="flex self-center translate-y-[1px]">
						{#if open}
							<ChevronUp strokeWidth="3.5" className="size-3.5" />
						{:else}
							<ChevronDown strokeWidth="3.5" className="size-3.5" />
						{/if}
					</div>
				</div>
			</div>

			{#if !grow}
				{#if open && !hide}
					<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
						{#if attributes?.type === 'tool_calls'}
							{#if isWebToolName(attributes?.name)}
								{#await loadToolCallResult()}
									<div
										class="my-2 overflow-hidden rounded-2xl border border-gray-100 bg-gray-50/70 text-sm dark:border-gray-800 dark:bg-gray-950/40"
									>
										<div
											class="flex items-center gap-2 border-b border-gray-100 bg-white px-2.5 py-2 dark:border-gray-800 dark:bg-gray-900"
										>
											<div class="h-6 w-36 rounded-lg bg-gray-100 dark:bg-gray-800"></div>
											<div class="h-6 w-20 rounded-lg bg-gray-100 dark:bg-gray-800"></div>
										</div>
										<div class="space-y-2 p-3">
											<div class="h-4 w-1/3 rounded bg-gray-100 dark:bg-gray-800"></div>
											<div class="h-16 rounded-xl bg-gray-100 dark:bg-gray-800"></div>
										</div>
									</div>
								{:then ToolCallResult}
									<svelte:component
										this={ToolCallResult.default}
										id={`${collapsibleId}-tool-calls-${attributes?.id}-result`}
										name={attributes.name}
										argsRaw={args}
										resultRaw={rawResult}
										done={toolDone}
									/>
								{/await}
							{:else if attributes?.done === 'true'}
								{@const result = decode(rawResult)}
								<Markdown
									id={`${collapsibleId}-tool-calls-${attributes?.id}-result`}
									content={`> \`\`\`json
> ${formatJSONString(args)}
> ${formatJSONString(result)}
> \`\`\``}
								/>
							{:else}
								<Markdown
									id={`${collapsibleId}-tool-calls-${attributes?.id}-result`}
									content={`> \`\`\`json
> ${formatJSONString(args)}
> \`\`\``}
								/>
							{/if}
						{:else}
							<slot name="content" />
						{/if}
					</div>
				{/if}
			{/if}
		{/if}

		{#if attributes?.done === 'true'}
			{@const files = parseJSONString(decode(rawFiles))}
			{#if typeof files === 'object'}
				{#each files ?? [] as file, idx}
					{#if typeof file === 'string'}
						{#if file.startsWith('data:image/')}
							<Image
								id={`${collapsibleId}-tool-calls-${attributes?.id}-result-${idx}`}
								src={file}
								alt="Image"
							/>
						{/if}
					{:else if typeof file === 'object'}
						{#if file.type === 'image' && file.url}
							<Image
								id={`${collapsibleId}-tool-calls-${attributes?.id}-result-${idx}`}
								src={file.url}
								alt="Image"
							/>
						{/if}
					{/if}
				{/each}
			{/if}
		{/if}
	{:else}
		{#if title !== null}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div
				class="{buttonClassName} cursor-pointer"
				on:pointerup={() => {
					if (!disabled) {
						open = !open;
					}
				}}
			>
				<div
					class=" w-full font-medium flex items-center justify-between gap-2 {attributes?.done &&
					attributes?.done !== 'true'
						? 'shimmer'
						: ''}
			"
				>
					{#if attributes?.done && attributes?.done !== 'true'}
						<div>
							<Spinner className="size-4" />
						</div>
					{/if}

					<div class="">
						{#if attributes?.type === 'reasoning'}
							{#if attributes?.done === 'true' && attributes?.duration}
								{#if attributes.duration < 1}
									{$i18n.t('Thought for less than a second')}
								{:else if attributes.duration < 60}
									{$i18n.t('Thought for {{DURATION}} seconds', {
										DURATION: attributes.duration
									})}
								{:else}
									{$i18n.t('Thought for {{DURATION}}', {
										DURATION: dayjs.duration(attributes.duration, 'seconds').humanize()
									})}
								{/if}
							{:else}
								{$i18n.t('Thinking...')}
							{/if}
						{:else if attributes?.type === 'code_interpreter'}
							{#if attributes?.done === 'true'}
								{$i18n.t('Analyzed')}
							{:else}
								{$i18n.t('Analyzing...')}
							{/if}
						{:else}
							{title}
						{/if}
					</div>

					<div class="flex self-center translate-y-[1px]">
						{#if open}
							<ChevronUp strokeWidth="3.5" className="size-3.5" />
						{:else}
							<ChevronDown strokeWidth="3.5" className="size-3.5" />
						{/if}
					</div>
				</div>
			</div>
		{:else}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div
				class="{buttonClassName} cursor-pointer"
				on:click={(e) => {
					e.stopPropagation();
				}}
				on:pointerup={(e) => {
					if (!disabled) {
						open = !open;
					}
				}}
			>
				<div>
					<div class="flex items-start justify-between">
						<slot />

						{#if chevron}
							<div class="flex self-start translate-y-1">
								{#if open}
									<ChevronUp strokeWidth="3.5" className="size-3.5" />
								{:else}
									<ChevronDown strokeWidth="3.5" className="size-3.5" />
								{/if}
							</div>
						{/if}
					</div>

					{#if grow}
						{#if open && !hide}
							<div
								transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}
								on:pointerup={(e) => {
									e.stopPropagation();
								}}
							>
								<slot name="content" />
							</div>
						{/if}
					{/if}
				</div>
			</div>
		{/if}

		{#if !grow}
			{#if open && !hide}
				<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
					<slot name="content" />
				</div>
			{/if}
		{/if}
	{/if}
</div>
