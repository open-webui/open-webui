<script lang="ts">
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	export let show = false;
</script>

{#if show}
	<div
		class="absolute inset-0 w-full h-full flex z-[9999] touch-none pointer-events-none"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div
			class="absolute w-full h-full backdrop-blur-sm bg-gray-100/50 dark:bg-gray-900/80 flex justify-center"
		>
			<div class="m-auto flex flex-col justify-center">
				<div class="max-w-md">
					<AddFilesPlaceholder />
				</div>
			</div>
		</div>
	</div>
{/if}
