<script lang="ts">
	import { page } from '$app/stores';
	import { createEventDispatcher, onMount } from 'svelte';
	import {
		getGrantsFeedback,
		createNewGrantFeedback,
		updateGrantFeedback
	} from '$lib/apis/grants_feedback';
	import { getGrantsNote, createNewGrantNote, updateGrantNote } from '$lib/apis/grants_notes';

	export let open = false;
	export let chatId = '';
	export let userId = '';
	const dispatch = createEventDispatcher();

	let notes = '';
	let feedback = '';
	let noteExists = false;
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
		if (notes.trim() === '') {
			saving = false;
			return;
		}
		try {
			if (noteExists) {
				await updateGrantNote(localStorage.token, chatId, notes);
			} else {
				await createNewGrantNote(localStorage.tokens, chatId, notes);
				noteExists = true;
			}
		} catch (e) {
			console.error('Notes save error', e);
		} finally {
			saving = false;
		}
	};

	const submitFeedback = async () => {
		if (feedback.trim() === '') return;

		try {
			await createNewGrantFeedback(localStorage.token, chatId, feedback);
			feedback = '';
		} catch (e) {
			console.error('Feedback submit error', e);
		}
	};

	onMount(async () => {
		if (chatId && userId) {
			try {
				const existingNote = await getGrantsNote(localStorage.token, chatId);
				if (existingNote?.note) {
					notes = existingNote.note;
					noteExists = true;
				}
			} catch (e) {
				console.log('No existing note found for this chat.');
			}
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
		<!-- Header -->
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
	
		<!-- Content Area -->
		<div class="flex flex-col flex-grow p-4 space-y-4">
			<!-- Notes Section -->
			<div class="flex flex-col flex-1 overflow-hidden space-y-2">
				<h3 class="font-semibold text-sm">Notes</h3>
				<textarea
					bind:value={notes}
					class="w-full flex-grow p-2 rounded bg-gray-100 dark:bg-gray-800 text-sm resize-none"
				/>
				<button
					on:click={saveNotes}
					class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
					disabled={saving}
				>
					{saving ? 'Saving...' : 'Save Notes'}
				</button>
			</div>
	
			<!-- Feedback Section -->
			<div class="flex flex-col flex-1 overflow-hidden space-y-2">
				<h3 class="font-semibold text-sm">Feedback</h3>
				<textarea
					bind:value={feedback}
					class="w-full flex-grow p-2 rounded bg-gray-100 dark:bg-gray-800 text-sm resize-none"
					placeholder="Your feedback here..."
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
			class="bg-gray-700 text-white dark:bg-gray-900 px-2 py-1 rounded-l hover:bg-gray-600 flex flex-col items-center gap-1 border border-gray-300 dark:border-gray-700"
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
