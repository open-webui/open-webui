<script lang="ts">
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
  	import type { Writable } from 'svelte/store';
  	import type { i18n as i18nType } from 'i18next'

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';
	import { getSignUpEnabledStatus, toggleSignUpEnabledStatus } from '$lib/apis/auths';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import AddUserModal from '$lib/components/admin/AddUserModal.svelte';
	import SettingsModal from '$lib/components/admin/SettingsModal.svelte';
	import EditUserModal from '$lib/components/admin/EditUserModal.svelte';
	import UserChatsModal from '$lib/components/admin/UserChatsModal.svelte';

	const i18n:Writable<i18nType> = getContext('i18n');

	let page = 1;
	let search = '';
	let loaded = false;
	let users: any[] = [];
	let selectedUser: any = null;
	let showSettingsModal = false;
	let showAddUserModal = false;
	let showUserChatsModal = false;
	let showEditUserModal = false;
	
  	enum View { Overview, Plugins };
  	let view:any = View.Overview;

	onMount(async ()=>{
		if ($user?.role!=='admin') await goto('/');
		else users = await getUsers(localStorage.token);
		loaded = true;
	});
	const updateRoleHandler = async (id:string, role:string)=>{
		const res = await updateUserRole(localStorage.token, id, role)
			.catch((error)=>{ toast.error(error); return null; });
		if (res) users = await getUsers(localStorage.token);
	};
	const editUserPasswordHandler = async (id:string, password:string)=>{
		const res = await deleteUserById(localStorage.token, id)
			.catch((error)=>{ toast.error(error); return null;});
		if (res) {
			users = await getUsers(localStorage.token);
			toast.success($i18n.t('Successfully updated.'));
		}
	};
	const deleteUserHandler = async (id:string)=>{
		const res = await deleteUserById(localStorage.token, id)
			.catch((error)=>{ toast.error(error); return null; });
		if (res) users = await getUsers(localStorage.token);
	};
	
</script>
<svelte:head>
	<title>{$i18n.t('Admin Panel')} | {$WEBUI_NAME}</title>
