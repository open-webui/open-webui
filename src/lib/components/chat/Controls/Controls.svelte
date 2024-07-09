<script>
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';

	export let params = {};
</script>

<div class=" dark:text-white">
	<div class=" flex justify-between dark:text-gray-100 mb-2">
		<div class=" text-lg font-medium self-center font-primary">{$i18n.t('Chat Controls')}</div>
		<button
			class="self-center"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-4" />
		</button>
	</div>

	<div class=" dark:text-gray-200 text-sm font-primary">
		<div>
			<div class="mb-1.5 font-medium">System Prompt</div>

			<div>
				<textarea
					bind:value={params.system}
					class="w-full rounded-lg px-4 py-3 text-sm dark:text-gray-300 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 outline-none resize-none"
					rows="3"
					placeholder="Enter system prompt"
				/>
			</div>
		</div>

		<hr class="my-2 border-gray-100 dark:border-gray-800" />

		<div>
			<div class="mb-1.5 font-medium">Advanced Params</div>

			<div>
				<AdvancedParams bind:params />
			</div>
		</div>
	</div>
</div>
