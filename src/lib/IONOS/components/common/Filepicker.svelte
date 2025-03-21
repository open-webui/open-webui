<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	let files: FileList;
	let value = '';

	function change() {
		if (!files || files.length === 0) {
			console.warn('File change handler: no files in collection?');
			return;
		}

		dispatch('selected', [...files]);
	}
</script>

<label class="cursor-pointer">
	<slot />
	<input
		type="file"
		bind:value={value}
		bind:files={files}
		multiple
		on:change={change}
		class="hidden"
	/>
</label>
