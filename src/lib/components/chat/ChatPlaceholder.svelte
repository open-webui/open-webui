<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { marked } from 'marked';

	import { config, user, models as _models, temporaryChatEnabled } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from './Suggestions.svelte';
	import { sanitizeResponseContent } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';

	const i18n = getContext('i18n') as any;

	export let modelIds: string[] = [];
	export let models: any[] = [];
	export let atSelectedModel;

	export let submitPrompt;

	let mounted = false;
	let selectedModelIdx = 0;

	$: if (modelIds.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = (modelIds ?? []).map((id: string) => $_models?.find((m: any) => m.id === id));

	onMount(() => {
		mounted = true;
	});
</script>

{#key mounted}
	<!-- FIXED: Responsive padding and max-width -->
	<div class="m-auto w-full max-w-6xl px-4 sm:px-6 md:px-8 lg:px-20">
		
		<!-- Model Avatars Section -->
		<div class="flex justify-start">
			<div class="flex -space-x-4 mb-0.5" in:fade={{ duration: 200 }}>
				{#each models as model, modelIdx}
					<button
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						<Tooltip
							content={marked.parse(
								sanitizeResponseContent(models[selectedModelIdx]?.info?.meta?.description ?? '')
							)}
							placement="right"
						>
							<img
								crossorigin="anonymous"
								src={model?.info?.meta?.profile_image_url ??
									($i18n.language === 'dg-DG'
										? `/doge.png`
										: `${WEBUI_BASE_URL}/static/favicon.png`)}
								class="size-10 sm:size-[2.7rem] rounded-full border-[1px] border-gray-100 dark:border-none"
								alt="logo"
								draggable="false"
							/>
						</Tooltip>
					</button>
				{/each}
			</div>
		</div>

		<!-- Temporary Chat Badge -->
		{#if $temporaryChatEnabled}
			<Tooltip
				content={$i18n.t('This chat wont appear in history and your messages will not be saved.')}
				className="w-full flex justify-center mb-0.5"
				placement="top"
			>
				<div class="flex items-center gap-2 text-gray-500 font-medium text-base sm:text-lg my-2 w-fit">
					<EyeSlash strokeWidth="2.5" className="size-4 sm:size-5" />
					{$i18n.t('Temporary Chat')}
				</div>
			</Tooltip>
		{/if}

		<!-- FIXED: Suggestions Grid - Responsive columns -->
		<div class="w-full font-primary mb-4 sm:mb-6" in:fade={{ duration: 200, delay: 300 }}>
			<Suggestions
				className="grid grid-cols-1 sm:grid-cols-2 gap-2"
				suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
					models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
					$config?.default_prompt_suggestions ??
					[]}
				on:select={(e) => {
					submitPrompt(e.detail);
				}}
			/>
		</div>

		<!-- FIXED: Model Name & Description - Responsive text sizes -->
		<div
			class="mt-2 mb-4 text-2xl sm:text-3xl text-gray-800 dark:text-gray-100 font-medium text-left flex items-center gap-4 font-primary"
		>
			<div class="w-full">
				<!-- Model Name -->
				<div class="capitalize line-clamp-1" in:fade={{ duration: 200 }}>
					{#if models[selectedModelIdx]?.name}
						{models[selectedModelIdx]?.name}
					{:else}
						{$i18n.t('Hello, {{name}}', { name: $user?.name })}
					{/if}
				</div>
				
				<!-- Model Description -->
				<div in:fade={{ duration: 200, delay: 200 }}>
					{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
						<div
							class="mt-0.5 text-sm sm:text-base font-normal text-gray-500 dark:text-gray-400 line-clamp-2 sm:line-clamp-3 markdown"
						>
							{@html marked.parse(
								sanitizeResponseContent(models[selectedModelIdx]?.info?.meta?.description ?? '')
							)}
						</div>
						{#if models[selectedModelIdx]?.info?.meta?.user}
							<div class="mt-0.5 text-xs sm:text-sm font-normal text-gray-400 dark:text-gray-500">
								By
								{#if models[selectedModelIdx]?.info?.meta?.user.community}
									<a
										href="https://openwebui.com/m/{models[selectedModelIdx]?.info?.meta?.user
											.username}"
										class="hover:underline"
									>
										{models[selectedModelIdx]?.info?.meta?.user.name
											? models[selectedModelIdx]?.info?.meta?.user.name
											: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}
									</a>
								{:else}
									{models[selectedModelIdx]?.info?.meta?.user.name}
								{/if}
							</div>
						{/if}
					{:else}
						<div class="text-sm sm:text-base font-medium text-gray-400 dark:text-gray-500 line-clamp-1">
							{$i18n.t('How can I help you today?')}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/key}