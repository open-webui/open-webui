<script lang="ts">
	export let size = 20; // default size

	$: componentSize = size * 0.2; // calculate component size based on spinner size
</script>

<!--
@component
### Props
- `size` (number): Specifies the diameter of the spinner in pixels. Default is `20`.

### Styles
- The spinner dynamically adjusts its size and internal components using CSS variables:
- `--spinner-size`: Sets the overall size of the spinner.
- `--component-size`: Defines the size of the internal spinner elements.

-->

<div
	class="spinner"
	style="
		--spinner-size: {size}px;
		--component-size: {componentSize}px;
	"
/>

<style>
	.spinner {
		width: var(--spinner-size);
		height: var(--spinner-size);
		border-radius: 50%;
		background: radial-gradient(farthest-side, #1474c4 calc(100% - var(--component-size)), #0000) top/var(--component-size) var(--component-size) no-repeat, conic-gradient(#0000 30%, #1474c4);
		mask: radial-gradient(farthest-side, #0000 calc(100% - var(--component-size)), #000 0);
		animation: spinner-c7wet2 1s infinite linear;
	}

	@keyframes spinner-c7wet2 {
		100% {
			transform: rotate(1turn);
		}
	}
</style>
