<script lang="ts">
	import { onDestroy } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getTraceDetail, type TraceDetail } from '$lib/apis/analytics';

	export let traceId: string | null = null;
	export let onClose: () => void = () => {};

	let detail: TraceDetail | null = null;
	let loading = false;
	let error: string | null = null;
	let inputOpen = true;
	let outputOpen = true;

	const load = async (id: string) => {
		loading = true;
		error = null;
		detail = null;
		try {
			const token = localStorage.getItem('token') || '';
			detail = await getTraceDetail(token, id);
		} catch (e: any) {
			error = typeof e === 'string' ? e : e?.detail || e?.message || '불러오기 실패';
		} finally {
			loading = false;
		}
	};

	$: if (traceId) load(traceId);

	const handleKey = (ev: KeyboardEvent) => {
		if (ev.key === 'Escape' && traceId) onClose();
	};

	if (typeof window !== 'undefined') {
		window.addEventListener('keydown', handleKey);
		onDestroy(() => window.removeEventListener('keydown', handleKey));
	}

	const formatLatency = (ms: number): string =>
		ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`;

	const formatTime = (iso: string): string => {
		try {
			return new Date(iso).toLocaleString();
		} catch {
			return iso;
		}
	};
</script>

{#if traceId}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 bg-black/40"
		on:click={onClose}
		on:keydown={(e) => e.key === 'Enter' && onClose()}
		role="button"
		tabindex="0"
		aria-label="close"
		transition:fade={{ duration: 150 }}
	></div>

	<!-- Drawer -->
	<aside
		class="fixed top-0 right-0 z-50 h-full w-full sm:w-[480px] lg:w-[560px] bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 shadow-xl flex flex-col"
		transition:fly={{ x: 400, duration: 200 }}
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
			<div class="min-w-0">
				<h3 class="text-sm font-semibold text-gray-900 dark:text-white truncate">
					{detail?.user?.name || detail?.user?.id || '트레이스 상세'}
				</h3>
				{#if detail}
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						{formatTime(detail.timestamp)}
					</p>
				{/if}
			</div>
			<button
				type="button"
				class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
				on:click={onClose}
				aria-label="닫기"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
					<path
						d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
					/>
				</svg>
			</button>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-4 space-y-4">
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<Spinner className="size-6" />
				</div>
			{:else if error}
				<div class="text-sm text-red-600 dark:text-red-400 py-4">{error}</div>
			{:else if detail}
				<!-- Metric grid -->
				<div class="grid grid-cols-2 gap-2 text-sm">
					<div class="bg-gray-50 dark:bg-gray-800 rounded p-2.5">
						<p class="text-xs text-gray-500 dark:text-gray-400">응답시간</p>
						<p class="font-semibold text-gray-900 dark:text-white mt-0.5">
							{formatLatency(detail.latency_ms)}
						</p>
					</div>
					<div class="bg-gray-50 dark:bg-gray-800 rounded p-2.5">
						<p class="text-xs text-gray-500 dark:text-gray-400">비용</p>
						<p class="font-semibold text-green-600 dark:text-green-400 mt-0.5">
							${detail.total_cost_usd.toFixed(4)}
						</p>
					</div>
					<div class="bg-gray-50 dark:bg-gray-800 rounded p-2.5">
						<p class="text-xs text-gray-500 dark:text-gray-400">토큰 (input)</p>
						<p class="font-semibold text-gray-900 dark:text-white mt-0.5">
							{detail.input_tokens.toLocaleString()}
						</p>
					</div>
					<div class="bg-gray-50 dark:bg-gray-800 rounded p-2.5">
						<p class="text-xs text-gray-500 dark:text-gray-400">토큰 (output)</p>
						<p class="font-semibold text-gray-900 dark:text-white mt-0.5">
							{detail.output_tokens.toLocaleString()}
						</p>
					</div>
				</div>

				{#if detail.model}
					<div class="text-xs text-gray-500 dark:text-gray-400">
						모델 <span class="font-mono text-gray-700 dark:text-gray-300">{detail.model}</span>
					</div>
				{/if}

				<!-- Input preview -->
				{#if detail.input_preview}
					<div class="border border-gray-200 dark:border-gray-700 rounded">
						<button
							type="button"
							class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800"
							on:click={() => (inputOpen = !inputOpen)}
						>
							<span>입력 미리보기</span>
							<span class="text-gray-400">{inputOpen ? '−' : '+'}</span>
						</button>
						{#if inputOpen}
							<pre
								class="px-3 py-2 text-xs whitespace-pre-wrap break-words font-mono text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 max-h-48 overflow-y-auto">{detail.input_preview}</pre>
						{/if}
					</div>
				{/if}

				<!-- Output preview -->
				{#if detail.output_preview}
					<div class="border border-gray-200 dark:border-gray-700 rounded">
						<button
							type="button"
							class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800"
							on:click={() => (outputOpen = !outputOpen)}
						>
							<span>응답 미리보기</span>
							<span class="text-gray-400">{outputOpen ? '−' : '+'}</span>
						</button>
						{#if outputOpen}
							<pre
								class="px-3 py-2 text-xs whitespace-pre-wrap break-words font-mono text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 max-h-64 overflow-y-auto">{detail.output_preview}</pre>
						{/if}
					</div>
				{/if}

				<!-- Observations -->
				{#if detail.observations && detail.observations.length > 0}
					<div>
						<h4 class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">
							Span 분포
						</h4>
						<ul class="text-xs space-y-1">
							{#each detail.observations as o}
								<li class="flex items-center justify-between font-mono text-gray-700 dark:text-gray-300">
									<span class="truncate">{o.name}</span>
									<span class="text-gray-500 dark:text-gray-400">{formatLatency(o.latency_ms)}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Footer -->
		{#if detail?.langfuse_url}
			<div class="border-t border-gray-200 dark:border-gray-700 px-4 py-3">
				<a
					href={detail.langfuse_url}
					target="_blank"
					rel="noopener noreferrer"
					class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
				>
					Langfuse에서 상세 분석 →
				</a>
			</div>
		{/if}
	</aside>
{/if}
