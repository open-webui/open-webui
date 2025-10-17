<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import WorkspaceModelEditor from '$lib/components/admin/Users/Groups/WorkspaceModelEditor.svelte';

	import { getModels, updateModelById as updateModel } from '$lib/apis/models';
	import { getKnowledgeBases } from '$lib/apis/knowledge'; 
	import { getPrompts } from '$lib/apis/prompts';
	import { getTools } from '$lib/apis/tools'; 
	import { updateGroupById, getGroupById } from '$lib/apis/groups';
	import { updateModelById, toggleModelById } from '$lib/apis/models';

	export let show = false;
	export let group = null;
	export let onSubmit: Function = () => {};

	// All available items from APIs
	let allModels = [];
	let allKnowledge = [];
	let allPrompts = [];
	let allTools = [];

	let selectedTab = 'models';
	let searchQuery = '';
	let loading = false;
	let initialized = false;
	let resourcesLoaded = false;

	// Model editor state
	let showModelEditor = false;
	let editingModel = null;

	// Selected items for each category - store complete objects
	let selectedModels = [];
	let selectedKnowledge = [];
	let selectedPrompts = [];
	let selectedTools = [];

	// Store just IDs for comparison
	let selectedModelIds = [];
	let selectedKnowledgeIds = [];
	let selectedPromptIds = [];
	let selectedToolIds = [];

	// Full group data
	let fullGroup = null;

	const tabs = [
		{ id: 'models', label: 'Models' },
		{ id: 'knowledge', label: 'Knowledge' },
		{ id: 'prompts', label: 'Prompts' },
		{ id: 'tools', label: 'Tools' }
	];

	// Reactive current data based on selected tab
	$: currentData = (() => {
		if (!group?.id) return [];
		
		switch (selectedTab) {
			case 'models':
				return allModels.filter(model => 
					model.access_control?.read?.group_ids?.includes(group.id)
				);
			case 'knowledge':
				return allKnowledge.filter(kb => 
					kb.access_control?.read?.group_ids?.includes(group.id)
				);
			case 'prompts':
				return allPrompts.filter(prompt => 
					prompt.access_control?.read?.group_ids?.includes(group.id)
				);
			case 'tools':
				return allTools.filter(tool => 
					tool.access_control?.read?.group_ids?.includes(group.id)
				);
			default:
				return [];
		}
	})();

	// Reactive total count based on selected tab (filtered by group)
	$: totalCount = (() => {
		if (!group?.id) return 0;
		
		switch (selectedTab) {
			case 'models':
				return allModels.filter(model => 
					model.access_control?.read?.group_ids?.includes(group.id)
				).length;
			case 'knowledge':
				return allKnowledge.filter(kb => 
					kb.access_control?.read?.group_ids?.includes(group.id)
				).length;
			case 'prompts':
				return allPrompts.filter(prompt => 
					prompt.access_control?.read?.group_ids?.includes(group.id)
				).length;
			case 'tools':
				return allTools.filter(tool => 
					tool.access_control?.read?.group_ids?.includes(group.id)
				).length;
			default:
				return 0;
		}
	})();

	// Reactive current selected IDs based on selected tab
	$: currentSelected = (() => {
		switch (selectedTab) {
			case 'models':
				return selectedModelIds;
			case 'knowledge':
				return selectedKnowledgeIds;
			case 'prompts':
				return selectedPromptIds;
			case 'tools':
				return selectedToolIds;
			default:
				return [];
		}
	})();

	// Reactive filtered data
	$: filteredData = currentData.filter((item) => {
		const searchLower = searchQuery.toLowerCase();
		return (
			item.name?.toLowerCase().includes(searchLower) ||
			item.title?.toLowerCase().includes(searchLower) ||
			item.command?.toLowerCase().includes(searchLower) ||
			item.description?.toLowerCase().includes(searchLower) ||
			item.meta?.description?.toLowerCase().includes(searchLower) ||
			item.id?.toLowerCase().includes(searchLower)
		);
	});

	const toggleItem = (itemId) => {
		const item = currentData.find(i => i.id === itemId);
		if (!item) return;

		switch (selectedTab) {
			case 'models':
				if (selectedModelIds.includes(itemId)) {
					selectedModelIds = selectedModelIds.filter((id) => id !== itemId);
					selectedModels = selectedModels.filter((m) => m.id !== itemId);
				} else {
					selectedModelIds = [...selectedModelIds, itemId];
					selectedModels = [...selectedModels, item];
				}
				break;
			case 'knowledge':
				if (selectedKnowledgeIds.includes(itemId)) {
					selectedKnowledgeIds = selectedKnowledgeIds.filter((id) => id !== itemId);
					selectedKnowledge = selectedKnowledge.filter((k) => k.id !== itemId);
				} else {
					selectedKnowledgeIds = [...selectedKnowledgeIds, itemId];
					selectedKnowledge = [...selectedKnowledge, item];
				}
				break;
			case 'prompts':
				if (selectedPromptIds.includes(itemId)) {
					selectedPromptIds = selectedPromptIds.filter((id) => id !== itemId);
					selectedPrompts = selectedPrompts.filter((p) => p.id !== itemId);
				} else {
					selectedPromptIds = [...selectedPromptIds, itemId];
					selectedPrompts = [...selectedPrompts, item];
				}
				break;
			case 'tools':
				if (selectedToolIds.includes(itemId)) {
					selectedToolIds = selectedToolIds.filter((id) => id !== itemId);
					selectedTools = selectedTools.filter((t) => t.id !== itemId);
				} else {
					selectedToolIds = [...selectedToolIds, itemId];
					selectedTools = [...selectedTools, item];
				}
				break;
		}
	};

	const submitHandler = async () => {
		loading = true;

		try {
			// Create a set of all model IDs that need access (including base models)
			const modelIdsNeedingAccess = new Set(selectedModelIds);
			
			// Add base models for all selected models
			for (const modelId of selectedModelIds) {
				const model = allModels.find(m => m.id === modelId);
				if (model?.base_model_id) {
					modelIdsNeedingAccess.add(model.base_model_id);
					console.log(`Added base model ${model.base_model_id} for derived model ${modelId}`);
				}
			}

			console.log('Models needing access:', Array.from(modelIdsNeedingAccess));

			// Update access control for ALL models (derived + base)
			for (const model of allModels) {
				const shouldHaveAccess = modelIdsNeedingAccess.has(model.id);
				const currentlyHasAccess = model.access_control?.read?.group_ids?.includes(group.id) || false;
				
				if (shouldHaveAccess !== currentlyHasAccess) {
					const updatedGroupIds = shouldHaveAccess
						? [...(model.access_control?.read?.group_ids || []), group.id]
						: (model.access_control?.read?.group_ids || []).filter(id => id !== group.id);
					
					console.log(`Updating model ${model.id}: shouldHaveAccess=${shouldHaveAccess}, currentlyHasAccess=${currentlyHasAccess}`);
					
					await updateModelById(localStorage.token, model.id, {
						...model,
						access_control: {
							...model.access_control,
							read: {
								...model.access_control?.read,
								group_ids: [...new Set(updatedGroupIds)] // Remove duplicates
							}
						}
					});
				}
			}

			// Update the group workspace (only store derived model IDs, not base models)
			await updateGroupById(localStorage.token, group.id, {
				...fullGroup,
				workspace: {
					models: selectedModelIds, // Only the models user selected
					knowledge: selectedKnowledgeIds,
					prompts: selectedPromptIds,
					tools: selectedToolIds
				}
			});

			toast.success($i18n.t('Workspace updated successfully'));
			await onSubmit();
		} catch (error) {
			toast.error($i18n.t('Failed to update workspace'));
			console.error('Error in submitHandler:', error);
		}

		loading = false;
		show = false;
	};

	const init = async () => {
		if (!group?.id) {
			console.warn('No group ID provided to init');
			return;
		}

		loading = true;
		initialized = false;
		
		try {
			// Fetch the full group details
			fullGroup = await getGroupById(localStorage.token, group.id);
			
			// Pre-select items that have this group in their access control
			selectedModels = allModels.filter(model => 
				model.access_control?.read?.group_ids?.includes(group.id)
			);
			selectedModelIds = selectedModels.map(model => model.id);
			
			selectedKnowledge = allKnowledge.filter(kb => 
				kb.access_control?.read?.group_ids?.includes(group.id)
			);
			selectedKnowledgeIds = selectedKnowledge.map(kb => kb.id);
			
			selectedPrompts = allPrompts.filter(prompt => 
				prompt.access_control?.read?.group_ids?.includes(group.id)
			);
			selectedPromptIds = selectedPrompts.map(prompt => prompt.id);
			
			selectedTools = allTools.filter(tool => 
				tool.access_control?.read?.group_ids?.includes(group.id)
			);
			selectedToolIds = selectedTools.map(tool => tool.id);
			
			initialized = true;
		} catch (error) {
			console.error('Error loading group:', error);
			toast.error($i18n.t('Failed to load group details'));
		} finally {
			loading = false;
		}
	};

	// Handle modal open/close and initialization
	$: if (show && group && !initialized && resourcesLoaded) {
		init();
	} else if (!show) {
		// Reset state when modal closes
		initialized = false;
		selectedModels = [];
		selectedKnowledge = [];
		selectedPrompts = [];
		selectedTools = [];
		selectedModelIds = [];
		selectedKnowledgeIds = [];
		selectedPromptIds = [];
		selectedToolIds = [];
		fullGroup = null;
		searchQuery = '';
		selectedTab = 'models';
		showModelEditor = false;
		editingModel = null;
	}

	onMount(async () => {
		loading = true;
		
		try {
			allModels = await getModels(localStorage.token);
			allKnowledge = await getKnowledgeBases(localStorage.token);
			allPrompts = await getPrompts(localStorage.token);
			allTools = await getTools(localStorage.token);
			
			resourcesLoaded = true;
		} catch (error) {
			console.error('Error loading resources:', error);
			toast.error($i18n.t('Failed to load workspace resources'));
		} finally {
			loading = false;
		}
	});
