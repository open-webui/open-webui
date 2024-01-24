<script lang="ts">
	import Modal from '../common/Modal.svelte';

	export let downloadChat: Function;
	export let shareChat: Function;

	export let show = false;
</script>

<Modal bind:show size="xs">
	<div class="px-4 pt-4 pb-5 w-full flex flex-col justify-center">

		<div class="flex justify-center space-x-1 mt-1.5">

			<button
				class=" self-center rounded-full text-xs font-medium text-gray-700 dark:text-gray-500 underline"
				type="button"
				on:click={() => {
					downloadChat();
					show = false;
				}}
			>
				Als Datei herunterladen
			</button>
		</div>
	</div>
</Modal>
