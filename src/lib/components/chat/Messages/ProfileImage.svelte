<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { safeImageUrl } from '$lib/utils/safeImageUrl';

	export let className = 'size-8';
	// LICENSE covers this Open WebUI fallback logo.
	// Do not alter, remove, obscure, or replace it except as LICENSE permits:
	// https://docs.openwebui.com/license.
	const FALLBACK_SRC = `${WEBUI_BASE_URL}/static/gcat.png`;

	export let src = FALLBACK_SRC;
	export let allowExternal = false;
</script>

<img
	aria-hidden="true"
	src={safeImageUrl(src, allowExternal)}
	class=" {className} object-cover rounded-2xl"
	class:bg-gray-900={src?.includes('/static/gcat.')}
	class:p-1={src?.includes('/static/gcat.')}
	alt="profile"
	draggable="false"
	on:error={(e) => {
		if (!e.currentTarget.src.endsWith(FALLBACK_SRC)) {
			e.currentTarget.src = FALLBACK_SRC;
			e.currentTarget.classList.add('bg-gray-900', 'p-1');
		}
	}}
/>
