import { isSavedChatId } from '$lib/utils/chatId';
import { sha256 } from 'js-sha256';
import { writable } from 'svelte/store';
import type { CommentAnchor, CommentResource, CommentTarget } from '$lib/apis/comments';

export type CommentSurface = CommentResource &
	CommentTarget & {
		surface_id: string;
		content_hash: string;
		toolbar_id?: string;
		enabled?: boolean;
		prepare?: () => Promise<void>;
		onComment?: (target: CommentTarget & { comment_id?: string }) => void;
	};
export const contentHash = (text: string) => sha256(text);
export function noteCommentText(content: { json?: unknown; md?: string }) {
	const text = (node: any): string =>
		!node || typeof node !== 'object'
			? ''
			: node.type === 'text'
				? (node.text ?? '')
				: (node.content ?? []).map(text).join('');
	return content.json && typeof content.json === 'object' ? text(content.json) : (content.md ?? '');
}
const surfaces = new Map<HTMLElement, CommentSurface>();
export const surfaceRevision = writable(0);
export const commentSelectionDraft = writable<ReturnType<typeof selectedComment>>(null);
export const getCommentSurfaces = () => surfaces;
let pendingSurfaceUpdate = false;
const surfaceChanged = () => {
	if (pendingSurfaceUpdate) return;
	pendingSurfaceUpdate = true;
	queueMicrotask(() => {
		pendingSurfaceUpdate = false;
		surfaceRevision.update((value) => value + 1);
	});
};
export function commentSurface(node: HTMLElement, options: CommentSurface) {
	surfaces.set(node, options);
	surfaceChanged();
	const observer = new MutationObserver(surfaceChanged);
	observer.observe(node, { childList: true, characterData: true, subtree: true });
	return {
		update(value: CommentSurface) {
			surfaces.set(node, value);
			surfaceChanged();
		},
		destroy() {
			observer.disconnect();
			surfaces.delete(node);
			surfaceChanged();
		}
	};
}

// Both capture and lookup use the same visible text nodes, excluding interactive/hidden output.
export function surfaceText(node: HTMLElement) {
	const nodes: Text[] = [];
	const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
		acceptNode: (text) => {
			const parent = text.parentElement;
			return parent &&
				!parent.closest(
					'button, script, style, iframe, [hidden], [aria-hidden="true"], details, .katex-mathml, [data-comment-ignore]'
				)
				? NodeFilter.FILTER_ACCEPT
				: NodeFilter.FILTER_REJECT;
		}
	});
	while (walker.nextNode()) nodes.push(walker.currentNode as Text);
	return { nodes, text: nodes.map((n) => n.data).join('') };
}
export function anchorPosition(text: string, anchor: CommentAnchor): [number, number] | null {
	const chars = [...text];
	const quote = [...anchor.quote];
	const matches = (start: number) =>
		chars.slice(start, start + quote.length).join('') === anchor.quote &&
		(!anchor.prefix ||
			chars.slice(Math.max(0, start - [...anchor.prefix].length), start).join('') ===
				anchor.prefix) &&
		(!anchor.suffix ||
			chars
				.slice(start + quote.length, start + quote.length + [...anchor.suffix].length)
				.join('') === anchor.suffix);
	if (sha256(text) === anchor.source && matches(anchor.start))
		return [anchor.start, anchor.start + quote.length];
	// A quote alone is insufficient when identical passages exist.
	const candidates: number[] = [];
	let from = 0;
	while (from <= text.length) {
		const index = text.indexOf(anchor.quote, from);
		if (index < 0) break;
		const start = [...text.slice(0, index)].length;
		if (matches(start)) candidates.push(start);
		if (candidates.length > 1) return null;
		from = index + Math.max(1, anchor.quote.length);
	}
	return candidates.length === 1 ? [candidates[0], candidates[0] + quote.length] : null;
}
export function selectedComment() {
	if (window.location.pathname.startsWith('/s/')) return null;
	const selection = window.getSelection();
	if (!selection?.rangeCount || selection.isCollapsed) return null;
	const range = selection.getRangeAt(0).cloneRange();
	for (const [node, options] of surfaces) {
		if (
			options.enabled === false ||
			(options.resource_type === 'chat' && !isSavedChatId(options.resource_id)) ||
			!options.resource_id ||
			!node.contains(range.startContainer) ||
			!node.contains(range.endContainer)
		)
			continue;
		const { nodes, text } = surfaceText(node);
		if (
			Array.from(node.querySelectorAll('details, iframe, [hidden], [data-comment-ignore]')).some(
				(el) => range.intersectsNode(el)
			)
		)
			return null;
		// Require text endpoints and no excluded content inside the selection.
		if (
			!nodes.includes(range.startContainer as Text) ||
			!nodes.includes(range.endContainer as Text)
		)
			continue;
		let start = 0,
			end = 0,
			offset = 0;
		for (const n of nodes) {
			if (n === range.startContainer) start = offset + range.startOffset;
			if (n === range.endContainer) end = offset + range.endOffset;
			offset += n.length;
		}
		const quote = text.slice(start, end);
		if (!quote.trim() || [...quote].length > 10000) return null;
		const chars = [...text];
		const from = [...text.slice(0, start)].length;
		const to = [...text.slice(0, end)].length;
		const anchor: CommentAnchor = {
			quote,
			start: from,
			end: to,
			prefix: chars.slice(Math.max(0, from - 64), from).join(''),
			suffix: chars.slice(to, to + 64).join(''),
			surface_id: options.surface_id,
			source: sha256(text),
			content_hash: options.content_hash
		};
		return { options, anchor, rect: range.getBoundingClientRect() };
	}
	return null;
}
export function anchorRange(node: HTMLElement, anchor: CommentAnchor): Range | null {
	const { nodes, text } = surfaceText(node);
	const position = anchorPosition(text, anchor);
	if (!position) return null;
	const range = document.createRange();
	const start = [...text].slice(0, position[0]).join('').length;
	const end = [...text].slice(0, position[1]).join('').length;
	let offset = 0;
	for (const n of nodes) {
		if (start >= offset && start < offset + n.length) range.setStart(n, start - offset);
		if (end > offset && end <= offset + n.length) {
			range.setEnd(n, end - offset);
			return range;
		}
		offset += n.length;
	}
	return null;
}

export function highlightAnchor(
	resource: CommentResource,
	targetId: string,
	anchor: CommentAnchor
): boolean {
	for (const [node, options] of surfaces) {
		if (
			options.resource_type !== resource.resource_type ||
			options.resource_id !== resource.resource_id ||
			options.target_id !== targetId ||
			options.surface_id !== anchor.surface_id
		)
			continue;
		const range = anchorRange(node, anchor);
		if (!range) return false;
		const highlights = (CSS as any).highlights;
		const HighlightClass = (window as any).Highlight;
		if (highlights && HighlightClass) {
			highlights.set('resource-comment', new HighlightClass(range));
			setTimeout(() => highlights.delete('resource-comment'), 5000);
		} else {
			window.getSelection()?.removeAllRanges();
			window.getSelection()?.addRange(range);
		}
		range.startContainer.parentElement?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		return true;
	}
	return false;
}
