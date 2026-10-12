<script lang="ts">
	import { getContext, onMount, setContext } from 'svelte';
	import { writable } from 'svelte/store';
	import { goto } from '$app/navigation';

	import { config, mobile, showSidebar, user } from '$lib/stores';
	import { getAutomationItems } from '$lib/apis/automations';
	import type i18nType from '$lib/i18n';
	import { formatNumber } from '$lib/utils';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n: typeof i18nType = getContext('i18n');

	const total = writable<number | null>(null);

	let itemName: string | null = null;
	let HeaderActions: any = null;
	let headerActionProps: Record<string, any> = {};

	const setHeader = ({
		itemName: nextItemName = null,
		actions = null,
		actionProps = {}
	}: {
		itemName?: string | null;
		actions?: any;
		actionProps?: Record<string, any>;
	}) => {
		itemName = nextItemName;
		HeaderActions = actions;
		headerActionProps = actionProps;
	};

	const clearHeader = () => {
		itemName = null;
		HeaderActions = null;
		headerActionProps = {};
	};

	const refreshCount = async () => {
		const res = await getAutomationItems(localStorage.token, null, 'all', 1).catch(() => null);
		if (res) {
			total.set(res.total);
		}
	};

	setContext('automationsLayout', {
		total,
		setTotal: (value: number | null) => total.set(value),
		refreshCount,
		setHeader,
		clearHeader
	});

	onMount(async () => {
		if (
			!($config?.features as any)?.enable_automations ||
			($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false))
		) {
			goto('/');
			return;
		}

		await refreshCount();
	});
</script>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex h-full min-h-0 flex-col">
		<div class="shrink-0 px-2.5 pt-2 pb-1">
			<div class="flex items-center gap-0.5 md:gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
							<button
								id="sidebar-toggle-button"
								class="flex size-7 items-center justify-center text-gray-400 transition"
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
								type="button"
							>
								<SidebarIcon className="size-4" />
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="flex w-full min-w-0 items-center">
					<div class="flex min-w-0 flex-1 items-center gap-1 py-1">
						{#if itemName}
							<button
								class="min-w-fit px-1 text-sm select-none transition"
								aria-label={$i18n.t('Back')}
								on:click={() => goto('/automations')}
								type="button"
							>
								{$i18n.t('Automations')}
							</button>
						{:else}
							<span class="min-w-fit px-1 text-sm select-none">{$i18n.t('Automations')}</span>
						{/if}
						<span class="text-sm text-gray-500 dark:text-gray-500">
							{$total === null ? '' : formatNumber($total)}
						</span>
						{#if itemName}
							<span class="text-sm text-gray-300 dark:text-gray-800 px-2">/</span>
							<span class="min-w-0 flex-1 truncate text-sm text-gray-900 dark:text-white">
								{itemName}
							</span>
						{/if}
					</div>

					{#if HeaderActions}
						<svelte:component this={HeaderActions} {...headerActionProps} />
					{/if}
				</div>
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-hidden">
			<slot />
		</div>
	</div>
</div>
