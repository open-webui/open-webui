<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { removeMembersById } from '$lib/apis/channels';

	import Spinner from '$lib/components/common/Spinner.svelte';
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

	const init = () => {};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

{#if channel}
	<AddMembersModal bind:show={showAddMembersModal} {channel} {onUpdate} />
	<Modal size="sm" bind:show>
		<div>
			<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
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
					class="self-center"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-5'} />
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
								onAdd={channel?.type === 'group' && channel?.is_manager
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
