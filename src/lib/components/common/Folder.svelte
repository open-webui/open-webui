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

	let folderElement;

	let dragged = false;

	const onDragOver = (e) => {
		e.preventDefault();
		dragged = true;
	};

	const onDrop = (e) => {
		e.preventDefault();

		if (folderElement.contains(e.target)) {
			console.log('Dropped on the Button');

			// get data from the drag event
			const dataTransfer = e.dataTransfer.getData('text/plain');
			const data = JSON.parse(dataTransfer);
			console.log(data);
			dispatch('drop', data);

			dragged = false;
		}
	};

	const onDragLeave = (e) => {
		e.preventDefault();
		dragged = false;
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

<div bind:this={folderElement} class="relative">
	{#if dragged}
		<div
			class="absolute top-0 left-0 w-full h-full rounded-sm bg-gray-200 bg-opacity-50 dark:bg-opacity-10 z-50 pointer-events-none touch-none"
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
			<div class="mx-2 w-full">
				<button
					class="w-full py-1 px-1.5 rounded-md flex items-center gap-1 text-xs text-gray-500 dark:text-gray-500 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition"
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

			<div slot="content">
				<slot></slot>
			</div>
		</Collapsible>
	{:else}
		<slot></slot>
	{/if}
</div>
