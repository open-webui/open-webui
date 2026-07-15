<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MemberSelector from '$lib/components/workspace/common/MemberSelector.svelte';

	export let show = false;
	export let shareUsers = true;
	export let allowGroups = true;
	export let accessGrants: { principal_type: string; principal_id: string }[] = [];
	export let onAdd = (payload: { userIds: string[]; groupIds: string[] }) => {};

	let userIds: string[] = [];
	let groupIds: string[] = [];
	let loading = false;

	const submitHandler = () => {
		loading = true;
		onAdd({ userIds, groupIds });
		show = false;

		userIds = [];
		groupIds = [];
		loading = false;
	};
</script>

<Modal size="sm" bind:show>
		<div>
			<div class="flex justify-between dark:text-gray-100 px-4 pt-3 mb-1">
				<div class="self-center text-sm font-medium">
					<div class="flex items-center gap-0.5 shrink-0">
						{$i18n.t('Add Access')}
					</div>
				</div>
				<button
					class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-4'} />
				</button>
			</div>

			<div class="flex flex-col md:flex-row w-full px-3 pb-3 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="flex flex-col w-full h-full pb-2">
						<MemberSelector
							bind:userIds
							bind:groupIds
							includeGroups={allowGroups}
							includeUsers={shareUsers}
							includeSessionUser={false}
							{accessGrants}
						/>
					</div>

					<div class="flex justify-end pt-2 text-sm font-normal gap-1.5">
						<button
							class="px-3 py-1.5 text-sm font-normal bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
							type="submit"
						>
							{$i18n.t('Add')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
