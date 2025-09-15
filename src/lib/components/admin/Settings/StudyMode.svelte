<script lang="ts">
	import { getStudyModeConfig, updateStudyModeConfig } from '$lib/apis';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	const updateStudyModeHandler = async () => {
		studyModeConfig = await updateStudyModeConfig(localStorage.token, studyModeConfig);
	};

	let studyModeConfig = { ENABLE_STUDY_MODE: false, PROMPT: '' };

	const init = async () => {
		studyModeConfig = await getStudyModeConfig(localStorage.token);
	};

	onMount(async () => {
		await init();
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateStudyModeHandler();
		dispatch('save');
	}}
>
	<div class="  overflow-y-scroll scrollbar-hidden h-full pr-1.5">
		<div class=" mb-2.5 text-base font-medium">{$i18n.t('Study Mode')}</div>
		<hr class=" border-gray-100 dark:border-gray-850 my-2" />
		<div class="mb-3.5">
			<div class=" mb-2 font-medium flex items-center justify-between">
				<div class="mb-2.5 flex w-full items-center">
					<div class=" self-center text-xs font-medium mr-1">
						{$i18n.t('Enable Study Mode')}
					</div>
					<Tooltip
						content={$i18n.t(
							'In Study Mode, the Large Language Model does not give straight answers to any question, but instead walks the user through the solution step-by-step.'
						)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
							/>
						</svg>
					</Tooltip>
				</div>
				<Switch bind:state={studyModeConfig.ENABLE_STUDY_MODE} />
			</div>

			{#if studyModeConfig.ENABLE_STUDY_MODE}
				<div class="mb-2.5">
					<div class=" mb-1 text-xs font-medium">{$i18n.t('System Prompt')}</div>

					<Tooltip
						content={$i18n.t('Enter the system prompt to use for Study Mode')}
						placement="top-start"
					>
						<Textarea
							bind:value={studyModeConfig.PROMPT}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
