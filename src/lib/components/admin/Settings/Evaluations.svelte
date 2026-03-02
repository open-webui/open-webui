<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { models, settings, user, config } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();
	import { getModels } from '$lib/apis';
	import { getConfig, updateConfig } from '$lib/apis/evaluations';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Model from './Evaluations/Model.svelte';
	import ArenaModelModal from './Evaluations/ArenaModelModal.svelte';

	const i18n = getContext('i18n');

	let evaluationConfig = null;
	let showAddModel = false;

	const submitHandler = async () => {
		evaluationConfig = await updateConfig(localStorage.token, evaluationConfig).catch((err) => {
			toast.error(err);
			return null;
		});

		if (evaluationConfig) {
			toast.success('Settings saved successfully');
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	const addModelHandler = async (model) => {
		evaluationConfig.EVALUATION_ARENA_MODELS.push(model);
		evaluationConfig.EVALUATION_ARENA_MODELS = [...evaluationConfig.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const editModelHandler = async (model, modelIdx) => {
		evaluationConfig.EVALUATION_ARENA_MODELS[modelIdx] = model;
		evaluationConfig.EVALUATION_ARENA_MODELS = [...evaluationConfig.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const deleteModelHandler = async (modelIdx) => {
		evaluationConfig.EVALUATION_ARENA_MODELS = evaluationConfig.EVALUATION_ARENA_MODELS.filter(
			(m, mIdx) => mIdx !== modelIdx
		);

		await submitHandler();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			evaluationConfig = await getConfig(localStorage.token).catch((err) => {
				toast.error(err);
				return null;
			});
		}
	});
</script>

<ArenaModelModal
	bind:show={showAddModel}
	on:submit={async (e) => {
		addModelHandler(e.detail);
	}}
/>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		dispatch('save');
	}}
>
	<div class="overflow-y-scroll scrollbar-hidden h-full px-1">
		{#if evaluationConfig !== null}
			<div class="space-y-6">
				<!-- General Settings Section -->
				<div class="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-800">
					<div class="flex items-center gap-2 mb-4">
						<div class="w-1 h-6 bg-orange-500 rounded-full"></div>
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('General')}</h3>
					</div>

					<div class="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
								{$i18n.t('Arena Models')}
							</span>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								{$i18n.t('Message rating should be enabled to use this feature')}
							</span>
						</div>
						<Tooltip content={$i18n.t(`Message rating should be enabled to use this feature`)}>
							<Switch bind:state={evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS} />
						</Tooltip>
					</div>
				</div>

				{#if evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS}
					<!-- Manage Models Section -->
					<div class="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-800">
						<div class="flex items-center justify-between mb-4">
							<div class="flex items-center gap-2">
								<div class="w-1 h-6 bg-orange-500 rounded-full"></div>
								<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Manage')}</h3>
							</div>

							<Tooltip content={$i18n.t('Add Arena Model')}>
								<button
									class="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all duration-200 shadow-sm hover:shadow-md active:scale-95"
									type="button"
									on:click={() => {
										showAddModel = true;
									}}
								>
									<Plus />
									<span class="hidden sm:inline">{$i18n.t('Add Model')}</span>
								</button>
							</Tooltip>
						</div>

						<div class="space-y-3">
							{#if (evaluationConfig?.EVALUATION_ARENA_MODELS ?? []).length > 0}
								{#each evaluationConfig.EVALUATION_ARENA_MODELS as model, index}
									<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 transition-all duration-200 hover:shadow-md">
										<Model
											{model}
											on:edit={(e) => {
												editModelHandler(e.detail, index);
											}}
											on:delete={(e) => {
												deleteModelHandler(index);
											}}
										/>
									</div>
								{/each}
							{:else}
								<div class="flex flex-col items-center justify-center p-8 bg-white dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
									<svg class="w-12 h-12 text-gray-400 dark:text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
									</svg>
									<p class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
										{$i18n.t('No custom models added')}
									</p>
									<p class="text-xs text-gray-500 dark:text-gray-400 text-center max-w-md">
										{$i18n.t('Using the default arena model with all models. Click the plus button to add custom models.')}
									</p>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex h-full justify-center items-center">
				<div class="flex flex-col items-center gap-3">
					<Spinner className="size-8" />
					<p class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading configuration...')}</p>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-4 px-1 border-t border-gray-200 dark:border-gray-800 mt-4">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>