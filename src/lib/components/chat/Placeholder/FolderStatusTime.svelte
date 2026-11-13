<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import dayjs from 'dayjs';
	import { statusKey, type StatusDef, type WorkspaceChat } from '$lib/utils/folders';
	import { formatElapsed, formatElapsedShort } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const defs = getContext<Readable<StatusDef[]> | undefined>('folder-statuses');

	export let chat: WorkspaceChat;
	export let className = '';

	const escape = (value: string) => value.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
	const nameOf = (id: string) => $defs?.find((item) => item.id === id)?.name ?? id;
	// A plain length of time, e.g. "2 hours", from a number of seconds.
	const span = (seconds: number) => formatElapsed(Date.now() / 1000 - seconds, $i18n.language);

	$: current = statusKey(chat.status);
	$: earlier = chat.status_durations?.[current] ?? 0;
	$: others = Object.entries(chat.status_durations ?? {}).filter(
		([id, seconds]) => id !== current && seconds > 0
	);

	// What the "3d" label can't say: when this stretch began, whether earlier time is
	// included, and how long the chat spent in its other statuses.
	$: tip = !chat.status_since
		? ''
		: [
				`${escape(nameOf(current))} · ${escape(
					earlier
						? $i18n.t('{{duration}} in total', {
								duration: formatElapsed(chat.status_since, $i18n.language)
							})
						: formatElapsed(chat.status_since, $i18n.language)
				)}`,
				...(chat.status_entered_at
					? [
							`<span class="opacity-60">${escape(
								$i18n.t(earlier ? 'This time since {{date}}' : 'Since {{date}}', {
									date: dayjs(chat.status_entered_at * 1000)
										.locale($i18n.language)
										.format('llll')
								})
							)}</span>`
						]
					: []),
				...(others.length
					? [
							`<span class="opacity-60">${escape(
								$i18n.t('Before: {{statuses}}', {
									statuses: others
										.map(([id, seconds]) => `${nameOf(id)} ${span(seconds)}`)
										.join(' · ')
								})
							)}</span>`
						]
					: [])
			].join('<br>');
</script>

{#if chat.status_since && chat.status}
	<Tooltip content={tip} placement="top" allowHTML as="span" className="flex shrink-0">
		<span class="text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-500 {className}"
			>{formatElapsedShort(chat.status_since)}</span
		>
	</Tooltip>
{/if}
