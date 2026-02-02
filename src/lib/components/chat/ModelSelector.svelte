<script lang="ts">
	import { settings } from '$lib/stores';

	export let selectedModels = ['gpt-5.2-chat-latest'];
</script>

<div class="flex flex-col w-full items-start">
	<div class="flex w-full max-w-fit">
		<div
			class="flex w-full text-left px-0.5 bg-transparent truncate text-lg justify-between {($settings?.highContrastMode ??
			false)
				? 'dark:placeholder-gray-100 placeholder-gray-800'
				: 'placeholder-gray-400'}"
		>
			gpt-5.2-chat-latest
		</div>
	</div>
</div>
