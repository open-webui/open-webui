<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { isValidHttpUrl } from '$lib/utils';

	const i18n = getContext('i18n');

	export let show = false;
	export let onSubmit: Function = () => {};

	let url = '';

	const submitHandler = () => {
		const urls = url
			.split('\n')
			.map((u) => u.trim())
			.filter((u) => u !== '');

		const validUrls = urls.filter((u) => isValidHttpUrl(u));

		if (validUrls.length === 0) {
			toast.error($i18n.t('Please enter at least one valid URL.'));
			return;
		}

		onSubmit({ type: 'web', data: validUrls });
		show = false;
		url = '';
	};
</script>

<Modal size="sm" bind:show>
	<div class="px-4 py-3">
		<div class="flex justify-between items-center mb-3">
			<div class="text-lg font-bold">{$i18n.t('Attach Webpage')}</div>
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

		<div class="flex flex-col w-full">
			<div class="mb-2 text-xs text-gray-500">
				{$i18n.t('Enter one URL per line.')}
			</div>

			<textarea
				class="w-full h-32 p-2 rounded-lg bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-800 outline-hidden resize-none text-sm"
				placeholder={$i18n.t('Enter URLs here...')}
				bind:value={url}
			/>

			<div class="flex justify-end mt-3">
				<button
					class="px-4 py-2 bg-black text-white dark:bg-white dark:text-black rounded-full font-medium text-sm transition hover:opacity-80"
					on:click={submitHandler}
				>
					{$i18n.t('Add')}
				</button>
			</div>
		</div>
	</div>
</Modal>
