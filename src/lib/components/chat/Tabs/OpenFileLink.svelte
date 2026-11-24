<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';

	export let href: string;
	export let label: string;
</script>

<Tooltip content={label}>
	<a
		class="inline-flex h-7 min-w-7 shrink-0 items-center justify-center rounded-md p-1.5 text-base-500 transition hover:bg-base-100 dark:text-base-400 dark:hover:bg-base-800"
		{href}
		target="_blank"
		rel="noopener noreferrer"
		aria-label={label}
	>
		<Icon name="external-link" size={14} />
	</a>
</Tooltip>
