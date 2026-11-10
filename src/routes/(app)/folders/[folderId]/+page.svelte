<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		getFolderState,
		loadFolderDetails,
		beginFolderOpening,
		isCurrentFolderOpening,
		isCancelledFolderRequest,
	} from '$lib/stores/folderStates';
	import { selectedFolder } from '$lib/stores';

	let ready = false;
	let loadedFolderId = '';

	const init = async (folderId: string) => {
		if (!folderId) {
			await goto('/');
			return;
		}

		const generation = beginFolderOpening();
		const loaded = getFolderState(folderId).details;
		if (!loaded && $selectedFolder?.id !== folderId) ready = false;
		try {
			const folder = loaded ?? await loadFolderDetails(localStorage.token, folderId);
			if (!isCurrentFolderOpening(generation) || folderId !== loadedFolderId) return;
			if ($selectedFolder?.id !== folderId) selectedFolder.set(folder);
			if (loaded) void loadFolderDetails(localStorage.token, folderId, true).catch((error) => {
				if (!isCancelledFolderRequest(error)) console.error(error);
			});
		} catch (error) {
			if (!isCurrentFolderOpening(generation) || isCancelledFolderRequest(error)) return;
			toast.error(`${error}`);
			await goto('/');
			return;
		}

		ready = true;
	};

	$: if ($page.params.folderId !== loadedFolderId) {
		loadedFolderId = $page.params.folderId ?? '';
		init(loadedFolderId);
	}

	onDestroy(() => {
		if ($selectedFolder?.id === loadedFolderId) selectedFolder.set(null);
	});
</script>

{#if ready}
	<Chat />
{:else}
	<div class="w-full h-screen flex items-center justify-center">
		<Spinner />
	</div>
{/if}
