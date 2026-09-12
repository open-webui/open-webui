<script lang="ts">
	import { decode } from 'html-entities';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';

	import { settings } from '$lib/stores';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let id = '';
	export let tokens: Array<{
		summary?: string;
		text?: string;
		attributes?: {
			type?: string;
			name?: string;
			done?: string;
			id?: string;
			status?: string;
			duration?: string;
			embeds?: string;
			arguments?: string;
		};
	}> = [];

	export let messageDone = true;
	export let allowEmbeds = true;
	export let compactPreview = false;
	export let resolvable = false;
	export let resolvingCallId = '';
	export let onResolve: (callId: string, approved: boolean) => void = () => {};

	let open = $settings?.expandDetails ?? false;

	function parseJSONString(str: string) {
		try {
			return parseJSONString(JSON.parse(str));
		} catch (e) {
			return str;
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

	$: toolCallCount = tokens.filter((t) => t?.attributes?.type === 'tool_calls').length;
	$: reasoningCount = tokens.filter((t) => t?.attributes?.type === 'reasoning').length;
	$: pendingToolTokens = tokens.filter(
		(t) => t?.attributes?.type === 'tool_calls' && t?.attributes?.status === 'pending'
	);
	$: hasActiveToolCalls = tokens.some(
		(t) =>
			t?.attributes?.type === 'tool_calls' &&
			t?.attributes?.status !== 'rejected' &&
			t?.attributes?.status !== 'failed' &&
			t?.attributes?.status !== 'incomplete' &&
			t?.attributes?.done !== 'true'
	);
	$: hasRejected = tokens.some(
		(t) => t?.attributes?.type === 'tool_calls' && t?.attributes?.status === 'rejected'
	);
	$: hasError = tokens.some(
		(t) =>
			t?.attributes?.type === 'tool_calls' &&
			(t?.attributes?.status === 'failed' ||
				(t?.attributes?.done === 'true' && isToolResultError(decode(t?.text ?? ''))))
	);

	$: codeInterpreterCount = tokens.filter((t) => t?.attributes?.type === 'code_interpreter').length;

	// Collect all embeds from tool_calls tokens
	$: allEmbeds = (() => {
		if (!allowEmbeds) return [];

		const result: Array<{ name: string; embed: string; args: string }> = [];
		for (const t of tokens) {
			if (t?.attributes?.type !== 'tool_calls') continue;
			const raw = decode(t.attributes?.embeds ?? '');
			try {
				const parsed = parseJSONString(raw);
				if (Array.isArray(parsed) && parsed.length > 0) {
					for (const embed of parsed) {
						result.push({
							name: t.attributes?.name ?? '',
							embed,
							args: decode(t.attributes?.arguments ?? '')
						});
					}
				}
			} catch {}
		}
		return result;
	})();

	$: summaryText = (() => {
		const parts = [];

		if (toolCallCount > 0) {
			// Group by tool name and show counts
			const nameCounts: Record<string, number> = {};
			tokens
				.filter((t) => t?.attributes?.type === 'tool_calls')
				.forEach((t) => {
					const name = t?.attributes?.name ?? 'tool';
					nameCounts[name] = (nameCounts[name] || 0) + 1;
				});

			const toolParts = Object.entries(nameCounts).map(([name, count]) =>
				count > 1 ? `${count} ${name}` : name
			);
			parts.push(...toolParts);
		}

		if (codeInterpreterCount > 0) {
			if (codeInterpreterCount === 1) {
				parts.push($i18n.t('Ran {{COUNT}} analysis', { COUNT: codeInterpreterCount }));
			} else {
				parts.push($i18n.t('Ran {{COUNT}} analyses', { COUNT: codeInterpreterCount }));
			}
		}

		const detail = parts.join(', ');
		return detail;
	})();

	$: prefixText = hasActiveToolCalls ? $i18n.t('Exploring') : $i18n.t('Explored');
</script>

<div {id} class="w-full min-w-0">
	<div class="flex w-full min-w-0 items-center gap-2">
		<div
			role="button"
			tabindex="0"
			class="flex-1 min-w-0 py-0.5 text-left {compactPreview
				? 'text-xs'
				: 'text-[0.9375rem]'} text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition cursor-pointer"
			aria-label={$i18n.t('Toggle details')}
			aria-expanded={open}
			on:click={() => {
				open = !open;
			}}
			on:keydown={(event) => {
				if (event.key === 'Enter' || event.key === ' ') {
					event.preventDefault();
					open = !open;
				}
			}}
		>
			<div class="flex items-center gap-1.5 min-w-0">
				<!-- Status icon -->
				{#if hasActiveToolCalls}
					<div>
						<Spinner className="size-4" />
					</div>
				{:else if hasRejected}
					<div class="text-red-400 dark:text-red-500">
						<XMark className="size-4" strokeWidth="2.5" />
					</div>
				{:else if toolCallCount > 0 && hasError}
					<div class="text-red-500 dark:text-red-400">
						<XMark className="size-4" strokeWidth="2.5" />
					</div>
				{:else if toolCallCount > 0}
					<div class="text-emerald-500 dark:text-emerald-400">
						<CheckCircle className="size-4" strokeWidth="2" />
					</div>
				{:else}
					<div class="text-gray-400 dark:text-gray-500">
						<Sparkles className="size-3.5" />
					</div>
				{/if}

				<!-- Summary text -->
				<div class="flex-1 line-clamp-1">
					<span class="text-gray-600 dark:text-gray-300 {hasActiveToolCalls ? 'shimmer' : ''}"
						>{prefixText}</span
					>
					{#if summaryText}
						<span class="text-gray-400 dark:text-gray-500">{summaryText}</span>
					{/if}
				</div>

				{#if resolvable && pendingToolTokens.length === 1 && pendingToolTokens[0]?.attributes?.name !== 'ask_user'}
					{@const pendingCallId = pendingToolTokens[0]?.attributes?.id ?? ''}
					<span class="flex gap-1 shrink-0">
						<button
							type="button"
							class="tool-call-allow-button text-[0.6875rem] px-2.5 py-0.5 rounded-md text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-white/8 hover:bg-gray-200 dark:hover:bg-white/12 transition-colors duration-100 disabled:opacity-50"
							disabled={!pendingCallId || resolvingCallId === pendingCallId}
							on:click|stopPropagation={() => onResolve(pendingCallId, true)}
						>
							{$i18n.t('Allow')}
						</button>
						<button
							type="button"
							class="tool-call-deny-button text-[0.6875rem] px-2 py-0.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 disabled:opacity-50"
							disabled={!pendingCallId || resolvingCallId === pendingCallId}
							on:click|stopPropagation={() => onResolve(pendingCallId, false)}
						>
							{$i18n.t('Deny')}
						</button>
					</span>
				{:else}
					<!-- Chevron -->
					<div class="flex shrink-0 self-center text-gray-400 dark:text-gray-500">
						{#if open}
							<ChevronUp strokeWidth="3.5" className="size-3" />
						{:else}
							<ChevronDown strokeWidth="3.5" className="size-3" />
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>

	{#if !open && resolvable && pendingToolTokens.length > 1}
		<div class="mt-1 space-y-0.5">
			{#each pendingToolTokens as token}
				{@const pendingCallId = token?.attributes?.id ?? ''}
				<div class="flex items-center gap-2 py-1 px-1">
					<span class="text-xs text-gray-500 dark:text-gray-400 flex-1 min-w-0 line-clamp-1">
						{token?.attributes?.name ?? $i18n.t('tool')}
					</span>
					{#if token?.attributes?.name !== 'ask_user'}
						<span class="flex gap-1 shrink-0">
							<button
								type="button"
								class="tool-call-allow-button text-[0.6875rem] px-2.5 py-0.5 rounded-md text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-white/8 hover:bg-gray-200 dark:hover:bg-white/12 transition-colors duration-100 disabled:opacity-50"
								disabled={!pendingCallId || resolvingCallId === pendingCallId}
								on:click={() => onResolve(pendingCallId, true)}
							>
								{$i18n.t('Allow')}
							</button>
							<button
								type="button"
								class="tool-call-deny-button text-[0.6875rem] px-2 py-0.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 disabled:opacity-50"
								disabled={!pendingCallId || resolvingCallId === pendingCallId}
								on:click={() => onResolve(pendingCallId, false)}
							>
								{$i18n.t('Deny')}
							</button>
						</span>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	{#if open}
		<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
			<div class="mb-1">
				<slot name="content" />
			</div>
		</div>
	{/if}

	{#if allEmbeds.length > 0}
		{#each allEmbeds as embedItem, idx}
			<div id={`${id}-embed-${idx}`}>
				<FullHeightIframe
					src={embedItem.embed}
					args={embedItem.args}
					allowScripts={true}
					allowForms={$settings?.iframeSandboxAllowForms ?? false}
					allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
					allowPopups={true}
				/>
			</div>
		{/each}
	{/if}
</div>
