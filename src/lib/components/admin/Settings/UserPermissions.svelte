<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getUserDefaultPermissions, updateUserDefaultPermissions } from '$lib/apis/users';
	import { DEFAULT_PERMISSIONS } from '$lib/constants/permissions';

	import Permissions from '$lib/components/admin/Users/Groups/Permissions.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function = () => {};

	let loaded = false;
	let saving = false;
	let permissions: any = { ...DEFAULT_PERMISSIONS };

	const updateHandler = async () => {
		saving = true;
		const res = await updateUserDefaultPermissions(localStorage.token, permissions).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		saving = false;

		if (res) {
			permissions = res;
			saveHandler();
		}
	};

	onMount(async () => {
		const res = await getUserDefaultPermissions(localStorage.token).catch((err) => {
			toast.error(`${err}`);
			return null;
		});

		if (res) {
			permissions = res;
		}

		loaded = true;
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={updateHandler}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if loaded}
			<div>
				<div class=" mt-0.5 mb-2.5 text-base font-medium">
					{$i18n.t('User Permissions')}
				</div>

				<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t(
						'These are the global default permissions applied to all non-admin users. Group memberships can grant additional access on top of these defaults. Admins are not affected. Changes apply on the next page load.'
					)}
				</div>

				<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

				<Permissions bind:permissions defaultPermissions={DEFAULT_PERMISSIONS} />
			</div>
		{:else}
			<div class="flex h-full items-center justify-center">
				<Spinner />
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 {saving
				? 'cursor-not-allowed'
				: ''}"
			type="submit"
			disabled={saving || !loaded}
		>
			{$i18n.t('Save')}

			{#if saving}
				<span class="shrink-0">
					<Spinner />
				</span>
			{/if}
		</button>
	</div>
</form>
