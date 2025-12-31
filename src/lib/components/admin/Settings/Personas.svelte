<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import {
		type PersonaPrompt,
		type PromptGroupWithMappings,
		type PromptType,
		getPromptGroups,
		getPersonaPrompts,
		getDefaultPromptGroup,
		setDefaultPromptGroup,
		createPromptGroup,
		updatePromptGroup,
		deletePromptGroup,
		createPersonaPrompt,
		updatePersonaPrompt,
		deletePersonaPrompt,
		addPromptToGroup,
		removePromptFromGroup
	} from '$lib/apis/prompt-groups';

	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import PromptItem from './Personas/PromptItem.svelte';
	import PromptGroupItem from './Personas/PromptGroupItem.svelte';
	import CreatePersonaPromptModal from './Personas/CreatePersonaPromptModal.svelte';
	import CreatePromptGroupModal from './Personas/CreatePromptGroupModal.svelte';
	import AddPromptToGroupModal from './Personas/AddPromptToGroupModal.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	// State
	let loaded = false;
	let promptGroups: PromptGroupWithMappings[] = [];
	let personaPrompts: PersonaPrompt[] = [];
	let defaultGroupId: string | null = null;
	let expandedGroups: Record<string, boolean> = {};

	// Filters
	let promptTypeFilter: PromptType | 'all' | 'general' = 'all';
	let searchQuery = '';

	// Modal states
	let showCreateGroupModal = false;
	let showAddPromptModal = false;
	let showCreatePromptModal = false;
	let editingGroup: PromptGroupWithMappings | null = null;
	let editingPrompt: PersonaPrompt | null = null;
	let selectedGroupForAddPrompt: PromptGroupWithMappings | null = null;

	// Search with Fuse.js
	let fuse: Fuse<PersonaPrompt>;
	let filteredPrompts: PersonaPrompt[] = [];

	$: {
		fuse = new Fuse(personaPrompts, {
			keys: ['title', 'command', 'content'],
			threshold: 0.3
		});
	}

	$: {
		let results = searchQuery
			? fuse.search(searchQuery).map((r) => r.item)
			: personaPrompts;

		if (promptTypeFilter !== 'all') {
			if (promptTypeFilter === 'general') {
				results = results.filter((p) => p.prompt_type === null);
			} else {
				results = results.filter((p) => p.prompt_type === promptTypeFilter);
			}
		}

		filteredPrompts = results;
	}

	// Load data
	const loadData = async () => {
		try {
			const token = localStorage.token;
			promptGroups = await getPromptGroups(token);
			personaPrompts = await getPersonaPrompts(token);
			defaultGroupId = await getDefaultPromptGroup(token);
		} catch (error) {
			console.error('Failed to load persona data:', error);
			toast.error($i18n.t('데이터를 불러오는데 실패했습니다.'));
		}
		loaded = true;
	};

	onMount(() => {
		loadData();
	});

	// Group handlers
	const handleCreateGroup = async (e: CustomEvent<{ name: string; description: string }>) => {
		try {
			const { name, description } = e.detail;
			const newGroup = await createPromptGroup(localStorage.token, { name, description });
			promptGroups = [...promptGroups, newGroup];
			toast.success($i18n.t('그룹이 생성되었습니다.'));
		} catch (error) {
			console.error('Failed to create group:', error);
			toast.error($i18n.t('그룹 생성에 실패했습니다.'));
		}
	};

	const handleUpdateGroup = async (e: CustomEvent<{ name: string; description: string }>) => {
		if (!editingGroup) return;
		try {
			const { name, description } = e.detail;
			const updated = await updatePromptGroup(localStorage.token, editingGroup.id, { name, description });
			promptGroups = promptGroups.map((g) => (g.id === editingGroup!.id ? { ...g, ...updated } : g));
			editingGroup = null;
			toast.success($i18n.t('그룹이 수정되었습니다.'));
		} catch (error) {
			console.error('Failed to update group:', error);
			toast.error($i18n.t('그룹 수정에 실패했습니다.'));
		}
	};

	const handleDeleteGroup = async (group: PromptGroupWithMappings) => {
		if (!confirm($i18n.t('정말로 이 그룹을 삭제하시겠습니까?'))) return;
		try {
			await deletePromptGroup(localStorage.token, group.id);
			promptGroups = promptGroups.filter((g) => g.id !== group.id);
			if (defaultGroupId === group.id) {
				defaultGroupId = null;
			}
			toast.success($i18n.t('그룹이 삭제되었습니다.'));
		} catch (error) {
			console.error('Failed to delete group:', error);
			toast.error($i18n.t('그룹 삭제에 실패했습니다.'));
		}
	};

	const handleSetDefaultGroup = async (group: PromptGroupWithMappings) => {
		try {
			await setDefaultPromptGroup(localStorage.token, group.id);
			defaultGroupId = group.id;
			toast.success($i18n.t('기본 그룹이 설정되었습니다.'));
		} catch (error) {
			console.error('Failed to set default group:', error);
			toast.error($i18n.t('기본 그룹 설정에 실패했습니다.'));
		}
	};

	// Prompt handlers
	const handleCreatePrompt = async (e: CustomEvent<PersonaPrompt>) => {
		try {
			const newPrompt = await createPersonaPrompt(localStorage.token, e.detail);
			personaPrompts = [...personaPrompts, newPrompt];
			toast.success($i18n.t('프롬프트가 생성되었습니다.'));
		} catch (error) {
			console.error('Failed to create prompt:', error);
			toast.error($i18n.t('프롬프트 생성에 실패했습니다.'));
		}
	};

	const handleUpdatePrompt = async (e: CustomEvent<PersonaPrompt>) => {
		if (!editingPrompt) return;
		try {
			const updated = await updatePersonaPrompt(localStorage.token, editingPrompt.command, e.detail);
			personaPrompts = personaPrompts.map((p) => (p.command === editingPrompt!.command ? updated : p));
			editingPrompt = null;
			toast.success($i18n.t('프롬프트가 수정되었습니다.'));
		} catch (error) {
			console.error('Failed to update prompt:', error);
			toast.error($i18n.t('프롬프트 수정에 실패했습니다.'));
		}
	};

	const handleDeletePrompt = async (prompt: PersonaPrompt) => {
		if (!confirm($i18n.t('정말로 이 프롬프트를 삭제하시겠습니까?'))) return;
		try {
			await deletePersonaPrompt(localStorage.token, prompt.command);
			personaPrompts = personaPrompts.filter((p) => p.command !== prompt.command);
			// Also remove from all groups
			promptGroups = promptGroups.map((g) => ({
				...g,
				mappings: g.mappings.filter((m) => m.prompt_command !== prompt.command)
			}));
			toast.success($i18n.t('프롬프트가 삭제되었습니다.'));
		} catch (error) {
			console.error('Failed to delete prompt:', error);
			toast.error($i18n.t('프롬프트 삭제에 실패했습니다.'));
		}
	};

	// Group-Prompt mapping handlers
	const handleAddPromptsToGroup = async (e: CustomEvent<{ groupId: string; prompts: { command: string; order: number }[] }>) => {
		const { groupId, prompts } = e.detail;
		try {
			for (const { command, order } of prompts) {
				await addPromptToGroup(localStorage.token, groupId, command, order);
			}
			// Refresh groups
			promptGroups = await getPromptGroups(localStorage.token);
			selectedGroupForAddPrompt = null;
			toast.success($i18n.t('프롬프트가 그룹에 추가되었습니다.'));
		} catch (error) {
			console.error('Failed to add prompts to group:', error);
			toast.error($i18n.t('프롬프트 추가에 실패했습니다.'));
		}
	};

	const handleRemovePromptFromGroup = async (e: CustomEvent<{ group: PromptGroupWithMappings; prompt: PersonaPrompt }>) => {
		const { group, prompt } = e.detail;
		try {
			await removePromptFromGroup(localStorage.token, group.id, prompt.command);
			promptGroups = promptGroups.map((g) =>
				g.id === group.id
					? { ...g, mappings: g.mappings.filter((m) => m.prompt_command !== prompt.command) }
					: g
			);
			toast.success($i18n.t('프롬프트가 그룹에서 제거되었습니다.'));
		} catch (error) {
			console.error('Failed to remove prompt from group:', error);
			toast.error($i18n.t('프롬프트 제거에 실패했습니다.'));
		}
	};

	const handleEditPrompt = (e: CustomEvent<PersonaPrompt>) => {
		editingPrompt = e.detail;
		showCreatePromptModal = true;
	};
