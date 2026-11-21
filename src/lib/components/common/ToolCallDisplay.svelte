<script lang="ts">
	import { decode } from 'html-entities';
	import { v4 as uuidv4 } from 'uuid';

	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	const i18n = getContext<Writable<i18nType>>('i18n');

	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Spinner from './Spinner.svelte';
	import WrenchSolid from '../icons/WrenchSolid.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import XMark from '../icons/XMark.svelte';
	import Image from './Image.svelte';
	import FullHeightIframe from './FullHeightIframe.svelte';
	import MCPApp from '$lib/components/chat/Messages/MCPApp.svelte';
	import DiffBlock from '$lib/components/chat/Messages/DiffBlock.svelte';
	import {
		agentViewName,
		agentViewOutput,
		diffStats,
		type AgentView
	} from '$lib/components/chat/Messages/agentViews';
	import { toolCallLabel } from '$lib/components/chat/Messages/builtinToolLabels';
	import { settings } from '$lib/stores';

	export let id: string = '';
	export let attributes: {
		type?: string;
		id?: string;
		name?: string;
		tool_id?: string;
		display_label?: string;
		running_label?: string;
		arguments?: string;
		result?: string;
		files?: string;
		embeds?: string;
		done?: string;
		status?: string;
	} = {};

	// Commands and file edits from terminal agents, drawn as a terminal block or a diff.
	export let view: AgentView | null = null;
	export let open = false;
	export let grouped = false;
	export let allowEmbeds = false;
	export let className = '';
	export let resolvable = false;
	export let resolving = false;
	export let onResolve: (approved: boolean) => void = () => {};

	const RESULT_PREVIEW_LIMIT = 10000;
	let expandedResult = false;

	$: if (!open) expandedResult = false;
	export let buttonClassName =
		'py-1 text-[0.9375rem] text-base-500 hover:text-base-700 dark:hover:text-base-300 transition';

	const componentId = id || uuidv4();

	function parseJSONString(str: string) {
		// Iteratively unwrap nested JSON-encoded strings. Same result as the previous
		// recursive form, but without the stack-overflow-and-recover path it hit on
		// scalar values (e.g. JSON.parse('5') -> 5 -> infinite self-recursion).
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		let value: any = str;
		while (typeof value === 'string') {
			try {
				value = JSON.parse(value);
			} catch {
				break;
			}
		}
		return value;
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

	function isToolResultError(value: unknown): boolean {
		if (typeof value === 'string') {
			const text = value.trim().toLowerCase();
			if (
				text.startsWith('error:') ||
				text.startsWith('exception:') ||
				text.startsWith('traceback') ||
				text.startsWith('http error!')
			) {
				return true;
			}
		}

		let parsed = value;
		while (typeof parsed === 'string') {
			try {
				parsed = JSON.parse(parsed);
			} catch {
				break;
			}
		}
		if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return false;

		const result = parsed as Record<string, unknown>;
		const error = result.error;
		if (
			(typeof error === 'string' && error.trim().length > 0) ||
			(typeof error === 'object' && error !== null)
		) {
			return true;
		}

		const status = typeof result.status === 'string' ? result.status.trim().toLowerCase() : '';
		if (status === 'error' || status === 'failed') return true;

		const message = result.message;
		return (
			(result.success === false || result.ok === false) &&
			((typeof message === 'string' && message.trim().length > 0) ||
				(typeof message === 'object' && message !== null))
		);
	}

	export let resultContent: string = '';

	$: result = resultContent || decode(attributes?.result ?? '');
	$: files = parseJSONString(decode(attributes?.files ?? ''));
	$: embeds = parseJSONString(decode(attributes?.embeds ?? ''));
	$: isAskUser = attributes?.name === 'ask_user';
	$: needsInput = isAskUser && attributes?.status === 'pending';
	$: needsApproval = !isAskUser && attributes?.status === 'pending' && resolvable;
	$: args =
		open || needsApproval || needsInput || (Array.isArray(embeds) && embeds.length > 0)
			? decode(attributes?.arguments ?? '')
			: '';
	$: isRejected = attributes?.status === 'rejected';
	$: isDone =
		attributes?.done === 'true' ||
		attributes?.status === 'failed' ||
		attributes?.status === 'incomplete';
	$: isExecuting = !isDone && !isRejected && attributes?.status === 'completed';
	$: isPreparing = !isDone && !isRejected && !needsApproval && !needsInput && !isExecuting;
	$: isActive = isPreparing || isExecuting;
	$: isError = attributes?.status === 'failed' || (isDone && isToolResultError(result));
	$: toolName = view ? agentViewName(view) : attributes.name;
	// Literal keys so the i18n parser picks them up.
	const viewText = (kind: AgentView['kind'], done: boolean, NAME: string) => {
		switch (kind) {
			case 'command':
				return done ? $i18n.t('Ran {{NAME}}', { NAME }) : $i18n.t('Running {{NAME}}', { NAME });
			case 'edit':
				return done ? $i18n.t('Edited {{NAME}}', { NAME }) : $i18n.t('Editing {{NAME}}', { NAME });
			case 'read':
				return done ? $i18n.t('Read {{NAME}}', { NAME }) : $i18n.t('Reading {{NAME}}', { NAME });
			case 'search':
				return done
					? $i18n.t('Searched for {{NAME}}', { NAME })
					: $i18n.t('Searching for {{NAME}}', { NAME });
			case 'list':
				return done ? $i18n.t('Listed {{NAME}}', { NAME }) : $i18n.t('Listing {{NAME}}', { NAME });
			case 'web':
				return done
					? $i18n.t('Searched the web for {{NAME}}', { NAME })
					: $i18n.t('Searching the web for {{NAME}}', { NAME });
			case 'fetch':
				return done
					? $i18n.t('Fetched {{NAME}}', { NAME })
					: $i18n.t('Fetching {{NAME}}', { NAME });
		}
	};
	$: viewLabel =
		view &&
		toolName &&
		!needsApproval &&
		!isRejected &&
		!['pending', 'queued'].includes(attributes.status ?? '')
			? viewText(view.kind, isDone, toolName)
			: '';
	$: displayLabel =
		viewLabel ||
		(!needsInput &&
		!isRejected &&
		!['pending', 'queued', 'requires_approval', 'incomplete'].includes(attributes.status ?? '')
			? toolCallLabel(attributes, isDone, isError, $i18n.t)
			: '');
	$: viewOutput = view ? agentViewOutput(view) : '';
	$: editStats =
		view?.kind === 'edit'
			? view.files
					.map((file) => diffStats(file.diff))
					.reduce(
						(total, stats) => ({
							additions: total.additions + stats.additions,
							deletions: total.deletions + stats.deletions
						}),
						{ additions: 0, deletions: 0 }
					)
			: null;

	$: parsedArgs = parseArguments(args);
	$: parsedResult = parseJSONString(result);

	const toggleOpen = () => {
		open = !open;
	};

	const toggleOpenOnKeydown = (event: KeyboardEvent) => {
		if (event.target !== event.currentTarget) return;
		if (event.key !== 'Enter' && event.key !== ' ') {
			return;
		}

		event.preventDefault();
		toggleOpen();
	};
</script>

<div {id} class={className}>
	{#if allowEmbeds && !grouped && embeds && Array.isArray(embeds) && embeds.length > 0}
		<!-- Embed Mode: Show iframes without collapsible behavior -->
		<div class="py-1 w-full cursor-pointer">
			<div class="w-full text-xs text-base-500">
				{attributes.name}
			</div>
			{#each embeds as embed, idx}
				<div class="my-2" id={`${componentId}-tool-call-embed-${idx}`}>
					{#if typeof embed === 'object' && embed?.type === 'mcp_app'}
						{#key JSON.stringify(embed)}<MCPApp app={embed} />{/key}
					{:else if typeof embed === 'string'}
						<FullHeightIframe
							src={embed}
							{args}
							allowScripts={true}
							allowForms={$settings?.iframeSandboxAllowForms ?? false}
							allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
							allowPopups={true}
						/>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<!-- Tool call display -->
		<div
			class="{buttonClassName} w-full min-w-0 cursor-pointer"
			role="button"
			tabindex="0"
			aria-expanded={open}
			on:click={toggleOpen}
			on:keydown={toggleOpenOnKeydown}
		>
			<div
				class="w-full min-w-0 max-w-full font-normal flex items-center gap-1.5 {isActive
					? 'shimmer'
					: ''}"
			>
				<!-- Status icon -->
				{#if isActive}
					<div>
						<Spinner className="size-4" />
					</div>
				{:else if isRejected}
					<div class="text-red-400 dark:text-red-500">
						<XMark className="size-4" strokeWidth="2.5" />
					</div>
				{:else if isError}
					<div class="text-red-500 dark:text-red-400">
						<XMark className="size-4" strokeWidth="2.5" />
					</div>
				{:else if isDone}
					<div class="text-emerald-500 dark:text-emerald-400">
						<CheckCircle className="size-4" strokeWidth="2" />
					</div>
				{:else}
					<div class="text-base-400 dark:text-base-500">
						<WrenchSolid className="size-3.5" />
					</div>
				{/if}

				<!-- Label, with an edit's line counts right after it -->
				<div class="flex-1 min-w-0 flex items-baseline gap-1.5">
					<div class="min-w-0 line-clamp-1">
						<!-- Short label (below md) -->
						<span
							class="@md:hidden text-base-1000 dark:text-base-0"
							title={displayLabel ? attributes.name : undefined}>{displayLabel || toolName}</span
						>
						<!-- Full label (md and above) -->
						<span
							class="hidden @md:inline font-normal"
							title={displayLabel ? attributes.name : undefined}
						>
							{#if isRejected}
								{$i18n.t('Denied {{NAME}}', { NAME: toolName })}
							{:else if displayLabel}
								{displayLabel}
							{:else if isDone}
								{$i18n.t('View Result from {{NAME}}', { NAME: toolName })}
							{:else if needsInput}
								{$i18n.t('Input needed')}
							{:else if needsApproval}
								{$i18n.t('Allow {{NAME}}?', { NAME: toolName })}
							{:else if isPreparing}
								{$i18n.t('Preparing {{NAME}}...', { NAME: toolName })}
							{:else}
								{$i18n.t('Executing {{NAME}}...', { NAME: toolName })}
							{/if}
						</span>
					</div>
					{#if editStats && !isRejected && (editStats.additions || editStats.deletions)}
						<span class="shrink-0 flex gap-1 text-xs font-mono tabular-nums">
							{#if editStats.additions}<span class="text-green-600 dark:text-green-400"
									>+{editStats.additions}</span
								>{/if}
							{#if editStats.deletions}<span class="text-red-500 dark:text-red-400"
									>−{editStats.deletions}</span
								>{/if}
						</span>
					{/if}
				</div>

				{#if needsApproval && !isAskUser}
					<span class="flex gap-1 shrink-0">
						<button
							type="button"
							class="tool-call-allow-button text-[0.6875rem] px-2.5 py-0.5 rounded-md text-base-600 dark:text-base-300 bg-base-100 dark:bg-base-0/8 hover:bg-base-200 dark:hover:bg-base-0/12 transition-colors duration-100 disabled:opacity-50"
							disabled={resolving}
							on:click|stopPropagation={() => onResolve(true)}
						>
							{$i18n.t('Allow')}
						</button>
						<button
							type="button"
							class="tool-call-deny-button text-[0.6875rem] px-2 py-0.5 rounded-md text-base-400 dark:text-base-500 hover:text-base-600 dark:hover:text-base-300 transition-colors duration-100 disabled:opacity-50"
							disabled={resolving}
							on:click|stopPropagation={() => onResolve(false)}
						>
							{$i18n.t('Deny')}
						</button>
					</span>
				{:else}
					<!-- Chevron -->
					<div class="flex shrink-0 self-center translate-y-[1px]">
						{#if open}
							<ChevronUp strokeWidth="3.5" className="size-3" />
						{:else}
							<ChevronDown strokeWidth="3.5" className="size-3" />
						{/if}
					</div>
				{/if}
			</div>
		</div>

		{#if open}
			<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
				<div
					class="border border-base-50 dark:border-base-850/30 rounded-2xl my-1.5 p-2.5 space-y-2"
				>
					{#if view && view.kind !== 'edit'}
						{@const isTruncated = viewOutput.length > RESULT_PREVIEW_LIMIT && !expandedResult}
						{#if view.kind === 'command' || viewOutput}
							<pre
								class="text-xs text-base-600 dark:text-base-300 whitespace-pre-wrap break-words font-mono max-h-80 overflow-y-auto">{#if view.kind === 'command'}<span
										class="text-base-400 dark:text-base-500 select-none"
										>$ </span><span class="text-base-900 dark:text-base-100">{view.command}</span
									>{viewOutput ? '\n' : ''}{/if}{isTruncated
									? viewOutput.slice(0, RESULT_PREVIEW_LIMIT)
									: viewOutput}</pre>
						{/if}
						{#if isTruncated}
							<button
								class="text-xs text-base-500 hover:text-base-700 dark:hover:text-base-300 transition"
								on:click|stopPropagation={() => {
									expandedResult = true;
								}}
							>
								{$i18n.t('Show all ({{COUNT}} characters)', {
									COUNT: viewOutput.length.toLocaleString()
								})}
							</button>
						{/if}
						{#if view.kind === 'command' && view.exitCode != null && view.exitCode !== 0}
							<div class="text-xs text-red-500 dark:text-red-400">
								{$i18n.t('Exit code {{CODE}}', { CODE: view.exitCode })}
							</div>
						{/if}
					{:else if view?.kind === 'edit'}
						{#each view.files as file, idx (`${file.path}-${idx}`)}
							{@const stats = diffStats(file.diff)}
							<div>
								<div class="flex items-baseline gap-1.5 text-xs mb-1 px-1 min-w-0">
									<span class="font-mono text-base-500 dark:text-base-400 truncate"
										>{file.path}</span
									>
									{#if stats.additions}<span class="shrink-0 text-green-600 dark:text-green-400"
											>+{stats.additions}</span
										>{/if}
									{#if stats.deletions}<span class="shrink-0 text-red-500 dark:text-red-400"
											>−{stats.deletions}</span
										>{/if}
								</div>
								{#if file.diff}
									<div class="max-h-80 overflow-y-auto">
										<DiffBlock code={file.diff} compact />
									</div>
								{/if}
							</div>
						{/each}
						{#if isError && result}
							<pre
								class="text-xs text-red-500 dark:text-red-400 whitespace-pre-wrap break-words font-mono">{result}</pre>
						{/if}
					{:else if args}
						<!-- Input -->
						<div>
							<div
								class="text-[0.625rem] uppercase tracking-wider font-normal text-base-400 dark:text-base-500 mb-1.5 px-1"
							>
								{$i18n.t('Input')}
							</div>

							{#if parsedArgs}
								<div class="px-1 space-y-0.5">
									{#each Object.entries(parsedArgs) as [key, value]}
										<div class="flex gap-2 text-xs py-0.5">
											<span class="font-normal text-base-600 dark:text-base-400 shrink-0"
												>{key}</span
											>
											<span class="text-base-800 dark:text-base-200 break-all"
												>{typeof value === 'object' ? JSON.stringify(value) : value}</span
											>
										</div>
									{/each}
								</div>
							{:else}
								<div class="tool-call-body w-full max-w-none!">
									<pre
										class="text-xs text-base-600 dark:text-base-300 whitespace-pre font-mono bg-base-50 dark:bg-base-900 rounded-lg p-2 overflow-x-auto">{formatJSONString(
											args
										)}</pre>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Output -->
					{#if !view && isDone && result}
						<div>
							<div
								class="text-[0.625rem] uppercase tracking-wider font-normal text-base-400 dark:text-base-500 mb-1.5 px-1"
							>
								{$i18n.t('Output')}
							</div>
							<div class="w-full max-w-none!">
								{#if typeof parsedResult === 'object' && parsedResult !== null}
									<pre
										class="text-xs text-base-600 dark:text-base-300 whitespace-pre font-mono bg-base-50 dark:bg-base-900 rounded-lg p-2 overflow-x-auto">{JSON.stringify(
											parsedResult,
											null,
											2
										)}</pre>
								{:else}
									{@const resultStr = String(parsedResult)}
									{@const isTruncated = resultStr.length > RESULT_PREVIEW_LIMIT && !expandedResult}
									<pre
										class="text-xs text-base-600 dark:text-base-300 whitespace-pre-wrap break-words font-mono">{isTruncated
											? resultStr.slice(0, RESULT_PREVIEW_LIMIT)
											: resultStr}</pre>
									{#if isTruncated}
										<button
											class="mt-1 text-xs text-base-500 hover:text-base-700 dark:hover:text-base-300 transition"
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
