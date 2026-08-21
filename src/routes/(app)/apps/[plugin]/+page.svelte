<script lang="ts">
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { getPluginApp } from '$lib/apis/plugins';

	$: pluginId = $page.params.plugin;
	$: token = browser ? (localStorage.token ?? '') : '';

	$: if (browser && pluginId) {
		void getPluginApp(token, pluginId).then((app) => {
			if (app) void goto(`/apps/${pluginId}/${app.default_page}`, { replaceState: true });
		});
	}
</script>

<div class="flex h-full items-center justify-center text-sm text-gray-500">Loading app…</div>
