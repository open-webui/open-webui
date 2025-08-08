<script lang="ts">
	export let animating = false;
	export let className: string;

	const r = Math.random() * Math.PI;
	const r2 = Math.max(Math.random(), 0.05);
	const precomputedVariedSine = (() => {
		const variedSine = [...Array(50)].map((_, i) =>
			Math.abs(
				Math.sin(r + i * Math.PI * 0.1) * 10 +
					Math.sin(r + i * Math.PI * 0.3) * 5 +
					Math.sin(r + i * Math.PI * r2) * 2
			)
		);
		const sineMin = Math.min(...variedSine);
		const sineMax = Math.max(...variedSine);

		return variedSine.map((v) => (v - sineMin) / (sineMax - sineMin));
	})();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 210 40"
	stroke-width="4"
	stroke="currentColor"
	stroke-linecap="round"
	class={className}
>
	{#each Array(21) as _, i}
		<line
			x1={5 + i * 10}
			x2={5 + i * 10}
			y1={20 + precomputedVariedSine[i] * 15}
			y2={20 - precomputedVariedSine[i] * 15}
		>
			{#if animating}
				<animate
					attributeName="y1"
					values={precomputedVariedSine
						.slice(1, 21)
						.map((v) => 20 + v * 15)
						.join(';')}
					dur="2s"
					begin={`${i * 0.1}s`}
					repeatCount="indefinite"
				/>
				<animate
					attributeName="y2"
					values={precomputedVariedSine
						.slice(1, 21)
						.map((v) => 20 - v * 15)
						.join(';')}
					dur="2s"
					begin={`${i * 0.1}s`}
					repeatCount="indefinite"
				/>
			{/if}
		</line>
	{/each}
</svg>
