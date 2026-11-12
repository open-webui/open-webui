export type Sample = {
	start: number;
	first?: number;
	end?: number;
	status: string;
	stream?: boolean;
};

export function number(value: unknown): number | undefined {
	return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : undefined;
}
export function format(value: unknown, unit = '', locale?: string): string {
	const n = number(value);
	return n === undefined ? '—' : `${n.toLocaleString(locale, { maximumFractionDigits: 2 })}${unit}`;
}
export function metrics(usage: Record<string, unknown> = {}) {
	const u = usage ?? {};
	return {
		input: number(u.input_tokens) ?? number(u.prompt_tokens),
		output: number(u.output_tokens) ?? number(u.completion_tokens),
		speed: number(u.predicted_per_second),
		promptSpeed: number(u.prompt_per_second),
		promptMs: number(u.prompt_ms),
		generationMs: number(u.predicted_ms)
	};
}

// Open WebUI forwards both raw deltas and normalized response events.
// A terminal-only/non-stream response cannot establish browser TTFT.
export function observeSample(sample: Sample, data: any, now: number): Sample {
	if (sample.end !== undefined) return sample;
	const text = (value: unknown) => typeof value === 'string' && value.trim().length > 0;
	const delta = data?.choices?.[0]?.delta;
	const typedDelta =
		[
			'response.output_text.delta',
			'response.reasoning_text.delta',
			'response.reasoning_summary_text.delta'
		].includes(data?.type) && text(data?.delta);
	const snapshot =
		Array.isArray(data?.output) &&
		data.output.some(
			(item: any) =>
				['message', 'reasoning'].includes(item?.type) &&
				[
					...(Array.isArray(item?.content) ? item.content : []),
					...(Array.isArray(item?.summary) ? item.summary : [])
				].some((part: any) => text(part?.text))
		);
	const terminal =
		data?.done || data?.error || ['response.failed', 'response.incomplete'].includes(data?.type);
	const meaningful =
		typedDelta ||
		text(delta?.content) ||
		text(delta?.reasoning_content) ||
		text(delta?.reasoning) ||
		text(delta?.thinking) ||
		(!terminal && (text(data?.content) || snapshot));
	const next = { ...sample };
	if (
		next.stream !== false &&
		next.first === undefined &&
		meaningful &&
		!data?.choices?.[0]?.message
	)
		next.first = now;
	if (terminal) {
		next.end = now;
		next.status =
			data?.error || data?.type === 'response.failed'
				? 'error'
				: data?.type === 'response.incomplete'
					? 'cancelled'
					: 'done';
	}
	return next;
}
