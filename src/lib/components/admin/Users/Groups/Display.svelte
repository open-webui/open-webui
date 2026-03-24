<script lang="ts">
	import { getContext } from 'svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let name = '';
	export let color = '';
	export let description = '';
</script>

<div class="space-y-3.5">
	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/40 px-3.5 py-3">
		<div class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
			{$i18n.t('Name')}
		</div>

		<div class="flex-1">
			<input
				class="w-full text-sm font-medium text-gray-800 dark:text-gray-100 bg-transparent placeholder:text-gray-400 dark:placeholder:text-gray-500 outline-none"
				type="text"
				bind:value={name}
				placeholder={$i18n.t('Group Name')}
				autocomplete="off"
				required
			/>
		</div>
	</div>

<!-- <div class="flex flex-col w-full mt-2">
	<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Color')}</div>

	<div class="flex-1">
		<Tooltip content={$i18n.t('Hex Color - Leave empty for default color')} placement="top-start">
			<div class="flex gap-0.5">
				<div class="text-gray-500">#</div>

				<input
					class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
					type="text"
					bind:value={color}
					placeholder={$i18n.t('Hex Color')}
					autocomplete="off"
				/>
			</div>
		</Tooltip>
	</div>npm 
</div> -->

	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/40 px-3.5 py-3">
		<div class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
			{$i18n.t('Description')}
		</div>

		<div class="flex-1">
			<Textarea
				className="w-full text-sm text-gray-700 dark:text-gray-200 bg-transparent placeholder:text-gray-400 dark:placeholder:text-gray-500 outline-none resize-none leading-5"
				rows={4}
				bind:value={description}
				placeholder={$i18n.t('Group Description')}
			/>
		</div>
	</div>
</div>
