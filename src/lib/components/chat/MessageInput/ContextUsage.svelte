<script lang="ts">
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';
	import { getOllamaModelInfo } from '$lib/apis/ollama';

	const i18n = getContext('i18n');

	export let history;
	export let selectedModels: string[] = [];

	// Numerator: tokens the most recent response consumed. Only assistant
	// responses carry usage/info token counts, so their presence is enough.
	let used: number | null = null;
	$: {
		const msg = history?.currentId ? history?.messages?.[history.currentId] : null;
		const usage = msg?.usage ?? {};
		const info = msg?.info ?? {};
		if (typeof usage.total_tokens === 'number') {
			used = usage.total_tokens;
		} else if (
			typeof usage.prompt_tokens === 'number' ||
			typeof usage.completion_tokens === 'number'
		) {
			used = (usage.prompt_tokens ?? 0) + (usage.completion_tokens ?? 0);
		} else if (typeof info.total_tokens === 'number') {
			used = info.total_tokens;
		} else if (typeof info.prompt_eval_count === 'number' || typeof info.eval_count === 'number') {
			used = (info.prompt_eval_count ?? 0) + (info.eval_count ?? 0);
		} else {
			used = null;
		}
	}

	// Denominator: the model's context window.
	//  - Ollama models expose the real window; fetch it once from /api/show and cache.
	//  - Other models use a configured num_ctx when present.
	let windowCache: Record<string, number> = {};

	const resolveOllamaWindow = async (id: string) => {
		if (!id || windowCache[id] !== undefined) {
			return;
		}
		try {
			const res = await getOllamaModelInfo(localStorage.token, id);
			const modelInfo = res?.model_info ?? {};
			const key = Object.keys(modelInfo).find((k) => k.endsWith('.context_length'));
			const n = key ? modelInfo[key] : undefined;
			if (typeof n === 'number' && n > 0) {
				windowCache = { ...windowCache, [id]: n };
			}
		} catch {
			// No window available; the gauge falls back to a raw token count.
		}
	};

	$: model = ($models ?? []).find((m) => m.id === selectedModels?.[0]);
	$: if (model?.owned_by === 'ollama' && model?.id) {
		resolveOllamaWindow(model.id);
	}

	let limit: number | null = null;
	$: {
		const cached = model?.id ? windowCache[model.id] : undefined;
		const configured = ((model?.info?.params ?? {}) as Record<string, unknown>).num_ctx;
		const n = typeof cached === 'number' ? cached : configured;
		limit = typeof n === 'number' && n > 0 ? n : null;
	}

	// Once the window is known, show the gauge from the start (0% before the first
	// response); otherwise fall back to the raw count once tokens are reported.
	$: shownUsed = used ?? 0;
	$: percent = limit != null ? Math.min(100, Math.round((shownUsed / limit) * 100)) : 0;

	const RADIUS = 7;
	const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
	$: dashOffset = CIRCUMFERENCE * (1 - percent / 100);

	$: color =
		percent >= 90
			? 'text-red-500'
			: percent >= 75
				? 'text-yellow-500'
				: 'text-gray-400 dark:text-gray-500';

	const fmt = (n: number) => n.toLocaleString();
</script>

{#if limit != null}
	<div
		class="flex items-center gap-1 self-center px-1 text-xs {color}"
		title={`${fmt(shownUsed)} / ${fmt(limit)} ${$i18n.t('tokens')} (${percent}%)`}
	>
		<svg width="16" height="16" viewBox="0 0 18 18" class="-rotate-90 shrink-0">
			<circle
				cx="9"
				cy="9"
				r={RADIUS}
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				class="text-gray-200 dark:text-gray-700"
			/>
			<circle
				cx="9"
				cy="9"
				r={RADIUS}
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-dasharray={CIRCUMFERENCE}
				stroke-dashoffset={dashOffset}
			/>
		</svg>
		<span>{percent}%</span>
	</div>
{:else if used != null}
	<div
		class="flex items-center self-center px-1 text-xs text-gray-400 dark:text-gray-500"
		title={`${fmt(used)} ${$i18n.t('tokens')}`}
	>
		{fmt(used)}
	</div>
{/if}
