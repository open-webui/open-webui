<script lang="ts">
	import { getContext, untrack } from 'svelte';

	import CodeEditor from './CodeEditor.svelte';
	import Modal from './Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: any = getContext('i18n');

	let {
		show = $bindable(false),
		value = '',
		lang = 'python',
		title = '',
		description = '',
		onChange = (_value: string) => {},
		onSave = () => {}
	}: {
		show?: boolean;
		value?: string;
		lang?: string;
		title?: string;
		description?: string;
		onChange?: (value: string) => void;
		onSave?: () => void;
	} = $props();

	// Edits stay in a draft until saved, so closing (or Escape) discards them.
	let draft = $state('');

	$effect(() => {
		if (show) {
			draft = untrack(() => value) ?? '';
		}
	});

	const jsonError = $derived.by(() => {
		if (lang !== 'json' || !draft.trim()) return '';
		try {
			JSON.parse(draft);
			return '';
		} catch (e) {
			return e instanceof Error ? e.message : `${e}`;
		}
	});

	const format = () => {
		if (lang !== 'json' || !draft.trim() || jsonError) return;
		draft = JSON.stringify(JSON.parse(draft), null, 2);
	};

	const save = () => {
		if (jsonError) return;
		onChange(draft);
		onSave();
		show = false;
	};
</script>

<Modal bind:show size="lg" ariaLabel={title || $i18n.t('Code Editor')}>
	<div class="flex h-[min(80dvh,46rem)] flex-col dark:text-base-200">
		<div class="flex items-start justify-between gap-4 px-4 pt-3 pb-2">
			<div class="min-w-0">
				<h1 class="text-sm font-medium text-base-900 dark:text-base-100">
					{title || $i18n.t('Code Editor')}
				</h1>
				{#if description}
					<div class="text-xs text-base-500 line-clamp-1">{description}</div>
				{/if}
			</div>

			<button
				class="shrink-0 self-start mt-0.5"
				type="button"
				aria-label={$i18n.t('Close')}
				onclick={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div
			class="code-editor-modal mx-4 min-h-0 flex-1 overflow-hidden rounded-2xl border border-base-100/80 bg-base-50/60 py-1 dark:border-base-850 dark:bg-base-950/40"
		>
			<CodeEditor
				value={draft}
				{lang}
				ariaLabel={title || $i18n.t('Code Editor')}
				className="text-xs"
				onChange={(content: string) => {
					draft = content;
				}}
				onSave={save}
			/>
		</div>

		<div class="flex items-center justify-between gap-3 px-4 pt-3 pb-4">
			<div class="min-w-0 flex items-center gap-3 text-xs">
				{#if lang === 'json'}
					<button
						class="shrink-0 text-base-500 transition hover:text-base-900 hover:underline disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed dark:hover:text-white"
						type="button"
						disabled={!draft.trim() || !!jsonError}
						onclick={format}
					>
						{$i18n.t('Format')}
					</button>
				{/if}

				{#if jsonError}
					<div class="truncate text-red-500 dark:text-red-400" title={jsonError}>
						{$i18n.t('Invalid JSON')}: {jsonError}
					</div>
				{/if}
			</div>

			<div class="flex shrink-0 items-center gap-2">
				<button
					class="px-1 py-1.5 text-xs text-base-500 transition hover:text-base-700 hover:underline dark:text-base-400 dark:hover:text-base-200"
					type="button"
					onclick={() => {
						show = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>

				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-white"
					type="button"
					disabled={!!jsonError}
					onclick={save}
				>
					{$i18n.t('Save')}
				</button>
			</div>
		</div>
	</div>
</Modal>

<style>
	/* Sit on the panel instead of the editor's own white/black (or One Dark) background. */
	.code-editor-modal :global(.cm-editor),
	.code-editor-modal :global(.cm-gutters) {
		background-color: transparent !important;
	}

	.code-editor-modal :global(.cm-gutters) {
		color: var(--color-base-400);
	}

	.code-editor-modal :global(.cm-activeLine),
	.code-editor-modal :global(.cm-activeLineGutter) {
		background-color: color-mix(in oklab, currentColor 4%, transparent) !important;
	}
</style>
