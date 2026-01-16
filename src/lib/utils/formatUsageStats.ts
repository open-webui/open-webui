/**
 * Format usage statistics for display in chat message tooltips.
 * This is a minimal-intrusion utility that beautifies and localizes token usage info.
 */

interface UsageData {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    prompt_tokens_details?: {
        cached_tokens?: number;
        text_tokens?: number;
        audio_tokens?: number;
        image_tokens?: number;
    };
    completion_tokens_details?: {
        text_tokens?: number;
        audio_tokens?: number;
        reasoning_tokens?: number;
    };
    // Additional fields that might exist
    input_tokens?: number;
    output_tokens?: number;
    input_tokens_details?: unknown;
    [key: string]: unknown;
}

interface BillingConfig {
    type?: 'free' | 'per_use' | 'per_token';
    // per_use fields
    per_use_price?: number;
    per_use_multiplier?: number;
    // per_token fields
    input_price?: number;
    output_price?: number;
    price_unit?: 'K' | 'M';
    token_multiplier?: number;
    // common
    currency?: 'USD' | 'CNY';
}

interface ModelInfo {
    info?: {
        meta?: {
            billing?: BillingConfig;
        };
    };
}

type I18nFunction = (key: string) => string;

/**
 * Format usage statistics into a clean, localized HTML string.
 */
export function formatUsageStats(
    usage: UsageData | null | undefined,
    model: ModelInfo | null | undefined,
    t: I18nFunction
): string {
    // If usage is null/undefined, show a friendly message
    if (!usage) {
        return `<pre style="margin: 0; font-family: inherit;">${t('Model did not return usage information')}</pre>`;
    }

    const lines: string[] = [];

    // Input tokens (prompt_tokens or input_tokens)
    const inputTokens = usage.prompt_tokens ?? usage.input_tokens ?? 0;
    if (inputTokens > 0) {
        lines.push(`${t('Input Tokens')}: ${inputTokens.toLocaleString()}`);
    }

    // Output tokens (completion_tokens or output_tokens)
    const outputTokens = usage.completion_tokens ?? usage.output_tokens ?? 0;
    if (outputTokens > 0) {
        lines.push(`${t('Output Tokens')}: ${outputTokens.toLocaleString()}`);
    }

    // Reasoning tokens (if available in completion_tokens_details)
    const reasoningTokens = usage.completion_tokens_details?.reasoning_tokens ?? 0;
    if (reasoningTokens > 0) {
        lines.push(`${t('Reasoning Tokens')}: ${reasoningTokens.toLocaleString()}`);
    }

    // Total tokens
    const totalTokens = usage.total_tokens ?? (inputTokens + outputTokens);
    if (totalTokens > 0) {
        lines.push(`${t('Total Tokens')}: ${totalTokens.toLocaleString()}`);
    }

    // If we have no token data at all, show a friendly message
    if (lines.length === 0) {
        return `<pre style="margin: 0; font-family: inherit;">${t('Model did not return usage information')}</pre>`;
    }

    // Calculate cost if billing config is available
    const billing = model?.info?.meta?.billing;
    if (billing && billing.type !== 'free') {
        const cost = calculateCost(inputTokens, outputTokens, billing);
        if (cost !== null) {
            lines.push('─'.repeat(16));
            const currencySymbol = billing.currency === 'CNY' ? '¥' : '$';
            lines.push(`${t('Total Cost')}: ${currencySymbol}${cost.toFixed(4)}`);
        }
    }

    return `<pre style="margin: 0; font-family: inherit;">${lines.join('\n')}</pre>`;
}

/**
 * Calculate the cost based on billing configuration.
 */
function calculateCost(
    inputTokens: number,
    outputTokens: number,
    billing: BillingConfig
): number | null {
    if (billing.type === 'per_use') {
        const multiplier = billing.per_use_multiplier ?? 1;
        return (billing.per_use_price ?? 0) * multiplier;
    }

    if (billing.type === 'per_token') {
        const multiplier = billing.token_multiplier ?? 1;
        const unitDivisor = billing.price_unit === 'M' ? 1_000_000 : 1_000;
        const inputPrice = billing.input_price ?? 0;
        const outputPrice = billing.output_price ?? 0;

        const inputCost = (inputTokens / unitDivisor) * inputPrice;
        const outputCost = (outputTokens / unitDivisor) * outputPrice;

        return (inputCost + outputCost) * multiplier;
    }

    return null;
}

export default formatUsageStats;
