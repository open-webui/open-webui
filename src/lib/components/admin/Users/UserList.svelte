<script>
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';

	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import EditUserModal from '$lib/components/admin/Users/UserList/EditUserModal.svelte';
	import UserChatsModal from '$lib/components/admin/Users/UserList/UserChatsModal.svelte';
	import AddUserModal from '$lib/components/admin/Users/UserList/AddUserModal.svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import About from '$lib/components/chat/Settings/About.svelte';
	import Banner from '$lib/components/common/Banner.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	const i18n = getContext('i18n');

	export let users = [];

	let search = '';
	let selectedUser = null;

	let page = 1;

	let showDeleteConfirmDialog = false;
	let showAddUserModal = false;

	let showUserChatsModal = false;
	let showEditUserModal = false;

	const updateRoleHandler = async (id, role) => {
		const res = await updateUserRole(localStorage.token, id, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	const deleteUserHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	let sortKey = 'created_at'; // default sort key
	let sortOrder = 'asc'; // default sort order

	function setSortKey(key) {
		if (sortKey === key) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortOrder = 'asc';
		}
	}

	let filteredUsers;

	$: filteredUsers = users
		.filter((user) => {
			if (search === '') {
				return true;
			} else {
				let name = user.name.toLowerCase();
				let email = user.email.toLowerCase();
				const query = search.toLowerCase();
				return name.includes(query) || email.includes(query);
			}
		})
		.sort((a, b) => {
			if (a[sortKey] < b[sortKey]) return sortOrder === 'asc' ? -1 : 1;
			if (a[sortKey] > b[sortKey]) return sortOrder === 'asc' ? 1 : -1;
			return 0;
		})
		.slice((page - 1) * 20, page * 20);
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		deleteUserHandler(selectedUser.id);
	}}
/>

