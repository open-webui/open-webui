<script lang="ts">
	import Modal from '../common/Modal.svelte';

	import Tags from '../common/Tags.svelte';

	export let tags;
	export let deleteTag: (tag: string) => void;
	export let addTag: (tag: string) => void;

	export let show = false;
</script>

<Modal bind:show size="xs">
	<div class="px-4 pt-4 pb-5 w-full flex flex-col justify-center">
		<Tags {tags} {deleteTag} {addTag} />
	</div>
</Modal>
