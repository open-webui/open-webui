<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { models, socket } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let chatId: string;
	export let messageId: string;
	export let taskId: string | null = null;
	export let currentModelId: string;
	export let onSwitch: (modelId: string) => void = () => {};

	let show = false;
	let pendingSwitch: string | null = null;

	// Filter to only show available models (exclude current)
	$: availableModels = $models.filter(
		(m) => m.id !== currentModelId && !(m?.info?.meta?.hidden ?? false)
	);

	const switchModel = async (modelId: string) => {
		pendingSwitch = modelId;
		
		// Emit model-switch event via socket
		$socket?.emit('model-switch', {
			chat_id: chatId,
			message_id: messageId,
			task_id: taskId,
			model_id: modelId
		});

		onSwitch(modelId);
		show = false;
	};
</script>

<Dropdown
	bind:show
	align="end"
>
	<Tooltip content={$i18n.t('Switch Model')} placement="bottom">
		<button
			class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition animate-pulse"
			aria-label={$i18n.t('Switch Model')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				class="w-4 h-4"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
				/>
			</svg>
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[280px] rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition max-h-80 overflow-y-auto"
			sideOffset={4}
			side="top"
			align="end"
			transition={flyAndScale}
		>
			<div class="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800 mb-1">
				{$i18n.t('Switch to another model')}
			</div>
			
			{#if pendingSwitch}
				<div class="px-3 py-2 text-sm text-amber-600 dark:text-amber-400 flex items-center gap-2">
					<svg class="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					{$i18n.t('Switching...')}
				</div>
			{:else}
				{#each availableModels as model}
					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
						on:click={() => switchModel(model.id)}
					>
						{#if model?.info?.meta?.profile_image_url}
							<img
								src={model.info.meta.profile_image_url}
								class="w-5 h-5 rounded-full"
								alt={model.name}
							/>
						{:else}
							<div class="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs">
								{model.name?.charAt(0) ?? 'M'}
							</div>
						{/if}
						<span class="truncate">{model.name ?? model.id}</span>
					</DropdownMenu.Item>
				{/each}

				{#if availableModels.length === 0}
					<div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('No other models available')}
					</div>
				{/if}
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
