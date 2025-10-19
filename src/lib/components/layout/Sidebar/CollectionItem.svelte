<script lang="ts">
	import { goto } from '$app/navigation';
	import { getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { mobile, showSidebar } from '$lib/stores';
	import Database from '$lib/components/icons/Database.svelte'; // Or appropriate icon
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import CollectionMenu from './CollectionMenu.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';
	import Document from '$lib/components/icons/Document.svelte';

	export let id;
	export let name;
	export let className = '';
	export let folderId;

	let itemElement;
	let dragged = false;

	let x = 0;
	let y = 0;
	const dragImage = new Image();
	dragImage.src =
		'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

	const onDragStart = (e, collectionId, currentFolderId) => {
		e.stopPropagation();
		e.dataTransfer.setDragImage(dragImage, 0, 0);
		e.dataTransfer.setData(
			'text/plain',
			JSON.stringify({
				type: 'collection',
				id: id,
				sourceFolderId: folderId
			})
		);
		dragged = true;
		e.dataTransfer.effectAllowed = 'move';
		e.target.style.opacity = '0.5';
		itemElement.style.opacity = '0.5'; // Optional: Visual cue to show it's being dragged
	};

	const onDragEnd = (e) => {
		e.stopPropagation();
		e.target.style.opacity = '1';
		itemElement.style.opacity = '1';
		dragged = false;
	};
</script>

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div class=" bg-black/80 backdrop-blur-2xl px-2 py-1 rounded-lg w-fit max-w-40">
			<div class="flex items-center gap-1">
				<Document className=" size-[18px]" strokeWidth="2" />
				<div class=" text-xs text-white line-clamp-1">
					{name}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div
	bind:this={itemElement}
	class="group relative w-full {className}"
	draggable="true"
	role="button"
	tabindex="0"
	on:dragstart={onDragStart}
	on:dragend={onDragEnd}
>
	<button
		class="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-900 transition w-full text-left"
		on:click={async () => {
			await goto(`/workspace/knowledge/${id}`, { replaceState: false, invalidateAll: true });
			if ($mobile) {
				showSidebar.set(!$showSidebar);
			}
		}}
	>
		<div class="flex flex-1 items-center gap-2 overflow-hidden">
			<div class="flex-shrink-0">
				<Database className="size-4" />
			</div>
			<div class="flex-1 text-sm line-clamp-1">
				{name}
			</div>
		</div>
	</button>

	<div class="absolute right-2 top-1/2 -translate-y-1/2 invisible group-hover:visible">
		<CollectionMenu
			on:remove={() => {
				dispatch('remove', { id });
			}}
		>
			<button class="p-1 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg">
				<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
			</button>
		</CollectionMenu>
	</div>
</div>
