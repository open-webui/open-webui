<script lang="ts">
	import Modal from './Modal.svelte';
	import { createEventDispatcher } from 'svelte';

	export let show = false;
	export let title = '';
	export let message = '';

	let confirmText = '';

	const dispatch = createEventDispatcher();

	const onConfirm = () => {
		if (confirmText === 'REVOKE') {
			dispatch('confirm');
		}
	};
</script>

<Modal bind:show on:close>
	<div class="p-4">
		<h3 class="text-lg font-medium leading-6 text-gray-900 dark:text-gray-100">{title}</h3>
		<div class="mt-2">
			<p class="text-sm text-gray-500 dark:text-gray-300">
				{@html message}
			</p>
		</div>

		<div class="mt-4">
			<input
				type="text"
				bind:value={confirmText}
				class="w-full px-3 py-2 text-gray-700 bg-gray-100 border border-gray-300 rounded-md dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
				placeholder="Type REVOKE to confirm"
			/>
		</div>

		<div class="mt-4 flex justify-end space-x-2">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
				on:click={() => (show = false)}
			>
				Cancel
			</button>
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
				disabled={confirmText !== 'REVOKE'}
				on:click={onConfirm}
			>
				Revoke All
			</button>
		</div>
	</div>
</Modal>
