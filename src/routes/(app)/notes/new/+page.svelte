<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from '$lib/dayjs';
	import { createNoteHandler } from '$lib/components/notes/utils';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext<Writable<I18n>>('i18n');
	const title = $page.url.searchParams.get('title') ?? dayjs().format('YYYY-MM-DD');
	const content = $page.url.searchParams.get('content') ?? '';
	let showConfirm = true;

	const createNote = async () => {
		const res = await createNoteHandler(title, content);

		if (res) {
			goto(`/notes/${res.id}`, { replaceState: true });
		} else {
			showConfirm = true;
		}
	};
</script>

<ConfirmDialog
	bind:show={showConfirm}
	title={$i18n.t('Create a new note')}
	on:confirm={createNote}
	on:cancel={() => goto('/notes', { replaceState: true })}
>
	<div class="text-sm text-gray-500 whitespace-pre-wrap break-words max-h-60 overflow-auto">
		<div class="font-medium">{title}</div>
		{content}
	</div>
</ConfirmDialog>
