<script lang="ts">
	import { createEventDispatcher, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { DropdownMenu } from 'bits-ui';
	import Fuse from 'fuse.js';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import Search from '$lib/components/icons/Search.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import {
		getSharepointAuthStatus,
		getSharepointAuthUrl,
		logoutSharepoint,
		getSharepointTenants,
		getSharepointDrives,
		getSharepointSites,
		getSharepointSiteDrives,
		getSharepointFiles,
		getSharepointFilesRecursive,
		downloadSharepointFile,
		type DriveInfo,
		type DriveItem,
		type SiteInfo,
		type SharePointAuthStatus,
		type TenantInfo
	} from '$lib/apis/sharepoint';
	import { addSharePointFolderToSpace } from '$lib/apis/spaces';

	export let show = false;
	export let token: string;
	export let spaceId: string | null = null;

	const dispatch = createEventDispatcher();
	const RECENT_DRIVES_KEY = 'sharepoint_recent_drives';
	const MAX_RECENT_DRIVES = 5;

	let authStatus: SharePointAuthStatus | null = null;
	let tenants: TenantInfo[] = [];
	let currentTenant: TenantInfo | null = null;
	let drives: DriveInfo[] = [];
	let currentDrive: DriveInfo | null = null;
	let items: DriveItem[] = [];
	let selectedItems: Set<string> = new Set();
	let selectedFolders: Set<string> = new Set();
	let folderStack: { id: string; name: string }[] = [];

	let sites: SiteInfo[] = [];
	let currentSite: SiteInfo | null = null;

	let loading = false;
	let loadingAuth = true;
	let loadingTenants = false;
	let loadingSites = false;
	let loadingDrives = false;
	let downloading = false;

	let siteDropdownOpen = false;
	let siteSearchValue = '';
	let selectedSiteIdx = 0;

	let driveDropdownOpen = false;
	let driveSearchValue = '';
	let selectedDriveIdx = 0;
	let selectedDriveType = '';

	let recentDriveIds: string[] = [];

	$: recentDrives = recentDriveIds
		.map((id) => drives.find((d) => d.id === id))
		.filter((d): d is DriveInfo => d !== undefined);

	$: driveTypes = [...new Set(drives.map((d) => d.drive_type).filter(Boolean))].sort();

	const fuse = new Fuse<DriveInfo>([], {
		keys: ['name', 'owner', 'drive_type'],
		threshold: 0.4
	});

	const siteFuse = new Fuse<SiteInfo>([], {
		keys: ['display_name', 'name'],
		threshold: 0.4
	});

	$: if (drives.length > 0) {
		fuse.setCollection(drives);
	}

	$: if (sites.length > 0) {
		siteFuse.setCollection(sites);
	}

	$: filteredSites = siteSearchValue ? siteFuse.search(siteSearchValue).map((r) => r.item) : sites;

	$: filteredDrives = (() => {
		let result = driveSearchValue ? fuse.search(driveSearchValue).map((r) => r.item) : drives;

		if (selectedDriveType) {
			result = result.filter((d) => d.drive_type === selectedDriveType);
		}

		return result;
	})();

	$: if (siteSearchValue) {
		resetSiteSelection();
	}

	$: if (selectedDriveType || driveSearchValue) {
		resetDriveSelection();
	}

	async function resetSiteSelection() {
		await tick();
		const idx = filteredSites.findIndex((s) => s.id === currentSite?.id);
		selectedSiteIdx = idx >= 0 ? idx : 0;
		scrollToSelectedSite();
	}

	function scrollToSelectedSite() {
		const item = document.querySelector('[data-site-selected="true"]');
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
	}

	async function resetDriveSelection() {
		await tick();
		const idx = filteredDrives.findIndex((d) => d.id === currentDrive?.id);
		selectedDriveIdx = idx >= 0 ? idx : 0;
		scrollToSelectedDrive();
	}

	function scrollToSelectedDrive() {
		const item = document.querySelector('[data-drive-selected="true"]');
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
	}

	function loadRecentDrives() {
		try {
			const stored = localStorage.getItem(RECENT_DRIVES_KEY);
			recentDriveIds = stored ? JSON.parse(stored) : [];
		} catch {
			recentDriveIds = [];
		}
	}

	function saveRecentDrive(driveId: string) {
		recentDriveIds = [driveId, ...recentDriveIds.filter((id) => id !== driveId)].slice(
			0,
			MAX_RECENT_DRIVES
		);
		try {
			localStorage.setItem(RECENT_DRIVES_KEY, JSON.stringify(recentDriveIds));
		} catch {}
	}

	function handleSiteKeydown(e: KeyboardEvent) {
		if (e.code === 'Enter' && filteredSites.length > 0) {
			selectSite(filteredSites[selectedSiteIdx]);
			return;
		} else if (e.code === 'ArrowDown') {
			e.preventDefault();
			e.stopPropagation();
			selectedSiteIdx = Math.min(selectedSiteIdx + 1, filteredSites.length - 1);
		} else if (e.code === 'ArrowUp') {
			e.preventDefault();
			e.stopPropagation();
			selectedSiteIdx = Math.max(selectedSiteIdx - 1, 0);
		} else {
			selectedSiteIdx = 0;
		}
		scrollToSelectedSite();
	}

	function handleDriveKeydown(e: KeyboardEvent) {
		if (e.code === 'Enter' && filteredDrives.length > 0) {
			selectDrive(filteredDrives[selectedDriveIdx]);
			driveDropdownOpen = false;
			return;
		} else if (e.code === 'ArrowDown') {
			e.preventDefault();
			e.stopPropagation();
			selectedDriveIdx = Math.min(selectedDriveIdx + 1, filteredDrives.length - 1);
		} else if (e.code === 'ArrowUp') {
			e.preventDefault();
			e.stopPropagation();
			selectedDriveIdx = Math.max(selectedDriveIdx - 1, 0);
		} else {
			selectedDriveIdx = 0;
		}
		scrollToSelectedDrive();
	}

	onMount(async () => {
		loadRecentDrives();
		await checkAuthStatus();
	});

	async function checkAuthStatus() {
		loadingAuth = true;
		try {
			authStatus = await getSharepointAuthStatus(token);
			if (authStatus.authenticated) {
				await loadTenants();
			}
		} catch (error) {
			console.error('Failed to check auth status:', error);
			toast.error('Failed to check SharePoint authentication status');
		} finally {
			loadingAuth = false;
		}
	}

	async function loadTenants() {
		loadingTenants = true;
		try {
			tenants = await getSharepointTenants(token);
			if (tenants.length > 0) {
				await selectTenant(tenants[0]);
			} else {
				await loadSites();
			}
		} catch (error) {
			console.error('Failed to load tenants:', error);
			await loadSites();
		} finally {
			loadingTenants = false;
		}
	}

	async function selectTenant(tenant: TenantInfo) {
		currentTenant = tenant;
		currentSite = null;
		sites = [];
		currentDrive = null;
		drives = [];
		items = [];
		folderStack = [];
		selectedItems.clear();
		await loadSites();
	}

	async function loadSites() {
		if (!currentTenant) return;
		loadingSites = true;
		try {
			sites = await getSharepointSites(token, currentTenant.id);
			if (sites.length > 0) {
				await selectSite(sites[0]);
			}
		} catch (error) {
			console.error('Failed to load sites:', error);
			toast.error('Failed to load departments');
		} finally {
			loadingSites = false;
		}
	}

	async function selectSite(site: SiteInfo) {
		currentSite = site;
		siteSearchValue = '';
		siteDropdownOpen = false;
		currentDrive = null;
		drives = [];
		folderStack = [];
		selectedItems.clear();
		selectedFolders.clear();

		// Load drives for this site and auto-select first one
		loadingDrives = true;
		try {
			drives = await getSharepointSiteDrives(token, currentTenant!.id, site.id);
			if (drives.length > 0) {
				await selectDrive(drives[0]);
			}
		} catch (error) {
			console.error('Failed to load site drives:', error);
			toast.error('Failed to load document libraries');
		} finally {
			loadingDrives = false;
		}
	}

	async function startAuth() {
		try {
			const { url } = await getSharepointAuthUrl(token);
			// Open OAuth popup
			const popup = window.open(url, '_blank', 'width=600,height=700');

			// Poll for auth completion
			const pollInterval = setInterval(async () => {
				try {
					const status = await getSharepointAuthStatus(token);
					if (status.authenticated) {
						clearInterval(pollInterval);
						authStatus = status;
						await loadTenants();
						toast.success('Connected to SharePoint');
					}
				} catch (e) {
					// Ignore polling errors
				}
			}, 2000);

			// Clear polling after 5 minutes
			setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
		} catch (error) {
			console.error('Failed to start auth:', error);
			toast.error('Failed to start SharePoint authentication');
		}
	}

	async function logout() {
		try {
			await logoutSharepoint(token);
			authStatus = { enabled: true, authenticated: false, provider: 'microsoft_sharepoint' };
			tenants = [];
			currentTenant = null;
			sites = [];
			currentSite = null;
			drives = [];
			currentDrive = null;
			items = [];
			selectedItems.clear();
			selectedFolders.clear();
			folderStack = [];
			toast.success('Disconnected from SharePoint');
		} catch (error) {
			console.error('Failed to logout:', error);
			toast.error('Failed to disconnect from SharePoint');
		}
	}

	async function loadDrives() {
		if (!currentTenant) {
			console.error('No tenant selected');
			return;
		}
		loadingDrives = true;
		try {
			drives = await getSharepointDrives(token, currentTenant.id);
			if (drives.length > 0) {
				await selectDrive(drives[0]);
			}
		} catch (error) {
			console.error('Failed to load drives:', error);
			toast.error('Failed to load drives');
		} finally {
			loadingDrives = false;
		}
	}

	async function selectDrive(drive: DriveInfo) {
		currentDrive = drive;
		saveRecentDrive(drive.id);
		folderStack = [];
		selectedItems.clear();
		selectedFolders.clear();
		await loadItems();
	}

	async function loadItems(folderId?: string) {
		if (!currentDrive || !currentTenant) return;

		loading = true;
		try {
			items = await getSharepointFiles(token, currentTenant.id, currentDrive.id, folderId);
		} catch (error) {
			console.error('Failed to load files:', error);
			toast.error('Failed to load files');
		} finally {
			loading = false;
		}
	}

	async function navigateToFolder(item: DriveItem) {
		folderStack = [...folderStack, { id: item.id, name: item.name }];
		selectedItems.clear();
		selectedFolders.clear();
		await loadItems(item.id);
	}

	async function navigateUp() {
		if (folderStack.length === 0) return;

		folderStack = folderStack.slice(0, -1);
		selectedItems.clear();
		selectedFolders.clear();
		const parentId = folderStack.length > 0 ? folderStack[folderStack.length - 1].id : undefined;
		await loadItems(parentId);
	}

	async function navigateToBreadcrumb(index: number) {
		if (index < 0) {
			folderStack = [];
			selectedItems.clear();
			selectedFolders.clear();
			await loadItems();
		} else {
			folderStack = folderStack.slice(0, index + 1);
			selectedItems.clear();
			selectedFolders.clear();
			await loadItems(folderStack[index].id);
		}
	}

	function toggleFolderSelection(item: DriveItem, event: MouseEvent) {
		event.stopPropagation();
		if (selectedFolders.has(item.id)) {
			selectedFolders.delete(item.id);
		} else {
			selectedFolders.add(item.id);
		}
		selectedFolders = selectedFolders;
	}

	function toggleSelection(item: DriveItem) {
		if (item.is_folder) {
			navigateToFolder(item);
			return;
		}

		if (selectedItems.has(item.id)) {
			selectedItems.delete(item.id);
		} else {
			selectedItems.add(item.id);
		}
		selectedItems = selectedItems;
	}

	async function downloadSelected() {
		if (!currentDrive || (selectedItems.size === 0 && selectedFolders.size === 0)) return;

		downloading = true;

		if (!currentTenant || !currentDrive) {
			toast.error('No tenant or drive selected');
			downloading = false;
			return;
		}

		try {
			// When spaceId is provided and folders are selected, use bulk folder import
			if (spaceId && selectedFolders.size > 0) {
				let totalAdded = 0;
				let totalSkipped = 0;
				let totalFailed = 0;

				for (const folderId of selectedFolders) {
					const folder = items.find((i) => i.id === folderId);
					const folderName = folder?.name || 'folder';
					toast.info(`Importing ${folderName}...`);

					const result = await addSharePointFolderToSpace(
						token,
						spaceId,
						currentTenant.id,
						currentDrive.id,
						folderId,
						folderName,
						currentSite?.display_name,
						true,
						10
					);

					totalAdded += result.added;
					totalSkipped += result.skipped;
					totalFailed += result.failed;

					for (const file of result.files) {
						dispatch('fileDownloaded', file);
					}
				}

				// Also handle individually selected files
				for (const itemId of selectedItems) {
					const item = items.find((i) => i.id === itemId && !i.is_folder);
					if (item) {
						const result = await downloadSharepointFile(
							token,
							currentTenant.id,
							currentDrive.id,
							item.id,
							item.name
						);
						dispatch('fileDownloaded', result);
						totalAdded++;
					}
				}

				const message =
					`Imported ${totalAdded} file(s)` +
					(totalSkipped > 0 ? `, ${totalSkipped} skipped` : '') +
					(totalFailed > 0 ? `, ${totalFailed} failed` : '');
				toast.success(message);
			} else {
				// Original flow: enumerate and download files one by one
				const filesToDownload = items.filter(
					(item) => selectedItems.has(item.id) && !item.is_folder
				);

				for (const folderId of selectedFolders) {
					const folder = items.find((i) => i.id === folderId);
					const folderName = folder?.name || 'folder';
					toast.info(`Scanning ${folderName}...`);

					const folderFiles = await getSharepointFilesRecursive(
						token,
						currentTenant.id,
						currentDrive.id,
						folderId
					);
					filesToDownload.push(...folderFiles);
				}

				if (filesToDownload.length === 0) {
					toast.warning('No files to import');
					downloading = false;
					return;
				}

				toast.info(`Importing ${filesToDownload.length} file(s)...`);

				for (const file of filesToDownload) {
					const result = await downloadSharepointFile(
						token,
						currentTenant.id,
						currentDrive.id,
						file.id,
						file.name
					);
					dispatch('fileDownloaded', result);
				}

				toast.success(`Imported ${filesToDownload.length} file(s)`);
			}

			selectedItems.clear();
			selectedFolders.clear();
			selectedItems = selectedItems;
			selectedFolders = selectedFolders;
			show = false;
		} catch (error) {
			console.error('Failed to download files:', error);
			toast.error('Failed to download files');
		} finally {
			downloading = false;
		}
	}

	function formatFileSize(bytes?: number): string {
		if (!bytes) return '';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
		return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
	}

	function getFileIcon(item: DriveItem): string {
		if (item.is_folder) return '📁';
		const ext = item.name.split('.').pop()?.toLowerCase();
		switch (ext) {
			case 'pdf':
				return '📄';
			case 'doc':
			case 'docx':
				return '📝';
			case 'xls':
			case 'xlsx':
				return '📊';
			case 'ppt':
			case 'pptx':
				return '📽️';
			case 'jpg':
			case 'jpeg':
			case 'png':
			case 'gif':
			case 'webp':
				return '🖼️';
			case 'mp4':
			case 'mov':
			case 'avi':
				return '🎬';
			case 'mp3':
			case 'wav':
				return '🎵';
			case 'zip':
			case 'rar':
			case '7z':
				return '📦';
			case 'txt':
				return '📃';
			case 'csv':
				return '📈';
			default:
				return '📄';
		}
	}
