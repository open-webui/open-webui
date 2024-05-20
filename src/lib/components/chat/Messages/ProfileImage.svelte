<script lang="ts">
	import { settings } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let src = '/user.png';
</script>

<div class={($settings?.chatDirection ?? 'LTR') === 'LTR' ? 'mr-3' : 'ml-3'}>
	<img
		crossorigin="anonymous"
		src={src.startsWith(WEBUI_BASE_URL) ||
		src.startsWith('https://www.gravatar.com/avatar/') ||
		src.startsWith('data:') ||
		src.startsWith('/')
			? src
			: `/user.png`}
		class=" w-8 object-cover rounded-full"
		alt="profile"
		draggable="false"
	/>
</div>
