<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import tippy, { type Instance } from 'tippy.js';
	import dayjs from '$lib/dayjs';
	import { socket, user, showControls } from '$lib/stores';
	import {
		commentsRequest,
		resourceQuery,
		type CommentResource,
		type ResourceComment
	} from '$lib/apis/comments';
	import { isSavedChatId } from '$lib/utils/chatId';
	import {
		anchorRange,
		getCommentSurfaces,
		surfaceRevision,
		commentSelectionDraft,
		type CommentSurface
	} from './anchors';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import CommentComposer from './CommentComposer.svelte';
	import CommentReplyComposer from './CommentReplyComposer.svelte';
	import { scrollToComment } from '$lib/utils';
	import XMark from '$lib/components/icons/XMark.svelte';

	type LocatedComment = { comment: ResourceComment; range: Range; node: HTMLElement };
	const i18n = getContext<any>('i18n');
	let mounted = false;
	let records: Record<string, ResourceComment[]> = {};
	let located: LocatedComment[] = [];
	let hovered: LocatedComment[] = [];
	let preview: HTMLDivElement;
	let popup: Instance;
	let referenceRect: DOMRect;
	let refreshTimer: ReturnType<typeof setTimeout>;
	let connection: typeof $socket = null;
	let composer: CommentComposer;
	let previousDraft: typeof $commentSelectionDraft = null;
	let postedComment: ResourceComment | null = null;
	const requests = new Map<string, AbortController>();
	const focusable = new Map<HTMLElement, { tabindex: string | null; description: string | null }>();

	$: surfaces =
		($surfaceRevision,
		[...getCommentSurfaces()].filter(
			([, options]) =>
				options.enabled !== false &&
				(options.resource_type === 'note' ||
					(options.resource_type === 'chat' && isSavedChatId(options.resource_id)))
		));
	$: resourceKeys = [...new Set(surfaces.map(([, options]) => resourceQuery(options)))];
	$: if (mounted) syncResources(resourceKeys);
	$: if (mounted) rebuild(surfaces, records);
	$: draftRange = $commentSelectionDraft ? selectionRange($commentSelectionDraft, surfaces) : null;
	$: if (mounted) paint('comment-draft', draftRange ? [draftRange] : []);
	$: if (mounted && $commentSelectionDraft !== previousDraft) {
		previousDraft = $commentSelectionDraft;
		if ($commentSelectionDraft) void startDraft($commentSelectionDraft);
		else hide();
	}
	$: if (mounted)
		paint(
			'comment-active',
			(hovered.length
				? hovered
				: located.filter(
						({ comment }) =>
							comment.id ===
							(typeof $showControls === 'object' ? $showControls.comment_id : undefined)
					)
			).map(({ range }) => range)
		);

	const paint = (name: string, ranges: Range[]) => {
		const highlights = (window.CSS as any)?.highlights;
		const HighlightClass = (window as any).Highlight;
		if (!highlights || !HighlightClass) return;
		if (ranges.length) highlights.set(name, new HighlightClass(...ranges));
		else highlights.delete(name);
	};
	const selectionRange = (
		draft: NonNullable<typeof $commentSelectionDraft>,
		entries: typeof surfaces
	) => {
		const entry = entries.find(
			([, surface]) =>
				surface.resource_type === draft.options.resource_type &&
				surface.resource_id === draft.options.resource_id &&
				surface.target_id === draft.options.target_id &&
				surface.surface_id === draft.anchor.surface_id
		);
		return entry ? anchorRange(entry[0], draft.anchor) : null;
	};
	const startDraft = async (draft: NonNullable<typeof $commentSelectionDraft>) => {
		hovered = [];
		postedComment = null;
		referenceRect = draft.rect;
		await tick();
		if (!mounted || $commentSelectionDraft !== draft) return;
		popup.show();
		await popup.popperInstance?.update();
		composer?.focus();
	};
	const dismissDraft = () => {
		commentSelectionDraft.set(null);
		hide();
	};
	const submitted = async () => {
		const created = postedComment;
		if (!mounted || !created) return;
		commentSelectionDraft.set(null);
		await tick();
		const item = located.find(({ comment }) => comment.id === created.id);
		if (item) void reveal([item], item.range.getBoundingClientRect());
	};
	const load = async (key: string) => {
		requests.get(key)?.abort();
		const controller = new AbortController();
		requests.set(key, controller);
		let items: ResourceComment[] = [];
		let cursor: string | null = null;
		try {
			do {
				const page = await commentsRequest<{
					items: ResourceComment[];
					next_cursor: string | null;
				}>(
					`/?${key}&anchored=true&limit=50${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`,
					'GET',
					undefined,
					controller.signal
				);
				if (controller.signal.aborted) return;
				items = [
					...items,
					...page.items.filter((comment) => !comment.deleted_at && comment.meta?.anchor)
				];
				cursor = page.next_cursor;
			} while (cursor);
			if (!controller.signal.aborted) records = { ...records, [key]: items };
		} catch {
			if (!controller.signal.aborted) {
				records = { ...records, [key]: [] };
				hide();
			}
		}
	};
	const syncResources = (keys: string[]) => {
		for (const [key, request] of requests) {
			if (keys.includes(key)) continue;
			request.abort();
			requests.delete(key);
			delete records[key];
		}
		for (const key of keys) if (!requests.has(key)) void load(key);
	};
	const refresh = () => {
		clearTimeout(refreshTimer);
		refreshTimer = setTimeout(() => {
			for (const key of resourceKeys) void load(key);
		}, 150);
	};
	const changed = (resource: CommentResource) => {
		if (resourceKeys.includes(resourceQuery(resource))) refresh();
	};
	$: if (mounted && connection !== $socket) {
		connection?.off('comments:changed', changed);
		connection?.off('connect', refresh);
		connection = $socket;
		connection?.on('comments:changed', changed);
		connection?.on('connect', refresh);
	}
	const restoreFocus = () => {
		for (const [node, previous] of focusable) {
			for (const [attribute, value] of [
				['tabindex', previous.tabindex],
				['aria-description', previous.description]
			]) {
				if (value === null) node.removeAttribute(attribute!);
				else node.setAttribute(attribute!, value!);
			}
		}
		focusable.clear();
	};
	const rebuild = (entries: [HTMLElement, CommentSurface][], comments: typeof records) => {
		restoreFocus();
		const next: LocatedComment[] = [];
		for (const [node, surface] of entries) {
			for (const comment of comments[resourceQuery(surface)] ?? []) {
				const anchor = comment.meta?.anchor;
				if (
					!anchor ||
					comment.target_id !== surface.target_id ||
					anchor.surface_id !== surface.surface_id
				)
					continue;
				const range = anchorRange(node, anchor);
				if (range) next.push({ comment, range, node });
			}
		}
		located = next;
		paint(
			'comment-anchors',
			next.map(({ range }) => range)
		);
		for (const node of new Set(next.map(({ node }) => node))) {
			focusable.set(node, {
				tabindex: node.getAttribute('tabindex'),
				description: node.getAttribute('aria-description')
			});
			if (!node.hasAttribute('tabindex')) node.tabIndex = 0;
			node.setAttribute('aria-description', $i18n.t('Comments'));
		}
		if (hovered.length) {
			hovered = next.filter(({ comment }) =>
				hovered.some((item) => item.comment.id === comment.id)
			);
			if (!hovered.length) hide();
		}
	};
	const hide = () => {
		popup?.hide();
		hovered = [];
	};
	const leave = () => {
		if (!$commentSelectionDraft && !preview?.contains(document.activeElement)) hide();
	};
	const reveal = async (items: LocatedComment[], rect: DOMRect) => {
		referenceRect = rect;
		hovered = items;
		await tick();
		if (!mounted || !hovered.length) return;
		popup.show();
		void popup.popperInstance?.update();
	};
	const atPoint = (event: MouseEvent) => {
		if (!(event.target instanceof Node)) return [];
		return located.filter(
			({ node, range }) =>
				node.contains(event.target as Node) &&
				[...range.getClientRects()].some(
					(rect) =>
						event.clientX >= rect.left &&
						event.clientX <= rect.right &&
						event.clientY >= rect.top &&
						event.clientY <= rect.bottom
				)
		);
	};
	const move = (event: MouseEvent) => {
		if ($commentSelectionDraft || preview?.contains(document.activeElement)) return;
		if (popup?.popper.contains(event.target as Node)) return;
		if (event.buttons || !window.getSelection()?.isCollapsed) {
			hide();
			return;
		}
		const items = atPoint(event);
		if (!items.length) {
			leave();
			return;
		}
		if (items.length === hovered.length && items.every((item, index) => item === hovered[index])) {
			return;
		}
		const rect = [...items[0].range.getClientRects()].find(
			(rect) => event.clientY >= rect.top && event.clientY <= rect.bottom
		)!;
		void reveal(items, rect);
	};
	const open = async (comment: ResourceComment) => {
		hide();
		if (comment.resource_type === 'chat') {
			showControls.set({ tab: 'comments', comment_id: comment.id });
		} else {
			const surface = surfaces.find(
				([, options]) =>
					options.resource_type === comment.resource_type &&
					options.resource_id === comment.resource_id &&
					options.target_id === comment.target_id
			)?.[1];
			surface?.onComment?.({ comment_id: comment.id });
		}
		await tick();
		scrollToComment(comment.id);
	};
	const click = (event: MouseEvent) => {
		if ($commentSelectionDraft) return;
		if (
			!window.getSelection()?.isCollapsed ||
			(event.target as Element)?.closest('a, button, input, textarea, [contenteditable="true"]')
		)
			return;
		const items = atPoint(event);
		if (items.length === 1) open(items[0].comment);
	};
	const focus = (event: FocusEvent) => {
		if ($commentSelectionDraft) return;
		const items = located.filter(({ node }) => node === event.target);
		if (items.length) void reveal(items, items[0].range.getBoundingClientRect());
		else if (!popup?.popper.contains(event.target as Node) && !popup?.popper.matches(':hover'))
			hide();
	};
	const keydown = (event: KeyboardEvent) => {
		if ($commentSelectionDraft) {
			if (event.key === 'Escape' && !document.getElementById('suggestions-container')) {
				event.stopPropagation();
				dismissDraft();
			}
			return;
		}
		if (
			event.key === 'Escape' &&
			hovered.length &&
			!document.getElementById('suggestions-container')
		) {
			event.stopPropagation();
			hide();
		}
		if (event.key === 'Enter' && focusable.has(event.target as HTMLElement)) {
			const item = located.find(({ node }) => node === event.target);
			if (item) {
				event.preventDefault();
				open(item.comment);
			}
		}
	};
	const scroll = (event: Event) => {
		if ($commentSelectionDraft || preview?.contains(document.activeElement)) {
			void popup?.popperInstance?.update();
			return;
		}
		if (!preview?.contains(event.target as Node)) hide();
	};
	onMount(() => {
		referenceRect = new DOMRect();
		popup = tippy(document.body, {
			content: preview,
			trigger: 'manual',
			interactive: true,
			placement: 'bottom-start',
			getReferenceClientRect: () => draftRange?.getBoundingClientRect() ?? referenceRect,
			appendTo: () => document.body,
			arrow: false,
			maxWidth: 'min(320px, calc(100vw - 24px))',
			theme: 'comment-preview',
			duration: 0,
			hideOnClick: false,
			offset: [0, 0]
		});
		mounted = true;
		document.addEventListener('mousemove', move);
		document.addEventListener('mouseleave', leave);
		window.addEventListener('blur', leave);
		document.addEventListener('click', click);
		document.addEventListener('focusin', focus);
		document.addEventListener('keydown', keydown);
		document.addEventListener('scroll', scroll, true);
		window.addEventListener('resize', hide);
		window.addEventListener('focus', refresh);
		window.addEventListener('comments:updated', refresh);
		return () => {
			mounted = false;
			clearTimeout(refreshTimer);
			for (const request of requests.values()) request.abort();
			connection?.off('comments:changed', changed);
			connection?.off('connect', refresh);
			document.removeEventListener('mousemove', move);
			document.removeEventListener('mouseleave', leave);
			window.removeEventListener('blur', leave);
			document.removeEventListener('click', click);
			document.removeEventListener('focusin', focus);
			document.removeEventListener('keydown', keydown);
			document.removeEventListener('scroll', scroll, true);
			window.removeEventListener('resize', hide);
			window.removeEventListener('focus', refresh);
			window.removeEventListener('comments:updated', refresh);
			restoreFocus();
			paint('comment-anchors', []);
			paint('comment-active', []);
			paint('comment-draft', []);
			popup.destroy();
		};
	});
