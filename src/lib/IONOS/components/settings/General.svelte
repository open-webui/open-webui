<script lang="ts">
	import type { Readable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Confirm from '$lib/IONOS/components/common/Confirm.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte'
	import {
		deleteAll,
		exportAll,
	} from '$lib/IONOS/services/chats';
	const i18n = getContext<Readable<I18Next>>('i18n');

	let confirmChatDeletion = false;

	async function onExportChats() {
		await exportAll();
	}

	function onDeleteAllChats() {
		confirmChatDeletion = true;
	}

	async function onDeleteChatsConfirmed() {
		try {
			await deleteAll();
			toast.success($i18n.t('All chats successfully deleted.', { ns: 'ionos' }));
			confirmChatDeletion = false;
		} catch (e) {
			console.error(`Error deleting all chats:`, e);
			toast.error($i18n.t('Error deleting all chats.', { ns: 'ionos' }));
		}
	}
</script>

<div class="flex flex-col gap-5 text-sm">
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Export all chats', { ns: 'ionos' })}
		</div>
		<div>
			<Button
				on:click={onExportChats}
				type={ButtonType.secondary}
			>
				{$i18n.t('Export chats', { ns: 'ionos' })}
			</Button>
		</div>
	</div>
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Delete all chats', { ns: 'ionos' })}
		</div>
		<div>
			<Button
				on:click={onDeleteAllChats}
				type={ButtonType.caution}
			>
				{$i18n.t('Delete chats', { ns: 'ionos' })}
			</Button>
		</div>
	</div>
</div>

<Confirm
	title={$i18n.t('Do you want to delete all chats?', { ns: 'ionos' })}
	show={confirmChatDeletion}
	confirmText={$i18n.t('Delete all chats', { ns: 'ionos' })}
	confirmHandler={onDeleteChatsConfirmed}
	cancelHandler={() => { confirmChatDeletion = false; }}
>
	{$i18n.t('This action can not be undone', { ns: 'ionos' })}
</Confirm>
