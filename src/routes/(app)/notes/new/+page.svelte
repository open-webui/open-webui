<script lang="ts">
	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from '$lib/dayjs';
	import { createNoteHandler } from '$lib/components/notes/utils';

	onMount(async () => {
		const title = $page.url.searchParams.get('title') ?? dayjs().format('YYYY-MM-DD');
		const content = $page.url.searchParams.get('content') ?? '';

		const res = await createNoteHandler(title, content);

		if (res) {
			goto(`/notes/${res.id}`);
		}
	});
</script>
