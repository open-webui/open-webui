<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { config, user, showControls } from '$lib/stores';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import CommentHighlights from './CommentHighlights.svelte';
	import { selectedComment, commentSelectionDraft } from './anchors';
	import { toast } from 'svelte-sonner';
	const i18n = getContext<any>('i18n');
	let selection: ReturnType<typeof selectedComment> = null;
	let account: string | null = null;
	let currentUrl = $page.url.href;
	let navigation = 0;
	$: if ($page.url.href !== currentUrl) {
		currentUrl = $page.url.href;
		navigation += 1;
		commentSelectionDraft.set(null);
		selection = null;
	}
	$: commentsAllowed = !!(
		$config?.features?.enable_comments &&
		$user &&
		!$page.url.pathname.startsWith('/s/')
	);
	let preparing = false;
	$: if (($user?.id ?? null) !== account) {
		account = $user?.id ?? null;
		commentSelectionDraft.set(null);
		selection = null;
	}
	const select = () => {
		if (!preparing) selection = commentsAllowed ? selectedComment() : null;
	};
	const commentSelection = async () => {
		const selected = selection;
		if (!selected || preparing) return;
		preparing = true;
		const version = navigation;
		const accountId = account;
		try {
			await selected.options.prepare?.();
			if (version !== navigation || accountId !== account) return;
			commentSelectionDraft.set(selected);
			window.getSelection()?.removeAllRanges();
			selection = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : String(e));
		} finally {
			preparing = false;
		}
	};
	onMount(() => {
		document.addEventListener('mouseup', select);
		document.addEventListener('keyup', select);
		return () => {
			document.removeEventListener('mouseup', select);
			document.removeEventListener('keyup', select);
		};
	});
</script>

<svelte:window
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			if (
				($showControls === 'comments' || typeof $showControls === 'object') &&
				!document.querySelector('.modal, [aria-modal="true"]')
			)
				showControls.set(false);
			selection = null;
		}
	}}
	on:scroll|capture={() => (selection = null)}
/>
{#if commentsAllowed}
	{#key account}<CommentHighlights />{/key}
	{#if selection && !selection.options.toolbar_id}
		<button
			type="button"
			class="fixed z-9999 flex items-center gap-1 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 px-2 py-1 text-xs shadow-xl"
			style={`left:${Math.max(8, Math.min(selection.rect.left, window.innerWidth - 130))}px;top:${Math.min(window.innerHeight - 48, selection.rect.bottom + 12)}px`}
			on:mousedown|preventDefault
			disabled={preparing}
			on:click={commentSelection}><Annotation className="size-3" />{$i18n.t('Comment')}</button
		>
	{/if}
{/if}

<style>
	:global(::highlight(resource-comment)) {
		background: #fde68a;
		color: #111827;
	}
</style>
