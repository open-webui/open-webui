<script lang="ts">
	import { getDataVizConfig, updateDataVizConfig } from '$lib/apis';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let enableDataViz = false;
	let sharedCorePrompt = '';

	let diagramEnabled = true;
	let diagramPrompt = '';

	let mockupInteractiveEnabled = true;
	let mockupInteractivePrompt = '';

	let chartDataVizEnabled = true;
	let chartDataVizPrompt = '';

	let artEnabled = true;
	let artPrompt = '';

	let elicitationEnabled = true;
	let elicitationPrompt = '';

	let autoRepairEnabled = true;
	let autoRepairMaxAttempts = 3;
	let autoRepairModel = '';
	let autoRepairReasoningEffort = ''; // '' | 'low' | 'medium' | 'high'

	const submitHandler = async () => {
		const clampedAttempts = Math.max(1, Math.min(5, Number(autoRepairMaxAttempts) || 1));
		const res = await updateDataVizConfig(localStorage.token, {
			ENABLE_DATA_VIZ: enableDataViz,
			DATA_VIZ_SHARED_CORE_PROMPT: sharedCorePrompt,
			DATA_VIZ_MODULE_DIAGRAM_ENABLED: diagramEnabled,
			DATA_VIZ_MODULE_DIAGRAM_PROMPT: diagramPrompt,
			DATA_VIZ_MODULE_MOCKUP_INTERACTIVE_ENABLED: mockupInteractiveEnabled,
			DATA_VIZ_MODULE_MOCKUP_INTERACTIVE_PROMPT: mockupInteractivePrompt,
			DATA_VIZ_MODULE_CHART_DATAVIZ_ENABLED: chartDataVizEnabled,
			DATA_VIZ_MODULE_CHART_DATAVIZ_PROMPT: chartDataVizPrompt,
			DATA_VIZ_MODULE_ART_ENABLED: artEnabled,
			DATA_VIZ_MODULE_ART_PROMPT: artPrompt,
			DATA_VIZ_MODULE_ELICITATION_ENABLED: elicitationEnabled,
			DATA_VIZ_MODULE_ELICITATION_PROMPT: elicitationPrompt,
			DATA_VIZ_AUTO_REPAIR_ENABLED: autoRepairEnabled,
			DATA_VIZ_AUTO_REPAIR_MAX_ATTEMPTS: clampedAttempts,
			DATA_VIZ_AUTO_REPAIR_MODEL: autoRepairModel,
			DATA_VIZ_AUTO_REPAIR_REASONING_EFFORT: autoRepairReasoningEffort
		});

		if (res) {
			toast.success($i18n.t('Settings saved successfully'));
		}
	};

	onMount(async () => {
		const res = await getDataVizConfig(localStorage.token);

		if (res) {
			enableDataViz = res.ENABLE_DATA_VIZ ?? false;
			sharedCorePrompt = res.DATA_VIZ_SHARED_CORE_PROMPT ?? '';

			diagramEnabled = res.DATA_VIZ_MODULE_DIAGRAM_ENABLED ?? true;
			diagramPrompt = res.DATA_VIZ_MODULE_DIAGRAM_PROMPT ?? '';

			mockupInteractiveEnabled = res.DATA_VIZ_MODULE_MOCKUP_INTERACTIVE_ENABLED ?? true;
			mockupInteractivePrompt = res.DATA_VIZ_MODULE_MOCKUP_INTERACTIVE_PROMPT ?? '';

			chartDataVizEnabled = res.DATA_VIZ_MODULE_CHART_DATAVIZ_ENABLED ?? true;
			chartDataVizPrompt = res.DATA_VIZ_MODULE_CHART_DATAVIZ_PROMPT ?? '';

			artEnabled = res.DATA_VIZ_MODULE_ART_ENABLED ?? true;
			artPrompt = res.DATA_VIZ_MODULE_ART_PROMPT ?? '';

			elicitationEnabled = res.DATA_VIZ_MODULE_ELICITATION_ENABLED ?? true;
			elicitationPrompt = res.DATA_VIZ_MODULE_ELICITATION_PROMPT ?? '';

			autoRepairEnabled = res.DATA_VIZ_AUTO_REPAIR_ENABLED ?? true;
			autoRepairMaxAttempts = res.DATA_VIZ_AUTO_REPAIR_MAX_ATTEMPTS ?? 3;
			autoRepairModel = res.DATA_VIZ_AUTO_REPAIR_MODEL ?? '';
			autoRepairReasoningEffort = res.DATA_VIZ_AUTO_REPAIR_REASONING_EFFORT ?? '';
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="">
			<div class="mb-3">
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Data Visualization')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="  mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Data Visualization')}
					</div>
					<div class="flex items-center relative">
						<Switch bind:state={enableDataViz} />
					</div>
				</div>

				{#if enableDataViz}
					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip
									content={$i18n.t(
										'Always included when Data Visualization is enabled. Paste your shared core prompt here.'
									)}
								>
									{$i18n.t('Shared Core Prompt')}
								</Tooltip>
							</div>

							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Paste shared core prompt...')}
								bind:value={sharedCorePrompt}
							></textarea>
						</div>
					</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-3" />
					<div class=" mb-2 text-sm font-medium">{$i18n.t('Modules')}</div>

					<!-- Diagram -->
					<div class="mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Diagram')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={diagramEnabled} />
						</div>
					</div>
					{#if diagramEnabled}
						<div class="mb-2.5 flex w-full flex-col">
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Paste diagram module prompt...')}
								bind:value={diagramPrompt}
							></textarea>
						</div>
					{/if}

					<!-- Mockup / Interactive -->
					<div class="mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Mockup / Interactive')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={mockupInteractiveEnabled} />
						</div>
					</div>
					{#if mockupInteractiveEnabled}
						<div class="mb-2.5 flex w-full flex-col">
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Paste mockup / interactive module prompt...')}
								bind:value={mockupInteractivePrompt}
							></textarea>
						</div>
					{/if}

					<!-- Chart / Data Viz -->
					<div class="mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Chart / Data Viz')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={chartDataVizEnabled} />
						</div>
					</div>
					{#if chartDataVizEnabled}
						<div class="mb-2.5 flex w-full flex-col">
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Paste chart / data viz module prompt...')}
								bind:value={chartDataVizPrompt}
							></textarea>
						</div>
					{/if}

					<!-- Art -->
					<div class="mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Art')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={artEnabled} />
						</div>
					</div>
					{#if artEnabled}
						<div class="mb-2.5 flex w-full flex-col">
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Paste art module prompt...')}
								bind:value={artPrompt}
							></textarea>
						</div>
					{/if}

					<!-- Elicitation -->
					<div class="mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Elicitation')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={elicitationEnabled} />
						</div>
					</div>
					{#if elicitationEnabled}
						<div class="mb-2.5 flex w-full flex-col">
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Paste elicitation module prompt...')}
								bind:value={elicitationPrompt}
							></textarea>
						</div>
					{/if}

					<hr class="border-gray-100 dark:border-gray-850 my-3" />

					<div class="mb-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
						{$i18n.t('Auto-repair')}
					</div>

					<div class="mb-2.5 flex w-full justify-between">
						<div class="self-center text-xs font-medium">
							<Tooltip
								content={$i18n.t(
									'When a rendered widget throws a runtime error, re-prompt the model with the error and replace the broken widget in-place.'
								)}
							>
								{$i18n.t('Auto-repair widget errors')}
							</Tooltip>
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={autoRepairEnabled} />
						</div>
					</div>

					{#if autoRepairEnabled}
						<div class="mb-2.5 flex w-full justify-between">
							<div class="self-center text-xs font-medium">
								<Tooltip
									content={$i18n.t(
										'Max number of repair attempts per broken widget (1–5). Each attempt is a separate model call.'
									)}
								>
									{$i18n.t('Max repair attempts')}
								</Tooltip>
							</div>
							<div class="flex items-center relative">
								<input
									type="number"
									min="1"
									max="5"
									step="1"
									class="w-20 rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden text-right"
									bind:value={autoRepairMaxAttempts}
								/>
							</div>
						</div>

						<div class="mb-2.5 flex w-full justify-between">
							<div class="self-center text-xs font-medium">
								<Tooltip
									content={$i18n.t(
										'Model id to use for repair calls. Leave blank to use the same model that produced the original widget.'
									)}
								>
									{$i18n.t('Repair model (optional)')}
								</Tooltip>
							</div>
							<div class="flex items-center relative">
								<input
									type="text"
									placeholder={$i18n.t('Use chat model')}
									class="w-56 rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden text-right"
									bind:value={autoRepairModel}
								/>
							</div>
						</div>

						<div class="mb-2.5 flex w-full justify-between">
							<div class="self-center text-xs font-medium">
								<Tooltip
									content={$i18n.t(
										'Reasoning effort to apply on repair model calls. Leave on Default for non-reasoning models — sending an effort to a model that doesn\'t support it can error.'
									)}
								>
									{$i18n.t('Reasoning effort')}
								</Tooltip>
							</div>
							<div class="flex items-center relative">
								<select
									class="w-32 rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden text-right"
									bind:value={autoRepairReasoningEffort}
								>
									<option value="">{$i18n.t('Default')}</option>
									<option value="low">{$i18n.t('Low')}</option>
									<option value="medium">{$i18n.t('Medium')}</option>
									<option value="high">{$i18n.t('High')}</option>
								</select>
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-book-cloth hover:bg-kraft text-white dark:bg-book-cloth dark:text-white dark:hover:bg-kraft transition-colors duration-200 ease-paper rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
