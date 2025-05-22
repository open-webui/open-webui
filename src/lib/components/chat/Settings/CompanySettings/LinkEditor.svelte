<script>
	import { onMount, createEventDispatcher, getContext } from 'svelte';
	import { Editor } from '@tiptap/core';
	import StarterKit from '@tiptap/starter-kit';
	import Link from '@tiptap/extension-link';
	import AddLinkIcon from '$lib/components/icons/AddLinkIcon.svelte';
	import { companyConfig } from '$lib/stores';

	const i18n = getContext('i18n');
	let editor;
	let url = '';
	let showLinkInput = false;
	
	const dispatch = createEventDispatcher();

	onMount(() => {
		editor = new Editor({
			element: document.querySelector('#editor'),
			extensions: [
				StarterKit,
				Link.configure({
					openOnClick: false
				})
			],
			content: $companyConfig?.config?.ui?.custom_user_notice ? $companyConfig?.config?.ui?.custom_user_notice : 'LLMs can make mistakes. Verify important information.',
			onUpdate: ({ editor }) => {
				dispatch('updateContent', editor.getHTML());
			}
		});
	});

	function setLink() {
		if (!editor) return;
		const previousUrl = editor.getAttributes('link').href;
		url = previousUrl || '';
		showLinkInput = true;
	}

	function applyLink() {
		editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
		showLinkInput = false;
		url = '';
	}

	function removeLink() {
		editor.chain().focus().unsetLink().run();
		showLinkInput = false;
		url = '';
	}
</script>

<div class="relative">
	<div class="{editor?.getHTML() === '<p></p>' ? 'text-sm' : 'text-xs'} absolute text-lightGray-100/50 left-2.5 top-1 dark:text-customGray-100/50">
		{$i18n.t('User notice')}
	</div>
	<div
		id="editor"
		class="prose rounded p-2 px-2.5 text-lightGray-100 bg-lightGray-300 dark:bg-customGray-900 min-h-[48px] dark:text-customGray-100"
	></div>
	<button on:click={setLink} class="absolute right-2 w-4 h-4 top-4">
		<AddLinkIcon />
	</button>

	{#if showLinkInput}
		<div>
			<div class="mt-2 flex flex-col md:flex-row">
				<input
					type="url"
					bind:value={url}
					placeholder="Enter URL"
					class="outline-none mb-2 md:mb-0 text-sm md:mr-2 text-lightGray-100 placeholder:text-lightGray-100 dark:text-customGray-100 rounded-md p-1 bg-lightGray-300 dark:bg-customGray-900 w-full md:w-[300px]"
				/>
				<div class="flex items-center">
					<button
						on:click={applyLink}
						class=" mr-2 text-xs dark:text-customGray-200 h-[30px] border dark:border-customGray-700 bg-lightGray-300 dark:bg-customGray-950 rounded-lg px-4 py-1"
						>{$i18n.t('Apply')}</button
					>
					<button on:click={removeLink} class="text-xs dark:text-customGray-200">{$i18n.t('Remove Link')}</button>
				</div>
			</div>
		</div>
	{/if}
</div>
