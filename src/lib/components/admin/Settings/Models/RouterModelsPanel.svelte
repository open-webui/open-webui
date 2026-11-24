<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick } from 'svelte';

	import { models } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getRouterModelsConfig, setRouterModelsConfig } from '$lib/apis/configs';
	import { updateModelAccessGrants } from '$lib/apis/models';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ModelSettingsLabel from '$lib/components/workspace/Models/ModelSettingsLabel.svelte';
	import RouterModel from './RouterModel.svelte';
	import RouterModelModal from './RouterModelModal.svelte';

	const i18n = getContext('i18n');

	export let initHandler = async () => {};

	let routerModelsConfig = null;
	let expanded = false;
	let rows: Record<string, RouterModel> = {};

	// Opens a router model's editor, for clicks from the model list.
	export const openModel = async (id: string) => {
		expanded = true;
		await tick();
		rows[id]?.open();
	};
	let showAddModel = false;

	// Access lives on the model row, like any model, so it's saved through the model API.
	const submitHandler = async (
		nextConfig = routerModelsConfig,
		model = null,
		accessGrants = null
	) => {
		const result = await setRouterModelsConfig(localStorage.token, nextConfig).catch((err) => {
			toast.error(
				Array.isArray(err?.detail)
					? err.detail.map((entry) => entry.msg).join('\n')
					: `${err?.detail ?? err}`
			);
			return null;
		});

		if (result) {
			routerModelsConfig = result;
			if (model && accessGrants) {
				await updateModelAccessGrants(localStorage.token, model.id, model.name, accessGrants).catch(
					(err) => toast.error(`${err?.detail ?? err}`)
				);
			}
			toast.success($i18n.t('Settings saved successfully!'));
			models.set(await getModels(localStorage.token));
			await initHandler();
		}
		return !!result;
	};

	const addModelHandler = async (model, accessGrants) => {
		return submitHandler(
			{
				...routerModelsConfig,
				ROUTER_MODELS: [...routerModelsConfig.ROUTER_MODELS, model]
			},
			model,
			accessGrants
		);
	};

	const editModelHandler = async (model, modelIdx, accessGrants) => {
		return submitHandler(
			{
				...routerModelsConfig,
				ROUTER_MODELS: routerModelsConfig.ROUTER_MODELS.map((item, idx) =>
					idx === modelIdx ? model : item
				)
			},
			model,
			accessGrants
		);
	};

	const deleteModelHandler = async (modelIdx) => {
		return submitHandler({
			...routerModelsConfig,
			ROUTER_MODELS: routerModelsConfig.ROUTER_MODELS.filter((_, idx) => idx !== modelIdx)
		});
	};

	onMount(async () => {
		routerModelsConfig = await getRouterModelsConfig(localStorage.token).catch((err) => {
			toast.error(`${err?.detail ?? err}`);
			return null;
		});
	});
</script>

<RouterModelModal bind:show={showAddModel} onSubmit={addModelHandler} />

<div class="shrink-0 -mx-1">
	<div class="flex items-center gap-1 pr-1">
		<button
			class="flex flex-1 items-center justify-between gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal text-base-600 focus-visible:outline focus-visible:outline-2 dark:text-base-400"
			type="button"
			aria-expanded={expanded}
			on:click={() => (expanded = !expanded)}
		>
			<ModelSettingsLabel
				label={$i18n.t('settings.admin.models.routerModels.label')}
				description={$i18n.t('settings.admin.models.routerModels.description')}
			/>
			<ChevronRight
				className={`size-3 text-base-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
			/>
		</button>

		{#if routerModelsConfig}
			<Tooltip content={$i18n.t('settings.admin.models.routerModels.add.label')}>
				<button
					aria-label={$i18n.t('settings.admin.models.routerModels.add.label')}
					class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-base-1000/5 hover:text-base-900 dark:text-base-600 dark:hover:bg-base-0/5 dark:hover:text-base-0"
					type="button"
					on:click={() => {
						showAddModel = true;
					}}
				>
					<Plus className="size-3.5" />
				</button>
			</Tooltip>
		{/if}
	</div>

	{#if expanded}
		<div class="pl-3 pr-1 pb-1">
			{#if routerModelsConfig === null}
				<div class="py-1 text-xs text-base-400 dark:text-base-600">{$i18n.t('Loading...')}</div>
			{:else if routerModelsConfig.ROUTER_MODELS.length === 0}
				<div class="py-1 text-xs text-base-400 dark:text-base-600">
					{$i18n.t('settings.admin.models.routerModels.empty')}
				</div>
			{:else}
				{#each routerModelsConfig.ROUTER_MODELS as model, modelIdx (model.id)}
					<RouterModel
						bind:this={rows[model.id]}
						{model}
						onEdit={(nextModel, accessGrants) =>
							editModelHandler(nextModel, modelIdx, accessGrants)}
						on:delete={() => deleteModelHandler(modelIdx)}
					/>
				{/each}
			{/if}
		</div>
	{/if}
</div>