</script>

<div class="flex flex-col gap-6">
	<!-- Header -->
	<div>
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
			{$i18n.t('페르소나 프롬프트 설정')}
		</h2>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
			{$i18n.t('학생 맞춤형 응답을 위한 페르소나 기반 시스템 프롬프트를 관리합니다.')}
		</p>
	</div>

	{#if !loaded}
		<div class="flex justify-center py-8">
			<Spinner className="size-6" />
		</div>
	{:else}
		<!-- Default Group Setting -->
		<div class="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<div>
					<h3 class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('기본 프롬프트 그룹')}
					</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						{$i18n.t('모든 채팅에 기본으로 적용될 프롬프트 그룹입니다.')}
					</p>
				</div>
				<select
					class="px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
					value={defaultGroupId ?? ''}
					on:change={(e) => {
						const groupId = e.currentTarget.value || null;
						if (groupId) {
							const group = promptGroups.find((g) => g.id === groupId);
							if (group) handleSetDefaultGroup(group);
						} else {
							setDefaultPromptGroup(localStorage.token, null).then(() => {
								defaultGroupId = null;
							});
						}
					}}
				>
					<option value="">{$i18n.t('없음')}</option>
					{#each promptGroups as group}
						<option value={group.id}>{group.name}</option>
					{/each}
				</select>
			</div>
		</div>

		<!-- Prompt Groups Section -->
		<div class="space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-sm font-medium text-gray-900 dark:text-white">
					{$i18n.t('프롬프트 그룹 관리')}
				</h3>
				<button
					type="button"
					class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
					on:click={() => {
						editingGroup = null;
						showCreateGroupModal = true;
					}}
				>
					<Plus className="size-4" />
					{$i18n.t('새 그룹')}
				</button>
			</div>

			{#if promptGroups.length === 0}
				<div class="p-8 text-center border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-12 mx-auto text-gray-300 dark:text-gray-600 mb-3">
						<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
					</svg>
					<p class="text-gray-500 dark:text-gray-400 text-sm">
						{$i18n.t('프롬프트 그룹이 없습니다')}
					</p>
					<button
						type="button"
						class="mt-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
						on:click={() => {
							editingGroup = null;
							showCreateGroupModal = true;
						}}
					>
						+ {$i18n.t('첫 번째 그룹 만들기')}
					</button>
				</div>
			{:else}
				<div class="space-y-2">
					{#each promptGroups as group (group.id)}
						<PromptGroupItem
							{group}
							prompts={personaPrompts}
							bind:expanded={expandedGroups[group.id]}
							isDefault={defaultGroupId === group.id}
							on:edit={(e) => {
								editingGroup = e.detail;
								showCreateGroupModal = true;
							}}
							on:delete={(e) => handleDeleteGroup(e.detail)}
							on:setDefault={(e) => handleSetDefaultGroup(e.detail)}
							on:addPrompt={(e) => {
								selectedGroupForAddPrompt = e.detail;
								showAddPromptModal = true;
							}}
							on:removePrompt={handleRemovePromptFromGroup}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Persona Prompts Section -->
		<div class="space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-sm font-medium text-gray-900 dark:text-white">
					{$i18n.t('페르소나 프롬프트 목록')}
				</h3>
				<button
					type="button"
					class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
					on:click={() => {
						editingPrompt = null;
						showCreatePromptModal = true;
					}}
				>
					<Plus className="size-4" />
					{$i18n.t('새 프롬프트')}
				</button>
			</div>

			<!-- Search & Filter -->
			<div class="flex gap-2">
				<div class="flex-1 flex items-center border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 px-3">
					<Search className="size-4 text-gray-400" />
					<input
						type="text"
						class="flex-1 px-2 py-2 text-sm bg-transparent outline-none"
						placeholder={$i18n.t('프롬프트 검색...')}
						bind:value={searchQuery}
					/>
					{#if searchQuery}
						<button
							type="button"
							class="p-0.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition"
							on:click={() => (searchQuery = '')}
						>
							<XMark className="size-3.5" />
						</button>
					{/if}
				</div>

				<select
					class="px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg outline-none"
					bind:value={promptTypeFilter}
				>
					<option value="all">{$i18n.t('전체')}</option>
					<option value="general">{$i18n.t('일반')}</option>
					<option value="base">base</option>
					<option value="proficiency">proficiency</option>
					<option value="style">style</option>
				</select>
			</div>

			<!-- Prompt List -->
			<div class="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
				{#if filteredPrompts.length === 0}
					<div class="p-8 text-center">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-12 mx-auto text-gray-300 dark:text-gray-600 mb-3">
							<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
						</svg>
						<p class="text-gray-500 dark:text-gray-400 text-sm">
							{searchQuery || promptTypeFilter !== 'all'
								? $i18n.t('검색 결과가 없습니다')
								: $i18n.t('페르소나 프롬프트가 없습니다')}
						</p>
						{#if !searchQuery && promptTypeFilter === 'all'}
							<button
								type="button"
								class="mt-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
								on:click={() => {
									editingPrompt = null;
									showCreatePromptModal = true;
								}}
							>
								+ {$i18n.t('첫 번째 프롬프트 만들기')}
							</button>
						{/if}
					</div>
				{:else}
					<div class="divide-y divide-gray-100 dark:divide-gray-800">
						{#each filteredPrompts as prompt (prompt.command)}
							<PromptItem
								{prompt}
								on:edit={handleEditPrompt}
								on:delete={(e) => handleDeletePrompt(e.detail)}
							/>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<!-- Modals -->
<CreatePromptGroupModal
	bind:show={showCreateGroupModal}
	editMode={!!editingGroup}
	group={editingGroup}
	on:create={handleCreateGroup}
	on:update={handleUpdateGroup}
	on:close={() => {
		showCreateGroupModal = false;
		editingGroup = null;
	}}
/>

<CreatePersonaPromptModal
	bind:show={showCreatePromptModal}
	editMode={!!editingPrompt}
	prompt={editingPrompt}
	on:create={handleCreatePrompt}
	on:update={handleUpdatePrompt}
	on:close={() => {
		showCreatePromptModal = false;
		editingPrompt = null;
	}}
/>

{#if selectedGroupForAddPrompt}
	<AddPromptToGroupModal
		bind:show={showAddPromptModal}
		groupId={selectedGroupForAddPrompt.id}
		existingMappings={selectedGroupForAddPrompt.mappings.map((m) => m.prompt_command)}
		availablePrompts={personaPrompts}
		on:add={handleAddPromptsToGroup}
		on:close={() => {
			showAddPromptModal = false;
			selectedGroupForAddPrompt = null;
		}}
	/>
{/if}
