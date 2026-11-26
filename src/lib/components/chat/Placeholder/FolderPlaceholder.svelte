<script lang="ts">
	import { getContext, onMount, setContext, tick } from 'svelte';
	import { writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { config, machines, showFileNavPath, socket, selectedFolder, user } from '$lib/stores';
	import { resolveMachineTarget } from '$lib/apis/machines';
	import { machineIdOf } from '$lib/utils/machines';
	import { folderSessionId } from '$lib/utils/chatId';
	import {
		changeChatView,
		chatViewChanges,
		chatViewEntry,
		loadChatView
	} from '$lib/stores/chatViewStates';
	import {
		loadFolderChatPage,
		folderChatPageKey,
		getFolderState,
		updateFolderDetails,
		markFolderChatsDirty,
		isCancelledFolderRequest,
		type FolderDetails
	} from '$lib/stores/folderStates';
	import {
		registerFolderRefreshHandler,
		refreshChatList,
		refreshFolderChatLists
	} from '$lib/stores/chatList';
	import {
		FOLDER_PAGE_SIZE,
		type FolderSection,
		NO_STATUS,
		NO_PRIORITY,
		statusDefs,
		groupedStatusDefs,
		priorityDefs,
		priorityKey,
		isChatUnread,
		type FolderUser,
		type FolderStatus,
		type FolderPriority,
		type StatusEntry,
		type StatusDef,
		type CanEditChat,
		type FolderActivity,
		type WorkspacePage,
		type WorkspaceChat,
		statusKey
	} from '$lib/utils/folders';
	import { tagDot, type FolderTag } from '$lib/utils/tags';
	import ChatList from './ChatList.svelte';
	import FolderTitle from './FolderTitle.svelte';
	import FolderBoard from './FolderBoard.svelte';
	import FolderStatusesModal from './FolderStatusesModal.svelte';
	import {
		updateFolderById,
		getFolderNotes,
		getFolderTags,
		getFolderUsers,
		updateFolderChatStatus,
		updateFolderChatPriority
	} from '$lib/apis/folders';
	import StatusIcon from './FolderStatusIcon.svelte';
	import PriorityIcon from './FolderPriorityIcon.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import FolderAutomations from './FolderAutomations.svelte';
	import FolderNotes from './FolderNotes.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';
	import KnowledgeSelector from '$lib/components/workspace/Models/Knowledge/KnowledgeSelector.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import NotesIcon from '$lib/components/layout/Sidebar/icons/Notes.svelte';
	import { getFolderAutomations, type FolderAutomation } from '$lib/apis/automations';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import TagIcon from '$lib/components/icons/Tag.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { formatNumber } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let folder: FolderDetails | null = null;
	export let readOnly = false;
	/** Which part of the folder is showing: its files, chats, notes, automations or knowledge. */
	export let folderSection: FolderSection = 'chats';

	// The page is saved with the folder's tabs, so it opens exactly as it was left.
	$: folderView =
		folder?.id && $user?.id ? chatViewEntry($user.id, folderSessionId(folder.id, $user.id)) : null;
	// The tabs load it too; this covers the page showing first.
	$: if (folderView && !folderView.loaded) void loadChatView(folderView)?.catch(() => {});
	// Read again whenever a view changes; loading one does not reassign it.
	const isSettled = (view: typeof folderView, _changes: number) =>
		!!view && (view.loaded || !!view.error);
	$: folderViewSettled = isSettled(folderView, $chatViewChanges);
	let restoredFolderId: string | null = null;
	let filesDirectory: string | null = null;
	const saveFolderPage = () => {
		if (!folderView?.loaded || restoredFolderId !== folder?.id) return;
		const folderPage = { section: folderSection, directory: filesDirectory };
		const saved = folderView.state.folderPage;
		if (saved?.section === folderPage.section && (saved.directory ?? null) === folderPage.directory)
			return;
		changeChatView(folderView, { ...folderView.state, folderPage });
	};

	// A folder opened on a machine's directory shows that directory's files.
	$: filesTarget =
		!readOnly && folder?.id && $user?.id
			? resolveMachineTarget(
					machineIdOf(folder.data) ?? null,
					$machines ?? [],
					localStorage.token,
					{
						chatId: folderSessionId(folder.id, $user.id)
					}
				)
			: null;
	$: if (folderSection === 'files' && $machines && !filesTarget) folderSection = 'chats';

	let notes: any[] = [];
	let notesTotal = 0;
	let notesPage = 1;
	let notesLoading = false;
	let notesView: FolderNotes;

	$: canUseNotes =
		($config?.features?.enable_notes ?? false) &&
		($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true));
	$: if (!canUseNotes && folderSection === 'notes') folderSection = 'chats';

	// Refreshes keep every page already loaded.
	async function loadNotes(pages = notesPage) {
		const folderId = folder?.id;
		if (!folderId || !canUseNotes) return;
		const state = getFolderState(folderId);
		notesLoading = true;
		try {
			const results = await Promise.all(
				Array.from({ length: pages }, (_, index) =>
					getFolderNotes(localStorage.token, folderId, index + 1)
				)
			);
			state.notes = results[0];
			if (folder?.id !== folderId) return;
			notes = [
				...new Map(results.flatMap((page) => page.items).map((note) => [note.id, note])).values()
			];
			notesTotal = results[results.length - 1].total;
			notesPage = pages;
		} catch (error) {
			if (folder?.id === folderId) toast.error(`${error}`);
		} finally {
			notesLoading = false;
		}
	}

	async function loadMoreNotes() {
		if (!notesLoading) await loadNotes(notesPage + 1);
	}

	let automations: FolderAutomation[] = [];
	let automationsLoading = false;
	let automationsView: FolderAutomations;

	async function loadAutomations() {
		const folderId = folder?.id;
		if (!folderId || !canUseAutomations) return;
		const state = getFolderState(folderId);
		automationsLoading = true;
		try {
			const folderAutomations = await getFolderAutomations(localStorage.token, folderId);
			state.automations = folderAutomations;
			if (folder?.id === folderId) automations = folderAutomations;
		} catch (error) {
			if (folder?.id === folderId) automations = [];
		} finally {
			automationsLoading = false;
		}
	}

	$: canUseAutomations =
		$config?.features?.enable_automations &&
		($user?.role === 'admin' || $user?.permissions?.features?.automations);

	$: if (!canUseAutomations && folderSection === 'automations') folderSection = 'chats';

	let knowledgeView: FolderKnowledge;
	let knowledgeItems: any[] = [];
	let showKnowledgePicker = false;
	// Pending uploads count while the list is open; otherwise the folder's saved entries.
	$: knowledgeCount =
		folderSection === 'knowledge' ? knowledgeItems.length : (folder?.data?.files ?? []).length;
	$: canUploadKnowledge =
		$user?.role === 'admin' || ($user?.permissions?.chat?.file_upload ?? true);

	function showSection(section: FolderSection, save = true) {
		folderSection = section;
		if (section === 'notes') void loadNotes();
		if (section === 'automations') void loadAutomations();
		if (save) saveFolderPage();
	}
	export let onNewChat: () => void = () => {};

	async function newNote() {
		showSection('notes');
		await tick();
		await notesView?.startNew();
	}
	export let folderTabActions: import('svelte').Snippet | undefined = undefined;

	type GroupKey = string;
	type GroupBy = 'none' | 'status' | 'priority' | 'tags' | 'activity';
	type Group = {
		id: string;
		label: string;
		status?: FolderStatus;
		priority?: FolderPriority;
		dot?: string;
		spinner?: boolean;
	};
	// Like the 'none' status: tag id 'none' means untagged (tag names can't be 'none').
	const UNTAGGED = 'none';
	type Facet = 'status' | 'priority' | 'tags' | 'users' | 'activity' | 'updated';
	type SortKey = 'updated_at' | 'title' | 'priority';
	// The chat fields a drop or picker can set.
	type Field = 'status' | 'priority';

	const activityOptions = [
		['unread', 'Unread'],
		['generating', 'Generating'],
		['waiting_for_approval', 'Waiting for approval'],
		['idle', 'Read']
	] as const;
	const updatedOptions = [
		['today', 'Today'],
		['7d', 'Last 7 days'],
		['30d', 'Last 30 days']
	] as const;
	const facets: { id: Facet; label: string }[] = [
		{ id: 'status', label: 'Status' },
		{ id: 'priority', label: 'Priority' },
		{ id: 'tags', label: 'Tags' },
		{ id: 'users', label: 'Users' },
		{ id: 'activity', label: 'Activity' },
		{ id: 'updated', label: 'Updated' }
	];

	// Layout and ordering are personal preferences; filters stay per visit.
	const PREFS = 'folder-workspace-display';
	const prefs = (() => {
		try {
			return JSON.parse(localStorage.getItem(PREFS) ?? '{}') ?? {};
		} catch {
			return {};
		}
	})();
	let view: 'list' | 'board' = prefs.view === 'board' ? 'board' : 'list';
	const groupByPref = (value: unknown): GroupBy =>
		value === 'status' || value === 'priority' || value === 'tags' || value === 'activity'
			? value
			: 'none';
	// List grouping, board columns and board rows (swimlanes) are separate choices.
	let grouping: GroupBy = groupByPref(prefs.grouping);
	let columnsBy: Exclude<GroupBy, 'none'> =
		prefs.columnsBy === 'priority' || prefs.columnsBy === 'tags' || prefs.columnsBy === 'activity'
			? prefs.columnsBy
			: 'status';
	let rowsBy: GroupBy =
		groupByPref(prefs.rowsBy) === columnsBy ? 'none' : groupByPref(prefs.rowsBy);
	let sortBy: SortKey =
		prefs.sortBy === 'title' || prefs.sortBy === 'priority' ? prefs.sortBy : 'updated_at';
	let sortDir: 'asc' | 'desc' =
		prefs.sortDir === 'asc' || prefs.sortDir === 'desc'
			? prefs.sortDir
			: sortBy === 'title'
				? 'asc'
				: 'desc';
	let showEmptyGroups = prefs.showEmptyGroups === true;
	let showPriority = prefs.showPriority !== false;
	const savePrefs = () => {
		try {
			localStorage.setItem(
				PREFS,
				JSON.stringify({
					view,
					grouping,
					columnsBy,
					rowsBy,
					sortBy,
					sortDir,
					showEmptyGroups,
					showPriority
				})
			);
		} catch {
			/* Storage is optional. */
		}
	};

	// Folded groups are remembered per folder and grouping.
	const COLLAPSED = 'folder-workspace-collapsed';
	let collapsed: Record<string, Record<string, boolean>> = (() => {
		try {
			return JSON.parse(localStorage.getItem(COLLAPSED) ?? '{}') ?? {};
		} catch {
			return {};
		}
	})();
	const toggleCollapsed = (by: GroupBy, id: string) => {
		if (!folder?.id) return;
		const key = `${folder.id}:${by}`;
		const { [id]: folded, ...rest } = collapsed[key] ?? {};
		const next = folded ? rest : { ...rest, [id]: true };
		const { [key]: _, ...others } = collapsed;
		collapsed = Object.keys(next).length ? { ...others, [key]: next } : others;
		try {
			localStorage.setItem(COLLAPSED, JSON.stringify(collapsed));
		} catch {
			/* Storage is optional. */
		}
	};

	// Built-in plus folder-defined statuses, shared with rows, cards and menus.
	let defs: StatusDef[] = statusDefs(null, (key) => key);
	const defsStore = writable<StatusDef[]>(defs);
	const manageStore = writable<(() => void) | null>(null);
	setContext('folder-statuses', defsStore);
	setContext('folder-statuses-manage', manageStore);
	let showStatuses = false;
	$: defs = statusDefs(folder?.meta, (key) => $i18n.t(key));
	$: defsStore.set(defs);
	$: manageStore.set(readOnly ? null : () => (showStatuses = true));
	// Who may change a chat's tags, status and priority here (the server checks the same).
	const canEditStore = writable<CanEditChat>(() => false);
	setContext('folder-can-edit', canEditStore);
	$: canEditStore.set((chat) => !readOnly || chat.user_id === $user?.id);

	// The folder's emoji is picked here only; the tab just shows it.
	let iconSaving = false;
	let showEditFolder = false;
	async function saveIcon(icon: string | null) {
		if (!folder?.id || readOnly || iconSaving) return;
		const folderId = folder.id;
		iconSaving = true;
		try {
			const updated = await updateFolderById(localStorage.token, folderId, {
				meta: { icon: icon ?? '' }
			});
			if (!updated) return;
			updateFolderDetails(folderId, updated);
			selectedFolder.update((current) =>
				current?.id === folderId ? { ...current, ...updated } : current
			);
			await refreshFolderChatLists(null);
		} catch (error) {
			toast.error(String(error));
		} finally {
			iconSaving = false;
		}
	}

	// A reorder changes no chat, so it skips the reload.
	async function saveStatuses(statuses: StatusEntry[], reload = true) {
		if (!folder?.id) return;
		const folderId = folder.id;
		const updated = await updateFolderById(localStorage.token, folderId, {
			meta: { statuses }
		});
		if (!updated) return;
		updateFolderDetails(folderId, updated);
		selectedFolder.update((current) =>
			current?.id === folderId ? { ...current, ...updated } : current
		);
		if (!reload) return;
		const valid = new Set(statusDefs(updated.meta, (key) => key).map((item) => item.id));
		statusFilter = statusFilter.filter((id) => valid.has(id));
		markFolderChatsDirty(folderId);
		await tick();
		await load();
	}

	// Board columns dragged into a new order; statuses the filter hides keep their places.
	async function reorderStatuses(ids: string[]) {
		const order = groupedStatusDefs(folder?.meta, (key) => key);
		const moved = ids.filter((id) => order.some((item) => item.id === id));
		const byId = new Map(order.map((item) => [item.id, item]));
		let index = 0;
		const next = order.map((item) => (moved.includes(item.id) ? byId.get(moved[index++])! : item));
		try {
			await saveStatuses(
				next.map(({ id, name, glyph, color, icon }) =>
					id === NO_STATUS ? { id: NO_STATUS } : { id, name, glyph, color, icon }
				),
				false
			);
		} catch (error) {
			toast.error(String(error));
		}
	}

	let currentFolderId = '';
	let section: HTMLElement;
	let searchInput: HTMLInputElement;
	let searchOpen = false;

	let search = '';
	let appliedSearch = '';
	let statusFilter: FolderStatus[] = [];
	let priorityFilter: FolderPriority[] = [];
	let selectedTags: string[] = [];
	let selectedUsers: string[] = [];
	let folderUsers: FolderUser[] = [];
	let activity: FolderActivity | undefined = undefined;
	let updatedRange = '';
	let updatedAtGte: number | undefined = undefined;

	let groups: Partial<Record<GroupKey, WorkspacePage>> = {};
	let groupPages: Partial<Record<GroupKey, number>> = {};
	let options: FolderTag[] = [];
	let optionsError = '';
	let optionsReady = false;
	let loading = false;
	let loadingGroup = '';
	let saving = '';
	let error = '';
	let generation = 0;
	let optionsGeneration = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	let filterShow = false;
	let filterDropdown: Dropdown;
	let tagQuery = '';

	$: groupByLabel = (value: GroupBy) =>
		value === 'status'
			? $i18n.t('Status')
			: value === 'priority'
				? $i18n.t('Priority')
				: value === 'tags'
					? $i18n.t('Tags')
					: value === 'activity'
						? $i18n.t('Activity')
						: $i18n.t('None');
	const activeBy = (): GroupBy => (view === 'board' ? columnsBy : grouping);

	// The groups a view splits into, honouring the matching filter.
	// `_deps` only lets reactive callers re-run when filters, tags or statuses change.
	function groupsFor(
		by: GroupBy,
		t: (key: string) => string = (key) => key,
		_deps?: unknown
	): Group[] {
		if (by === 'status') {
			return groupedStatusDefs(folder?.meta, t)
				.filter((status) => !statusFilter.length || statusFilter.includes(status.id))
				.map((status) => ({ id: status.id, label: status.name, status: status.id }));
		}
		if (by === 'priority') {
			const defined = priorityDefs(t).filter(
				(priority) => !priorityFilter.length || priorityFilter.includes(priority.id)
			);
			// Urgent first; "No priority" last, like "No status".
			return [
				...defined.filter((priority) => priority.id !== NO_PRIORITY),
				...defined.filter((priority) => priority.id === NO_PRIORITY)
			].map((priority) => ({ id: priority.id, label: priority.name, priority: priority.id }));
		}
		if (by === 'tags') {
			const untaggedGroup = {
				id: UNTAGGED,
				label: t('Untagged'),
				dot: 'border border-dashed border-base-400 dark:border-base-500'
			};
			const picked = (id: string) => !selectedTags.length || selectedTags.includes(id);
			return [
				...options
					.filter((tag) => picked(tag.id))
					.slice(0, 40)
					.map((tag) => ({ id: tag.id, label: tag.name, dot: tagDot(tag) })),
				...(picked(UNTAGGED) ? [untaggedGroup] : [])
			];
		}
		if (by === 'activity') {
			// Same markers as the rows: approval, generating, unread, then everything else.
			const states: Group[] = [
				{ id: 'waiting_for_approval', label: t('Waiting for approval'), dot: 'bg-yellow-500' },
				{ id: 'generating', label: t('Generating'), spinner: true },
				{ id: 'unread', label: t('Unread'), dot: 'bg-sky-500' },
				{ id: 'idle', label: t('Read'), dot: 'border border-base-300 dark:border-base-600' }
			];
			return activity ? states.filter((state) => state.id === activity) : states;
		}
		return [{ id: 'all', label: '' }];
	}
	// Tag groups can overlap, so the total comes from one extra ungrouped query.
	const groupKeys = (): GroupKey[] => {
		const keys = groupsFor(activeBy()).map((group) => group.id);
		return activeBy() === 'tags' ? [...keys, 'all'] : keys;
	};

	$: by = view === 'board' ? columnsBy : grouping;
	$: currentGroups = groupsFor(by, (key) => $i18n.t(key), [
		statusFilter,
		priorityFilter,
		selectedTags,
		options,
		defs
	]);
	$: total =
		by === 'none' || by === 'tags'
			? (groups.all?.total ?? 0)
			: currentGroups.map((group) => groups[group.id]?.total ?? 0).reduce((sum, n) => sum + n, 0);
	$: hasData = Object.keys(groups).length > 0;
	$: filterCount =
		(statusFilter.length ? 1 : 0) +
		(priorityFilter.length ? 1 : 0) +
		(selectedTags.length ? 1 : 0) +
		(selectedUsers.length ? 1 : 0) +
		(activity ? 1 : 0) +
		(updatedRange ? 1 : 0);
	$: filtered = Boolean(appliedSearch || filterCount);
	$: listGroups =
		by === 'none'
			? [{ id: 'all', label: '', page: groups.all }]
			: currentGroups
					.map((group) => ({ ...group, page: groups[group.id] }))
					.filter((group) => showEmptyGroups || (group.page?.total ?? 0) > 0);
	$: boardColumns = currentGroups.map((group) => ({ ...group, page: groups[group.id] }));
	$: boardRows =
		rowsBy === 'none'
			? null
			: groupsFor(rowsBy, (key) => $i18n.t(key), [
					statusFilter,
					priorityFilter,
					selectedTags,
					options,
					defs
				]);
	const rowOf = (chat: WorkspaceChat) =>
		rowsBy === 'activity'
			? [
					chat.pending_approval
						? 'waiting_for_approval'
						: chat.active
							? 'generating'
							: chat.user_id === $user?.id && isChatUnread(chat)
								? 'unread'
								: 'idle'
				]
			: rowsBy === 'status'
				? [defs.some((status) => status.id === chat.status) ? statusKey(chat.status) : NO_STATUS]
				: rowsBy === 'priority'
					? [priorityKey(chat.priority)]
					: chat.tags?.length
						? chat.tags.map((tag) => tag.id)
						: [UNTAGGED];
	// What a drop into a board cell sets: its column's and its row's status or priority.
	const isField = (value: GroupBy): value is Field => value === 'status' || value === 'priority';
	const dropTargets = (column: string, row: string | null): [Field, string][] => [
		...(isField(columnsBy) ? [[columnsBy, column] as [Field, string]] : []),
		...(isField(rowsBy) && row != null ? [[rowsBy, row] as [Field, string]] : [])
	];

	type FilterOption = {
		facet: Facet;
		value: string;
		label: string;
		checked: boolean;
		status?: FolderStatus;
		priority?: FolderPriority;
		dot?: string;
		avatar?: string;
		count?: number;
	};
	let filterOptions: FilterOption[] = [];
	$: filterOptions = [
		...defs.map((status) => ({
			facet: 'status' as Facet,
			value: status.id as string,
			label: status.name,
			checked: statusFilter.includes(status.id),
			status: status.id as FolderStatus | undefined,
			dot: '',
			avatar: undefined as string | undefined,
			count: undefined as number | undefined
		})),
		...priorityDefs((key) => $i18n.t(key)).map((priority) => ({
			facet: 'priority' as Facet,
			value: priority.id as string,
			label: priority.name,
			checked: priorityFilter.includes(priority.id),
			status: undefined,
			priority: priority.id,
			dot: '',
			count: undefined
		})),
		{
			facet: 'tags' as Facet,
			value: UNTAGGED,
			label: $i18n.t('Untagged'),
			checked: selectedTags.includes(UNTAGGED),
			status: undefined,
			dot: 'border border-dashed border-base-400 dark:border-base-500',
			count: undefined
		},
		...options.map((tag) => ({
			facet: 'tags' as Facet,
			value: tag.id,
			label: tag.name,
			checked: selectedTags.includes(tag.id),
			status: undefined,
			dot: tagDot(tag),
			count: tag.count
		})),
		...folderUsers.map((entry) => ({
			facet: 'users' as Facet,
			value: entry.id,
			label: entry.name,
			checked: selectedUsers.includes(entry.id),
			status: undefined,
			dot: '',
			avatar: `${WEBUI_API_BASE_URL}/users/${entry.id}/profile/image`,
			count: entry.count as number | undefined
		})),
		...activityOptions.map(([value, label]) => ({
			facet: 'activity' as Facet,
			value: value as string,
			label: $i18n.t(label),
			checked: activity === value,
			status: undefined,
			dot: '',
			count: undefined
		})),
		...updatedOptions.map(([value, label]) => ({
			facet: 'updated' as Facet,
			value: value as string,
			label: $i18n.t(label),
			checked: updatedRange === value,
			status: undefined,
			dot: '',
			count: undefined
		}))
	];
	const facetOptions = (id: Facet, query = '') =>
		filterOptions.filter(
			(option) =>
				option.facet === id && option.label.toLowerCase().includes(query.trim().toLowerCase())
		);

	const facetCount = (id: Facet) =>
		id === 'status'
			? statusFilter.length
			: id === 'priority'
				? priorityFilter.length
				: id === 'tags'
					? selectedTags.length
					: id === 'users'
						? selectedUsers.length
						: id === 'activity'
							? Number(Boolean(activity))
							: Number(Boolean(updatedRange));

	function query(page: number, key: GroupKey) {
		return {
			page,
			sortBy,
			sortDir,
			workspace: true,
			search: appliedSearch,
			userIds: selectedUsers,
			tagIds: activeBy() === 'tags' && key !== 'all' ? [key] : selectedTags,
			activity: activeBy() === 'activity' && key !== 'all' ? (key as FolderActivity) : activity,
			updatedAtGte,
			status:
				activeBy() === 'status' && key !== 'all'
					? key
					: statusFilter.length
						? [...statusFilter].sort()
						: undefined,
			priority:
				activeBy() === 'priority' && key !== 'all'
					? (key as FolderPriority)
					: priorityFilter.length
						? [...priorityFilter].sort()
						: undefined
		};
	}

	const fetchPage = (id: string, page: number, key: GroupKey) =>
		loadFolderChatPage(
			localStorage.token,
			id,
			query(page, key),
			true
		) as unknown as Promise<WorkspacePage>;

	function merge(pages: WorkspacePage[]): WorkspacePage {
		const last = pages[pages.length - 1];
		const unique = new Map(pages.flatMap((page) => page.chats).map((chat) => [chat.id, chat]));
		return { chats: [...unique.values()], total: last.total, has_more: last.has_more };
	}

	// The latest tag/user fetch, so tag-grouped loads can wait for whichever one is current.
	let optionsPromise: Promise<void> | null = null;
	function loadOptions() {
		optionsPromise = fetchOptions();
		return optionsPromise;
	}
	async function fetchOptions() {
		const id = folder?.id;
		if (!id) return;
		const state = getFolderState(id);
		const version = ++optionsGeneration;
		try {
			const [next, nextUsers] = await Promise.all([
				getFolderTags(localStorage.token, id),
				getFolderUsers(localStorage.token, id)
			]);
			if (version === optionsGeneration) {
				state.tags = next;
				state.users = nextUsers;
				options = next;
				folderUsers = nextUsers;
				optionsReady = true;
				optionsError = '';
			}
		} catch (failure) {
			if (version === optionsGeneration) optionsError = String(failure);
		}
	}

	// Refreshes keep every page already loaded so live updates never collapse the list.
	async function load(reset = false) {
		if (!folder?.id) return;
		const id = folder.id;
		const version = ++generation;
		// Tag columns are built from the folder's tags, so wait for the newest tag fetch.
		let awaited: Promise<void> | null = null;
		while (activeBy() === 'tags' && !optionsReady && awaited !== optionsPromise) {
			awaited = optionsPromise ?? loadOptions();
			await awaited;
		}
		if (version !== generation) return;
		const keys = groupKeys();
		const depth = reset ? {} : groupPages;
		if (reset) {
			// What was shown before stays until it is refreshed.
			const { chatPages } = getFolderState(id);
			groups = Object.fromEntries(
				keys.flatMap((key) => {
					const page = chatPages[folderChatPageKey(query(1, key))];
					return page ? [[key, page]] : [];
				})
			) as unknown as typeof groups;
			groupPages = {};
		}
		loading = true;
		error = '';
		loadingGroup = '';
		try {
			const next = await Promise.all(
				keys.map(async (key) => {
					const pages = depth[key] ?? 1;
					const results = await Promise.all(
						Array.from({ length: pages }, (_, index) => fetchPage(id, index + 1, key))
					);
					return [key, merge(results)] as const;
				})
			);
			if (version !== generation) return;
			groups = Object.fromEntries(next) as typeof groups;
			groupPages = Object.fromEntries(
				next.map(([key, page]) => [
					key,
					Math.max(1, Math.min(depth[key] ?? 1, Math.ceil(page.total / FOLDER_PAGE_SIZE)))
				])
			) as typeof groupPages;
		} catch (failure) {
			if (version === generation && !isCancelledFolderRequest(failure)) error = String(failure);
		} finally {
			if (version === generation) loading = false;
		}
	}

	async function loadMore(key: string) {
		const group = key as GroupKey;
		if (!folder?.id || loadingGroup || loading || !groups[group]?.has_more) return;
		const version = generation;
		loadingGroup = group;
		const nextPage = (groupPages[group] ?? 1) + 1;
		try {
			const next = await fetchPage(folder.id, nextPage, group);
			if (version !== generation) return;
			groups = { ...groups, [group]: merge([groups[group]!, next]) };
			groupPages = { ...groupPages, [group]: nextPage };
		} catch (failure) {
			if (version === generation) toast.error(String(failure));
		} finally {
			if (version === generation) loadingGroup = '';
		}
	}

	function apply() {
		clearTimeout(timer);
		appliedSearch = search.trim();
		void load(true);
	}

	function searchChanged() {
		++generation;
		clearTimeout(timer);
		timer = setTimeout(apply, 250);
	}

	function setView(next: 'list' | 'board') {
		if (view === next) return;
		view = next;
		savePrefs();
		apply();
	}

	function setGrouping(next: GroupBy) {
		if (grouping === next) return;
		grouping = next;
		savePrefs();
		apply();
	}

	function setColumns(next: Exclude<GroupBy, 'none'>) {
		if (columnsBy === next) return;
		columnsBy = next;
		if (rowsBy === next) rowsBy = 'none';
		savePrefs();
		apply();
	}

	function setRows(next: GroupBy) {
		if (rowsBy === next || next === columnsBy) return;
		rowsBy = next;
		savePrefs();
		if (next === 'tags' && !optionsReady) void loadOptions();
	}

	function setSort(key: SortKey, dir?: 'asc' | 'desc') {
		const nextDir = dir ?? (key === sortBy ? sortDir : key === 'title' ? 'asc' : 'desc');
		if (key === sortBy && nextDir === sortDir) return;
		sortBy = key;
		sortDir = nextDir;
		savePrefs();
		apply();
	}

	function toggleTag(id: string) {
		selectedTags = selectedTags.includes(id)
			? selectedTags.filter((tag) => tag !== id)
			: [...selectedTags, id];
		apply();
	}

	function selectUpdated(value: string) {
		updatedRange = updatedRange === value ? '' : value;
		const now = new Date();
		updatedAtGte = !updatedRange
			? undefined
			: Math.floor(
					(updatedRange === 'today'
						? new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
						: now.getTime() - (updatedRange === '7d' ? 7 : 30) * 86400000) / 1000
				);
		apply();
	}

	function toggleOption(option: (typeof filterOptions)[number]) {
		if (option.facet === 'status') {
			const status = option.value as FolderStatus;
			statusFilter = statusFilter.includes(status)
				? statusFilter.filter((item) => item !== status)
				: [...statusFilter, status];
			apply();
		} else if (option.facet === 'priority') {
			const priority = option.value as FolderPriority;
			priorityFilter = priorityFilter.includes(priority)
				? priorityFilter.filter((item) => item !== priority)
				: [...priorityFilter, priority];
			apply();
		} else if (option.facet === 'tags') {
			toggleTag(option.value);
		} else if (option.facet === 'users') {
			selectedUsers = selectedUsers.includes(option.value)
				? selectedUsers.filter((id) => id !== option.value)
				: [...selectedUsers, option.value];
			apply();
		} else if (option.facet === 'activity') {
			activity = activity === option.value ? undefined : (option.value as FolderActivity);
			apply();
		} else selectUpdated(option.value);
	}

	function clearFacet(id: Facet) {
		if (id === 'status') statusFilter = [];
		else if (id === 'priority') priorityFilter = [];
		else if (id === 'tags') {
			selectedTags = [];
		} else if (id === 'users') selectedUsers = [];
		else if (id === 'activity') activity = undefined;
		else {
			updatedRange = '';
			updatedAtGte = undefined;
		}
		apply();
	}

	function clear() {
		search = '';
		statusFilter = [];
		priorityFilter = [];
		selectedTags = [];
		selectedUsers = [];
		activity = undefined;
		updatedRange = '';
		updatedAtGte = undefined;
		apply();
	}

	function openFilter() {
		tagQuery = '';
		filterShow = true;
	}

	function openFilterFromKeyboard() {
		tagQuery = '';
		if (filterDropdown) filterDropdown.openWithFocus();
		else filterShow = true;
	}

	async function openSearch() {
		searchOpen = true;
		await tick();
		searchInput?.focus();
	}

	async function changed() {
		markFolderChatsDirty();
		await loadOptions();
		await load();
	}

	const valueOf = (chat: WorkspaceChat, field: Field): string =>
		field === 'status' ? statusKey(chat.status) : priorityKey(chat.priority);

	// Status and priority changes land instantly; the server refresh reconciles counts and filters.
	// Each change is a group key: 'none' (NO_STATUS, NO_PRIORITY) clears the field (null).
	async function update(chat: WorkspaceChat, changes: [Field, string][]) {
		changes = changes.filter(([field, key]) => valueOf(chat, field) !== key);
		if (!folder?.id || saving || !$canEditStore(chat) || !changes.length) return;
		const folderId = folder.id;
		let moved = chat;
		for (const [field, key] of changes) {
			if (field === 'status') {
				const value = key === NO_STATUS ? null : key;
				// Earlier time in the target status comes back with the refresh below.
				const now = value ? Math.floor(Date.now() / 1000) : null;
				moved = { ...moved, status: value, status_since: now, status_entered_at: now };
			} else {
				moved = {
					...moved,
					priority: key === NO_PRIORITY ? null : (key as WorkspaceChat['priority'])
				};
			}
		}
		saving = chat.id;
		const regrouped = changes.find(([field]) => field === activeBy());
		if (regrouped) {
			const from = valueOf(chat, regrouped[0]);
			const to = regrouped[1];
			const source = groups[from];
			const target = groups[to];
			groups = {
				...groups,
				...(source && {
					[from]: {
						...source,
						chats: source.chats.filter((item) => item.id !== chat.id),
						total: Math.max(0, source.total - 1)
					}
				}),
				...(target && {
					[to]: {
						...target,
						chats: [moved, ...target.chats.filter((item) => item.id !== chat.id)],
						total: target.total + 1
					}
				})
			};
		} else {
			groups = Object.fromEntries(
				Object.entries(groups).flatMap(([key, page]) =>
					page
						? [
								[
									key,
									{ ...page, chats: page.chats.map((item) => (item.id === chat.id ? moved : item)) }
								]
							]
						: []
				)
			) as typeof groups;
		}
		try {
			for (const [field, key] of changes) {
				const value = key === 'none' ? null : key;
				if (field === 'status')
					await updateFolderChatStatus(localStorage.token, folderId, chat.id, value);
				else await updateFolderChatPriority(localStorage.token, folderId, chat.id, value);
			}
			markFolderChatsDirty(folderId);
		} catch (failure) {
			toast.error(String(failure));
		} finally {
			saving = '';
		}
		if (folder?.id === folderId) await load();
	}
	const move = (chat: WorkspaceChat, status: FolderStatus) => update(chat, [['status', status]]);
	const prioritize = (chat: WorkspaceChat, priority: FolderPriority) =>
		update(chat, [['priority', priority]]);

	// Linear-style single-key shortcuts while the workspace is on screen.
	function shortcuts(event: KeyboardEvent) {
		if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
		if (!section?.offsetParent) return;
		const target = event.target as HTMLElement | null;
		if (
			target?.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"]') ||
			document.querySelector('[aria-modal="true"]')
		)
			return;
		if (folderSection !== 'chats' && (event.key === '/' || event.key === 'f')) return;
		if (event.key === '/') {
			event.preventDefault();
			void openSearch();
		} else if (event.key === 'f') {
			event.preventDefault();
			openFilterFromKeyboard();
		} else if (event.key === 'c' && !readOnly) {
			event.preventDefault();
			onNewChat();
		}
	}

	onMount(() => {
		const unregister = registerFolderRefreshHandler((id) => {
			if (id == null || id === folder?.id) return Promise.all([load(), loadNotes()]);
		});
		const connection = $socket;
		const events = (event: {
			chat_id?: string;
			data?: { type?: string; data?: { active?: boolean; pending_approval?: boolean } };
		}) => {
			if (event.data?.type === 'chat:active') {
				const patch = (chat: WorkspaceChat) =>
					chat.id === event.chat_id
						? {
								...chat,
								active: event.data?.data?.active ?? false,
								pending_approval: event.data?.data?.pending_approval ?? false
							}
						: chat;
				groups = Object.fromEntries(
					Object.entries(groups).flatMap(([key, page]) =>
						page ? [[key, { ...page, chats: page.chats.map(patch) }]] : []
					)
				) as typeof groups;
				// Server-side activity groups and filters need a refetch; swimlanes re-sort on their own.
				if (activity || activeBy() === 'activity') {
					markFolderChatsDirty(folder?.id);
					void load();
				}
			} else if (event.data?.type === 'chat:list') void changed();
		};
		const reconnect = () => {
			void changed();
		};
		connection?.on('events', events);
		connection?.on('connect', reconnect);
		return () => {
			++generation;
			++optionsGeneration;
			clearTimeout(timer);
			unregister();
			connection?.off('events', events);
			connection?.off('connect', reconnect);
		};
	});

	$: if (folder?.id && folder.id !== currentFolderId) {
		currentFolderId = folder.id;
		// What was shown before stays until it is refreshed.
		const state = getFolderState(folder.id);
		search = '';
		appliedSearch = '';
		searchOpen = false;
		statusFilter = [];
		priorityFilter = [];
		selectedTags = [];
		selectedUsers = [];
		folderUsers = state.users ?? [];
		activity = undefined;
		updatedRange = '';
		updatedAtGte = undefined;
		options = state.tags ?? [];
		optionsReady = !!state.tags;
		optionsError = '';
		clearTimeout(timer);
		// Only someone who can reach the folder's machine lands on its files.
		folderSection = filesTarget ? 'files' : 'chats';
		automations = state.automations ?? [];
		notes = state.notes?.items ?? [];
		notesTotal = state.notes?.total ?? 0;
		void loadOptions();
		void load(true);
		void loadNotes(1);
		void loadAutomations();
	}

	// After the reset above, so the page left last wins once the folder's view is in.
	$: if (folderViewSettled && folder?.id && restoredFolderId !== folder.id) {
		restoredFolderId = folder.id;
		const saved = folderView?.state.folderPage;
		filesDirectory = saved?.directory ?? null;
		if (saved) showSection(saved.section, false);
	}

	// Backstop: tag groups that appear later (e.g. a tag created while open) get their chats.
	$: if (
		by === 'tags' &&
		hasData &&
		!loading &&
		!error &&
		currentGroups.some((group) => !groups[group.id])
	)
		void load();

	// Same row and panel styles as the submenus in ModelControls.
	const subRow =
		'flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] outline-hidden';
	// Same as ChatMenu's submenus: DropdownSub sizes them to the parent menu, so no width here.
	const subMenu = 'select-none z-50 max-h-80 overflow-y-auto';
	const iconButton =
		'relative flex size-6.5 shrink-0 items-center justify-center rounded-full border border-base-100 bg-base-50/60 text-base-500 transition-colors hover:bg-base-100 hover:text-base-900 aria-expanded:bg-base-100 aria-expanded:text-base-900 dark:border-base-850 dark:bg-base-850/50 dark:text-base-400 dark:hover:bg-base-850 dark:hover:text-base-0 dark:aria-expanded:bg-base-850 dark:aria-expanded:text-base-0';