</svelte:head>
{#key selectedUser}
	<EditUserModal 
		bind:show={showEditUserModal} {selectedUser} sessionUser={$user}
		on:save={async()=>{users= await getUsers(localStorage.token)}}
	/>
{/key}
<AddUserModal
	bind:show={showAddUserModal}
	on:save={async()=>users=await getUsers(localStorage.token)}
/>
<UserChatsModal bind:show={showUserChatsModal} user={selectedUser} />
<SettingsModal bind:show={showSettingsModal} />
<section>
	<header>
		<h2>{$i18n.t(`Dashboard`)}</h2>
		<div>
			<button on:click={()=>showSettingsModal=!showSettingsModal}>
				<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
					<!-- cog-8-tooth --><path fill-rule="evenodd" clip-rule="evenodd" d="M6.955 1.45A.5.5 0 0 1 7.452 1h1.096a.5.5 0 0 1 .497.45l.17 1.699c.484.12.94.312 1.356.562l1.321-1.081a.5.5 0 0 1 .67.033l.774.775a.5.5 0 0 1 .034.67l-1.08 1.32c.25.417.44.873.561 1.357l1.699.17a.5.5 0 0 1 .45.497v1.096a.5.5 0 0 1-.45.497l-1.699.17c-.12.484-.312.94-.562 1.356l1.082 1.322a.5.5 0 0 1-.034.67l-.774.774a.5.5 0 0 1-.67.033l-1.322-1.08c-.416.25-.872.44-1.356.561l-.17 1.699a.5.5 0 0 1-.497.45H7.452a.5.5 0 0 1-.497-.45l-.17-1.699a4.973 4.973 0 0 1-1.356-.562L4.108 13.37a.5.5 0 0 1-.67-.033l-.774-.775a.5.5 0 0 1-.034-.67l1.08-1.32a4.971 4.971 0 0 1-.561-1.357l-1.699-.17A.5.5 0 0 1 1 8.548V7.452a.5.5 0 0 1 .45-.497l1.699-.17c.12-.484.312-.94.562-1.356L2.629 4.107a.5.5 0 0 1 .034-.67l.774-.774a.5.5 0 0 1 .67-.033L5.43 3.71a4.97 4.97 0 0 1 1.356-.561l.17-1.699ZM6 8c0 .538.212 1.026.558 1.385l.057.057a2 2 0 0 0 2.828-2.828l-.058-.056A2 2 0 0 0 6 8Z"/>
				</svg>
				<span>{$i18n.t(`Admin Settings`)}</span>
			</button>
		</div>
	</header>
	<nav class="tabs">
		<button class:active={view==View.Overview} on:click={()=>view=View.Overview}>{$i18n.t(`Overview`)}</button>
		<!-- <button class:active={view==View.Plugins} on:click={()=>view=View.Plugins}>{$i18n.t(`Plugins`)}</button> -->
	</nav>
	{#if view === View.Overview }
		<nav class="top">
			<div class="left">
				<span>{$i18n.t(`All Users`)}</span><spacer/><span>{users.length}</span>
			</div>
			<div class="right">
				<input bind:value={search} placeholder={$i18n.t(`Search`)}>
				<Tooltip content={$i18n.t('Add User')}>
					<button on:click={()=>showAddUserModal=!showAddUserModal}>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-4 h-4">
							<!-- plus --><path d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"/>
						</svg>
					</button>
				</Tooltip>
			</div>
		</nav>
		<div class="frame">
			<table>
				<thead>
					<tr>
						<th scope="col">{$i18n.t('Role')}</th>
						<th scope="col">{$i18n.t('Name')}</th>
						<th scope="col">{$i18n.t('Email')}</th>
						<th scope="col">{$i18n.t('Last Active')}</th>
						<th scope="col">{$i18n.t('Created at')}</th>
						<th scope="col"/>
					</tr>
				</thead>
				<tbody>
					{#each users.filter((user)=>{
							if (!search) return true;
							let name = user.name.toLowerCase();
							const query = search.toLowerCase();
							return name.includes(query);
						})
						.slice((page-1)*20,page*20) as user }
						<tr>
							<td>
								<button
									class:is-user={user.role=='user'}
									class:is-admin={user.role=='admin'}
									class:is-pending={user.role=='pending'}
									on:click={()=>
										(user.role === 'user') ? updateRoleHandler(user.id, 'admin') :
										(user.role === 'pending') ? updateRoleHandler(user.id, 'user') :
										updateRoleHandler(user.id, 'pending')
									}>
									<spacer/>
									<span>{$i18n.t(user.role)}</span>
								</button>
							</td>
							<td>
								<div>
									<img alt="user" src={user.profile_image_url} />
									<div>{user.name}</div>
								</div>
							</td>
							<td>{user.email}</td>
							<td>{dayjs(user.last_active_at * 1000).fromNow()}</td>
							<td>{dayjs(user.created_at * 1000).format($i18n.t('MMMM DD, YYYY'))}</td>
							<td>
								<div class="actions">
									{#if user.role == 'admin'}
										<Tooltip content={$i18n.t('Chats')}>
											<button	on:click={async()=>{
												showUserChatsModal=!showUserChatsModal;
												selectedUser=user; }}>
												<ChatBubbles />
											</button>
										</Tooltip>
										<Tooltip content={$i18n.t('Edit User')}>
											<button	on:click={async()=>{
												showEditUserModal=!showEditUserModal;
												selectedUser=user; }}>
												<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke="currentColor">
													<!-- pencil --><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"/>
												</svg>
											</button>
										</Tooltip>
										<Tooltip content={$i18n.t('Delete User')}>
											<button on:click={async()=>deleteUserHandler(user.id)}>
												<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke="currentColor">
													<!-- trash --><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/>
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
		<footer>
			ⓘ {$i18n.t("Click on the user role button to change a user's role.")}
		</footer>
		<Pagination bind:page count={users.length} />
	<!-- 
	{:else if view === View.Plugins }
	-->
	{/if}
</section>
<style lang="postcss">
	h2 { @apply text-2xl font-semibold self-center }
	section { @apply flex flex-col h-full w-screen flex-grow dark:text-white }
	header { @apply flex justify-between items-center px-6 pt-4 }
	header button { @apply flex items-center space-x-1 p-2 md:px-3 md:py-1.5 transition rounded-xl }
	header button { @apply bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 }
	header button span { @apply hidden md:inline text-xs }
	nav.tabs { @apply px-3 mb-3 border-b dark:border-gray-800 text-gray-700 dark:text-gray-400 }
	nav.tabs button { @apply mx-3 py-3 border-b font-medium text-sm }
	nav.tabs button.active { @apply dark:text-gray-100 }
	nav.top { @apply flex flex-col md:flex-row justify-between mx-6 mt-0.5 mb-3 gap-1 text-lg }
	nav.top div.left { @apply flex flex-row md:flex-row md:justify-between px-0.5 font-medium }
	nav.top div.left div { @apply flex }
	nav.top div.left span:first-child { @apply font-medium }
	nav.top div.left span:last-child { @apply text-gray-500 dark:text-gray-300 }
	nav.top div.left spacer { @apply self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700 }
	nav.top div.right { @apply flex items-center gap-1 }
	nav.top input { @apply w-full md:w-60 rounded-xl py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none }
	nav.top button { @apply px-2 py-2 flex items-center rounded-xl font-medium text-sm border transition }
	nav.top button { @apply border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 }
	div.frame { @apply mx-6 relative overflow-x-auto whitespace-nowrap overflow-hidden }
	table { @apply w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto }
	table thead { @apply text-xs uppercase text-gray-700 bg-gray-50 dark:bg-gray-850 dark:text-gray-400 }
	table thead th { @apply px-3 py-2 }
	table thead th:last-child { @apply text-right }
	table tbody tr { @apply bg-white border-b dark:bg-gray-900 dark:border-gray-700 text-xs }
	table tbody tr td { @apply px-3 py-2 }
	table tbody tr td:nth-child(1) { @apply min-w-[7rem] w-28 }
	table button { @apply flex items-center gap-2 text-xs px-3 py-0.5 rounded-lg }
	table button spacer { @apply w-1 h-1 rounded-full }
	table button.is-user { @apply text-green-600 dark:text-green-200 bg-green-200/30 }
	table button.is-user spacer { @apply bg-green-600 dark:bg-green-300 }
	table button.is-admin { @apply text-sky-600 dark:text-sky-200 bg-sky-200/30 }
	table button.is-admin spacer { @apply bg-sky-600 dark:bg-sky-300 }
	table button.is-pending { @apply text-gray-600 dark:text-gray-200 bg-gray-200/30 }
	table button.is-pending spacer { @apply bg-gray-600 dark:bg-gray-300 }
	table td:nth-child(2) { @apply font-medium text-gray-900 dark:text-white w-max }
	table td:nth-child(2) > div { @apply flex flex-row w-max }
	table td:nth-child(2) > div > img { @apply rounded-full w-6 h-6 object-cover mr-2.5 }
	table td:nth-child(2) > div > div { @apply font-medium self-center }
	table td:last-child { @apply text-right }
	table td:last-child button { @apply self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl }
	table td:last-child div { @apply flex justify-end w-full }
	footer { @apply mx-6 text-gray-500 text-xs mt-2 text-right }
</style>
