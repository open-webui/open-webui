<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import { onMount } from 'svelte';

	let idx = $state(0);

	interface Props {
		className?: string;
		words?: any;
		duration?: number;
	}

	let { className = '', words = ['lorem', 'ipsum'], duration = 4000 }: Props = $props();

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
