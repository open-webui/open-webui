<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext<any>('i18n');

	import { config, user } from '$lib/stores';
	import type { App } from '$lib/apis/apps';
	import { removeMembersById, getChannelAppsById, removeAppFromChannel } from '$lib/apis/channels';

	import Modal from '$lib/components/common/Modal.svelte';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Hashtag from '../icons/Hashtag.svelte';
	import Lock from '../icons/Lock.svelte';
	import UserList from './ChannelInfoModal/UserList.svelte';
	import AddMembersModal from './ChannelInfoModal/AddMembersModal.svelte';

	export let show = false;
	export let channel: any = null;

	export let onUpdate = () => {};

	let showAddMembersModal = false;
	let joinedApps: App[] = [];
	$: canManage =
		channel?.type !== 'dm' &&
		(channel?.is_manager || $user?.role === 'admin' || channel?.user_id === $user?.id);
	const updateMembers = async () => {
		await init();
		onUpdate();
	};
	const removeAppHandler = async (appId: string) => {
		try {
			await removeAppFromChannel(localStorage.token, channel.id, appId);
			await updateMembers();
		} catch (error) {
			toast.error(`${error}`);
		}
	};
	const submitHandler = async () => {};

	const hasPublicReadGrant = (grants: any) =>
		Array.isArray(grants) &&
		grants.some(
			(grant) =>
				grant?.principal_type === 'user' &&
				grant?.principal_id === '*' &&
				grant?.permission === 'read'
		);

	const isPublicChannel = (channel: any): boolean => {
		if (channel?.type === 'group') {
			if (typeof channel?.is_private === 'boolean') {
				return !channel.is_private;
			}
			return hasPublicReadGrant(channel?.access_grants);
		}
		return hasPublicReadGrant(channel?.access_grants);
	};

	const removeMemberHandler = async (userId) => {
		const res = await removeMembersById(localStorage.token, channel.id, {
			user_ids: [userId]
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Member removed successfully'));
			onUpdate();
		} else {
			toast.error($i18n.t('Failed to remove member'));
		}
	};

	const init = async () => {
		joinedApps = [];
		if (show && channel?.type !== 'dm' && $config?.features?.enable_apps) {
			joinedApps = await getChannelAppsById(localStorage.token, channel.id).catch((error) => {
				toast.error(`${error}`);
				return [];
			});
		}
	};

	$: if (show) {
		init();
	}
</script>

{#if channel}
	<AddMembersModal
		bind:show={showAddMembersModal}
		{channel}
		{joinedApps}
		onUpdate={updateMembers}
	/>
	<Modal size="sm" bind:show>
		<div>
			<div class=" flex justify-between dark:text-gray-100 px-4 pt-3 mb-1">
				<div class="self-center text-base">
					<div class="flex items-center gap-0.5 shrink-0">
						{#if channel?.type === 'dm'}
							<div class=" text-left self-center overflow-hidden w-full line-clamp-1 flex-1">
								{$i18n.t('Direct Message')}
							</div>
						{:else}
							<div class=" size-4 justify-center flex items-center">
								{#if isPublicChannel(channel)}
									<Hashtag className="size-3.5" strokeWidth="2.5" />
								{:else}
									<Lock className="size-5.5" strokeWidth="2" />
								{/if}
							</div>

							<div class=" text-left self-center overflow-hidden w-full line-clamp-1 flex-1">
								{channel.name}
							</div>
						{/if}
					</div>
				</div>
				<button
					class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-4'} />
				</button>
			</div>

			<div class="flex flex-col md:flex-row w-full px-3 pb-4 md:space-x-4 dark:text-gray-200">
				<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
					<form
						class="flex flex-col w-full"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						<div class="flex flex-col w-full h-full pb-2">
							<UserList
								{channel}
								apps={joinedApps}
								onRemoveApp={canManage ? removeAppHandler : null}
								onAdd={canManage && (channel?.type === 'group' || $config?.features?.enable_apps)
									? () => {
											showAddMembersModal = true;
										}
									: null}
								onRemove={channel?.type === 'group' && channel?.is_manager
									? (userId) => {
											removeMemberHandler(userId);
										}
									: null}
								search={channel?.type !== 'dm'}
								sort={channel?.type !== 'dm'}
							/>
						</div>
					</form>
				</div>
			</div>
		</div>
	</Modal>
{/if}
