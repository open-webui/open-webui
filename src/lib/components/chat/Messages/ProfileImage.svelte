<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { base } from '$app/paths';

	export let className = 'size-8';
	export let src = `${base}/static/favicon.png`;
</script>

<img
	crossorigin="anonymous"
	src={src === ''
		? `${WEBUI_BASE_URL}/static/favicon.png`
		: src.startsWith(WEBUI_BASE_URL) ||
			  src.startsWith('https://www.gravatar.com/avatar/') ||
			  src.startsWith('data:') ||
			  src.startsWith('/')
			? src
			: `${base}/user.png`}
	class=" {className} object-cover rounded-full -translate-y-[1px]"
	alt="profile"
	draggable="false"
/>
