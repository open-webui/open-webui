<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { config, user, showTabs } from '$lib/stores';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import CommentHighlights from './CommentHighlights.svelte';
	import { selectedComment, commentSelectionDraft } from './anchors';
	import { toast } from 'svelte-sonner';
	import { positionSelectionToolbar } from '$lib/utils/selectionToolbar';
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
	let selectionButton: HTMLButtonElement;
	let usingSelectionButton = false;
	$: if (($user?.id ?? null) !== account) {
		account = $user?.id ?? null;
		commentSelectionDraft.set(null);
		selection = null;
	}
	const select = () => {
		if (!preparing && !usingSelectionButton) selection = commentsAllowed ? selectedComment() : null;
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
		document.addEventListener('selectionchange', select);
		return () => {
			document.removeEventListener('selectionchange', select);
		};
	});
</script>

<svelte:document
	on:focusin={(event) => {
		usingSelectionButton = !!selectionButton?.contains(event.target as Node);
	}}
	on:pointerdown|capture={(event) => {
		usingSelectionButton = !!selectionButton?.contains(event.target as Node);
	}}
/>
<svelte:window
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			if (
				($showTabs === 'comments' || typeof $showTabs === 'object') &&
				!document.querySelector('.modal, [aria-modal="true"]')
			)
				showTabs.set(false);
			selection = null;
		}
	}}
/>
{#if commentsAllowed}
	{#key account}<CommentHighlights />{/key}
	{#if selection && !selection.options.toolbar_id}
		<button
			bind:this={selectionButton}
			use:positionSelectionToolbar={selection.range}
			type="button"
			class="fixed z-9999 min-h-9 sm:min-h-0 flex items-center gap-1 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 px-2 py-1 text-xs shadow-xl"
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