</script>

<svelte:window on:keydown={shortcuts} />

{#snippet facetIcon(id: Facet)}
	{#if id === 'status'}
		<StatusIcon glyph="backlog" className="size-3.5 text-current!" />
	{:else if id === 'priority'}
		<PriorityIcon priority="high" />
	{:else if id === 'tags'}
		<TagIcon className="size-3.5" strokeWidth="1.5" />
	{:else if id === 'users'}
		<Icon name="user" size={14} />
	{:else if id === 'activity'}
		<Icon name="chat-bubble" size={14} />
	{:else}
		<Icon name="clock" size={14} />
	{/if}
{/snippet}

{#snippet groupMenu(
	label: string,
	value: GroupBy,
	choices: readonly GroupBy[],
	onSelect: (value: GroupBy) => void
)}
	<DropdownSub contentClass={subMenu} maxWidth={320} sideOffset={6}>
		<button slot="trigger" type="button" class={subRow}>
			<span class="min-w-0 flex-1 truncate text-left">{label}</span>
			<span class="truncate text-base-500 dark:text-base-400">{groupByLabel(value)}</span>
			<ChevronRight className="size-3.5 shrink-0 text-base-400 rtl:rotate-180" />
		</button>
		{#each choices as choice (choice)}
			<button
				type="button"
				role="menuitemradio"
				aria-checked={value === choice}
				on:click={() => onSelect(choice)}
			>
				<span class="flex-1 text-left">{groupByLabel(choice)}</span>
				{#if value === choice}<Check className="size-3! shrink-0" />{/if}
			</button>
		{/each}
	</DropdownSub>
{/snippet}

{#snippet folderIcon()}
	{#if folder?.meta?.icon}
		<Emoji shortCode={folder.meta.icon} className="size-4 shrink-0" />
	{:else}
		<Icon name="folder" size={14} class="shrink-0 text-base-500 dark:text-base-400" />
	{/if}
{/snippet}

{#snippet chip(
	id: Facet,
	values: {
		label: string;
		dot?: string;
		status?: FolderStatus;
		priority?: FolderPriority;
		avatar?: string;
	}[]
)}
	<div
		class="inline-flex h-6 max-w-full items-center overflow-hidden rounded-full border border-base-100 bg-base-50/60 text-xs dark:border-base-850 dark:bg-base-850/50"
	>
		<span class="flex h-full items-center gap-1.5 pl-2 pr-1.5 text-base-500 dark:text-base-400">
			{@render facetIcon(id)}{$i18n.t(facets.find((item) => item.id === id)?.label ?? '')}
		</span>
		<span class="flex h-full items-center px-1 text-base-400 dark:text-base-500">
			{values.length > 1 ? $i18n.t('is any of') : $i18n.t('is')}
		</span>
		<button
			type="button"
			class="flex h-full min-w-0 items-center gap-1.5 px-1.5 text-base-700 transition-colors hover:bg-base-100 dark:text-base-200 dark:hover:bg-base-800"
			on:click={openFilter}
		>
			{#each values.slice(0, 3) as item}
				{#if item.status}<StatusIcon
						status={item.status}
						className="size-3"
					/>{:else if item.priority}<PriorityIcon
						priority={item.priority}
						className="size-3"
					/>{:else if item.avatar}<img
						src={item.avatar}
						alt=""
						class="size-3.5 shrink-0 rounded-full object-cover"
					/>{:else if item.dot}<span class="size-1.5 shrink-0 rounded-full {item.dot}"></span>{/if}
			{/each}
			<span class="truncate"
				>{values.length > 2
					? $i18n.t('{{count}} selected', { count: values.length })
					: values.map((item) => item.label).join(', ')}</span
			>
		</button>
		<button
			type="button"
			class="flex h-full w-6 shrink-0 items-center justify-center border-l border-base-100 text-base-400 transition-colors hover:bg-base-100 hover:text-base-700 dark:border-base-850 dark:hover:bg-base-800 dark:hover:text-base-200"
			aria-label={$i18n.t('Remove filter')}
			on:click={() => clearFacet(id)}><XMark className="size-3" /></button
		>
	</div>
{/snippet}

<section
	bind:this={section}
	class="folder-workspace flex h-full min-h-0 min-w-0 w-full flex-col text-left text-base-600 @container dark:text-base-300"
	aria-label={$i18n.t('Folder')}
	aria-busy={loading}
>
	<FolderTitle
		bind:showFolderModal={showEditFolder}
		{folder}
		{readOnly}
		{onNewChat}
		onNewNote={canUseNotes ? newNote : null}
		bind:folderTabActions
		onUpdate={async () => {
			await Promise.all([refreshChatList(localStorage.token), refreshFolderChatLists(null)]);
		}}
		onDelete={async (deletedFolder: { id: string }) => {
			await Promise.all([refreshChatList(localStorage.token), refreshFolderChatLists(null)]);
			if ($selectedFolder?.id === deletedFolder.id) selectedFolder.set(null);
		}}
	/>

	<div class="flex shrink-0 items-center gap-1 px-1.5 pb-1 md:px-2.5">
		<h2
			class="flex h-6.5 min-w-0 items-center gap-1 px-1 text-sm text-base-900 select-none dark:text-base-100"
			aria-live="polite"
		>
			<!-- Folder first, like a breadcrumb, then the Workspace-tab style title + count. -->
			<span class="flex min-w-0 items-center gap-1.5">
				{#if readOnly}
					{@render folderIcon()}
				{:else}
					<EmojiPicker side="bottom" selected={folder?.meta?.icon || null} onSubmit={saveIcon}>
						<button
							type="button"
							class="flex size-5 shrink-0 items-center justify-center rounded-md transition-colors hover:bg-base-100 disabled:opacity-50 dark:hover:bg-base-850"
							aria-label={$i18n.t('Change folder icon')}
							title={$i18n.t('Change folder icon')}
							disabled={iconSaving}
						>
							{@render folderIcon()}
						</button>
					</EmojiPicker>
				{/if}
				{#if readOnly}
					<span class="truncate" title={folder?.name}>{folder?.name}</span>
				{:else}
					<button
						type="button"
						class="min-w-0 truncate rounded text-left transition-colors hover:text-base-600 dark:hover:text-base-300"
						title={$i18n.t('Edit Folder')}
						on:click={() => (showEditFolder = true)}>{folder?.name}</button
					>
				{/if}
			</span>
			<ChevronRight
				className="mx-0.5 size-3 shrink-0 text-base-400 rtl:rotate-180 dark:text-base-500"
				strokeWidth="2"
			/>
			<Dropdown align="start" closeOnSelect>
				<button
					type="button"
					class="-mx-1 flex shrink-0 items-center gap-1 rounded-md px-1 transition-colors hover:bg-base-100 dark:hover:bg-base-850"
					aria-label={$i18n.t('Switch section')}
				>
					{#if folderSection === 'files'}
						<span>{$i18n.t('Files')}</span>
					{:else if folderSection === 'notes'}
						<span>{$i18n.t('Notes')}</span>
						{#if notesTotal}<span class="text-sm opacity-60">{formatNumber(notesTotal)}</span>{/if}
					{:else if folderSection === 'automations'}
						<span>{$i18n.t('Automations')}</span>
						{#if automations.length}<span class="text-sm opacity-60">{automations.length}</span
							>{/if}
					{:else if folderSection === 'knowledge'}
						<span>{$i18n.t('Knowledge')}</span>
						{#if knowledgeCount}<span class="text-sm opacity-60">{knowledgeCount}</span>{/if}
					{:else}
						<span>{$i18n.t('Chats')}</span>
						{#if loading && hasData}
							<Spinner className="size-3 opacity-60" />
						{:else if hasData && !error}
							<span class="text-sm opacity-60">{formatNumber(total)}</span>
						{/if}
					{/if}
					<ChevronDown className="size-2.5 text-base-400 dark:text-base-500" strokeWidth="2.5" />
				</button>
				<DropdownMenu slot="content" className="w-44">
					{#if filesTarget}
						<button
							type="button"
							role="menuitemradio"
							aria-checked={folderSection === 'files'}
							on:click={() => showSection('files')}
						>
							<Icon name="folder" size={14} />
							<span class="flex-1 text-left">{$i18n.t('Files')}</span>
							{#if folderSection === 'files'}<Check className="size-3! shrink-0" />{/if}
						</button>
					{/if}
					<button
						type="button"
						role="menuitemradio"
						aria-checked={folderSection === 'chats'}
						on:click={() => showSection('chats')}
					>
						<Icon name="chat-bubble" size={14} />
						<span class="flex-1 text-left">{$i18n.t('Chats')}</span>
						{#if hasData}<span class="text-xs tabular-nums text-base-400"
								>{formatNumber(total)}</span
							>{/if}
						{#if folderSection === 'chats'}<Check className="size-3! shrink-0" />{/if}
					</button>
					{#if canUseNotes}
						<button
							type="button"
							role="menuitemradio"
							aria-checked={folderSection === 'notes'}
							on:click={() => showSection('notes')}
						>
							<NotesIcon className="size-3.5" strokeWidth="1.5" />
							<span class="flex-1 text-left">{$i18n.t('Notes')}</span>
							{#if notesTotal}<span class="text-xs tabular-nums text-base-400"
									>{formatNumber(notesTotal)}</span
								>{/if}
							{#if folderSection === 'notes'}<Check className="size-3! shrink-0" />{/if}
						</button>
					{/if}
					{#if canUseAutomations}
						<button
							type="button"
							role="menuitemradio"
							aria-checked={folderSection === 'automations'}
							on:click={() => showSection('automations')}
						>
							<Icon name="clock" size={14} />
							<span class="flex-1 text-left">{$i18n.t('Automations')}</span>
							{#if automations.length}<span class="text-xs tabular-nums text-base-400"
									>{automations.length}</span
								>{/if}
							{#if folderSection === 'automations'}<Check className="size-3! shrink-0" />{/if}
						</button>
					{/if}
					<button
						type="button"
						role="menuitemradio"
						aria-checked={folderSection === 'knowledge'}
						on:click={() => showSection('knowledge')}
					>
						<Database className="size-3.5" />
						<span class="flex-1 text-left">{$i18n.t('Knowledge')}</span>
						{#if knowledgeCount}<span class="text-xs tabular-nums text-base-400"
								>{knowledgeCount}</span
							>{/if}
						{#if folderSection === 'knowledge'}<Check className="size-3! shrink-0" />{/if}
					</button>
				</DropdownMenu>
			</Dropdown>
		</h2>

		<div class="ml-auto flex items-center gap-1">
			{#if folderSection === 'files'}
				<!-- The file browser keeps its own toolbar. -->
			{:else if folderSection === 'notes'}
				{#if !readOnly}
					<button
						type="button"
						class={iconButton}
						aria-label={$i18n.t('New Note')}
						title={$i18n.t('New Note')}
						on:click={() => notesView?.startNew()}
						><Plus className="size-3.5" strokeWidth="2" /></button
					>
				{/if}
			{:else if folderSection === 'automations'}
				{#if !readOnly}
					<button
						type="button"
						class={iconButton}
						aria-label={$i18n.t('New automation')}
						title={$i18n.t('New automation')}
						on:click={() => automationsView?.startNew()}
						><Plus className="size-3.5" strokeWidth="2" /></button
					>
				{/if}
			{:else if folderSection === 'knowledge'}
				{#if !readOnly}
					<KnowledgeSelector
						bind:show={showKnowledgePicker}
						align="end"
						selectedItems={knowledgeItems}
						on:select={(event) => knowledgeView?.add(event.detail)}
					>
						<button
							type="button"
							class={iconButton}
							aria-label={$i18n.t('Add knowledge')}
							title={$i18n.t('Add knowledge')}><Plus className="size-3.5" strokeWidth="2" /></button
						>
						<svelte:fragment slot="actions">
							{#if canUploadKnowledge}
								<button
									type="button"
									class="hover:text-base-900 dark:hover:text-base-100"
									on:click={() => {
										showKnowledgePicker = false;
										knowledgeView?.upload();
									}}>{$i18n.t('Upload Files')}</button
								>
							{/if}
							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
								<a
									href="/workspace/knowledge"
									target="_blank"
									rel="noreferrer"
									class="ml-auto hover:text-base-900 dark:hover:text-base-100"
									>{$i18n.t('Manage')}</a
								>
							{/if}
						</svelte:fragment>
					</KnowledgeSelector>
				{/if}
			{:else}
				{#if searchOpen || search}
					<div
						class="flex h-6.5 w-40 items-center gap-1.5 rounded-full border border-base-100 bg-base-50/60 px-2 text-base-400 @lg:w-52 dark:border-base-850 dark:bg-base-850/50 dark:text-base-500"
					>
						<Icon name="search" size={13} />
						<input
							bind:this={searchInput}
							class="min-w-0 flex-1 bg-transparent text-[0.8125rem] text-base-800 outline-none placeholder:text-base-400 dark:text-base-100 dark:placeholder:text-base-500"
							aria-label={$i18n.t('Search this folder')}
							title={$i18n.t('Search conversation titles and messages')}
							placeholder={$i18n.t('Search…')}
							maxlength="256"
							bind:value={search}
							on:input={searchChanged}
							on:blur={() => {
								if (!search) searchOpen = false;
							}}
							on:keydown={(event) => {
								if (event.key === 'Enter') apply();
								if (event.key === 'Escape') {
									search = '';
									apply();
									searchOpen = false;
									searchInput.blur();
								}
							}}
						/>
						{#if search}
							<button
								type="button"
								class="flex size-4 shrink-0 items-center justify-center rounded-full hover:text-base-700 dark:hover:text-base-200"
								aria-label={$i18n.t('Clear search')}
								on:mousedown|preventDefault
								on:click={() => {
									search = '';
									apply();
									searchInput?.focus();
								}}><XMark className="size-3" /></button
							>
						{/if}
					</div>
				{:else}
					<button
						type="button"
						class={iconButton}
						aria-label={$i18n.t('Search')}
						title={`${$i18n.t('Search')}  /`}
						on:click={openSearch}><Icon name="search" size={14} /></button
					>
				{/if}

				<Dropdown
					bind:this={filterDropdown}
					bind:show={filterShow}
					align="end"
					onOpenChange={() => (tagQuery = '')}
				>
					<button
						type="button"
						class="{iconButton} {filterCount ? 'text-base-800 dark:text-base-100' : ''}"
						aria-label={$i18n.t('Filter')}
						title={`${$i18n.t('Filter')}  F`}
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
					</button>

					<DropdownMenu slot="content" className="w-48">
						{#each facets as item (item.id)}
							<DropdownSub
								contentClass={subMenu}
								maxWidth={item.id === 'users' ? 224 : 320}
								sideOffset={6}
							>
								<button slot="trigger" type="button" class={subRow}>
									<span class="text-base-500 dark:text-base-400">{@render facetIcon(item.id)}</span>
									<span class="min-w-0 flex-1 truncate text-left">{$i18n.t(item.label)}</span>
									{#if facetCount(item.id)}<span class="text-xs tabular-nums text-base-400"
											>{facetCount(item.id)}</span
										>{/if}
									<ChevronRight className="size-3.5 shrink-0 text-base-400 rtl:rotate-180" />
								</button>

								{#if (item.id === 'tags' && options.length > 8) || (item.id === 'users' && folderUsers.length > 8)}
									<div class="flex h-[1.6875rem] items-center gap-2 px-2">
										<Icon
											name="search"
											size={12}
											class="shrink-0 text-base-400 dark:text-base-500"
										/>
										<input
											class="min-w-0 flex-1 bg-transparent text-[0.8125rem] outline-none placeholder:text-base-400 dark:placeholder:text-base-500"
											aria-label={item.id === 'users'
												? $i18n.t('Find users')
												: $i18n.t('Find tags')}
											placeholder={item.id === 'users'
												? $i18n.t('Find users…')
												: $i18n.t('Find tags…')}
											bind:value={tagQuery}
										/>
									</div>
								{/if}
								{#if optionsError && item.id === 'tags'}
									<button type="button" class="text-red-500" on:click={loadOptions}
										>{$i18n.t('Could not load tags. Retry')}</button
									>
								{/if}
								{#each facetOptions(item.id, item.id === 'tags' || item.id === 'users' ? tagQuery : '') as option (`${option.facet}:${option.value}`)}
									<button
										type="button"
										role={item.id === 'status' ||
										item.id === 'priority' ||
										item.id === 'tags' ||
										item.id === 'users'
											? 'menuitemcheckbox'
											: 'menuitemradio'}
										aria-checked={option.checked}
										on:click={() => toggleOption(option)}
									>
										{#if option.status}
											<StatusIcon status={option.status} />
										{:else if option.priority}
											<PriorityIcon priority={option.priority} />
										{:else if option.avatar}
											<img
												src={option.avatar}
												alt=""
												class="size-3.5 shrink-0 rounded-full object-cover"
											/>
										{:else if item.id === 'tags'}
											<span class="flex size-3.5 shrink-0 items-center justify-center"
												><span class="size-2 rounded-full {option.dot}"></span></span
											>
										{/if}
										<span class="min-w-0 flex-1 truncate text-left" title={option.label}
											>{option.label}</span
										>
										{#if option.count != null}<span
												class="shrink-0 text-xs tabular-nums text-base-400">{option.count}</span
											>{/if}
										{#if option.checked}<Check className="size-3! shrink-0" />{/if}
									</button>
								{:else}
									<div class="px-2 py-1.5 text-xs text-base-400 dark:text-base-500">
										{$i18n.t('No results')}
									</div>
								{/each}
							</DropdownSub>
						{/each}
						{#if filterCount}
							<hr class="border-base-50/30 dark:border-base-800/30" />
							<button type="button" on:click={clear}>
								<XMark className="size-3.5" />{$i18n.t('Clear filters')}
							</button>
						{/if}
					</DropdownMenu>
				</Dropdown>

				<Dropdown align="end">
					<button
						type="button"
						class={iconButton}
						aria-label={$i18n.t('Display options')}
						title={$i18n.t('Display options')}
					>
						<AdjustmentsHorizontal className="size-3.75" />
					</button>

					<DropdownMenu slot="content" className="w-52">
						<div class="px-2 pt-1.5 pb-0.5 text-xs text-base-400 dark:text-base-500">
							{$i18n.t('Layout')}
						</div>
						{#each [['list', 'List', 'list'], ['board', 'Board', 'grid']] as const as [value, label, icon]}
							<button
								type="button"
								role="menuitemradio"
								aria-checked={view === value}
								on:click={() => setView(value)}
							>
								<Icon name={icon} size={14} />
								<span class="flex-1 text-left">{$i18n.t(label)}</span>
								{#if view === value}<Check className="size-3! shrink-0" />{/if}
							</button>
						{/each}

						<hr class="border-base-50/30 dark:border-base-800/30" />

						{#if view === 'list'}
							{@render groupMenu(
								$i18n.t('Grouping'),
								grouping,
								['none', 'status', 'priority', 'tags', 'activity'],
								(value) => setGrouping(value)
							)}
						{:else}
							{@render groupMenu(
								$i18n.t('Columns'),
								columnsBy,
								['status', 'priority', 'tags', 'activity'],
								(value) => setColumns(value as Exclude<GroupBy, 'none'>)
							)}
							{@render groupMenu(
								$i18n.t('Rows'),
								rowsBy,
								(['none', 'status', 'priority', 'tags', 'activity'] as const).filter(
									(value) => value !== columnsBy
								),
								(value) => setRows(value)
							)}
						{/if}

						<DropdownSub contentClass={subMenu} maxWidth={320} sideOffset={6}>
							<button slot="trigger" type="button" class={subRow}>
								<span class="min-w-0 flex-1 truncate text-left">{$i18n.t('Ordering')}</span>
								<span class="truncate text-base-500 dark:text-base-400"
									>{sortBy === 'title'
										? $i18n.t('Title')
										: sortBy === 'priority'
											? $i18n.t('Priority')
											: $i18n.t('Updated')}</span
								>
								<ChevronRight className="size-3.5 shrink-0 text-base-400 rtl:rotate-180" />
							</button>
							{#each [['updated_at', 'Updated'], ['title', 'Title'], ['priority', 'Priority']] as const as [value, label]}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={sortBy === value}
									on:click={() => setSort(value)}
								>
									<span class="flex-1 text-left">{$i18n.t(label)}</span>
									{#if sortBy === value}<Check className="size-3! shrink-0" />{/if}
								</button>
							{/each}
							<hr class="border-base-50/30 dark:border-base-800/30" />
							{#each [['asc', 'Ascending'], ['desc', 'Descending']] as const as [value, label]}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={sortDir === value}
									on:click={() => setSort(sortBy, value)}
								>
									<span class="flex-1 text-left">{$i18n.t(label)}</span>
									{#if sortDir === value}<Check className="size-3! shrink-0" />{/if}
								</button>
							{/each}
						</DropdownSub>

						{#if view === 'list' && grouping !== 'none'}
							<button
								type="button"
								role="menuitemcheckbox"
								aria-checked={showEmptyGroups}
								on:click={() => {
									showEmptyGroups = !showEmptyGroups;
									savePrefs();
								}}
							>
								<span class="flex-1 text-left">{$i18n.t('Show empty groups')}</span>
								{#if showEmptyGroups}<Check className="size-3! shrink-0" />{/if}
							</button>
						{/if}
						<button
							type="button"
							role="menuitemcheckbox"
							aria-checked={showPriority}
							on:click={() => {
								showPriority = !showPriority;
								savePrefs();
							}}
						>
							<span class="flex-1 text-left">{$i18n.t('Show priority')}</span>
							{#if showPriority}<Check className="size-3! shrink-0" />{/if}
						</button>
					</DropdownMenu>
				</Dropdown>
			{/if}
		</div>
	</div>

	<!-- The folder's description sits under its name, above any filter chips. -->
	{#if folder?.data?.description?.trim()}
		<p
			class="shrink-0 px-2.5 pb-1.5 text-xs leading-5 whitespace-pre-line md:px-3.5 text-base-500 line-clamp-2 dark:text-base-400"
			title={folder.data.description}
		>
			{folder.data.description.trim()}
		</p>
	{/if}

	{#if filterCount && folderSection === 'chats'}
		<div class="flex shrink-0 flex-wrap items-center gap-1 px-2.5 pb-1.5 md:px-3.5">
			{#if statusFilter.length}
				{@render chip(
					'status',
					defs
						.filter((status) => statusFilter.includes(status.id))
						.map((status) => ({ label: status.name, status: status.id }))
				)}
			{/if}
			{#if priorityFilter.length}
				{@render chip(
					'priority',
					priorityDefs((key) => $i18n.t(key))
						.filter((priority) => priorityFilter.includes(priority.id))
						.map((priority) => ({ label: priority.name, priority: priority.id }))
				)}
			{/if}
			{#if selectedTags.length}
				{@render chip(
					'tags',
					selectedTags.map((id) => {
						if (id === UNTAGGED)
							return { label: $i18n.t('Untagged'), dot: 'border border-dashed border-base-400' };
						const tag = options.find((item) => item.id === id) ?? {
							id,
							name: id.replaceAll('_', ' ')
						};
						return { label: tag.name, dot: tagDot(tag) };
					})
				)}
			{/if}
			{#if selectedUsers.length}
				{@render chip(
					'users',
					selectedUsers.map((id) => ({
						label: folderUsers.find((entry) => entry.id === id)?.name ?? $i18n.t('Unknown'),
						avatar: `${WEBUI_API_BASE_URL}/users/${id}/profile/image`
					}))
				)}
			{/if}
			{#if activity}
				{@render chip('activity', [
					{ label: $i18n.t(activityOptions.find(([value]) => value === activity)?.[1] ?? '') }
				])}
			{/if}
			{#if updatedRange}
				{@render chip('updated', [
					{ label: $i18n.t(updatedOptions.find(([value]) => value === updatedRange)?.[1] ?? '') }
				])}
			{/if}
			<button
				type="button"
				class="flex size-5 items-center justify-center rounded-full text-base-400 transition-colors hover:text-base-600 dark:text-base-500 dark:hover:text-base-300"
				aria-label={$i18n.t('Clear filters')}
				title={$i18n.t('Clear filters')}
				on:click={clear}><XMark className="size-3" /></button
			>
		</div>
	{/if}

	{#if error}
		<div
			role="alert"
			class="mx-3 mb-1.5 flex items-center justify-between gap-3 rounded-xl bg-red-50/60 px-3 py-2 text-xs text-red-600 dark:bg-red-500/5 dark:text-red-400"
		>
			<span class="min-w-0 truncate">{error}</span>
			<button type="button" class="shrink-0 underline" on:click={() => load()}
				>{$i18n.t('Retry')}</button
			>
		</div>
	{/if}

	<div class="min-h-0 min-w-0 flex-1 overflow-hidden">
		{#if folderSection === 'files' && filesTarget && folderViewSettled}
			<div class="h-full">
				{#key filesTarget.selector}
					{#await import('../FileNav.svelte') then { default: FileNav }}
						<FileNav
							target={filesTarget}
							machineId={filesTarget.selector}
							initialDirectory={filesDirectory || folder?.data?.working_directory || null}
							manageFileRequests={false}
							showTerminalDock={false}
							onOpenFile={(path, page) => showFileNavPath.set({ path, page })}
							onViewChange={(view) => {
								filesDirectory = view?.directory ?? null;
								saveFolderPage();
							}}
						/>
					{/await}
				{/key}
			</div>
		{:else if folderSection === 'notes'}
			<FolderNotes
				bind:this={notesView}
				folderId={folder?.id ?? ''}
				{notes}
				total={notesTotal}
				loading={notesLoading}
				canCreate={!readOnly}
				onReload={() => loadNotes()}
				onMore={loadMoreNotes}
			/>
		{:else if folderSection === 'automations'}
			<FolderAutomations
				bind:this={automationsView}
				folderId={folder?.id ?? ''}
				{automations}
				loading={automationsLoading}
				canCreate={!readOnly}
				onReload={loadAutomations}
			/>
		{:else if folderSection === 'knowledge'}
			<FolderKnowledge
				bind:this={knowledgeView}
				bind:items={knowledgeItems}
				{folder}
				{readOnly}
				onPick={() => (showKnowledgePicker = true)}
			/>
		{:else if loading && !hasData}
			<div
				role="status"
				aria-label={$i18n.t('Loading…')}
				class="flex h-full items-center justify-center"
				style="padding-bottom: var(--folder-composer-space, 0px)"
			>
				<Spinner className="size-4" />
			</div>
		{:else if hasData && !total && !error && view === 'list'}
			<div
				class="flex h-full flex-col items-center justify-center gap-1 px-6 text-center"
				style="padding-bottom: calc(var(--folder-composer-space, 0px) + 2rem)"
			>
				<div class="text-sm text-base-800 dark:text-base-100">
					{filtered ? $i18n.t('No matching conversations') : $i18n.t('No conversations yet')}
				</div>
				<div class="text-xs text-base-500 dark:text-base-400">
					{filtered
						? $i18n.t('Try a different search or remove a filter.')
						: readOnly
							? $i18n.t('Conversations in this folder will show up here.')
							: $i18n.t('Ask anything below to start one.')}
				</div>
				{#if filtered}
					<button
						type="button"
						class="mt-2 text-xs text-base-400 transition-colors hover:text-base-600 dark:text-base-500 dark:hover:text-base-300"
						on:click={clear}>{$i18n.t('Clear filters')}</button
					>
				{/if}
			</div>
		{:else if view === 'board'}
			<FolderBoard
				onAddStatus={readOnly || columnsBy !== 'status' ? null : () => (showStatuses = true)}
				onReorder={readOnly || columnsBy !== 'status' ? null : reorderStatuses}
				columns={boardColumns}
				rows={boardRows}
				{rowOf}
				{dropTargets}
				{showPriority}
				{saving}
				{loading}
				{loadingGroup}
				onMore={loadMore}
				onMove={move}
				onPriority={prioritize}
				onDrop={update}
				onTagsChange={changed}
				collapsed={collapsed[`${folder?.id}:${rowsBy}`] ?? {}}
				onCollapse={(id) => toggleCollapsed(rowsBy, id)}
			/>
		{:else}
			<ChatList
				groups={listGroups}
				{showPriority}
				{saving}
				{loading}
				{loadingGroup}
				onMore={loadMore}
				onMove={move}
				onPriority={prioritize}
				onTagsChange={changed}
				collapsed={collapsed[`${folder?.id}:${grouping}`] ?? {}}
				onCollapse={(id) => toggleCollapsed(grouping, id)}
			/>
		{/if}
	</div>
</section>

<FolderStatusesModal
	bind:show={showStatuses}
	statuses={groupedStatusDefs(folder?.meta, (key) => $i18n.t(key))}
	onSave={saveStatuses}
/>
