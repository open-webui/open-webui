<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import {
		addModelsToGroup,
		getAvailableGroupModels,
		getGroupModels,
		removeModelsFromGroup
	} from '$lib/apis/groups';

	type GroupModel = {
		id: string;
		name?: string;
		base_model_id?: string | null;
		description?: string | null;
		selected?: boolean;
	};

	const i18n: any = getContext('i18n');

	export let groupId: string;

	let loading = true;
	let saving = false;
	let models: GroupModel[] = [];
	let availableModels: GroupModel[] = [];
	let query = '';
	let addQuery = '';
	let showAddModal = false;
	let selectedModelIds = new Set<string>();
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let availableRequestId = 0;

	$: filteredModels = models.filter((model) => {
		if (!query) {
			return true;
		}
		const q = query.toLowerCase();
		return model.id.toLowerCase().includes(q) || (model.name ?? '').toLowerCase().includes(q);
	});

	const loadModels = async () => {
		loading = true;
		models = await getGroupModels(localStorage.token, groupId).catch((error) => {
			toast.error(`${error}`);
			return [];
		});
		loading = false;
	};

	const loadAvailableModels = async () => {
		const requestId = ++availableRequestId;
		const models = await getAvailableGroupModels(localStorage.token, groupId, addQuery).catch(
			(error) => {
				toast.error(`${error}`);
				return [];
			}
		);
		if (requestId === availableRequestId) {
			availableModels = models;
		}
	};

	const searchAvailableModels = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(loadAvailableModels, 300);
	};

	const openAddModal = async () => {
		selectedModelIds = new Set();
		addQuery = '';
		showAddModal = true;
		await loadAvailableModels();
	};

	const toggleSelected = (modelId: string) => {
		const next = new Set(selectedModelIds);
		if (next.has(modelId)) {
			next.delete(modelId);
		} else {
			next.add(modelId);
		}
		selectedModelIds = next;
	};

	const addSelectedModels = async () => {
		const modelIds = Array.from(selectedModelIds);
		if (modelIds.length === 0) {
			return;
		}
		saving = true;
		const updatedModels = await addModelsToGroup(localStorage.token, groupId, modelIds).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		saving = false;
		if (!updatedModels) {
			return;
		}
		models = updatedModels;
		showAddModal = false;
		toast.success($i18n.t('Models added successfully'));
	};

	const removeModel = async (modelId: string) => {
		saving = true;
		const updatedModels = await removeModelsFromGroup(localStorage.token, groupId, [modelId]).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		saving = false;
		if (!updatedModels) {
			return;
		}
		models = updatedModels;
		toast.success($i18n.t('Model removed successfully'));
	};

	onMount(loadModels);

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<Modal size="lg" bind:show={showAddModal}>
	<div class="px-5 pt-4 pb-5 dark:text-gray-100">
		<div class="flex items-center justify-between mb-3">
			<div class="text-lg font-medium">{$i18n.t('Add Models')}</div>
			<button on:click={() => (showAddModal = false)}><XMark className="size-5" /></button>
		</div>

		<div class="flex items-center w-full rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2 mb-3">
			<Search className="size-3.5" />
			<input
				class="w-full text-sm ml-2 bg-transparent outline-hidden"
				bind:value={addQuery}
				placeholder={$i18n.t('Search models')}
				on:input={searchAvailableModels}
			/>
		</div>

		<div class="max-h-96 overflow-y-auto space-y-1 pr-1">
			{#each availableModels as model}
				<div
					class="w-full text-left px-3 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition flex items-center gap-3 {model.selected
						? 'opacity-50'
						: ''}"
				>
					<Checkbox
						state={selectedModelIds.has(model.id) || model.selected ? 'checked' : 'unchecked'}
						disabled={model.selected}
						on:change={() => toggleSelected(model.id)}
					/>
					<div class="min-w-0">
						<div class="text-sm font-medium truncate">{model.name}</div>
						<div class="text-xs text-gray-500 truncate">{model.id}</div>
					</div>
				</div>
			{/each}
		</div>

		<div class="flex justify-end pt-4">
			<button
				class="px-3.5 py-1.5 rounded-full bg-black text-white dark:bg-white dark:text-black text-sm font-medium disabled:opacity-50 flex items-center gap-2"
				type="button"
				disabled={saving || selectedModelIds.size === 0}
				on:click={addSelectedModels}
			>
				{$i18n.t('Add')}
				{#if saving}<Spinner />{/if}
			</button>
		</div>
	</div>
</Modal>

<div class="flex flex-col h-full">
	<div class="flex items-center gap-2 mb-3">
		<div class="flex items-center flex-1 rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2">
			<Search className="size-3.5" />
			<input
				class="w-full text-sm ml-2 bg-transparent outline-hidden"
				bind:value={query}
				placeholder={$i18n.t('Search models')}
			/>
		</div>
		<button
			class="px-3 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium flex items-center gap-1"
			type="button"
			on:click={openAddModal}
		>
			<Plus className="size-3" />
			{$i18n.t('Add')}
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center py-12"><Spinner /></div>
	{:else if filteredModels.length === 0}
		<div class="text-center text-sm text-gray-500 py-12">{$i18n.t('No models assigned')}</div>
	{:else}
		<div class="space-y-1 overflow-y-auto pr-1">
			{#each filteredModels as model}
				<div class="flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-gray-50/60 dark:bg-gray-850/60">
					<div class="min-w-0">
						<div class="text-sm font-medium truncate">{model.name}</div>
						<div class="text-xs text-gray-500 truncate">{model.id}</div>
					</div>
					<button
						class="text-xs text-red-600 dark:text-red-400 hover:underline disabled:opacity-50"
						type="button"
						disabled={saving}
						on:click={() => removeModel(model.id)}
					>
						{$i18n.t('Remove')}
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
