<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, mobile, showSidebar, user, config } from '$lib/stores';

	import {
		getAutomationItems,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		type AutomationResponse
	} from '$lib/apis/automations';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationMenu from '$lib/components/automations/AutomationMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Select from '$lib/components/common/Select.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let automations: AutomationResponse[] | null = null;
	let total: number | null = null;
	let loading = false;

	let showCreateModal = false;

	let showDeleteConfirm = false;
	let deleteTarget: AutomationResponse | null = null;

	let query = '';
	let statusFilter = 'all';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let page = 1;

	// Debounce only query changes (gate behind loaded to prevent double-fetch on mount)
	$: if (loaded && query !== undefined) {
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			page = 1;
			getAutomationList();
		}, 300);
	}

	// Immediate response to page/filter changes (gate behind loaded)
	$: if (loaded && page && statusFilter !== undefined) {
		getAutomationList();
	}

	const getAutomationList = async () => {
		if (!loaded) return;

		loading = true;
		try {
			const res = await getAutomationItems(localStorage.token, query, statusFilter, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				automations = res.items;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	};

	const toggleHandler = async (automation: AutomationResponse) => {
		const res = await toggleAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			automations = (automations ?? []).map((a) => (a.id === res.id ? res : a));
		}
	};

	const runNowHandler = async (automation: AutomationResponse) => {
		const res = await runAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Automation triggered'));
		}
	};

	const deleteHandler = async (automation: AutomationResponse) => {
		const res = await deleteAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: automation.name }));
		}

		page = 1;
		getAutomationList();
	};

	const formatRRule = (rrule: string): string => {
		// Detect one-time schedule (ONCE)
		if (rrule.includes('COUNT=1')) {
			const match = rrule.match(/DTSTART:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
			if (match) {
				const d = new Date(`${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}`);
				return `Once · ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`;
			}
			return 'Once';
		}
		const parts: Record<string, string> = {};
		rrule
			.replace('RRULE:', '')
			.split(';')
			.forEach((p) => {
				const [k, v] = p.split('=');
				if (k && v) parts[k] = v;
			});
		const freq = parts.FREQ || '';
		const hour = parseInt(parts.BYHOUR || '0');
		const min = (parts.BYMINUTE || '0').padStart(2, '0');
		const iv = parseInt(parts.INTERVAL || '1');
		const ampm = hour >= 12 ? 'PM' : 'AM';
		const h12 = hour % 12 || 12;
		const time = `${h12}:${min} ${ampm}`;

		if (freq === 'MINUTELY') return iv === 1 ? 'Every minute' : `Every ${iv} minutes`;
		if (freq === 'HOURLY') return iv === 1 ? 'Hourly' : `Every ${iv} hours`;
		if (freq === 'DAILY') return `Daily at ${time}`;
		if (freq === 'WEEKLY') {
			const days = parts.BYDAY || '';
			return days ? `${days} at ${time}` : `Weekly at ${time}`;
		}
		if (freq === 'MONTHLY')
			return `Monthly on the ${parts.BYMONTHDAY || '1'}${ordinal(parts.BYMONTHDAY || '1')} at ${time}`;
		return rrule;
	};

	const ordinal = (n: string): string => {
		const num = parseInt(n);
		if (num % 10 === 1 && num !== 11) return 'st';
		if (num % 10 === 2 && num !== 12) return 'nd';
		if (num % 10 === 3 && num !== 13) return 'rd';
		return 'th';
	};

	onMount(async () => {
		if ($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false)) {
			goto('/');
			return;
		}

		loaded = true;
		// Explicit initial fetch — reactive blocks will handle subsequent changes
		await getAutomationList();

		return () => {
			clearTimeout(searchDebounceTimer);
		};
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<svelte:head>
	<title>{$i18n.t('Automations')} • {$WEBUI_NAME}</title>
</svelte:head>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete automation?')}
	on:confirm={() => {
		if (deleteTarget) deleteHandler(deleteTarget);
	}}
>
	<div class="text-sm text-gray-500 truncate">
		{$i18n.t('This will delete')} <span class="font-medium">{deleteTarget?.name}</span>.
	</div>
</DeleteConfirmDialog>

<AutomationModal
	bind:show={showCreateModal}
	automation={null}
	on:save={(e) => {
		getAutomationList();
		if (e.detail?.id) {
			goto(`/automations/${e.detail.id}`);
		}
	}}
/>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex-1 max-h-full overflow-y-auto">
		{#if loaded}
			<div class="pb-1 px-3 md:px-[18px] pt-2">
				<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
					<div class="flex justify-between items-center">
						<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
							{#if $mobile}
								<Tooltip
									content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								>
									<button
										id="sidebar-toggle-button"
										class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
										on:click={() => {
											showSidebar.set(!$showSidebar);
										}}
									>
										<div class="self-center p-1.5">
											<SidebarIcon />
										</div>
									</button>
								</Tooltip>
							{/if}
							<div>{$i18n.t('Automations')}</div>
							<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
								{total ?? ''}
							</div>
						</div>

						<div class="flex w-full justify-end gap-1.5">
							<button
								class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
								on:click={() => {
									showCreateModal = true;
								}}
							>
								<Plus className="size-3" strokeWidth="2.5" />
								<div class="hidden md:block md:ml-1 text-xs">
									{$i18n.t('New Automation')}
								</div>
							</button>
						</div>
					</div>
				</div>

				<div
					class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
				>
					<div class="px-3.5 flex flex-1 items-center w-full space-x-2 py-0.5 pb-2">
						<div class="flex flex-1 items-center">
							<div class="self-center ml-1 mr-3">
								<Search className="size-3.5" />
							</div>
							<input
								class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
								bind:value={query}
								aria-label={$i18n.t('Search Automations')}
								placeholder={$i18n.t('Search Automations')}
								maxlength="500"
							/>

							{#if query}
								<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
									<button
										class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
										aria-label={$i18n.t('Clear search')}
										on:click={() => {
											query = '';
										}}
									>
										<XMark className="size-3" strokeWidth="2" />
									</button>
								</div>
							{/if}
						</div>
					</div>

					<div class="px-3 flex w-full bg-transparent overflow-x-auto scrollbar-none -mx-1">
						<div
							class="flex gap-0.5 w-fit text-center text-sm rounded-full bg-transparent px-1.5 whitespace-nowrap"
						>
							<Select
								bind:value={statusFilter}
								items={[
									{ value: 'all', label: $i18n.t('All') },
									{ value: 'active', label: $i18n.t('Active') },
									{ value: 'paused', label: $i18n.t('Paused') }
								]}
								onChange={() => {
									page = 1;
								}}
								triggerClass="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl"
							>
								<svelte:fragment slot="trigger" let:selectedLabel>
									<span
										class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
									>
										{selectedLabel}
									</span>
									<ChevronDown className="size-3.5" strokeWidth="2.5" />
								</svelte:fragment>

								<svelte:fragment slot="item" let:item let:selected>
									{item.label}
									<div class="ml-auto {selected ? '' : 'invisible'}">
										<Check />
									</div>
								</svelte:fragment>
							</Select>
						</div>
					</div>

					{#if automations === null || loading}
						<div class="w-full h-full flex justify-center items-center my-16 mb-24">
							<Spinner className="size-5" />
						</div>
					{:else if (automations ?? []).length === 0}
						<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
							<div class="max-w-md text-center">
								<div class="text-3xl mb-3">⚡</div>
								<div class="text-lg font-medium mb-1">
									{query ? $i18n.t('No results found') : $i18n.t('No automations found')}
								</div>
								<div class="text-gray-500 text-center text-xs">
									{query
										? $i18n.t(
												'Try adjusting your search or filter to find what you are looking for.'
											)
										: $i18n.t(
												'Create scheduled prompts that run automatically on a recurring basis.'
											)}
								</div>
							</div>
						</div>
					{:else}
						<div class="gap-2 grid my-2 px-3">
							{#each automations as automation (automation.id)}
								<a
									class="flex space-x-4 text-left w-full px-3 py-2.5 dark:hover:bg-gray-850/50 hover:bg-gray-50 transition rounded-2xl"
									href={`/automations/${automation.id}`}
								>
									<div class="flex-1">
										<div class="line-clamp-1 text-sm">{automation.name}</div>
										<div class="text-xs text-gray-500 line-clamp-1">
											{formatRRule(automation.data.rrule)}
										</div>
									</div>

									<div class="flex flex-row gap-0.5 self-center">
										<AutomationMenu
											editHandler={() => {
												goto(`/automations/${automation.id}`);
											}}
											runHandler={() => {
												runNowHandler(automation);
											}}
											deleteHandler={() => {
												deleteTarget = automation;
												showDeleteConfirm = true;
											}}
										>
											<button
												class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
											>
												<EllipsisHorizontal className="size-5" />
											</button>
										</AutomationMenu>

										<button
											on:click={(e) => {
												e.stopPropagation();
												e.preventDefault();
											}}
										>
											<Tooltip
												content={automation.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}
											>
												<Switch
													bind:state={automation.is_active}
													on:change={() => {
														toggleHandler(automation);
													}}
												/>
											</Tooltip>
										</button>
									</div>
								</a>
							{/each}
						</div>

						{#if total > 30}
							<div class="flex justify-center mt-4 mb-2">
								<Pagination bind:page count={total} perPage={30} />
							</div>
						{/if}
					{/if}
				</div>
			</div>
		{:else}
			<div class="w-full h-full flex justify-center items-center">
				<Spinner className="size-5" />
			</div>
		{/if}
	</div>
</div>
