<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getBuiltinToolCategories } from '$lib/apis/tools';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	let categories: Record<string, { name: string; description: string; functions: string[] }> = {};
	let allTools: string[] = [];

	export let builtinTools: Record<string, boolean> = {};

	onMount(async () => {
		try {
			categories = await getBuiltinToolCategories(localStorage.token);
			allTools = Object.keys(categories);
			for (const tool of allTools) {
				if (!(tool in builtinTools)) {
					builtinTools[tool] = true;
				}
			}
		} catch (e) {
			console.error('Failed to load builtin tool categories:', e);
		}
	});
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class="self-center text-xs font-medium text-gray-500">{$i18n.t('Builtin Tools')}</div>
	</div>
	<div class="flex items-center mt-2 flex-wrap">
		{#each allTools as tool}
			<div class="flex items-center gap-2 mr-3">
				<Checkbox
					state={builtinTools[tool] !== false ? 'checked' : 'unchecked'}
					on:change={(e) => {
						builtinTools = {
							...builtinTools,
							[tool]: e.detail === 'checked'
						};
					}}
				/>

				<div class="py-0.5 text-sm">
					<Tooltip content={marked.parse(categories[tool]?.description ?? '')}>
						{$i18n.t(categories[tool]?.name ?? tool)}
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>
</div>
