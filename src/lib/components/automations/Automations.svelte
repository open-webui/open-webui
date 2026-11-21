<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto, active, tab: pageTab } = getPageContext();

	import { formatSchedule } from '$lib/utils/schedule';
	import { onMount, onDestroy, getContext } from 'svelte';

	import dayjs from '$lib/dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import { closePageTabs } from '$lib/stores/chatViewStates';

	import { WEBUI_NAME, user, config, channels, folders, mobile, showSidebar } from '$lib/stores';
	import { getFolders } from '$lib/apis/folders';
	import { getChannels } from '$lib/apis/channels';

	import {
		createAutomation,
		getAutomationItems,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		startsNew,
		type AutomationForm,
		type AutomationResponse
	} from '$lib/apis/automations';
	import type i18nType from '$lib/i18n';
	// @ts-ignore file-saver ships without local typings in this repo.
	import fileSaver from 'file-saver';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationMenu from '$lib/components/automations/AutomationMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';

	dayjs.extend(relativeTime);

	const { saveAs } = fileSaver;

	const i18n: typeof i18nType = getContext('i18n');

	let loaded = false;
	let automations: AutomationResponse[] | null = null;
	let total: number | null = null;
	let loading = false;

	let showCreateModal = false;
	let cloneFrom: AutomationResponse | null = null;

	let showDeleteConfirm = false;
	let shiftKey = false;
	let deleteTarget: AutomationResponse | null = null;
	let openAutomationMenuId: string | null = null;

	let query = '';
	let statusFilter = 'all';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let page = 1;
	let importFiles: FileList | null = null;
	let automationsImportInputElement: HTMLInputElement;
	let foldersLoaded = false;
	let channelsLoaded = false;

	const newAutomationHandler = () => {
		cloneFrom = null;
		showCreateModal = true;
	};

	const menuLabel = 'px-2 pt-1.5 pb-0.5 text-xs text-base-400 dark:text-base-500';
	const iconButton =
		'relative flex size-6.5 shrink-0 items-center justify-center rounded-full border border-base-100 bg-base-50/60 text-base-500 transition-colors hover:bg-base-100 hover:text-base-900 aria-expanded:bg-base-100 aria-expanded:text-base-900 dark:border-base-850 dark:bg-base-850/50 dark:text-base-400 dark:hover:bg-base-850 dark:hover:text-base-0 dark:aria-expanded:bg-base-850 dark:aria-expanded:text-base-0';

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
	$: if (loaded && $active && page && statusFilter !== undefined) {
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

	const ensureFolders = async () => {
		if (foldersLoaded || ($folders ?? []).length > 0) return;
		const res = await getFolders(localStorage.token).catch(() => null);
		if (res) folders.set(res);
		foldersLoaded = true;
	};

	const ensureChannels = async () => {
		if (channelsLoaded || ($channels ?? []).length > 0) return;
		const res = await getChannels(localStorage.token).catch(() => null);
		if (res) channels.set(res);
		channelsLoaded = true;
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
		const allAutomations = await getAllAutomations(query, statusFilter).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (!allAutomations) return;

		const targets = allAutomations.filter((a) => a.is_active !== enable);
		if (targets.length === 0) return;

		try {
			await Promise.all(targets.map((a) => toggleAutomationById(localStorage.token, a.id)));
			if (statusFilter !== 'all') page = 1;
			await getAutomationList();
		} catch (err) {
			toast.error(`${err}`);
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
			closePageTabs(`/automations/${automation.id}`);
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
			? dayjs(automation.last_run_at / 1000000)
					.locale($i18n.language)
					.fromNow()
			: $i18n.t('Never');
	};

	const formatDestination = (automation: AutomationResponse): string => {
		if (automation.data.target?.type === 'channel') {
			const channel = ($channels ?? []).find(
				(channel) => channel.id === automation.data.target?.channel_id
			);
			return channel?.name ? `#${channel.name}` : $i18n.t('Channel');
		}
		if (automation.folder_id) return $i18n.t('Folder');
		return startsNew(automation.data.target) ? $i18n.t('New chat') : $i18n.t('Ongoing chat');
	};

	const getAllAutomations = async (query: string | null = null, status = 'all') => {
		let currentPage = 1;
		let allAutomations: AutomationResponse[] = [];
		let totalAutomations = 0;

		do {
			const res = await getAutomationItems(localStorage.token, query, status, currentPage);
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
		folder_id: automation.folder_id,
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

		await ensureFolders();
		const validFolderIds = new Set(($folders ?? []).map((folder) => folder.id));

		for (const automation of automationItems) {
			await createAutomation(localStorage.token, {
				name: automation.name,
				folder_id: validFolderIds.has(automation.folder_id) ? automation.folder_id : null,
				data: automation.data,
				meta: automation.meta ?? undefined,
				is_active: automation.is_active ?? true
			});
		}

		page = 1;
		await getAutomationList();
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
		ensureChannels();

		let keyboardFocusedElement: Element | null = null;
		const onFocusIn = (event: FocusEvent) => {
			const target = event.target as Element;
			keyboardFocusedElement = target.matches(':focus-visible:not(input, textarea)')
				? target
				: null;
		};

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Shift' && document.activeElement !== keyboardFocusedElement) {
				shiftKey = true;
				openAutomationMenuId = null;
			}
		};

		const onKeyUp = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('focusin', onFocusIn);
		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);

		return () => {
			clearTimeout(searchDebounceTimer);

			window.removeEventListener('focusin', onFocusIn);
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
	import PageTitle from '$lib/components/common/PageTitle.svelte';
</script>

<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
<PageTitle title={$i18n.t('Automations') + ' / ' + $WEBUI_NAME} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete automation?')}
	on:confirm={() => {
		if (deleteTarget) deleteHandler(deleteTarget);
	}}
>
	<div class="text-sm text-base-500 truncate">
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
			<div class="flex h-8 items-center gap-1">
				{#if $mobile && !pageTab}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
							<button
								id="sidebar-toggle-button"
								class="flex size-7 items-center justify-center text-base-400 transition"
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

				<label
					class="flex h-full min-w-0 flex-1 items-center gap-2 px-1 text-base-400 dark:text-base-500"
				>
					<Icon name="search" size={14} class="shrink-0" />
					<input
						class="min-w-0 flex-1 bg-transparent text-[0.8125rem] text-base-800 outline-hidden placeholder:text-base-400 dark:text-base-100 dark:placeholder:text-base-500"
						bind:value={query}
						on:input={handleSearchInput}
						on:keydown={(event) => {
							if (event.key === 'Escape' && query) {
								query = '';
								handleSearchInput();
							}
						}}
						aria-label={$i18n.t('Search Automations')}
						placeholder={$i18n.t('Search Automations')}
						maxlength="500"
					/>
					{#if query}
						<button
							type="button"
							class="flex size-4 shrink-0 items-center justify-center rounded-full hover:text-base-700 dark:hover:text-base-200"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								handleSearchInput();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					{/if}
				</label>

				<div class="flex shrink-0 items-center gap-1">
					<Dropdown align="end">
						<button
							type="button"
							class="{iconButton} {statusFilter !== 'all'
								? 'text-base-800 dark:text-base-100'
								: ''}"
							aria-label={$i18n.t('Filter')}
							title={$i18n.t('Filter')}
						>
							<svg
								class="size-3.75"
								viewBox="0 0 16 16"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-linecap="round"
								aria-hidden="true"><path d="M2.5 4h11M4.5 8h7M6.5 12h3" /></svg
							>
							{#if statusFilter !== 'all'}
								<span
									class="absolute -right-0.5 -top-0.5 size-1.5 rounded-full bg-base-800 dark:bg-base-100"
								></span>
							{/if}
						</button>

						<DropdownMenu slot="content" className="w-44">
							<div class={menuLabel}>{$i18n.t('Status')}</div>
							{#each [['all', 'All'], ['active', 'Active'], ['paused', 'Paused']] as const as [value, label]}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={statusFilter === value}
									on:click={() => {
										statusFilter = value;
										page = 1;
									}}
								>
									<span class="flex-1 text-left">{$i18n.t(label)}</span>
									{#if statusFilter === value}<Check className="size-3! shrink-0" />{/if}
								</button>
							{/each}
						</DropdownMenu>
					</Dropdown>

					<Dropdown align="end" closeOnSelect>
						<button
							type="button"
							class={iconButton}
							aria-label={$i18n.t('More')}
							title={$i18n.t('More')}
						>
							<EllipsisHorizontal className="size-3.5" />
						</button>

						<DropdownMenu slot="content" className="w-44">
							<button type="button" on:click={() => bulkToggleHandler(true)}>
								<CheckCircle className="size-3.5" />
								<span class="flex-1 text-left">{$i18n.t('Enable All')}</span>
							</button>
							<button type="button" on:click={() => bulkToggleHandler(false)}>
								<Minus className="size-3.5" />
								<span class="flex-1 text-left">{$i18n.t('Disable All')}</span>
							</button>
							<hr class="border-base-50/30 dark:border-base-800/30" />
							<button type="button" on:click={() => automationsImportInputElement?.click()}>
								<Icon name="upload" size={14} />
								<span class="flex-1 text-left">{$i18n.t('Import JSON')}</span>
							</button>
							<button type="button" on:click={exportAutomations}>
								<Icon name="download" size={14} />
								<span class="flex-1 text-left">{$i18n.t('Export JSON')}</span>
							</button>
						</DropdownMenu>
					</Dropdown>

					<button
						type="button"
						class={iconButton}
						aria-label={$i18n.t('New automation')}
						title={$i18n.t('New automation')}
						on:click={newAutomationHandler}
					>
						<Plus className="size-3.5" strokeWidth="2" />
					</button>
				</div>
			</div>

			{#if automations === null || loading}
				<div class="flex min-h-[calc(100dvh-13rem)] w-full items-center justify-center">
					<Spinner className="size-5" />
				</div>
			{:else if (automations ?? []).length === 0}
				<div class="flex min-h-[calc(100dvh-13rem)] w-full flex-col items-center justify-center">
					<div class="max-w-sm text-center text-base-900 dark:text-base-100">
						<div class="mb-1.5 text-sm">
							{query ? $i18n.t('No results found') : $i18n.t('No automations found')}
						</div>
						<div class="text-center text-xs leading-5 text-base-500">
							{query
								? $i18n.t('Try adjusting your search or filter to find what you are looking for.')
								: $i18n.t('Create scheduled prompts that run automatically on a recurring basis.')}
						</div>
					</div>
				</div>
			{:else}
				<div class="gap-y-0.5 grid my-1">
					<!-- Preserve the former row label for i18n extraction: $i18n.t('Open automation') -->
					{#each automations as automation (automation.id)}
						<div
							role="presentation"
							class="group flex min-h-8 w-full cursor-pointer items-center gap-2 overflow-hidden rounded-xl px-2 py-1 text-left"
							on:click={(e) => {
								if (e.target instanceof Element && e.target.closest('a')) return;
								goto(`/automations/${automation.id}`);
							}}
						>
							<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
								<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
									<div class="flex min-w-0 items-center gap-2 overflow-hidden">
										<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
											<Tooltip content={automation.name} className="min-w-0" placement="top-start">
												<a
													href={`/automations/${automation.id}`}
													class="focus-ring block truncate rounded text-[0.8125rem] leading-5 text-base-800 group-hover:underline focus-visible:underline dark:text-base-200"
													>{automation.name}</a
												>
											</Tooltip>

											<Tooltip
												content={automation.last_run_at
													? dayjs(automation.last_run_at / 1000000)
															.locale($i18n.language)
															.format('LLLL')
													: $i18n.t('Never')}
											>
												<div
													class="shrink-0 truncate text-[0.6875rem] leading-5 text-base-400 dark:text-base-600"
												>
													{formatLastRun(automation)}
												</div>
											</Tooltip>
										</div>
									</div>
								</div>
							</div>

							<div
								class="hidden max-w-56 shrink-0 self-center truncate text-right text-[0.6875rem] leading-5 text-base-500 dark:text-base-500 md:block"
							>
								<Tooltip
									content={`${formatSchedule(automation.data.rrule, $i18n)} · ${formatDestination(automation)}`}
									className="min-w-0"
								>
									<div class="truncate">
										{formatSchedule(automation.data.rrule, $i18n)} · {formatDestination(automation)}
									</div>
								</Tooltip>
							</div>

							<div class="flex shrink-0 flex-row items-center self-center">
								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="flex size-6 items-center justify-center rounded-lg text-base-400 transition dark:text-base-500"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click={(e) => {
												e.preventDefault();
												e.stopPropagation();
												deleteHandler(automation);
											}}
										>
											<GarbageBin className="size-4" />
										</button>
									</Tooltip>
								{:else}
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
												class="flex size-6 items-center justify-center rounded-lg text-base-400 transition dark:text-base-500"
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

										<div
											class="flex h-6 items-center"
											role="presentation"
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
													ariaLabel={$i18n.t('Enabled')}
													on:change={() => {
														toggleHandler(automation);
													}}
												/>
											</Tooltip>
										</div>
									</div>
								{/if}
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
