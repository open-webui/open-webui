<script lang="ts">
	import { getStudyModeConfig, updateStudyModeConfig } from '$lib/apis';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let enableStudyMode = false;
	let studyModeSystemPrompt = '';

	const submitHandler = async () => {
		const res = await updateStudyModeConfig(localStorage.token, {
			ENABLE_STUDY_MODE: enableStudyMode,
			STUDY_MODE_SYSTEM_PROMPT: studyModeSystemPrompt
		});

		if (res) {
			toast.success($i18n.t('Settings saved successfully'));
		}
	};

	onMount(async () => {
		const res = await getStudyModeConfig(localStorage.token);

		if (res) {
			enableStudyMode = res.ENABLE_STUDY_MODE;
			studyModeSystemPrompt = res.STUDY_MODE_SYSTEM_PROMPT;
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
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Study Mode')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="  mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Study Mode')}
					</div>
					<div class="flex items-center relative">
						<Switch bind:state={enableStudyMode} />
					</div>
				</div>

				{#if enableStudyMode}
					<div class="mb-2.5 flex w-full flex-col">
						<div class=" self-center text-xs font-medium mb-1">
							{$i18n.t('System Prompt')}
						</div>

						<textarea
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
							rows="6"
							placeholder={$i18n.t('Enter system prompt for study mode...')}
							bind:value={studyModeSystemPrompt}
						></textarea>
					</div>
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
