<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { getUsers } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import { addUserToGroup, removeUserFromGroup } from '$lib/apis/groups';

	export let groupId: string;
	export let userCount = 0;

	let users = [];
	let total = 0;

	let query = '';
	let page = 1;

	const getUserList = async () => {
		try {
			const res = await getUsers(
				localStorage.token,
				query,
				`group_id:${groupId}`,
				null,
				page
			).catch((error) => {
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

	const toggleMember = async (userId, state) => {
		if (state === 'checked') {
			await addUserToGroup(localStorage.token, groupId, [userId]).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		} else {
			await removeUserFromGroup(localStorage.token, groupId, [userId]).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		}

		page = 1;
		getUserList();
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

<div class=" max-h-full h-full w-full flex flex-col">
	<div class="w-full h-fit">
		<div class="flex flex-1 h-fit">
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

	<div class="mt-3 overflow-y-auto flex-1">
		<div class="flex flex-col gap-2.5">
			{#if users.length > 0}
				{#each users as user, userIdx (user.id)}
					<div class="flex flex-row items-center gap-3 w-full text-sm">
						<div class="flex items-center">
							<Checkbox
								state={(user?.group_ids ?? []).includes(groupId) ? 'checked' : 'unchecked'}
								on:change={(e) => {
									toggleMember(user.id, e.detail);
								}}
							/>
						</div>

						<div class="flex w-full items-center justify-between overflow-hidden">
							<Tooltip content={user.email} placement="top-start">
								<div class="flex">
									<div class=" font-medium self-center truncate">{user.name}</div>
								</div>
							</Tooltip>

							{#if (user?.group_ids ?? []).includes(groupId)}
								<Badge type="success" content="member" />
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="text-gray-500 text-xs text-center py-2 px-10">
					{$i18n.t('No users were found.')}
				</div>
			{/if}
		</div>
	</div>

	{#if total > 30}
		<Pagination bind:page count={total} perPage={30} />
	{/if}
</div>
