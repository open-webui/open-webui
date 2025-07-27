<script lang="ts">
	// Import Svelte lifecycle functions and utilities at the top
	import { getContext, createEventDispatcher, onDestroy, onMount } from 'svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	import { archiveChatById, deleteSharedChatById } from '$lib/apis/chats';

	const dispatch = createEventDispatcher();

	export let show = false; // Controls visibility of the initial prompt
	export let chat;

	const i18n = getContext('i18n');

	// State to control which confirmation step is active
	let showDeleteConfirm = false; // Controls visibility of the "Delete Link" confirmation modal

	const handleArchive = async () => {
		await archiveChatById(localStorage.token, chat.id);
		dispatch('change');
		show = false; // Close initial modal
	};

	const handleDeleteAndArchive = async () => {
		await deleteSharedChatById(localStorage.token, chat.id);
		await archiveChatById(localStorage.token, chat.id); // Archive after deleting the link
		dispatch('change');
		show = false; // Close initial modal
		showDeleteConfirm = false; // Close second confirmation modal
	};

	// --- Modal management for the initial 3-button prompt ---
	let initialModalElement: HTMLDivElement | null = null;
	let initialModalMounted = false;

	// This block runs when `show` changes
	$: if (initialModalMounted) {
		if (show && initialModalElement) {
			document.body.appendChild(initialModalElement);
			document.body.style.overflow = 'hidden';
		} else if (initialModalElement && initialModalElement.parentNode === document.body) {
			document.body.removeChild(initialModalElement);
			// Only unset overflow if no other modal is active
			if (!showDeleteConfirm) {
				document.body.style.overflow = 'unset';
			}
		}
	}

	// onMount must be imported and called directly at the top level of the script
	onMount(() => {
		initialModalMounted = true;
	});

	onDestroy(() => {
		show = false;
		showDeleteConfirm = false;
		if (initialModalElement && initialModalElement.parentNode === document.body) {
			document.body.removeChild(initialModalElement);
		}
		document.body.style.overflow = 'unset';
	});
</script>

<!-- First Modal: Archive Chat with 3 options -->
{#if show}
	<!-- Overlay and Modal Container from ConfirmDialog.svelte structure -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={initialModalElement}
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
						on:click={() => {
							showDeleteConfirm = true; // Show the second confirmation modal
							// The initial modal stays visible but covered by the second.
							// Both will close on final action.
						}}
					>
						{$i18n.t('Delete Link')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Second Modal: Confirmation for "Delete Link" -->
<!-- This should ideally be a separate ConfirmDialog.svelte component instance -->
<!-- For demonstration, I'm embedding similar structure. In a real app, use the component. -->
{#if showDeleteConfirm}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] flex justify-center z-99999999 overflow-hidden overscroll-contain"
		in:fade={{ duration: 100 }}
		on:mousedown={() => {
			showDeleteConfirm = false;
			// Keep the initial modal 'show' as true here, so it's still accessible after this cancel
		}}
	>
		<div
			class="m-auto rounded-2xl max-w-full w-[32rem] mx-2 bg-gray-50 dark:bg-gray-950 max-h-[100dvh] shadow-3xl"
			in:flyAndScale
			on:mousedown={(e) => e.stopPropagation()}
		>
			<div class="px-[1.75rem] py-6 flex flex-col">
				<h2 class="text-lg font-semibold dark:text-gray-200 mb-2.5">
					{$i18n.t('Confirm Delete Link')}
				</h2>
				<p class="text-sm text-gray-500 flex-1">
					{$i18n.t('Are you sure you want to delete the shared link before archiving? This action cannot be undone.')}
				</p>

				<div class="mt-6 flex justify-between gap-1.5">
					<button
						class="bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white font-medium w-full py-2.5 rounded-lg transition"
						on:click={() => {
							showDeleteConfirm = false;
							// Keep the initial modal 'show' as true here
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="bg-red-500 hover:bg-red-600 text-white font-medium w-full py-2.5 rounded-lg transition"
						on:click={handleDeleteAndArchive}
					>
						{$i18n.t('Delete Link')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}