<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import { settings } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { isValidHttpUrl } from '$lib/utils';

	export let show = false;
	export let onSubmit: (e) => void;

	let url = '';

	const highContrastInputClass =
		'rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const submitHandler = () => {
		let urls = url
			.split('\n')
			.map((u) => u.trim())
			.filter((u) => u !== '')
			.filter((u) => isValidHttpUrl(u));

		urls = [...new Set(urls)];

		if (urls.length === 0) {
			toast.error($i18n.t('Please enter a valid URL.'));
			return;
		}

		onSubmit({ type: 'web', data: urls });
		show = false;
		url = '';
	};
</script>

<Modal bind:show size="sm">
	<div class="flex flex-col h-full">
		<div class="flex justify-between items-center dark:text-gray-100 px-4 pt-3 pb-1">
			<h1 class="text-sm font-medium self-center">
				{$i18n.t('Attach Webpage')}
			</h1>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="px-5 pb-4">
			<form
				on:submit={(e) => {
					e.preventDefault();
					submitHandler();
				}}
			>
				<div class="flex justify-between mb-0.5">
					<label
						for="webpage-url"
						class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
						>{$i18n.t('Webpage URLs')}</label
					>
				</div>

				<textarea
					id="webpage-url"
					class={`w-full flex-1 text-sm ${($settings?.highContrastMode ?? false) ? highContrastInputClass : 'bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
					type="text"
					bind:value={url}
					rows="3"
					placeholder={'https://example.com'}
					autocomplete="off"
					required
				/>

				<div class="flex justify-end gap-2 pt-3 bg-gray-50 dark:bg-gray-900/50">
					<button
						class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full"
						type="submit"
					>
						{$i18n.t('Add')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>
