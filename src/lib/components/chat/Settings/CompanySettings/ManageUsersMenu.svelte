<script lang="ts">
	import { getContext } from 'svelte';
	import { onClickOutside } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Plus from '$lib/components/icons/Plus.svelte';
	import CheckmarkIcon from '$lib/components/icons/CheckmarkIcon.svelte';

	const i18n = getContext('i18n');
	
	export let users;
	export let group;
	export let updateGroupHandler;
	let showDropdown = false;
	let root;
	let search = '';
	let filteredUsers;

	let name = '';
	let description = '';
	let permissions = {};
	let userIds = [];

	const init = () => {
		if (group) {
			name = group.name;
			description = group.description;
			permissions = group?.permissions ?? {};
			userIds = group?.user_ids ?? [];
		}
	};

	$: if (showDropdown) {
		init();
	}

	$: filteredUsers = users
		// .filter((user) => user?.first_name !== 'INVITED')
		.filter((user) => !group?.user_ids?.includes(user.id))
		.filter((user) => {
			if (search === '') {
				return true;
			} else {
				let fullName = `${user.first_name.toLowerCase()} ${user.last_name.toLowerCase()}`;
				const query = search.toLowerCase();
				return fullName?.includes(query);
			}
		});
    $: noUsersToAdd = users
		// .filter((user) => user?.first_name !== 'INVITED')
		.filter((user) => !group?.user_ids?.includes(user.id))?.length === 0 ? true : false
</script>

<div bind:this={root} class="relative w-full" use:onClickOutside={() => (showDropdown = false)}>
	<div
		on:click={(e) => {
			e.stopPropagation();
			showDropdown = !showDropdown;
		}}
	>
		<slot />
	</div>
	{#if showDropdown}
		<div
			class="min-w-[18rem] flex flex-col absolute left-0 right-0 bg-lightGray-300 border-lightGray-400 dark:bg-customGray-900 px-2 py-2 border dark:border-customGray-700 rounded-lg z-10"
		>
			<div class="flex">
				<div
					class="flex border dark:border-customGray-700 rounded-lg dark:bg-customGray-900 dark:text-customGray-200"
				>
					<div class=" self-center ml-4 mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-3 h-3"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						class=" w-full text-xs pr-4 py-1 rounded-r-xl outline-none bg-transparent h-[30px]"
						bind:value={search}
						placeholder={$i18n.t('Search')}
					/>
				</div>
				<button
					on:click={async () => {
                        if(noUsersToAdd) return;
						const allUsersIds = filteredUsers.map((user) => user.id);
						await updateGroupHandler(group.id, {
							...group,
							user_ids: [...group.user_ids, ...allUsersIds]
						});
						document.getElementById(`group-${group.id}`)?.click();
					}}
					type="button"
					class="flex items-center shrink-0 ml-2.5 font-medium dark:text-white"
				>
					<Plus className="size-3" />
					{$i18n.t('Add All')}
				</button>
			</div>
            {#if noUsersToAdd}
                <div class="mt-3">{$i18n.t('No users to add')}</div>
            {/if}
			<div class="mt-2 max-h-[180px] overflow-y-auto overflow-x-hidden custom-scrollbar pr-1">
				{#each filteredUsers as user}
					<button
						on:click={async () => {
							await updateGroupHandler(group.id, {
								...group,
								user_ids: [...group.user_ids, user.id]
							});
							document.getElementById(`group-${group.id}`)?.click();
						}}
						class="w-full flex items-center p-1 hover:bg-lightGray-700 hover:dark:bg-customGray-950 rounded-lg cursor-pointer"
					>
						<img
							class=" rounded-full w-3 h-3 object-cover mr-1 whitespace-nowrap"
							src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
							user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
							user.profile_image_url.startsWith('data:')
								? user.profile_image_url
								: `/user.png`}
							alt="user"
						/>
						{#if user?.first_name !== "INVITED"}
							<div class="text-xs text-lightGray-100 dark:text-customGray-100 mr-1 whitespace-nowrap">
								{user.first_name}
								{user.last_name}
							</div>
						{/if}
						<div class="text-xs text-lightGray-100 dark:text-customGray-590 mr-1 whitespace-nowrap">{user.email}</div>
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>
