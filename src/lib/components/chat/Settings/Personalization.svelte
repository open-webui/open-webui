<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ManageModal from './Personalization/ManageModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let showManageModal = false;

	// Memory Settings
	let enableMemory = false;
	let enableMemoryRecall = true;
	let injectProfileInfo = false;
	let enableAutomaticMemory = false;
	let memoryExtractionPrompt = '';

	const defaultMemoryExtractionPrompt = 'Extract key facts and user preferences...';

	onMount(async () => {
		enableMemory = $settings?.memory ?? false;
		enableMemoryRecall = $settings?.memoryRecall ?? true;
		injectProfileInfo = $settings?.injectProfileInfo ?? false;
		enableAutomaticMemory = $settings?.automaticMemory ?? false;
		memoryExtractionPrompt = $settings?.memoryExtractionPrompt ?? '';
	});
</script>

<ManageModal bind:show={showManageModal} />

<form
	id="tab-personalization"
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<div class="py-1 overflow-y-scroll max-h-[28rem] md:max-h-full">
		<div>
			<!-- Memory Toggle -->
			<div class="flex items-center justify-between mb-1">
				<Tooltip
					content={$i18n.t(
						'This is an experimental feature, it may not function as expected and is subject to change at any time.'
					)}
				>
					<div class="text-sm font-medium">
						{$i18n.t('Memory')}

						<span class=" text-xs text-gray-500">({$i18n.t('Experimental')})</span>
					</div>
				</Tooltip>

				<div class="">
					<Switch
						bind:state={enableMemory}
						on:change={async () => {
							saveSettings({ memory: enableMemory });
						}}
					/>
				</div>
			</div>
		</div>

		{#if enableMemory}
			<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">
				<div>
					{$i18n.t(
						"You can personalize your interactions with LLMs by adding memories through the 'Manage' button below, making them more helpful and tailored to you."
					)}
				</div>
			</div>

			<div class="mt-3 mb-1 ml-1">
				<button
					type="button"
					class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
					on:click={() => {
						showManageModal = true;
					}}
				>
					{$i18n.t('Manage')}
				</button>
			</div>

			<!-- Active Memory Recall Toggle -->
			<div class="flex items-center justify-between mt-4">
				<div class="text-sm font-medium">
					{$i18n.t('Active Memory Recall')}
				</div>

				<div class="">
					<Switch
						bind:state={enableMemoryRecall}
						on:change={async () => {
							saveSettings({ memoryRecall: enableMemoryRecall });
						}}
					/>
				</div>
			</div>

			<!-- Inject Profile Info Toggle -->
			<div class="flex items-center justify-between mt-3">
				<Tooltip
					content={$i18n.t(
						'Include your account name, bio, and gender in chat context to help the model personalize responses.'
					)}
				>
					<div class="text-sm font-medium">
						{$i18n.t('Inject Profile Info')}
					</div>
				</Tooltip>

				<div class="">
					<Switch
						bind:state={injectProfileInfo}
						on:change={async () => {
							saveSettings({ injectProfileInfo });
						}}
					/>
				</div>
			</div>

			<!-- Automatic Memory Creation Toggle -->
			<div class="flex items-center justify-between mt-3">
				<div class="text-sm font-medium">
					{$i18n.t('Automatic Memory Creation')}
				</div>

				<div class="">
					<Switch
						bind:state={enableAutomaticMemory}
						on:change={async () => {
							saveSettings({ automaticMemory: enableAutomaticMemory });
						}}
					/>
				</div>
			</div>

			{#if enableAutomaticMemory}
				<div class="mt-2">
					<div class="text-xs text-gray-600 dark:text-gray-400 mb-1.5">
						{$i18n.t('Define the prompt logic used to extract memories from your conversations.')}
					</div>
					<Textarea
						bind:value={memoryExtractionPrompt}
						placeholder={$i18n.t('e.g. Extract key facts and preferences in third-person form...')}
						on:change={() => {
							saveSettings({ memoryExtractionPrompt });
						}}
					/>
				</div>
			{/if}
		{/if}
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
