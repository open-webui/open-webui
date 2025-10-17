<script>
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import dayjs from 'dayjs';
	import timezone from 'dayjs/plugin/timezone';
	import utc from 'dayjs/plugin/utc';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	// Extend dayjs with timezone and utc plugins
	dayjs.extend(timezone);
	dayjs.extend(utc);
	dayjs.extend(localizedFormat);

	const i18n = getContext('i18n');

	import { deleteGroupById, updateGroupById } from '$lib/apis/groups';

	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Clock from '$lib/components/icons/Clock.svelte';
	import User from '$lib/components/icons/User.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import GroupModal from './EditGroupModal.svelte';
	import ConversationHistoryModal from './ConversationHistoryModal.svelte';
	import EditGroupWorkSpaceModal from './EditGroupWorkSpaceModal.svelte';
	import { getChatById } from '$lib/apis/chats';
	export let users = [];
	export let group = {
		name: 'Admins',
		user_ids: [1, 2, 3]
	};

	export let setGroups = () => {};

	let showEdit = false;
	let showHistory = false;
	let showWorkspaceModal = false;

	const updateHandler = async (_group) => {
		const res = await updateGroupById(localStorage.token, group.id, _group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group updated successfully'));
			setGroups();
		}
	};

	const deleteHandler = async () => {
		const res = await deleteGroupById(localStorage.token, group.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group deleted successfully'));
			setGroups();
		}
	};

	// Helper function to format date in desired format
	const formatDateTime = (timestamp) => {
		// Convert timestamp to JavaScript Date object
		const date = new Date(timestamp * 1000);
		
		// Get timezone abbreviation
		const timezoneAbbr = date.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop();
		
		// Format using dayjs for better control
		const dayjsDate = dayjs(timestamp * 1000);
		
		// Format: "Aug 18 2025, 04:05:15 PM (EST)"
		const formattedDate = dayjsDate.format('MMM DD YYYY, hh:mm:ss A');
		
		return `${formattedDate} (${timezoneAbbr})`;
	};
</script>

<GroupModal
	bind:show={showEdit}
	edit
	{users}
	{group}
	onSubmit={updateHandler}
	onDelete={deleteHandler}
/>

<ConversationHistoryModal bind:show={showHistory} {users} {group} />
<EditGroupWorkSpaceModal bind:show={showWorkspaceModal}  {group} />

<button
	class="flex items-center gap-3 justify-between px-1 text-xs w-full transition"
	on:click={() => {
		showEdit = true;
	}}
>
	<div class="flex items-center gap-1.5 w-288 font-medium text-left">
		<div>
			<UserCircleSolid className="size-4" />
		</div>
		{group.name}
	</div>

	<div class="flex items-center gap-1.5 w-76 font-medium text-left">
		{group.user_ids.length}

		<div>
			<User className="size-3.5" />
		</div>
	</div>

	<div class="flex items-center gap-1.5 w-136 font-medium text-left">
		{dayjs(group.created_at * 1000).fromNow()}
	</div>
	<div class="flex items-center gap-1.5 w-136 font-medium text-left">
		{dayjs(group.last_active_at * 1000).fromNow()}
	</div>
	<!-- CREATED AT & LAST ACTIVE: src/lib/components/admin/Users/Groups.svelte -->
	<!-- UserList has similar feature: src/lib/components/admin/Users/UserList.svelte -->
	<div class="w-full flex w-full items-center gap-1">
		<button
			class="rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition flex items-center gap-1.5"
			on:click|stopPropagation={() => {
				showWorkspaceModal = true;
			}}
		>
			<span class="text-xs text-gray-750 dark:text-gray-400 font-medium">Edit Workspace</span>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
				<path fill-rule="evenodd" d="M6.955 1.45A.5.5 0 0 1 7.452 1h1.096a.5.5 0 0 1 .497.45l.17 1.699c.484.12.94.312 1.356.562l1.321-1.081a.5.5 0 0 1 .67.033l.774.775a.5.5 0 0 1 .034.67l-1.08 1.32c.25.417.44.873.561 1.357l1.699.17a.5.5 0 0 1 .45.497v1.096a.5.5 0 0 1-.45.497l-1.699.17c-.12.484-.312.94-.562 1.356l1.082 1.322a.5.5 0 0 1-.034.67l-.774.774a.5.5 0 0 1-.67.033l-1.322-1.08c-.416.25-.872.44-1.356.561l-.17 1.699a.5.5 0 0 1-.497.45H7.452a.5.5 0 0 1-.497-.45l-.17-1.699a4.973 4.973 0 0 1-1.356-.562L4.108 13.37a.5.5 0 0 1-.67-.033l-.774-.775a.5.5 0 0 1-.034-.67l1.08-1.32a4.971 4.971 0 0 1-.561-1.357l-1.699-.17A.5.5 0 0 1 1 8.548V7.452a.5.5 0 0 1 .45-.497l1.699-.17c.12-.484.312-.94.562-1.356L2.629 4.107a.5.5 0 0 1 .034-.67l.774-.774a.5.5 0 0 1 .67-.033L5.43 3.71a4.97 4.97 0 0 1 1.356-.561l.17-1.699ZM6 8c0 .538.212 1.026.558 1.385l.057.057a2 2 0 0 0 2.828-2.828l-.058-.056A2 2 0 0 0 6 8Z" clip-rule="evenodd"/>
			</svg>
		</button>
		<!-- History button -->
		<button
			class="rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition flex items-center gap-1.5"
			on:click|stopPropagation={() => {
				showHistory = true;
			}}
		>
			<span class="text-xs text-gray-750 dark:text-gray-400 font-medium">Conversation History</span>
			<Clock className="size-3.5" />
		</button>

		<!-- Existing edit button -->
		<div
			class="rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition flex items-center gap-1.5"
		>
			<span class="text-xs text-gray-750 dark:text-gray-400 font-medium whitespace-nowrap">Edit</span>
			<Pencil className="size-3.5" />
		</div>
	</div>
	<!-- Clicking anywhere in the group item shows the edit modal, not just the pencil icon-->
</button>
