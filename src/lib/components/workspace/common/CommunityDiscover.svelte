<script lang="ts">
	import { getContext } from 'svelte';

	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	export let href = '';
	export let title = '';
	export let description = '';
</script>

<div class="mt-6 px-2">
	<div class="mb-0.5 text-[11px] font-normal text-gray-400 dark:text-gray-600">
		{$i18n.t('Made by Open WebUI Community')}
	</div>

	<a
		class="flex w-full cursor-pointer items-center justify-between gap-3 px-0 py-1 text-left transition"
		{href}
		target="_blank"
	>
		<div class="min-w-0">
			<div class="line-clamp-1 text-[13px] font-normal text-gray-700 dark:text-gray-200">
				{title}
			</div>
			<div class="line-clamp-1 text-xs text-gray-500 dark:text-gray-500">
				{description}
			</div>
		</div>

		<ChevronRight className="size-3.5 shrink-0 text-gray-400 dark:text-gray-600" />
	</a>
</div>
