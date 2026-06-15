<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { updateFolderAccessById } from '$lib/apis/folders';
	import { user } from '$lib/stores';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group';
		principal_id: string;
		permission: 'read' | 'write';
	};

	export let show = false;
	export let folder: any = null;

	let accessGrants: AccessGrant[] = [];

	$: if (folder) {
		accessGrants = folder.access_grants ?? [];
	}

	const handleAccessChange = async () => {
		if (!folder) return;
		try {
			const res = await updateFolderAccessById(localStorage.token, folder.id, accessGrants);
			if (res) {
				accessGrants = res.access_grants ?? accessGrants;
			}
		} catch (e) {
			console.error('Failed to update folder access', e);
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-3 pb-1">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Share')}: {folder?.name ?? ''}
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

		<div class="w-full px-5 pb-4 dark:text-white">
			<AccessControl
				bind:accessGrants
				onChange={handleAccessChange}
				accessRoles={['read', 'write']}
				share={$user?.role === 'admin' || $user?.permissions?.sharing?.folders}
				sharePublic={false}
				shareUsers={$user?.role === 'admin' || $user?.permissions?.access_grants?.allow_users}
			/>
		</div>
	</div>
</Modal>
