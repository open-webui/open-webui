<script lang="ts">
	import { toast } from 'svelte-sonner';
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte'
	import Confirm from '$lib/IONOS/components/common/Confirm.svelte';
	import LoadingCover from '$lib/IONOS/components/common/LoadingCover.svelte';
	import { config, user } from '$lib/stores';
	import { resetPassword, deleteAccount } from '$lib/IONOS/services/account';
	const i18n = getContext<Readable<I18Next>>('i18n');

	const isAccountDeletionAllowedBackend = $config?.features?.ionos_user_account_deletion_allowed ?? false;
	const isAccountDeletionAllowedFrontend = localStorage.accountDeletionAllowedOverride === 'true';

	let confirmAccountDeletion = false;
	let loading = false;

	async function onDeleteAccountConfirmed() {
		try {
			confirmAccountDeletion = false;
			loading = true;
			await deleteAccount();
		} catch(e) {
			toast.error($i18n.t('Deleting your account failed.', { ns: 'ionos' }));
		}
	}
</script>

<div class="flex flex-col gap-5 text-sm">
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Email', { ns: 'ionos' })}
		</div>
		<div>
			{$user.email}
		</div>
	</div>
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Reset password', { ns: 'ionos' })}
		</div>
		<div>
			<Button
				on:click={() => resetPassword()}
				type={ButtonType.secondary}>
				{$i18n.t('Reset password', { ns: 'ionos' })}
			</Button>
		</div>
	</div>
	{#if isAccountDeletionAllowedFrontend || isAccountDeletionAllowedBackend}
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Delete account', { ns: 'ionos' })}
		</div>
		<div>
			<Button
				on:click={() => { confirmAccountDeletion = true; }}
				type={ButtonType.caution}>
				{$i18n.t('Delete account', { ns: 'ionos' })}
			</Button>
		</div>
	</div>
	{/if}
</div>

{#if loading}
	<LoadingCover />
{/if}

<Confirm
	title={$i18n.t('Do you want to delete your account?', { ns: 'ionos' })}
	show={confirmAccountDeletion}
	confirmText={$i18n.t('Delete my account', { ns: 'ionos' })}
	confirmHandler={onDeleteAccountConfirmed}
	cancelHandler={() => { confirmAccountDeletion = false; }}
>
	<p class="my-3">
		{$i18n.t('All your chats and uploaded documents will be lost.', { ns: 'ionos' })}
	</p>

	<p class="my-3">
		{$i18n.t('This action can not be undone.', { ns: 'ionos' })}
	</p>
</Confirm>
