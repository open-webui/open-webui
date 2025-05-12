<script>
	import { tick } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import AddLinkIcon from '$lib/components/icons/AddLinkIcon.svelte';
    import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let text = '';
	export let label = '';
	let textareaEl;
	let showLinkEditor = false;
	let selectedText = '';
	let linkUrl = '';
	let selectionStart = 0;
	let selectionEnd = 0;

	function prepareLinkEditor() {
		selectionStart = textareaEl.selectionStart;
		selectionEnd = textareaEl.selectionEnd;

		if (selectionStart === selectionEnd) {
            toast.error($i18n.t('Select word to add link'))
            return;
        }

		selectedText = text.slice(selectionStart, selectionEnd);
		console.log(selectedText);
		showLinkEditor = true;
		linkUrl = '';
	}

	async function insertLink() {
		if (!linkUrl || !selectedText) return;

		const before = text.slice(0, selectionStart);
		const after = text.slice(selectionEnd);

		const linkedText = `<a href="${linkUrl}" target="_blank" rel="noopener">${selectedText}</a>`;
		text = before + linkedText + after;

		showLinkEditor = false;
		selectedText = '';
		linkUrl = '';

		await tick();
		textareaEl.focus();
	}
</script>

<div class="flex flex-col w-full mb-2.5 relative">
	<div class="relative w-full dark:bg-customGray-900 rounded-md">
		{#if text}
			<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
				{label}
			</div>
		{/if}
		<textarea
			rows={3}
			class={`pl-2.5 pr-4 text-sm pt-4 w-full bg-transparent dark:text-customGray-100 dark:placeholder:text-customGray-100 outline-none`}
			placeholder={label}
			bind:this={textareaEl}
			bind:value={text}
		/>
	</div>
	<button on:click={prepareLinkEditor} class="absolute right-2 w-4 h-4 top-4">
		<AddLinkIcon />
	</button>
	{#if showLinkEditor}
		<div
			class="absolute top-20 rounded p-3 dark:bg-customGray-900 flex items-end justify-between w-full border dark:border-customGray-700"
		>
			<button
				on:click={() => {
					showLinkEditor = false;
					selectedText = '';
					linkUrl = '';
				}}
				class="absolute top-2 right-2 text-gray-500 text-xs"
				aria-label="Close"
			>
				✕
			</button>
			<div class="w-24 mr-1">
				<label class="block text-xs dark:text-customGray-100/50">{$i18n.t('Selected Text')}</label>
				<input
					type="text"
					bind:value={selectedText}
					class="w-full outline-none text-sm border dark:text-customGray-100 p-1 bg-transparent dark:border-customGray-700 rounded-md"
				/>
			</div>
			<div class="flex-1">
				<label class="block text-xs dark:text-customGray-100/50">{$i18n.t('URL')}</label>
				<input
					type="text"
					placeholder="https://example.com"
					bind:value={linkUrl}
					class="outline-none w-full text-sm border dark:text-customGray-100 dark:border-customGray-700 rounded-md p-1 bg-transparent"
				/>
			</div>

			<button
				on:click={insertLink}
				class=" ml-1 text-xs dark:text-customGray-200 h-[30px] border dark:border-customGray-700 dark:bg-customGray-950 rounded-lg px-4 py-1"
			>
				{$i18n.t('Insert link')}
			</button>
		</div>
	{/if}
</div>
