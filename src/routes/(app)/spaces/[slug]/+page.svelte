<script lang="ts">
	import { page } from '$app/stores';

	import SpaceDetail from '$lib/components/space/SpaceDetail.svelte';
</script>

<SpaceDetail slug={$page.params.slug} />
