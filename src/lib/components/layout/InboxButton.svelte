<script lang="ts">
	import { getContext } from 'svelte';
	import { pushState } from '$app/navigation';
	import { page } from '$app/stores';
	import { settings, user } from '$lib/stores';
	import { inboxCount } from '$lib/stores/inbox';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Bell from '$lib/components/icons/Bell.svelte';
	import InboxBadge from './InboxBadge.svelte';
	export let onClose: () => void;
	const i18n = getContext<any>('i18n');
	$: opened = !!$page.state.inbox && $page.state.inboxUserId === $user?.id;
	$: activeClass =
		($settings?.highContrastMode ?? false)
			? 'bg-black/[0.035] dark:bg-white/[0.06]'
			: 'bg-black/[0.035] dark:bg-white/[0.045]';
</script>

<Tooltip content={$i18n.t('Notifications')} placement="bottom">
	<button
		type="button"
		data-inbox-trigger
		class="flex size-[1.875rem] shrink-0 items-center justify-center rounded-lg text-gray-600 dark:text-gray-400 transition {opened
			? activeClass
			: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
		aria-label={`${$i18n.t('Notifications')}${$inboxCount ? ` (${$inboxCount})` : ''}`}
		aria-pressed={opened}
		aria-controls="sidebar-notifications"
		on:click={(event) => {
			event.stopPropagation();
			event.preventDefault();
			event.currentTarget.focus({ preventScroll: true });
			if (opened) onClose();
			else pushState('', { ...$page.state, inbox: true, inboxUserId: $user?.id });
		}}
	>
		<span class="relative flex size-4 items-center justify-center">
			<Bell className="size-4" />
			<InboxBadge className="-top-1.5 -translate-x-0.5 text-[0.5rem]" />
		</span>
	</button>
</Tooltip>
