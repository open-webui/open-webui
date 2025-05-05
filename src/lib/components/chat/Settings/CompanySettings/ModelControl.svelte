<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getBaseModels } from '$lib/apis/models';
	import { getModels } from '$lib/apis';
	import { modelsInfo, mapModelsToOrganizations } from '../../../../../data/modelsInfo';
	import { getModelIcon } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { onClickOutside } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';
	import { companyConfig, models as storeModels } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import GroupIcon from '$lib/components/icons/GroupIcon.svelte';
	import PublicIcon from '$lib/components/icons/PublicIcon.svelte';
	import PrivateIcon from '$lib/components/icons/PrivateIcon.svelte';
	import AccessModel from '$lib/components/common/AccessModel.svelte';
	import { getGroups } from '$lib/apis/groups';
	import { updateModelById } from '$lib/apis/models';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import InfoIcon from '$lib/components/icons/InfoIcon.svelte';
	import AdditionaModelInfo from '../../ModelSelector/AdditionaModelInfo.svelte';
	import { getCompanyConfig } from '$lib/apis/auths';

	const i18n = getContext('i18n');

	let models = null;

	let config = null;

	let modelIds = [];
	let defaultModelIds = [];

	let baseModelName = '';
	let showBaseDropdown = false;
	let dropdownBaseRef;

	let imageModelName = '';
	let showImageDropdown = false;
	let dropdownImageRef;

	let organizations = mapModelsToOrganizations(modelsInfo);

	let workspaceModels = null;
	let baseModels = null;
	let accessControl = null;

	const init = async () => {
		workspaceModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, true);

		models = baseModels.map((m) => {
			const workspaceModel = workspaceModels.find((wm) => wm.id === m.id);

			if (workspaceModel) {
				return {
					...m,
					...workspaceModel
				};
			} else {
				return {
					...m,
					id: m.id,
					name: m.name,

					is_active: true
				};
			}
		});
		storeModels.set(baseModels);
	};

	const defaultInit = async () => {
		config = await getModelsConfig(localStorage.token);

		if (config?.DEFAULT_MODELS) {
			defaultModelIds = (config?.DEFAULT_MODELS).split(',').filter((id) => id);
		} else {
			defaultModelIds = [];
		}
		const modelOrderList = config.MODEL_ORDER_LIST || [];
		const allModelIds = $storeModels.map((model) => model.id);

		// Create a Set for quick lookup of ordered IDs
		const orderedSet = new Set(modelOrderList);

		modelIds = [
			// Add all IDs from MODEL_ORDER_LIST that exist in allModelIds
			...modelOrderList.filter((id) => orderedSet.has(id) && allModelIds.includes(id)),
			// Add remaining IDs not in MODEL_ORDER_LIST, sorted alphabetically
			...allModelIds.filter((id) => !orderedSet.has(id)).sort((a, b) => a.localeCompare(b))
		];
	};

	const savebaseModel = async (defaultModelIds) => {
		const res = await setModelsConfig(localStorage.token, {
			DEFAULT_MODELS: defaultModelIds.join(','),
			MODEL_ORDER_LIST: modelIds
		});

		if (res) {
			toast.success($i18n.t('Models configuration saved successfully'));
			defaultInit();
			const companyConfigInfo = await getCompanyConfig(localStorage.token)
			.catch(error => toast.error(error));
			if(companyConfigInfo) {
				companyConfig.set(companyConfigInfo);
			}
		} else {
			toast.error($i18n.t('Failed to save models configuration'));
		}
	};
	onMount(async () => {
		init();
		defaultInit();
	});
	let groups = [];
	onMount(async () => {
		groups = await getGroups(localStorage.token);
	});

	let openAccessDropdownId = null;

	const updateModel = async (modelId, accessControl) => {
		const selectedModel = models.find((model) => model.id === modelId);
		console.log(selectedModel);
		console.log(modelId, accessControl);
		let info = {};
		info.id = selectedModel.id;
		info.name = selectedModel.name;
		info.base_model_id = null;
		info.params = {};
		info.access_control = accessControl;
		info.is_active = selectedModel.is_active;
		info.created_at = selectedModel.created_at;
		info.updated_at = selectedModel.updated_at;
		info.user_id = selectedModel.user_id;
		info.company_id = selectedModel.company_id;
		info.meta = { ...selectedModel.meta, files: [] };

		const res = await updateModelById(localStorage.token, modelId, info).catch((error) => {
			return null;
		});

		if (res) {
			toast.success($i18n.t('Model updated successfully'));
		}
		init();
	};
</script>

