<script lang="ts">
	import { settings } from '$lib/stores';

	export let src = '/user.png';
</script>

<div class={$settings?.chatDirection === 'LTR' ? "mr-4" : "ml-4"}>
	<img {src} class=" max-w-[28px] object-cover rounded-full" alt="profile" draggable="false" />
</div>
