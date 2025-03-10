<script lang="ts">
	/* Known issues:
	 *
	 * 1. It can happen that drop is not handeled when the item was dragged
	 *    _across the boundary_ between two elements (list items). This is
	 *    due to `drop` not being fired where expected (while `dragenter`,
	 *    `dragleave` was correctly fired). This was observed in the
	 *    current Chrome. There's no workaround for a not fired event.
	 */

	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	export let onDrop = (e: DragEvent) => { };

	let el: HTMLElement|null;
	let draggedOver = false;

	function onDragOver(e: DragEvent): void {
		if (! e.dataTransfer || !e.dataTransfer.types.includes("Files")) {
			return;
		}

		// Signals drop is allowed
		e.preventDefault();

		draggedOver = true;
	}

	function onDragLeave(e: DragEvent): void {
		// 1. Workaround for Safari, which does not correctly implement the
		//    drag and drop specification and leaves relatedTarget null.
		//    Bug: https://bugs.webkit.org/show_bug.cgi?id=66547
		// 2. target and relatedTarget can be null in Firefox on drop on an
		//    invalid target
		if (!e.relatedTarget || el?.contains(e.relatedTarget as HTMLElement)) {
			// Ignore this leave *within* the drag-drop container
			// Otherwise pseudo-elements and border would cause leaves too
			return;
		}

		draggedOver = false;
	}

	function onDropInternal(e: DragEvent) {
		draggedOver = false;

		if (!e.dataTransfer || !e.dataTransfer.types.includes("Files")) {
			return;
		}

		onDrop(e);

		// Signals drop is allowed
		e.preventDefault();
	}
</script>

<div
	bind:this={el}
	aria-label={$i18n.t('Drop zone for file upload via drag and drop')}
	role="form"
	data-id="drop-zone"
	data-state={draggedOver ? 'dragged-over' : ''}
	class="border-2 border-transparent rounded-md border-dashed relative after:absolute after:block after:left-0 after:top-0 after:right-0 after:bottom-0 after:bg-white/75 after:pointer-events-none"
	class:border-gray-300={draggedOver}
	class:after:absolute={draggedOver}
	on:dragover={onDragOver}
	on:dragleave={onDragLeave}
	on:drop={onDropInternal}
>
	<slot />
</div>
