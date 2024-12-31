<script lang="ts">
	import XMark from '$lib/components/icons/XMark.svelte';

	export let threadId = null;
	export let channel = null;

	export let onClose = () => {};
</script>

<div class="flex flex-col w-full h-full bg-gray-50 dark:bg-gray-850 px-3.5 py-3">
	<div class="flex items-center justify-between">
		<div class=" font-medium text-lg">Thread</div>

		<div>
			<button
				class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 p-2"
				on:click={() => {
					onClose();
				}}
			>
				<XMark />
			</button>
		</div>
	</div>
	{threadId}

	{channel}
</div>
