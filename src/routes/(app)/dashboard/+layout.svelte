<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, user, mobile } from '$lib/stores';
	import { isInstructor } from '$lib/stores';
	import DashboardTopNav from '$lib/components/dashboard/DashboardTopNav.svelte';

	const i18n = getContext('i18n');
	let loaded = false;

	onMount(async () => {
		// Route protection: instructor/admin only
		if (!isInstructor($user)) {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Dashboard')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col h-screen max-h-[100dvh] w-full">
		{#if !$mobile}
			<DashboardTopNav />
		{/if}

		<div class="flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}
