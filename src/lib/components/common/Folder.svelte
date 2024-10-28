<script>
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Collapsible from './Collapsible.svelte';

	export let open = true;

	export let id = '';
	export let name = '';
	export let collapsible = true;

	export let className = '';

	let folderElement;

	let draggedOver = false;

	const onDragOver = (e) => {
		e.preventDefault();
		e.stopPropagation();
		draggedOver = true;
	};

	const onDrop = (e) => {
		e.preventDefault();
		e.stopPropagation();

		if (folderElement.contains(e.target)) {
			console.log('Dropped on the Button');

			if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
				// Iterate over all items in the DataTransferItemList use functional programming
				for (const item of Array.from(e.dataTransfer.items)) {
					// If dropped items aren't files, reject them
					if (item.kind === 'file') {
						const file = item.getAsFile();
						if (file && file.type === 'application/json') {
							console.log('Dropped file is a JSON file!');

							// Read the JSON file with FileReader
							const reader = new FileReader();
							reader.onload = async function (event) {
								try {
									const fileContent = JSON.parse(event.target.result);
									console.log('Parsed JSON Content: ', fileContent);
									open = true;
									dispatch('import', fileContent);
								} catch (error) {
									console.error('Error parsing JSON file:', error);
								}
							};

							// Start reading the file
							reader.readAsText(file);
						} else {
							console.error('Only JSON file types are supported.');
						}
					} else {
						open = true;

						const dataTransfer = e.dataTransfer.getData('text/plain');
						const data = JSON.parse(dataTransfer);

						console.log(data);
						dispatch('drop', data);
					}
				}
			}

			draggedOver = false;
		}
	};

	const onDragLeave = (e) => {
		e.preventDefault();
		e.stopPropagation();

		draggedOver = false;
	};

	onMount(() => {
		folderElement.addEventListener('dragover', onDragOver);
		folderElement.addEventListener('drop', onDrop);
		folderElement.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		folderElement.addEventListener('dragover', onDragOver);
		folderElement.removeEventListener('drop', onDrop);
		folderElement.removeEventListener('dragleave', onDragLeave);
	});
</script>

<div bind:this={folderElement} class="relative {className}">
	{#if draggedOver}
		<div
			class="absolute top-0 left-0 w-full h-full rounded-sm bg-[hsla(260,85%,65%,0.1)] bg-opacity-50 dark:bg-opacity-10 z-50 pointer-events-none touch-none"
		></div>
	{/if}

	{#if collapsible}
		<Collapsible
			bind:open
			className="w-full "
			buttonClassName="w-full"
			on:change={(e) => {
				dispatch('change', e.detail);
			}}
		>
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div class="w-full">
				<button
					class="w-full py-1.5 px-2 rounded-md flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-500 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				>
					<div class="text-gray-300 dark:text-gray-600">
						{#if open}
							<ChevronDown className=" size-3" strokeWidth="2.5" />
						{:else}
							<ChevronRight className=" size-3" strokeWidth="2.5" />
						{/if}
					</div>

					<div class="translate-y-[0.5px]">
						{name}
					</div>
				</button>
			</div>

			<div slot="content" class="w-full">
				<slot></slot>
			</div>
		</Collapsible>
	{:else}
		<slot></slot>
	{/if}
</div>
