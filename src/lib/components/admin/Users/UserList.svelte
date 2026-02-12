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
	<div class="mt-1 mb-3">
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

<!-- Header Section -->
<div class="mb-6 space-y-4">
	<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
		<!-- Title and Count -->
		<div class="flex items-center gap-3">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Users')}
			</h2>
			<div class="h-6 w-px bg-gray-300 dark:bg-gray-700"></div>
			{#if ($config?.license_metadata?.seats ?? null) !== null}
				{#if users.length > $config?.license_metadata?.seats}
					<div class="flex items-baseline gap-1.5">
						<span class="text-lg font-semibold text-red-600 dark:text-red-400">{users.length}</span>
						<span class="text-sm text-gray-500 dark:text-gray-400">of</span>
						<span class="text-lg font-semibold text-red-600 dark:text-red-400">{$config?.license_metadata?.seats}</span>
						<span class="text-sm text-gray-500 dark:text-gray-400">seats</span>
					</div>
				{:else}
					<div class="flex items-baseline gap-1.5">
						<span class="text-lg font-semibold text-gray-700 dark:text-gray-300">{users.length}</span>
						<span class="text-sm text-gray-500 dark:text-gray-400">of</span>
						<span class="text-lg font-semibold text-gray-700 dark:text-gray-300">{$config?.license_metadata?.seats}</span>
						<span class="text-sm text-gray-500 dark:text-gray-400">seats</span>
					</div>
				{/if}
			{:else}
				<span class="text-lg font-semibold text-gray-700 dark:text-gray-300">{users.length}</span>
			{/if}
		</div>

		<!-- Search and Add Button -->
		<div class="flex items-center gap-3">
			<div class="relative flex-1 md:w-80">
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
					class="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all duration-150"
					bind:value={search}
					placeholder={$i18n.t('Search users...')}
				/>
			</div>

			<Tooltip content={$i18n.t('Add User')}>
				<button
					class="p-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white transition-colors duration-150 shadow-sm hover:shadow"
					on:click={() => {
						showAddUserModal = !showAddUserModal;
					}}
				>
					<Plus className="size-4" strokeWidth="2.5" />
				</button>
			</Tooltip>
		</div>
	</div>
</div>

<!-- Table Container -->
<div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
	<div class="overflow-x-auto">
		<table class="w-full text-sm text-left">
			<thead class="bg-gray-50 dark:bg-gray-850 border-b border-gray-200 dark:border-gray-800">
				<tr>
					<th
						scope="col"
						class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-gray-700 dark:text-gray-300 cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => setSortKey('role')}
					>
						<div class="flex items-center gap-2">
							<span>{$i18n.t('Role')}</span>
							{#if sortKey === 'role'}
								<span class="text-blue-600 dark:text-blue-400">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" strokeWidth="2.5" />
									{:else}
										<ChevronDown className="size-3.5" strokeWidth="2.5" />
									{/if}
								</span>
							{:else}
								<span class="text-gray-400 opacity-0 group-hover:opacity-100">
									<ChevronUp className="size-3.5" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-gray-700 dark:text-gray-300 cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => setSortKey('name')}
					>
						<div class="flex items-center gap-2">
							<span>{$i18n.t('Name')}</span>
							{#if sortKey === 'name'}
								<span class="text-blue-600 dark:text-blue-400">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" strokeWidth="2.5" />
									{:else}
										<ChevronDown className="size-3.5" strokeWidth="2.5" />
									{/if}
								</span>
							{:else}
								<span class="text-gray-400 opacity-0 group-hover:opacity-100">
									<ChevronUp className="size-3.5" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-gray-700 dark:text-gray-300 cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => setSortKey('email')}
					>
						<div class="flex items-center gap-2">
							<span>{$i18n.t('Email')}</span>
							{#if sortKey === 'email'}
								<span class="text-blue-600 dark:text-blue-400">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" strokeWidth="2.5" />
									{:else}
										<ChevronDown className="size-3.5" strokeWidth="2.5" />
									{/if}
								</span>
							{:else}
								<span class="text-gray-400 opacity-0 group-hover:opacity-100">
									<ChevronUp className="size-3.5" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-gray-700 dark:text-gray-300 cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => setSortKey('last_active_at')}
					>
						<div class="flex items-center gap-2">
							<span>{$i18n.t('Last Active')}</span>
							{#if sortKey === 'last_active_at'}
								<span class="text-blue-600 dark:text-blue-400">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" strokeWidth="2.5" />
									{:else}
										<ChevronDown className="size-3.5" strokeWidth="2.5" />
									{/if}
								</span>
							{:else}
								<span class="text-gray-400 opacity-0 group-hover:opacity-100">
									<ChevronUp className="size-3.5" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-gray-700 dark:text-gray-300 cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => setSortKey('created_at')}
					>
						<div class="flex items-center gap-2">
							<span>{$i18n.t('Created at')}</span>
							{#if sortKey === 'created_at'}
								<span class="text-blue-600 dark:text-blue-400">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" strokeWidth="2.5" />
									{:else}
										<ChevronDown className="size-3.5" strokeWidth="2.5" />
									{/if}
								</span>
							{:else}
								<span class="text-gray-400 opacity-0 group-hover:opacity-100">
									<ChevronUp className="size-3.5" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-gray-700 dark:text-gray-300 cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => setSortKey('oauth_sub')}
					>
						<div class="flex items-center gap-2">
							<span>{$i18n.t('OAuth ID')}</span>
							{#if sortKey === 'oauth_sub'}
								<span class="text-blue-600 dark:text-blue-400">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-3.5" strokeWidth="2.5" />
									{:else}
										<ChevronDown className="size-3.5" strokeWidth="2.5" />
									{/if}
								</span>
							{:else}
								<span class="text-gray-400 opacity-0 group-hover:opacity-100">
									<ChevronUp className="size-3.5" />
								</span>
							{/if}
						</div>
					</th>
					<th scope="col" class="px-4 py-3 text-right">
						<span class="sr-only">Actions</span>
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-100 dark:divide-gray-850">
				{#each filteredUsers as user, userIdx}
					<tr class="hover:bg-gray-50 dark:hover:bg-gray-850/50 transition-colors">
						<td class="px-4 py-3">
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
						<td class="px-4 py-3">
							<div class="flex items-center gap-3">
								<img
									class="rounded-full w-8 h-8 object-cover ring-2 ring-gray-100 dark:ring-gray-800"
									src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
									user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
									user.profile_image_url.startsWith('data:')
										? user.profile_image_url
										: `/user.png`}
									alt="user"
								/>
								<span class="font-medium text-gray-900 dark:text-gray-100">{user.name}</span>
							</div>
						</td>
						<td class="px-4 py-3 text-gray-600 dark:text-gray-400">{user.email}</td>
						<td class="px-4 py-3 text-gray-600 dark:text-gray-400">
							{dayjs(user.last_active_at * 1000).fromNow()}
						</td>
						<td class="px-4 py-3 text-gray-600 dark:text-gray-400">
							{dayjs(user.created_at * 1000).format('LL')}
						</td>
						<td class="px-4 py-3 text-gray-600 dark:text-gray-400">
							{user.oauth_sub ?? '—'}
						</td>
						<td class="px-4 py-3">
							<div class="flex items-center justify-end gap-1">
								{#if $config.features.enable_admin_chat_access && user.role !== 'admin'}
									<Tooltip content={$i18n.t('Chats')}>
										<button
											class="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150"
											on:click={async () => {
												showUserChatsModal = !showUserChatsModal;
												selectedUser = user;
											}}
										>
											<ChatBubbles className="size-4" />
										</button>
									</Tooltip>
								{/if}

								<Tooltip content={$i18n.t('Edit User')}>
									<button
										class="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150"
										on:click={async () => {
											showEditUserModal = !showEditUserModal;
											selectedUser = user;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2"
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
											class="p-2 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors duration-150"
											on:click={async () => {
												showDeleteConfirmDialog = true;
												selectedUser = user;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2"
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

<!-- Help Text -->
<div class="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
	<svg
		xmlns="http://www.w3.org/2000/svg"
		viewBox="0 0 20 20"
		fill="currentColor"
		class="w-4 h-4 flex-shrink-0"
	>
		<path
			fill-rule="evenodd"
			d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
			clip-rule="evenodd"
		/>
	</svg>
	<span>{$i18n.t("Click on the user role button to change a user's role.")}</span>
</div>

<div class="mt-4">
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