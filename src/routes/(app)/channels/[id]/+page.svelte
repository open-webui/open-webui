<script lang="ts">
	import { page } from '$app/stores';

	import Channel from '$lib/components/channel/Channel.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
</script>

<Sidebar />
<Channel id={$page.params.id} />
