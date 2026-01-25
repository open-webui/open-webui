<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import {
		getChannelWebhooks,
		createChannelWebhook,
		updateChannelWebhook,
		deleteChannelWebhook
	} from '$lib/apis/channels';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import WebhookItem from './WebhookItem.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let channel = null;

	let webhooks = [];
	let isLoading = false;
	let isSaving = false;

	let showDeleteConfirmDialog = false;
	let selectedWebhookId = null;

	// Track pending changes from child components
	let pendingChanges: { [webhookId: string]: { name: string; profile_image_url: string } } = {};

	const loadWebhooks = async () => {
		isLoading = true;
		try {
			webhooks = await getChannelWebhooks(localStorage.token, channel.id);
		} catch {
			webhooks = [];
		}
		isLoading = false;
	};

	const createHandler = async () => {
		isSaving = true;
		try {
			const newWebhook = await createChannelWebhook(localStorage.token, channel.id, {
				name: 'New Webhook'
			});
			if (newWebhook) {
				webhooks = [...webhooks, newWebhook];
				selectedWebhookId = newWebhook.id;
			}
		} catch (error) {
			toast.error(`${error}`);
		}
		isSaving = false;
	};

	const saveHandler = async () => {
		isSaving = true;
		try {
			for (const [webhookId, changes] of Object.entries(pendingChanges)) {
				await updateChannelWebhook(localStorage.token, channel.id, webhookId, changes);
			}
			pendingChanges = {};
			await loadWebhooks();
			toast.success($i18n.t('Saved'));
		} catch (error) {
			toast.error(`${error}`);
		}
		isSaving = false;
	};

	const deleteHandler = async () => {
		if (!selectedWebhookId) return;

		try {
			await deleteChannelWebhook(localStorage.token, channel.id, selectedWebhookId);
			webhooks = webhooks.filter((webhook) => webhook.id !== selectedWebhookId);
			toast.success($i18n.t('Deleted'));
		} catch (error) {
			toast.error(`${error}`);
		}

		selectedWebhookId = null;
		showDeleteConfirmDialog = false;
	};

	$: if (show && channel) {
		loadWebhooks();
		selectedWebhookId = null;
		pendingChanges = {};
	}
</script>

<ConfirmDialog bind:show={showDeleteConfirmDialog} on:confirm={deleteHandler} />

{#if channel}
	<Modal size="sm" bind:show>
		<div>
			<div class="flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
				<div class="flex w-full justify-between items-center mr-3">
					<div class="self-center text-base flex gap-1.5 items-center">
						<div>{$i18n.t('Webhooks')}</div>
						<span class="text-sm text-gray-500">{webhooks.length}</span>
					</div>

					<button
						type="button"
						class="px-3 py-1.5 gap-1 rounded-xl bg-gray-100/50 dark:bg-gray-850/50 text-black dark:text-white transition font-medium text-xs flex items-center justify-center"
						on:click={createHandler}
						disabled={isSaving}
					>
						<Plus className="size-3.5" />
						<span>{$i18n.t('New Webhook')}</span>
					</button>
				</div>

				<button class="self-center" on:click={() => (show = false)}>
					<XMark className="size-5" />
				</button>
			</div>

			<div class="flex flex-col w-full px-4 pb-4 dark:text-gray-200">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						saveHandler();
					}}
				>
					{#if isLoading}
						<div class="flex justify-center py-10">
							<Spinner className="size-5" />
						</div>
					{:else if webhooks.length > 0}
						<div class="w-full py-2">
							{#each webhooks as webhook (webhook.id)}
								<WebhookItem
									{webhook}
									expanded={selectedWebhookId === webhook.id}
									onClick={() => {
										selectedWebhookId = selectedWebhookId === webhook.id ? null : webhook.id;
									}}
									onDelete={() => {
										showDeleteConfirmDialog = true;
									}}
									onUpdate={(changes) => {
										pendingChanges[webhook.id] = changes;
									}}
								/>
							{/each}
						</div>
					{:else}
						<div class="text-gray-500 text-xs text-center py-8 px-10">
							{$i18n.t('No webhooks yet')}
						</div>
					{/if}

					<div class="flex justify-end text-sm font-medium gap-1.5">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {isSaving
								? 'cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={isSaving}
						>
							{$i18n.t('Save')}
							{#if isSaving}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</Modal>
{/if}
