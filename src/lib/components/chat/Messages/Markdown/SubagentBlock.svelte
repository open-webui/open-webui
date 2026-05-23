<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import { toast } from 'svelte-sonner';

	import { chatId, socket, subagentLiveStates } from '$lib/stores';
	import { rerunSubagent, type SubagentRerunScope } from '$lib/apis/subagents';
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
	$: subagentChatId = run?.chat_id ?? attributes?.id ?? '';
	$: continuation = run?.continuation === true;
	$: stale = run?.stale === true;

	// Subagent body renders the structured `content_blocks` directly via a
	// keyed `{#each}` (see template below). We deliberately do NOT compute a
	// flat markdown projection here: it would re-walk + re-stringify the
	// whole array on every store update, and the parent `<Markdown>` would
	// re-tokenise + {@html}-wipe the DOM on every chunk. That's the O(N²)
	// pattern that made the UI feel like 1-2 TPS while OpenRouter was happily
	// streaming at 20+. Structural rendering with keyed each lets Svelte
	// reuse component instances for unchanged blocks and apply O(diff) text
	// node updates for the one growing block, so per-event cost is O(1) and
	// the UI tracks upstream as fast as the model can produce.
	//
	// During streaming we render text blocks as plain pre-wrapped text — no
	// `marked.parse` per chunk. Once the run is complete we swap each text
	// block to a full `<Markdown>` render so the final answer gets headings,
	// lists, code blocks, etc. (one parse, total).
	$: contentBlocks = (run?.content_blocks ?? []) as any[];
	$: hasContent = contentBlocks.length > 0;
	$: doneRendering = status !== 'running';

	// Default collapsed in every state (running / done / error / cancelled).
	// The user clicks the header (or the redo button) to expand and watch
	// the subagent's current work. The status badge + spinner in the header
	// still convey progress at a glance without forcing the body open.
	let open = false;

	const toggle = () => {
		open = !open;
	};

	// Used by the tool_calls per-block render to look up the matching result
	// entry. Lives outside the template so the typed callback doesn't trip
	// Svelte's template parser (which doesn't accept TS annotations inside
	// `{@const}` expressions).
	const findToolResult = (results: any[] | undefined, callId: string | undefined) =>
		(results ?? []).find((r: any) => r?.tool_call_id === callId);

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

	// Redo menu state — anchored to the redo button in the header. The
	// outside-click handler covers both "click elsewhere" and "click on the
	// header (which would toggle the collapsible)".
	let redoMenuOpen = false;
	let redoMenuContainer: HTMLDivElement | null = null;
	let redoBusy = false;

	const closeRedoMenu = () => {
		redoMenuOpen = false;
	};

	const onDocClick = (e: MouseEvent) => {
		if (!redoMenuOpen) return;
		const target = e.target as Node | null;
		if (target && redoMenuContainer && !redoMenuContainer.contains(target)) {
			redoMenuOpen = false;
		}
	};

	const onDocKey = (e: KeyboardEvent) => {
		if (e.key === 'Escape') redoMenuOpen = false;
	};

	if (typeof document !== 'undefined') {
		document.addEventListener('click', onDocClick);
		document.addEventListener('keydown', onDocKey);
	}
	onDestroy(() => {
		if (typeof document !== 'undefined') {
			document.removeEventListener('click', onDocClick);
			document.removeEventListener('keydown', onDocKey);
		}
	});

	const toggleRedoMenu = (e: Event) => {
		e.preventDefault();
		e.stopPropagation();
		redoMenuOpen = !redoMenuOpen;
	};

	const triggerRerun = async (scope: SubagentRerunScope) => {
		closeRedoMenu();
		if (redoBusy) return;
		if (status === 'running') {
			toast.error($i18n.t('Subagent is already running.'));
			return;
		}
		// We need a few things to call /rerun: which parent chat (the chat
		// we're inside), which parent message (stored on the run), which
		// entry to refresh (the stateKey), and a session_id so events route
		// back to us. If any are missing the rerun would no-op silently —
		// surface that instead.
		const parentChatId = $chatId;
		const parentMessageId = run?.parent_message_id;
		const sessionId = $socket?.id;
		if (!parentChatId || !parentMessageId || !sessionId || !stateKey) {
			toast.error(
				$i18n.t('Cannot redo subagent: missing chat / message / session context.')
			);
			return;
		}

		redoBusy = true;
		try {
			await rerunSubagent(localStorage.token, {
				parent_chat_id: parentChatId,
				parent_message_id: parentMessageId,
				session_id: sessionId,
				entry_key: stateKey,
				scope
			});
			// Optimistically flip status so the spinner shows while the
			// backend's `chat:subagent:start` event is in flight. The store
			// entry will fully refresh once that event arrives.
			subagentLiveStates.update((s) => {
				const cur = s[stateKey];
				if (!cur) return s;
				return {
					...s,
					[stateKey]: {
						...cur,
						status: 'running',
						content_blocks: [],
						content: '',
						final_text: undefined,
						error: undefined,
						stale: false,
						started_at: Math.floor(Date.now() / 1000),
						ended_at: undefined
					}
				};
			});
			// Note: we don't auto-expand the body on rerun. The default is
			// collapsed in every state; the user clicks the header to see
			// the live work if they want to.
		} catch (err: any) {
			console.error(err);
			toast.error(`${err?.detail ?? err?.message ?? err}`);
		} finally {
			redoBusy = false;
		}
	};
</script>

