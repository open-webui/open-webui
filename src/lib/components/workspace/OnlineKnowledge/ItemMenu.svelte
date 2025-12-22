<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import EllipsisVertical from '../../icons/EllipsisVertical.svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	let show = false;
</script>

<DropdownMenu.Root bind:open={show}>
	<DropdownMenu.Trigger>
		<button
			class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
			on:click|stopPropagation
		>
			<EllipsisVertical className="size-4" />
		</button>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		class="bg-white dark:bg-gray-850 rounded-xl shadow-lg border border-gray-100 dark:border-gray-800 py-1 min-w-[140px] z-50"
		align="end"
		sideOffset={4}
	>
		<DropdownMenu.Item
			class="flex items-center gap-2 px-3 py-2 text-sm text-error-500 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition"
			on:click={() => {
				show = false;
				dispatch('delete');
			}}
		>
			<GarbageBin className="size-4" />
			<span>{$i18n.t('삭제')}</span>
		</DropdownMenu.Item>
	</DropdownMenu.Content>
</DropdownMenu.Root>
