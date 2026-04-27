<script lang="ts">
	import FunctionGraph from './Markdown/FunctionGraph.svelte';

	export let title: string = 'f(x) = sin(x)';
	export let template: 'function' | 'polar' | 'parametric' | 'vector_field' = 'function';

	// 템플릿별 기본 GraphSpec 목업
	const templateSpecs: Record<string, any> = {
		function: {
			type: 'function_2d',
			expressions: ['sin(x)'],
			domain: { x: [-6.28, 6.28] },
			title: 'f(x) = sin(x)'
		},
		polar: {
			type: 'polar',
			expressions: ['cos(2 * theta)'],
			domain: { theta: [0, 6.28] },
			title: 'r = cos(2θ)'
		},
		parametric: {
			type: 'parametric_2d',
			expressions: [['cos(t)', 'sin(t)']],
			domain: { t: [0, 6.28] },
			title: '원 (매개변수 곡선)'
		},
		vector_field: {
			type: 'function_2d',
			expressions: ['sin(x) * cos(y)'],
			domain: { x: [-3, 3] },
			title: 'f(x,y) = sin(x)cos(y)'
		}
	};

	const templateLabels: Record<string, string> = {
		function: '일반 함수',
		polar: '극좌표',
		parametric: '매개변수 곡선',
		vector_field: '벡터장'
	};

	let selectedTemplate = template;
	$: spec = templateSpecs[selectedTemplate];
</script>

<div class="rounded-xl border border-teal-200 dark:border-teal-800/50 overflow-hidden mb-3">
	<!-- 헤더 -->
	<div class="bg-teal-50 dark:bg-teal-950/30 px-4 py-2.5 flex items-center gap-2 border-b border-teal-200 dark:border-teal-800/40 flex-wrap">
		<span class="text-teal-600">📈</span>
		<span class="text-sm font-semibold text-teal-900 dark:text-teal-200">{title}</span>
		<div class="ml-auto flex gap-1">
			{#each Object.keys(templateSpecs) as tmpl}
				<button
					class="px-2 py-0.5 rounded text-xs transition
						{selectedTemplate === tmpl
							? 'bg-teal-600 text-white'
							: 'border border-teal-300 dark:border-teal-700 text-teal-600 dark:text-teal-400 hover:bg-teal-100 dark:hover:bg-teal-900/30'}"
					on:click={() => (selectedTemplate = tmpl)}
				>
					{templateLabels[tmpl]}
				</button>
			{/each}
		</div>
	</div>

	<!-- 그래프 영역 -->
	<div class="bg-white dark:bg-gray-900/50 p-2">
		{#if spec}
			<FunctionGraph {spec} />
		{/if}
	</div>
</div>