</script>

<Modal size="lg" bind:show>
	<div class="rounded-2xl overflow-hidden">
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
			<div class="font-primary">
				<div class="text-lg font-medium text-gray-650 dark:text-gray-400">Update Workspace</div>
				<div class="text-lg font-primary">{group?.name || 'Group'}</div>
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					{#if !initialized || !resourcesLoaded}
						<!-- Show loading state -->
						<div class="text-center py-16">
							<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"></div>
							<div class="mt-2 text-sm text-gray-500">
								{!resourcesLoaded ? $i18n.t('Loading resources...') : $i18n.t('Loading workspace...')}
							</div>
						</div>
					{:else}
						<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
							<!-- Sidebar Tabs -->
							<div
								class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
							>
								{#each tabs as tab}
									<button
										class="px-0.5 py-1 max-w-fit w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
										tab.id
											? 'text-[#57068c] dark:text-white'
											: 'text-gray-600 dark:text-gray-600 hover:text-[#57068c] dark:hover:text-white'}"
										on:click={() => {
											selectedTab = tab.id;
											searchQuery = '';
										}}
										type="button"
									>
										<div class="self-center mr-2">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													fill-rule="evenodd"
													d="M6.955 1.45A.5.5 0 0 1 7.452 1h1.096a.5.5 0 0 1 .497.45l.17 1.699c.484.12.94.312 1.356.562l1.321-1.081a.5.5 0 0 1 .67.033l.774.775a.5.5 0 0 1 .034.67l-1.08 1.32c.25.417.44.873.561 1.357l1.699.17a.5.5 0 0 1 .45.497v1.096a.5.5 0 0 1-.45.497l-1.699.17c-.12.484-.312.94-.562 1.356l1.082 1.322a.5.5 0 0 1-.034.67l-.774.774a.5.5 0 0 1-.67.033l-1.322-1.08c-.416.25-.872.44-1.356.561l-.17 1.699a.5.5 0 0 1-.497.45H7.452a.5.5 0 0 1-.497-.45l-.17-1.699a4.973 4.973 0 0 1-1.356-.562L4.108 13.37a.5.5 0 0 1-.67-.033l-.774-.775a.5.5 0 0 1-.034-.67l1.08-1.32a4.971 4.971 0 0 1-.561-1.357l-1.699-.17A.5.5 0 0 1 1 8.548V7.452a.5.5 0 0 1 .45-.497l1.699-.17c.12-.484.312-.94.562-1.356L2.629 4.107a.5.5 0 0 1 .034-.67l.774-.774a.5.5 0 0 1 .67-.033L5.43 3.71a4.97 4.97 0 0 1 1.356-.561l.17-1.699ZM6 8c0 .538.212 1.026.558 1.385l.057.057a2 2 0 0 0 2.828-2.828l-.058-.056A2 2 0 0 0 6 8Z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
										<div class="self-center">
											{$i18n.t(tab.label)}
											({tab.id === 'models' ? allModels.filter(m => m.access_control?.read?.group_ids?.includes(group.id)).length : 
											  tab.id === 'knowledge' ? allKnowledge.filter(k => k.access_control?.read?.group_ids?.includes(group.id)).length : 
											  tab.id === 'prompts' ? allPrompts.filter(p => p.access_control?.read?.group_ids?.includes(group.id)).length : 
											  allTools.filter(t => t.access_control?.read?.group_ids?.includes(group.id)).length})
										</div>
									</button>
								{/each}
							</div>

							<!-- Content Area -->
							<div
								class="flex-1 mt-1 lg:mt-1 lg:h-[22rem] lg:max-h-[22rem] overflow-y-auto scrollbar-hidden"
							>
								<!-- Search Bar -->
								<div class="mb-3">
									<div class="flex flex-1">
										<div class="self-center ml-1 mr-3">
											<Search className="size-3.5" />
										</div>
										<input
											class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
											bind:value={searchQuery}
											placeholder={$i18n.t('Search {{tab}}', { tab: selectedTab })}
										/>
									</div>
								</div>

								<!-- Items List -->
								<div class="gap-2 grid lg:grid-cols-1">
									{#each filteredData as item}
										{@const isSelected = currentSelected.includes(item.id)}
										{@const itemName = item.name || item.title}
										
										{#if selectedTab === 'models'}
											<!-- Model Card Display -->
											<div
												class="flex flex-col cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition"
											>
												<div class="flex gap-4 mt-0.5 mb-0.5">
													<!-- Model Avatar -->
													<div class="w-[44px]">
														<div class="rounded-full object-cover {item.is_active ? '' : 'opacity-50 dark:opacity-50'}">
															<img
																src={item?.meta?.profile_image_url ?? '/static/favicon.png'}
																alt="model profile"
																class="rounded-full w-full h-auto object-cover"
															/>
														</div>
													</div>
													
													<!-- Model Info -->
													<div class="flex-1 self-center {item.is_active ? '' : 'text-gray-500'}">
														<Tooltip
															content={item?.meta?.description ?? item.id}
															className="w-fit"
															placement="top-start"
														>
															<div class="font-semibold line-clamp-1">{itemName}</div>
														</Tooltip>

														<div class="flex gap-1 text-xs overflow-hidden">
															<div class="line-clamp-1">
																{#if (item?.meta?.description ?? '').trim()}
																	{item?.meta?.description}
																{:else}
																	{item.id}
																{/if}
															</div>
														</div>
													</div>
												</div>

												<!-- Model Footer -->
												<div class="flex justify-between items-center -mb-0.5 px-0.5">
													<div class="text-xs mt-0.5">
														<Tooltip
															content={item?.user?.email ?? $i18n.t('Deleted User')}
															className="flex shrink-0"
															placement="top-start"
														>
															<div class="shrink-0 text-gray-500">
																{$i18n.t('By {{name}}', { 
																	name: item?.user?.name || item?.user?.email || $i18n.t('Unknown') 
																})}
															</div>
														</Tooltip>
													</div>

													<!-- Action Buttons -->
													<div class="flex flex-row gap-0.5 items-center">
														<!-- Edit Button -->
														<Tooltip content={$i18n.t('Edit')}>
															<button
																class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																type="button"
																on:click|stopPropagation={() => {
																	editingModel = item;
																	showModelEditor = true;
																}}
															>
																<svg
																	xmlns="http://www.w3.org/2000/svg"
																	fill="none"
																	viewBox="0 0 24 24"
																	stroke-width="1.5"
																	stroke="currentColor"
																	class="w-4 h-4"
																>
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
																	/>
																</svg>
															</button>
														</Tooltip>

														<!-- Enable/Disable Toggle -->
														<div class="ml-1" on:click|stopPropagation on:keydown|stopPropagation role="button" tabindex="-1">
															<Tooltip content={item.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
																<Switch
																	bind:state={item.is_active}
																	on:change={async (e) => {
																		e.stopPropagation();
																		await toggleModelById(localStorage.token, item.id);
																		// Refresh the models list
																		allModels = await getModels(localStorage.token);
																	}}
																/>
															</Tooltip>
														</div>
													</div>
												</div>
											</div>
										{:else if selectedTab === 'knowledge'}
											<!-- Knowledge Base Display -->
											<div
												class="flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition {isSelected ? 'bg-black/5 dark:bg-white/5' : ''}"
												on:click={() => toggleItem(item.id)}
												on:keydown={(e) => {
													if (e.key === 'Enter' || e.key === ' ') {
														toggleItem(item.id);
													}
												}}
												role="button"
												tabindex="0"
											>
												<div class="w-full">
													<div class="flex justify-between items-start">
														<div class="flex-1 min-w-0">
															<div class="font-semibold line-clamp-1">{itemName}</div>
															<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
																{item.description || ''}
															</div>
															{#if item.user}
																<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
																	{$i18n.t('By {{name}}', { name: item.user.name || item.user.email })}
																</div>
															{/if}
														</div>

														<!-- Toggle Button -->
														<div class="flex-shrink-0">
															<Tooltip content={isSelected ? $i18n.t('Remove') : $i18n.t('Add')}>
																<button
																	class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	type="button"
																	on:click|stopPropagation={() => toggleItem(item.id)}
																>
																	{#if isSelected}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 16 16"
																			fill="currentColor"
																			class="w-4 h-4"
																		>
																			<path
																				d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
																			/>
																		</svg>
																	{:else}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 16 16"
																			fill="currentColor"
																			class="w-4 h-4"
																		>
																			<path
																				d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
																			/>
																		</svg>
																	{/if}
																</button>
															</Tooltip>
														</div>
													</div>
												</div>
											</div>
										{:else if selectedTab === 'prompts'}
											<!-- Prompt Display -->
											<div
												class="flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition {isSelected ? 'bg-black/5 dark:bg-white/5' : ''}"
												on:click={() => toggleItem(item.id)}
												on:keydown={(e) => {
													if (e.key === 'Enter' || e.key === ' ') {
														toggleItem(item.id);
													}
												}}
												role="button"
												tabindex="0"
											>
												<div class="w-full">
													<div class="flex justify-between items-start">
														<div class="flex-1 min-w-0">
															<div class="font-semibold text-sm line-clamp-1 capitalize">
																{itemName}
																{#if item.command}
																	<span class="text-gray-500 text-xs font-normal ml-1">
																		/{item.command}
																	</span>
																{/if}
															</div>
															{#if item.user}
																<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
																	{$i18n.t('By {{name}}', { name: item.user.name || item.user.email })}
																</div>
															{/if}
														</div>

														<!-- Toggle Button -->
														<div class="flex-shrink-0">
															<Tooltip content={isSelected ? $i18n.t('Remove') : $i18n.t('Add')}>
																<button
																	class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	type="button"
																	on:click|stopPropagation={() => toggleItem(item.id)}
																>
																	{#if isSelected}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 16 16"
																			fill="currentColor"
																			class="w-4 h-4"
																		>
																			<path
																				d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
																			/>
																		</svg>
																	{:else}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 16 16"
																			fill="currentColor"
																			class="w-4 h-4"
																		>
																			<path
																				d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
																			/>
																		</svg>
																	{/if}
																</button>
															</Tooltip>
														</div>
													</div>
												</div>
											</div>
										{:else if selectedTab === 'tools'}
											<!-- Tool Display -->
											<div
												class="flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition {isSelected ? 'bg-black/5 dark:bg-white/5' : ''}"
												on:click={() => toggleItem(item.id)}
												on:keydown={(e) => {
													if (e.key === 'Enter' || e.key === ' ') {
														toggleItem(item.id);
													}
												}}
												role="button"
												tabindex="0"
											>
												<div class="w-full">
													<div class="flex justify-between items-start">
														<div class="flex-1 min-w-0">
															<div class="font-semibold flex items-center gap-1.5">
																<div
																	class="text-xs font-bold px-1 rounded-sm uppercase line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
																>
																	TOOL
																</div>
																<div class="line-clamp-1">
																	{itemName}
																	<span class="text-gray-500 text-xs font-medium">{item.id}</span>
																</div>
															</div>
															<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1 mt-0.5">
																{item.meta?.description || item.description || ''}
															</div>
															{#if item.user}
																<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
																	{$i18n.t('By {{name}}', { name: item.user.name || item.user.email })}
																</div>
															{/if}
														</div>

														<!-- Toggle Button -->
														<div class="flex-shrink-0">
															<Tooltip content={isSelected ? $i18n.t('Remove') : $i18n.t('Add')}>
																<button
																	class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	type="button"
																	on:click|stopPropagation={() => toggleItem(item.id)}
																>
																	{#if isSelected}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 16 16"
																			fill="currentColor"
																			class="w-4 h-4"
																		>
																			<path
																				d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
																			/>
																		</svg>
																	{:else}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 16 16"
																			fill="currentColor"
																			class="w-4 h-4"
																		>
																			<path
																				d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
																			/>
																		</svg>
																	{/if}
																</button>
															</Tooltip>
														</div>
													</div>
												</div>
											</div>
										{/if}
									{:else}
										<div class="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
											{searchQuery
												? $i18n.t('No {{tab}} found matching search', { tab: selectedTab })
												: $i18n.t('No {{tab}} available', { tab: selectedTab })}
										</div>
									{/each}
								</div>
							</div>
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
							<button
								class="px-4.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
									? 'cursor-not-allowed'
									: ''}"
								type="submit"
								disabled={loading}
							>
								{$i18n.t('Save')}

								{#if loading}
									<div class="ml-2 self-center">
										<svg
											class="w-4 h-4"
											viewBox="0 0 24 24"
											fill="currentColor"
											xmlns="http://www.w3.org/2000/svg"
											><style>
												.spinner_ajPY {
													transform-origin: center;
													animation: spinner_AtaB 0.75s infinite linear;
												}
												@keyframes spinner_AtaB {
													100% {
														transform: rotate(360deg);
													}
												}
											</style><path
												d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
												opacity=".25"
											/><path
												d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
												class="spinner_ajPY"
											/></svg
										>
									</div>
								{/if}
							</button>
						</div>
					{/if}
				</form>
			</div>
		</div>
	</div>
</Modal>

<!-- WorkspaceModelEditor Modal -->
{#if showModelEditor && editingModel}
	<Modal size="lg" bind:show={showModelEditor}>
		<div class="rounded-2xl overflow-hidden">
			<div class="flex justify-between dark:text-gray-100 px-5 pt-4 mb-3">
				<div class="font-primary">
					<div class="text-lg font-medium">{$i18n.t('Edit Model for Workspace')}</div>
					<div class="text-sm text-gray-500">{editingModel.name}</div>
				</div>
				<button
					class="self-center"
					on:click={() => {
						showModelEditor = false;
						editingModel = null;
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-5 h-5"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</button>
			</div>

			<div class="px-5 pb-5 overflow-y-auto max-h-[70vh]">
				<WorkspaceModelEditor
					bind:show={showModelEditor}
					modelId={editingModel.id}
					groupId={group.id}
					onSubmit={async () => {
						toast.success($i18n.t('Model updated successfully'));
						// Refresh models list
						allModels = await getModels(localStorage.token);
						showModelEditor = false;
						editingModel = null;
					}}
					onClose={() => {
						showModelEditor = false;
						editingModel = null;
					}}
				/>
			</div>
		</div>
	</Modal>
{/if}