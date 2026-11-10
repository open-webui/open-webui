<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getCwd, setCwd, type TerminalTarget } from '$lib/apis/terminal';
	import { loadRecentFolders, rememberRecentFolder } from '$lib/apis/terminal/recentFolders';
	import { selectedFolder, showFileNav } from '$lib/stores';
	import type { TerminalContext } from '$lib/types';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SearchInput from './InputMenu/SearchInput.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FileNav from '../FileNav.svelte';

	const i18n = getContext<any>('i18n');
	export let target: TerminalTarget;
	export let chatId: string | null = null;
	export let userId: string;
	export let terminalContext: TerminalContext | null = null;
	export let disabled = false;
	export let inMenu = false;
	export let onSelect: (path: string) => Promise<void> = async () => {};

	let show = false;
	let showPicker = false;
	let search = '';
	let cwd = '';
	let recent: string[] = [];
	let saving = false;
	let disposed = false;
	let home = '';
	let historyError = '';
	let historyVersion = 0;
	let initialization: Promise<void>;
	const folderName = (path: string) => path.replace(/\/+$/, '').split('/').pop() || '/';
	const normalize = (path: string) => path.replace(/\/+$/, '') || '/';

	$: if (terminalContext?.terminalId === target.selector)
		cwd = terminalContext.currentDirectory;
	$: directory = cwd;
	$: options = [...new Set([directory, ...recent].filter(Boolean).map(normalize))].filter((path) =>
		path.toLowerCase().includes(search.trim().toLowerCase())
	);
	$: if (disabled && show) show = false;
	$: if (disabled && showPicker) showPicker = false;

	async function refreshRecentFolders() {
		const version = ++historyVersion;
		try {
			await initialization;
			if (disposed) return;
			if (!home) {
				const result = await getCwd(target);
				if (disposed) return;
				home = result?.home ?? '';
			}
			if (!home) throw new Error('Terminal home is unavailable');
			const paths = await loadRecentFolders(target, home, userId);
			if (disposed || version !== historyVersion) return;
			recent = paths;
			historyError = '';
		} catch {
			if (!disposed && version === historyVersion)
				historyError = $i18n.t('Failed to load recent folders');
		}
	}

	onMount(() => {
		if (!chatId && terminalContext?.terminalId !== target.selector) {
			terminalContext = {
				terminalId: target.selector,
				currentDirectory:
					$selectedFolder?.data?.terminal_id === target.selector
						? ($selectedFolder.data.working_directory ?? '')
						: ''
			};
		}
		const selectedContext =
			terminalContext?.terminalId === target.selector ? terminalContext : null;
		if (selectedContext) cwd = selectedContext.currentDirectory;
		initialization = getCwd(target).then(
			(result) => {
				if (disposed) return;
				home = result?.home ?? '';
				// A new chat ID remounts this menu before its session cwd may be ready.
				if (chatId && !selectedContext) cwd = result?.cwd ?? '';
			}
		);
		void refreshRecentFolders();
	});
	onDestroy(() => (disposed = true));

	async function selectDirectory(path: string) {
		if (disabled || saving) return;
		saving = true;
		// A draft has no terminal session yet; submission applies this choice after creating the chat.
		const result = chatId
			? await setCwd(target, path)
			: { cwd: path || home };
		if (disposed) return;
		if (!result?.cwd) {
			saving = false;
			toast.error($i18n.t('Failed to load folder'));
			return;
		}
		// An empty path resets the terminal to its default directory.
		cwd = path ? result.cwd : '';
		terminalContext = { terminalId: target.selector, currentDirectory: cwd };
		try {
			await onSelect(cwd);
		} catch (error) {
			toast.error(String(error));
		}
		if (disposed) return;
		if (cwd) {
			recent = [
				normalize(cwd),
				...recent.filter((entry) => normalize(entry) !== normalize(cwd))
			].slice(0, 8);
		}
		// Ignore history reads started before this selection.
		++historyVersion;
		if (cwd) {
			try {
				await initialization;
				if (disposed) return;
				await rememberRecentFolder(target, home, userId, cwd);
				if (disposed) return;
				historyError = '';
			} catch {
				if (disposed) return;
				historyError = $i18n.t('Failed to save recent folders');
				toast.error(historyError);
			}
		}
		saving = false;
		show = false;
		showPicker = false;
	}
</script>

