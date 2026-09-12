<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getSubagentsConfig, setSubagentsConfig } from '$lib/apis/configs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let saving = false;
	let enabled = false;
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
			backgroundEnabled = config?.SUBAGENTS_BACKGROUND_ENABLED ?? false;
			maxConcurrent = Number(config?.SUBAGENTS_MAX_CONCURRENT) || 20;
			maxAsync = Number(config?.SUBAGENTS_MAX_ASYNC) || 20;
			maxIterations = Number(config?.SUBAGENTS_MAX_ITERATIONS) || 30;
			maxOutput = Number(config?.SUBAGENTS_MAX_OUTPUT) || 30000;
			systemPrompt = config?.SUBAGENTS_SYSTEM_PROMPT ?? '';
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
				SUBAGENTS_BACKGROUND_ENABLED: backgroundEnabled,
				SUBAGENTS_MAX_CONCURRENT: maxConcurrent,
				SUBAGENTS_MAX_ASYNC: maxAsync,
				SUBAGENTS_MAX_ITERATIONS: maxIterations,
				SUBAGENTS_MAX_OUTPUT: maxOutput,
				SUBAGENTS_SYSTEM_PROMPT: systemPrompt
			});
			toast.success($i18n.t('Settings saved successfully!'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};
</script>

<form class="flex h-full flex-col justify-between text-sm" on:submit|preventDefault={save}>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Sub-agents')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if loading}
			<div class="flex justify-center py-8"><Spinner className="size-6" /></div>
		{:else}
			<div class="flex flex-col gap-2.5">
				<label class="flex cursor-pointer items-center justify-between">
					<span class="text-xs text-gray-600 dark:text-gray-400">
						{$i18n.t('Enable sub-agents')}
					</span>
					<Switch bind:state={enabled} />
				</label>
				<p class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
					{$i18n.t(
						'Allow the AI to delegate tasks to sub-agents. Each sub-agent creates a real chat with full tool access. Uses additional LLM calls.'
					)}
				</p>

				{#if enabled}
					<div>
						<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-concurrent">
							{$i18n.t('Max concurrent')}
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
						<label class="flex cursor-pointer items-center justify-between">
							<span class="text-xs text-gray-600 dark:text-gray-400">
								{$i18n.t('Enable background sub-agents')}
							</span>
							<Switch bind:state={backgroundEnabled} />
						</label>
						<p class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t(
								'Allow delegated sub-agents to keep running while the parent chat continues.'
							)}
						</p>
					</div>

					{#if backgroundEnabled}
						<div>
							<label class="text-xs text-gray-600 dark:text-gray-400" for="sa-async">
								{$i18n.t('Max background')}
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
							{$i18n.t('Max iterations')}
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
							{$i18n.t('Max output')}
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
							{$i18n.t('System prompt')}
						</label>
						<textarea
							id="sa-prompt"
							bind:value={systemPrompt}
							rows="4"
							placeholder={$i18n.t('You are a sub-agent...')}
							class="mt-1 w-full resize-y rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 font-mono text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
						></textarea>
						<p class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Leave empty for the built-in default.')}
						</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	{#if !loading}
		<div class="flex justify-end pt-6 text-sm font-normal">
			<button
				class="rounded-full bg-black px-3.5 py-1.5 text-sm font-normal text-white transition hover:bg-gray-900 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-gray-100"
				type="submit"
				disabled={saving}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	{/if}
</form>
