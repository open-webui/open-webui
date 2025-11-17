<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import { getUsers } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';
	import Pagination from '$lib/components/common/Pagination.svelte';

	export let userCount = 0;
	let userIds = [];

	let users = [];
	let total = 0;

	let query = '';
	let page = 1;

	const getUserList = async () => {
		try {
			const res = await getUsers(localStorage.token, query, null, null, page).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				users = res.users;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		}
	};

	$: if (page) {
		getUserList();
	}

	$: if (query !== null) {
		getUserList();
	}

	$: if (query) {
		page = 1;
	}
</script>

<div class=" max-h-full">
	<div class="flex w-full">
		<div class="flex flex-1">
			<div class=" self-center mr-3">
				<Search />
			</div>
			<input
				class=" w-full text-sm pr-4 rounded-r-xl outline-hidden bg-transparent"
				bind:value={query}
				placeholder={$i18n.t('Search')}
			/>
		</div>
	</div>

	<div class="mt-3 overflow-y-auto">
		<div class="flex flex-col gap-2.5">
			{#if users.length > 0}
				{#each users as user, userIdx (user.id)}
					<div class="flex flex-row items-center gap-3 w-full text-sm">
						<div class="flex items-center">
							<Checkbox
								state={userIds.includes(user.id) ? 'checked' : 'unchecked'}
								on:change={(e) => {
									if (e.detail === 'checked') {
										userIds = [...userIds, user.id];
									} else {
										userIds = userIds.filter((id) => id !== user.id);
									}
								}}
							/>
						</div>

						<div class="flex w-full items-center justify-between overflow-hidden">
							<Tooltip content={user.email} placement="top-start">
								<div class="flex">
									<div class=" font-medium self-center truncate">{user.name}</div>
								</div>
							</Tooltip>

							{#if userIds.includes(user.id)}
								<Badge type="success" content="member" />
							{/if}
						</div>
					</div>
				{/each}

				{page}

				{total}

				{#if total > 30}
					<Pagination bind:page count={total} perPage={30} />
				{/if}
			{:else}
				<div class="text-gray-500 text-xs text-center py-2 px-10">
					{$i18n.t('No users were found.')}
				</div>
			{/if}
		</div>
	</div>
</div>
