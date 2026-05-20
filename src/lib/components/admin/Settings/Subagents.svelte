<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getSubagentsConfig, updateSubagentsConfig } from '$lib/apis/subagents';
	import { models } from '$lib/stores';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	let enableSubagents = false;
	let defaultModel = '';
	let systemPrompt = '';
	let parentPrompt = '';

	// Cached defaults so the "Reset to default" buttons work without an
	// extra round-trip. Populated on first load when the user hasn't
	// customized the prompts yet (we can't tell apart "user set it to the
	// default text" from "never customized" — the reset button just shows
	// the most-recently-fetched value, which is fine since saving an
	// unchanged value is a no-op).
	let initialSystemPrompt = '';
	let initialParentPrompt = '';

	const submitHandler = async () => {
		try {
			const res = await updateSubagentsConfig(localStorage.token, {
				ENABLE_SUBAGENTS: enableSubagents,
				SUBAGENT_DEFAULT_MODEL: defaultModel,
				SUBAGENT_SYSTEM_PROMPT: systemPrompt,
				SUBAGENT_PARENT_PROMPT: parentPrompt
			});
			if (res) {
				toast.success($i18n.t('Settings saved successfully'));
			}
		} catch (err) {
			console.error(err);
			toast.error(`${err}`);
		}
	};

	onMount(async () => {
		try {
			const res = await getSubagentsConfig(localStorage.token);
			if (res) {
				enableSubagents = !!res.ENABLE_SUBAGENTS;
				defaultModel = res.SUBAGENT_DEFAULT_MODEL ?? '';
				systemPrompt = res.SUBAGENT_SYSTEM_PROMPT ?? '';
				parentPrompt = res.SUBAGENT_PARENT_PROMPT ?? '';
				initialSystemPrompt = systemPrompt;
				initialParentPrompt = parentPrompt;
			}
		} catch (err) {
			console.error(err);
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
		<div>
			<div class="mb-3">
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Subagents')}</div>
				<div class=" text-xs text-gray-500 dark:text-gray-400 mb-2">
					{$i18n.t(
						'Subagents let the parent chat model spawn isolated research workers via the subagent_launch / subagent_continue tools. Each subagent runs in its own context with web search + fetch and returns its synthesized answer.'
					)}
				</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Subagents')}
					</div>
					<div class="flex items-center relative">
						<Switch bind:state={enableSubagents} />
					</div>
				</div>

				{#if enableSubagents}
					<div class="mb-2.5 flex w-full flex-col">
						<div class=" self-center text-xs font-medium mb-1 mr-auto">
							{$i18n.t('Default subagent model')}
						</div>
						<div class=" text-xs text-gray-500 dark:text-gray-400 mb-1">
							{$i18n.t(
								"Empty = fall back to the parent chat's model. A per-chat override (chat.params.subagentModel) still wins when set."
							)}
						</div>
						<select
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={defaultModel}
						>
							<option value="">{$i18n.t('— Use parent model —')}</option>
							{#each $models ?? [] as m}
								<option value={m.id}>{m.name ?? m.id}</option>
							{/each}
						</select>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div class="flex w-full items-center mb-1">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Subagent system prompt')}
							</div>
							<button
								type="button"
								class="ml-auto text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
								on:click|preventDefault={() => {
									systemPrompt = initialSystemPrompt;
								}}
							>
								{$i18n.t('Reset')}
							</button>
						</div>
						<div class=" text-xs text-gray-500 dark:text-gray-400 mb-1">
							{$i18n.t(
								"Prepended to the subagent model's own system prompt. Defines the subagent's role and its stop condition (no tool calls in the final turn = done)."
							)}
						</div>
						<textarea
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
							rows="8"
							placeholder={$i18n.t('Subagent system prompt…')}
							bind:value={systemPrompt}
						></textarea>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div class="flex w-full items-center mb-1">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Parent chat instructions')}
							</div>
							<button
								type="button"
								class="ml-auto text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
								on:click|preventDefault={() => {
									parentPrompt = initialParentPrompt;
								}}
							>
								{$i18n.t('Reset')}
							</button>
						</div>
						<div class=" text-xs text-gray-500 dark:text-gray-400 mb-1">
							{$i18n.t(
								'Appended to the parent chat system prompt when subagents are enabled. Teaches the parent model when and how to call subagent_launch / subagent_continue.'
							)}
						</div>
						<textarea
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
							rows="8"
							placeholder={$i18n.t('Parent chat instructions…')}
							bind:value={parentPrompt}
						></textarea>
					</div>
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
