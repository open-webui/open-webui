<script>
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import { bulkUpdateModelOptions } from '$lib/apis/models';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import DefaultFeatures from '$lib/components/workspace/Models/DefaultFeatures.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let onUpdate = () => {};

	// Capabilities
	let capabilities = {
		vision: true,
		file_upload: true,
		web_search: true,
		image_generation: true,
		code_interpreter: true,
		citations: true,
		status_updates: true,
		usage: undefined,
		builtin_tools: true
	};

	let defaultFeatureIds = [];

	$: availableFeatures = Object.entries(capabilities)
		.filter(
			([key, value]) =>
				['web_search', 'code_interpreter', 'image_generation'].includes(key) && value
		)
		.map(([key, value]) => key);

	let loading = false;
	let showConfirmDialog = false;

	const toggleAll = (type, value) => {
		if (type === 'capabilities') {
			const newCapabilities = { ...capabilities };
			Object.keys(newCapabilities).forEach((key) => {
				newCapabilities[key] = value;
			});
			capabilities = newCapabilities;
		} else if (type === 'defaultFeatures') {
			defaultFeatureIds = value ? availableFeatures : [];
		}
	};

	const submitHandler = async () => {
		showConfirmDialog = true;
	};

	const applyBulkUpdate = async () => {
		loading = true;

		try {
			// Build the update payload
			const payload = {};

			payload.capabilities = capabilities;
			payload.defaultFeatureIds = defaultFeatureIds;

			const res = await bulkUpdateModelOptions(localStorage.token, payload);

			if (res) {
				toast.success(
					$i18n.t('Updated options for {{count}} model(s)', {
						count: res.updated
					})
				);
				onUpdate();
				show = false;
			} else {
				toast.error($i18n.t('Failed to update model options'));
			}
		} catch (e) {
			toast.error($i18n.t('Failed to update model options'));
			console.error(e);
		}

		loading = false;
		showConfirmDialog = false;
	};
</script>

<ConfirmDialog
	title={$i18n.t('Apply to All Models')}
	message={$i18n.t(
		'This will update options for ALL models. Individual models can still override these settings afterward.'
	)}
	bind:show={showConfirmDialog}
	onConfirm={applyBulkUpdate}
/>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Bulk Model Capabilities')}
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

		<div class="flex flex-col w-full px-5 dark:text-gray-200">
			<div class="flex flex-col w-full pb-4">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="px-6 py-4 space-y-6 h-[400px] overflow-y-scroll max-h-[400px] scrollbar-hidden">
						<div class="text-sm text-gray-500 dark:text-gray-400 mb-3">
							{$i18n.t(
								'Set default capabilities for all models. Individual models can still override these settings.'
							)}
						</div>

						<div>
							<div class="flex justify-between items-center mb-2">
								<div class="text-xs font-medium text-gray-500 uppercase">
									{$i18n.t('Capabilities')}
								</div>
								<div class="flex gap-2 text-xs font-medium">
									<button
										class="text-gray-900 dark:text-gray-100 items-center justify-center hover:underline"
										type="button"
										on:click={() => toggleAll('capabilities', true)}>{$i18n.t('Select All')}</button
									>
									<button
										class="text-gray-900 dark:text-gray-100 items-center justify-center hover:underline"
										type="button"
										on:click={() => toggleAll('capabilities', false)}>{$i18n.t('None')}</button
									>
								</div>
							</div>
							<Capabilities bind:capabilities showTitle={false} />
						</div>

						{#if availableFeatures.length > 0}
							<!-- remove mt-3 since parent has space-y-6 -->
							<div>
								<div class="flex justify-between items-center mb-2">
									<div class="text-xs font-medium text-gray-500 uppercase">
										{$i18n.t('Default Features')}
									</div>
									<div class="flex gap-2 text-xs font-medium">
										<button
											class="text-gray-900 dark:text-gray-100 items-center justify-center hover:underline"
											type="button"
											on:click={() => toggleAll('defaultFeatures', true)}
											>{$i18n.t('Select All')}</button
										>
										<button
											class="text-gray-900 dark:text-gray-100 items-center justify-center hover:underline"
											type="button"
											on:click={() => toggleAll('defaultFeatures', false)}>{$i18n.t('None')}</button
										>
									</div>
								</div>
								<DefaultFeatures
									bind:featureIds={defaultFeatureIds}
									{availableFeatures}
									showTitle={false}
								/>
							</div>
						{/if}
					</div>

					<div
						class="flex justify-end pt-2 text-sm font-medium gap-1.5"
					>
						<button
							class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-950 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
							type="button"
							on:click={() => {
								show = false;
							}}
						>
							{$i18n.t('Cancel')}
						</button>

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Apply to All Models')}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
