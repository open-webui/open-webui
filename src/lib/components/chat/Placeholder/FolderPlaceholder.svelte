<script>
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { fade } from 'svelte/transition';

	import ChatList from './ChatList.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getChatListByFolderId } from '$lib/apis/chats';
	import { getKnowledgeById } from '$lib/apis/knowledge';
	import { getNoteById } from '$lib/apis/notes';
	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	export let folder = null;

	let selectedTab = 'chats';

	let chats = null;
	let page = 1;
	let notes = null;
	let notesPage = 1;
	let collections = null;
	const setChatList = async () => {
		chats = null;

		if (folder && folder.id) {
			const res = await getChatListByFolderId(localStorage.token, folder.id, page);

			if (res) {
				chats = res;
			} else {
				chats = [];
			}
		} else {
			chats = [];
		}
	};

	const setNoteList = async () => {
		notes = null;

		if (folder && folder.id && folder.data?.notes) {
			try {
				const notePromises = folder.data.notes.map((noteId) =>
					getNoteById(localStorage.token, noteId)
				);
				notes = await Promise.all(notePromises);
			} catch (error) {
				console.error('Error loading notes:', error);
				notes = [];
			}
		} else {
			notes = [];
		}
	};

	const setCollectionList = async () => {
		collections = null;

		if (folder && folder.data?.collections) {
			try {
				collections = await Promise.all(
					folder.data.collections.map(async (collectionId) => {
						return await getKnowledgeById(localStorage.token, collectionId).catch(() => null);
					})
				).then((results) => results.filter((c) => c !== null));
			} catch (error) {
				console.error('Error loading notes:', error);
				collections = [];
			}
		} else {
			collections = [];
		}
	};

	$: if (folder) {
		setChatList();
		setNoteList();
		setCollectionList();
	}
</script>

<div>
	<div class="mb-1">
		<div
			class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1"
		>
			<button
				class="min-w-fit p-1.5 {selectedTab === 'knowledge'
					? ''
					: 'text-gray-300 dark:text-gray-600'} transition"
				on:click={() => {
					selectedTab = 'knowledge';
				}}
			>
				{$i18n.t('Knowledge')}
			</button>

			<button
				class="min-w-fit p-1.5 {selectedTab === 'notes'
					? ''
					: 'text-gray-300 dark:text-gray-600'} transition"
				on:click={() => {
					selectedTab = 'notes';
				}}
			>
				{$i18n.t('Notes')}
			</button>

			<button
				class="min-w-fit p-1.5 {selectedTab === 'chats'
					? ''
					: 'text-gray-300 dark:text-gray-600'} transition"
				on:click={() => {
					selectedTab = 'chats';
				}}
			>
				{$i18n.t('Chats')}
			</button>
		</div>
	</div>

	<div class="">
		{#if selectedTab === 'knowledge'}
			{#if collections !== null}
				{#if collections.length > 0}
					<div class="gap-2.5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
						{#each collections as collection}
							<div
								class="flex space-x-4 cursor-pointer w-full px-4.5 py-4 border border-gray-50 dark:border-gray-850 bg-transparent dark:hover:bg-gray-850 hover:bg-white rounded-2xl transition"
							>
								<a href="/workspace/knowledge/{collection.id}" class="w-full">
									<div class="flex flex-col gap-1">
										<div class="font-semibold line-clamp-1 text-sm">
											{collection.name}
										</div>
									</div>
								</a>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-10 text-gray-500">
						<div class="text-sm">{$i18n.t('No collection in this folder')}</div>
					</div>
				{/if}
			{:else}
				<div class="py-10"><Spinner /></div>
			{/if}
		{:else if selectedTab === 'notes'}
			{#if notes !== null}
				{#if notes.length > 0}
					<div class="gap-2.5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
						{#each notes as note}
							<div
								class="flex space-x-4 cursor-pointer w-full px-4.5 py-4 border border-gray-50 dark:border-gray-850 bg-transparent dark:hover:bg-gray-850 hover:bg-white rounded-2xl transition"
							>
								<a href="/notes/{note.id}" class="w-full">
									<div class="flex flex-col gap-1">
										<div class="font-semibold line-clamp-1 text-sm">
											{note.title}
										</div>
										<div class="text-xs text-gray-500 dark:text-gray-500">
											{dayjs(note.updated_at / 1000000).fromNow()}
										</div>
									</div>
								</a>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-10 text-gray-500">
						<div class="text-sm">{$i18n.t('No notes in this folder')}</div>
					</div>
				{/if}
			{:else}
				<div class="py-10"><Spinner /></div>
			{/if}
		{:else if selectedTab === 'chats'}
			{#if chats !== null}
				<ChatList {chats} />
			{:else}
				<div class="py-10">
					<Spinner />
				</div>
			{/if}
		{/if}
	</div>
</div>
