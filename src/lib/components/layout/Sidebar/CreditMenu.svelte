<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { fade } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<!-- <DropdownMenu.Content
			class="w-full {className} text-sm rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary"
			sideOffset={8}
			side="top"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => window.open('https://pmt2.ust.hk/openai/', '_blank')}
			>
				<div class=" self-center truncate">{$i18n.t('Purchase API Credit')}</div>
			</button>
		</DropdownMenu.Content> -->
	</slot>
</DropdownMenu.Root>
