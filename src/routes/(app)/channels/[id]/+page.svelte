<script lang="ts">
	import { page } from '$app/state';

	import Channel from '$lib/components/channel/Channel.svelte';
</script>

<Channel id={page.params.id} />
