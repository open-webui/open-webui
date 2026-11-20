<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto, tab: pageTab } = getPageContext();

	import { onMount } from 'svelte';

	import { config, showSidebar, user } from '$lib/stores';

	onMount(() => {
		if (
			!($config?.features as any)?.enable_automations ||
			($user?.role !== 'admin' && !($user?.permissions?.features?.automations ?? false))
		) {
			goto('/');
		}
	});
</script>

<div
	class="flex flex-col w-full h-full max-h-full transition-width duration-200 ease-in-out {$showSidebar &&
	!pageTab
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="min-h-0 flex-1 overflow-hidden">
		<slot />
	</div>
</div>
