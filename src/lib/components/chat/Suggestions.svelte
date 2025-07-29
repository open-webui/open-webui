<script lang="ts">

	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import i18n from '$lib/i18n';
	import { settings, WEBUI_NAME, mobile } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';
	import MaterialIcon from '$lib/components/common/MaterialIcon.svelte';
	import SuggestionsIcon from '$lib/components/icons/SuggestionsIcon.svelte';

	const dispatch = createEventDispatcher();

	export let suggestionPrompts: any[] = [];
	export let className = '';
	let sortedPrompts: any[] = [];



	// Track current locale for reactivity
	let currentLocale = localStorage.getItem('locale') || 'en-US';
	
	// Create a reactive statement that updates when locale changes
	$: {
		currentLocale = localStorage.getItem('locale') || 'en-US';
	}
	
	$: if (suggestionPrompts) {
		sortedPrompts = [...(suggestionPrompts ?? [])].sort(() => Math.random() - 0.5);
	}
	
	// Listen for storage changes (when locale is changed from other components)
	onMount(() => {
		const handleStorageChange = (e: StorageEvent) => {
			if (e.key === 'locale') {
				currentLocale = e.newValue || 'en-US';
			}
		};
		
		window.addEventListener('storage', handleStorageChange);
		
		return () => {
			window.removeEventListener('storage', handleStorageChange);
		};
	});
</script>

<!-- <div class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-600 dark:text-gray-400">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{:else}
		

		<div
			class="flex w-full {$settings?.landingPageMode === 'chat'
				? ' -mt-1'
				: 'text-center items-center justify-center'}  self-start text-gray-600 dark:text-gray-400"
		>
			{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
		</div>
	{/if}
</div> -->

<div class="w-full max-w-[1020px] m-auto flex items-center justify-center">
	{#if suggestionPrompts.length > 0}
	<div
	class="gap-[8px] mt-4 w-full justify-center {$mobile
		? 'flex overflow-x-auto scrollbar-none items-center mx-4'
		: 'grid'}"
	style={!$mobile ? 'grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));' : ''}
>
			{#each sortedPrompts as prompt, idx (prompt.id || prompt.content)}
				<button
					class="flex {$mobile
						? 'items-center gap-[4px] flex-shrink-0'
						: 'shadow-custom3 flex-col items-start'} text-typography-subtext hover:text-typography-titles border border-[#E5EBF3] hover:border-[#90C9FF] p-[16px] rounded-[20px] whitespace-nowrap overflow-hidden text-ellipsis transition
							bg-light-bg dark:border-[#2D3642] dark:hover:border-[#004280] dark:hover:text-white"
					style="animation-delay: {idx * 60}ms;"
					on:click={() => {
						const content = $i18n.t(`suggestion.${prompt.id}.content`);
						dispatch('select', content);
					}}
				>
					{#if prompt.icon_name}
						<SuggestionsIcon name={prompt.icon_name} />
					{:else}
						<MaterialIcon name="lightbulb" className="w-[24px] h-[24px]" />
					{/if}
					<div
						class="w-full text-left {$mobile
							? ' '
							: ' mt-[12px]'} text-[14px] leading-[22px] whitespace-nowrap"
					>
						{$i18n.t(`suggestion.${prompt.id}.title`)}
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	/* Waterfall animation for the suggestions */
	@keyframes fadeInUp {
		0% {
			opacity: 0;
			transform: translateY(20px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.waterfall {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
	}
</style>
