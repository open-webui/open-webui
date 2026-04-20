<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { CalendarEventModel } from '$lib/apis/calendar';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let event: CalendarEventModel;
	export let calendarColor: string | null = null;

	const dispatch = createEventDispatcher();
</script>

<Tooltip content="{event.title}{event.location ? ` · ${event.location}` : ''}">
	<button
		class="w-full text-left text-xs flex items-start gap-1.5 py-[1px] px-0.5 rounded-md
			{event.meta?.automation_id ? 'opacity-60' : ''}
			hover:bg-gray-50 dark:hover:bg-gray-800/50 transition truncate"
		on:click|stopPropagation={() => dispatch('click', event)}
	>
		<span
			class="shrink-0 size-[7px] rounded-full mt-[5px]"
			style="background-color: {event.color || calendarColor || '#3b82f6'};"
		></span>
		<span class="truncate">
			{#if !event.all_day}<span class="text-gray-500 dark:text-gray-400"
					>{new Date(event.start_at / 1_000_000)
						.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
						.replace(' ', '')}</span
				>{/if}
			{event.title}
		</span>
	</button>
</Tooltip>
