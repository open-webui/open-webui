<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import dayjs from '$lib/dayjs';
	import { folders, pinnedNotes, settings, user } from '$lib/stores';
	import {
		getNoteById,
		getPinnedNoteList,
		toggleNotePinnedStatusById,
		updateNoteById,
		updateNoteFolderIdById
	} from '$lib/apis/notes';
	import { refreshFolderChatLists } from '$lib/stores/chatList';
	import {
		capitalizeFirstLetter,
		copyToClipboard,
		formatDateDetails,
		formatShortDate
	} from '$lib/utils';
	import { downloadNote, setNoteDragData } from '../utils';

	import FolderTags from '$lib/components/chat/Placeholder/FolderTags.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import NoteMenu from './NoteMenu.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	/** A note's row in the notes page and in a folder. */
	export let note: any;
	export let href: string;
	export let editable = true;
	export let snippet = '';
	export let showFolder = false;
	/** Shift is held: the menu becomes a delete button. */
	export let shiftKey = false;
	export let onOpen: (href: string) => void;
	export let onChange: () => Promise<void> = async () => {};
	/** Null when the user may not delete the note. */
	export let onDelete: ((confirm: boolean) => void) | null = null;
	export let onAccess: (() => void) | null = null;

	let element: HTMLLIElement;
	let menuOpen = false;
	$: if (shiftKey) menuOpen = false;

	$: folder = note.folder_id ? $folders.find((item) => item.id === note.folder_id) : null;

	// Inline rename, like the folder chat list.
	let renaming = false;
	let renameValue = '';
	const startRename = async () => {
		renaming = true;
		renameValue = note.title;
		await tick();
		const input = element?.querySelector<HTMLInputElement>('[data-rename-input]');
		input?.focus();
		input?.select();
	};
	const saveRename = async () => {
		if (!renaming) return;
		const title = renameValue.trim();
		renaming = false;
		if (!title || title === note.title) return;

		const res = await updateNoteById(localStorage.token, note.id, { title }).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!res) return;

		note = { ...note, title };
		pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
		await onChange();
	};

	const moveHandler = async (folderId: string | null) => {
		const previous = note.folder_id;
		const res = await updateNoteFolderIdById(localStorage.token, note.id, folderId).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);
		if (!res) return;

		toast.success($i18n.t('Note moved successfully'));
		await onChange();
		for (const id of [previous, folderId]) if (id) void refreshFolderChatLists(id);
	};

	const downloadHandler = async (type: string) => {
		// Fetch the full note since the list response may not contain full content
		try {
			await downloadNote(await getNoteById(localStorage.token, note.id), type);
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const copyLinkHandler = async () => {
		if (await copyToClipboard(`${window.location.origin}/notes/${note.id}`))
			toast.success($i18n.t('Copied link to clipboard'));
		else toast.error($i18n.t('Failed to copy link'));
	};

	const pinHandler = async () => {
		await toggleNotePinnedStatusById(localStorage.token, note.id);
		pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
	};

	const clickHandler = (event: MouseEvent) => {
		if ((event.target as Element).closest('a, button, input, [role="menu"]')) return;
		if (window.getSelection()?.toString()) return;
		onOpen(href);
	};
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
<li
	bind:this={element}
	data-note-item
	class="group flex min-h-8 w-full cursor-pointer items-center gap-2 rounded-xl px-2 py-[0.375rem] text-left transition hover:bg-base-50 focus-within:bg-base-50 dark:hover:bg-base-900 dark:focus-within:bg-base-900"
	draggable={!renaming}
	on:dragstart={(event) => setNoteDragData(event, note, href)}
	on:click={clickHandler}
>
	<div class="flex min-w-0 flex-1 items-center gap-2">
		{#if renaming}
			<input
				data-rename-input
				class="min-w-0 flex-1 bg-transparent text-[0.8125rem] leading-5 text-base-900 outline-none dark:text-base-0"
				aria-label={$i18n.t('Rename')}
				bind:value={renameValue}
				on:blur={saveRename}
				on:keydown={(event) => {
					if (event.isComposing || event.keyCode === 229) return;
					if (event.key === 'Enter') {
						event.preventDefault();
						saveRename();
					} else if (event.key === 'Escape') {
						event.preventDefault();
						renaming = false;
					}
				}}
			/>
		{:else}
			<Tooltip content={note.title} className="min-w-0" placement="top-start">
				<a
					data-row-link
					{href}
					dir="auto"
					class="focus-ring block h-[1.25rem] truncate rounded text-[0.8125rem] leading-5 text-base-800 group-hover:underline focus-visible:underline dark:text-base-200"
					on:click={(event) => {
						if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
						event.preventDefault();
						onOpen(href);
					}}
				>
					{note.title}
				</a>
			</Tooltip>

			{#if showFolder && folder}
				<span
					class="hidden max-w-28 shrink-0 truncate text-[0.6875rem] text-base-400 @md:block dark:text-base-500"
					>{folder.name}</span
				>
			{/if}

			{#if snippet}
				<span
					dir="auto"
					class="hidden min-w-0 flex-1 truncate text-xs text-base-400 @lg:block dark:text-base-500"
					>{snippet}</span
				>
			{/if}
		{/if}
	</div>

	<div class="ml-2 flex shrink-0 items-center justify-end gap-3">
		<div class="hidden @md:flex">
			<FolderTags resourceType="notes" chat={note} {editable} {onChange} />
		</div>
		<div
			class="hidden max-w-44 shrink-0 truncate text-right text-[0.6875rem] leading-5 text-base-500 dark:text-base-500 md:block"
		>
			<Tooltip
				content={note?.user?.email ?? $i18n.t('Deleted User')}
				className="min-w-0"
				placement="top-start"
			>
				<span class="flex min-w-0 max-w-44 items-center gap-1.75">
					<ProfileImage
						src={note?.user?.id ? `/api/v1/users/${note.user.id}/profile/image` : '/user.png'}
						className="size-4 shrink-0 rounded-full!"
					/>
					<span class="min-w-0 max-w-24 truncate">
						{capitalizeFirstLetter(
							note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
						)}
					</span>
				</span>
			</Tooltip>
		</div>

		<!-- The menu takes the date's place on hover, so nothing shifts. -->
		<div
			class="date-slot relative flex w-14 shrink-0 items-center justify-end"
			class:open={(shiftKey && onDelete) || menuOpen}
		>
			<Tooltip
				as="span"
				className="row-date flex shrink-0"
				placement="top-end"
				content={formatDateDetails(note.updated_at / 1000000000, $i18n.language)}
			>
				<time
					class="w-14 text-right text-[0.6875rem] tabular-nums text-base-400 dark:text-base-500"
					datetime={dayjs(note.updated_at / 1000000).toISOString()}
					>{formatShortDate(note.updated_at / 1000000000, $i18n.language)}</time
				>
			</Tooltip>

			<div class="note-menu absolute inset-y-0 right-0 flex items-center">
				{#if shiftKey && onDelete}
					<Tooltip content={$i18n.t('Delete')}>
						<button
							class="flex {($settings?.highContrastMode ?? false)
								? 'size-6'
								: 'size-5'} shrink-0 items-center justify-center rounded-lg text-base-400 transition hover:text-base-700 dark:text-base-500 dark:hover:text-base-200"
							type="button"
							aria-label={$i18n.t('Delete')}
							on:click={(e) => {
								e.preventDefault();
								e.stopPropagation();
								onDelete?.(false);
							}}
						>
							<GarbageBin className="size-3.5" />
						</button>
					</Tooltip>
				{:else}
					<NoteMenu
						{onAccess}
						show={menuOpen}
						folderId={note.folder_id}
						onRename={editable ? startRename : null}
						onMove={note.user_id === $user?.id ? moveHandler : null}
						onDownload={downloadHandler}
						onCopyLink={copyLinkHandler}
						onDelete={onDelete ? () => onDelete?.(true) : null}
						isPinned={$pinnedNotes.some((n) => n.id === note.id)}
						onPin={pinHandler}
						onChange={(state) => {
							menuOpen = state;
						}}
					>
						<button
							class="flex {($settings?.highContrastMode ?? false)
								? 'size-6'
								: 'size-5'} shrink-0 items-center justify-center rounded-lg text-base-400 transition hover:text-base-700 dark:text-base-500 dark:hover:text-base-200"
							type="button"
							aria-label={$i18n.t('Note Menu')}
							on:click={(e) => {
								e.preventDefault();
								e.stopPropagation();
								menuOpen = !menuOpen;
							}}
						>
							<EllipsisHorizontal className="size-3.5" />
						</button>
					</NoteMenu>
				{/if}
			</div>
		</div>
	</div>
</li>

<style>
	/* The menu replaces the date on hover, focus, or while open; touch shows the menu. */
	@media (hover: hover) {
		.date-slot:not(.open) .note-menu {
			opacity: 0;
			pointer-events: none;
		}
		:global([data-note-item]:hover) .date-slot .note-menu,
		:global([data-note-item]:focus-within) .date-slot .note-menu {
			opacity: 1;
			pointer-events: auto;
		}
		.date-slot.open :global(.row-date),
		:global([data-note-item]:hover) .date-slot :global(.row-date),
		:global([data-note-item]:focus-within) .date-slot :global(.row-date) {
			opacity: 0;
		}
	}
	@media (hover: none) {
		.date-slot :global(.row-date) {
			opacity: 0;
		}
	}
</style>
