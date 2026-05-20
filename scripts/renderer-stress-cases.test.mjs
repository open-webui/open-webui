import { describe, expect, it } from 'vitest';

import { TARGET_LONG_CHAT_CHARS, createRendererStressCases } from './renderer-stress-cases.mjs';

describe('renderer stress cases', () => {
	it('covers markdown, collapsed tools, expanded tools, streaming, and long chat payloads', () => {
		const cases = createRendererStressCases({ longChatChars: TARGET_LONG_CHAT_CHARS });
		const byName = new Map(cases.map((testCase) => [testCase.name, testCase]));

		expect(byName.has('markdown-kitchen-sink')).toBe(true);
		expect(byName.has('tool-calls-collapsed-heavy')).toBe(true);
		expect(byName.has('tool-calls-expanded-heavy')).toBe(true);
		expect(byName.has('streaming-code-and-tools')).toBe(true);
		expect(byName.has('mixed-long-chat-1m-context')).toBe(true);

		expect(byName.get('mixed-long-chat-1m-context').characters).toBeGreaterThanOrEqual(
			TARGET_LONG_CHAT_CHARS
		);
		expect(byName.get('mixed-long-chat-1m-context').approxContextTokens).toBeGreaterThanOrEqual(
			1_000_000
		);
		expect(byName.get('streaming-code-and-tools').done).toBe(false);
		expect(byName.get('tool-calls-expanded-heavy').settings.expandDetails).toBe(true);
		expect(byName.get('tool-calls-collapsed-heavy').settings.expandDetails).toBe(false);
	});

	it('escapes tool-call attributes and preserves raw result content for parser stress', () => {
		const cases = createRendererStressCases({ longChatChars: 20_000 });
		const collapsedTools = cases.find((testCase) => testCase.name === 'tool-calls-collapsed-heavy');

		expect(collapsedTools.content).toContain('type="tool_calls"');
		expect(collapsedTools.content).toContain('arguments="{&quot;query&quot;');
		expect(collapsedTools.content).toContain('"rows": [');
		expect(collapsedTools.content).not.toContain('arguments="{"query"');
	});
});
