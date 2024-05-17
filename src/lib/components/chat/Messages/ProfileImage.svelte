<script lang="ts">
	import { settings } from '$lib/stores';

	export let src = '/user.png';
</script>

<div class={$settings?.chatDirection === 'LTR' ? "mr-3" : "ml-3"}>
	<img
		crossorigin="anonymous"
		{src}
		class=" w-8 object-cover rounded-full"
		alt="profile"
		draggable="false"
	/>
</div>
