<script>
	import { onMount } from 'svelte';
	import { baseModels, config, models, settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import Models from '$lib/components/workspace/Models.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			})()
		]);
	});
</script>

{#if $baseModels !== null}
	<Models />
{/if}
