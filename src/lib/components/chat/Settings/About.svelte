<script lang="ts">
	import { WEBUI_NAME, config } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
</script>

<div class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class="space-y-6 overflow-y-auto max-h-[28rem] lg:max-h-full px-2">
		<div class="flex flex-col space-y-2">
			<h2 class="text-xl font-medium text-gray-800 dark:text-gray-200">WEBSPACEAI</h2>
			<p class="text-base text-gray-700 dark:text-gray-300 leading-relaxed">
				WEBSPACEAI is a cutting-edge platform dedicated to revolutionizing the way businesses and individuals create and manage their online presence. Leveraging the power of artificial intelligence, WEBSPACEAI simplifies website development by offering intuitive tools for designing, building, and optimizing websites without requiring technical expertise.
			</p>
		</div>
	</div>
</div>
