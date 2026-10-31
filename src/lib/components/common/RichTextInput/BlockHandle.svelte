<script lang="ts">
	import { getContext } from 'svelte';
	import type { Editor } from '@tiptap/core';
	import type { Transaction } from 'prosemirror-state';
	import Dropdown from '../Dropdown.svelte';
	import DropdownMenu from '../DropdownMenu.svelte';
	import Tooltip from '../Tooltip.svelte';
	import { listPointerDragKey, moveBlock } from './listDragHandlePlugin';

	export let editor: Editor;
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	let position = -1;
	let end = 0;
	let show = false;
	let pointerStart: { x: number; y: number } | null = null;
	let handle: HTMLDivElement;

	function locate(pos: number) {
		if (!editor.isEditable || editor.isDestroyed) return;
		const $pos = editor.state.doc.resolve(pos);
		const start = $pos.depth ? $pos.before(1) : pos;
		const node = editor.state.doc.nodeAt(start);
		const dom = editor.view.nodeDOM(start);
		if (!node || !(dom instanceof HTMLElement)) return;
		const rect = dom.getBoundingClientRect();
		const parent = editor.view.dom.parentElement!;
		const bounds = parent.getBoundingClientRect();
		handle.style.left = `${rect.left - bounds.left + parent.scrollLeft - 20}px`;
		handle.style.top = `${rect.top - bounds.top + parent.scrollTop + (rect.height - handle.offsetHeight) / 2}px`;
		position = start;
		end = start + node.nodeSize;
	}

	function mount(node: HTMLDivElement) {
		const parent = editor.view.dom.parentElement!;
		const surface = parent.closest('[role="tabpanel"]') ?? parent.parentElement!;
		parent.appendChild(node);
		const dragging = () => listPointerDragKey.getState(editor.state)?.dragging;
		const hover = (event: MouseEvent) => {
			if (show || dragging() || node.contains(event.target as Node)) return;
			const bounds = editor.view.dom.getBoundingClientRect();
			const pos = editor.view.posAtCoords({
				left: Math.max(bounds.left + 1, Math.min(event.clientX, bounds.right - 1)),
				top: event.clientY
			});
			if (pos) locate(pos.pos);
		};
		const leave = () => {
			if (!editor.isEmpty && !show && !dragging() && !node.contains(document.activeElement))
				position = -1;
		};
		const selection = () => {
			if (!show && !dragging()) locate(editor.state.selection.from);
		};
		const transaction = ({ transaction }: { transaction: Transaction }) => {
			if (transaction.docChanged || !editor.isEditable) {
				position = -1;
				show = false;
				if (editor.isEmpty) locate(0);
			}
		};
		const resize = new ResizeObserver(() => {
			if (editor.isEmpty) locate(0);
			else if (position >= 0) locate(position);
		});
		resize.observe(parent);
		surface.addEventListener('mousemove', hover);
		surface.addEventListener('mouseleave', leave);
		editor.on('selectionUpdate', selection);
		editor.on('transaction', transaction);
		return {
			destroy() {
				resize.disconnect();
				surface.removeEventListener('mousemove', hover);
				surface.removeEventListener('mouseleave', leave);
				editor.off('selectionUpdate', selection);
				editor.off('transaction', transaction);
				node.remove();
			}
		};
	}

	function move(direction: number) {
		if (position < 0) return;
		const $pos = editor.state.doc.resolve(position);
		const to =
			direction < 0
				? position - ($pos.nodeBefore?.nodeSize ?? 0)
				: end + (editor.state.doc.nodeAt(end)?.nodeSize ?? 0);
		moveBlock(editor.view, position, to);
	}
</script>

<div
	bind:this={handle}
	use:mount
	class="absolute z-10 not-prose"
	style:visibility={position < 0 ? 'hidden' : 'visible'}
	data-comment-ignore
>
	<Dropdown bind:show align="start" closeOnSelect>
		<Tooltip content={`${$i18n.t('Drag to move')} · ${$i18n.t('Click for options')}`}>
			<button
				type="button"
				class="pm-list-drag-handle pm-block-drag-handle hover:opacity-100 focus-visible:opacity-100"
				style="position: static"
				aria-label={$i18n.t('Block options')}
				data-block-pos={position}
				on:mousedown={(event) => {
					pointerStart = { x: event.clientX, y: event.clientY };
					const plugin = listPointerDragKey.get(editor.state);
					if (!show) plugin?.props.handleDOMEvents?.mousedown?.call(plugin, editor.view, event);
				}}
				on:click|capture={(event) => {
					if (
						event.detail &&
						pointerStart &&
						Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 2
					) {
						event.preventDefault();
						event.stopPropagation();
					}
					pointerStart = null;
				}}>⋮⋮</button
			>
		</Tooltip>
		<div slot="content">
			<DropdownMenu className="min-w-36 text-sm">
				<button disabled={position <= 0} class="disabled:opacity-40" on:click={() => move(-1)}
					>{$i18n.t('Move up')}</button
				>
				<button
					disabled={end >= editor.state.doc.content.size}
					class="disabled:opacity-40"
					on:click={() => move(1)}>{$i18n.t('Move down')}</button
				>
			</DropdownMenu>
		</div>
	</Dropdown>
</div>
