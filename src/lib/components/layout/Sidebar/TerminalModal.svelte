<!-- TerminalModal.svelte -->
<script lang="ts">
	export let show = false;
	export let onClose = () => {};
	export let url = 'https://localhost:5000'; // default fallback
</script>

{#if show}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-[9999]">
		<div
			class="bg-white dark:bg-gray-900 rounded-lg p-4 font-mono w-[98ch] h-[32em] relative overflow-hidden"
		>
			<button class="absolute top-2 right-2 text-gray-500 hover:text-gray-800" on:click={onClose}
				>x</button
			>
			<iframe src={url} class="w-full h-full border-none rounded"></iframe>
		</div>
	</div>
{/if}
