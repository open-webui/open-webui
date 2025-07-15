<script>
	import { getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from './AccessControl.svelte';
	let accessControlRef;

	export let show = false;
	export let accessControl = {};
	export let accessRoles = ['read'];
	export let allowPublic = true;

	const dispatch = createEventDispatcher();

	function commitChanges() {
		if (accessControlRef && accessControlRef.commitChanges) {
			accessControlRef.commitChanges();
			dispatch('save', accessControl);
			show = false;
		}
}
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-3 pb-1">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Access Control')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="w-full px-5 pb-4 dark:text-white">
			<AccessControl bind:accessControl bind:this={accessControlRef} {accessRoles} {allowPublic} />

			<div class="flex justify-end mt-4">
				<button
					class="text-sm w-full lg:w-fit px-4 py-2 transition rounded-lg bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black flex w-full justify-center"
					type="button"
					on:click={commitChanges}
				>
					{$i18n.t('Save')}
				</button>
			</div>
		</div>
	</div>
</Modal>
