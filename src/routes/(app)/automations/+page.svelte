<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, mobile, showSidebar, user, config } from '$lib/stores';

	import {
		createAutomation,
		getAutomationItems,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		type AutomationForm,
		type AutomationResponse
	} from '$lib/apis/automations';
	import fileSaver from 'file-saver';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationMenu from '$lib/components/automations/AutomationMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import SplitCreateButton from '$lib/components/common/SplitCreateButton.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Select from '$lib/components/common/Select.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import { formatNumber } from '$lib/utils';

	const { saveAs } = fileSaver;

	const i18n = getContext('i18n');

	let loaded = false;
	let automations: AutomationResponse[] | null = null;
	let total: number | null = null;
	let loading = false;

	let showCreateModal = false;
	let cloneFrom: AutomationResponse | null = null;

	let showDeleteConfirm = false;
	let deleteTarget: AutomationResponse | null = null;

	let query = '';
	let statusFilter = 'all';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let page = 1;
	let importFiles: FileList | null = null;
	let automationsImportInputElement: HTMLInputElement;

	const handleSearchInput = () => {
		if (!loaded) return;

		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				getAutomationList();
			}
		}, 300);
	};

	// Immediate response to page/filter changes (gate behind loaded)
	$: if (loaded && page && statusFilter !== undefined) {
		getAutomationList();
	}

	$: if (!showCreateModal) {
		cloneFrom = null;
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

	const bulkToggleHandler = async (enable: boolean) => {
		const targets = (automations ?? []).filter((a) => a.is_active !== enable);
		if (targets.length === 0) return;

		// Optimistic UI update via map for proper Svelte reactivity
		automations = (automations ?? []).map((a) =>
			targets.some((t) => t.id === a.id) ? { ...a, is_active: enable } : a
		);

		try {
			await Promise.all(targets.map((a) => toggleAutomationById(localStorage.token, a.id)));
		} catch (err) {
			toast.error(`${err}`);
			// Refresh from server to restore consistent state
			await getAutomationList();
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

	const cloneHandler = (automation: AutomationResponse) => {
		cloneFrom = {
			...automation,
			name: `${automation.name} (Clone)`
		};
		showCreateModal = true;
	};

	const getAllAutomations = async () => {
		let currentPage = 1;
		let allAutomations: AutomationResponse[] = [];
		let totalAutomations = 0;

		do {
			const res = await getAutomationItems(localStorage.token, null, 'all', currentPage);
			const pageItems = res?.items ?? [];
			totalAutomations = res?.total ?? pageItems.length;
			allAutomations = [...allAutomations, ...pageItems];
			currentPage += 1;

			if (pageItems.length === 0) break;
		} while (allAutomations.length < totalAutomations);

		return allAutomations;
	};

	const toAutomationForm = (automation: AutomationResponse): AutomationForm => ({
		name: automation.name,
		data: automation.data,
		meta: automation.meta ?? undefined,
		is_active: automation.is_active
	});

	const exportAutomations = async () => {
		const allAutomations = await getAllAutomations().catch((err) => {
			toast.error(`${err}`);
			return null;
		});

		if (!allAutomations) return;

		const blob = new Blob([JSON.stringify(allAutomations.map(toAutomationForm), null, 2)], {
			type: 'application/json'
		});
		saveAs(blob, `automations-export-${Date.now()}.json`);
	};

	const importAutomations = async (file: File) => {
		const text = await file.text();
		const savedAutomations = JSON.parse(text);
		const automationItems = Array.isArray(savedAutomations)
			? savedAutomations
			: (savedAutomations?.automations ?? []);

		if (!Array.isArray(automationItems)) {
			throw new Error($i18n.t('Invalid JSON format'));
		}

		for (const automation of automationItems) {
			await createAutomation(localStorage.token, {
				name: automation.name,
				data: automation.data,
				meta: automation.meta ?? undefined,
				is_active: automation.is_active ?? true
			});
		}

		page = 1;
		await getAutomationList();
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
		if (
			!$config?.features?.enable_automations ||
			($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false))
		) {
			goto('/');
			return;
		}

		loaded = true;

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
		{$i18n.t('This will delete')} <span class="font-normal">{deleteTarget?.name}</span>.
	</div>
</DeleteConfirmDialog>

<input
	id="automations-import-input"
	bind:this={automationsImportInputElement}
	bind:files={importFiles}
	type="file"
	accept=".json"
	hidden
	on:change={async () => {
		if (!importFiles || importFiles.length === 0) return;

		try {
			await importAutomations(importFiles[0]);
			toast.success($i18n.t('Imported automations successfully'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			importFiles = null;
			automationsImportInputElement.value = '';
		}
	}}
/>

<AutomationModal
	bind:show={showCreateModal}
	automation={null}
	{cloneFrom}
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
			<div class="pb-1 px-2.5 pt-2">
				<div class="flex items-center gap-0.5 md:gap-1 mb-1">
					{#if $mobile}
						<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
							<Tooltip
								content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								interactive={true}
							>
								<button
									id="sidebar-toggle-button"
									class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
									on:click={() => {
										showSidebar.set(!$showSidebar);
									}}
								>
									<div class="self-center p-1.5">
										<SidebarIcon className="size-4" />
									</div>
								</button>
							</Tooltip>
						</div>
					{/if}

					<div class="flex w-full items-center">
						<div class="flex items-center gap-1 py-1 min-w-0">
							<span class="min-w-fit px-1 text-sm select-none">{$i18n.t('Automations')}</span>
							<span class="text-sm text-gray-500 dark:text-gray-500">
								{total === null ? '' : formatNumber(total)}
							</span>
						</div>

						<div class="ml-auto flex items-center gap-1">
							<SplitCreateButton
								actions={[
									{
										id: 'automations-new',
										label: $i18n.t('Create'),
										onClick: () => {
											cloneFrom = null;
											showCreateModal = true;
										}
									},
									{
										id: 'automations-import',
										label: $i18n.t('Import JSON'),
										onClick: () => automationsImportInputElement?.click()
									},
									{
										id: 'automations-export',
										label: $i18n.t('Export JSON'),
										onClick: exportAutomations
									}
								]}
							/>
						</div>
					</div>
				</div>

				<div class="space-y-1">
					<div class="flex h-8 flex-1 items-center w-full gap-2">
						<div class="flex min-w-0 flex-1 items-center">
							<div class="self-center ml-1 mr-3">
								<Search className="size-3.5" />
							</div>
							<input
								class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
								bind:value={query}
								on:input={handleSearchInput}
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
											handleSearchInput();
										}}
									>
										<XMark className="size-3" strokeWidth="2" />
									</button>
								</div>
							{/if}
						</div>

						<div
							class="flex max-w-[55%] shrink-0 overflow-x-auto scrollbar-none"
							on:wheel={(e) => {
								if (e.deltaY !== 0) {
									e.preventDefault();
									e.currentTarget.scrollLeft += e.deltaY;
								}
							}}
						>
							<div
								class="flex w-fit gap-0.5 text-center text-sm rounded-full bg-transparent whitespace-nowrap"
							>
								<Select
									bind:value={statusFilter}
									align="end"
									items={[
										{ value: 'all', label: $i18n.t('All') },
										{ value: 'active', label: $i18n.t('Active') },
										{ value: 'paused', label: $i18n.t('Paused') }
									]}
									onChange={() => {
										page = 1;
									}}
									triggerClass="relative h-8 w-full flex items-center gap-0.5 px-1.5 py-1.5 bg-transparent rounded-xl text-[13px] font-normal text-gray-700 transition hover:text-gray-900 dark:text-gray-200 dark:hover:text-gray-100"
								>
									<svelte:fragment slot="trigger" let:selectedLabel>
										<span
											class="inline-flex h-input w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
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

								<Dropdown align="end">
									<Tooltip content={$i18n.t('Actions')}>
										<button
											class="flex h-8 items-center gap-1.5 rounded-xl bg-transparent px-1.5 text-[13px] font-normal text-gray-700 transition hover:text-gray-900 dark:text-gray-200 dark:hover:text-gray-100"
											type="button"
										>
											<span>{$i18n.t('Actions')}</span>
											<ChevronDown className="size-3" strokeWidth="2.5" />
										</button>
									</Tooltip>

									<div slot="content">
										<DropdownMenu className="w-[170px] shadow-sm">
											<button
												class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
												type="button"
												on:click={() => bulkToggleHandler(true)}
											>
												<CheckCircle className="size-3.5" />
												{$i18n.t('Enable All')}
											</button>
											<button
												class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
												type="button"
												on:click={() => bulkToggleHandler(false)}
											>
												<Minus className="size-3.5" />
												{$i18n.t('Disable All')}
											</button>
										</DropdownMenu>
									</div>
								</Dropdown>
							</div>
						</div>
					</div>

					{#if automations === null || loading}
						<div class="flex min-h-[calc(100dvh-13rem)] w-full items-center justify-center">
							<Spinner className="size-5" />
						</div>
					{:else if (automations ?? []).length === 0}
						<div
							class="flex min-h-[calc(100dvh-13rem)] w-full flex-col items-center justify-center"
						>
							<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
								<div class="mb-1.5 text-sm">
									{query ? $i18n.t('No results found') : $i18n.t('No automations found')}
								</div>
								<div class="text-center text-xs leading-5 text-gray-500">
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
						<div class="gap-y-0.5 grid my-1">
							{#each automations as automation (automation.id)}
								<a
									class="flex space-x-4 text-left w-full px-3 py-2 bg-transparent hover:bg-gray-50/70 dark:hover:bg-gray-850/50 transition rounded-2xl"
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
											cloneHandler={() => {
												cloneHandler(automation);
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
												class="self-center w-fit text-sm p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 rounded-xl"
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
