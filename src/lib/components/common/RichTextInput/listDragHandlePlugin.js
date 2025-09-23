// listPointerDragPlugin.js
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
export const listPointerDragKey = new PluginKey('listPointerDrag');
export function listDragHandlePlugin(options = {}) {
	const {
		itemTypeNames = ['list_item'], // add 'taskItem' if using tiptap task-list
		handleTitle = 'Drag to move',
		handleInnerHTML = '⋮⋮',
		classItemWithHandle = 'pm-li--with-handle',
		classHandle = 'pm-list-drag-handle',
		classDropBefore = 'pm-li-drop-before',
		classDropAfter = 'pm-li-drop-after',
		classDraggingGhost = 'pm-li-ghost',
		dragThresholdPx = 2 // ignore tiny wiggles
	} = options;
	const itemTypesSet = new Set(itemTypeNames);
	const isListItem = (node) => node && itemTypesSet.has(node.type.name);
	// ---------- decoration builder ----------
	function buildHandleDecos(doc) {
		const decos = [];
		doc.descendants((node, pos) => {
			if (!isListItem(node)) return;
			decos.push(Decoration.node(pos, pos + node.nodeSize, { class: classItemWithHandle }));
			decos.push(
				Decoration.widget(
					pos + 1,
					(view, getPos) => {
						const el = document.createElement('span');
						el.className = classHandle;
						el.setAttribute('title', handleTitle);
						el.setAttribute('role', 'button');
						el.setAttribute('aria-label', 'Drag list item');
						el.contentEditable = 'false';
						el.innerHTML = handleInnerHTML;
						el.pmGetPos = getPos; // live resolver
						return el;
					},
					{ side: -1, ignoreSelection: true, key: `li-handle-${pos}` }
				)
			);
		});
		return DecorationSet.create(doc, decos);
	}
	function findListItemAround($pos) {
		for (let d = $pos.depth; d > 0; d--) {
			const node = $pos.node(d);
			if (isListItem(node)) {
				const start = $pos.before(d);
				return { depth: d, node, start, end: start + node.nodeSize };
			}
		}
		return null;
	}
	function infoFromCoords(view, clientX, clientY) {
		const result = view.posAtCoords({ left: clientX, top: clientY });
		if (!result) return null;
		const $pos = view.state.doc.resolve(result.pos);
		const li = findListItemAround($pos);
		if (!li) return null;
		const dom = /** @type {Element} */ (view.nodeDOM(li.start));
		if (!(dom instanceof Element)) return null;
		const rect = dom.getBoundingClientRect();
		const side = clientY - rect.top < rect.height / 2 ? 'before' : 'after';
		return { ...li, dom, side };
	}
	// ---------- state shape ----------
	const init = (state) => ({
		decorations: buildHandleDecos(state.doc),
		dragging: null, // {fromStart, startMouse: {x,y}, ghostEl} | null
		dropTarget: null // {start, end, side} | null
	});
	const apply = (tr, prev) => {
		let next = prev;
		let decorations = prev.decorations;
		if (tr.docChanged) {
			decorations = buildHandleDecos(tr.doc);
		} else {
			decorations = decorations.map(tr.mapping, tr.doc);
		}
		next = { ...next, decorations };
		const meta = tr.getMeta(listPointerDragKey);
		if (meta) {
			if (meta.type === 'set-drag') next = { ...next, dragging: meta.dragging };
			if (meta.type === 'set-drop') next = { ...next, dropTarget: meta.drop };
			if (meta.type === 'clear') next = { ...next, dragging: null, dropTarget: null };
		}
		return next;
	};
	const decorationsProp = (state) => {
		const ps = listPointerDragKey.getState(state);
		if (!ps) return null;
		let deco = ps.decorations;
		if (ps.dropTarget) {
			const { start, end, side } = ps.dropTarget;
			const cls = side === 'before' ? classDropBefore : classDropAfter;
			deco = deco.add(state.doc, [Decoration.node(start, end, { class: cls })]);
		}
		return deco;
	};
	// ---------- helpers ----------
	function setDrag(view, dragging) {
		view.dispatch(view.state.tr.setMeta(listPointerDragKey, { type: 'set-drag', dragging }));
	}
	function setDrop(view, drop) {
		view.dispatch(view.state.tr.setMeta(listPointerDragKey, { type: 'set-drop', drop }));
	}
	function clearAll(view) {
		view.dispatch(view.state.tr.setMeta(listPointerDragKey, { type: 'clear' }));
	}
	function moveItem(view, fromStart, toPos) {
		const { state, dispatch } = view;
		const { doc } = state;

		const node = doc.nodeAt(fromStart);
		if (!node || !isListItem(node)) return false;

		// No-op if dropping inside itself
		if (toPos >= fromStart && toPos <= fromStart + node.nodeSize) return true;

		// Resolve a position inside the list_item to read its ancestry
		const $inside = doc.resolve(fromStart + 1);

		// Find the list_item and its parent list
		let itemDepth = -1;
		for (let d = $inside.depth; d > 0; d--) {
			if ($inside.node(d) === node) {
				itemDepth = d;
				break;
			}
		}
		if (itemDepth < 0) return false;

		const listDepth = itemDepth - 1;
		const parentList = $inside.node(listDepth);
		const parentListStart = $inside.before(listDepth);

		// If the parent list has only this one child, delete the whole list.
		// Otherwise, just delete the single list_item.
		const deleteFrom = parentList.childCount === 1 ? parentListStart : fromStart;
		const deleteTo =
			parentList.childCount === 1
				? parentListStart + parentList.nodeSize
				: fromStart + node.nodeSize;

		let tr = state.tr.delete(deleteFrom, deleteTo);

		// Map the drop position through the deletion. Use a right bias so
		// dropping "after" the deleted block stays after the gap.
		const mappedTo = tr.mapping.map(toPos, 1);

		tr = tr.insert(mappedTo, node);

		dispatch(tr.scrollIntoView());
		return true;
	}

	// Create & update a simple ghost box that follows the pointer
	function ensureGhost(view, fromStart) {
		const el = document.createElement('div');
		el.className = classDraggingGhost;
		const dom = /** @type {Element} */ (view.nodeDOM(fromStart));
		const rect = dom instanceof Element ? dom.getBoundingClientRect() : null;
		if (rect) {
			el.style.position = 'fixed';
			el.style.left = rect.left + 'px';
			el.style.top = rect.top + 'px';
			el.style.width = rect.width + 'px';
			el.style.pointerEvents = 'none';
			el.style.opacity = '0.75';
			// lightweight content
			el.textContent = dom.textContent?.trim().slice(0, 80) || '…';
		}
		document.body.appendChild(el);
		return el;
	}
	function updateGhost(ghost, x, y) {
		if (!ghost) return;
		ghost.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
	}
	// ---------- plugin ----------
	return new Plugin({
		key: listPointerDragKey,
		state: { init: (_, state) => init(state), apply },
		props: {
			decorations: decorationsProp,
			handleDOMEvents: {
				// Start dragging with a handle press (pointerdown => capture move/up on window)
				mousedown(view, event) {
					const target = /** @type {HTMLElement} */ (event.target);
					const handle = target.closest?.(`.${classHandle}`);
					if (!handle) return false;
					event.preventDefault();
					const getPos = handle.pmGetPos;
					if (typeof getPos !== 'function') return true;
					const posInside = getPos();
					const fromStart = posInside - 1;
					// visually select the node if allowed (optional)
					try {
						const { NodeSelection } = require('prosemirror-state');
						const sel = NodeSelection.create(view.state.doc, fromStart);
						view.dispatch(view.state.tr.setSelection(sel));
					} catch {}
					const startMouse = { x: event.clientX, y: event.clientY };
					const ghostEl = ensureGhost(view, fromStart);
					setDrag(view, { fromStart, startMouse, ghostEl, active: false });
					const onMove = (e) => {
						const ps = listPointerDragKey.getState(view.state);
						if (!ps?.dragging) return;
						const dx = e.clientX - ps.dragging.startMouse.x;
						const dy = e.clientY - ps.dragging.startMouse.y;
						// Mark as active if moved beyond threshold
						if (!ps.dragging.active && Math.hypot(dx, dy) > dragThresholdPx) {
							setDrag(view, { ...ps.dragging, active: true });
						}
						updateGhost(ps.dragging.ghostEl, dx, dy);
						const info = infoFromCoords(view, e.clientX, e.clientY);
						if (!info) {
							setDrop(view, null);
							return;
						}
						const toPos = info.side === 'before' ? info.start : info.end;
						const same =
							ps.dropTarget &&
							ps.dropTarget.start === info.start &&
							ps.dropTarget.end === info.end &&
							ps.dropTarget.side === info.side;
						if (!same) setDrop(view, { start: info.start, end: info.end, side: info.side, toPos });
					};
					const endDrag = (e) => {
						window.removeEventListener('mousemove', onMove, true);
						window.removeEventListener('mouseup', endDrag, true);
						const ps = listPointerDragKey.getState(view.state);
						if (ps?.dragging?.ghostEl) ps.dragging.ghostEl.remove();
						if (ps?.dragging && ps?.dropTarget && ps.dragging.active) {
							const toPos =
								ps.dropTarget.side === 'before' ? ps.dropTarget.start : ps.dropTarget.end;
							moveItem(view, ps.dragging.fromStart, toPos);
						}
						clearAll(view);
					};
					window.addEventListener('mousemove', onMove, true);
					window.addEventListener('mouseup', endDrag, true);
					return true;
				},
				// Escape cancels
				keydown(view, event) {
					if (event.key === 'Escape') {
						const ps = listPointerDragKey.getState(view.state);
						if (ps?.dragging?.ghostEl) ps.dragging.ghostEl.remove();
						clearAll(view);
						return true;
					}
					return false;
				}
			}
		}
	});
}
