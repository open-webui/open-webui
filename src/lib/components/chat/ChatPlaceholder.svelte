<script lang="ts">
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { marked } from 'marked';

	import { config, models as _models, temporaryChatEnabled } from '$lib/stores';
	import { onMount, onDestroy, getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from './Suggestions.svelte';
	import { sanitizeResponseContent } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';

	const i18n = getContext('i18n');

	export let modelIds = [];
	export let models = [];
	export let atSelectedModel;

	export let onSelect = (e) => {};

	let mounted = false;
	let selectedModelIdx = 0;

	$: if (modelIds.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = modelIds.map((id) => $_models.find((m) => m.id === id));

	onMount(() => {
		mounted = true;
		document.querySelector('.app > div')?.classList.add('copilot-landing-active-surface');

		return () => {
			document.querySelector('.app > div')?.classList.remove('copilot-landing-active-surface');
		};
	});

	onDestroy(() => {
		document.querySelector('.app > div')?.classList.remove('copilot-landing-active-surface');
	});
</script>

{#key mounted}
	<div class="copilot-landing-shell m-auto w-full max-w-6xl px-8 lg:px-20">
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
								sanitizeResponseContent(
									models[selectedModelIdx]?.info?.meta?.description ?? ''
								).replaceAll('\n', '<br>')
							)}
							placement="right"
						>
							<img
								src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}`}
								class=" size-[2.7rem] rounded-full border-[1px] border-gray-100 dark:border-none"
								alt="logo"
								draggable="false"
								on:error={(e) => {
									e.currentTarget.src = '/favicon.png';
								}}
							/>
						</Tooltip>
					</button>
				{/each}
			</div>
		</div>

		{#if $temporaryChatEnabled}
			<Tooltip
				content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
				className="w-full flex justify-start mb-0.5"
				placement="top"
			>
				<div class="flex items-center gap-2 text-[#0f2b48] text-lg mt-2 w-fit">
					<EyeSlash strokeWidth="2.5" className="size-5" />{$i18n.t('Temporary Chat')}
				</div>
			</Tooltip>
		{/if}

		<div
			class=" mt-2 mb-4 text-3xl text-[#0f2b48] text-left flex items-center gap-4 font-primary"
		>
			<div>
				<div class=" capitalize line-clamp-1" in:fade={{ duration: 200 }}>
					VenomX
				</div>

				<div in:fade={{ duration: 200, delay: 200 }}>
					{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
						<div class="mt-0.5 text-base font-normal text-[#1d436b] line-clamp-3 markdown">
							{@html marked.parse(
								sanitizeResponseContent(
									models[selectedModelIdx]?.info?.meta?.description
								).replaceAll('\n', '<br>')
							)}
						</div>
						{#if models[selectedModelIdx]?.info?.meta?.user}
							<div class="mt-0.5 text-sm font-normal text-[#2a4e73]">
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
						<div class=" text-[#2a4e73] line-clamp-1 font-p">
							{$i18n.t('How can I help you today?')}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class=" w-full font-primary" in:fade={{ duration: 200, delay: 300 }}>
			<Suggestions
				className="items-start"
				chipMode={true}
				suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
					models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
					$config?.default_prompt_suggestions ??
					[]}
				{onSelect}
			/>
		</div>
	</div>
{/key}
