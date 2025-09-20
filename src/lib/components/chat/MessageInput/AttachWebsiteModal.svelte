<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { settings } from '$lib/stores';

	const i18n = getContext('i18n');

	export let show = false;
	export let addUrlHandler: (url: string) => void;

	let url = '';

	const handleSubmit = () => {
		if (addUrlHandler) {
			addUrlHandler(url);
		}
		show = false;
		url = '';
	};
</script>

<Modal bind:show size="sm">
	<div class="flex flex-col h-full">
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-1.5">
			<h1 class="text-lg font-medium self-center font-primary">
				{$i18n.t('Attach Website')}
			</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark class="size-5" />
			</button>
		</div>

		<div class="flex-1 px-5 py-2 text-sm text-gray-600 dark:text-gray-400">
			{$i18n.t('Enter a web address (URL) to automatically fetch its content and attach it as a document to your chat.')}
		</div>

		<div class="px-5 pb-5">
			<form on:submit|preventDefault={handleSubmit}>
				<label for="url-input" class="sr-only">{$i18n.t('Website URL')}</label>
				<input
					id="url-input"
					class={`w-full text-sm bg-transparent border-gray-300 dark:border-gray-700 border rounded-lg p-2 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-500'}`}
					type="text"
					bind:value={url}
					placeholder={$i18n.t("e.g. https://example.com or a YouTube Video URL")}
					required
					autocomplete="off"
				/>
			</form>
		</div>

		<div class="flex justify-end gap-2 p-4 pt-1 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl">
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-white hover:bg-gray-100 text-gray-700 dark:text-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition rounded-full"
				on:click={() => {
					show = false;
				}}
			>
				{$i18n.t('Close')}
			</button>
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full"
				on:click={handleSubmit}
			>
				{$i18n.t('Add')}
			</button>
		</div>
	</div>
</Modal>
