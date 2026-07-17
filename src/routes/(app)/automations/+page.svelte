<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';

	import dayjs from '$lib/dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, user, config } from '$lib/stores';

	import {
		createAutomation,
		getAutomationItems,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		type AutomationForm,
		type AutomationResponse
	} from '$lib/apis/automations';
	import type i18nType from '$lib/i18n';
	// @ts-ignore file-saver ships without local typings in this repo.
	import fileSaver from 'file-saver';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationListHeaderActions from '$lib/components/automations/AutomationListHeaderActions.svelte';
	import AutomationMenu from '$lib/components/automations/AutomationMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
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

	dayjs.extend(relativeTime);

	const { saveAs } = fileSaver;

	const i18n: typeof i18nType = getContext('i18n');
	const automationsLayout: any = getContext('automationsLayout');

	let loaded = false;
	let automations: AutomationResponse[] | null = null;
	let total: number | null = null;
	let loading = false;

	let showCreateModal = false;
	let cloneFrom: AutomationResponse | null = null;

	let showDeleteConfirm = false;
	let deleteTarget: AutomationResponse | null = null;
	let openAutomationMenuId: string | null = null;

	let query = '';
	let statusFilter = 'all';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let page = 1;
	let importFiles: FileList | null = null;
	let automationsImportInputElement: HTMLInputElement;

	const syncHeader = () => {
		automationsLayout?.setHeader({
			itemName: null,
			actions: AutomationListHeaderActions,
			actionProps: {
				actions: [
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
				]
			}
		});
	};

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
				automationsLayout?.setTotal(total);
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

	const formatLastRun = (automation: AutomationResponse): string => {
		return automation.last_run_at
			? dayjs(automation.last_run_at / 1000000).fromNow()
			: $i18n.t('Never');
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

	onMount(() => {
		if (
			!($config?.features as any)?.enable_automations ||
			($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false))
		) {
			goto('/');
			return;
		}

		loaded = true;
		syncHeader();

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
	on:save={async (e) => {
		await getAutomationList();
		if (e.detail?.id) {
			goto(`/automations/${e.detail.id}`);
		}
	}}
/>

<div class="h-full overflow-y-auto px-2.5 pb-1">
	{#if loaded}
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
								class="p-0.5 rounded-full transition"
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
							triggerClass="relative h-8 w-full flex items-center gap-0.5 px-1.5 py-1.5 bg-transparent rounded-xl text-[13px] font-normal text-gray-700 transition dark:text-gray-200"
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
									class="flex h-8 items-center gap-1.5 rounded-xl bg-transparent px-1.5 text-[13px] font-normal text-gray-700 transition dark:text-gray-200"
									type="button"
								>
									<span>{$i18n.t('Actions')}</span>
									<ChevronDown className="size-3" strokeWidth="2.5" />
								</button>
							</Tooltip>

							<div slot="content">
								<DropdownMenu className="w-[170px] shadow-sm">
									<button
										class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px]"
										type="button"
										on:click={() => bulkToggleHandler(true)}
									>
										<CheckCircle className="size-3.5" />
										{$i18n.t('Enable All')}
									</button>
									<button
										class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px]"
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
				<div class="flex min-h-[calc(100dvh-13rem)] w-full flex-col items-center justify-center">
					<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
						<div class="mb-1.5 text-sm">
							{query ? $i18n.t('No results found') : $i18n.t('No automations found')}
						</div>
						<div class="text-center text-xs leading-5 text-gray-500">
							{query
								? $i18n.t('Try adjusting your search or filter to find what you are looking for.')
								: $i18n.t('Create scheduled prompts that run automatically on a recurring basis.')}
						</div>
					</div>
				</div>
			{:else}
				<div class="gap-y-0.5 grid my-1">
					{#each automations as automation (automation.id)}
						<div
							role="button"
							tabindex="0"
							aria-label={$i18n.t('Open automation')}
							class="group flex min-h-8 w-full cursor-pointer items-center gap-2 overflow-hidden rounded-xl px-2 py-1 text-left"
							on:click={() => {
								goto(`/automations/${automation.id}`);
							}}
							on:keydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									goto(`/automations/${automation.id}`);
								}
							}}
						>
							<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
								<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
									<div class="flex min-w-0 items-center gap-2 overflow-hidden">
										<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
											<Tooltip content={automation.name} className="min-w-0" placement="top-start">
												<div
													class="truncate text-[13px] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
												>
													{automation.name}
												</div>
											</Tooltip>

											<Tooltip
												content={automation.last_run_at
													? dayjs(automation.last_run_at / 1000000).format('LLLL')
													: $i18n.t('Never')}
											>
												<div
													class="shrink-0 truncate text-[11px] leading-5 text-gray-400 dark:text-gray-600"
												>
													{formatLastRun(automation)}
												</div>
											</Tooltip>
										</div>
									</div>
								</div>
							</div>

							<div
								class="hidden max-w-44 shrink-0 self-center truncate text-right text-[11px] leading-5 text-gray-500 dark:text-gray-500 md:block"
							>
								<Tooltip content={formatRRule(automation.data.rrule)} className="min-w-0">
									<div class="truncate">
										{formatRRule(automation.data.rrule)}
									</div>
								</Tooltip>
							</div>

							<div class="flex shrink-0 flex-row items-center gap-1.5 self-center">
								<AutomationMenu
									show={openAutomationMenuId === automation.id}
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
									onClose={() => {
										openAutomationMenuId = null;
									}}
								>
									<button
										class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
										type="button"
										aria-label={$i18n.t('Automation Menu')}
										on:click={(e) => {
											e.preventDefault();
											e.stopPropagation();
											openAutomationMenuId =
												openAutomationMenuId === automation.id ? null : automation.id;
										}}
									>
										<EllipsisHorizontal className="size-4" />
									</button>
								</AutomationMenu>

								<button
									class="flex h-6 items-center"
									type="button"
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
						</div>
					{/each}
				</div>

				{#if (total ?? 0) > 30}
					<div class="flex justify-center mt-4 mb-2">
						<Pagination bind:page count={total ?? 0} perPage={30} />
					</div>
				{/if}
			{/if}
		</div>
	{:else}
		<div class="w-full h-full flex justify-center items-center">
			<Spinner className="size-5" />
		</div>
	{/if}
</div>
