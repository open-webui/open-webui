<script context="module" lang="ts">
	// Like the sidebar, only one hover preview stays open at a time.
	let closeActive: (() => void) | null = null;
</script>

<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import { settings } from '$lib/stores';
	import ChatHoverPreview from '$lib/components/layout/Sidebar/ChatHoverPreview.svelte';

	/** A chat title link with the sidebar's compact hover preview. */
	export let chatId: string;
	export let title: string;
	export let className = '';
	export let disabled = false;
	export let side: 'left' | 'right' | 'bottom' | 'top' = 'bottom';
	export let align: 'start' | 'end' | 'center' = 'start';
	/** Marks the link for the list's j/k row navigation. */
	export let rowLink = false;
	export let onclick: (event: MouseEvent) => void = () => {};

	let open = false;
	const close = () => (open = false);
	const opened = (next: boolean) => {
		if (!next || closeActive === close) return;
		closeActive?.();
		closeActive = close;
	};
	$: if (disabled) open = false;
</script>

<LinkPreview.Root
	openDelay={300}
	closeDelay={0}
	disabled={disabled || !($settings?.chatHoverPreview ?? true)}
	bind:open
	onOpenChange={opened}
>
	<LinkPreview.Trigger
		class={className}
		href="/c/{chatId}"
		draggable="false"
		data-row-link={rowLink ? '' : undefined}
		{onclick}
	>
		{title}
	</LinkPreview.Trigger>

	<ChatHoverPreview {chatId} {title} openPreview={open} {side} {align} />
</LinkPreview.Root>
