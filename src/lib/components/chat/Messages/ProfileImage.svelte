<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { safeImageUrl } from '$lib/utils/safeImageUrl';

	export let className = 'size-8';
	// LICENSE covers this Open WebUI fallback logo.
	// Do not alter, remove, obscure, or replace it except as LICENSE permits:
	// https://docs.openwebui.com/license.
	export let src = `${WEBUI_BASE_URL}/static/favicon.png`;
</script>

<img
	aria-hidden="true"
	src={safeImageUrl(src)}
	class=" {className} object-cover rounded-2xl"
	alt="profile"
	draggable="false"
/>
