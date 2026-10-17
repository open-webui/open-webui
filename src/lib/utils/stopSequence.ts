const percentDecode = (value: string): string => {
        try {
                return decodeURIComponent(value);
        } catch {
                return value;
        }
};

/**
 * Decodes a single stop sequence token: backslash escapes first (so a literal
 * `\n` becomes a newline), then percent-encoding. Both steps are lenient — a
 * token that is not a valid escape or percent sequence (e.g. "100%") is kept
 * as-is instead of throwing (#32648).
 */
export const decodeStopToken = (token: string): string => {
        let decoded = token;
        try {
                decoded = JSON.parse(`"${token.replace(/"/g, '\\"')}"`);
        } catch {
                // Keep tokens with invalid escape sequences as-is.
        }
        return percentDecode(decoded);
};

export const getStopTokens = (
        stop: string | string[] | null | undefined
): string[] | undefined => {
        if (!stop) return undefined;

        const tokens = Array.isArray(stop) ? stop : stop.split(',').map((s) => s.trim());

        return tokens.filter(Boolean).map(decodeStopToken);
};
