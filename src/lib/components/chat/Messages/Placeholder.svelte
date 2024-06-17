<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config, user, models as _models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from '../MessageInput/Suggestions.svelte';

	const i18n = getContext('i18n');

	export let modelIds = [];
	export let models = [];

	export let submitPrompt;

	let mounted = false;
	let selectedModelIdx = 0;

	$: if (modelIds.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = modelIds.map((id) => $_models.find((m) => m.id === id));

	onMount(() => {
		mounted = true;
	});
</script>

{#key mounted}
	<div class="m-auto w-full max-w-6xl px-8 lg:px-24 pb-10">
		<div class="flex justify-start">
			<div class="flex -space-x-4 mb-1" in:fade={{ duration: 200 }}>
				{#each models as model, modelIdx}
					<button
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						<img
							crossorigin="anonymous"
							src={model?.info?.meta?.profile_image_url ??
								($i18n.language === 'dg-DG' ? `/doge.png` : `${WEBUI_BASE_URL}/static/favicon.png`)}
							class=" size-[2.7rem] rounded-full border-[1px] border-gray-200 dark:border-none"
							alt="logo"
							draggable="false"
						/>
					</button>
				{/each}
			</div>
		</div>

		<div
			class=" mt-2 mb-4 text-3xl text-gray-800 dark:text-gray-100 font-semibold text-left flex items-center gap-4"
		>
			<div>
				<div class=" capitalize line-clamp-1" in:fade={{ duration: 200 }}>
					{#if models[selectedModelIdx]?.info}
						{models[selectedModelIdx]?.info?.name}
					{:else}
						{$i18n.t('Hello, {{name}}', { name: $user.name })}
					{/if}
				</div>

				<div in:fade={{ duration: 200, delay: 200 }}>
					{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
						<div class="mt-0.5 text-base font-normal text-gray-500 dark:text-gray-400 line-clamp-3">
							{models[selectedModelIdx]?.info?.meta?.description}
						</div>
						{#if models[selectedModelIdx]?.info?.meta?.user}
							<div class="mt-0.5 text-sm font-normal text-gray-400 dark:text-gray-500">
								By
								{#if models[selectedModelIdx]?.info?.meta?.user.community}
									<a
										href="https://openwebui.com/m/{models[selectedModelIdx]?.info?.meta?.user
											.username}"
										>{models[selectedModelIdx]?.info?.meta?.user.name
											? models[selectedModelIdx]?.info?.meta?.user.name
											: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
									>
								{:else}
									{models[selectedModelIdx]?.info?.meta?.user.name}
								{/if}
							</div>
						{/if}
					{:else}
						<div class=" font-medium text-gray-400 dark:text-gray-500 line-clamp-1">
							{$i18n.t('How can I help you today?')}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class=" w-full" in:fade={{ duration: 200, delay: 300 }}>
			<Suggestions
				suggestionPrompts={models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
					$config.default_prompt_suggestions}
				{submitPrompt}
			/>
		</div>
	</div>
{/key}