</script>

<div class="hidden">
	<div
		bind:this={preview}
		class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 text-gray-800 dark:text-gray-200 shadow-lg"
	>
		{#if $commentSelectionDraft}
			{@const draft = $commentSelectionDraft}
			<div class="w-80 max-w-[calc(100vw-24px)] px-3 py-2">
				<div class="mb-2.5 flex min-w-0 items-center gap-2">
					<ProfileImage
						src={$user?.id ? `${WEBUI_API_BASE_URL}/users/${$user.id}/profile/image` : undefined}
						className="-ml-1 size-6 shrink-0 rounded-full!"
					/>
					<span class="min-w-0 truncate text-[0.8125rem] text-gray-900 dark:text-gray-100"
						>{$user?.name ?? $i18n.t('Unknown User')}</span
					>
					<button
						type="button"
						aria-label={$i18n.t('Close')}
						class="ms-auto shrink-0 p-0 text-gray-400 hover:text-gray-900 dark:text-gray-500 dark:hover:text-gray-100"
						on:click={dismissDraft}><XMark className="size-3.5" /></button
					>
				</div>
				<div
					class="my-1 border-l-2 border-gray-200 dark:border-gray-700 ps-2 text-xs text-gray-500 dark:text-gray-400 whitespace-pre-wrap break-words"
				>
					{draft.anchor.quote}
				</div>
				{#key `${resourceQuery(draft.options)}:${draft.options.target_id}:${draft.anchor.surface_id}:${draft.anchor.start}:${draft.anchor.end}`}
					<CommentComposer
						bind:this={composer}
						resource={draft.options}
						scrollable={false}
						embedded={true}
						draftKey={`${$user?.id}:${resourceQuery(draft.options)}:${draft.options.target_id}:${draft.anchor.surface_id}:${draft.anchor.source}:${draft.anchor.start}:${draft.anchor.end}`}
						onCancel={dismissDraft}
						onSubmitted={submitted}
						onSubmit={async (content, temp_id) => {
							const created = await commentsRequest<ResourceComment>('/', 'POST', {
								resource_type: draft.options.resource_type,
								resource_id: draft.options.resource_id,
								target_type: draft.options.target_type,
								target_id: draft.options.target_id,
								anchor: draft.anchor,
								content,
								temp_id
							});
							if (!mounted || $commentSelectionDraft !== draft) return;
							postedComment = created;
							records = {
								...records,
								[resourceQuery(created)]: [
									...(records[resourceQuery(created)] ?? []).filter(
										(item) => item.id !== created.id
									),
									created
								]
							};
						}}
					/>
				{/key}
			</div>
		{/if}
		{#each hovered as { comment } (comment.id)}
			<div class="w-80 max-w-[calc(100vw-24px)] px-3 py-2">
				<div class="mb-2.5 flex min-w-0 items-center gap-2">
					<ProfileImage
						src={comment.user?.id
							? `${WEBUI_API_BASE_URL}/users/${comment.user.id}/profile/image`
							: undefined}
						className="-ml-1 size-6 shrink-0 rounded-full!"
					/>
					<span class="min-w-0 truncate text-[0.8125rem] text-gray-900 dark:text-gray-100"
						>{comment.user?.name ?? $i18n.t('Deleted user')}</span
					>
					<span class="ms-auto shrink-0 text-xs text-gray-400 dark:text-gray-500"
						>{dayjs(comment.created_at / 1e6).fromNow()}</span
					>
				</div>
				{#if comment.meta?.anchor}
					<div
						class="my-1 border-l-2 border-gray-200 dark:border-gray-700 ps-2 text-xs text-gray-500 dark:text-gray-400 whitespace-pre-wrap break-words"
					>
						{comment.meta.anchor.quote}
					</div>
				{/if}
				<div class="mt-1 text-[0.8125rem] text-gray-600 dark:text-gray-300 break-words">
					<Markdown
						id={`comment-preview-${comment.id}`}
						content={comment.content}
						done={true}
						allowEmbeds={false}
						allowHtml={false}
						compactPreview={true}
					/>
				</div>
				<button
					type="button"
					class="mt-2 p-0 text-xs text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
					on:click={() => open(comment)}>{$i18n.t('View comment')}</button
				>
				<div class="-mx-1 mt-2">
					<CommentReplyComposer
						{comment}
						autofocus={false}
						className=""
						onCancel={null}
						onSubmitted={hide}
						onPosted={refresh}
					/>
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	:global(::highlight(comment-anchors)) {
		background-color: #fbbf2433;
	}
	:global(::highlight(comment-active)) {
		background-color: #fbbf2466;
	}
	:global(::highlight(comment-draft)) {
		background-color: #fbbf2466;
	}
	:global(.tippy-box[data-theme~='comment-preview']) {
		background: transparent;
		color: inherit;
	}
	:global(.tippy-box[data-theme~='comment-preview'] > .tippy-content) {
		/* Keep the gap to the passage inside the popup's hover area. */
		padding: 6px 0;
	}
</style>
