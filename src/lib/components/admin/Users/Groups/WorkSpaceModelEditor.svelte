<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getTools } from '$lib/apis/tools';
	import { updateModelById, getModelById } from '$lib/apis/models';

	const i18n = getContext('i18n');

	export let show = false;
	export let modelId = null;
	export let groupId = null;
	export let onSubmit: Function = () => {};
	export let onClose: Function = () => {};

	let loading = false;
	let model = null;
	
	// Group-level resources (not user-specific)
	let allKnowledge = [];
	let allTools = [];
	
	// Selected items for this model
	let selectedKnowledge = [];
	let selectedToolIds = [];

	const loadData = async () => {
		loading = true;
		
		try {
			// Load the full model
			model = await getModelById(localStorage.token, modelId);
			
			// Load ALL knowledge and tools (not just user's)
			// The API should return all resources accessible by the group
			allKnowledge = await getKnowledgeBases(localStorage.token);
			allTools = await getTools(localStorage.token);
			
			// Filter to show only resources that belong to the group
			// This assumes your API returns resources with group information
			allKnowledge = allKnowledge.filter(kb => 
				kb.access_control?.read?.group_ids?.includes(groupId) ||
				kb.user_id === model.user_id // Include resources from model owner
			);
			
			allTools = allTools.filter(tool => 
				tool.access_control?.read?.group_ids?.includes(groupId) ||
				tool.user_id === model.user_id
			);
			
			// Set current selections
			selectedKnowledge = model?.meta?.knowledge || [];
			selectedToolIds = model?.meta?.toolIds || [];
			
		} catch (error) {
			console.error('Error loading model data:', error);
			toast.error($i18n.t('Failed to load model data'));
		} finally {
			loading = false;
		}
	};

	const submitHandler = async () => {
		loading = true;
		
		try {
			// Only update knowledge and tools, not other model properties
			const updatedModel = {
				...model,
				meta: {
					...model.meta,
					knowledge: selectedKnowledge.length > 0 ? selectedKnowledge : undefined,
					toolIds: selectedToolIds.length > 0 ? selectedToolIds : undefined
				}
			};
			
			// Remove undefined properties
			if (!updatedModel.meta.knowledge) {
				delete updatedModel.meta.knowledge;
			}
			if (!updatedModel.meta.toolIds) {
				delete updatedModel.meta.toolIds;
			}
			
			await updateModelById(localStorage.token, modelId, updatedModel);
			
			toast.success($i18n.t('Model updated successfully'));
			await onSubmit();
			show = false;
		} catch (error) {
			console.error('Error updating model:', error);
			toast.error($i18n.t('Failed to update model'));
		} finally {
			loading = false;
		}
	};

	$: if (show && modelId && groupId) {
		loadData();
	}

	onMount(() => {
		if (show && modelId && groupId) {
			loadData();
		}
	});
</script>

{#if show}
	<div class="flex flex-col w-full">
		{#if loading}
			<div class="text-center py-8">
				<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"></div>
				<div class="mt-2 text-sm text-gray-500">{$i18n.t('Loading...')}</div>
			</div>
		{:else if model}
			<form
				class="flex flex-col w-full gap-4"
				on:submit|preventDefault={submitHandler}
			>
				<!-- Model Info (Read-only) -->
				<div class="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
					<img
						src={model?.meta?.profile_image_url ?? '/static/favicon.png'}
						alt="model profile"
						class="rounded-lg w-16 h-16 object-cover"
					/>
					<div class="flex-1">
						<div class="font-semibold text-lg">{model.name}</div>
						<div class="text-sm text-gray-500">{model.id}</div>
						{#if model.base_model_id}
							<div class="text-xs text-gray-400 mt-1">
								{$i18n.t('Base Model')}: {model.base_model_id}
							</div>
						{/if}
					</div>
				</div>

				<!-- Notice about limited editing -->
				<div class="text-sm text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4 inline-block mr-1"
					>
						<path
							fill-rule="evenodd"
							d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
							clip-rule="evenodd"
						/>
					</svg>
					{$i18n.t('You can only edit Knowledge and Tools for workspace models. To modify other settings, edit the model directly.')}
				</div>

				<!-- Knowledge Section -->
				<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
					<div class="text-sm font-semibold mb-3">{$i18n.t('Knowledge')}</div>
					<Knowledge 
						bind:selectedKnowledge={selectedKnowledge} 
						collections={allKnowledge}
					/>
				</div>

				<!-- Tools Section -->
				<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
					<div class="text-sm font-semibold mb-3">{$i18n.t('Tools')}</div>
					<ToolsSelector 
						bind:selectedToolIds={selectedToolIds} 
						tools={allTools}
					/>
				</div>

				<!-- Action Buttons -->
				<div class="flex justify-end gap-2 pt-4">
					<button
						type="button"
						class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
						on:click={() => {
							show = false;
							onClose();
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					
					<button
						type="submit"
						class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg flex items-center gap-2"
						disabled={loading}
					>
						{$i18n.t('Save Changes')}
						{#if loading}
							<div class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white dark:border-black"></div>
						{/if}
					</button>
				</div>
			</form>
		{/if}
	</div>
{/if}