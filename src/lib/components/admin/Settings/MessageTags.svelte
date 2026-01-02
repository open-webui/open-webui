<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import {
		type TagDefinition,
		type DaemonConfig,
		type TagStats,
		type DaemonProgress,
		getDaemonConfig,
		updateDaemonConfig,
		runDaemonManually,
		unlockDaemon,
		getDaemonProgress,
		getAllTags,
		deleteTag,
		updateTagProtection,
		getTagStats,
		getBlacklist,
		addToBlacklist,
		removeFromBlacklist
	} from '$lib/apis/message-tags';
	import { getStores, type GeminiRagStore } from '$lib/apis/gemini-rag';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import CreateTagModal from './MessageTags/CreateTagModal.svelte';
	import RenameTagModal from './MessageTags/RenameTagModal.svelte';
	import MergeTagsModal from './MessageTags/MergeTagsModal.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	// State
	let loaded = false;
	let saving = false;
	let runningDaemon = false;
	let unlockingDaemon = false;
	let progressPolling: ReturnType<typeof setInterval> | null = null;

	// Data
	let stats: TagStats | null = null;
	let config: DaemonConfig | null = null;
	let tags: TagDefinition[] = [];
	let blacklist: string[] = [];
	let ragStores: GeminiRagStore[] = [];
	let progress: DaemonProgress | null = null;

	// Form state (bound to config)
	let formEnabled = false;
	let formSchedule: 'daily' | 'weekly' = 'daily';
	let formRunTime = '03:00';
	let formLookbackDays = 7;
	let formBatchSize = 10;
	let formMaxTags = 100;
	let formConsolidationThreshold = 90;
	let formCustomTaggingPrompt = '';
	let formCustomSystemInstruction = '';
	let formRagStoreNames: string[] = [];

	// Search & Filter
	let searchQuery = '';
	let fuse: Fuse<TagDefinition>;
	let filteredTags: TagDefinition[] = [];

	// Modal states
	let showCreateModal = false;
	let showRenameModal = false;
	let showMergeModal = false;
	let selectedTag: TagDefinition | null = null;
	let selectedTagsForMerge: TagDefinition[] = [];

	// Blacklist state
	let newBlacklistTag = '';
	let addingToBlacklist = false;

	// Search setup
	$: {
		fuse = new Fuse(tags, {
			keys: ['id', 'name'],
			threshold: 0.3
		});
	}

	$: {
		filteredTags = searchQuery
			? fuse.search(searchQuery).map((r) => r.item)
			: tags;
	}

	// Load data
	const loadData = async () => {
		try {
			const token = localStorage.token;
			const [statsRes, configRes, tagsRes, blacklistRes, ragStoresRes] = await Promise.all([
				getTagStats(token),
				getDaemonConfig(token),
				getAllTags(token),
				getBlacklist(token),
				getStores(token)
			]);

			stats = statsRes;
			config = configRes;
			tags = tagsRes || [];
			blacklist = blacklistRes || [];
			ragStores = ragStoresRes || [];

			// Initialize form with config values
			if (config) {
				formEnabled = config.enabled;
				formSchedule = config.schedule;
				formRunTime = config.run_time;
				formLookbackDays = config.lookback_days;
				formBatchSize = config.batch_size;
				formMaxTags = config.max_tags;
				formConsolidationThreshold = config.consolidation_threshold;
				formCustomTaggingPrompt = config.custom_tagging_prompt || '';
				formCustomSystemInstruction = config.custom_system_instruction || '';
				formRagStoreNames = config.rag_store_names || [];
			}
		} catch (error) {
			console.error('Failed to load message tags data:', error);
			toast.error($i18n.t('데이터를 불러오는데 실패했습니다.'));
		}
		loaded = true;
	};

	// Save config
	const handleSaveConfig = async () => {
		saving = true;
		try {
			const result = await updateDaemonConfig(localStorage.token, {
				enabled: formEnabled,
				schedule: formSchedule,
				run_time: formRunTime,
				lookback_days: formLookbackDays,
				batch_size: formBatchSize,
				max_tags: formMaxTags,
				consolidation_threshold: formConsolidationThreshold,
				custom_tagging_prompt: formCustomTaggingPrompt || null,
				custom_system_instruction: formCustomSystemInstruction || null,
				rag_store_names: formRagStoreNames
			});

			if (result) {
				config = result;
				toast.success($i18n.t('설정이 저장되었습니다.'));
				saveHandler();
			}
		} catch (error) {
			console.error('Failed to save config:', error);
			toast.error($i18n.t('설정 저장에 실패했습니다.'));
		}
		saving = false;
	};

	// Run daemon manually
	const handleRunDaemon = async () => {
		runningDaemon = true;
		try {
			const result = await runDaemonManually(localStorage.token);
			if (result) {
				toast.success($i18n.t('태깅 작업이 시작되었습니다.'));
				// Start polling progress
				startProgressPolling();
			}
		} catch (error) {
			console.error('Failed to run daemon:', error);
			toast.error($i18n.t('태깅 작업 실행에 실패했습니다.'));
		}
		runningDaemon = false;
	};

	// Unlock daemon
	const handleUnlockDaemon = async () => {
		if (!confirm($i18n.t('데몬 lock을 강제로 해제하시겠습니까?'))) {
			return;
		}

		unlockingDaemon = true;
		try {
			const result = await unlockDaemon(localStorage.token);
			if (result?.success) {
				toast.success($i18n.t('Lock이 해제되었습니다.'));
				// Reload config to refresh lock status
				await loadData();
			}
		} catch (error) {
			console.error('Failed to unlock daemon:', error);
			toast.error($i18n.t('Lock 해제에 실패했습니다.'));
		}
		unlockingDaemon = false;
	};

	// Delete tag
	const handleDeleteTag = async (tag: TagDefinition) => {
		if (!confirm($i18n.t('정말로 이 태그를 삭제하시겠습니까? 관련된 모든 메시지 태그도 삭제됩니다.'))) {
			return;
		}

		try {
			const result = await deleteTag(localStorage.token, tag.id);
			if (result?.success) {
				tags = tags.filter((t) => t.id !== tag.id);
				toast.success($i18n.t('태그가 삭제되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to delete tag:', error);
			toast.error($i18n.t('태그 삭제에 실패했습니다.'));
		}
	};

	// Toggle protection
	const handleToggleProtection = async (tag: TagDefinition) => {
		try {
			const result = await updateTagProtection(localStorage.token, tag.id, !tag.is_protected);
			if (result) {
				tags = tags.map((t) => (t.id === tag.id ? result : t));
				toast.success(
					result.is_protected
						? $i18n.t('태그가 보호 상태로 변경되었습니다.')
						: $i18n.t('태그 보호가 해제되었습니다.')
				);
			}
		} catch (error) {
			console.error('Failed to toggle protection:', error);
			toast.error($i18n.t('보호 상태 변경에 실패했습니다.'));
		}
	};

	// Blacklist handlers
	const handleAddToBlacklist = async () => {
		if (!newBlacklistTag.trim()) {
			toast.error($i18n.t('태그 ID를 입력해주세요.'));
			return;
		}

		addingToBlacklist = true;
		try {
			const result = await addToBlacklist(localStorage.token, [newBlacklistTag.trim()]);
			if (result?.success) {
				blacklist = [...blacklist, newBlacklistTag.trim()];
				// Remove from tags list if exists
				tags = tags.filter((t) => t.id !== newBlacklistTag.trim());
				newBlacklistTag = '';
				toast.success($i18n.t('블랙리스트에 추가되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to add to blacklist:', error);
			toast.error($i18n.t('블랙리스트 추가에 실패했습니다.'));
		}
		addingToBlacklist = false;
	};

	const handleRemoveFromBlacklist = async (tagId: string) => {
		try {
			const result = await removeFromBlacklist(localStorage.token, [tagId]);
			if (result?.success) {
				blacklist = blacklist.filter((id) => id !== tagId);
				toast.success($i18n.t('블랙리스트에서 제거되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to remove from blacklist:', error);
			toast.error($i18n.t('블랙리스트 제거에 실패했습니다.'));
		}
	};

	// Format timestamp
	const formatDate = (timestamp: number | null) => {
		if (!timestamp) return '-';
		return new Date(timestamp * 1000).toLocaleString('ko-KR');
	};

	// Progress polling
	const startProgressPolling = () => {
		stopProgressPolling();
		updateProgress(); // Initial fetch
		progressPolling = setInterval(updateProgress, 2000); // Poll every 2 seconds
	};

	const stopProgressPolling = () => {
		if (progressPolling) {
			clearInterval(progressPolling);
			progressPolling = null;
		}
	};

	const updateProgress = async () => {
		try {
			const result = await getDaemonProgress(localStorage.token);
			progress = result;
			
			// Stop polling if not running or completed/error
			if (result && (!result.is_running || result.status === 'completed' || result.status === 'error')) {
				stopProgressPolling();
				// Reload data after completion
				if (result.status === 'completed') {
					setTimeout(loadData, 1000);
				}
			}
		} catch (error) {
			console.error('Failed to fetch progress:', error);
		}
	};

	// Status display helpers
	const getStatusText = (status: string) => {
		const statusMap = {
			idle: '대기 중',
			collecting: '메시지 수집 중',
			processing: '태그 처리 중',
			consolidating: '태그 통합 중',
			completed: '완료',
			error: '오류 발생'
		};
		return statusMap[status] || status;
	};

	const getStatusColor = (status: string) => {
		const colorMap = {
			idle: 'text-gray-500',
			collecting: 'text-blue-600 dark:text-blue-400',
			processing: 'text-blue-600 dark:text-blue-400',
			consolidating: 'text-purple-600 dark:text-purple-400',
			completed: 'text-green-600 dark:text-green-400',
			error: 'text-red-600 dark:text-red-400'
		};
		return colorMap[status] || 'text-gray-500';
	};

	onMount(() => {
		loadData();
		// Check if daemon is already running
		updateProgress();
		
		return () => {
			stopProgressPolling();
		};
	});
</script>

<div class="flex flex-col gap-6 text-sm">
	{#if !loaded}
		<div class="flex justify-center py-8">
			<Spinner />
		</div>
	{:else}
		<!-- Stats Cards -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-4">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('총 태그 수')}</div>
				<div class="text-2xl font-semibold text-gray-900 dark:text-white">
					{stats?.total_unique_tags ?? 0}
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-4">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('태그된 메시지')}</div>
				<div class="text-2xl font-semibold text-gray-900 dark:text-white">
					{stats?.total_tagged_messages ?? 0}
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-4">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('최대 태그 제한')}</div>
				<div class="text-2xl font-semibold text-gray-900 dark:text-white">
					{stats?.max_tags_limit ?? 100}
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-4">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('마지막 실행')}</div>
				<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
					{formatDate(stats?.last_run_at ?? null)}
				</div>
				{#if stats?.last_run_status}
					<div class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
						{stats.last_run_status}
					</div>
				{/if}
			</div>
		</div>

		<!-- Progress Section -->
		{#if progress && progress.is_running}
			<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5">
				<div class="flex items-center justify-between mb-3">
					<h3 class="text-base font-semibold text-blue-900 dark:text-blue-100">
						{$i18n.t('태깅 진행 중')}
					</h3>
					<div class="flex items-center gap-2">
						<Spinner className="w-4 h-4 text-blue-600" />
						<span class="text-sm font-medium {getStatusColor(progress.status)}">
							{getStatusText(progress.status)}
						</span>
					</div>
				</div>

				<!-- Progress bar -->
				<div class="mb-3">
					<div class="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
						<span>{progress.processed_messages} / {progress.total_messages} 메시지</span>
						<span>{progress.progress_percent.toFixed(1)}%</span>
					</div>
					<div class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
						<div 
							class="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-300"
							style="width: {progress.progress_percent}%;"
						></div>
					</div>
				</div>

				<!-- Details -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
					<div>
						<div class="text-gray-500 dark:text-gray-400">배치</div>
						<div class="font-medium text-gray-900 dark:text-white">
							{progress.current_batch} / {progress.total_batches}
						</div>
					</div>
					<div>
						<div class="text-gray-500 dark:text-gray-400">시작 시간</div>
						<div class="font-medium text-gray-900 dark:text-white">
							{formatDate(progress.started_at)}
						</div>
					</div>
					{#if progress.last_error}
						<div class="col-span-2">
							<div class="text-red-500 dark:text-red-400">오류</div>
							<div class="font-medium text-red-600 dark:text-red-400 truncate">
								{progress.last_error}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Daemon Config Section -->
		<div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
			<h3 class="text-base font-semibold text-gray-900 dark:text-white mb-4">
				{$i18n.t('자동 태깅 데몬 설정')}
			</h3>

			<div class="space-y-4">
				<!-- Enabled -->
				<div class="flex items-center justify-between">
					<div>
						<div class="font-medium text-gray-900 dark:text-white">{$i18n.t('데몬 활성화')}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('자동 태깅 데몬을 활성화합니다.')}
						</div>
					</div>
					<Switch bind:state={formEnabled} />
				</div>

				<!-- Schedule -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('실행 주기')}
						</label>
						<select
							bind:value={formSchedule}
							class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						>
							<option value="daily">{$i18n.t('매일')}</option>
							<option value="weekly">{$i18n.t('매주')}</option>
						</select>
					</div>
					<div>
						<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('실행 시간 (UTC)')}
						</label>
						<input
							type="time"
							bind:value={formRunTime}
							class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						/>
					</div>
				</div>

				<!-- Numeric settings -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
					<div>
						<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('검색 기간 (일)')}
						</label>
						<input
							type="number"
							bind:value={formLookbackDays}
							min="1"
							max="365"
							class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						/>
					</div>
					<div>
						<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('배치 크기')}
						</label>
						<input
							type="number"
							bind:value={formBatchSize}
							min="1"
							max="100"
							class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						/>
					</div>
					<div>
						<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('최대 태그 수')}
						</label>
						<input
							type="number"
							bind:value={formMaxTags}
							min="1"
							max="1000"
							class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						/>
					</div>
					<div>
						<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('통합 임계값 (%)')}
						</label>
						<input
							type="number"
							bind:value={formConsolidationThreshold}
							min="0"
							max="100"
							class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						/>
					</div>
				</div>

				<!-- Custom prompts -->
				<div>
					<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('커스텀 태깅 프롬프트')}
						<Tooltip content={$i18n.t('{existing_tags}와 {messages} 플레이스홀더 사용 가능')}>
							<span class="text-gray-400 cursor-help">ⓘ</span>
						</Tooltip>
					</label>
					<textarea
						bind:value={formCustomTaggingPrompt}
						rows="10"
						placeholder={$i18n.t('비워두면 기본 프롬프트 사용')}
						class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg resize-none"
					/>
				</div>

				<div>
					<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('커스텀 시스템 지시사항')}
					</label>
					<textarea
						bind:value={formCustomSystemInstruction}
						rows="10"
						placeholder={$i18n.t('비워두면 기본 시스템 지시사항 사용')}
						class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg resize-none"
					/>
				</div>

				<!-- RAG Store Selection -->
				<div>
					<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.t('RAG Store 선택')}
						<Tooltip content={$i18n.t('태깅 시 참조할 RAG Store를 선택합니다.')}>
							<span class="text-gray-400 cursor-help">ⓘ</span>
						</Tooltip>
					</label>
					{#if ragStores.length > 0}
						<div class="space-y-2 max-h-40 overflow-y-auto p-2 bg-gray-50 dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700">
							{#each ragStores as store (store.name)}
								<label class="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded cursor-pointer transition">
									<input
										type="checkbox"
										value={store.name}
										checked={formRagStoreNames.includes(store.name)}
										on:change={(e) => {
											if (e.currentTarget.checked) {
												formRagStoreNames = [...formRagStoreNames, store.name];
											} else {
												formRagStoreNames = formRagStoreNames.filter(n => n !== store.name);
											}
										}}
										class="w-4 h-4 text-blue-600 rounded border-gray-300 dark:border-gray-600 focus:ring-blue-500"
									/>
									<div class="flex-1 min-w-0">
										<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{store.display_name}
										</div>
										<div class="text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
											{store.name}
										</div>
									</div>
								</label>
							{/each}
						</div>
						{#if formRagStoreNames.length > 0}
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{formRagStoreNames.length}개 선택됨
							</div>
						{/if}
					{:else}
						<div class="text-sm text-gray-500 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700">
							{$i18n.t('사용 가능한 RAG Store가 없습니다.')}
						</div>
					{/if}
				</div>

				<!-- Buttons -->
				<div class="flex gap-3 pt-2">
					<button
						on:click={handleRunDaemon}
						disabled={runningDaemon}
						class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition disabled:opacity-50"
					>
						{#if runningDaemon}
							<Spinner className="w-4 h-4" />
						{:else}
							{$i18n.t('수동 실행')}
						{/if}
					</button>
					<button
						on:click={handleUnlockDaemon}
						disabled={unlockingDaemon}
						class="px-4 py-2 text-sm font-medium text-yellow-700 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 hover:bg-yellow-100 dark:hover:bg-yellow-900/30 rounded-lg transition disabled:opacity-50"
					>
						{#if unlockingDaemon}
							<Spinner className="w-4 h-4" />
						{:else}
							{$i18n.t('Lock 해제')}
						{/if}
					</button>
					<button
						on:click={handleSaveConfig}
						disabled={saving}
						class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50"
					>
						{#if saving}
							<Spinner className="w-4 h-4" />
						{:else}
							{$i18n.t('설정 저장')}
						{/if}
					</button>
				</div>
			</div>
		</div>

		<!-- Tags Management Section -->
		<div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
			<div class="flex items-center justify-between mb-4">
				<h3 class="text-base font-semibold text-gray-900 dark:text-white">
					{$i18n.t('태그 관리')}
				</h3>
				<div class="flex items-center gap-2">
					<!-- Search -->
					<div class="relative">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
						<input
							type="text"
							bind:value={searchQuery}
							placeholder={$i18n.t('태그 검색...')}
							class="pl-9 pr-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg w-48"
						/>
					</div>
					<!-- Create button -->
					<button
						on:click={() => (showCreateModal = true)}
						class="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
					>
						<Plus className="w-4 h-4" />
						{$i18n.t('새 태그')}
					</button>
					<!-- Merge button -->
					<button
						on:click={() => {
							selectedTagsForMerge = [];
							showMergeModal = true;
						}}
						class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
					>
						{$i18n.t('태그 병합')}
					</button>
				</div>
			</div>

			<!-- Tags Table -->
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="border-b border-gray-200 dark:border-gray-700">
							<th class="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t('태그 ID')}
							</th>
							<th class="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t('이름')}
							</th>
							<th class="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t('사용 횟수')}
							</th>
							<th class="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t('보호')}
							</th>
							<th class="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t('생성일')}
							</th>
							<th class="text-right py-2 px-3 font-medium text-gray-500 dark:text-gray-400">
								{$i18n.t('작업')}
							</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredTags as tag (tag.id)}
							<tr class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850">
								<td class="py-2 px-3 text-gray-900 dark:text-white font-mono text-xs">
									{tag.id}
								</td>
								<td class="py-2 px-3 text-gray-900 dark:text-white">
									{tag.name}
								</td>
								<td class="py-2 px-3 text-center text-gray-600 dark:text-gray-400">
									{tag.usage_count}
								</td>
								<td class="py-2 px-3 text-center">
									{#if tag.is_protected}
										<span class="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
											{$i18n.t('보호됨')}
										</span>
									{:else}
										<span class="text-gray-400">-</span>
									{/if}
								</td>
								<td class="py-2 px-3 text-gray-600 dark:text-gray-400 text-xs">
									{formatDate(tag.created_at)}
								</td>
								<td class="py-2 px-3 text-right">
									<div class="flex items-center justify-end gap-1">
										<button
											on:click={() => {
												selectedTag = tag;
												showRenameModal = true;
											}}
											class="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition"
										>
											{$i18n.t('이름 변경')}
										</button>
										<button
											on:click={() => handleToggleProtection(tag)}
											class="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition"
										>
											{tag.is_protected ? $i18n.t('보호 해제') : $i18n.t('보호 설정')}
										</button>
										<button
											on:click={() => handleDeleteTag(tag)}
											class="px-2 py-1 text-xs text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition"
										>
											{$i18n.t('삭제')}
										</button>
									</div>
								</td>
							</tr>
						{:else}
							<tr>
								<td colspan="6" class="py-8 text-center text-gray-500 dark:text-gray-400">
									{$i18n.t('태그가 없습니다.')}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<!-- Blacklist Section -->
		<div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
			<h3 class="text-base font-semibold text-gray-900 dark:text-white mb-4">
				{$i18n.t('블랙리스트')}
			</h3>
			<p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
				{$i18n.t('블랙리스트에 추가된 태그는 자동 태깅에서 제외되며, 기존 태그도 삭제됩니다.')}
			</p>

			<!-- Add to blacklist -->
			<div class="flex gap-2 mb-4">
				<input
					type="text"
					bind:value={newBlacklistTag}
					placeholder={$i18n.t('태그 ID 입력...')}
					class="flex-1 px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
					on:keydown={(e) => e.key === 'Enter' && handleAddToBlacklist()}
				/>
				<button
					on:click={handleAddToBlacklist}
					disabled={addingToBlacklist || !newBlacklistTag.trim()}
					class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition disabled:opacity-50"
				>
					{#if addingToBlacklist}
						<Spinner className="w-4 h-4" />
					{:else}
						{$i18n.t('추가')}
					{/if}
				</button>
			</div>

			<!-- Blacklist items -->
			{#if blacklist.length > 0}
				<div class="flex flex-wrap gap-2">
					{#each blacklist as tagId (tagId)}
						<div class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-full text-sm">
							<span class="font-mono text-xs">{tagId}</span>
							<button
								on:click={() => handleRemoveFromBlacklist(tagId)}
								class="p-0.5 hover:bg-red-200 dark:hover:bg-red-800/50 rounded-full transition"
							>
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
					{$i18n.t('블랙리스트가 비어있습니다.')}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Modals -->
<CreateTagModal
	bind:show={showCreateModal}
	on:created={(e) => {
		tags = [...tags, e.detail];
		showCreateModal = false;
	}}
/>

<RenameTagModal
	bind:show={showRenameModal}
	tag={selectedTag}
	on:renamed={(e) => {
		tags = tags.map((t) => (t.id === e.detail.id ? e.detail : t));
		showRenameModal = false;
		selectedTag = null;
	}}
/>

<MergeTagsModal
	bind:show={showMergeModal}
	{tags}
	on:merged={() => {
		loadData();
		showMergeModal = false;
	}}
/>
