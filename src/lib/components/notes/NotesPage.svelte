<script>
	import { getPageContext } from '$lib/utils/page';
	const { goto, url: pageUrl, tab: pageTab } = getPageContext();

	import { getContext, onMount } from 'svelte';

	import dayjs from '$lib/dayjs';
	import { showSidebar } from '$lib/stores';

	import { createNoteHandler } from '$lib/components/notes/utils';

	import Notes from '$lib/components/notes/Notes.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');
	const title = $pageUrl.searchParams.get('title') ?? dayjs().format('YYYY-MM-DD');
	const content = $pageUrl.searchParams.get('content') ?? '';
	let loaded = false;
	let showConfirm = false;

	onMount(() => {
		if (
			$pageUrl.searchParams.get('content') !== null ||
			$pageUrl.searchParams.get('title') !== null
		) {
			showConfirm = true;
		}

		loaded = true;
	});
</script>

<ConfirmDialog
	bind:show={showConfirm}
	title={$i18n.t('Create a new note')}
	on:confirm={async () => {
		const res = await createNoteHandler(title, content);
		if (res) goto(`/notes/${res.id}`, { replaceState: true });
		else showConfirm = true;
	}}
>
	<div class="text-sm text-gray-500 whitespace-pre-wrap break-words max-h-60 overflow-auto">
		<div class="font-medium">{title}</div>
		{content}
	</div>
</ConfirmDialog>

<div
	class="flex flex-col w-full h-full max-h-full transition-width duration-200 ease-in-out {$showSidebar &&
	!pageTab
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex-1 max-h-full overflow-y-auto">
		{#if loaded}
			<div class="pb-1 px-1.5 md:px-2.5">
				<Notes />
			</div>
		{:else}
			<div class="w-full h-full flex justify-center items-center">
				<Spinner className="size-5" />
			</div>
		{/if}
	</div>
</div>
