<script lang="ts">
	import { getContext } from 'svelte';
	import { getGroupMembers } from '$lib/apis/groups';
	const i18n = getContext<any>('i18n');
	export let groupId: string;
	export let groups: import('../Groups.svelte').GroupListItem[] = [];
	let query = '';
	let page = 1;
	$: members = getGroupMembers(localStorage.token, groupId, 'inherited', query, page);
</script>

<div class="space-y-3 text-sm">
	<p class="text-xs text-gray-500">
		{$i18n.t('Inherited members are managed in their directly assigned groups.')}
	</p>
	<input
		class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent px-2 py-1"
		aria-label={$i18n.t('Search inherited members')}
		placeholder={$i18n.t('Search inherited members')}
		bind:value={query}
		on:input={() => {
			page = 1;
		}}
	/>
	{#await members}
		<p>{$i18n.t('Loading...')}</p>
	{:then result}
		<p class="text-xs text-gray-500">
			{$i18n.t(
				'Direct: {{direct}} · Inherited: {{inherited}} · Total: {{effective}}',
				result.counts
			)}
		</p>
		{#each result.items as member (member.id)}
			<div class="border-b border-gray-100 dark:border-gray-800 py-2">
				<div>{member.name} <span class="text-gray-500">{member.email}</span></div>
				<div class="text-xs text-gray-500">
					{$i18n.t('Inherited via')}
					{#each member.via_group_ids as id, index}
						{index ? ', ' : ''}<a class="underline" href={`/admin/users/groups?id=${id}`}
							>{groups.find((group) => group.id === id)?.path || id}</a
						>
					{/each}
				</div>
			</div>
		{:else}<p class="text-gray-500">{$i18n.t('No inherited members')}</p>{/each}
		<div class="flex items-center justify-between">
			<button type="button" disabled={page <= 1} class="disabled:opacity-40" on:click={() => page--}
				>{$i18n.t('Previous')}</button
			>
			<span>{page} / {Math.max(1, Math.ceil(result.total / 30))}</span>
			<button
				type="button"
				disabled={page * 30 >= result.total}
				class="disabled:opacity-40"
				on:click={() => page++}>{$i18n.t('Next')}</button
			>
		</div>
	{:catch error}
		<p role="alert" class="text-red-500">{String(error)}</p>
	{/await}
</div>
