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

	const submitHandler = async () => {
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
			DATA_VIZ_MODULE_ELICITATION_PROMPT: elicitationPrompt
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
				{/if}
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
