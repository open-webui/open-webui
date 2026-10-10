<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getFolderById } from '$lib/apis/folders';
	import { selectedFolder } from '$lib/stores';

	let ready = false;
	let loadedFolderId = '';

	const init = async (folderId) => {
		if (!folderId) {
			await goto('/');
			return;
		}

		// The sidebar click handler already fetches the folder and sets
		// `selectedFolder` before navigating here; refetching would duplicate
		// the request and re-trigger the sidebar's folder refresh.
		if ($selectedFolder?.id !== folderId) {
			const folder = await getFolderById(localStorage.token, folderId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (folderId !== loadedFolderId) {
				return;
			}

			if (!folder) {
				await goto('/');
				return;
			}

			await selectedFolder.set(folder);
		}

		ready = true;
	};

	$: if ($page.params.folderId !== loadedFolderId) {
		loadedFolderId = $page.params.folderId;
		init(loadedFolderId);
	}

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
