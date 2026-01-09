<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

import { getModels, getModelById, updateModelById as updateModel, updateModelById, toggleModelById } from '$lib/apis/models';
import { updateGroupById, getGroupById } from '$lib/apis/groups';

	export let show = false;
	export let group = null;
	export let onSubmit: Function = () => {};

	// All available items from APIs
	let allModels = [];

	let selectedTab = 'models';
	let searchQuery = '';
	let loading = false;
	let initialized = false;
	let resourcesLoaded = false;
	let showUnassigned = false; // Control collapse state for unassigned items

	// Model editor state
	let showModelEditor = false;
	let editingModel = null;

	// Edit spinner state
	let editingLoading = false;

	// Selected items for each category - store complete objects
	let selectedModels = [];

	// Store just IDs for comparison
	let selectedModelIds = [];

	// Full group data
	let fullGroup = null;

	const tabs = [
		{ id: 'models', label: 'Models' }
	];

	// Reactive assigned items (items that have access to this group)
	$: assignedData = (() => {
		if (!group?.id) return [];
		
		return allModels.filter(model => 
			model.access_control?.read?.group_ids?.includes(group.id)
		);
	})();

	// Reactive unassigned items (items that don't have access to this group)
	$: unassignedData = (() => {
		if (!group?.id) return [];
		
		return allModels.filter(model => 
			!model.access_control?.read?.group_ids?.includes(group.id)
		);
	})();

	// Combine for backwards compatibility
	$: currentData = [...assignedData, ...unassignedData];

	// Reactive total count based on selected tab (filtered by group)
	$: totalCount = (() => {
		if (!group?.id) return 0;
		
		return allModels.filter(model => 
			model.access_control?.read?.group_ids?.includes(group.id)
		).length;
	})();

	// Reactive current selected IDs based on selected tab
	$: currentSelected = selectedModelIds;

	// Reactive filtered data - separate for assigned and unassigned
	$: filteredAssignedData = assignedData.filter((item) => {
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

	$: filteredUnassignedData = unassignedData.filter((item) => {
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

	// Combine for backwards compatibility
	$: filteredData = [...filteredAssignedData, ...filteredUnassignedData];

	const toggleItem = (itemId) => {
		const item = currentData.find(i => i.id === itemId);
		if (!item) return;

		if (selectedModelIds.includes(itemId)) {
			selectedModelIds = selectedModelIds.filter((id) => id !== itemId);
			selectedModels = selectedModels.filter((m) => m.id !== itemId);
		} else {
			selectedModelIds = [...selectedModelIds, itemId];
			selectedModels = [...selectedModels, item];
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
					models: selectedModelIds // Only the models user selected
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
		selectedModelIds = [];
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
							<div class="flex justify-center">
								<Spinner />
							</div>
							<div class="mt-2 text-sm text-gray-500">
								{!resourcesLoaded ? $i18n.t('Loading resources...') : $i18n.t('Loading workspace...')}
							</div>
						</div>
					{:else}
						<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
							<!-- Sidebar Tabs -->
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
											placeholder={$i18n.t('Search models')}
										/>
									</div>
								</div>

								<!-- Items List -->
								<div class="flex flex-col gap-3">
									<!-- Assigned Items Section -->
									{#if filteredAssignedData.length > 0}
										<div>
											<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-1">
												{$i18n.t('Assigned')} ({filteredAssignedData.length})
											</div>
											<div class="gap-2 grid lg:grid-cols-1">
												{#each filteredAssignedData as item}
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
																on:click|stopPropagation={async () => {
																	editingLoading = true;

																	try {
																		// Fetch full model details BEFORE opening modal
																		const fullModel = await getModelById(localStorage.token, item.id);

																		editingModel = fullModel;
																		showModelEditor = true;
																	} catch (error) {
																		console.error('Failed to load model details:', error);
																		toast.error($i18n.t('Failed to load model details'));
																	} finally {
																		editingLoading = false;
																	}
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
										{/if}
									{/each}
								</div>
							</div>
						{:else}
							<div class="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
								{searchQuery
									? $i18n.t('No assigned models found matching search')
									: $i18n.t('No assigned models')}
							</div>
						{/if}

						<!-- All Other Items Section (Collapsible) -->
						{#if filteredUnassignedData.length > 0}
							<div class="mt-4">
								<button
									type="button"
									on:click={() => showUnassigned = !showUnassigned}
									class="w-full flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-1 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition"
								>
									<span>{$i18n.t('All Other models')} ({filteredUnassignedData.length})</span>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-5 h-5 transition-transform {showUnassigned ? 'rotate-180' : ''}"
									>
										<path
											fill-rule="evenodd"
											d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
								
								{#if showUnassigned}
									<div class="gap-2 grid lg:grid-cols-1">
										{#each filteredUnassignedData as item}
											{@const isSelected = currentSelected.includes(item.id)}
											{@const itemName = item.name || item.title}
											
											{#if selectedTab === 'models'}
												<!-- Model Card Display -->
												<div
													class="flex flex-col cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition"
													on:click={() => toggleItem(item.id)}
													on:keydown={(e) => {
														if (e.key === 'Enter' || e.key === ' ') {
															toggleItem(item.id);
														}
													}}
													role="button"
													tabindex="0"
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
														
														<!-- Action Buttons -->
														<div class="flex flex-row gap-0.5 items-center">
															<!-- Edit Button -->
															<Tooltip content={$i18n.t('Edit')}>
																<button
																	class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	type="button"
																	on:click|stopPropagation={async () => {
																		editingLoading = true;

																		try {
																			// Fetch full model details BEFORE opening modal
																			const fullModel = await getModelById(localStorage.token, item.id);

																			editingModel = fullModel;
																			showModelEditor = true;
																		} catch (error) {
																			console.error('Failed to load model details:', error);
																			toast.error($i18n.t('Failed to load model details'));
																		} finally {
																			editingLoading = false;
																		}
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

															<!-- Add to Group Button -->
															<Tooltip content={$i18n.t('Add to group')}>
																<button
																	class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	type="button"
																	on:click|stopPropagation={async () => {
																		// Get current access control or create default
																		const currentAccessControl = item.access_control || {
																			read: { group_ids: [], user_ids: [] },
																			write: { group_ids: [], user_ids: [] }
																		};

																		// Add current group to read access if not already there
																		if (!currentAccessControl.read.group_ids.includes(group.id)) {
																			currentAccessControl.read.group_ids = [
																				...currentAccessControl.read.group_ids,
																				group.id
																			];

																			// Update the model with the complete object, following ModelEditor pattern
																			const result = await updateModelById(localStorage.token, item.id, {
																				...item,
																				access_control: currentAccessControl
																			});

																			if (result) {
																				toast.success($i18n.t('Model added to group'));
																				// Refresh the models list to update the UI
																				allModels = await getModels(localStorage.token);
																				// Re-initialize to update the selected items
																				await init();
																			}
																		} else {
																			toast.info($i18n.t('Model already in group'));
																		}
																	}}
																>
																	<svg
																		xmlns="http://www.w3.org/2000/svg"
																		fill="none"
																		viewBox="0 0 24 24"
																		stroke-width="2"
																		stroke="currentColor"
																		class="w-4 h-4"
																	>
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			d="M12 4.5v15m7.5-7.5h-15"
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
													</div>
												</div>
											{/if}
										{/each}
									</div>
								{/if}
							</div>
						{/if}

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
										<div class="m-auto">
											<Spinner />
										</div>
									</div>
								{/if}
							</button>
						</div>
					</div>
				</div>
			</div>
					{/if}
				</form>
			</div>
		</div>
	</div>
{#if editingLoading}
	<div class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40">
		<div class="flex flex-col items-center gap-3 bg-white dark:bg-gray-900 px-6 py-5 rounded-xl">
			<Spinner />
		</div>
	</div>
{/if}
</Modal>

<!-- Model Editor Modal -->
{#if showModelEditor && editingModel}
	<Modal size="lg" bind:show={showModelEditor}>
		<div class="rounded-2xl overflow-hidden bg-white dark:bg-gray-900 dark:text-gray-100">
			<div class="flex justify-between dark:text-gray-100 px-5 pt-4 mb-3">
				<div class="font-primary">
					<div class="text-lg font-medium">Edit Model</div>
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
				<ModelEditor
					model={editingModel}
					edit={true}
					onSubmit={async (modelInfo) => {
						const res = await updateModel(localStorage.token, editingModel.id, modelInfo);
						if (res) {
							toast.success($i18n.t('Model updated successfully'));
							// Refresh models list
							allModels = await getModels(localStorage.token);
							showModelEditor = false;
							editingModel = null;
						}
					}}
					onBack={() => {
						showModelEditor = false;
						editingModel = null;
					}}
				/>
			</div>
		</div>
	</Modal>
{/if}