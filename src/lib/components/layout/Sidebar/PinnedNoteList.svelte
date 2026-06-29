<script>
	import Sortable from 'sortablejs';

	import { onMount, getContext, tick } from 'svelte';

	import { chatId, mobile, pinnedNotes, settings, showSidebar } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { getPinnedNoteList, toggleNotePinnedStatusById } from '$lib/apis/notes';
	import Note from '$lib/components/icons/Note.svelte';

	const i18n = getContext('i18n');

	export let selectedChatId = null;

	$: sortedPinnedNotes = (() => {
		const order = $settings?.pinnedNotesOrder;
		if (!order || order.length === 0) return $pinnedNotes;
		const orderMap = new Map(order.map((id, idx) => [id, idx]));
		return [...$pinnedNotes].sort((a, b) => {
			const aIdx = orderMap.has(a.id) ? orderMap.get(a.id) : Infinity;
			const bIdx = orderMap.has(b.id) ? orderMap.get(b.id) : Infinity;
			return aIdx - bIdx;
		});
	})();

	const initPinnedNotesSortable = () => {
		const pinnedNotesList = document.getElementById('pinned-notes-list');
		if (pinnedNotesList && !$mobile) {
			new Sortable(pinnedNotesList, {
				animation: 150,
				setData: function (dataTransfer, dragEl) {
					dataTransfer.setData(
						'text/plain',
						JSON.stringify({
							type: 'note',
							id: dragEl.dataset.id
						})
					);
					dataTransfer.setData('application/x-open-webui-drag', '');
				},
				onUpdate: async (event) => {
					const noteId = event.item.dataset.id;
					const newIndex = event.newIndex;
					const current = sortedPinnedNotes.map((n) => n.id);
					const oldIndex = current.indexOf(noteId);
					current.splice(oldIndex, 1);
					current.splice(newIndex, 0, noteId);
					settings.set({ ...$settings, pinnedNotesOrder: current });
					await updateUserSettings(localStorage.token, { ui: $settings });
				}
			});
		}
	};

	onMount(async () => {
		await tick();
		initPinnedNotesSortable();
	});
</script>

<div class="mt-0.5 pb-1.5" id="pinned-notes-list">
	{#each sortedPinnedNotes as note (note.id)}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="flex items-center text-gray-800 dark:text-gray-200 cursor-grab relative group rounded-xl px-2.5 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
			data-id={note.id}
		>
			<a
				class="grow flex items-center gap-2.5 text-sm"
				href={`/notes/${note.id}`}
				on:click={() => {
					selectedChatId = null;
					chatId.set('');
					if ($mobile) {
						showSidebar.set(false);
					}
				}}
				draggable="false"
			>
				<div class="self-center">
					<Note className="size-4" strokeWidth="2" />
				</div>
				<div class="flex-1 text-ellipsis line-clamp-1">
					{note.title}
				</div>
			</a>
			<button
				class="invisible group-hover:visible self-center p-0.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg transition"
				on:click|preventDefault|stopPropagation={async () => {
					await toggleNotePinnedStatusById(localStorage.token, note.id);
					const _pinnedNotes = await getPinnedNoteList(localStorage.token).catch(() => []);
					pinnedNotes.set(_pinnedNotes);
				}}
				aria-label={$i18n.t('Unpin')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-3.5"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
				</svg>
			</button>
		</div>
	{/each}
</div>
