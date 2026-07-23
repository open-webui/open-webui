<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getFolderById } from '$lib/apis/folders';
	import { selectedFolder } from '$lib/stores';

	let ready = false;

	onMount(async () => {
		const folderId = $page.params.folderId;
		if (!folderId) {
			await goto('/');
			return;
		}

		const folder = await getFolderById(localStorage.token, folderId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!folder) {
			await goto('/');
			return;
		}

		await selectedFolder.set(folder);
		ready = true;
	});

	onDestroy(() => {
		selectedFolder.set(null);
	});
</script>

{#if ready}
	<Chat />
{:else}
	<div class="w-full h-screen flex items-center justify-center">
		<Spinner />
	</div>
{/if}
