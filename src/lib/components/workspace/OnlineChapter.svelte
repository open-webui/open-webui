<script lang="ts">
	import Fuse from 'fuse.js';
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { WEBUI_NAME, user } from '$lib/stores';
	import { getStores, type GeminiRagStore } from '$lib/apis/gemini-rag';
	import {
		getTextbookData,
		createSection,
		updateSection,
		deleteSection,
		createSubsection,
		updateSubsection,
		deleteSubsection,
		type Section,
		type Subsection
	} from '$lib/apis/textbook';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';

	import PartItem from './OnlineChapter/PartItem.svelte';
	import ChapterItem from './OnlineChapter/ChapterItem.svelte';
	import CreatePartModal from './OnlineChapter/CreatePartModal.svelte';
	import CreateChapterModal from './OnlineChapter/CreateChapterModal.svelte';

	// Types (UI용, API 타입과 매핑)
	// API Section → UI Part, API Subsection → UI Chapter
	interface Part {
		id: string;
		name: string; // API: title
		chapters: Chapter[];
	}

	interface Chapter {
		id: string;
		partId: string;
		name: string; // API: title (예: "1. 1계 상미분방정식")
		description: string; // API: subtitle
		linkedKnowledgeGroups: string[]; // API: rag_store_name
	}

	interface KnowledgeGroup {
		id: string;
		name: string;
		itemCount: number;
	}

	// State
	let loaded = false;
	let query = '';
	let expandedParts: Record<string, boolean> = {};

	// Modal states
	let showCreatePartModal = false;
	let showCreateChapterModal = false;
	let showDeleteConfirm = false;
	let editingPart: Part | null = null;
	let editingChapter: Chapter | null = null;
	let selectedPartIdForChapter: string | null = null;
	let deleteTarget: { type: 'part' | 'chapter'; id: string } | null = null;

	// Data
	let parts: Part[] = [];
	let knowledgeGroups: KnowledgeGroup[] = [];

	// API Section을 UI Part로 변환
	const mapSectionToPart = (section: Section): Part => ({
		id: section.id,
		name: section.title, // API title → UI name
		chapters: (section.subsections || []).map((sub) => ({
			id: sub.id,
			partId: section.id,
			name: sub.title, // API title → UI name
			description: sub.subtitle || '',
			linkedKnowledgeGroups: sub.rag_store_name ? [sub.rag_store_name] : []
		}))
	});

	// Load knowledge groups from API
	const loadKnowledgeGroups = async () => {
		try {
			const response = await getStores(localStorage.token);
			const stores = response?.stores;
			if (stores) {
				knowledgeGroups = stores.map((store: GeminiRagStore) => ({
					id: store.name.replace('fileSearchStores/', ''),
					name: store.display_name,
					itemCount: store.corpora_count || 0
				}));
			}
		} catch (error) {
			console.error('Failed to load knowledge groups:', error);
			toast.error($i18n.t('지식 그룹을 불러오는데 실패했습니다.'));
		}
	};

	// Load textbook data from API
	const loadTextbookData = async () => {
		try {
			const data = await getTextbookData(localStorage.token);
			if (data?.sections) {
				parts = data.sections.map(mapSectionToPart);
				// Expand first part by default
				if (parts.length > 0) {
					expandedParts[parts[0].id] = true;
				}
			}
		} catch (error) {
			console.error('Failed to load textbook data:', error);
			toast.error($i18n.t('교재 데이터를 불러오는데 실패했습니다.'));
		}
	};

	// Search with Fuse.js
	let filteredParts: Part[] = [];
	let partFuse: Fuse<Part> | null = null;

	const setupFuse = async () => {
		// Create a flat array for searching both parts and chapters
		partFuse = new Fuse(parts, {
			keys: ['name', 'description', 'chapters.name', 'chapters.title', 'chapters.description'],
			threshold: 0.3
		});
		await tick();
		updateFilteredParts();
	};

	$: if (parts) {
		setupFuse();
	}

	const updateFilteredParts = () => {
		if (!partFuse || !query) {
			filteredParts = [...parts];
			return;
		}
		filteredParts = partFuse.search(query).map((result) => result.item);
	};

	$: if (query !== undefined && partFuse) {
		updateFilteredParts();
	}

	// Get total counts
	$: totalParts = parts.length;
	$: totalChapters = parts.reduce((acc, p) => acc + p.chapters.length, 0);

	// Handlers
	const togglePart = (partId: string) => {
		expandedParts[partId] = !expandedParts[partId];
		expandedParts = expandedParts;
	};

	const handleCreatePart = async (event: CustomEvent<{ name: string; description: string }>) => {
		const { name } = event.detail;
		try {
			const result = await createSection(
				localStorage.token,
				name || `Part ${String.fromCharCode(65 + parts.length)}`
			);
			if (result) {
				parts = [...parts, mapSectionToPart({ ...result, subsections: [] })];
				showCreatePartModal = false;
				toast.success($i18n.t('파트가 생성되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to create section:', error);
			toast.error($i18n.t('파트 생성에 실패했습니다.'));
		}
	};

	const handleEditPart = (part: Part) => {
		editingPart = part;
		showCreatePartModal = true;
	};

	const handleUpdatePart = async (event: CustomEvent<{ name: string; description: string }>) => {
		if (!editingPart) return;
		const { name } = event.detail;
		try {
			const result = await updateSection(localStorage.token, editingPart.id, {
				title: name || editingPart.name
			});
			if (result) {
				parts = parts.map((p) =>
					p.id === editingPart!.id ? { ...p, name: result.title } : p
				);
				editingPart = null;
				showCreatePartModal = false;
				toast.success($i18n.t('파트가 수정되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to update section:', error);
			toast.error($i18n.t('파트 수정에 실패했습니다.'));
		}
	};

	const handleDeletePart = (partId: string) => {
		deleteTarget = { type: 'part', id: partId };
		showDeleteConfirm = true;
	};

	const handleCreateChapter = (partId: string) => {
		selectedPartIdForChapter = partId;
		editingChapter = null;
		showCreateChapterModal = true;
	};

	const handleSaveChapter = async (
		event: CustomEvent<{
			partId: string;
			name: string;
			title: string;
			description: string;
			linkedKnowledgeGroups: string[];
		}>
	) => {
		const { partId, name, description, linkedKnowledgeGroups } = event.detail;
		// rag_store_name은 하나만 지원 (첫 번째 선택된 그룹)
		const ragStoreName = linkedKnowledgeGroups.length > 0 ? linkedKnowledgeGroups[0] : null;

		if (editingChapter) {
			// Update existing subsection
			try {
				const result = await updateSubsection(localStorage.token, editingChapter.id, {
					title: name || editingChapter.name,
					subtitle: description || '',
					rag_store_name: ragStoreName
				});
				if (result) {
					parts = parts.map((p) => {
						if (p.id === partId) {
							return {
								...p,
								chapters: p.chapters.map((ch) =>
									ch.id === editingChapter!.id
										? {
												...ch,
												name: result.title,
												description: result.subtitle || '',
												linkedKnowledgeGroups: result.rag_store_name ? [result.rag_store_name] : []
											}
										: ch
								)
							};
						}
						return p;
					});
					toast.success($i18n.t('챕터가 수정되었습니다.'));
				}
			} catch (error) {
				console.error('Failed to update subsection:', error);
				toast.error($i18n.t('챕터 수정에 실패했습니다.'));
			}
		} else {
			// Create new subsection
			try {
				const result = await createSubsection(localStorage.token, partId, {
					title: name || `Chapter ${totalChapters + 1}`,
					subtitle: description || '',
					rag_store_name: ragStoreName
				});
				if (result) {
					const newChapter: Chapter = {
						id: result.id,
						partId: partId,
						name: result.title,
						description: result.subtitle || '',
						linkedKnowledgeGroups: result.rag_store_name ? [result.rag_store_name] : []
					};
					parts = parts.map((p) => {
						if (p.id === partId) {
							return {
								...p,
								chapters: [...p.chapters, newChapter]
							};
						}
						return p;
					});
					// Expand the part when adding a chapter
					expandedParts[partId] = true;
					expandedParts = expandedParts;
					toast.success($i18n.t('챕터가 생성되었습니다.'));
				}
			} catch (error) {
				console.error('Failed to create subsection:', error);
				toast.error($i18n.t('챕터 생성에 실패했습니다.'));
			}
		}

		editingChapter = null;
		showCreateChapterModal = false;
	};

	const handleEditChapter = (chapter: Chapter) => {
		editingChapter = chapter;
		selectedPartIdForChapter = chapter.partId;
		showCreateChapterModal = true;
	};

	const handleDeleteChapter = (chapterId: string) => {
		deleteTarget = { type: 'chapter', id: chapterId };
		showDeleteConfirm = true;
	};

	const confirmDelete = async () => {
		if (!deleteTarget) return;

		try {
			if (deleteTarget.type === 'part') {
				await deleteSection(localStorage.token, deleteTarget.id);
				parts = parts.filter((p) => p.id !== deleteTarget!.id);
				toast.success($i18n.t('파트가 삭제되었습니다.'));
			} else {
				await deleteSubsection(localStorage.token, deleteTarget.id);
				parts = parts.map((p) => ({
					...p,
					chapters: p.chapters.filter((ch) => ch.id !== deleteTarget!.id)
				}));
				toast.success($i18n.t('챕터가 삭제되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to delete:', error);
			toast.error($i18n.t('삭제에 실패했습니다.'));
		}

		deleteTarget = null;
		showDeleteConfirm = false;
	};

	const getKnowledgeGroupName = (groupId: string): string => {
		return knowledgeGroups.find((g) => g.id === groupId)?.name || groupId;
	};

	onMount(async () => {
		await Promise.all([loadKnowledgeGroups(), loadTextbookData()]);
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('온라인 챕터')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog bind:show={showDeleteConfirm} on:confirm={confirmDelete} />

	<CreatePartModal
		bind:show={showCreatePartModal}
		editMode={!!editingPart}
		part={editingPart}
		on:create={handleCreatePart}
		on:update={handleUpdatePart}
		on:close={() => {
			editingPart = null;
		}}
	/>

	<CreateChapterModal
		bind:show={showCreateChapterModal}
		editMode={!!editingChapter}
		chapter={editingChapter}
		partId={selectedPartIdForChapter}
		{parts}
		{knowledgeGroups}
		on:save={handleSaveChapter}
		on:close={() => {
			editingChapter = null;
		}}
	/>

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3 text-gray-900 dark:text-gray-100">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<span>{$i18n.t('온라인 챕터')}</span>
				<span class="text-lg font-medium text-gray-500"
					>{totalParts} parts • {totalChapters} chapters</span
				>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				<button
					class="px-2 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center"
					on:click={() => {
						editingPart = null;
						showCreatePartModal = true;
					}}
				>
					<Plus className="size-3" strokeWidth="2.5" />
					<span class="hidden md:block md:ml-1 text-xs">{$i18n.t('새 파트')}</span>
				</button>
				<button
					class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					on:click={() => {
						selectedPartIdForChapter = parts.length > 0 ? parts[0].id : null;
						editingChapter = null;
						showCreateChapterModal = true;
					}}
				>
					<Plus className="size-3" strokeWidth="2.5" />
					<span class="hidden md:block md:ml-1 text-xs">{$i18n.t('새 챕터')}</span>
				</button>
			</div>
		</div>
	</div>

	<div
		class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-850"
	>
		<!-- Search -->
		<div class="flex w-full space-x-2 py-0.5 px-3.5 pb-2">
			<div class="flex flex-1">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('파트 또는 챕터 검색')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
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

		<!-- Tree View Content -->
		{#if filteredParts.length > 0}
			<div class="my-2 px-3">
				{#each filteredParts as part (part.id)}
					<PartItem
						{part}
						isExpanded={expandedParts[part.id] || false}
						on:toggle={() => togglePart(part.id)}
						on:edit={() => handleEditPart(part)}
						on:delete={() => handleDeletePart(part.id)}
						on:addChapter={() => handleCreateChapter(part.id)}
					>
						{#if expandedParts[part.id]}
							<div class="ml-6 mt-1 mb-2 border-l-2 border-gray-200 dark:border-gray-700">
								{#each part.chapters as chapter, idx (chapter.id)}
									<ChapterItem
										{chapter}
										isLast={idx === part.chapters.length - 1}
										{knowledgeGroups}
										{getKnowledgeGroupName}
										on:edit={() => handleEditChapter(chapter)}
										on:delete={() => handleDeleteChapter(chapter.id)}
									/>
								{/each}
								{#if part.chapters.length === 0}
									<div class="pl-4 py-2 text-sm text-gray-400 dark:text-gray-500">
										{$i18n.t('챕터가 없습니다')}
									</div>
								{/if}
							</div>
						{/if}
					</PartItem>
				{/each}
			</div>
		{:else}
			<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class="text-3xl mb-3">📚</div>
					<div class="text-lg font-medium mb-1 dark:text-white">
						{query ? $i18n.t('검색 결과가 없습니다') : $i18n.t('파트가 없습니다')}
					</div>
					<div class="text-gray-500 text-center text-xs">
						{query
							? $i18n.t('다른 검색어로 시도해 보세요.')
							: $i18n.t('새 파트를 만들어 챕터를 관리해 보세요.')}
					</div>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
