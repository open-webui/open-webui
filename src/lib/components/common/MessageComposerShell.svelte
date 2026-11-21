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
	class="flex-1 flex flex-col relative w-full shadow-[0_6px_24px_-4px_rgba(0,0,0,0.1)] rounded-3xl border border-base-200/60 dark:border-base-850/40 transition px-0.5 bg-base-0/60 dark:bg-base-900/50 backdrop-blur-md dark:text-base-100"
>
	<slot />
</div>
