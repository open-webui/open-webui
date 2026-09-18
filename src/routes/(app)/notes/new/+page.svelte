<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from '$lib/dayjs';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { createNoteHandler } from '$lib/components/notes/utils';

	const i18n: Writable<i18nType> = getContext('i18n');
	let showConfirmation = false;
	let creating = false;
	let title = '';
	let content = '';
	let sourceUrl = '';

	onMount(() => {
		if (window.self !== window.top) {
			goto('/notes', { replaceState: true });
			return;
		}

		sourceUrl = $page.url.href;
		title = $page.url.searchParams.get('title') ?? dayjs().format('YYYY-MM-DD');
		content = $page.url.searchParams.get('content') ?? '';
		showConfirmation = true;
	});

	const createNote = async () => {
		if (creating || window.self !== window.top || $page.url.href !== sourceUrl) {
			return;
		}

		creating = true;
		const res = await createNoteHandler(title, content);

		if (res) {
			goto(`/notes/${res.id}`, { replaceState: true });
		} else {
			creating = false;
			showConfirmation = true;
		}
	};
</script>

<ConfirmDialog
	bind:show={showConfirmation}
	title={$i18n.t('New Note')}
	confirmLabel={$i18n.t('Create')}
	on:confirm={createNote}
	on:cancel={() => goto('/notes', { replaceState: true })}
>
	<dl class="text-sm max-h-80 overflow-y-auto">
		<dt class="font-medium">{$i18n.t('Title')}</dt>
		<dd class="mt-1 whitespace-pre-wrap break-words text-gray-500">{title}</dd>
		<dt class="mt-4 font-medium">{$i18n.t('Content')}</dt>
		<dd class="mt-1 whitespace-pre-wrap break-words text-gray-500">{content}</dd>
	</dl>
</ConfirmDialog>
