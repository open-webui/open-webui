<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getBaseModels } from '$lib/apis/models';
	import { getModels } from '$lib/apis';
	import { modelsInfo, mapModelsToOrganizations } from '../../../../../data/modelsInfo';
	import { getModelIcon } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { onClickOutside } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let models = null;

	let selectedModelId = '';
	let defaultModelIds = [];
	let modelIds = [];

	let baseModelName = '';
	let showBaseDropdown = false;
	let dropdownBaseRef;

	let imageModelName = '';
	let showImageDropdown = false;
	let dropdownImageRef;

	let organizations = mapModelsToOrganizations(modelsInfo);

	let workspaceModels = null;
	let baseModels = null;

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
	};
	onMount(async () => {
		init();
	});

	$: console.log(models, 'models');
</script>

<div class="min-h-[40rem] pb-4">
	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Model')}</div>
		</div>
	</div>
	<div class="mb-2.5" use:onClickOutside={() => (showBaseDropdown = false)}>
		<div class="relative" bind:this={dropdownBaseRef}>
			<button
				type="button"
				class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2  ${showBaseDropdown ? 'border' : ''} border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
				on:click={() => (showBaseDropdown = !showBaseDropdown)}
			>
				<span class="text-gray-500 dark:text-customGray-100"
					>{$i18n.t('Default Model')}</span
				>
				<div class="flex items-center gap-2">
					{#if baseModelName}
						<div
							class="flex items-center gap-2 text-xs dark:text-customGray-100/50"
						>
							<img
								src={getModelIcon(baseModelName)}
								alt="icon"
								class="w-4 h-4"
							/>
							{baseModelName}
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
									baseModelName = model.name
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
	<div class="mb-5" use:onClickOutside={() => (showImageDropdown = false)}>
		<div class="relative" bind:this={dropdownImageRef}>
			<button
				type="button"
				class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2  ${showImageDropdown ? 'border' : ''} border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
				on:click={() => (showImageDropdown = !showImageDropdown)}
			>
				<span class="text-gray-500 dark:text-customGray-100"
					>{$i18n.t('Image generation model')}</span
				>
				<div class="flex items-center gap-2">
					{#if imageModelName}
						<div
							class="flex items-center gap-2 text-xs dark:text-customGray-100/50"
						>
							<img
								src={getModelIcon(imageModelName)}
								alt="icon"
								class="w-4 h-4"
							/>
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
									imageModelName = model.name
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
	</div>
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
									<img class="w-4 h-4 rounded-full" src={getModelIcon(model.id)}/>
									<div class="text-xs dark:text-white ml-2">{model.name}</div>
								</div>
								<div class="text-xs dark:text-customGray-590">{modelsInfo[model.id].description}</div>
							</div>
							<div class="border-r border-customGray-700 flex justify-center items-center">
								<div class="text-xs dark:text-white">{modelsInfo[model.id]?.creditsPerMessage}x</div>
							</div>
							<div class="border-r border-customGray-700"></div>
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
