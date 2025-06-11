<script>
	import { getContext } from 'svelte';
	import UploadIcon from './icons/UploadIcon.svelte';

	export let title = '';
	export let content = '';
	const i18n = getContext('i18n');
</script>

<div class="px-3">
	<div class="flex justify-center mb-3 text-lightGray-100 dark:text-customGray-100">
		<UploadIcon className="size-8"/>
	</div>
	<div class="text-center text-lightGray-100 dark:text-customGray-100 font-medium text-xl z-50">
		{#if title}
			{title}
		{:else}
			{$i18n.t('Add Files')}
		{/if}
	</div>

	<slot
		><div class="px-2 mt-2 text-center text-sm text-lightGray-100 dark:text-customGray-100 w-full">
			{#if content}
				{content}
			{:else}
				{$i18n.t('Drop any files here to add to the conversation')}
			{/if}
		</div>
	</slot>
</div>
