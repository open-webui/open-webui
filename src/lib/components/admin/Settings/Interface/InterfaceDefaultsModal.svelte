<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { getInterfaceDefaults, setInterfaceDefaults } from '$lib/apis/configs';
	import InterfaceSettings from '$lib/components/chat/Settings/Interface.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let loading = false;
	let saving = false;
	let adminDefaults: Record<string, any> = {};

	const saveAdminSettings = async (updates: object) => {
		adminDefaults = { ...adminDefaults, ...updates };
	};

	const loadDefaults = async () => {
		loading = true;
		try {
			adminDefaults = await getInterfaceDefaults(localStorage.token);
		} catch (error) {
			console.error('Error loading interface defaults:', error);
			toast.error($i18n.t('Failed to load interface defaults'));
		} finally {
			loading = false;
		}
	};

	// Prepare settings for backend - normalize chatDirection and filter nulls
	const prepareForBackend = (settings: any): object => {
		const result = { ...settings };

		if (result.chatDirection) {
			result.chatDirection = result.chatDirection.toLowerCase();
		}

		return Object.fromEntries(
			Object.entries(result).filter(([_, v]) => v !== undefined && v !== null)
		);
	};

	const submitHandler = async () => {
		saving = true;
		try {
			await setInterfaceDefaults(localStorage.token, prepareForBackend(adminDefaults));
			toast.success($i18n.t('Interface defaults saved successfully'));
			show = false;
		} catch (error) {
			console.error('Error saving interface defaults:', error);
			toast.error($i18n.t('Failed to save interface defaults'));
		} finally {
			saving = false;
		}
	};

	$: if (show) {
		loadDefaults();
	}
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Interface Defaults')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				{$i18n.t(
					"These settings will be used as defaults for all users who haven't customized their interface settings."
				)}
			</div>

			{#if !loading}
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="interface-defaults-wrapper">
						<InterfaceSettings initialSettings={adminDefaults} saveSettings={saveAdminSettings} />
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {saving
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={saving}
						>
							{$i18n.t('Save')}

							{#if saving}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			{:else}
				<div class="flex justify-center items-center py-8">
					<Spinner className="size-5" />
				</div>
			{/if}
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
