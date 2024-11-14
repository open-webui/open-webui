<script>
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import User from '$lib/components/icons/User.svelte';

	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import GroupModal from './EditGroupModal.svelte';

	export let users = [];
	export let group = {
		name: 'Admins',
		user_ids: [1, 2, 3]
	};

	let showEdit = false;
</script>

<GroupModal bind:show={showEdit} edit {group} {users} />

<div class="flex items-center gap-3 justify-between px-1 text-xs w-full transition">
	<div class="flex items-center gap-1.5 w-full font-medium">
		<div>
			<UserCircleSolid className="size-4" />
		</div>
		{group.name}
	</div>

	<div class="flex items-center gap-1.5 w-full font-medium">
		{group.user_ids.length}

		<div>
			<User className="size-3.5" />
		</div>
	</div>

	<div class="w-full flex justify-end">
		<button
			class=" rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
			on:click={() => {
				showEdit = true;
			}}
		>
			<Pencil />
		</button>
	</div>
</div>
