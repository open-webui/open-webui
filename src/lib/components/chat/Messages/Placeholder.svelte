<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { user } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let models = [];
	export let modelfiles = [];

	let modelfile = null;
	let selectedModelIdx = 0;

	$: modelfile =
		models[selectedModelIdx] in modelfiles ? modelfiles[models[selectedModelIdx]] : null;

	$: if (models.length > 0) {
		selectedModelIdx = models.length - 1;
	}
</script>

{#if models.length > 0}
	<div class="m-auto text-center max-w-md px-2">
		<div class="flex justify-center mt-8">
			<div class="flex -space-x-4 mb-1">
				{#each models as model, modelIdx}
					<button
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						{#if model in modelfiles}
							<img
								src={modelfiles[model]?.imageUrl ?? `${WEBUI_BASE_URL}/static/favicon.png`}
								alt="modelfile"
								class=" w-14 rounded-full border-[1px] border-gray-200 dark:border-none"
								draggable="false"
							/>
						{:else}
							<img
								src={models.length === 1
									? `${WEBUI_BASE_URL}/static/favicon.png`
									: `${WEBUI_BASE_URL}/static/favicon.png`}
								class=" w-14 rounded-full border-[1px] border-gray-200 dark:border-none"
								alt="logo"
								draggable="false"
							/>
						{/if}
					</button>
				{/each}
			</div>
		</div>
		<div class=" mt-2 mb-5 text-2xl text-gray-800 dark:text-gray-100 font-semibold">
			{#if modelfile}
				<span class=" capitalize">
					{modelfile.title}
				</span>
				<div class="mt-0.5 text-base font-normal text-gray-600 dark:text-gray-400">
					{modelfile.desc}
				</div>
				{#if modelfile.user}
					<div class="mt-0.5 text-sm font-normal text-gray-500 dark:text-gray-500">
						By <a href="https://openwebui.com/m/{modelfile.user.username}"
							>{modelfile.user.name ? modelfile.user.name : `@${modelfile.user.username}`}</a
						>
					</div>
				{/if}
			{:else}
				<div class=" line-clamp-1">{$i18n.t('Hello, {{name}}', { name: $user.name })}</div>

				<div>{$i18n.t('How can I help you today?')}</div>
			{/if}
		</div>
	</div>
{/if}
