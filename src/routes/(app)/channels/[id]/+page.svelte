<script lang="ts">
	import { page } from '$app/stores';

	import Channel from '$lib/components/channel/Channel.svelte';
</script>

<Channel id={$page.params.id} />
