<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { AppLayoutContext } from '$lib/types';
	import { toast } from 'svelte-sonner';
	import { socket } from '$lib/stores';
	import { toggleAutomationById, type FolderAutomation } from '$lib/apis/automations';
	import { formatShortDate } from '$lib/utils';
	import { formatSchedule } from '$lib/utils/schedule';
	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	/** The folder's automations as a list; new ones use the automation modal, existing ones open their page. */
	export let folderId: string;
	export let automations: FolderAutomation[] = [];
	export let loading = false;
	export let canCreate = false;
	export let onReload: () => Promise<void>;

	let showModal = false;
	let busy = '';

	export function startNew() {
		showModal = true;
	}

	// An existing automation opens as its own page, in a tab beside the folder like chats do.
	function edit(automation: FolderAutomation) {
		if (!automation.can_edit) return;
		const href = `/automations/${automation.id}`;
		if (appLayout?.openPageTab) appLayout.openPageTab({ href, label: automation.name });
		else void goto(href);
	}

	async function toggle(automation: FolderAutomation) {
		busy = automation.id;
		try {
			await toggleAutomationById(localStorage.token, automation.id);
			await onReload();
		} catch (error: any) {
			toast.error(error?.detail ?? String(error));
		} finally {
			busy = '';
		}
	}

	const lastRun = (automation: FolderAutomation) =>
		!automation.is_active
			? $i18n.t('Paused')
			: automation.last_run
				? formatShortDate(automation.last_run.created_at / 1e9, $i18n.language)
				: $i18n.t('Not run yet');

	onMount(() => {
		// A finished run updates the list's last-run times.
		const refresh = () => void onReload();
		$socket?.on('automation:result', refresh);
		return () => $socket?.off('automation:result', refresh);
	});
</script>

<AutomationModal bind:show={showModal} {folderId} on:save={onReload} />

{#if loading && !automations.length}
	<div class="flex h-full items-center justify-center"><Spinner className="size-4" /></div>
{:else if !automations.length}
	<div class="flex h-full flex-col items-center justify-center gap-1 px-6 pb-16 text-center">
		<div class="text-sm text-gray-800 dark:text-gray-100">{$i18n.t('No automations yet')}</div>
		<div class="text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Run a prompt in this folder on a schedule. Each run lands here as a chat.')}
		</div>
		{#if canCreate}
			<button
				type="button"
				class="mt-2 text-xs text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
				on:click={startNew}>{$i18n.t('New automation')}</button
			>
		{/if}
	</div>
{:else}
	<ul class="scrollbar-hidden h-full overflow-y-auto px-3" aria-label={$i18n.t('Automations')}>
		{#each automations as automation (automation.id)}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
			<li
				class="flex items-center gap-2.5 rounded-xl px-3 py-1.5 transition-colors hover:bg-gray-50 dark:hover:bg-gray-850/50 {automation.can_edit
					? 'cursor-pointer'
					: ''}"
				on:click={() => edit(automation)}
			>
				<Icon name="clock" size={14} class="text-gray-400 dark:text-gray-500" />
				<span
					class="min-w-0 shrink truncate text-[0.8125rem] leading-5 text-gray-700 dark:text-gray-200"
					>{automation.name}</span
				>
				<span class="hidden min-w-0 truncate text-xs text-gray-400 @md:block dark:text-gray-500"
					>{formatSchedule(automation.data.rrule, $i18n)}</span
				>
				<span class="flex-1"></span>
				<span class="text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-500"
					>{lastRun(automation)}</span
				>
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
				<div on:click|stopPropagation>
					<Switch
						state={automation.is_active}
						disabled={!automation.can_manage || busy === automation.id}
						ariaLabel={$i18n.t('Active')}
						on:change={() => toggle(automation)}
					/>
				</div>
			</li>
		{/each}
	</ul>
{/if}
