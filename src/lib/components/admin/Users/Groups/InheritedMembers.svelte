<script lang="ts">
	import { getContext } from 'svelte';
	import { getGroupMembers } from '$lib/apis/groups';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	const i18n = getContext<import('svelte/store').Writable<import('i18next').i18n>>('i18n');
	export let groupId: string;
	export let groups: import('../Groups.svelte').GroupListItem[] = [];
	let query = '';
	let page = 1;
	$: members = getGroupMembers(localStorage.token, groupId, 'inherited', query, page);
</script>

<div class="flex w-full min-w-0 flex-col text-sm">
	<div class="mb-1.5 flex flex-wrap items-center gap-2">
		<div class="flex min-w-0 flex-1 basis-full items-center sm:basis-0">
			<div class="self-center mr-3">
				<Search />
			</div>
			<input
				class="w-full min-w-0 text-sm pr-4 rounded-r-xl outline-hidden bg-transparent"
				aria-label={$i18n.t('Search inherited members')}
				placeholder={$i18n.t('Search')}
				bind:value={query}
				on:input={() => {
					page = 1;
				}}
			/>
		</div>
		<slot name="filter" />
	</div>
	{#await members}
		<div class="my-10" role="status" aria-label={$i18n.t('Loading...')}>
			<Spinner className="size-5" />
		</div>
	{:then result}
		<p class="my-2 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Inherited members are managed in their directly assigned groups.')}
		</p>
		{#if result.items.length > 0}
			<table class="w-full table-fixed text-left text-sm text-gray-500 dark:text-gray-400">
				<thead class="text-xs text-gray-800 uppercase dark:text-gray-200">
					<tr class="border-b-[1.5px] border-gray-50/50 dark:border-gray-800/10">
						<th scope="col" class="w-1/2 px-2.5 py-1.5">{$i18n.t('Name')}</th>
						<th scope="col" class="px-2.5 py-1.5">{$i18n.t('Inherited via')}</th>
					</tr>
				</thead>
				<tbody>
					{#each result.items as member (member.id)}
						<tr class="text-xs">
							<td class="px-3 py-1 font-normal text-gray-900 dark:text-white">
								<Tooltip content={member.email} placement="top-start">
									<div class="flex min-w-0 items-center gap-2">
										<img
											class="size-6 shrink-0 rounded-full object-cover"
											src={`${WEBUI_API_BASE_URL}/users/${member.id}/profile/image`}
											alt=""
										/>
										<div class="truncate">{member.name}</div>
									</div>
								</Tooltip>
							</td>
							<td class="px-3 py-1">
								{#each member.via_group_ids as id}
									<a
										class="block truncate rounded-sm transition hover:text-gray-700 hover:underline dark:hover:text-gray-200"
										href={`/admin/users/groups?id=${id}`}
										title={groups.find((group) => group.id === id)?.path || id}
									>
										{groups.find((group) => group.id === id)?.path || id}
									</a>
								{/each}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<div class="px-10 py-2 text-center text-xs text-gray-500">
				{$i18n.t('No inherited members')}
			</div>
		{/if}
		{#if result.total > 30}
			<Pagination bind:page count={result.total} perPage={30} />
		{/if}
	{:catch error}
		<p role="alert" class="py-4 text-center text-xs text-red-500">{String(error)}</p>
	{/await}
</div>
