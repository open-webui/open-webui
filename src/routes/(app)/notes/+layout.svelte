<script lang="ts">
	import { base } from '$app/paths';
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, functions, config, user, showArchivedChats } from '$lib/stores';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (
			!(
				($config?.features?.enable_notes ?? false) &&
				($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
			)
		) {
			// If the feature is not enabled, redirect to the home page
			goto(`${base}/`);
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Notes')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<slot />
{/if}
