<script lang="ts">
	import { getContext } from 'svelte';
	import Icon from '../FileNav/Icon.svelte';

	const i18n: any = getContext('i18n');

	export let show = false;
</script>

{#if show}
	<div
		class="pointer-events-none absolute inset-0 z-50 bg-black/[0.02] dark:bg-white/[0.02]"
		role="status"
		aria-label={$i18n.t('Drag and Drop Container')}
	>
		<div
			class="absolute left-1/2 top-1/2 flex max-w-[calc(100%-1rem)] -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-lg bg-white/95 px-2.5 py-1.5 text-xs text-gray-600 shadow-sm ring-1 ring-black/5 dark:bg-gray-850/95 dark:text-gray-300 dark:ring-white/10"
		>
			<Icon name="upload-tray" size={14} strokeWidth={1.5} />
			<span class="truncate">{$i18n.t('Drop to upload')}</span>
		</div>
	</div>
{/if}