<div
	class="my-2 rounded-2xl border {stale
		? 'border-gray-200/60 dark:border-gray-800/50 bg-white/20 dark:bg-gray-900/20 opacity-70'
		: 'border-gray-200 dark:border-gray-800 bg-white/40 dark:bg-gray-900/40'} overflow-hidden subagent-block"
	data-tool-call-id={attributes?.tool_call_id ?? ''}
	data-subagent-id={attributes?.id ?? ''}
>
	<div class="flex items-center gap-2 px-3 py-2">
		<button
			type="button"
			class="flex-1 flex items-center gap-2 text-left hover:opacity-90 transition-opacity"
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
				{#if stale}
					<span
						class="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500 italic"
						title={$i18n.t('Subagent was restarted; this turn is outdated.')}
					>
						{$i18n.t('stale')}
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

		<!-- Redo dropdown (sibling of the header toggle, not inside it, so the
			click doesn't bubble up to the collapsible toggle). -->
		<div class="relative shrink-0" bind:this={redoMenuContainer}>
			<button
				type="button"
				class="p-1.5 rounded-md text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
				on:click={toggleRedoMenu}
				disabled={status === 'running' || redoBusy}
				aria-label={$i18n.t('Redo subagent')}
				title={$i18n.t('Redo subagent')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.75"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-4"
				>
					<polyline points="23 4 23 10 17 10" />
					<path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
				</svg>
			</button>

			{#if redoMenuOpen}
				<div
					class="absolute right-0 top-full mt-1 z-10 min-w-[200px] rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg overflow-hidden"
					transition:slide={{ duration: 120, axis: 'y' }}
				>
					<button
						type="button"
						class="w-full text-left px-3 py-2 text-sm text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 flex flex-col gap-0.5"
						on:click|preventDefault={() => triggerRerun('this_turn')}
					>
						<span class="font-medium">{$i18n.t('Redo last subagent turn')}</span>
						<span class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('Re-send the same request; keep prior turns intact.')}
						</span>
					</button>
					<div class="h-px bg-gray-100 dark:bg-gray-800" />
					<button
						type="button"
						class="w-full text-left px-3 py-2 text-sm text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 flex flex-col gap-0.5"
						on:click|preventDefault={() => triggerRerun('from_launch')}
					>
						<span class="font-medium">{$i18n.t('Redo subagent')}</span>
						<span class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t("Discard the subagent's work; restart from the original prompt.")}
						</span>
					</button>
				</div>
			{/if}
		</div>
	</div>

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

			{#if hasContent}
				<div class="subagent-inner space-y-2">
					{#each contentBlocks as block, i (i)}
						{#if block?.type === 'text'}
							{#if doneRendering}
								<div class="markdown-prose">
									<Markdown
										id={`subagent-${stateKey}-text-${i}`}
										content={block.content ?? ''}
										done={true}
										editCodeBlock={false}
									/>
								</div>
							{:else}
								<div
									class="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 leading-relaxed"
								>{block.content ?? ''}</div>
							{/if}
						{:else if block?.type === 'reasoning'}
							<details class="rounded-lg bg-gray-50 dark:bg-gray-850 px-3 py-1.5">
								<summary
									class="text-xs font-medium text-gray-600 dark:text-gray-400 cursor-pointer select-none"
								>
									{#if block.duration != null}
										{$i18n.t('Thought for {{n}}s', { n: block.duration })}
									{:else}
										{$i18n.t('Thinking…')}
									{/if}
								</summary>
								<div
									class="mt-2 whitespace-pre-wrap text-xs text-gray-500 dark:text-gray-400 leading-relaxed"
								>{block.content ?? ''}</div>
							</details>
						{:else if block?.type === 'tool_calls'}
							<div class="space-y-1">
								{#each block.content ?? [] as call, j (call?.id ?? `tc-${i}-${j}`)}
									{@const result = findToolResult(block.results, call?.id)}
									<div
										class="flex items-baseline gap-2 text-xs text-gray-600 dark:text-gray-400 font-mono"
									>
										<span class="shrink-0 w-3 text-center">
											{result !== undefined ? '✓' : '·'}
										</span>
										<span class="font-medium text-gray-800 dark:text-gray-300">
											{call?.function?.name ?? 'tool'}
										</span>
										<span class="truncate text-gray-500 dark:text-gray-500">
											{call?.function?.arguments ?? ''}
										</span>
									</div>
								{/each}
							</div>
						{:else if block?.type === 'code_interpreter'}
							<div class="rounded-lg bg-gray-50 dark:bg-gray-850 px-3 py-2 text-xs">
								<div
									class="font-medium text-gray-700 dark:text-gray-300 mb-1 font-mono"
								>
									{block.attributes?.lang ?? 'code'}
								</div>
								<pre
									class="whitespace-pre-wrap font-mono text-gray-600 dark:text-gray-400">{block.content ?? ''}</pre>
							</div>
						{/if}
					{/each}
				</div>
			{:else if status === 'running'}
				<div class="text-sm text-gray-500 dark:text-gray-400 italic">
					{$i18n.t('Subagent is starting up…')}
				</div>
			{:else if status === 'done' && run?.final_text}
				<div class="markdown-prose">
					<Markdown
						id={`subagent-${stateKey}-final`}
						content={run.final_text}
						done={true}
						editCodeBlock={false}
					/>
				</div>
			{/if}

			{#if subagentChatId}
				<div class="mt-3 pt-2 border-t border-gray-100 dark:border-gray-800">
					<a
						href={`/c/${subagentChatId}`}
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
