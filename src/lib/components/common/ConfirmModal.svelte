<script>
	import { getContext, createEventDispatcher } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte'

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let title = '';
	export let content = '';

</script>

<Modal bind:show size="sm">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
			<div class=" text-lg font-medium self-center">{title}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
					dispatch('cancel');
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

		<div class="md:flex-row w-full px-10 py-4 md:space-x-4">
			{content}
			<div class="flex justify-end pt-5 text-sm font-medium">
				<button
				class=" px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white transition rounded-lg mr-4"
				on:click={() => {
					dispatch('cancel');
					show = false;
				}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
					on:click={() => {
						dispatch('confirm');
						show = false;
					}}
				>
					{$i18n.t('Confirm')}
				</button>
			</div>
		</div>
	</div>
</Modal>
