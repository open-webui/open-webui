<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import Modal from '$lib/components/common/Modal.svelte';
	import { getInterfaceDefaults, setInterfaceDefaults } from '$lib/apis/configs';
	import InterfaceSettings from '$lib/components/chat/Settings/Interface.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let loading = false;
	let saving = false;

	// Create a local store to hold admin defaults
	let adminDefaults = writable({});

	// Custom saveSettings function that updates local adminDefaults instead of user settings
	const saveAdminSettings = async (updates: object) => {
		adminDefaults.update((current) => ({
			...current,
			...updates
		}));
	};

	const loadDefaults = async () => {
		loading = true;
		try {
			const defaults = await getInterfaceDefaults(localStorage.token);
			adminDefaults.set(defaults);
		} catch (error) {
			console.error('Error loading interface defaults:', error);
			toast.error($i18n.t('Failed to load interface defaults'));
		} finally {
			loading = false;
		}
	};

	const handleSave = async () => {
		saving = true;
		try {
			const currentDefaults = $adminDefaults;
			await setInterfaceDefaults(localStorage.token, currentDefaults);
			toast.success($i18n.t('Interface defaults saved successfully'));
			show = false;
		} catch (error) {
			console.error('Error saving interface defaults:', error);
			toast.error($i18n.t('Failed to save interface defaults'));
		} finally {
			saving = false;
		}
	};

	const handleCancel = () => {
		show = false;
	};

	$: if (show) {
		loadDefaults();
	}
</script>

<Modal size="xl" bind:show>
	<div class="text-gray-700 dark:text-gray-100">
		<div class="flex justify-between dark:text-gray-300 px-4 md:px-4.5 pt-4.5 pb-2.5">
			<div class="text-lg font-medium self-center">
				{$i18n.t('Configure Global Interface Defaults')}
			</div>
			<button
				aria-label={$i18n.t('Close modal')}
				class="self-center"
				on:click={handleCancel}
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

		<div class="text-xs text-gray-500 dark:text-gray-400 px-4 pb-3">
			{$i18n.t(
				"These settings will be used as defaults for all users who haven't customized their interface settings."
			)}
		</div>

		<div class="px-4 pb-4" style="max-height: calc(100vh - 300px); overflow-y: auto;">
			{#if !loading}
				<!-- Pass adminDefaults to Interface component as initialSettings -->
				{#key $adminDefaults}
					<div class="interface-defaults-wrapper">
						<InterfaceSettings initialSettings={$adminDefaults} saveSettings={saveAdminSettings} />
					</div>
				{/key}
			{:else}
				<div class="flex justify-center items-center py-8">
					<div
						class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"
					></div>
				</div>
			{/if}
		</div>

		<!-- Modal footer with Save/Cancel buttons -->
		<div
			class="flex justify-end gap-2 px-4 py-3 border-t dark:border-gray-800 bg-gray-50 dark:bg-gray-900"
		>
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
				on:click={handleCancel}
				disabled={saving}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-white bg-gray-900 dark:bg-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={handleSave}
				disabled={saving || loading}
			>
				{#if saving}
					<div class="flex items-center gap-2">
						<div
							class="animate-spin rounded-full h-4 w-4 border-b-2 border-white dark:border-gray-900"
						></div>
						{$i18n.t('Saving...')}
					</div>
				{:else}
					{$i18n.t('Save Defaults')}
				{/if}
			</button>
		</div>
	</div>
</Modal>

<style>
	/* Override the form styling from Interface.svelte since we're wrapping it in a modal */
	:global(.interface-defaults-wrapper form) {
		height: auto !important;
		display: block !important;
	}

	/* Hide the submit button from the original Interface component */
	:global(.interface-defaults-wrapper form button[type='submit']) {
		display: none !important;
	}
</style>
