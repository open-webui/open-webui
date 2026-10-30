<script lang="ts">
	import { settings } from '$lib/stores';
	export let id: string | undefined = undefined;
</script>

<div
	{id}
	dir={$settings?.chatDirection === 'RTL'
		? 'rtl'
		: $settings?.chatDirection === 'LTR'
			? 'ltr'
			: 'auto'}
	class="flex-1 flex flex-col relative w-full shadow-sm rounded-2xl border border-gray-100/60 dark:border-gray-800/50 hover:border-gray-100 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800 transition bg-white dark:bg-gray-400/5 dark:text-gray-100"
>
	<slot />
</div>
