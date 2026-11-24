<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { readable, type Readable } from 'svelte/store';

	import { getKnowledgeById } from '$lib/apis/knowledge';
	import { embed as openedEmbed, showEmbeds, showTabs } from '$lib/stores';
	import FileContextSwitch from '$lib/components/common/FileContextSwitch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Files from '$lib/components/workspace/Knowledge/KnowledgeBase/Files.svelte';
	import {
		fileName,
		type KnowledgeFile
	} from '$lib/components/workspace/Knowledge/KnowledgeBase/types';

	const i18n: any = getContext('i18n');

	/** The knowledge base this tab browses. */
	export let embed: any;
	/** The chat the tab is in now; one opened before its chat was saved has none of its own. */
	export let chatId = '';

	let knowledge: any = null;
	let loading = true;
	let selectedFileId: string | null = null;
	let query = '';
	let inputQuery = '';
	let debounce: ReturnType<typeof setTimeout>;

	$: external = knowledge?.meta?.source === 'external';
	// Still attached, so how it is sent can be changed
	const NO_FILES: Readable<any[]> = readable([]);
	let attachedFiles = NO_FILES;
	$: attachedFiles = embed.file.attachedFiles ?? NO_FILES;
	$: attachment = $attachedFiles.includes(embed.file.attachment) ? embed.file.attachment : null;

	// A file opens in its own tab, as cited and attached files do
	const open = (file: KnowledgeFile) => {
		selectedFileId = file.id ?? null;
		showTabs.set(true);
		showEmbeds.set(true);
		openedEmbed.set({
			file: { id: file.id, page: null, passages: [], content: '' },
			title: fileName(file),
			chatId: embed.chatId || chatId
		});
	};

	onMount(async () => {
		knowledge = await getKnowledgeById(localStorage.token, embed.file.knowledgeId).catch(
			() => null
		);
		loading = false;
	});
	onDestroy(() => clearTimeout(debounce));
</script>

<div class="flex h-full w-full flex-col">
	<div class="flex h-7 shrink-0 items-center gap-1 px-2 text-xs text-base-500 dark:text-base-400">
		{#if knowledge && !external}
			<Search className="mx-1 size-3.5 shrink-0" />
			<input
				aria-label={$i18n.t('Search Files')}
				placeholder={$i18n.t('Search Files')}
				bind:value={inputQuery}
				class="h-7 min-w-0 flex-1 bg-transparent px-1 outline-none"
				on:input={() => {
					clearTimeout(debounce);
					debounce = setTimeout(() => (query = inputQuery.trim()), 300);
				}}
			/>
		{:else}
			<span class="flex-1"></span>
		{/if}
		{#if attachment && !loading}
			<div class="shrink-0 px-1.5">
				<FileContextSwitch
					item={attachment}
					externalKnowledge={external}
					onChange={embed.file.onAttachmentChange}
				/>
			</div>
		{/if}
	</div>

	{#if loading || !knowledge || external}
		<div class="flex flex-1 items-center justify-center text-xs text-base-500 dark:text-base-400">
			{#if loading}
				<Spinner className="size-3.5" />
			{:else}
				{$i18n.t(knowledge ? 'No files found' : 'Preview failed')}
			{/if}
		</div>
	{:else}
		<Files
			knowledge={{ ...knowledge, write_access: false }}
			{selectedFileId}
			bind:query
			sortKey="name"
			direction="asc"
			onSelect={open}
		/>
	{/if}
</div>
