<script lang="ts">
	import { settings } from '$lib/stores';
	import { Falcor_BASE_URL } from '$lib/constants';

	export let className = 'size-8';

	export let src = '/user.png';
</script>

<div class={`flex-shrink-0 ${($settings?.chatDirection ?? 'LTR') === 'LTR' ? 'mr-3' : 'ml-3'}`}>
	<img
		crossorigin="anonymous"
		src={src.startsWith(Falcor_BASE_URL) ||
		src.startsWith('https://www.gravatar.com/avatar/') ||
		src.startsWith('data:') ||
		src.startsWith('/')
			? src
			: `/user.png`}
		class=" {className} object-cover rounded-full -translate-y-[1px]"
		alt="profile"
		draggable="false"
	/>
</div>
