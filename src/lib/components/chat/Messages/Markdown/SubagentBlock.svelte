<script lang="ts">
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import { blocksToDisplayMarkdown } from '$lib/utils';
	import { subagentLiveStates } from '$lib/stores';
	import Markdown from '../Markdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: any = getContext('i18n');

	// `attributes` is what `Collapsible.svelte` parses out of the
	// `<details type="subagent_launch" ...>` tag that
	// `serialize_content_blocks` (middleware.py) emits for every
	// subagent_launch / subagent_continue tool call in the parent message.
	// Keys we care about:
	//   tool_call_id — primary key into subagentLiveStates (one entry per
	//                  parent-model tool call; preferred over `id`)
	//   id           — backstop: the subagent's chat_id (set by middleware as
	//                  soon as the side-channel has it, may be empty before)
	//   name         — function name (subagent_launch or subagent_continue)
	//   arguments    — JSON-encoded args (used for the "Args" disclosure)
	//   done         — "true" once the parent tool result lands
	export let attributes: Record<string, any> = {};

	$: stateKey = (attributes?.tool_call_id || attributes?.id || '') as string;
	$: run = stateKey ? $subagentLiveStates[stateKey] : undefined;

	// Header status the user sees. Prefer the store entry (live + final);
	// fall back to the markdown attribute when the store hasn't been
	// hydrated yet for some reason (e.g. mid-stream race).
	$: status = (run?.status ?? (attributes?.done === 'true' ? 'done' : 'running')) as
		| 'running'
		| 'done'
		| 'error'
		| 'cancelled';

	$: displayName = run?.name ?? '';
	$: displayNum = run?.num ?? null;
	$: chatId = run?.chat_id ?? attributes?.id ?? '';
	$: continuation = run?.continuation === true;

	// Render the subagent's content_blocks via the SAME projection used for
	// regular assistant messages — that produces a markdown string with
	// nested `<details type="tool_calls">`, `<details type="reasoning">`,
	// etc. The recursive Markdown render then turns those into Collapsibles.
	// Note: there will never be a nested `<details type="subagent_launch">`
	// here because subagents don't get the subagent tools (enforced server-
	// side in run_subagent.py / get_tools).
	$: innerMarkdown = (() => {
		if (run?.content_blocks && Array.isArray(run.content_blocks) && run.content_blocks.length) {
			return blocksToDisplayMarkdown(run.content_blocks);
		}
		if (typeof run?.content === 'string' && run.content.length > 0) {
			return run.content;
		}
		if (typeof run?.final_text === 'string' && run.final_text.length > 0) {
			return run.final_text;
		}
		return '';
	})();

	// Auto-expand while running so the user can watch progress; auto-collapse
	// on completion so finished subagent blocks don't dominate the parent
	// message. Mirrors the reasoning block's `autoExpandReasoningDuringStreaming`
	// pattern.
	let open = true;
	let userToggled = false;
	$: if (!userToggled) {
		open = status === 'running' || status === 'error';
	}

	const toggle = () => {
		userToggled = true;
		open = !open;
	};

	const statusBadgeText = (s: typeof status) => {
		switch (s) {
			case 'running':
				return $i18n.t('Researching…');
			case 'done':
				return $i18n.t('Done');
			case 'error':
				return $i18n.t('Error');
			case 'cancelled':
				return $i18n.t('Cancelled');
			default:
				return s;
		}
	};
</script>

<div
	class="my-2 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/40 dark:bg-gray-900/40 overflow-hidden subagent-block"
	data-tool-call-id={attributes?.tool_call_id ?? ''}
	data-subagent-id={attributes?.id ?? ''}
>
	<button
		type="button"
		class="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-850 transition-colors"
		on:click|preventDefault={toggle}
		aria-expanded={open}
	>
		<!-- Status icon -->
		<span class="shrink-0 inline-flex items-center justify-center size-5">
			{#if status === 'running'}
				<Spinner className="size-4" />
			{:else if status === 'done'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-4 text-green-600 dark:text-green-500"
				>
					<path d="M20 6L9 17l-5-5" />
				</svg>
			{:else if status === 'error'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-4 text-red-600 dark:text-red-500"
				>
					<circle cx="12" cy="12" r="10" />
					<line x1="12" y1="8" x2="12" y2="12" />
					<line x1="12" y1="16" x2="12.01" y2="16" />
				</svg>
			{:else if status === 'cancelled'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-4 text-gray-500"
				>
					<circle cx="12" cy="12" r="10" />
					<line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
				</svg>
			{/if}
		</span>

		<!-- Header text -->
		<div class="flex-1 min-w-0 flex items-baseline gap-2">
			<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Subagent')}{displayNum != null ? ` #${displayNum}` : ''}
			</span>
			{#if displayName}
				<span class="text-sm text-gray-500 dark:text-gray-400 truncate">
					— {displayName}{continuation ? ` (${$i18n.t('continued')})` : ''}
				</span>
			{/if}
		</div>

		<!-- Status badge -->
		<span
			class="shrink-0 text-xs font-medium uppercase tracking-wide {status === 'done'
				? 'text-green-600 dark:text-green-500'
				: status === 'error'
					? 'text-red-600 dark:text-red-500'
					: status === 'cancelled'
						? 'text-gray-500'
						: 'text-blue-600 dark:text-blue-400'}"
		>
			{statusBadgeText(status)}
		</span>

		<!-- Caret -->
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			class="size-4 shrink-0 transition-transform text-gray-500 {open ? 'rotate-180' : ''}"
		>
			<polyline points="6 9 12 15 18 9" />
		</svg>
	</button>

	{#if open}
		<div transition:slide={{ duration: 250, easing: quintOut }} class="px-3 pb-3">
			{#if run?.prompt}
				<div
					class="mb-2 text-xs text-gray-500 dark:text-gray-500 border-l-2 border-gray-200 dark:border-gray-700 pl-2"
				>
					<span class="font-semibold text-gray-700 dark:text-gray-400">
						{$i18n.t('Prompt')}:
					</span>
					{run.prompt}
					{#if run?.background}
						<div class="mt-1">
							<span class="font-semibold text-gray-700 dark:text-gray-400">
								{$i18n.t('Background')}:
							</span>
							{run.background}
						</div>
					{/if}
				</div>
			{/if}

			{#if status === 'error' && run?.error}
				<div
					class="rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 px-3 py-2 text-sm text-red-700 dark:text-red-300"
				>
					{typeof run.error === 'string'
						? run.error
						: (run.error?.message ?? $i18n.t('Subagent failed without details.'))}
				</div>
			{/if}

			{#if innerMarkdown}
				<div class="subagent-inner-markdown markdown-prose">
					<Markdown
						id={`subagent-${stateKey}`}
						content={innerMarkdown}
						done={status !== 'running'}
						editCodeBlock={false}
					/>
				</div>
			{:else if status === 'running'}
				<div class="text-sm text-gray-500 dark:text-gray-400 italic">
					{$i18n.t('Subagent is starting up…')}
				</div>
			{/if}

			{#if chatId}
				<div class="mt-3 pt-2 border-t border-gray-100 dark:border-gray-800">
					<a
						href={`/c/${chatId}`}
						target="_blank"
						rel="noopener noreferrer"
						class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 inline-flex items-center gap-1"
					>
						{$i18n.t('Open full subagent chat')}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							class="size-3"
						>
							<path d="M7 17L17 7M17 7H9M17 7v8" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
					</a>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.subagent-block :global(details summary) {
		cursor: pointer;
	}
</style>
