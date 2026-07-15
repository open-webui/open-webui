<script lang="ts">
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { adminUserCount, config, user } from '$lib/stores';
	import { getContext, onDestroy } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import { getUsers, deleteUserById } from '$lib/apis/users';

	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import EditPencil from '$lib/components/icons/EditPencil.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import EditUserModal from '$lib/components/admin/Users/UserList/EditUserModal.svelte';
	import UserChatsModal from '$lib/components/admin/Users/UserList/UserChatsModal.svelte';
	import AddUserModal from '$lib/components/admin/Users/UserList/AddUserModal.svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Banner from '$lib/components/common/Banner.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import UserPreviewModal from '$lib/components/admin/UserPreviewModal.svelte';

	const i18n = getContext('i18n');

	let page = 1;

	let users = null;
	let total = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let orderBy = 'created_at'; // default sort key
	let direction = 'asc'; // default sort order

	let selectedUser = null;

	let showDeleteConfirmDialog = false;
	let showAddUserModal = false;

	let showUserChatsModal = false;
	let showEditUserModal = false;
	let showUserPreviewModal = false;

	const deleteUserHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		// if the user is deleted and the current page has only one user, go back to the previous page
		if (users.length === 1 && page > 1) {
			page -= 1;
		}

		if (res) {
			getUserList();
		}
	};

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const roleClass = (role) => {
		if (role === 'admin') {
			return 'text-[#4f6f93] dark:text-[#8ba6c6]';
		}
		if (role === 'user') {
			return 'text-[#4f7a5a] dark:text-[#8db395]';
		}
		return 'text-gray-500 dark:text-gray-400';
	};

	const getUserList = async () => {
		try {
			const res = await getUsers(localStorage.token, query, orderBy, direction, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				users = res.users;
				total = res.total;
				adminUserCount.set(total);
			}
		} catch (err) {
			console.error(err);
		}
	};

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				getUserList();
			}
		}, 300);
	};

	$: if (page !== null && orderBy !== null && direction !== null) {
		getUserList();
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		deleteUserHandler(selectedUser.id);
	}}
/>

<AddUserModal
	bind:show={showAddUserModal}
	on:save={async () => {
		getUserList();
	}}
/>

<EditUserModal
	bind:show={showEditUserModal}
	{selectedUser}
	sessionUser={$user}
	on:save={async () => {
		getUserList();
	}}
/>