<div class={inMenu ? 'w-full' : 'flex items-center translate-x-0.5'}>
	<Dropdown
		bind:show
		align="start"
		onOpenChange={(open) => {
			search = '';
			if (open) void refreshRecentFolders();
		}}
	>
		<Tooltip content={directory || $i18n.t('Working Directory')} placement="top">
			<button
				type="button"
				disabled={disabled || saving}
				aria-label={$i18n.t('Choose working directory')}
				class="flex min-w-0 items-center text-[0.8125rem] transition {inMenu
					? 'w-full gap-2 h-[1.6875rem] px-2 rounded-xl text-left hover:bg-gray-50/40 dark:hover:bg-gray-800/40'
					: 'gap-1.5 translate-y-[1px] rounded-lg p-1'} {disabled || saving
					? 'cursor-not-allowed opacity-40 text-gray-400 dark:text-gray-600'
					: directory
						? 'cursor-pointer text-gray-600 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200'
						: 'cursor-pointer text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400'}"
			>
				<Folder className="size-3.5 shrink-0" strokeWidth="2" />
				{#if inMenu || directory}
					<span class="truncate {inMenu ? 'flex-1' : 'max-w-[9.375rem]'}"
						>{directory ? folderName(directory) : $i18n.t('Working Directory')}</span
					>
				{/if}
				{#if inMenu}<ChevronRight />{/if}
			</button>
		</Tooltip>
		<div slot="content">
			<DropdownMenu className="{inMenu ? 'w-70' : 'w-60'} max-w-[calc(100vw-2rem)]">
				<SearchInput bind:value={search} placeholder={$i18n.t('Search folders')} />
				<hr class="mx-1 my-0.5 border-gray-50/30 dark:border-gray-800/30" />
				<button
					type="button"
					role="menuitemradio"
					aria-checked={!directory}
					disabled={saving || disabled}
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] font-normal cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 {!directory
						? 'bg-gray-50/40 dark:bg-gray-800/40'
						: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
					on:click={() => selectDirectory('')}
				>
					<Folder className="size-3.5 shrink-0" strokeWidth="2" />
					<span class="flex-1 text-start">{$i18n.t('No folder')}</span>
					{#if !directory}
						<Check
							className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
							strokeWidth="2"
						/>
					{/if}
				</button>
				{#if options.length > 0}
					<div
						class="px-2 py-1 text-[0.625rem] font-normal text-gray-400 dark:text-gray-500 uppercase tracking-wider"
					>
						{$i18n.t('Recently Used')}
					</div>
					{#if historyError}
						<div role="status" class="px-2 py-1 text-[0.6875rem] text-gray-500 dark:text-gray-400">
							{historyError}
						</div>
					{/if}
					<div class="max-h-60 overflow-y-auto overflow-x-hidden scrollbar-thin">
						{#each options as path}
							{@const selected = !!directory && normalize(directory) === path}
							<div
								class="group/directory relative rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
							>
								<button
									type="button"
									role="menuitemradio"
									aria-checked={selected}
									disabled={saving || disabled}
									title={path}
									class="flex h-[1.6875rem] w-full items-center justify-between gap-2 rounded-xl pl-2 {selected
										? 'pr-14'
										: 'pr-8'} text-[0.8125rem] font-normal cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 {selected
										? 'bg-gray-50/40 dark:bg-gray-800/40'
										: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
									on:click={() => selectDirectory(path)}
								>
									<div class="flex min-w-0 flex-1 items-center gap-2">
										<Folder className="size-3.5 shrink-0" strokeWidth="2" />
										<span class="truncate">{folderName(path)}</span>
									</div>
									{#if selected}
										<Check
											className="absolute right-2 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
											strokeWidth="2"
										/>
									{/if}
								</button>
								<div
									class="absolute inset-y-0 {selected
										? 'right-6'
										: 'right-1'} flex items-center opacity-0 pointer-events-none transition-opacity group-hover/directory:opacity-100 group-hover/directory:pointer-events-auto group-focus-within/directory:opacity-100 group-focus-within/directory:pointer-events-auto"
								>
									<Tooltip content={$i18n.t('Open folder')} placement="top">
										<button
											type="button"
											aria-label={$i18n.t('Open folder')}
											disabled={saving || disabled}
											class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus-visible:outline focus-visible:outline-2 disabled:cursor-not-allowed disabled:opacity-40"
											on:click|stopPropagation={() => {
												show = false;
												showFileNav.set({
													terminalId: target.selector,
													directory: path,
													chatId
												});
											}}><FolderOpen className="size-3.5" /></button
										>
									</Tooltip>
								</div>
							</div>
						{/each}
					</div>
				{/if}
				<hr class="mx-1 my-0.5 border-gray-50/30 dark:border-gray-800/30" />
				<button
					type="button"
					disabled={saving || disabled}
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-start text-[0.8125rem] font-normal cursor-pointer hover:bg-gray-50/40 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-gray-800/40"
					on:click={() => {
						show = false;
						showPicker = true;
					}}
				>
					<FolderOpen className="size-3.5 shrink-0" strokeWidth="2" />
					<span>{$i18n.t('Open folder')}</span>
				</button>
			</DropdownMenu>
		</div>
	</Dropdown>
</div>

{#if showPicker}
	<Modal bind:show={showPicker} ariaLabel={$i18n.t('Choose working directory')} size="md">
		<div class="px-2 py-4">
			<div class="mb-3 flex items-center justify-between px-2 text-sm">
				<span>{$i18n.t('Choose working directory')}</span>
				<button
					type="button"
					aria-label={$i18n.t('Close')}
					class="text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => (showPicker = false)}
				>
					<XMark className="size-4" />
				</button>
			</div>
			<div class="h-[60dvh] min-h-0" aria-busy={saving}>
				<FileNav
					terminalId={target.selector}
					{chatId}
					initialDirectory={directory || null}
					manageFileRequests={false}
					showTerminalDock={false}
					onSelectDirectory={selectDirectory}
				/>
			</div>
		</div>
	</Modal>
{/if}
