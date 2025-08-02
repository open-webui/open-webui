<script lang="ts">
	// Import Svelte lifecycle functions and utilities at the top
	import { getContext, createEventDispatcher, onDestroy, onMount } from 'svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	import { archiveChatById, deleteSharedChatById } from '$lib/apis/chats';

	const dispatch = createEventDispatcher();

	export let show = false; // Controls visibility of the main modal
	export let chat;

	const i18n = getContext('i18n');

	// Function to archive the chat without deleting the shared link
	const handleArchive = async () => {
		await archiveChatById(localStorage.token, chat.id);
		dispatch('change'); // Notify parent component of change (e.g., to refresh chat list)
		show = false; // Close the modal
	};

	// Function to delete the shared link and then archive the chat
	const handleDeleteAndArchive = async () => {
		await deleteSharedChatById(localStorage.token, chat.id);
		await archiveChatById(localStorage.token, chat.id); // Archive after deleting the link
		dispatch('change');
		show = false; // Close the modal
	};

	// --- Modal management for the single modal ---
	let modalElement: HTMLDivElement | null = null;
	let mounted = false;

	// This block runs when `show` changes
	$: if (mounted) {
		if (show && modalElement) {
			document.body.appendChild(modalElement);
			document.body.style.overflow = 'hidden'; // Prevent body scrolling
		} else if (modalElement && modalElement.parentNode === document.body) {
			document.body.removeChild(modalElement);
			document.body.style.overflow = 'unset'; // Restore body scrolling
		}
	}

	onMount(() => {
		mounted = true;
	});

	onDestroy(() => {
		show = false; // Ensure modal is hidden on component destroy
		if (modalElement && modalElement.parentNode === document.body) {
			document.body.removeChild(modalElement);
		}
		document.body.style.overflow = 'unset';
	});
</script>

<!-- Single Modal: Archive Chat with 3 options -->
{#if show}
	<!-- Overlay and Modal Container from ConfirmDialog.svelte structure -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={modalElement}
		class="fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] flex justify-center z-99999999 overflow-hidden overscroll-contain"
		in:fade={{ duration: 100 }}
		on:mousedown={() => {
			show = false;
			dispatch('cancel');
		}}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="m-auto rounded-2xl max-w-full w-[32rem] mx-2 bg-gray-50 dark:bg-gray-950 max-h-[100dvh] shadow-3xl"
			in:flyAndScale
			on:mousedown={(e) => e.stopPropagation()}
		>
			<div class="px-[1.75rem] py-6 flex flex-col h-full">
				<h2 class="text-lg font-semibold dark:text-gray-200 mb-2.5">
					{$i18n.t('Archive Chat')}
				</h2>
				<p class="text-sm text-gray-500 flex-1">
					{$i18n.t(
						'This chat has a shared link. Do you want to delete the shared link before archiving?'
					)}
				</p>

				<div class="mt-6 flex justify-end gap-2.5">
					<!-- Cancel Button: Style from ConfirmDialog.svelte cancel button -->
					<button
						class="bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white font-medium py-2.5 rounded-lg transition px-4"
						on:click={() => {
							show = false;
							dispatch('cancel');
						}}
					>
						{$i18n.t('Cancel')}
					</button>

					<!-- Keep Link Button: Style from ConfirmDialog.svelte confirm button -->
					<button
						class="bg-gray-900 hover:bg-gray-850 text-gray-100 dark:bg-gray-100 dark:hover:bg-white dark:text-gray-800 font-medium py-2.5 rounded-lg transition px-4"
						on:click={handleArchive}
					>
						{$i18n.t('Keep Link')}
					</button>

					<!-- Delete Link Button: Red, explicitly matching padding/font from ConfirmDialog -->
					<button
						class="bg-red-500 hover:bg-red-600 text-white font-medium py-2.5 rounded-lg transition px-4"
						on:click={handleDeleteAndArchive}
					>
						{$i18n.t('Delete Link')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}