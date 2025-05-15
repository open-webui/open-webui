<script lang="ts">
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Collapsible from './Collapsible.svelte';
	import Tooltip from './Tooltip.svelte';
	import Plus from '../icons/Plus.svelte';

	export let open = true;

	export let id = '';
	export let name = '';
	export let collapsible = true;

	export let onAddLabel: string = '';
	export let onAdd: null | Function = null;

	export let dragAndDrop = true;

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
		if (!dragAndDrop) {
			return;
		}
		folderElement.addEventListener('dragover', onDragOver);
		folderElement.addEventListener('drop', onDrop);
		folderElement.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		if (!dragAndDrop) {
			return;
		}
		folderElement.addEventListener('dragover', onDragOver);
		folderElement.removeEventListener('drop', onDrop);
		folderElement.removeEventListener('dragleave', onDragLeave);
	});
</script>

<div bind:this={folderElement} class="relative {className}">
	{#if draggedOver}
		<div
			class="absolute top-0 left-0 w-full h-full rounded-xs bg-gray-100/50 dark:bg-gray-700/20 bg-opacity-50 dark:bg-opacity-10 z-50 pointer-events-none touch-none"
		></div>
	{/if}

	{#if collapsible}
		<Collapsible
			bind:open
			className="w-full "
			buttonClassName="w-full"
			onChange={(state) => {
				dispatch('change', state);
			}}
		>
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				class="w-full group rounded-md relative flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-900 text-gray-500 dark:text-gray-500 transition"
			>
				<button class="w-full py-1.5 pl-2 flex items-center gap-1.5 text-xs font-medium">
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

				{#if onAdd}
					<button
						class="absolute z-10 right-2 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
						on:pointerup={(e) => {
							e.stopPropagation();
						}}
						on:click={(e) => {
							e.stopPropagation();
							onAdd();
						}}
					>
						<Tooltip content={onAddLabel}>
							<button
								class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto"
								on:click={(e) => {}}
							>
								<Plus className=" size-3" strokeWidth="2.5" />
							</button>
						</Tooltip>
					</button>
				{/if}
			</div>

			<div slot="content" class="w-full">
				<slot></slot>
			</div>
		</Collapsible>
	{:else}
		<slot></slot>
	{/if}
</div>
