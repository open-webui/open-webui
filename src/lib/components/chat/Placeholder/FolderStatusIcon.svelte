<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import {
		glyphColor,
		NO_STATUS,
		type FolderStatus,
		type StatusDef,
		type StatusGlyph
	} from '$lib/utils/folders';
	import type { TagColor } from '$lib/utils/tags';
	import Emoji from '$lib/components/common/Emoji.svelte';

	/** A folder status id, looked up in the folder's statuses. */
	export let status: FolderStatus = NO_STATUS;
	/** Explicit look, e.g. for previews; overrides the lookup. */
	export let glyph: StatusGlyph | undefined = undefined;
	export let color: TagColor | undefined = undefined;
	export let emoji: string | undefined = undefined;
	export let className = 'size-3.5';

	const defs = getContext<Readable<StatusDef[]> | undefined>('folder-statuses');
	$: def = glyph || emoji ? undefined : $defs?.find((item) => item.id === status);
	$: shownEmoji = emoji ?? def?.icon;
	$: shape = glyph ?? def?.glyph ?? (status === NO_STATUS || !def ? null : 'todo');
	$: tone = glyphColor[color ?? def?.color ?? 'gray'];
</script>

{#if shownEmoji}
	<Emoji shortCode={shownEmoji} className="shrink-0 {className}" />
{:else if !shape}
	<!-- No status -->
	<svg
		class="shrink-0 text-gray-300 dark:text-gray-600 {className}"
		viewBox="0 0 14 14"
		fill="none"
		aria-hidden="true"
	>
		<path d="M4.25 7h5.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
	</svg>
{:else}
	<svg class="shrink-0 {tone} {className}" viewBox="0 0 14 14" fill="none" aria-hidden="true">
		{#if shape === 'done'}
			<circle cx="7" cy="7" r="6.25" fill="currentColor" />
			<path
				d="M4.4 7.2 6.1 8.9 9.6 5.4"
				stroke="var(--color-white)"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
		{:else}
			<circle
				cx="7"
				cy="7"
				r="5.75"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-dasharray={shape === 'backlog' ? '1.6 1.8' : undefined}
			/>
			{#if shape === 'in_progress'}
				<path d="M7 4a3 3 0 0 1 0 6z" fill="currentColor" />
			{:else if shape === 'waiting'}
				<path d="M7 4a3 3 0 1 1-3 3h3z" fill="currentColor" />
			{/if}
		{/if}
	</svg>
{/if}
