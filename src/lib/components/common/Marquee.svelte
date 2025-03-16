<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import { onMount } from 'svelte';

	let idx = 0;

	export let className = '';
	export let words = ['lorem', 'ipsum'];
	export let duration = 4000;

	onMount(() => {
		setInterval(async () => {
			if (idx === words.length - 1) {
				idx = 0;
			} else {
				idx = idx + 1;
			}
		}, duration);
	});
</script>

<div class={className}>
	<div>
		{#key idx}
			<div class=" marquee-item" in:fly={{ y: '30%', duration: 1000 }}>
				{words.at(idx)}
			</div>
		{/key}
	</div>
</div>
