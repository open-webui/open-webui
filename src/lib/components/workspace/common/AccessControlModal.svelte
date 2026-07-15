<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from './AccessControl.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group';
		principal_id: string;
		permission: 'read' | 'write';
	};

	export let show = false;
	export let accessGrants: AccessGrant[] = [];
	export let accessControl: any = undefined;
	export let accessRoles = ['read'];

	export let share = true;
	export let sharePublic = true;
	export let shareUsers = true;

	export let onChange = () => {};
</script>

<Modal size="sm" bind:show>
		<div>
			<div class="flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
				<div class="text-base font-normal self-center">
					{$i18n.t('Access Control')}
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

			<div class="w-full px-4 pb-3 dark:text-white">
				<AccessControl
				bind:accessGrants
				bind:accessControl
				{onChange}
				{accessRoles}
				{share}
				{sharePublic}
				{shareUsers}
			/>
		</div>
	</div>
</Modal>
