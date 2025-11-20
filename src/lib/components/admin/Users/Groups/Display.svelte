<script lang="ts">
	import { getContext } from 'svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let name = '';
	export let created_by = '';
	export let created_at = '';
	export let updated_at = '';
	export let description = '';
	export let co_admin_emails: string[] | undefined = undefined;
	if (co_admin_emails !== undefined) {
		console.log('Display.svelte co_admin_emails:', co_admin_emails);
	} else {
		console.log('co_admin_emails MISSING');
	}
</script>

<div class="flex gap-2">
	<div class="flex flex-col w-full">
		<div class=" mb-0.5 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Name')}</div>

		<div class="flex-1">
			<input
				class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
				type="text"
				bind:value={name}
				placeholder={$i18n.t('Group Name')}
				autocomplete="off"
				required
			/>
		</div>
	</div>
</div>

<!-- <div class="flex flex-col w-full mt-2">
	<div class=" mb-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Color')}</div>

	<div class="flex-1">
		<Tooltip content={$i18n.t('Hex Color - Leave empty for default color')} placement="top-start">
			<div class="flex gap-0.5">
				<div class="text-gray-500">#</div>

				<input
					class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
					type="text"
					bind:value={color}
					placeholder={$i18n.t('Hex Color')}
					autocomplete="off"
				/>
			</div>
		</Tooltip>
	</div>
</div> -->

<div class="flex flex-col w-full mt-2">
	<div class=" mb-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Description')}</div>

	<div class="flex-1">
		<Textarea
			className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
			rows={4}
			bind:value={description}
			placeholder={$i18n.t('Group Description')}
		/>
	</div>



	<div class=" mb-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Created by')}</div>

	<div class="flex-1">
		<Textarea
			className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
			rows={4}
			bind:value={created_by}
			placeholder={$i18n.t('Created by')}
		/>
	</div>

		{#if co_admin_emails !== undefined}
		{#if co_admin_emails.length > 1}
			<div class=" mb-1 mt-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Co-admins')}</div>
		{:else}
			<div class=" mb-1 mt-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Co-admin')}</div>
		{/if}

		<div class="mb-2 flex flex-wrap gap-1 text-xs">
			{#if co_admin_emails.length > 0}
				{#each co_admin_emails as email}
					<div class="flex flex-wrap gap-1 text-xs">
						{email}
					</div>
				{/each}
			{:else}
				<div class="text-gray-500 dark:text-gray-600">{$i18n.t('None')}</div>
			{/if}
		</div>
	{/if}

	<div class=" mb-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Created at')}</div>

	<div class="flex-1">
		<Textarea
			className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
			rows={4}
			bind:value={created_at}
			placeholder={$i18n.t('Created at')}
		/>
	</div>

	<div class=" mb-1 text-xs text-gray-600 dark:text-gray-500">{$i18n.t('Updated at')}</div>

	<div class="flex-1">
		<Textarea
			className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
			rows={4}
			bind:value={updated_at}
			placeholder={$i18n.t('Updated at')}
		/>
	</div>
</div>

<!-- To add new properties:
 1. Apply here;
 2. src/lib/components/admin/Users/Groups/EditGroupModal.svelte
 3. Find <Display bind:name bind:description />
 4. Bind the new property
 5. Find src/lib/components/admin/Users/Groups/GroupItem.svelte
 6. Find bind:show={showEdit}. GroupModal is EditGroupModal.svelte
 7. They binded users, group, onSubmit, onDelete
 8. group (in const init) contains the new property
 9. group has[
    "id",
    "user_id",
    "created_by",
    "name",
    "description",
    "permissions",
    "data",
    "meta",
    "user_ids",
    "created_at",
    "updated_at"
]
10. in submitHandler, it is going to be handled in "updateGroupById", in src/lib/apis/groups/index.ts (currently no need to add creator name here)
11. in 
	 -->
