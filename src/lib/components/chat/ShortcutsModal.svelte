<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Modal from '../common/Modal.svelte';
	import { shortcuts } from '$lib/shortcuts';
	import ShortcutItem from './ShortcutItem.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	type CategorizedShortcuts = {
		[category: string]: {
			left: Shortcut[];
			right: Shortcut[];
		};
	};

	const i18n = getContext('i18n');

	export let show = false;

	let categorizedShortcuts: CategorizedShortcuts = {};
	let isMac = false;

	onMount(() => {
		isMac = /Mac/i.test(navigator.userAgent);
		const allShortcuts = Object.values(shortcuts);

		const result = allShortcuts.reduce((acc, shortcut) => {
			const category = shortcut.category;
			if (!acc[category]) {
				acc[category] = [];
			}
			acc[category].push(shortcut);
			return acc;
		}, {});

		for (const category in result) {
			const half = Math.ceil(result[category].length / 2);
			categorizedShortcuts[category] = {
				left: result[category].slice(0, half),
				right: result[category].slice(half)
			};
		}
	});
</script>

<Modal bind:show>
	<div class="text-gray-700 dark:text-gray-100">
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4">
			<div class="text-lg font-medium self-center">{$i18n.t('Shortcuts')}</div>
			<button class="self-center" on:click={() => (show = false)}>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#each Object.entries(categorizedShortcuts) as [category, columns], i}
			{#if i > 0}
				<div class="px-5">
					<div class="w-full border-t dark:border-gray-700 border-gray-200" />
				</div>
			{/if}

			<div class="flex justify-between dark:text-gray-300 px-5 pt-4">
				<div class="text-lg font-medium self-center">{$i18n.t(category)}</div>
			</div>
			<div class="flex flex-col md:flex-row w-full p-5 md:space-x-4 dark:text-gray-200">
				<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
					<div class="flex flex-col space-y-3 w-full self-start">
						{#each columns.left as shortcut}
							<ShortcutItem {shortcut} {isMac} />
						{/each}
					</div>
					<div class="flex flex-col space-y-3 w-full self-start">
						{#each columns.right as shortcut}
							<ShortcutItem {shortcut} {isMac} />
						{/each}
					</div>
				</div>
			</div>
		{/each}

		<div class="px-5 pb-4 text-xs text-gray-500 dark:text-gray-400">
			{@html $i18n.t(
				'Shortcuts with an asterisk (*) are situational and only active under specific conditions.'
			)}
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	.tabs::-webkit-scrollbar {
		display: none;
	}

	.tabs {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}

	input[type='number'] {
		-moz-appearance: textfield;
	}
</style>