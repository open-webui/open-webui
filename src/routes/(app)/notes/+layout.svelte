<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, user } from '$lib/stores';
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
			goto('/');
		}

		loaded = true;
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$i18n.t('Notes')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<slot />
{/if}
