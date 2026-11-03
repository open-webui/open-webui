<script lang="ts">
	import { config } from '$lib/stores';
	import { inboxCount } from '$lib/stores/inbox';
	export let className = '-top-1 text-[0.5625rem]';
</script>

{#if $config?.features?.enable_notifications && $inboxCount > 0}
	<span
		aria-hidden="true"
		class="pointer-events-none absolute -end-1.5 flex h-3 min-w-3 items-center justify-center rounded-full bg-sky-500 px-px font-semibold leading-none tabular-nums text-white ring-1 ring-gray-50 dark:ring-gray-950 {className}"
		>{$inboxCount}</span
	>
{/if}
