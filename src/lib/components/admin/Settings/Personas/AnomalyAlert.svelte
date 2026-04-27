<script lang="ts">
	import type { AnalyticsSummary } from '$lib/apis/analytics';

	export let summary: AnalyticsSummary | null;

	type Severity = 'warn' | 'critical';
	type Anomaly = { severity: Severity; message: string };

	const detect = (s: AnalyticsSummary | null): Anomaly[] => {
		if (!s) return [];
		const out: Anomaly[] = [];

		// 1. p95 latency surge based on daily cost halves as proxy for activity
		// (no per-day latency series; we use today's p95 vs threshold)
		// Better: keep simple — only fire if p95 is itself critical
		if (s.p95_latency_ms > 3000) {
			out.push({
				severity: 'critical',
				message: `응답시간 급증 — p95 ${(s.p95_latency_ms / 1000).toFixed(2)}s`
			});
		}

		// 2. Error rate
		if (s.error_rate > 0.05) {
			out.push({
				severity: 'critical',
				message: `에러율 ${(s.error_rate * 100).toFixed(1)}% 발생`
			});
		} else if (s.error_rate > 0.01) {
			out.push({
				severity: 'warn',
				message: `에러율 ${(s.error_rate * 100).toFixed(2)}% 관찰`
			});
		}

		// 3. Single-user cost concentration
		const topUsers = s.top_token_users || [];
		const topUser = topUsers[0];
		if (topUser && s.today_cost_usd > 0) {
			const share = topUser.cost / Math.max(s.today_cost_usd, 1e-9);
			if (share > 0.3) {
				const label = topUser.name || topUser.user_id.slice(0, 8);
				out.push({
					severity: 'warn',
					message: `특정 사용자 비용 점유 ${(share * 100).toFixed(0)}% (${label})`
				});
			}
		}

		// 4. Single-model concentration
		const topModels = s.top_models || [];
		const topModel = topModels[0];
		const totalModelCount = topModels.reduce((sum, m) => sum + m.count, 0);
		if (topModel && totalModelCount > 0) {
			const modelShare = topModel.count / totalModelCount;
			if (modelShare > 0.8 && totalModelCount >= 5) {
				out.push({
					severity: 'warn',
					message: `특정 모델 편중 ${(modelShare * 100).toFixed(0)}% (${topModel.model})`
				});
			}
		}

		// 5. Cost surge: late-half avg vs early-half avg (>50% increase)
		if (s.daily && s.daily.length >= 4) {
			const mid = Math.floor(s.daily.length / 2);
			const first = s.daily.slice(0, mid);
			const second = s.daily.slice(mid);
			const avg = (arr: typeof s.daily) =>
				arr.reduce((sum, p) => sum + p.cost, 0) / arr.length;
			const a = avg(first);
			const b = avg(second);
			if (a > 0 && (b - a) / a > 0.5) {
				out.push({
					severity: 'warn',
					message: `비용 급증 — 후반 평균 +${(((b - a) / a) * 100).toFixed(0)}%`
				});
			}
		}

		return out;
	};

	$: anomalies = detect(summary);
</script>

{#if anomalies.length > 0}
	<div
		class="anomaly-alert border border-red-200 dark:border-red-900/50 bg-red-50/60 dark:bg-red-900/15 rounded-lg p-3"
		role="alert"
	>
		<div class="flex items-start gap-2">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-5 text-red-500 shrink-0 mt-0.5"
			>
				<path
					fill-rule="evenodd"
					d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
					clip-rule="evenodd"
				/>
			</svg>
			<div class="flex-1 min-w-0">
				<h4 class="text-sm font-semibold text-red-900 dark:text-red-200">이상 감지</h4>
				<ul class="mt-1.5 space-y-1">
					{#each anomalies as a}
						<li class="flex items-center gap-2 text-sm text-red-800 dark:text-red-200">
							<span
								class="inline-block w-1.5 h-1.5 rounded-full {a.severity === 'critical'
									? 'bg-red-500'
									: 'bg-yellow-500'}"
							></span>
							<span>{a.message}</span>
						</li>
					{/each}
				</ul>
			</div>
		</div>
	</div>
{/if}
