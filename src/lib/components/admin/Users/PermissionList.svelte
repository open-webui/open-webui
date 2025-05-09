<script>
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import { getPermissions } from '$lib/apis/permissions';
	import AddPermissionModal from '$lib/components/admin/Users/Permissions/AddPermissionModal.svelte';

	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let permissions = [];

	let search = '';
	let page = 1;
	let showAddPermissionModal = false;

	let sortKey = 'id'; // default sort key
	let sortOrder = 'asc'; // default sort order

	function setSortKey(key) {
		if (sortKey === key) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortOrder = 'asc';
		}
	}

	onMount(async () => {
		permissions = await getPermissions(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		});
	});
</script>

<AddPermissionModal
	bind:show={showAddPermissionModal}
	on:save={async () => {
		permissions = await getPermissions(localStorage.token);
	}}
/>

<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5">
		<div class="flex-shrink-0">
			{$i18n.t('Permissions')}
		</div>
		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
	</div>

	<div class="flex gap-1">
		<div class=" flex w-full space-x-2">
			<div>
				<Tooltip content={$i18n.t('Add permission')}>
					<button
						class=" p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
						on:click={() => {
							showAddPermissionModal = !showAddPermissionModal;
						}}
					>
						<Plus className="size-3.5" />
					</button>
				</Tooltip>
			</div>
		</div>
	</div>
</div>

<div
	class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm pt-0.5"
>
	<table
		class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded-sm"
	>
		<thead
			class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
		>
			<tr class="">
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('id')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Identifier')}

						{#if sortKey === 'id'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('category')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Category')}

						{#if sortKey === 'category'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('name')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Name')}

						{#if sortKey === 'name'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('label')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Label')}
						{#if sortKey === 'label'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('description')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Description')}
						{#if sortKey === 'description'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
			</tr>
		</thead>

		<tbody class="">
			{#each permissions as perm}
				<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
					<td class="px-3 py-1 min-w-[7rem] w-28">
						<div class=" font-medium self-center">{perm.id}</div>
					</td>
					<td class="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
						<div class="flex flex-row w-max">
							<div class=" font-medium self-center">{perm.category}</div>
						</div>
					</td>
					<td class="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
						<div class="flex flex-row w-max">
							<div class=" font-medium self-center">{perm.name}</div>
						</div>
					</td>
					<td class="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
						<div class="flex flex-row w-max">
							<div class=" font-medium self-center">{perm.label}</div>
						</div>
					</td>
					<td class="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
						<div class="flex flex-row w-max">
							<div class=" font-medium self-center">{perm.description}</div>
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
