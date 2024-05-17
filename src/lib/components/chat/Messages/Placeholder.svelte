<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { user } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from '../MessageInput/Suggestions.svelte';

	const i18n = getContext('i18n');

	export let models = [];
	export let modelfiles = [];

	export let submitPrompt;
	export let suggestionPrompts;

	let mounted = false;
	let modelfile = null;
	let selectedModelIdx = 0;

	$: modelfile =
		models[selectedModelIdx] in modelfiles ? modelfiles[models[selectedModelIdx]] : null;

	$: if (models.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	onMount(() => {
		mounted = true;
	});
</script>

{#key mounted}
	<div class="m-auto w-full max-w-6xl px-8 lg:px-24 pb-16">
		<div class="flex justify-start">
			<div class="flex -space-x-4 mb-1" in:fade={{ duration: 200 }}>
				{#each models as model, modelIdx}
					<button
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						{#if model in modelfiles}
							<img
								crossorigin="anonymous"
								src={modelfiles[model]?.imageUrl ?? `${WEBUI_BASE_URL}/static/favicon.png`}
								alt="modelfile"
								class=" size-[2.7rem] rounded-full border-[1px] border-gray-200 dark:border-none"
								draggable="false"
							/>
						{:else}
							<img
								crossorigin="anonymous"
								src={$i18n.language === 'dg-DG'
									? `/doge.png`
									: `${WEBUI_BASE_URL}/static/favicon.png`}
								class=" size-[2.7rem] rounded-full border-[1px] border-gray-200 dark:border-none"
								alt="logo"
								draggable="false"
							/>
						{/if}
					</button>
				{/each}
			</div>
		</div>

		<div
			class=" mt-2 mb-4 text-3xl text-gray-800 dark:text-gray-100 font-semibold text-left flex items-center gap-4"
		>
			<div>
				<div class=" capitalize line-clamp-1" in:fade={{ duration: 200 }}>
					{#if modelfile}
						{modelfile.title}
					{:else}
						{$i18n.t('Hello, {{name}}', { name: $user.name })}
					{/if}
				</div>

				<div in:fade={{ duration: 200, delay: 200 }}>
					{#if modelfile}
						<div class="mt-0.5 text-base font-normal text-gray-500 dark:text-gray-400">
							{modelfile.desc}
						</div>
						{#if modelfile.user}
							<div class="mt-0.5 text-sm font-normal text-gray-400 dark:text-gray-500">
								By <a href="https://openwebui.com/m/{modelfile.user.username}"
									>{modelfile.user.name ? modelfile.user.name : `@${modelfile.user.username}`}</a
								>
							</div>
						{/if}
					{:else}
						<div class=" font-medium text-gray-400 dark:text-gray-500">
							{$i18n.t('How can I help you today?')}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class=" w-full" in:fade={{ duration: 200, delay: 300 }}>
			<Suggestions {suggestionPrompts} {submitPrompt} />
		</div>
	</div>
{/key}
