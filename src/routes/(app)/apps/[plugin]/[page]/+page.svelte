<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import PluginPageHost from '$lib/components/plugins/PluginPageHost.svelte';

	$: pluginId = $page.params.plugin;
	$: pageId = $page.params.page;
	$: token = browser ? (localStorage.token ?? '') : '';
</script>

<div class="h-full min-h-0 overflow-auto p-4 md:p-6">
	<PluginPageHost {pluginId} {pageId} {token} />
</div>
