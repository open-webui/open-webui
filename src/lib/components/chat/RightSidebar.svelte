<script lang="ts">
	import { page } from '$app/stores';
	import { createEventDispatcher, onMount } from 'svelte';

	export let open = false;
    export let chatId = '';
    export let userId = '';
	const dispatch = createEventDispatcher();

	let notes = '';
	let feedback = '';
	let saving = false;

	const close = () => {
		open = false;
		dispatch('close');
		document.getElementById('chat-container')?.classList.remove('with-sidebar');
	};

	const openSidebar = () => {
		open = true;
		dispatch('open');
		document.getElementById('chat-container')?.classList.add('with-sidebar');
	};

	const saveNotes = async () => {
		saving = true;
		try {
			await fetch('/api/notes', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					chatId: $page.url.pathname,
					notes
				})
			});
		} finally {
			saving = false;
		}
	};

	const submitFeedback = async () => {
		if (feedback.trim() === '') return;
		await fetch('/api/feedback', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ feedback, chatId: $page.url.pathname })
		});
		feedback = '';
	};

	onMount(() => {
		if (open) {
			document.getElementById('chat-container')?.classList.add('with-sidebar');
		}
	});
</script>

<!-- Sidebar Panel -->
<div
	class="fixed top-0 right-0 h-full w-80 transition-transform duration-300 ease-in-out z-40"
	class:translate-x-full={!open}
>
	{#if open}
		<div class="flex flex-col h-full">
			<div class="flex justify-between items-center p-2">
				<h2 class="text-base font-semibold">Notes & Feedback</h2>
				<button
					on:click={close}
					class="text-sm px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800"
					title="Close Sidebar"
				>
					✕
				</button>
			</div>

			<div class="flex flex-col justify-between h-full p-4 space-y-4">
				<!-- Notes -->
				<div class="space-y-2">
					<h3 class="font-semibold text-sm">Notes</h3>
					<textarea
						bind:value={notes}
						class="w-full h-32 p-2 rounded bg-gray-100 dark:bg-gray-800 text-sm resize-none"
					/>
					<button
						on:click={saveNotes}
						class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
						disabled={saving}
					>
						{saving ? 'Saving...' : 'Save Notes'}
					</button>
				</div>

				<!-- Feedback -->
				<div class="space-y-2 mt-auto">
					<h3 class="font-semibold text-sm">Feedback</h3>
					<textarea
						bind:value={feedback}
						class="w-full h-20 p-2 rounded bg-gray-100 dark:bg-gray-800 text-sm resize-none"
						placeholder="${chatId}: ${userId} - Your feedback here..."
					/>
					<button
						on:click={submitFeedback}
						class="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
					>
						Submit Feedback
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<!-- Vertical Toggle Button -->
{#if !open}
	<div class="fixed right-0 top-1/2 transform -translate-y-1/2 z-30">
		<button
			on:click={openSidebar}
			class="bg-gray-700 text-white dark:bg-gray-900 px-2 py-1 rounded-l hover:bg-gray-600 flex flex-col items-center gap-1"
			title="Open Notes & Feedback"
		>
			<span class="text-sm">←</span>
			<span
				class="text-sm font-semibold"
				style="writing-mode: vertical-lr; text-orientation: mixed; transform: rotate(180deg);"
			>
				Notes & Feedback
			</span>
		</button>
	</div>
{/if}

<style>
	.translate-x-full {
		transform: translateX(100%);
	}
</style>
