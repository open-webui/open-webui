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
	import { getChatById } from '$lib/apis/chats';
	export let users = [];
	export let group = {
		name: 'Admins',
		user_ids: [1, 2, 3]
	};

	export let setGroups = () => {};

	let showEdit = false;
	let showHistory = false;

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

	<div class="flex items-center gap-1.5 w-144 font-medium text-left">
		{dayjs(group.created_at * 1000).fromNow()}
	</div>
	<div class="flex items-center gap-1.5 w-144 font-medium text-left">
		{dayjs(group.last_active_at * 1000).fromNow()}
	</div>
	<!-- CREATED AT & LAST ACTIVE: src/lib/components/admin/Users/Groups.svelte -->
	<!-- UserList has similar feature: src/lib/components/admin/Users/UserList.svelte -->
	<div class="w-full flex w-full items-center gap-1">
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
			<span class="text-xs text-gray-750 dark:text-gray-400 font-medium">Edit</span>
			<Pencil className="size-3.5" />
		</div>
	</div>
	<!-- Clicking anywhere in the group item shows the edit modal, not just the pencil icon-->
</button>
