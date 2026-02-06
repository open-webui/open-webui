<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { theme } from '$lib/stores';

	export let className = 'size-8';

	$: defaultFavicon = `${WEBUI_BASE_URL}/static/${['dark', 'oled-dark'].includes($theme) ? 'favicon-dark' : 'favicon'}.png`;

	export let src = '';
</script>

<img
	crossorigin="anonymous"
	src={src === ''
		? defaultFavicon
		: src.startsWith(WEBUI_BASE_URL) ||
			  src.startsWith('https://www.gravatar.com/avatar/') ||
			  src.startsWith('data:') ||
			  src.startsWith('/')
			? src
			: `/user.png`}
	class=" {className} object-cover rounded-full -translate-y-[1px]"
	alt="profile"
	draggable="false"
/>
