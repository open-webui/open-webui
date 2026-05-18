<script lang="ts">
	import { WEBUI_VERSION } from '$lib/constants';
</script>

<div id="tab-about" class="flex flex-col h-full justify-center items-center text-sm">
	<div class="text-center space-y-2">
		<div class="text-lg font-semibold">
			Alyx AI Version
		</div>

		<div class="text-sm text-gray-600 dark:text-gray-300">
			v{WEBUI_VERSION}
		</div>

		<div class="text-xs text-gray-400 dark:text-gray-500">
			(latest)
		</div>
	</div>
</div>
