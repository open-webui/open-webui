<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let params: { reasoning_effort?: string | null } = {};
	export let options: string[] = [];

	let show = false;

	$: selected = params?.reasoning_effort ?? null;

	const select = (option: string | null) => {
		params.reasoning_effort = option;
		show = false;
	};
</script>

<div class="flex items-center">
	<Dropdown bind:show>
		<Tooltip content={$i18n.t('Reasoning Effort')} placement="top">
			<button
				type="button"
				aria-label={$i18n.t('Reasoning Effort')}
				class="flex items-center gap-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 text-sm transition rounded-lg cursor-pointer {selected
					? ' px-2.5 py-1 '
					: ' p-2 opacity-50'}"
			>
				<LightBulb className="size-3.5" strokeWidth="2" />

				{#if selected}
					<span class="truncate text-[13px] max-w-[100px] sm:max-w-[150px]">{selected}</span>
				{/if}
			</button>
		</Tooltip>

		<div slot="content">
			<div
				class="min-w-40 max-w-56 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
			>
				<button
					type="button"
					class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl {selected ===
					null
						? 'bg-gray-50 dark:bg-gray-800/50'
						: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
					on:click={() => select(null)}
				>
					<span class="truncate">{$i18n.t('Default')}</span>
					{#if selected === null}
						<Check className="size-4 shrink-0" strokeWidth="2.5" />
					{/if}
				</button>

				{#each options as option (option)}
					<button
						type="button"
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl {selected ===
						option
							? 'bg-gray-50 dark:bg-gray-800/50'
							: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
						on:click={() => select(option)}
					>
						<span class="truncate">{option}</span>
						{#if selected === option}
							<Check className="size-4 shrink-0" strokeWidth="2.5" />
						{/if}
					</button>
				{/each}
			</div>
		</div>
	</Dropdown>
</div>
