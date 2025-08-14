<!-- PATCH REDIRECT TO WAS -->
<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
    
	onMount(async () => {
		const WAS_REDIRECT = import.meta.env.PUBLIC_WAS_REDIRECT || false;
		WAS_REDIRECT ? window.open(WAS_REDIRECT, '_blank') : goto("/"); 
	});
</script>
<!-- /PATCH REDIRECT TO WAS -->
