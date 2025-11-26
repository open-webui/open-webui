<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils';
	import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Check, Copy, RotateCcw } from 'lucide-svelte';

	export let show = false;
	export let loadingTranslation = false;
	export let isTranslated = false;

	const dispatch = createEventDispatcher();

	const languages = [
		{ code: 'zh', name: '中文', flag: '🇨🇳' },
		{ code: 'ja', name: '日本語', flag: '🇯🇵' },
		{ code: 'ko', name: '한국어', flag: '🇰🇷' },
		{ code: 'en', name: 'English', flag: '🇺🇸' }
	];

	const handleSelect = (langCode: string) => {
		dispatch('select', langCode);
	};

	const handleRestore = () => {
		dispatch('restore');
	};

	const handleCopy = () => {
		dispatch('copy');
	};
</script>

{#if show}
	<div class="fixed inset-0 z-50" on:click={() => (show = false)}>
		<div class="fixed inset-0 bg-black/50" />
		<div class="fixed inset-0 flex items-center justify-center p-4">
			<div 
				class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 w-full max-w-sm"
				in:flyAndScale
				out:flyAndScale
				on:click|stopPropagation
			>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{isTranslated ? '翻译选项' : '选择翻译语言'}
					</h3>
					<button
						on:click={() => (show = false)}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				
				{#if isTranslated}
					<div class="space-y-2 mb-4">
						<Button
							variant="outline"
							size="sm"
							on:click={handleRestore}
							class="w-full justify-start"
							disabled={loadingTranslation}
						>
							<RotateCcw class="w-4 h-4 mr-2" />
							还原原文
						</Button>
						
						<Button
							variant="outline"
							size="sm"
							on:click={handleCopy}
							class="w-full justify-start"
							disabled={loadingTranslation}
						>
							<Copy class="w-4 h-4 mr-2" />
							复制翻译
						</Button>
					</div>
					<hr class="border-gray-200 dark:border-gray-700 mb-4" />
				{/if}
				
				<div class="space-y-2">
					{#each languages as lang}
						<Button
							variant="ghost"
							size="sm"
							on:click={() => handleSelect(lang.code)}
							class="w-full justify-start hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
							disabled={loadingTranslation}
						>
							<div class="flex items-center w-full">
								<span class="mr-3 text-lg">{lang.flag}</span>
								<span class="text-gray-800 dark:text-gray-200">{lang.name}</span>
								{#if loadingTranslation}
									<div class="ml-auto">
										<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900 dark:border-gray-100"></div>
									</div>
								{/if}
							</div>
						</Button>
					{/each}
				</div>
			</div>
		</div>
	</div>
{/if}