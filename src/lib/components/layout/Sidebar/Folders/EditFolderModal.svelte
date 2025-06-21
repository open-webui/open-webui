<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import { user } from '$lib/stores';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');
	export let show = false;
	export let folder = { id: '', name: '', system_prompt: '' };
	let currentName = '';
	let currentSystemPrompt = '';
	let loading = false;
	let initialized = false;
	// Initialize values once when modal opens
	$: if (show && folder && !initialized) {
		currentName = folder.name || '';
		currentSystemPrompt = folder.system_prompt || '';
		initialized = true;
	}
	// Reset when modal closes
	$: if (!show) {
		initialized = false;
		loading = false;
	}
	// Auto-focus name input when modal opens
	$: if (show && initialized) {
		setTimeout(() => {
			document.getElementById('folderName')?.focus();
		}, 150);
	}
	const handleSubmit = () => {
		if (!currentName.trim()) return;
		loading = true;
		dispatch('saveFolder', {
			id: folder.id,
			name: currentName.trim(),
			system_prompt: currentSystemPrompt.trim() || null
		});
	};
	const handleClose = () => {
		loading = false;
		initialized = false;
		dispatch('close');
	};
</script>

<Modal bind:show on:close={handleClose} size="md">
	<div>
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-1.5">
			<div class="text-lg font-medium self-center font-primary">
				{$i18n.t('Edit Folder')}
			</div>
			<button
				class="self-center p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full"
				on:click={handleClose}
				aria-label={$i18n.t('Close')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<form
			class="flex flex-col w-full px-6 pb-6 md:space-y-5 dark:text-gray-200"
			on:submit|preventDefault={handleSubmit}
		>
			<div class="px-1 space-y-4">
				<div>
					<label for="folderName" class="block mb-1 text-xs text-gray-500">
						{$i18n.t('Folder Name')}
					</label>
					<input
						id="folderName"
						class="w-full text-sm bg-transparent placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none border border-gray-300 dark:border-gray-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500"
						type="text"
						bind:value={currentName}
						placeholder={$i18n.t('Enter folder name')}
						required
					/>
				</div>

				{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
					<div>
						<label for="systemPrompt" class="block mb-1 text-xs text-gray-500">
							{$i18n.t('System Prompt (Optional)')}
						</label>
						<Textarea
							id="systemPrompt"
							bind:value={currentSystemPrompt}
							placeholder={$i18n.t('Enter a system prompt for all chats in this folder...')}
							className="w-full text-sm bg-transparent placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none border border-gray-300 dark:border-gray-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 min-h-[120px] resize-y"
							rows={5}
						/>
					</div>
				{/if}
			</div>
			<div class="flex justify-end items-center pt-4 text-sm font-medium gap-2">
				<button
					type="button"
					class="px-3.5 py-1.5 text-sm font-medium dark:bg-gray-700 dark:hover:bg-gray-600 bg-gray-100 hover:bg-gray-200 text-black dark:text-white transition rounded-full"
					on:click={handleClose}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full flex items-center"
					type="submit"
					disabled={loading}
				>
					{#if loading}
						<div class="mr-2 self-center">
							<svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
								<circle
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="2"
									fill="none"
									stroke-linecap="round"
									stroke-dasharray="32"
									stroke-dashoffset="32"
								/>
							</svg>
						</div>
					{/if}
					{$i18n.t('Save')}
				</button>
			</div>
		</form>
	</div>
</Modal>
