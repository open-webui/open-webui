<script lang="ts">
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Collapsible from './Collapsible.svelte';
	import Tooltip from './Tooltip.svelte';
	import Plus from '../icons/Plus.svelte';
	import MaterialIcon from '../common/MaterialIcon.svelte';

	export let open = true;

	export let id = '';
	export let name = '';
	export let collapsible = true;

	export let onAddLabel: string = '';
	export let onAdd: null | Function = null;

	export let dragAndDrop = true;

	export let className = '';

	export let showSidebar = true;

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
			className="w-full py-0"
			buttonClassName="w-full"
			onChange={(state) => {
				dispatch('change', state);
			}}
		>
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
	class="px-[16px] py-[8px] w-full group rounded-md relative flex items-center justify-between hover:bg-gradient-bg-2 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out"
	class:justify-center={!showSidebar}
	class:justify-between={showSidebar}
>
	<button class="w-full flex items-center gap-1.5 text-xs font-medium" class:justify-center={!showSidebar}
	class:justify-between={showSidebar}

	>
		<!-- Icon -->
		<div
			class="self-center transition-all duration-300 ease-in-out"
			class:mr-[8px]={showSidebar}
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" fill="none">
  <mask id="mask0_293_30659" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
    <rect width="20" height="20" fill="#D9D9D9"/>
  </mask>
  <g mask="url(#mask0_293_30659)">
    <path d="M3.54036 16.25C3.1355 16.25 2.7912 16.1082 2.50745 15.8246C2.22384 15.5408 2.08203 15.1965 2.08203 14.7917V5.25646C2.08203 4.8516 2.23189 4.49931 2.53161 4.19958C2.83134 3.89986 3.18363 3.75 3.58849 3.75H8.1637L9.83037 5.41667H16.4089C16.7818 5.41667 17.1034 5.53715 17.3737 5.77812C17.644 6.01896 17.8005 6.31514 17.8433 6.66667H9.31912L7.65245 5H3.58849C3.51363 5 3.45217 5.02403 3.40411 5.07208C3.35606 5.12014 3.33203 5.1816 3.33203 5.25646V14.7435C3.33203 14.8023 3.34675 14.8503 3.3762 14.8877C3.4055 14.9252 3.44418 14.9573 3.49224 14.984L5.4362 8.49354H19.3177L17.2999 15.2148C17.2048 15.5277 17.0267 15.7785 16.7656 15.9671C16.5043 16.1557 16.2145 16.25 15.8962 16.25H3.54036ZM4.80161 15H16.0564L17.6285 9.74354H6.3737L4.80161 15Z" fill="#23282E"/>
  </g>
</svg>
		</div>

		<!-- Label + Chevron Wrapper -->
		{#if showSidebar}
		<div class="w-full flex items-center justify-between">
			<!-- Label -->
			<div
				class="self-center overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
				class:max-w-[160px]={showSidebar}
				class:max-w-0={!showSidebar}
				class:opacity-100={showSidebar}
				class:opacity-0={!showSidebar}
			>
				<div class="link-style text-typography-titles">
					{name}
				</div>
			</div>

			<!-- Chevron Icon -->
			 {#if showSidebar}
				<div
				class="transition-all duration-300 ease-in-out"
				class:opacity-100={showSidebar}
				class:opacity-0={!showSidebar}
			>
				{#if open}
					<ChevronDown className="size-3" strokeWidth="2.5" />
				{:else}
					<ChevronRight className="size-3" strokeWidth="2.5" />
				{/if}
			</div>
			 {/if}

		</div>
		{/if}
	</button>

	<!-- Plus button -->
	{#if onAdd && showSidebar}
		<button
			class="absolute z-10 right-8 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
			on:pointerup={(e) => e.stopPropagation()}
			on:click={(e) => {
				e.stopPropagation();
				open = true;onAdd();
			}}
		>
			<Tooltip content={onAddLabel}>
				<button
					class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto"
				>
					<Plus className="size-3" strokeWidth="2.5" />
				</button>
			</Tooltip>
		</button>
	{/if}
</div>


			<div slot="content" class="w-full">
				{#if showSidebar}
					<slot></slot>
				{/if}
			</div>
		</Collapsible>
	{:else}
		<slot></slot>
	{/if}
</div>