<script lang="ts">
	import EncryptedChannel from '$lib/components/channel/EncryptedChannel.svelte';
	import { page } from '$app/stores';
</script>

<EncryptedChannel id={$page.params.id} />
