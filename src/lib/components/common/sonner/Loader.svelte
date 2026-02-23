<script>export let visible;
const bars = Array(12).fill(0);
</script>

<div class="sonner-loading-wrapper" data-visible={visible}>
	<div class="sonner-spinner">
		{#each bars as _, i (i)}
			<div class="sonner-loading-bar"></div>
		{/each}
	</div>
</div>
