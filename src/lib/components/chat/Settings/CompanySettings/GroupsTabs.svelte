<script lang="ts">
    import { getContext, onMount } from "svelte";
    import { createNewGroup, getGroups } from '$lib/apis/groups';
    import { user } from '$lib/stores';
    import { WEBUI_BASE_URL } from '$lib/constants';
    import Accordeon from "./Accordeon.svelte";
   
   const i18n = getContext('i18n');
   export let users = [];
   let groupName = '';
   let groups = [];

   $: console.log(groups)

   const setGroups = async () => {
		groups = await getGroups(localStorage.token);
	};

    onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		} else {
			await setGroups();
		}
	});
</script>
<div>
    <div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Group Management')}</div>
		</div>
	</div>
    <div class="flex-1 mb-1.5">
        <div class="relative w-full dark:bg-customGray-900 rounded-md">
            {#if groupName}
                <div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">{$i18n.t('Group name')}</div>
            {/if}
            <input
                class={`px-2.5 text-sm ${groupName ? "mt-2" : "mt-0"} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
                placeholder={$i18n.t('Create a group')}
                bind:value={groupName}
            />
            {#if !groupName}
                <span
                    class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs dark:text-customGray-100/50 pointer-events-none select-none"
                >
                    {$i18n.t('e.g., Marketing')}
                </span>
            {/if}
        </div>
    </div>
    <button
        class="bg-gray-900 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 text-gray-100 dark:text-customGray-200 py-2.5 px-4 h-12 rounded-lg transition"
        on:click={() => {}}
        type="button"
    >
        {$i18n.t('Done')}
    </button>
    <div>
        {#each groups as group (group.id)}
        <Accordeon title={`${group.name} (${users?.filter(user => group.user_ids?.includes(user.id))?.length} ${$i18n.t('Users')})`}>
                {#each users?.filter(user => group.user_ids?.includes(user.id)) as user (user.id)}
                    <div class="flex items-center mb-2.5">
				<img
					class=" rounded-full w-3 h-3 object-cover mr-2.5"
					src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
					user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
					user.profile_image_url.startsWith('data:')
						? user.profile_image_url
						: `/user.png`}
					alt="user"
				/>
				{#if (user?.first_name !== 'INVITED')}
					<div class="text-xs dark:text-customGray-100 mr-1 whitespace-nowrap">{user.first_name} {user.last_name}</div>
				{/if}
				<div class="text-xs dark:text-customGray-590 mr-1 whitespace-nowrap">{user.email}</div>
			</div>
                {/each}
            </Accordeon>
        {/each}

    </div>
</div>