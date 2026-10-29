<script lang="ts">
	import AdminSettingRow from './AdminSettingRow.svelte';
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { config as appConfig } from '$lib/stores';
	import { getBackendConfig, getModels } from '$lib/apis';
	import { getSubagentsConfig, setSubagentsConfig } from '$lib/apis/configs';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let saving = false;
	let enabled = false;
	let subagentModels: { id: string; description: string }[] = [];
	let models: any[] = [];
	let backgroundEnabled = false;
	let maxConcurrent = 20;
	let maxAsync = 20;
	let maxIterations = 30;
	let maxOutput = 30000;
	let systemPrompt = '';

	onMount(async () => {
		try {
			const config = await getSubagentsConfig(localStorage.token);
			enabled = config?.ENABLE_SUBAGENTS ?? false;
			subagentModels = config?.SUBAGENTS_MODELS ?? [];
			backgroundEnabled = config?.SUBAGENTS_BACKGROUND_ENABLED ?? false;
			maxConcurrent = Number(config?.SUBAGENTS_MAX_CONCURRENT) || 20;
			maxAsync = Number(config?.SUBAGENTS_MAX_ASYNC) || 20;
			maxIterations = Number(config?.SUBAGENTS_MAX_ITERATIONS) || 30;
			maxOutput = Number(config?.SUBAGENTS_MAX_OUTPUT) || 30000;
			systemPrompt = config?.SUBAGENTS_SYSTEM_PROMPT ?? '';
			models = await getModels(localStorage.token, null, false);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	});

	const save = async () => {
		saving = true;
		try {
			await setSubagentsConfig(localStorage.token, {
				ENABLE_SUBAGENTS: enabled,
				SUBAGENTS_MODELS: subagentModels,
				SUBAGENTS_BACKGROUND_ENABLED: backgroundEnabled,
				SUBAGENTS_MAX_CONCURRENT: maxConcurrent,
				SUBAGENTS_MAX_ASYNC: maxAsync,
				SUBAGENTS_MAX_ITERATIONS: maxIterations,
				SUBAGENTS_MAX_OUTPUT: maxOutput,
				SUBAGENTS_SYSTEM_PROMPT: systemPrompt
			});
			await appConfig.set(await getBackendConfig());
			toast.success($i18n.t('Settings saved successfully!'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};
</script>

<form class="flex h-full flex-col justify-between text-sm" on:submit|preventDefault={save}>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.admin.subagents.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if loading}
			<div class="flex justify-center py-8"><Spinner className="size-6" /></div>
		{:else}
			<div class="flex flex-col gap-2.5">
				<AdminSettingRow let:labelId>
					<span slot="label">
						{$i18n.t('settings.admin.subagents.enableSubAgents.label')}
					</span>
					<Switch ariaLabelledbyId={labelId} bind:state={enabled} />
				</AdminSettingRow>
				<p class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
					{$i18n.t(
						'Allow the AI to delegate tasks to sub-agents. Each sub-agent creates a real chat with full tool access. Uses additional LLM calls.'
					)}
				</p>

				{#if enabled}
					<div>
						<div class="mb-1 flex min-h-7 w-full items-center justify-between gap-2">
							<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400">
								{$i18n.t('settings.admin.subagents.models.label')}
							</div>
							<button
								class="flex size-6 shrink-0 items-center justify-center text-gray-400 dark:text-gray-600"
								type="button"
								aria-label={$i18n.t('settings.admin.subagents.addModel.label')}
								on:click={() => {
									if (
										subagentModels.length === 0 ||
										subagentModels[subagentModels.length - 1]?.id !== ''
									) {
										subagentModels = [...subagentModels, { id: '', description: '' }];
									}
								}}
							>
								<Plus />
							</button>
						</div>
						<div class="mb-2 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('settings.admin.subagents.models.description')}
						</div>
						<div class="flex flex-col gap-1.5">
							{#each subagentModels as subagentModel, subagentModelIdx}
								<div
									class="flex items-center gap-1 rounded-lg border border-gray-100/40 bg-transparent px-2 py-1 transition focus-within:border-blue-400 dark:border-gray-850/50 dark:focus-within:border-blue-500"
								>
									<SettingsSelect
										bind:value={subagentModel.id}
										required
										ariaLabel={$i18n.t('Model')}
										className="w-48 max-w-full shrink-0"
										selectClassName="!h-6 !border-transparent !bg-transparent !ps-1 dark:!bg-transparent"
									>
										<option value="" disabled hidden>{$i18n.t('Select a model')}</option>
										{#each models.filter((model: any) => model.id === subagentModel.id || !subagentModels.some((otherModel) => otherModel.id === model.id)) as model}
											<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
												{model.name}
												{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
											</option>
										{/each}
									</SettingsSelect>
									<input
										class="min-w-0 flex-1 bg-transparent text-[0.8125rem] leading-5 text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-200 dark:placeholder:text-gray-700"
										aria-label={$i18n.t('Description')}
										placeholder={$i18n.t('settings.admin.subagents.modelDescription.placeholder')}
										bind:value={subagentModel.description}
									/>
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="flex size-6 shrink-0 items-center justify-center text-gray-400 opacity-70 transition hover:text-gray-700 hover:opacity-100 dark:text-gray-600 dark:hover:text-gray-300"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click={() => {
												subagentModels.splice(subagentModelIdx, 1);
												subagentModels = subagentModels;
											}}
										>
											<XMark className="size-3.5" />
										</button>
									</Tooltip>
								</div>
							{/each}
						</div>
					</div>

					<div>
						<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-concurrent">
							{$i18n.t('settings.admin.subagents.maxConcurrent.label')}
						</label>
						<div class="mt-1 flex items-center gap-1.5">
							<input
								id="sa-concurrent"
								type="number"
								bind:value={maxConcurrent}
								min="-1"
								class="h-7 w-16 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
							/>
							<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t('simultaneous sub-agents')}
							</span>
						</div>
					</div>

					<div>
						<AdminSettingRow let:labelId>
							<span slot="label">
								{$i18n.t('settings.admin.subagents.enableBackgroundSubAgents.label')}
							</span>
							<Switch ariaLabelledbyId={labelId} bind:state={backgroundEnabled} />
						</AdminSettingRow>
						<p class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('settings.admin.subagents.enableBackgroundSubAgents.description')}
						</p>
					</div>

					{#if backgroundEnabled}
						<div>
							<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-async">
								{$i18n.t('settings.admin.subagents.maxBackground.label')}
							</label>
							<div class="mt-1 flex items-center gap-1.5">
								<input
									id="sa-async"
									type="number"
									bind:value={maxAsync}
									min="-1"
									class="h-7 w-16 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
								/>
								<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
									{$i18n.t('background sub-agents')}
								</span>
							</div>
						</div>
					{/if}

					<div>
						<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-iterations">
							{$i18n.t('settings.admin.subagents.maxIterations.label')}
						</label>
						<div class="mt-1 flex items-center gap-1.5">
							<input
								id="sa-iterations"
								type="number"
								bind:value={maxIterations}
								min="1"
								max="100"
								class="h-7 w-16 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
							/>
							<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t('tool loops per sub-agent')}
							</span>
						</div>
					</div>

					<div>
						<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-output">
							{$i18n.t('settings.admin.subagents.maxOutput.label')}
						</label>
						<div class="mt-1 flex items-center gap-1.5">
							<input
								id="sa-output"
								type="number"
								bind:value={maxOutput}
								min="1000"
								max="100000"
								step="1000"
								class="h-7 w-20 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
							/>
							<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">chars</span>
						</div>
					</div>

					<div>
						<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-prompt">
							{$i18n.t('settings.admin.subagents.systemPrompt.label')}
						</label>
						<textarea
							id="sa-prompt"
							bind:value={systemPrompt}
							rows="4"
							placeholder={$i18n.t('You are a sub-agent...')}
							class="mt-1 w-full resize-y rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 font-mono text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
						></textarea>
						<p class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('settings.admin.subagents.systemPrompt.description')}
						</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	{#if !loading}
		<div class="flex justify-end pt-6 text-sm font-normal">
			<button
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
				type="submit"
				disabled={saving}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	{/if}
</form>
