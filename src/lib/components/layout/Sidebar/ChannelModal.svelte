<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import { createNewChannel, deleteChannelById } from '$lib/apis/channels';
	import { user } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MemberSelector from '$lib/components/workspace/common/MemberSelector.svelte';
	import Visibility from '$lib/components/workspace/common/Visibility.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let show = false;
	export let onSubmit: Function = () => {};
	export let onUpdate: Function = () => {};

	export let channel = null;
	export let edit = false;

	let channelTypes = ['group', 'dm'];
	let type = '';
	let name = '';

	let isPrivate = null;
	let accessControl = {};

	let groupIds = [];
	let userIds = [];

	let loading = false;

	$: if (name) {
		name = name.replace(/\s/g, '-').toLocaleLowerCase();
	}

	$: onTypeChange(type);

	const onTypeChange = (type) => {
		if (type === 'group') {
			if (isPrivate === null) {
				isPrivate = true;
			}
		} else {
			isPrivate = null;
		}
	};

	const submitHandler = async () => {
		loading = true;
		if (name.length > 128) {
			toast.error($i18n.t('Channel name must be less than 128 characters'));
			loading = false;
			return;
		}

		await onSubmit({
			type: type,
			name: name.replace(/\s/g, '-'),
			is_private: type === 'group' ? isPrivate : null,
			access_control: type === '' ? accessControl : {},
			group_ids: groupIds,
			user_ids: userIds
		});
		show = false;
		loading = false;
	};

	const init = () => {
		if ($user?.role === 'admin') {
			channelTypes = ['', 'group', 'dm'];
		} else {
			channelTypes = ['group', 'dm'];
		}

		type = channel?.type ?? channelTypes[0];

		if (channel) {
			name = channel?.name ?? '';
			isPrivate = channel?.is_private ?? null;
			accessControl = channel.access_control;
			userIds = channel?.user_ids ?? [];
		}
	};

	$: if (show) {
		init();
	} else {
		resetHandler();
	}

	let showDeleteConfirmDialog = false;

	const deleteHandler = async () => {
		showDeleteConfirmDialog = false;

		const res = await deleteChannelById(localStorage.token, channel.id).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success($i18n.t('Channel deleted successfully'));
			onUpdate();

			if ($page.url.pathname === `/channels/${channel.id}`) {
				goto('/');
			}
		}

		show = false;
	};

	const resetHandler = () => {
		type = '';
		name = '';
		accessControl = {};
		userIds = [];
		loading = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Channel')}
				{:else}
					{$i18n.t('Create Channel')}
				{/if}
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

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					{#if !edit}
						<div class="flex flex-col w-full mt-2 mb-1">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Channel Type')}</div>

							<div class="flex-1">
								<Tooltip
									content={type === 'dm'
										? $i18n.t('A private conversation between you and selected users')
										: type === 'group'
											? $i18n.t('A collaboration channel where people join as members')
											: $i18n.t(
													'A discussion channel where access is controlled by groups and permissions'
												)}
									placement="top-start"
								>
									<select
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										bind:value={type}
									>
										{#each channelTypes as channelType, channelTypeIdx (channelType)}
											<option value={channelType} selected={channelTypeIdx === 0}>
												{#if channelType === 'group'}
													{$i18n.t('Group Channel')}
												{:else if channelType === 'dm'}
													{$i18n.t('Direct Message')}
												{:else if channelType === ''}
													{$i18n.t('Channel')}
												{/if}
											</option>
										{/each}
									</select>
								</Tooltip>
							</div>
						</div>
					{/if}

					<div class=" text-gray-300 dark:text-gray-700 text-xs">
						{#if type === ''}
							{$i18n.t('Discussion channel where access is based on groups and permissions')}
						{:else if type === 'group'}
							{$i18n.t('Collaboration channel where people join as members')}
						{:else if type === 'dm'}
							{$i18n.t('Private conversation between selected users')}
						{/if}
					</div>

					<div class="flex flex-col w-full mt-2">
						<div class=" mb-1 text-xs text-gray-500">
							{$i18n.t('Channel Name')}
							<span class="text-xs text-gray-200 dark:text-gray-800 ml-0.5"
								>{type === 'dm' ? `${$i18n.t('Optional')}` : ''}</span
							>
						</div>

						<div class="flex-1">
							<input
								class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
								type="text"
								bind:value={name}
								placeholder={`${$i18n.t('new-channel')}`}
								autocomplete="off"
								required={type !== 'dm'}
								max="100"
							/>
						</div>
					</div>

					{#if type !== 'dm'}
						<div class="-mx-2 mb-1 mt-2.5 px-2">
							{#if type === ''}
								<AccessControl bind:accessControl accessRoles={['read', 'write']} />
							{:else if type === 'group'}
								<Visibility
									state={isPrivate ? 'private' : 'public'}
									onChange={(value) => {
										if (value === 'private') {
											isPrivate = true;
										} else {
											isPrivate = false;
										}
										console.log(value, isPrivate);
									}}
								/>
							{/if}
						</div>
					{/if}

					{#if ['dm'].includes(type)}
						<div class="">
							<MemberSelector bind:userIds includeGroups={false} />
						</div>
					{/if}

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-black/90 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{#if edit}
								{$i18n.t('Update')}
							{:else}
								{$i18n.t('Create')}
							{/if}

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

<DeleteConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t('Are you sure you want to delete this channel?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		deleteHandler();
	}}
/>
