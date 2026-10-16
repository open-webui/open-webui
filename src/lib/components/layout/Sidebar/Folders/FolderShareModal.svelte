<script lang="ts">
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	const i18n = getContext<Writable<i18nType>>('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import XMark from '../icons/XMark.svelte';
	import { getFolderById, updateFolderAccessById } from '$lib/apis/folders';
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
	let loading = false;
	let shareMode: 'continue' | null = null;

	// Fetch fresh folder data (with access_grants) when modal opens
	$: if (show && folder?.id) {
		loadAccessGrants();
	}

	const loadAccessGrants = async () => {
		loading = true;
		try {
			const freshFolder = await getFolderById(localStorage.token, folder.id);
			if (freshFolder) {
				accessGrants = freshFolder.access_grants ?? [];
				shareMode = freshFolder.data?.share_mode ?? null;
			}
		} catch (e) {
			toast.error(`${e}`);
			accessGrants = folder?.access_grants ?? [];
			shareMode = folder?.data?.share_mode ?? null;
		} finally {
			loading = false;
		}
	};

	const handleAccessChange = async () => {
		if (!folder || loading) return;
		loading = true;
		try {
			const res = await updateFolderAccessById(
				localStorage.token,
				folder.id,
				accessGrants,
				shareMode
			);
			if (res) {
				accessGrants = res.access_grants ?? accessGrants;
				toast.success($i18n.t('Saved'));
			}
		} catch (e) {
			toast.error(`${e}`);
			await loadAccessGrants();
		} finally {
			loading = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-3 pb-1">
			<div class=" text-sm self-center">
				{$i18n.t('Access')}: {folder?.name ?? ''}
			</div>
			<button
				aria-label={$i18n.t('Close')}
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="w-full px-5 pb-4 dark:text-white" inert={loading} aria-busy={loading}>
			<AccessControl
				bind:accessGrants
				labels={{
					private: $i18n.t('Restricted'),
					empty: folder?.parent_id ? $i18n.t('No direct access grants.') : undefined
				}}
				onChange={handleAccessChange}
				accessRoles={['read', 'write']}
				defaultPermission="write"
				share={$user?.role === 'admin' || $user?.permissions?.sharing?.folders}
				sharePublic={false}
				shareUsers={$user?.role === 'admin' || $user?.permissions?.access_grants?.allow_users}
				allowGroups={$user?.role === 'admin' ||
					($user?.permissions?.access_grants?.allow_groups ?? true)}
			>
				{#if folder?.parent_id}
					<p class="text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Access granted to parent folders also applies here.')}
					</p>
				{/if}
				<label class="flex w-full items-center justify-between mt-3 mb-1 text-xs">
					<span>{$i18n.t('Sharing mode')}</span>
					<select
						class="bg-transparent text-xs outline-none"
						bind:value={shareMode}
						disabled={loading}
						on:change={handleAccessChange}
					>
						<option value={null}>{$i18n.t('Clone only')}</option>
						<option value="continue">{$i18n.t('Allow replies')}</option>
					</select>
				</label>
			</AccessControl>
		</div>
	</div>
</Modal>
