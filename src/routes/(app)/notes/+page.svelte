<script>
	import { onMount } from 'svelte';

	import dayjs from '$lib/dayjs';
	import { showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { createNoteHandler } from '$lib/components/notes/utils';

	import Notes from '$lib/components/notes/Notes.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let loaded = false;

	onMount(async () => {
		if (
			$page.url.searchParams.get('content') !== null ||
			$page.url.searchParams.get('title') !== null
		) {
			const title = $page.url.searchParams.get('title') ?? dayjs().format('YYYY-MM-DD');
			const content = $page.url.searchParams.get('content') ?? '';

			const res = await createNoteHandler(title, content);

			if (res) {
				goto(`/notes/${res.id}`);
			}
			return;
		}

		loaded = true;
	});
</script>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex-1 max-h-full overflow-y-auto">
		{#if loaded}
			<div class="pb-1 px-2.5 pt-2">
				<Notes />
			</div>
		{:else}
			<div class="w-full h-full flex justify-center items-center">
				<Spinner className="size-5" />
			</div>
		{/if}
	</div>
</div>