{#key selectedUser}
	<EditUserModal
		bind:show={showEditUserModal}
		{selectedUser}
		sessionUser={$user}
		on:save={async () => {
			users = await getUsers(localStorage.token);
		}}
	/>
{/key}

<AddUserModal
	bind:show={showAddUserModal}
	on:save={async () => {
		users = await getUsers(localStorage.token);
	}}
/>
<UserChatsModal bind:show={showUserChatsModal} user={selectedUser} />

{#if ($config?.license_metadata?.seats ?? null) !== null && users.length > $config?.license_metadata?.seats}
	<div class="mb-4">
		<Banner
			className="mx-0"
			banner={{
				type: 'error',
				title: 'License Error',
				content:
					'Exceeded the number of seats in your license. Please contact support to increase the number of seats.',
				dismissable: true
			}}
		/>
	</div>
{/if}

<div class="mb-6 flex flex-col gap-4">
	<!-- Header Section -->
	<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
		<div class="flex items-center gap-3">
			<div>
				<h2 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Users')}
				</h2>
				{#if ($config?.license_metadata?.seats ?? null) !== null}
					{#if users.length > $config?.license_metadata?.seats}
						<p class="text-sm text-red-600 dark:text-red-400 mt-0.5">
							{users.length} of {$config?.license_metadata?.seats} seats used
						</p>
					{:else}
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
							{users.length} of {$config?.license_metadata?.seats} seats used
						</p>
					{/if}
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
						{users.length} {users.length === 1 ? 'user' : 'users'}
					</p>
				{/if}
			</div>
		</div>

		<!-- Search and Add Section -->
		<div class="flex gap-2">
			<div class="relative flex-1 md:w-72">
				<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4 text-gray-400"
					>
						<path
							fill-rule="evenodd"
							d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<input
					class="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
					bind:value={search}
					placeholder={$i18n.t('Search users...')}
				/>
			</div>

			<Tooltip content={$i18n.t('Add User')}>
				<button
					class="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white transition-colors font-medium text-sm flex items-center gap-2 shadow-sm"
					on:click={() => {
						showAddUserModal = !showAddUserModal;
					}}
				>
					<Plus className="size-4" />
					<span class="hidden sm:inline">Add User</span>
				</button>
			</Tooltip>
		</div>
	</div>
</div>

<div class="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm bg-white dark:bg-gray-900">
	<div class="overflow-x-auto">
		<table class="w-full">
			<thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
				<tr>
					<th
						scope="col"
						class="px-6 py-3.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
						on:click={() => setSortKey('role')}
					>
						<div class="flex gap-2 items-center">
							{$i18n.t('Role')}
							<span class="text-gray-400">
								{#if sortKey === 'role'}
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								{:else}
									<ChevronUp className="size-3.5 opacity-0" />
								{/if}
							</span>
						</div>
					</th>
					<th
						scope="col"
						class="px-6 py-3.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
						on:click={() => setSortKey('name')}
					>
						<div class="flex gap-2 items-center">
							{$i18n.t('Name')}
							<span class="text-gray-400">
								{#if sortKey === 'name'}
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								{:else}
									<ChevronUp className="size-3.5 opacity-0" />
								{/if}
							</span>
						</div>
					</th>
					<th
						scope="col"
						class="px-6 py-3.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
						on:click={() => setSortKey('email')}
					>
						<div class="flex gap-2 items-center">
							{$i18n.t('Email')}
							<span class="text-gray-400">
								{#if sortKey === 'email'}
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								{:else}
									<ChevronUp className="size-3.5 opacity-0" />
								{/if}
							</span>
						</div>
					</th>
					<th
						scope="col"
						class="px-6 py-3.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
						on:click={() => setSortKey('last_active_at')}
					>
						<div class="flex gap-2 items-center">
							{$i18n.t('Last Active')}
							<span class="text-gray-400">
								{#if sortKey === 'last_active_at'}
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								{:else}
									<ChevronUp className="size-3.5 opacity-0" />
								{/if}
							</span>
						</div>
					</th>
					<th
						scope="col"
						class="px-6 py-3.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
						on:click={() => setSortKey('created_at')}
					>
						<div class="flex gap-2 items-center">
							{$i18n.t('Created at')}
							<span class="text-gray-400">
								{#if sortKey === 'created_at'}
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								{:else}
									<ChevronUp className="size-3.5 opacity-0" />
								{/if}
							</span>
						</div>
					</th>
					<th
						scope="col"
						class="px-6 py-3.5 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
						on:click={() => setSortKey('oauth_sub')}
					>
						<div class="flex gap-2 items-center">
							{$i18n.t('OAuth ID')}
							<span class="text-gray-400">
								{#if sortKey === 'oauth_sub'}
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								{:else}
									<ChevronUp className="size-3.5 opacity-0" />
								{/if}
							</span>
						</div>
					</th>
					<th scope="col" class="px-6 py-3.5 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
						{$i18n.t('Actions')}
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
				{#each filteredUsers as user, userIdx}
					<tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
						<td class="px-6 py-4 whitespace-nowrap">
							<button
								class="inline-block"
								on:click={() => {
									if (user.role === 'user') {
										updateRoleHandler(user.id, 'admin');
									} else if (user.role === 'pending') {
										updateRoleHandler(user.id, 'user');
									} else {
										updateRoleHandler(user.id, 'pending');
									}
								}}
							>
								<Badge
									type={user.role === 'admin' ? 'info' : user.role === 'user' ? 'success' : 'muted'}
									content={$i18n.t(user.role)}
								/>
							</button>
						</td>
						<td class="px-6 py-4 whitespace-nowrap">
							<div class="flex items-center gap-3">
								<img
									class="rounded-full w-9 h-9 object-cover ring-2 ring-gray-100 dark:ring-gray-800"
									src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
									user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
									user.profile_image_url.startsWith('data:')
										? user.profile_image_url
										: `/user.png`}
									alt="user"
								/>
								<div class="text-sm font-medium text-gray-900 dark:text-white">
									{user.name}
								</div>
							</div>
						</td>
						<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
							{user.email}
						</td>
						<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
							{dayjs(user.last_active_at * 1000).fromNow()}
						</td>
						<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
							{dayjs(user.created_at * 1000).format('LL')}
						</td>
						<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
							{user.oauth_sub ?? '-'}
						</td>
						<td class="px-6 py-4 whitespace-nowrap text-right">
							<div class="flex items-center justify-end gap-1">
								{#if $config.features.enable_admin_chat_access && user.role !== 'admin'}
									<Tooltip content={$i18n.t('Chats')}>
										<button
											class="p-2.5 hover:bg-gray-100 dark:hover:bg-gray-750 rounded-lg transition-colors"
											on:click={async () => {
												showUserChatsModal = !showUserChatsModal;
												selectedUser = user;
											}}
										>
											<ChatBubbles />
										</button>
									</Tooltip>
								{/if}

								<Tooltip content={$i18n.t('Edit User')}>
									<button
										class="p-2.5 hover:bg-gray-100 dark:hover:bg-gray-750 rounded-lg transition-colors"
										on:click={async () => {
											showEditUserModal = !showEditUserModal;
											selectedUser = user;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="w-4 h-4"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
											/>
										</svg>
									</button>
								</Tooltip>

								{#if user.role !== 'admin'}
									<Tooltip content={$i18n.t('Delete User')}>
										<button
											class="p-2.5 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg transition-colors"
											on:click={async () => {
												showDeleteConfirmDialog = true;
												selectedUser = user;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
												/>
											</svg>
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
</div>

<div class="mt-3 flex items-center justify-between">
	<p class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5">
			<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
		</svg>
		{$i18n.t("Click on the user role button to change a user's role.")}
	</p>
	
	<Pagination bind:page count={users.length} />
</div>

{#if !$config?.license_metadata}
	{#if users.length > 50}
		<div class="mt-6 text-sm">
			<Markdown
				content={`
> [!NOTE]
> # **Hey there! 👋**
>
> It looks like you have over 50 users — that usually falls under organizational usage.
> 
> Open WebUI is proudly open source and completely free, with no hidden limits — and we'd love to keep it that way. 🌱  
>
> By supporting the project through sponsorship or an enterprise license, you're not only helping us stay independent, you're also helping us ship new features faster, improve stability, and grow the project for the long haul. With an *enterprise license*, you also get additional perks like dedicated support, customization options, and more — all at a fraction of what it would cost to build and maintain internally.  
> 
> Your support helps us stay independent and continue building great tools for everyone. 💛
> 
> - 👉 **[Click here to learn more about enterprise licensing](https://docs.openwebui.com/enterprise)**
> - 👉 *[Click here to sponsor the project on GitHub](https://github.com/sponsors/tjbck)*
`}
			/>
		</div>
	{/if}
{/if}