</script>

<Modal bind:show size="lg">
	<div class="flex flex-col max-h-[85vh]">
		<!-- Header -->
		<div class="flex items-center justify-between px-6 pt-5 pb-4">
			<div class="flex items-center gap-3">
				<div
					class="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-blue-600 shadow-sm"
				>
					<svg
						class="w-4 h-4 text-white"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
						SharePoint Files
					</h2>
					{#if authStatus?.authenticated && currentSite}
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							{sites.length} department{sites.length === 1 ? '' : 's'} available
						</p>
					{/if}
				</div>
			</div>
			<div class="flex items-center gap-2">
				{#if authStatus?.authenticated}
					<button
						class="text-xs text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition-colors px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={logout}
						aria-label="Disconnect from SharePoint"
					>
						Disconnect
					</button>
				{/if}
				<button
					class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
					on:click={() => (show = false)}
					aria-label="Close"
				>
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		</div>

		{#if loadingAuth}
			<div class="flex flex-col items-center justify-center py-20 px-6">
				<Spinner className="size-5" />
				<p class="text-sm text-gray-400 dark:text-gray-500 mt-3">Connecting to SharePoint...</p>
			</div>
		{:else if !authStatus?.enabled}
			<div class="flex flex-col items-center justify-center py-20 px-6">
				<div
					class="w-12 h-12 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4"
				>
					<svg
						class="w-6 h-6 text-gray-400 dark:text-gray-500"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
						/>
					</svg>
				</div>
				<p class="text-sm font-medium text-gray-700 dark:text-gray-300">Not Available</p>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					SharePoint integration is not enabled for this instance.
				</p>
			</div>
		{:else if !authStatus?.authenticated}
			<div class="flex flex-col items-center justify-center py-16 px-6">
				<div
					class="w-16 h-16 rounded-2xl bg-gradient-to-br from-sky-50 to-blue-100 dark:from-sky-900/30 dark:to-blue-900/30 flex items-center justify-center mb-5 shadow-sm"
				>
					<svg
						class="w-8 h-8 text-blue-500 dark:text-blue-400"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.86-2.54a4.5 4.5 0 00-6.364-6.364L4.5 8.25"
						/>
					</svg>
				</div>
				<p class="text-sm font-medium text-gray-800 dark:text-gray-200 mb-1.5">
					Connect to Microsoft
				</p>
				<p
					class="text-xs text-gray-500 dark:text-gray-400 text-center max-w-xs mb-6 leading-relaxed"
				>
					Sign in with your Microsoft account to browse and import files from SharePoint and
					OneDrive.
				</p>
				<button
					class="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 rounded-xl shadow-sm hover:shadow transition-all active:scale-[0.98]"
					on:click={startAuth}
				>
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
						<path
							d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z"
						/>
					</svg>
					Connect Account
				</button>
			</div>
		{:else}
			<!-- Connected state -->
			<div class="flex flex-col flex-1 min-h-0">
				<!-- Controls bar -->
				<div class="px-6 pb-3 space-y-3">
					<!-- Tenant selector (segmented control) -->
					{#if tenants.length > 1}
						<div class="flex items-center gap-3">
							<div class="inline-flex p-0.5 rounded-lg bg-gray-100 dark:bg-gray-800">
								{#each tenants as tenant}
									<button
										class="relative px-3.5 py-1.5 text-xs font-medium rounded-md transition-all duration-200 {currentTenant?.id ===
										tenant.id
											? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => selectTenant(tenant)}
										aria-label="Switch to {tenant.name}"
									>
										{tenant.name}
									</button>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Department selector -->
					{#if loadingTenants || loadingSites}
						<div
							class="flex items-center gap-3 px-4 py-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-gray-100 dark:border-gray-800"
						>
							<Spinner className="size-4" />
							<div>
								<p class="text-sm font-medium text-gray-700 dark:text-gray-300">
									Loading departments
								</p>
								<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
									Fetching SharePoint sites...
								</p>
							</div>
						</div>
					{:else}
						<DropdownMenu.Root
							bind:open={siteDropdownOpen}
							onOpenChange={() => {
								siteSearchValue = '';
								selectedSiteIdx = 0;
								window.setTimeout(() => document.getElementById('site-search-input')?.focus(), 0);
							}}
							closeFocus={false}
						>
							<DropdownMenu.Trigger
								class="w-full flex items-center gap-3 px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800/60 border border-gray-200/80 dark:border-gray-700/60 rounded-xl hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100/50 dark:hover:bg-gray-800 transition-all text-left group"
								aria-label="Select department"
							>
								<div
									class="flex items-center justify-center w-8 h-8 rounded-lg bg-white dark:bg-gray-700 border border-gray-200/80 dark:border-gray-600/50 shadow-sm shrink-0"
								>
									<svg
										class="w-4 h-4 text-gray-500 dark:text-gray-400"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21"
										/>
									</svg>
								</div>
								<div class="flex-1 min-w-0">
									{#if currentSite}
										<div class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
											{currentSite.display_name}
										</div>
										<div class="text-xs text-gray-400 dark:text-gray-500 truncate">
											Department{currentDrive ? ` · ${currentDrive.name}` : ''}
										</div>
									{:else}
										<div class="text-sm text-gray-400 dark:text-gray-500">Select a department</div>
									{/if}
								</div>
								{#if loadingDrives}
									<Spinner className="size-3.5 shrink-0" />
								{:else}
									<ChevronDown
										className="size-4 text-gray-400 dark:text-gray-500 group-hover:text-gray-500 dark:group-hover:text-gray-400 transition-colors shrink-0"
									/>
								{/if}
							</DropdownMenu.Trigger>

							<DropdownMenu.Content
								class="z-[10000] w-[22rem] max-w-[calc(100vw-2rem)] rounded-xl bg-white dark:bg-gray-850 shadow-xl shadow-black/10 dark:shadow-black/30 border border-gray-200 dark:border-gray-700 outline-none overflow-hidden"
								transition={flyAndScale}
								side="bottom"
								sideOffset={4}
							>
								<!-- Search -->
								<div
									class="flex items-center gap-2.5 px-3.5 py-3 border-b border-gray-100 dark:border-gray-700/80"
								>
									<Search className="size-4 text-gray-400 shrink-0" />
									<input
										id="site-search-input"
										bind:value={siteSearchValue}
										class="flex-1 text-sm bg-transparent outline-none text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
										placeholder="Search {sites.length} departments..."
										autocomplete="off"
										on:keydown={handleSiteKeydown}
									/>
									{#if siteSearchValue}
										<button
											class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
											on:click={() => (siteSearchValue = '')}
											aria-label="Clear search"
										>
											<svg
												class="w-3.5 h-3.5"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M6 18L18 6M6 6l12 12"
												/>
											</svg>
										</button>
									{/if}
								</div>

								<!-- Site list -->
								<div class="max-h-64 overflow-y-auto overscroll-contain">
									{#each filteredSites as site, idx}
										<button
											data-site-selected={idx === selectedSiteIdx}
											class="w-full flex items-center gap-2.5 px-3.5 py-2 text-left transition-colors {currentSite?.id ===
											site.id
												? 'bg-blue-50/60 dark:bg-blue-900/15'
												: ''} {idx === selectedSiteIdx
												? 'bg-gray-50 dark:bg-gray-800'
												: 'hover:bg-gray-50 dark:hover:bg-gray-800'}"
											on:click={() => selectSite(site)}
										>
											<div class="flex-1 min-w-0">
												<div class="text-sm text-gray-800 dark:text-gray-200 truncate">
													{site.display_name}
												</div>
												{#if site.web_url}
													<div class="text-xs text-gray-400 dark:text-gray-500 truncate">
														Department
													</div>
												{/if}
											</div>
											{#if currentSite?.id === site.id}
												<Check className="size-3.5 text-blue-500 dark:text-blue-400 shrink-0" />
											{/if}
										</button>
									{:else}
										<div class="px-3.5 py-6 text-sm text-center text-gray-400 dark:text-gray-500">
											No departments match your search
										</div>
									{/each}
								</div>
							</DropdownMenu.Content>
						</DropdownMenu.Root>
					{/if}
				</div>

				<!-- Breadcrumbs -->
				<div class="flex items-center gap-1 px-6 pb-2 text-xs overflow-x-auto scrollbar-none">
					<button
						class="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all shrink-0"
						on:click={() => navigateToBreadcrumb(-1)}
						aria-label="Navigate to root"
					>
						<svg
							class="w-3.5 h-3.5"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
							/>
						</svg>
						<span class="max-w-[8rem] truncate">{currentDrive?.name || 'Root'}</span>
					</button>
					{#each folderStack as folder, i}
						<svg
							class="w-3 h-3 text-gray-300 dark:text-gray-600 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
						</svg>
						<button
							class="px-1.5 py-0.5 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all truncate max-w-[10rem] shrink-0"
							on:click={() => navigateToBreadcrumb(i)}
						>
							{folder.name}
						</button>
					{/each}
				</div>

				<!-- File list -->
				<div
					class="flex-1 min-h-0 mx-6 mb-3 border border-gray-200/80 dark:border-gray-700/60 rounded-xl overflow-hidden bg-white dark:bg-gray-850"
				>
					<div class="h-full max-h-[24rem] overflow-y-auto overscroll-contain">
						{#if loading}
							<div class="flex flex-col items-center justify-center py-16">
								<Spinner className="size-5" />
								<p class="text-xs text-gray-400 dark:text-gray-500 mt-3">Loading files...</p>
							</div>
						{:else if items.length === 0}
							<div class="flex flex-col items-center justify-center py-16">
								<div
									class="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-3"
								>
									<svg
										class="w-5 h-5 text-gray-400 dark:text-gray-500"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
										/>
									</svg>
								</div>
								<p class="text-sm text-gray-500 dark:text-gray-400">This folder is empty</p>
							</div>
						{:else}
							<!-- Navigate up -->
							{#if folderStack.length > 0}
								<button
									class="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-800/60 text-left border-b border-gray-100 dark:border-gray-700/50 transition-colors group"
									on:click={navigateUp}
								>
									<div
										class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center group-hover:bg-gray-200 dark:group-hover:bg-gray-700 transition-colors"
									>
										<svg
											class="w-4 h-4 text-gray-500 dark:text-gray-400"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3"
											/>
										</svg>
									</div>
									<span class="text-sm text-gray-500 dark:text-gray-400">..</span>
								</button>
							{/if}
							<!-- Items -->
							{#each items as item}
								<button
									class="w-full px-4 py-2.5 flex items-center gap-3 text-left transition-all group
										{selectedItems.has(item.id) || selectedFolders.has(item.id)
										? 'bg-blue-50/70 dark:bg-blue-900/15 hover:bg-blue-50 dark:hover:bg-blue-900/20'
										: 'hover:bg-gray-50 dark:hover:bg-gray-800/60'}"
									on:click={() => toggleSelection(item)}
								>
									<!-- Checkbox for files and folders -->
									<div class="shrink-0">
										{#if item.is_folder}
											<!-- svelte-ignore a11y_click_events_have_key_events -->
											<!-- svelte-ignore a11y_no_static_element_interactions -->
											<div
												class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all cursor-pointer
												{selectedFolders.has(item.id)
													? 'bg-amber-500 border-amber-500 dark:bg-amber-500 dark:border-amber-500'
													: 'border-gray-300 dark:border-gray-600 hover:border-amber-400 dark:hover:border-amber-500'}"
												on:click={(e) => toggleFolderSelection(item, e)}
												title="Select folder to import all files"
											>
												{#if selectedFolders.has(item.id)}
													<svg
														class="w-3 h-3 text-white"
														fill="none"
														stroke="currentColor"
														stroke-width="3"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M4.5 12.75l6 6 9-13.5"
														/>
													</svg>
												{/if}
											</div>
										{:else}
											<div
												class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all
												{selectedItems.has(item.id)
													? 'bg-blue-500 border-blue-500 dark:bg-blue-500 dark:border-blue-500'
													: 'border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500'}"
											>
												{#if selectedItems.has(item.id)}
													<svg
														class="w-3 h-3 text-white"
														fill="none"
														stroke="currentColor"
														stroke-width="3"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M4.5 12.75l6 6 9-13.5"
														/>
													</svg>
												{/if}
											</div>
										{/if}
									</div>
									<!-- Icon -->
									<div
										class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0
										{item.is_folder ? 'bg-amber-50 dark:bg-amber-900/20' : 'bg-gray-50 dark:bg-gray-800'}"
									>
										<span class="text-base leading-none">{getFileIcon(item)}</span>
									</div>
									<!-- Name & meta -->
									<div class="flex-1 min-w-0">
										<div
											class="text-sm text-gray-800 dark:text-gray-200 truncate group-hover:text-gray-900 dark:group-hover:text-white transition-colors"
										>
											{item.name}
										</div>
										{#if item.is_folder}
											<div class="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">
												Click row to browse · Check to import all files
											</div>
										{:else if item.size}
											<div class="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">
												{formatFileSize(item.size)}
											</div>
										{/if}
									</div>
									<!-- Folder chevron -->
									{#if item.is_folder}
										<svg
											class="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-500 transition-colors shrink-0"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											viewBox="0 0 24 24"
										>
											<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
										</svg>
									{/if}
								</button>
							{/each}
						{/if}
					</div>
				</div>

				<!-- Footer -->
				<div
					class="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 rounded-b-4xl"
				>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{#if selectedItems.size > 0 || selectedFolders.size > 0}
							<span class="inline-flex items-center gap-1.5 flex-wrap">
								{#if selectedItems.size > 0}
									<span
										class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-[10px] font-bold"
									>
										{selectedItems.size}
									</span>
									<span>file{selectedItems.size === 1 ? '' : 's'}</span>
								{/if}
								{#if selectedFolders.size > 0}
									{#if selectedItems.size > 0}
										<span class="text-gray-300 dark:text-gray-600">+</span>
									{/if}
									<span
										class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-white text-[10px] font-bold"
									>
										{selectedFolders.size}
									</span>
									<span>folder{selectedFolders.size === 1 ? '' : 's'}</span>
								{/if}
								<span class="text-gray-400">selected</span>
							</span>
						{:else}
							Select files or folders to import
						{/if}
					</div>
					<div class="flex items-center gap-2">
						<button
							class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-all"
							on:click={() => (show = false)}
						>
							Cancel
						</button>
						<button
							class="px-4 py-2 text-sm font-medium text-white bg-gray-900 dark:bg-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-gray-900 dark:disabled:hover:bg-white flex items-center gap-2 shadow-sm active:scale-[0.98]"
							disabled={(selectedItems.size === 0 && selectedFolders.size === 0) || downloading}
							on:click={downloadSelected}
						>
							{#if downloading}
								<Spinner className="size-3.5" />
								Importing...
							{:else}
								<svg
									class="w-4 h-4"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
									/>
								</svg>
								Import Selected
							{/if}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
</Modal>
