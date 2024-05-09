<script lang="ts">
        import { WEBUI_DEFAULT_USER_ICON } from '$lib/constants';
	export let src = WEBUI_DEFAULT_USER_ICON;
</script>

<div class=" mr-4">
	<img {src} class=" max-w-[28px] object-cover rounded-full" alt="profile" draggable="false" />
</div>