{#if selectedUser}
	<UserChatsModal bind:show={showUserChatsModal} user={selectedUser} />
{/if}

{#if ($config?.license_metadata?.seats ?? null) !== null && total && total > $config?.license_metadata?.seats}
	<div class=" mt-1 mb-2 text-xs text-red-500">
		<Banner
			className="mx-0"
			banner={{
				type: 'error',
				title: 'License Error',
				content:
					'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
			}}
		/>
	</div>
{/if}

{#if users === null || total === null}
	<div class="my-10">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="pt-0.5 pb-1 sticky top-0 z-10 bg-white dark:bg-gray-900">
		<div class="flex h-8 flex-1 items-center w-full gap-2">
			<div class="flex min-w-0 flex-1 items-center">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					on:input={handleSearchInput}
					aria-label={$i18n.t('Search')}
					placeholder={$i18n.t('Search')}
				/>

				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								handleSearchInput();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<Tooltip content={$i18n.t('Add User')}>
				<button
					class="p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-normal text-sm flex items-center"
					on:click={() => {
						showAddUserModal = !showAddUserModal;
					}}
				>
					<Plus className="size-3.5" />
				</button>
			</Tooltip>
		</div>
	</div>

	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
			<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
				<tr class=" border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
					<th
						scope="col"
						class="px-2.5 py-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('name')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Name')}

							{#if orderBy === 'name'}
								<span class="font-normal"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('role')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Role')}

							{#if orderBy === 'role'}
								<span class="font-normal"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('email')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Email')}

							{#if orderBy === 'email'}
								<span class="font-normal"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th
						scope="col"
						class="px-2.5 py-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('last_active_at')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Last Active')}
							<!-- {$i18n.t('Last Modified')} -->

							{#if orderBy === 'last_active_at'}
								<span class="font-normal"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('created_at')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Created at')}
							{#if orderBy === 'created_at'}
								<span class="font-normal"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th scope="col" class="px-2.5 py-1.5 text-right"></th>
				</tr>
			</thead>
			<tbody class="">
				{#each users as user (user.id)}
					<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
						<td class="px-3 py-1 font-normal text-gray-900 dark:text-white max-w-48">
							<div class="flex items-center gap-2">
								<ProfilePreview {user} side="right" align="center" sideOffset={6}>
									<img
										class="rounded-full w-6 min-w-6 h-6 object-cover flex-shrink-0"
										src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
										alt="user"
										on:error={(e) => {
											e.currentTarget.src = '/favicon.png';
										}}
									/>
								</ProfilePreview>

								<div class="font-normal truncate">{user.name}</div>

								{#if user?.last_active_at && Date.now() / 1000 - user.last_active_at < 180}
									<div>
										<span class="relative flex size-1.5">
											<span
												class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
											></span>
											<span class="relative inline-flex size-1.5 rounded-full bg-green-500"></span>
										</span>
									</div>
								{/if}
							</div>
						</td>
						<td class="px-3 py-1 min-w-[5rem] w-20">
							<button
								class="text-xs font-normal leading-4 capitalize transition {roleClass(user.role)}"
								aria-label={$i18n.t('Change User Role')}
								on:click={() => {
									selectedUser = user;
									showEditUserModal = !showEditUserModal;
								}}
							>
								{$i18n.t(user.role)}
							</button>
						</td>
						<td class=" px-3 py-1 max-w-48 truncate"> {user.email} </td>

						<td class=" px-3 py-1">
							{dayjs(user.last_active_at * 1000).fromNow()}
						</td>

						<td class=" px-3 py-1">
							{dayjs(user.created_at * 1000).format('LL')}
						</td>

						<td class="px-3 py-1 text-right">
							<div class="flex justify-end w-full">
								{#if $config.features.enable_admin_chat_access && user.role !== 'admin'}
									<Tooltip content={$i18n.t('Chats')}>
										<button
											class="self-center w-fit p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
											aria-label={$i18n.t('Chats')}
											on:click={async () => {
												showUserChatsModal = !showUserChatsModal;
												selectedUser = user;
											}}
										>
											<ChatBubbles className="size-3.5" />
										</button>
									</Tooltip>
								{/if}

								{#if user.role !== 'admin'}
									<Tooltip content={$i18n.t('Preview Access')}>
										<button
											class="self-center w-fit p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
											aria-label={$i18n.t('Preview Access')}
											on:click={() => {
												selectedUser = user;
												showUserPreviewModal = true;
											}}
										>
											<Eye className="size-3.5" />
										</button>
									</Tooltip>
								{/if}

								<Tooltip content={$i18n.t('Edit User')}>
									<button
										class="self-center w-fit p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
										aria-label={$i18n.t('Edit User')}
										on:click={async () => {
											showEditUserModal = !showEditUserModal;
											selectedUser = user;
										}}
									>
										<EditPencil className="size-3.5" />
									</button>
								</Tooltip>

								{#if user.role !== 'admin'}
									<Tooltip content={$i18n.t('Delete User')}>
										<button
											class="self-center w-fit p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
											aria-label={$i18n.t('Delete User')}
											on:click={async () => {
												showDeleteConfirmDialog = true;
												selectedUser = user;
											}}
										>
											<Trash className="size-3.5" />
										</button>
									</Tooltip>
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class=" text-gray-500 text-xs mt-1.5 text-right">
		ⓘ {$i18n.t("Click on the user role button to change a user's role.")}
	</div>

	{#if total > 30}
		<Pagination bind:page count={total} perPage={30} />
	{/if}
{/if}

{#if !$config?.license_metadata}
	{#if total > 50}
		<div class="mt-3 mb-3 pb-1 text-gray-700 dark:text-gray-300">
			<div class="max-w-3xl text-xs leading-5">
				<div class="text-gray-900 dark:text-gray-100">
					{$i18n.t('Running Open WebUI for a team?')}
				</div>
				<div class="mt-2 space-y-2">
					<p>
						{$i18n.t(
							'You have more than 50 users, which often means this workspace is supporting organizational use. Open WebUI is free to use as-is, with no restrictions or hidden limits, and we want to keep it that way.'
						)}
					</p>
					<p class="text-gray-500 dark:text-gray-400">
						{$i18n.t(
							'By supporting the project through sponsorship or an enterprise license, you help us stay independent, ship new features faster, improve stability, and grow Open WebUI for the long haul.'
						)}
					</p>
					<p class="text-gray-500 dark:text-gray-400">
						{$i18n.t(
							'Enterprise licenses also include dedicated support, customization options, and more, at a fraction of the cost of building and maintaining this stack internally.'
						)}
					</p>
				</div>

				<div class="mt-2 flex items-center gap-3">
					<a
						class="text-xs text-gray-700 underline transition hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
						href="https://docs.openwebui.com/enterprise"
						target="_blank"
						rel="noreferrer"
					>
						{$i18n.t('Enterprise licensing')}
					</a>
					<a
						class="text-xs text-gray-500 underline transition hover:text-gray-900 dark:text-gray-500 dark:hover:text-gray-100"
						href="https://github.com/sponsors/open-webui"
						target="_blank"
						rel="noreferrer"
					>
						{$i18n.t('Sponsor on GitHub')}
					</a>
				</div>
			</div>
		</div>
	{/if}
{/if}

{#if selectedUser}
	<UserPreviewModal
		bind:show={showUserPreviewModal}
		userId={selectedUser.id}
		userName={selectedUser.name}
	/>
{/if}
