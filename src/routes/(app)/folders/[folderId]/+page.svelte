<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getFolderById } from '$lib/apis/folders';
	import { selectedFolder } from '$lib/stores';

	type FolderSelection = { id?: string } | null;

	let ready = false;
	let loadingFolderId: string | null = null;

	const loadFolder = async (folderId: string | undefined) => {
		if (!folderId) {
			await goto('/');
			return;
		}

		loadingFolderId = folderId;
		ready = false;

		// The sidebar click handler already fetches the folder and sets
		// `selectedFolder` before navigating here; refetching would duplicate
		// the request and re-trigger the sidebar's folder refresh.
		if (($selectedFolder as FolderSelection)?.id !== folderId) {
			const folder = await getFolderById(localStorage.token, folderId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (!folder) {
				await goto('/');
				return;
			}

			if (loadingFolderId !== folderId) {
				return;
			}

			await selectedFolder.set(folder);
		}

		ready = true;
	};

	onMount(async () => {
		await loadFolder($page.params.folderId);
	});

	$: if (
		ready &&
		$page.params.folderId &&
		($selectedFolder as FolderSelection)?.id !== $page.params.folderId
	) {
		loadFolder($page.params.folderId);
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
