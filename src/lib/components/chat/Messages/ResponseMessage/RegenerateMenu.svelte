<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { models } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import LineSpace from '$lib/components/icons/LineSpace.svelte';
	import LineSpaceSmaller from '$lib/components/icons/LineSpaceSmaller.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let onRegenerate: Function = (prompt = null) => {};
	export let onRegenerateWithModel: Function = (
		modelId: string,
		preserveToolContext?: boolean
	) => {};
	export let onClose: Function = () => {};
	export let currentModelId: string = '';
	export let hasToolCalls: boolean = false;

	let show = false;
	let inputValue = '';
	let showModelSelector = false;
	let preserveContext = true;

	// Filter to only show available models
	$: availableModels = $models.filter((m) => !(m?.info?.meta?.hidden ?? false));
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
			showModelSelector = false;
		}
	}}
	align="end"
>
	<slot></slot>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[280px] rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if showModelSelector}
				<!-- Model Selector View -->
				<div
					class="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-gray-800"
				>
					<button
						class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
						on:click={() => {
							showModelSelector = false;
						}}
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
								d="M15.75 19.5 8.25 12l7.5-7.5"
							/>
						</svg>
					</button>
					<span class="text-sm font-medium">{$i18n.t('Select Model')}</span>
				</div>

				{#if hasToolCalls}
					<div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
						<label class="flex items-center gap-2 text-xs cursor-pointer">
							<input
								type="checkbox"
								bind:checked={preserveContext}
								class="rounded border-gray-300 dark:border-gray-600"
							/>
							<span class="text-gray-600 dark:text-gray-400">
								{$i18n.t('Keep tool results as context')}
							</span>
						</label>
					</div>
				{/if}

				<div class="max-h-60 overflow-y-auto py-1">
					{#each availableModels as model}
						<DropdownMenu.Item
							class="flex gap-2 items-center px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl {model.id ===
							currentModelId
								? 'bg-gray-50 dark:bg-gray-800'
								: ''}"
							on:click={() => {
								onRegenerateWithModel(model.id, preserveContext);
								show = false;
								showModelSelector = false;
							}}
						>
							{#if model?.info?.meta?.profile_image_url}
								<img
									src={model.info.meta.profile_image_url}
									class="w-5 h-5 rounded-full"
									alt={model.name}
								/>
							{:else}
								<div
									class="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs"
								>
									{model.name?.charAt(0) ?? 'M'}
								</div>
							{/if}
							<span class="truncate flex-1">{model.name ?? model.id}</span>
							{#if model.id === currentModelId}
								<span class="text-xs text-gray-400">{$i18n.t('Current')}</span>
							{/if}
						</DropdownMenu.Item>
					{/each}
				</div>
			{:else}
				<!-- Default Menu View -->
				<div class="py-1.5 px-2.5 flex dark:text-gray-100">
					<input
						type="text"
						id="floating-message-input"
						class="bg-transparent outline-hidden w-full flex-1 text-sm"
						placeholder={$i18n.t('Suggest a change')}
						bind:value={inputValue}
						autocomplete="off"
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								onRegenerate(inputValue);
								show = false;
							}
						}}
					/>

					<div class="ml-2 self-center flex items-center">
						<button
							class="{inputValue !== ''
								? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
								: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1 self-center"
							on:click={() => {
								onRegenerate(inputValue);
								show = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-3.5"
							>
								<path
									fill-rule="evenodd"
									d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					</div>
				</div>
				<hr class="border-gray-50 dark:border-gray-800 my-1 mx-2" />

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						onRegenerate();
						show = false;
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						aria-hidden="true"
						stroke="currentColor"
						class="w-4 h-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
						/>
					</svg>
					<div class="flex items-center">{$i18n.t('Try Again')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						onRegenerate($i18n.t('Add Details'));
					}}
				>
					<LineSpace strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Add Details')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						onRegenerate($i18n.t('More Concise'));
					}}
				>
					<LineSpaceSmaller strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('More Concise')}</div>
				</DropdownMenu.Item>

				<hr class="border-gray-50 dark:border-gray-800 my-1 mx-2" />

				<!-- Re-run with Different Model option -->
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={(e) => {
						e.preventDefault();
						showModelSelector = true;
					}}
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
					<div class="flex items-center flex-1">{$i18n.t('Re-run with Different Model')}</div>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="w-4 h-4 text-gray-400"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
					</svg>
				</DropdownMenu.Item>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
