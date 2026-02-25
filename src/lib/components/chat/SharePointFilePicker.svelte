<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import {
		getSharepointAuthStatus,
		getSharepointAuthUrl,
		logoutSharepoint,
		getSharepointTenants,
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
/** Files already in the space — used to pre-check matching items when the picker opens */
export let existingFiles: any[] = [];

	const dispatch = createEventDispatcher();
	const RECENT_DRIVES_KEY = 'sharepoint_recent_drives';
	const MAX_RECENT_DRIVES = 5;

	// ===== STATE =====
	let authStatus: SharePointAuthStatus | null = null;
	let tenants: TenantInfo[] = [];
	let currentTenant: TenantInfo | null = null;
	let drives: DriveInfo[] = [];
	let currentDrive: DriveInfo | null = null;
	let items: DriveItem[] = [];
	let selectedItems: Set<string> = new Set();
	let selectedFolders: Set<string> = new Set();

	// Derived sets of IDs already present in the space
	$: existingItemIds = new Set<string>(
		existingFiles.filter((f) => f.meta?.sharepoint_item_id).map((f) => f.meta.sharepoint_item_id)
	);
	$: existingFolderIds = new Set<string>(
		existingFiles.filter((f) => f.meta?.sharepoint_folder_id).map((f) => f.meta.sharepoint_folder_id)
	);

	// When the picker opens, pre-populate selection from existing space files
	$: if (show) {
		console.log('[SharePointPicker] Picker opened, pre-populating selection');
		console.log('[SharePointPicker] existingFiles:', existingFiles);
		console.log('[SharePointPicker] existingItemIds:', [...existingItemIds]);
		console.log('[SharePointPicker] existingFolderIds:', [...existingFolderIds]);
		selectedItems = new Set(existingItemIds);
		selectedFolders = new Set(existingFolderIds);
		console.log('[SharePointPicker] selectedItems after pre-population:', [...selectedItems]);
		console.log('[SharePointPicker] selectedFolders after pre-population:', [...selectedFolders]);
	}
	let folderStack: { id: string; name: string }[] = [];

	let sites: SiteInfo[] = [];
	let currentSite: SiteInfo | null = null;

	let loading = false;
	let loadingAuth = true;
	let loadingTenants = false;
	let loadingSites = false;
	let loadingDrives = false;
	let downloading = false;
	let abortController: AbortController | null = null;
	let importProgress = { current: 0, total: 0 };
	// Auth polling cleanup
	let authPollCleanup: (() => void) | null = null;
	let recentDriveIds: string[] = [];

	// ===== TREE STATE =====

	interface TreeNode {
		key: string;
		type: 'tenant' | 'site' | 'drive' | 'folder';
		label: string;
		tenant: TenantInfo;
		site?: SiteInfo;
		drive?: DriveInfo;
		folder?: DriveItem;
		/** Path from drive root to this folder node (inclusive), for setting folderStack */
		folderPath: { id: string; name: string }[];
	}

	interface FlatTreeItem {
		node: TreeNode;
		depth: number;
		isExpanded: boolean;
		isLoading: boolean;
		hasChildren: boolean;
	}

	let treeChildrenCache = new Map<string, TreeNode[]>();
	let expandedKeys = new Set<string>();
	let loadingKeys = new Set<string>();
	let sidebarSearch = '';
	let sidebarCollapsed = false;

	const treeFuse = new Fuse<TreeNode>([], { keys: ['label'], threshold: 0.4 });

	// Root nodes derived from tenants
	$: treeRootNodes = tenants.map(
		(t): TreeNode => ({
			key: `t:${t.id}`,
			type: 'tenant',
			label: t.name,
			tenant: t,
			folderPath: []
		})
	);

	// Active key: highlights the current location in the tree
	$: activeKey = (() => {
		if (!currentDrive || !currentTenant || !currentSite) return '';
		if (folderStack.length === 0) {
			return `drive:${currentTenant.id}:${currentSite.id}:${currentDrive.id}`;
		}
		return `folder:${currentDrive.id}:${folderStack[folderStack.length - 1].id}`;
	})();

	// All loaded nodes for fuzzy search
	$: allTreeNodes = collectAllNodes(treeRootNodes, treeChildrenCache);
	$: {
		treeFuse.setCollection(allTreeNodes);
	}

	// Flat list for rendering: either search results (grouped by tenant) or full tree
	$: flatTree = sidebarSearch
		? computeSearchResults(treeFuse.search(sidebarSearch).map((r) => r.item))
		: computeFlatTree(treeRootNodes, expandedKeys, loadingKeys, treeChildrenCache);

	// Group search results by tenant, showing tenant header + matching items + their children
	function computeSearchResults(matches: TreeNode[]): FlatTreeItem[] {
		if (matches.length === 0) return [];
		
		// Group by tenant
		const byTenant = new Map<string, TreeNode[]>();
		for (const node of matches) {
			const tenantKey = node.tenant.id;
			if (!byTenant.has(tenantKey)) byTenant.set(tenantKey, []);
			byTenant.get(tenantKey)!.push(node);
		}
		
		const result: FlatTreeItem[] = [];
		for (const [tenantId, nodes] of byTenant) {
			// Add tenant header
			const tenant = tenants.find((t) => t.id === tenantId);
			if (tenant) {
				result.push({
					node: { key: `t:${tenantId}`, type: 'tenant', label: tenant.name, tenant, folderPath: [] },
					depth: 0,
					isExpanded: true,
					isLoading: false,
					hasChildren: false
				});
			}
			// Add matching items under it, plus their cached children
			for (const node of nodes) {
				// Skip tenant nodes themselves (they're already headers)
				if (node.type === 'tenant') continue;
				
				// Check if this node has cached children
				const children = treeChildrenCache.get(node.key);
				const hasChildren = children !== undefined && children.length > 0;
				
				result.push({
					node,
					depth: 1,
					isExpanded: hasChildren, // Auto-expand if has children
					isLoading: loadingKeys.has(node.key),
					hasChildren: hasChildren || node.type === 'site' || node.type === 'drive'
				});
				
				// Include children (drives under sites, folders under drives)
				if (children && children.length > 0) {
					for (const child of children) {
						const childChildren = treeChildrenCache.get(child.key);
						const childHasChildren = childChildren !== undefined && childChildren.length > 0;
						
						result.push({
							node: child,
							depth: 2,
							isExpanded: false,
							isLoading: loadingKeys.has(child.key),
							hasChildren: childHasChildren || child.type === 'drive' || child.type === 'folder'
						});
					}
				}
			}
		}
		return result;
	}

	function collectAllNodes(roots: TreeNode[], cache: Map<string, TreeNode[]>): TreeNode[] {
		const result: TreeNode[] = [];
		const traverse = (nodes: TreeNode[]) => {
			for (const n of nodes) {
				result.push(n);
				const children = cache.get(n.key);
				if (children) traverse(children);
			}
		};
		traverse(roots);
		return result;
	}

	function computeFlatTree(
		nodes: TreeNode[],
		expanded: Set<string>,
		loading: Set<string>,
		cache: Map<string, TreeNode[]>,
		depth = 0
	): FlatTreeItem[] {
		const result: FlatTreeItem[] = [];
		for (const node of nodes) {
			const isExpanded = expanded.has(node.key);
			const isLoading = loading.has(node.key);
			const children = cache.get(node.key);
			// Tenant/site/drive always expandable; folder expandable if not loaded or has subfolders
			const hasChildren =
				node.type === 'tenant' ||
				node.type === 'site' ||
				node.type === 'drive' ||
				children === undefined ||
				children.length > 0;

			result.push({ node, depth, isExpanded, isLoading, hasChildren });

			if (isExpanded && children && children.length > 0) {
				result.push(...computeFlatTree(children, expanded, loading, cache, depth + 1));
			}
		}
		return result;
	}

	async function toggleTreeNode(node: TreeNode, event?: Event) {
		event?.stopPropagation();
		const key = node.key;
		if (expandedKeys.has(key)) {
			expandedKeys.delete(key);
			expandedKeys = new Set(expandedKeys);
		} else {
			expandedKeys.add(key);
			expandedKeys = new Set(expandedKeys);
			if (!treeChildrenCache.has(key)) {
				await loadTreeChildren(node);
			}
		}
	}

	async function loadTreeChildren(node: TreeNode) {
		loadingKeys.add(node.key);
		loadingKeys = new Set(loadingKeys);
		try {
			let children: TreeNode[] = [];

			if (node.type === 'tenant') {
				const sitesData = await getSharepointSites(token, node.tenant.id);
				children = sitesData.map(
					(s): TreeNode => ({
						key: `site:${node.tenant.id}:${s.id}`,
						type: 'site',
						label: s.display_name,
						tenant: node.tenant,
						site: s,
						folderPath: []
					})
				);
			} else if (node.type === 'site' && node.site) {
                let drivesData = await getSharepointSiteDrives(token, node.tenant.id, node.site.id);
                // Filter out system libraries like Preservation Hold Library
                drivesData = drivesData.filter((d) => !d.name.toLowerCase().includes('preservation hold'));
                children = drivesData.map(
                    (d): TreeNode => ({
                        key: `drive:${node.tenant.id}:${node.site!.id}:${d.id}`,
                        type: 'drive',
                        label: d.name,
                        tenant: node.tenant,
                        site: node.site,
                        drive: d,
                        folderPath: []
                    })
                );
			} else if ((node.type === 'drive' || node.type === 'folder') && node.drive) {
				const folderId = node.type === 'folder' ? node.folder?.id : undefined;
				const folderItems = await getSharepointFiles(
					token,
					node.tenant.id,
					node.drive.id,
					folderId
				);
				const basePath = node.type === 'folder' ? node.folderPath : [];
				children = folderItems
					.filter((i) => i.is_folder)
					.map(
						(i): TreeNode => ({
							key: `folder:${node.drive!.id}:${i.id}`,
							type: 'folder',
							label: i.name,
							tenant: node.tenant,
							site: node.site,
							drive: node.drive!,
							folder: i,
							folderPath: [...basePath, { id: i.id, name: i.name }]
						})
					);
			}

			treeChildrenCache.set(node.key, children);
			treeChildrenCache = new Map(treeChildrenCache);
		} catch (e) {
			console.error('Failed to load tree children:', e);
			treeChildrenCache.set(node.key, []);
			treeChildrenCache = new Map(treeChildrenCache);
		} finally {
			loadingKeys.delete(node.key);
			loadingKeys = new Set(loadingKeys);
		}
	}

	async function navigateToTreeNode(node: TreeNode) {
		// Tenants: just toggle expand
		if (node.type === 'tenant') {
			await toggleTreeNode(node);
			return;
		}
		// Sites: select the site (loads its drives, auto-selects first drive)
		if (node.type === 'site' && node.site) {
			currentTenant = node.tenant;
			await selectSite(node.site);
			if (!expandedKeys.has(node.key)) {
				expandedKeys.add(node.key);
				expandedKeys = new Set(expandedKeys);
				if (!treeChildrenCache.has(node.key)) {
					await loadTreeChildren(node);
				}
			}
			return;
		}
		// Drives: navigate to drive root AND expand
		if (node.type === 'drive' && node.drive) {
			currentTenant = node.tenant;
			if (node.site) currentSite = node.site;
			await selectDrive(node.drive);
			// Also expand to show subfolders
			if (!expandedKeys.has(node.key)) {
				expandedKeys.add(node.key);
				expandedKeys = new Set(expandedKeys);
				if (!treeChildrenCache.has(node.key)) {
					await loadTreeChildren(node);
				}
			}
			return;
		}
		// Folders: navigate directly into folder AND expand
		if (node.type === 'folder' && node.folder && node.drive) {
			currentTenant = node.tenant;
			if (node.site) currentSite = node.site;
			currentDrive = node.drive;
			folderStack = node.folderPath;
			selectedItems = new Set();
			selectedFolders = new Set();
			await loadItems(node.folder.id);
			// Also expand to show subfolders
			if (!expandedKeys.has(node.key)) {
				expandedKeys.add(node.key);
				expandedKeys = new Set(expandedKeys);
				if (!treeChildrenCache.has(node.key)) {
					await loadTreeChildren(node);
				}
			}
			return;
		}
	}

	// ===== PRESERVED FUNCTIONS =====

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

	onMount(async () => {
		loadRecentDrives();
		await checkAuthStatus();
	});
	onDestroy(() => {
		authPollCleanup?.();
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
		selectedItems = new Set();
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
			// Populate tree cache and auto-expand this tenant
			const tenantKey = `t:${currentTenant.id}`;
			const tenant = currentTenant;
			const siteNodes: TreeNode[] = sites.map((s) => ({
				key: `site:${tenant.id}:${s.id}`,
				type: 'site' as const,
				label: s.display_name,
				tenant,
				site: s,
				folderPath: []
			}));
			treeChildrenCache.set(tenantKey, siteNodes);
			treeChildrenCache = new Map(treeChildrenCache);
			expandedKeys.add(tenantKey);
			expandedKeys = new Set(expandedKeys);
		} catch (error) {
			console.error('Failed to load sites:', error);
			toast.error('Failed to load departments');
		} finally {
			loadingSites = false;
		}
	}

	async function selectSite(site: SiteInfo) {
		currentSite = site;
		currentDrive = null;
		drives = [];
		folderStack = [];
		selectedItems = new Set();
		selectedFolders = new Set();

		loadingDrives = true;
		try {
			drives = await getSharepointSiteDrives(token, currentTenant!.id, site.id);
			// Filter out system libraries like Preservation Hold Library
			drives = drives.filter((d) => !d.name.toLowerCase().includes('preservation hold'));
			// Don't auto-select a drive - let user pick from the sidebar tree
			// Populate tree cache and auto-expand this site
			const siteKey = `site:${currentTenant!.id}:${site.id}`;
			const tenant = currentTenant!;
			const driveNodes: TreeNode[] = drives.map((d) => ({
				key: `drive:${tenant.id}:${site.id}:${d.id}`,
				type: 'drive' as const,
				label: d.name,
				tenant,
				site,
				drive: d,
				folderPath: []
			}));
			treeChildrenCache.set(siteKey, driveNodes);
			treeChildrenCache = new Map(treeChildrenCache);
			expandedKeys.add(siteKey);
			expandedKeys = new Set(expandedKeys);
		} catch (error) {
			console.error('Failed to load site drives:', error);
			toast.error('Failed to load document libraries');
		} finally {
			loadingDrives = false;
		}
	}

	async function startAuth() {
		// Kill any existing poll before starting a new one
		authPollCleanup?.();

		try {
			const { url } = await getSharepointAuthUrl(token);
			const popup = window.open(url, '_blank', 'width=600,height=700');

			let active = true;
			const interval = setInterval(async () => {
				// Stop if popup was manually closed
				if (popup?.closed) {
					authPollCleanup?.();
					return;
				}
				if (!active) return;
				try {
					const status = await getSharepointAuthStatus(token);
					if (status.authenticated) {
						authPollCleanup?.();
						authStatus = status;
						await loadTenants();
						toast.success('Connected to SharePoint');
					}
				} catch {
					// Ignore transient polling errors
				}
			}, 2000);

			const timeout = setTimeout(() => authPollCleanup?.(), 5 * 60 * 1000);

			authPollCleanup = () => {
				active = false;
				clearInterval(interval);
				clearTimeout(timeout);
				authPollCleanup = null;
			};
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
			selectedItems = new Set();
			selectedFolders = new Set();
			folderStack = [];
			// Reset tree state
			treeChildrenCache = new Map();
			expandedKeys = new Set();
			loadingKeys = new Set();
			toast.success('Disconnected from SharePoint');
		} catch (error) {
			console.error('Failed to logout:', error);
			toast.error('Failed to disconnect from SharePoint');
		}
	}



	async function selectDrive(drive: DriveInfo) {
		currentDrive = drive;
		saveRecentDrive(drive.id);
		folderStack = [];
		selectedItems = new Set();
		selectedFolders = new Set();
		await loadItems();
	}

	async function loadItems(folderId?: string) {
		if (!currentDrive || !currentTenant) return;

		loading = true;
		try {
			items = await getSharepointFiles(token, currentTenant.id, currentDrive.id, folderId);
			console.log('[SharePointPicker] Loaded items:', items.map(i => ({ id: i.id, name: i.name, is_folder: i.is_folder })));
			console.log('[SharePointPicker] Checking selection match - selectedItems:', [...selectedItems]);
			console.log('[SharePointPicker] Items that match selection:', items.filter(i => selectedItems.has(i.id)).map(i => i.name));
		} catch (error) {
			console.error('Failed to load files:', error);
			toast.error('Failed to load files');
		} finally {
			loading = false;
	}

	async function navigateToFolder(item: DriveItem) {
		const newFolderStack = [...folderStack, { id: item.id, name: item.name }];
		folderStack = newFolderStack;
		selectedItems = new Set();
		selectedFolders = new Set();
		// Sync tree: expand the folder node if it exists in cache
		if (currentDrive) {
			const folderKey = `folder:${currentDrive.id}:${item.id}`;
			expandedKeys.add(folderKey);
			expandedKeys = new Set(expandedKeys);
			if (!treeChildrenCache.has(folderKey)) {
				// Lazy-load tree children for this folder so sidebar stays in sync
				const folderNode: TreeNode | undefined = (() => {
					for (const [, children] of treeChildrenCache) {
						const found = children.find((n) => n.key === folderKey);
						if (found) return found;
					}
				})();
				if (folderNode) loadTreeChildren(folderNode);
			}
		}
		await loadItems(item.id);
	}

	async function navigateUp() {
		if (folderStack.length === 0) return;
		folderStack = folderStack.slice(0, -1);
		selectedItems = new Set();
		selectedFolders = new Set();
		const parentId = folderStack.length > 0 ? folderStack[folderStack.length - 1].id : undefined;
		await loadItems(parentId);
	}

	async function navigateToBreadcrumb(index: number) {
		if (index < 0) {
			folderStack = [];
			selectedItems = new Set();
			selectedFolders = new Set();
			await loadItems();
		} else {
			folderStack = folderStack.slice(0, index + 1);
			selectedItems = new Set();
			selectedFolders = new Set();
			await loadItems(folderStack[index].id);
		}
	}

	function toggleFolderSelection(item: DriveItem, event: MouseEvent) {
		event.stopPropagation();
		if (selectedFolders.has(item.id)) selectedFolders.delete(item.id);
		else selectedFolders.add(item.id);
		selectedFolders = selectedFolders;
	}

	function toggleSelection(item: DriveItem) {
		if (item.is_folder) {
			navigateToFolder(item);
			return;
		}
		if (selectedItems.has(item.id)) selectedItems.delete(item.id);
		else selectedItems.add(item.id);
		selectedItems = selectedItems;
	}

	// ===== IMPORT HELPERS =====

	function buildItemsMap(): Map<string, DriveItem> {
		return new Map(items.map((i) => [i.id, i]));
	}

	async function importToSpace(signal: AbortSignal) {
		const itemsMap = buildItemsMap();
		let totalAdded = 0;
		let totalSkipped = 0;
		let totalFailed = 0;

		importProgress.total = selectedFolders.size + selectedItems.size;
		importProgress = { ...importProgress };

		for (const folderId of selectedFolders) {
			if (signal.aborted) break;
			const folderName = itemsMap.get(folderId)?.name ?? 'folder';
			const result = await addSharePointFolderToSpace(
				token, spaceId!, currentTenant!.id, currentDrive!.id,
				folderId, folderName, currentSite?.display_name, true, 10, signal
			);
			if (signal.aborted) break;
			totalAdded += result.added;
			totalSkipped += result.skipped;
			totalFailed += result.failed;
			for (const file of result.files) dispatch('fileDownloaded', file);
			importProgress = { ...importProgress, current: importProgress.current + 1 };
		}

		for (const itemId of selectedItems) {
			if (signal.aborted) break;
			const item = itemsMap.get(itemId);
			if (!item || item.is_folder) continue;
			const result = await downloadSharepointFile(
				token, currentTenant!.id, currentDrive!.id, item.id, item.name, signal
			);
			if (signal.aborted) break;
			dispatch('fileDownloaded', result);
			totalAdded++;
			importProgress = { ...importProgress, current: importProgress.current + 1 };
		}

		if (signal.aborted) {
			toast.warning(`Cancelled. Imported ${totalAdded} file(s) before stopping.`);
		} else {
			const msg =
				`Imported ${totalAdded} file(s)`
				+ (totalSkipped > 0 ? `, ${totalSkipped} skipped` : '')
				+ (totalFailed > 0 ? `, ${totalFailed} failed` : '');
			toast.success(msg);
		}
	}

	async function importDirect(signal: AbortSignal) {
		const itemsMap = buildItemsMap();
		const filesToDownload: DriveItem[] = items.filter(
			(item) => selectedItems.has(item.id) && !item.is_folder
		);

		for (const folderId of selectedFolders) {
			if (signal.aborted) break;
			const folderName = itemsMap.get(folderId)?.name ?? 'folder';
			toast.info(`Scanning ${folderName}...`);
			const folderFiles = await getSharepointFilesRecursive(
				token, currentTenant!.id, currentDrive!.id, folderId, 10, signal
			);
			if (signal.aborted) break;
			filesToDownload.push(...folderFiles);
		}

		if (signal.aborted) {
			toast.warning('Cancelled during folder scan.');
			return;
		}
		if (filesToDownload.length === 0) {
			toast.warning('No files to import');
			return;
		}

		importProgress = { current: 0, total: filesToDownload.length };
		for (const file of filesToDownload) {
			if (signal.aborted) break;
			const result = await downloadSharepointFile(
				token, currentTenant!.id, currentDrive!.id, file.id, file.name, signal
			);
			if (signal.aborted) break;
			dispatch('fileDownloaded', result);
			importProgress = { ...importProgress, current: importProgress.current + 1 };
		}

		if (signal.aborted) {
			toast.warning(`Cancelled. Imported ${importProgress.current} of ${importProgress.total} files.`);
		} else {
			toast.success(`Imported ${filesToDownload.length} file(s)`);
		}
	}

	async function downloadSelected() {
		if (!currentDrive || !currentTenant || (selectedItems.size === 0 && selectedFolders.size === 0)) return;

		downloading = true;
		abortController = new AbortController();
		importProgress = { current: 0, total: 0 };
		const signal = abortController.signal;

		try {
			if (spaceId && selectedFolders.size > 0) {
				await importToSpace(signal);
			} else {
				await importDirect(signal);
			}
			if (!signal.aborted) {
				selectedItems = new Set();
				selectedFolders = new Set();
				show = false;
			}
		} catch (error) {
			if (signal.aborted) {
				toast.warning(`Cancelled. Imported ${importProgress.current} of ${importProgress.total} files.`);
			} else {
				console.error('Failed to download files:', error);
				toast.error('Failed to download files');
			}
		} finally {
			downloading = false;
			abortController = null;
			importProgress = { current: 0, total: 0 };
		}
	}

	function cancelImport() {
		if (abortController) {
			abortController.abort();
		}
	}

	function formatFileSize(bytes?: number): string {
		if (!bytes) return '';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
		return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
	}

	function formatDate(dateStr?: string): string {
		if (!dateStr) return '';
		try {
			const d = new Date(dateStr);
			const now = new Date();
			const diff = now.getTime() - d.getTime();
			const days = Math.floor(diff / (1000 * 60 * 60 * 24));
			if (days === 0) return 'Today';
			if (days === 1) return 'Yesterday';
			if (days < 7) return `${days}d ago`;
			if (days < 365) {
				return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
			}
			return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
		} catch {
			return '';
		}
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

<Modal bind:show size="xl">
	<div class="flex flex-col" style="height: 80vh; max-height: 80vh;">
		<!-- ── Header ────────────────────────────────────────────── -->
		<div class="flex items-center justify-between px-5 pt-4 pb-3 shrink-0">
			<div class="flex items-center gap-2.5">
				<div
					class="flex items-center justify-center w-7 h-7 rounded-lg bg-gradient-to-br from-sky-500 to-blue-600 shadow-sm shrink-0"
				>
					<svg
						class="w-3.5 h-3.5 text-white"
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
				<h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
					SharePoint Files
				</h2>
			</div>
			<div class="flex items-center gap-1.5">
				{#if authStatus?.authenticated}
					<button
						class="text-xs text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition-colors px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={logout}
					>
						Disconnect
					</button>
				{/if}
				<button
					class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
					on:click={() => {
						if (downloading) cancelImport();
						show = false;
					}}
					aria-label="Close"
				>
					<svg
						class="w-3.5 h-3.5"
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

		<!-- ── Body ─────────────────────────────────────────────── -->
		{#if loadingAuth}
			<div class="flex flex-col items-center justify-center flex-1 pb-8">
				<Spinner className="size-5" />
				<p class="text-sm text-gray-400 dark:text-gray-500 mt-3">Connecting to SharePoint...</p>
			</div>
		{:else if !authStatus?.enabled}
			<div class="flex flex-col items-center justify-center flex-1 pb-8 px-6">
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
			<div class="flex flex-col items-center justify-center flex-1 pb-8 px-6">
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
			<!-- ── Connected: Split-Pane Explorer ──────────────── -->
			<div
				class="flex flex-1 min-h-0 overflow-hidden border-t border-gray-100 dark:border-gray-800/60"
			>
				<!-- ── Left Sidebar ─────────────────────────────── -->
				<div
					class="flex flex-col border-r border-gray-200/70 dark:border-gray-700/50 bg-gray-50/60 dark:bg-gray-900/30 transition-all duration-200 {sidebarCollapsed
						? 'w-0 overflow-hidden'
						: 'w-60 sm:w-64 shrink-0'}"
				>
					<!-- Search bar -->
					<div class="px-2.5 py-2 border-b border-gray-200/60 dark:border-gray-700/40 shrink-0">
						<div
							class="flex items-center gap-1.5 px-2.5 py-1.5 bg-white dark:bg-gray-800/70 rounded-lg border border-gray-200/80 dark:border-gray-700/60"
						>
							<Search className="size-3 text-gray-400 shrink-0" />
							<input
								bind:value={sidebarSearch}
								class="flex-1 text-xs bg-transparent outline-none text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 min-w-0"
								placeholder="Search..."
								autocomplete="off"
							/>
							{#if sidebarSearch}
								<button
									class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors shrink-0"
									on:click={() => (sidebarSearch = '')}
									aria-label="Clear search"
								>
									<svg
										class="w-3 h-3"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										viewBox="0 0 24 24"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							{/if}
						</div>
					</div>

					<!-- Tree -->
					<div class="flex-1 min-h-0 overflow-y-auto overscroll-contain py-1 px-1">
						{#if loadingTenants || loadingSites}
							<div class="flex items-center gap-2 px-3 py-2 mt-1">
								<Spinner className="size-3 text-gray-400" />
								<span class="text-xs text-gray-400 dark:text-gray-500">Loading...</span>
							</div>
						{:else if flatTree.length === 0 && sidebarSearch}
							<div class="px-3 py-4 text-xs text-gray-400 dark:text-gray-500 text-center">
								No results for "<span class="text-gray-600 dark:text-gray-400">{sidebarSearch}</span
								>"
							</div>
						{:else}
							{#each flatTree as item (item.node.key)}
								<!-- svelte-ignore a11y_click_events_have_key_events -->
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									class="group flex items-center min-w-0 h-[26px] cursor-pointer select-none rounded-md transition-colors duration-100
										{activeKey === item.node.key
										? 'bg-blue-500/10 dark:bg-blue-500/15'
										: 'hover:bg-gray-100/80 dark:hover:bg-gray-800/60'}"
									style="padding-left: {6 + item.depth * 8}px; padding-right: 4px;"
									on:click={() => navigateToTreeNode(item.node)}
								>
									<!-- Expand/collapse chevron -->
									<div
										class="flex items-center justify-center w-4 h-4 shrink-0 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors mr-0.5"
										on:click|stopPropagation={() => toggleTreeNode(item.node)}
										role="button"
										aria-label={item.isExpanded ? 'Collapse' : 'Expand'}
										tabindex="-1"
									>
										{#if item.isLoading}
											<Spinner className="size-2.5 text-gray-400" />
										{:else if item.hasChildren}
											<ChevronDown
												className="size-2.5 text-gray-400 dark:text-gray-500 transition-transform duration-150 {item.isExpanded
													? ''
													: '-rotate-90'}"
											/>
										{/if}
									</div>

									<!-- Node icon -->
									<span class="text-xs mr-1 shrink-0 leading-none">
										{#if item.node.type === 'tenant'}🏢
										{:else if item.node.type === 'site'}🏛️
										{:else if item.node.type === 'drive'}💼
										{:else}📁
										{/if}
									</span>

									<!-- Label -->
									<span
										class="text-xs truncate leading-tight transition-colors
											{activeKey === item.node.key
											? 'text-blue-700 dark:text-blue-300 font-medium'
											: 'text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white'}"
									>
										{item.node.label}
									</span>

									<!-- Active indicator dot -->
									{#if activeKey === item.node.key}
										<div class="w-1 h-1 rounded-full bg-blue-500 shrink-0 ml-auto mr-1" />
									{/if}
								</div>
							{/each}
						{/if}
					</div>
				</div>

				<!-- ── Right Main Pane ───────────────────────────── -->
				<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
					<!-- Breadcrumb + sidebar toggle -->
					<div
						class="flex items-center gap-0.5 px-3 py-2 border-b border-gray-100 dark:border-gray-800/60 bg-white/50 dark:bg-gray-900/20 overflow-x-auto scrollbar-none shrink-0"
					>
						<!-- Sidebar toggle (mobile / compact) -->
						<button
							class="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 shrink-0 mr-0.5 transition-colors"
							on:click={() => (sidebarCollapsed = !sidebarCollapsed)}
							aria-label="Toggle sidebar"
						>
							<svg
								class="w-3.5 h-3.5"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
							</svg>
						</button>

						{#if currentDrive}
							<!-- Tenant context (only with multiple tenants) -->
							{#if currentTenant && tenants.length > 1}
								<span
									class="text-xs text-gray-400 dark:text-gray-600 shrink-0 truncate max-w-[6rem]"
									>{currentTenant.name}</span
								>
								<svg
									class="w-2.5 h-2.5 text-gray-300 dark:text-gray-700 shrink-0"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									viewBox="0 0 24 24"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
								</svg>
							{/if}

							<!-- Site name -->
							{#if currentSite}
								<span
									class="text-xs text-gray-400 dark:text-gray-600 truncate max-w-[8rem] shrink-0"
									>{currentSite.display_name}</span
								>
								<svg
									class="w-2.5 h-2.5 text-gray-300 dark:text-gray-700 shrink-0"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									viewBox="0 0 24 24"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
								</svg>
							{/if}

							<!-- Drive root (clickable) -->
							<button
								class="text-xs px-1 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors shrink-0 font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white max-w-[8rem] truncate"
								on:click={() => navigateToBreadcrumb(-1)}
							>
								{currentDrive.name}
							</button>

							<!-- Folder breadcrumbs -->
							{#each folderStack as folder, i}
								<svg
									class="w-2.5 h-2.5 text-gray-300 dark:text-gray-700 shrink-0"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									viewBox="0 0 24 24"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
								</svg>
								<button
									class="text-xs px-1 py-0.5 rounded transition-colors shrink-0 truncate max-w-[10rem]
										{i === folderStack.length - 1
										? 'text-gray-800 dark:text-gray-100 font-semibold cursor-default'
										: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'}"
									on:click={() => navigateToBreadcrumb(i)}
								>
									{folder.name}
								</button>
							{/each}
						{:else}
							<span class="text-xs text-gray-400 dark:text-gray-500 italic">
								Select a location from the sidebar
							</span>
						{/if}
					</div>

					<!-- Column headers (shown when there are items) -->
					{#if !loading && items.length > 0 && currentDrive}
						<div
							class="flex items-center px-4 py-1.5 border-b border-gray-100 dark:border-gray-800/50 bg-gray-50/40 dark:bg-gray-900/10 shrink-0"
						>
							<div class="w-5 shrink-0 mr-3" />
							<div class="w-8 shrink-0 mr-2.5" />
							<div
								class="flex-1 text-[10px] font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-wider"
							>
								Name
							</div>
							<div
								class="w-20 text-right text-[10px] font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-wider shrink-0 hidden sm:block"
							>
								Size
							</div>
							<div
								class="w-24 text-right text-[10px] font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-wider shrink-0 hidden md:block"
							>
								Modified
							</div>
							<div class="w-4 shrink-0 ml-1" />
						</div>
					{/if}

					<!-- File list -->
					<div class="flex-1 min-h-0 overflow-y-auto overscroll-contain">
						{#if loading}
							<div class="flex flex-col items-center justify-center h-full">
								<Spinner className="size-5" />
								<p class="text-xs text-gray-400 dark:text-gray-500 mt-3">Loading files...</p>
							</div>
						{:else if !currentDrive && currentSite && drives.length > 0}
							<!-- Show available drives when site is selected but no drive chosen -->
							<div class="p-4">
								<div class="mb-3">
									<p class="text-sm font-medium text-gray-700 dark:text-gray-300">
										Document Libraries in {currentSite.display_name}
									</p>
									<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
										Select a document library to browse files
									</p>
								</div>
								<div class="grid gap-2">
									{#each drives as drive}
										<button
											class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all text-left group"
											on:click={() => selectDrive(drive)}
										>
											<div class="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center shrink-0 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
												<span class="text-lg">💼</span>
											</div>
											<div class="min-w-0 flex-1">
												<p class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate group-hover:text-gray-900 dark:group-hover:text-white">{drive.name}</p>
												{#if drive.drive_type}
													<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{drive.drive_type}</p>
												{/if}
											</div>
											<svg
												class="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-500 transition-colors shrink-0"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												viewBox="0 0 24 24"
											>
												<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
											</svg>
										</button>
									{/each}
								</div>
							</div>
						{:else if !currentDrive}
							<div class="flex flex-col items-center justify-center h-full text-center px-6">
								<div
									class="w-12 h-12 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-3"
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
											d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
										/>
									</svg>
								</div>
								<p class="text-sm font-medium text-gray-600 dark:text-gray-400">
									Choose a location
								</p>
								<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
									Expand the sidebar tree to navigate to a drive or folder
								</p>
							</div>
						{:else if items.length === 0}
							<div class="flex flex-col items-center justify-center h-full">
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
							<!-- Navigate up row -->
							{#if folderStack.length > 0}
								<button
									class="w-full flex items-center gap-0 px-4 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800/40 border-b border-gray-100/80 dark:border-gray-800/40 text-left transition-colors group"
									on:click={navigateUp}
								>
									<div class="w-5 shrink-0 mr-3" />
									<div
										class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center group-hover:bg-gray-200 dark:group-hover:bg-gray-700 transition-colors shrink-0 mr-2.5"
									>
										<svg
											class="w-3.5 h-3.5 text-gray-500 dark:text-gray-400"
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
									<span class="text-xs text-gray-500 dark:text-gray-400">..</span>
								</button>
							{/if}

							<!-- File/folder rows -->
							{#each items as item}
								<!-- svelte-ignore a11y_click_events_have_key_events -->
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									class="group flex items-center px-4 py-1.5 border-b border-gray-50 dark:border-gray-800/30 last:border-0 transition-colors
										{selectedItems.has(item.id) || selectedFolders.has(item.id)
										? 'bg-blue-50/60 dark:bg-blue-900/10'
										: 'hover:bg-gray-50/70 dark:hover:bg-gray-800/30'}"
									on:click={() => {
										if (!item.is_folder) {
											// File: toggle selection on row click
											if (selectedItems.has(item.id)) {
												selectedItems.delete(item.id);
											} else {
												selectedItems.add(item.id);
											}
											selectedItems = selectedItems;
										}
									}}
									on:dblclick={() => {
										if (item.is_folder) navigateToFolder(item);
									}}
								>
									<!-- Checkbox -->
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="w-5 shrink-0 mr-3 flex items-center justify-center"
										title={item.is_folder ? 'Import all files in this folder' : undefined}
								on:click|stopPropagation={() => {
									if (item.is_folder) {
										const next = new Set(selectedFolders);
										if (next.has(item.id)) next.delete(item.id); else next.add(item.id);
										selectedFolders = next;
									} else {
										const next = new Set(selectedItems);
										if (next.has(item.id)) next.delete(item.id); else next.add(item.id);
										selectedItems = next;
									}
								}}
									>
										<div
										class="w-4 h-4 rounded border-2 flex items-center justify-center transition-all cursor-pointer
											{item.is_folder
											? selectedFolders.has(item.id)
												? existingFolderIds.has(item.id)
													? 'bg-green-500 border-green-500'
													: 'bg-amber-500 border-amber-500'
												: 'border-gray-300 dark:border-gray-600 hover:border-amber-400 dark:hover:border-amber-500'
											: selectedItems.has(item.id)
												? existingItemIds.has(item.id)
													? 'bg-green-500 border-green-500'
													: 'bg-blue-500 border-blue-500'
												: 'border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500'}"
									>
											{#if selectedItems.has(item.id) || selectedFolders.has(item.id)}
												<svg
													class="w-2.5 h-2.5 text-white"
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
									</div>

									<!-- File/folder icon -->
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mr-2.5 transition-colors
											{item.is_folder
											? 'bg-amber-50 dark:bg-amber-900/20 group-hover:bg-amber-100 dark:group-hover:bg-amber-900/30'
											: 'bg-gray-50 dark:bg-gray-800/60 group-hover:bg-gray-100 dark:group-hover:bg-gray-800'}"
										on:click|stopPropagation={() => {
											if (item.is_folder) navigateToFolder(item);
										}}
									>
										<span class="text-sm leading-none">{getFileIcon(item)}</span>
									</div>

									<!-- Name + subtitle -->
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="flex-1 min-w-0 cursor-pointer"
										on:click|stopPropagation={() => {
											if (item.is_folder) navigateToFolder(item);
										}}
									>
										<div
											class="text-xs font-medium text-gray-800 dark:text-gray-200 truncate group-hover:text-gray-900 dark:group-hover:text-white transition-colors"
										>
											{item.name}
										</div>
										{#if item.is_folder}
											<div
												class="text-[10px] mt-0.5 hidden sm:block transition-colors
													{selectedFolders.has(item.id) ? 'text-amber-500/80 dark:text-amber-400/70' : 'text-gray-400 dark:text-gray-600'}"
											>
												{selectedFolders.has(item.id) ? 'All contents will be imported' : 'Folder · click to open'}
											</div>
										{/if}
									</div>

									<!-- Size (files only) -->
									<div
										class="w-20 text-right text-[11px] text-gray-400 dark:text-gray-500 shrink-0 hidden sm:block"
									>
										{#if !item.is_folder && item.size}
											{formatFileSize(item.size)}
										{:else if item.is_folder}
											—
										{/if}
									</div>

									<!-- Modified date -->
									<div
										class="w-24 text-right text-[11px] text-gray-400 dark:text-gray-500 shrink-0 hidden md:block"
									>
										{formatDate(item.modified_at)}
									</div>

									<!-- Navigate arrow for folders -->
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="ml-1 w-4 shrink-0"
										on:click|stopPropagation={() => {
											if (item.is_folder) navigateToFolder(item);
										}}
									>
										{#if item.is_folder}
											<svg
												class="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-500 transition-colors"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												viewBox="0 0 24 24"
											>
												<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
											</svg>
										{/if}
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>
			</div>

			<!-- ── Footer ────────────────────────────────────────── -->
			<div class="shrink-0 border-t border-gray-100 dark:border-gray-800/80 bg-gray-50/40 dark:bg-gray-900/20">
				<!-- Thin progress bar -->
				{#if downloading}
					<div class="h-0.5 bg-gray-200 dark:bg-gray-800 overflow-hidden">
						{#if importProgress.total > 0}
							<div
								class="h-full bg-blue-500 dark:bg-blue-400 transition-all duration-500 ease-out"
								style="width: {Math.round((importProgress.current / importProgress.total) * 100)}%"
							/>
						{:else}
							<div class="h-full bg-blue-500/40 dark:bg-blue-400/40 animate-pulse" />
						{/if}
					</div>
				{/if}

				<div class="flex items-center justify-between px-4 py-3">
					<!-- Status / selection count -->
					<div class="text-xs text-gray-500 dark:text-gray-400 min-w-0 mr-3">
						{#if downloading && importProgress.total > 0}
							<span class="inline-flex items-center gap-2">
								<Spinner className="size-3 shrink-0" />
								<span class="font-medium text-gray-700 dark:text-gray-300 truncate tabular-nums">
									{importProgress.current}<span class="text-gray-400 dark:text-gray-500 mx-0.5">/</span>{importProgress.total}
								</span>
								<span class="text-gray-400 dark:text-gray-500">imported</span>
							</span>
						{:else if downloading}
							<span class="inline-flex items-center gap-2">
								<Spinner className="size-3 shrink-0" />
								<span class="text-gray-500 dark:text-gray-400">Scanning folders…</span>
							</span>
						{:else if selectedItems.size > 0 || selectedFolders.size > 0}
							<span class="inline-flex items-center gap-1.5 flex-wrap">
								{#if selectedItems.size > 0}
									<span class="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-blue-500/90 text-white text-[10px] font-bold tabular-nums">
										{selectedItems.size}
									</span>
									<span>file{selectedItems.size === 1 ? '' : 's'}</span>
								{/if}
								{#if selectedFolders.size > 0}
									{#if selectedItems.size > 0}
										<span class="text-gray-300 dark:text-gray-600">·</span>
									{/if}
									<span class="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-amber-500/90 text-white text-[10px] font-bold tabular-nums">
										{selectedFolders.size}
									</span>
									<span>folder{selectedFolders.size === 1 ? '' : 's'}</span>
								{/if}
								<span class="text-gray-400 dark:text-gray-500">selected</span>
							</span>
						{:else}
							<span class="text-gray-400 dark:text-gray-500">Select files or folders to import</span>
						{/if}
					</div>

					<!-- Action buttons -->
					<div class="flex items-center gap-2 shrink-0">
						{#if downloading}
							<button
								class="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:text-white dark:hover:text-white hover:bg-red-500 dark:hover:bg-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg transition-all"
								on:click={cancelImport}
							>
								Cancel Import
							</button>
						{:else}
							<button
								class="px-3 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-all"
								on:click={() => (show = false)}
							>
								Cancel
							</button>
							<button
								class="px-3.5 py-1.5 text-xs font-medium text-white bg-gray-900 dark:bg-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
								disabled={selectedItems.size === 0 && selectedFolders.size === 0}
								on:click={downloadSelected}
							>
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
								</svg>
								{#if selectedFolders.size > 0 && selectedItems.size === 0}
									Import Folder{selectedFolders.size === 1 ? '' : 's'}
								{:else if selectedItems.size > 0 && selectedFolders.size === 0}
									Import File{selectedItems.size === 1 ? '' : 's'}
								{:else}
									Import Selected
								{/if}
							</button>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>
</Modal>
