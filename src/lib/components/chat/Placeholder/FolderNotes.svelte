<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import type { AppLayoutContext } from '$lib/types';
	import dayjs from '$lib/dayjs';
	import { user, pinnedNotes } from '$lib/stores';
	import { closePageTabs } from '$lib/stores/chatViewStates';
	import { deleteNoteById, getPinnedNoteList } from '$lib/apis/notes';
	import { createNoteHandler, groupNotes } from '$lib/components/notes/utils';
	import NoteItem from '$lib/components/notes/Notes/NoteItem.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	/** The folder's notes as a list; they open as their own page, in a tab beside the folder. */
	export let folderId: string;
	export let notes: any[] = [];
	export let total = 0;
	export let loading = false;
	export let canCreate = false;
	export let onReload: () => Promise<void>;
	export let onMore: () => Promise<void>;

	let deleting: any = null;
	let showDelete = false;

	function open(href: string, label = '') {
		if (appLayout?.openPageTab) appLayout.openPageTab({ href, label });
		else void goto(href);
	}

	export async function startNew() {
		const note = await createNoteHandler(
			dayjs().locale($i18n.language).format('YYYY-MM-DD'),
			'',
			'',
			folderId
		);
		if (!note) return;
		open(`/notes/${note.id}`, note.title);
		await onReload();
	}

	async function remove(note: any) {
		const res = await deleteNoteById(localStorage.token, note.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!res) return;
		closePageTabs(`/notes/${note.id}`);
		pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
		await onReload();
	}
</script>

<DeleteConfirmDialog
	bind:show={showDelete}
	title={$i18n.t('Delete note?')}
	on:confirm={() => remove(deleting)}
>
	<div class="truncate text-sm text-base-500">
		{$i18n.t('This will delete')} <span class="font-normal">{deleting?.title}</span>.
	</div>
</DeleteConfirmDialog>

{#if loading && !notes.length}
	<div class="flex h-full items-center justify-center"><Spinner className="size-4" /></div>
{:else if !notes.length}
	<div class="flex h-full flex-col items-center justify-center gap-1 px-6 pb-16 text-center">
		<div class="text-sm text-base-800 dark:text-base-100">{$i18n.t('No Notes')}</div>
		{#if canCreate}
			<button
				type="button"
				class="mt-2 text-xs text-base-400 transition-colors hover:text-base-600 dark:text-base-500 dark:hover:text-base-300"
				on:click={startNew}>{$i18n.t('New Note')}</button
			>
		{/if}
	</div>
{:else}
	{@const groups = groupNotes(notes)}
	<div class="scrollbar-hidden h-full overflow-y-auto px-3 pt-1.5 pb-6 @container">
		{#each groups as [timeRange, notesList], idx (timeRange)}
			<div class="w-full px-2 pb-1 text-xs text-base-500 dark:text-base-500">
				{$i18n.t(timeRange)}
			</div>
			<ul
				class="{groups.length - 1 !== idx ? 'mb-3' : ''} flex flex-col gap-y-0.5"
				aria-label={$i18n.t(timeRange)}
			>
				{#each notesList as note (note.id)}
					<NoteItem
						{note}
						href={`/notes/${note.id}`}
						editable={note.write_access}
						onOpen={(href) => open(href, note.title)}
						onChange={onReload}
						onDelete={note.user_id === $user?.id || $user?.role === 'admin'
							? () => {
									deleting = note;
									showDelete = true;
								}
							: null}
					/>
				{/each}
			</ul>
		{/each}
		{#if notes.length < total}
			<Loader on:visible={onMore}>
				<div class="flex h-10 items-center justify-center"><Spinner className="size-3.5" /></div>
			</Loader>
		{/if}
	</div>
{/if}
