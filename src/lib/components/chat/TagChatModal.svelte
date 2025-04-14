<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';

	import Tags from '../common/Tags.svelte';

	const i18n = getContext('i18n');


	interface Props {
		tags: any;
		deleteTag: Function;
		addTag: Function;
		show?: boolean;
	}

	let {
		tags,
		deleteTag,
		addTag,
		show = $bindable(false)
	}: Props = $props();
</script>

<Modal bind:show size="xs">
	<div class="px-4 pt-4 pb-5 w-full flex flex-col justify-center">
		<Tags
			{tags}
			on:delete={(e) => {
				deleteTag(e.detail);
			}}
			on:add={(e) => {
				addTag(e.detail);
			}}
		/>
	</div>
</Modal>
