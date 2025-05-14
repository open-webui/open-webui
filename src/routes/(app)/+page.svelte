<script lang="ts">
	import { onMount } from 'svelte';
	import Chat from '$lib/components/chat/Chat.svelte';
	import Help from '$lib/components/layout/Help.svelte';
	import {
		getCurrentSubscription
	} from '$lib/apis/payments';
	import { subscription } from '$lib/stores';

	// onMount(async () => {
	// 	const sub = await getCurrentSubscription(localStorage.token).catch(error => console.log(error));
	// 	if(sub){
	// 		subscription.set(sub);
	// 	}
	// })
</script>

<!-- <Help /> -->
<Chat />
