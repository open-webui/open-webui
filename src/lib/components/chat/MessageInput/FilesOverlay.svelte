<script lang="ts">
	import { showSidebar } from '$lib/stores';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	export let show = false;
	export let attachNoteToChat: Function;
	export let attachChatToChat: Function;
	export let attachKnowledgeToChat: Function;
	export let inputFilesHandler: Function;

	let overlayElement = null;
	let dragged = false;

	$: if (show && overlayElement) {
		document.body.appendChild(overlayElement);
		document.body.style.overflow = 'hidden';
	} else if (overlayElement) {
		document.body.removeChild(overlayElement);
		document.body.style.overflow = 'unset';
	}

	const handleOverlayDrop = async (e) => {
		e.preventDefault();
		e.stopPropagation();

		const Data = e.dataTransfer?.getData('text/plain');
		if (Data) {
			try {
				const data = JSON.parse(Data);
				if (data.type === 'note') {
					await attachNoteToChat(data.id);
					return;
				}

				if (data.type === 'chat') {
					await attachChatToChat(data.id);
					return;
				}

				if (data.type === 'collection') {
					await attachKnowledgeToChat(data.id);
					return;
				}
			} catch (error) {
				console.log('Not JSON data, checking for files');
			}
		}

		// Handle file drops
		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer.files);
			if (inputFiles && inputFiles.length > 0) {
				inputFilesHandler(inputFiles);
			}
		}
	};

	const handleOverlayDragOver = (e) => {
		e.preventDefault();
	};
</script>

{#if show}
	<div
		bind:this={overlayElement}
		class="fixed {$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}  fixed top-0 right-0 bottom-0 w-full h-full flex z-9999 touch-none pointer-events-none"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
		on:drop={handleOverlayDrop}
		on:dragover={handleOverlayDragOver}
	>
		<div
			class="absolute w-full h-full backdrop-blur-sm bg-gray-100/50 dark:bg-gray-900/80 flex justify-center"
		>
			<div class="m-auto flex flex-col justify-center">
				<div class="max-w-md">
					<AddFilesPlaceholder />
				</div>
			</div>
		</div>
	</div>
{/if}
