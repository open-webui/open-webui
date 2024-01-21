<script lang="ts">
	import { selectedUiConfigId, theme, uiConfigs } from '$lib/stores';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';

	export let models: any[] = [];
	export let modelfiles: any[] = [];

	let modelfile: any = null;
	let selectedModelIdx = 0;

	let orgLogo: any;
	let tagline: string;
	let selectedTheme: string = get(theme);

	onMount(() => {
		const configs: any[] = get(uiConfigs);
		const selectedConfigId = get(selectedUiConfigId);

		if (configs.length > 0 && selectedConfigId) {
			const selectedUiConfig = configs.find((config) => config.id === selectedConfigId);
			if (selectedUiConfig && selectedUiConfig.orgLogo) {
				orgLogo = selectedUiConfig.orgLogo;
			}
			if (selectedUiConfig) {
				tagline = selectedUiConfig.tagline;
			}
		}
		theme.subscribe((value) => {
			selectedTheme = value;
		});
	});


	$: modelfile =
		models[selectedModelIdx] in modelfiles ? modelfiles[models[selectedModelIdx]] : null;

	$: if (models.length > 0) {
		selectedModelIdx = models.length - 1;
	}
</script>

{#if models.length > 0}
	<div class="m-auto text-center max-w-md pb-56 px-2">
		<div class="flex justify-center mt-8">
			<div class="flex -space-x-10">
				{#each models as model, modelIdx}
					<button
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						{#if model in modelfiles}
							<img
								src={modelfiles[model]?.imageUrl ?? '/ollama-dark.png'}
								alt="modelfile"
								class=" w-20 mb-2 rounded-full {models.length > 1
									? ' border-[5px] border-white dark:border-gray-800'
									: ''}"
								draggable="false"
							/>
						{:else}
							<img
								src={orgLogo
									? selectedTheme === 'light'
										? orgLogo.light
										: orgLogo.dark
									: '/ollama-dark.png'}
								class=" w-96 mb-2 {models.length === 1
									? 'invert-[10%]'
									: 'border-[5px] border-white dark:border-gray-800'}  rounded-full"
								alt={orgLogo ? orgLogo.alt : 'ollama'}
								draggable="false"
							/>
						{/if}
					</button>
				{/each}
			</div>
		</div>
		<div class=" mt-2 text-2xl text-gray-800 dark:text-gray-100 font-semibold">
			{#if modelfile}
				<span class=" capitalize">
					{modelfile.title}
				</span>
				<div class="mt-0.5 text-base font-normal text-gray-600 dark:text-gray-400">
					{modelfile.desc}
				</div>
				{#if modelfile.user}
					<div class="mt-0.5 text-sm font-normal text-gray-500 dark:text-gray-500">
						By <a href="https://ollamahub.com/m/{modelfile.user.username}"
							>{modelfile.user.name ? modelfile.user.name : `@${modelfile.user.username}`}</a
						>
					</div>
				{/if}
			{:else}
				{tagline}
			{/if}
		</div>
	</div>
{/if}
