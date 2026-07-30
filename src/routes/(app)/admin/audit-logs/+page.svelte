<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, WEBUI_NAME } from '$lib/stores';
	import AuditLogs from '$lib/components/admin/AuditLogs.svelte';

	const i18n: any = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/', { replaceState: true });
			return;
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Audit Logs')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<AuditLogs />
{/if}