<div class="min-h-[40rem] pb-4">
	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Model')}</div>
		</div>
	</div>
	<div class="mb-5" use:onClickOutside={() => (showBaseDropdown = false)}>
		<div class="relative" bind:this={dropdownBaseRef}>
			<button
				type="button"
				class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2  ${showBaseDropdown ? 'border' : ''} border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
				on:click={() => (showBaseDropdown = !showBaseDropdown)}
			>
				<div class="text-gray-500 dark:text-customGray-100 flex items-center">
					<span>{$i18n.t('Default Model')}</span>
				</div>
				<div class="flex items-center gap-2">
					{#if defaultModelIds?.length > 0}
						<div class="flex items-center gap-2 text-xs dark:text-customGray-100/50">
							<img src={getModelIcon(defaultModelIds?.[0])} alt="icon" class="w-4 h-4" />
							{defaultModelIds?.[0]}
						</div>
					{/if}
					<ChevronDown className="size-3" />
				</div>
			</button>

			{#if showBaseDropdown}
				<div
					class="max-h-60 overflow-y-auto absolute z-50 w-full -mt-1 bg-white dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
				>
					<hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
					<div class="px-1">
						{#each models as model (model.id)}
							<button
								class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
								on:click={() => {
									// baseModelName = model.name
									savebaseModel([model.id]);
									showBaseDropdown = false;
								}}
							>
								<img src={getModelIcon(model.name)} alt="icon" class="w-4 h-4" />
								{model.name}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
	<!-- <div class="mb-5" use:onClickOutside={() => (showImageDropdown = false)}>
		<div class="relative" bind:this={dropdownImageRef}>
			<button
				type="button"
				class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2  ${showImageDropdown ? 'border' : ''} border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
				on:click={() => (showImageDropdown = !showImageDropdown)}
			>
				<div class="text-gray-500 dark:text-customGray-100 flex items-center">
					<span>{$i18n.t('Image generation model')}</span>
				</div>

				<div class="flex items-center gap-2">
					{#if imageModelName}
						<div class="flex items-center gap-2 text-xs dark:text-customGray-100/50">
							<img src={getModelIcon(imageModelName)} alt="icon" class="w-4 h-4" />
							{imageModelName}
						</div>
					{/if}
					<ChevronDown className="size-3" />
				</div>
			</button>

			{#if showImageDropdown}
				<div
					class="max-h-60 overflow-y-auto absolute z-50 w-full -mt-1 bg-white dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
				>
					<hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
					<div class="px-1">
						{#each models as model (model.id)}
							<button
								class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
								on:click={() => {
									imageModelName = model.name;
									showImageDropdown = false;
								}}
							>
								<img src={getModelIcon(model.name)} alt="icon" class="w-4 h-4" />
								{model.name}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div> -->
	{#if models !== null}
		<div>
			{#each Object.keys(organizations) as organization (organization)}
				<div class="mb-5">
					<div class="text-sm dark:text-customGray-100 mb-2.5">{organization}</div>
					{#each models?.filter((m) => organizations[organization]
							.map((item) => item.toLowerCase())
							.includes(m.id.toLowerCase())) as model (model.id)}
						<div class="grid grid-cols-[60%_1fr_1fr] border-t last:border-b border-customGray-700">
							<div class="border-l border-r border-customGray-700 py-2 px-2">
								<div class="flex items-center mb-1">
									<img class="w-4 h-4 rounded-full" src={getModelIcon(model.id)} alt={model.id} />
									<div class="text-xs dark:text-white ml-2">{model.name}</div>
									
										<AdditionaModelInfo hoveredItem={model} />
									
								</div>
								<div class="text-xs dark:text-customGray-590">
									{modelsInfo[model.id].description}
								</div>
							</div>
							<div class="border-r border-customGray-700 flex justify-center items-center">
								<div class="text-xs dark:text-white">
									{modelsInfo[model.id]?.creditsPerMessage}x
								</div>
							</div>
							<div class="border-r border-customGray-700 flex justify-center items-center">
								<div class="flex items-center justify-center">
									<div
										class="bg-customGray-900 px-2 py-1 rounded-lg"
										on:click={() =>
											(openAccessDropdownId = openAccessDropdownId === model.id ? null : model.id)}
									>
										{#if model.access_control === null}
											<div
												class="cursor-pointer flex items-center gap-1 text-xs dark:text-customGray-100/50 leading-none"
											>
												<PublicIcon className="size-3" />{$i18n.t('Public')}
											</div>
										{:else if [...(model?.access_control?.read?.group_ids ?? []), ...(model?.access_control?.write?.group_ids ?? [])].length > 0}
											<div
												class="cursor-pointer flex items-center gap-1 text-xs dark:text-customGray-100/50 leading-none"
											>
												<GroupIcon className="size-3" />{$i18n.t('Group')}
											</div>
										{:else}
											<div
												class="cursor-pointer flex items-center gap-1 text-xs dark:text-customGray-100/50 leading-none"
											>
												<PrivateIcon className="size-3" />{$i18n.t('Private')}
											</div>
										{/if}
									</div>
									<ChevronDown className="size-2 ml-[3px]" />
								</div>
								{#if openAccessDropdownId === model.id}
									<AccessModel
										bind:openAccessDropdownId
										{groups}
										{updateModel}
										accessControl={model.access_control}
									/>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/each}
		</div>
	{:else}
		<div class="h-[20rem] w-full flex justify-center items-center">
			<Spinner />
		</div>
	{/if}
</div>
