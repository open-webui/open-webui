<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let loading = false;
	let wikipediaGroundingEnabled = false;

	const submitHandler = async () => {
		loading = true;

		const res = await updateRAGConfig(localStorage.token, {
			ENABLE_WIKIPEDIA_GROUNDING: wikipediaGroundingEnabled
		});

		if (res) {
			await saveHandler();
			toast.success($i18n.t('Settings saved successfully!'));
		}
		loading = false;
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);
		if (res) {
			wikipediaGroundingEnabled = res?.ENABLE_WIKIPEDIA_GROUNDING ?? true;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={submitHandler}
	role="form"
	aria-label={$i18n.t('Web Grounding Configuration')}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div>
			<div class=" mb-1 text-sm font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Web Grounding')}
			</div>

			<div
				class="flex w-full justify-between items-center"
				role="group"
				aria-labelledby="web-grounding-label"
			>
				<div
					id="web-grounding-label"
					class=" self-center text-xs font-medium text-gray-800 dark:text-gray-200"
				>
					{$i18n.t('Enable Web Grounding')}
				</div>

				<Switch
					bind:state={wikipediaGroundingEnabled}
					aria-describedby="web-grounding-description"
					aria-labelledby="web-grounding-label"
				/>
			</div>
			<div id="web-grounding-description" class="text-xs text-gray-600 dark:text-gray-400 mt-1">
				{$i18n.t(
					'Automatically enhance responses with current, factual information. Works for both English and French queries.'
				)}
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div
			class="text-xs text-gray-600 dark:text-gray-400"
			role="region"
			aria-labelledby="how-it-works-heading"
		>
			<div id="how-it-works-heading" class="mb-2 font-medium text-gray-800 dark:text-gray-200">
				{$i18n.t('How it works:')}
			</div>
			<ul class="list-disc list-inside space-y-1" role="list">
				<li role="listitem">
					{$i18n.t('Uses semantic search over Wikipedia content for factual questions')}
				</li>
				<li role="listitem">
					{$i18n.t('For French queries: translates to English → searches → provides results')}
				</li>
				<li role="listitem">
					{$i18n.t('Provides current, accurate information without disrupting web search')}
				</li>
				<li role="listitem">
					{$i18n.t(
						'Covers global knowledge including people, places, government, and general topics'
					)}
				</li>
			</ul>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 focus:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 text-gray-100 transition rounded-lg flex flex-row space-x-1 items-center {loading
				? ' cursor-not-allowed opacity-75'
				: ''}"
			type="submit"
			disabled={loading}
			aria-label={loading
				? $i18n.t('Saving Web Grounding settings...')
				: $i18n.t('Save Web Grounding settings')}
		>
			{$i18n.t('Save')}

			{#if loading}
				<div class="ml-2 self-center">
					<svg
						class=" w-4 h-4"
						viewBox="0 0 24 24"
						fill="currentColor"
						xmlns="http://www.w3.org/2000/svg"
						><style>
							.spinner_ajPY {
								transform-origin: center;
								animation: spinner_AtaB 0.75s infinite linear;
							}
							@keyframes spinner_AtaB {
								100% {
									transform: rotate(360deg);
								}
							}
						</style><path
							d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
							opacity=".25"
						/><path
							d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
							class="spinner_ajPY"
						/></svg
					>
				</div>
			{/if}
		</button>
	</div>
</form>
