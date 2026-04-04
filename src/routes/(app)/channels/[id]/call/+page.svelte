<script lang="ts">
	import { page } from '$app/stores';

	import ChannelCall from '$lib/components/channel/ChannelCall.svelte';
</script>

<ChannelCall id={$page.params.id} />
