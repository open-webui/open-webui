import { describe, it, expect } from 'vitest';
import { stripIncompleteDetails, processResponseContent } from '$lib/utils';

/**
 * ACP-5048: Simulate the exact streaming scenario seen on dev.
 * The backend yields chunks like:
 *   t=0: '<details type="streaming">\n<summary>...'
 *   t=1: '...more events...'
 *   t=N: '\n</details>\n\n---\n\nFinal answer'
 *
 * During streaming (before </details> arrives), the accumulated content
 * has an unclosed <details> tag which the marked extension cannot parse,
 * causing it to render as raw XML text.
 */
describe('Streaming details scenario (ACP-5048)', () => {
	const streamingOpen =
		'<details type="streaming">\n' +
		'<summary>🔄 Real-time Agent Execution</summary>\n' +
		'\n🚀 Starting real-time workflow execution...\n';

	const streamingEvents =
		'\n🚀 [Orchestrator] Starting query analysis...\n' +
		'\n💭 [Orchestrator] Thinking: Calling tool\n' +
		'\n⚡ [Orchestrator] Action: execute_plan\n';

	const streamingClose = '\n</details>\n';

	const separator = '\n---\n\n';

	const finalAnswer = '## Results\n\nHere are the Zen 5 specs...';

	it('strips incomplete details during streaming (open tag only)', () => {
		// Simulates early streaming: only the opening tag arrived
		const partial = streamingOpen;
		const result = stripIncompleteDetails(partial);
		expect(result).not.toContain('<details');
		expect(result).toBe('');
	});

	it('strips incomplete details during streaming (open + events)', () => {
		// Simulates mid-streaming: events arriving but no closing tag yet
		const partial = streamingOpen + streamingEvents;
		const result = stripIncompleteDetails(partial);
		expect(result).not.toContain('<details');
	});

	it('keeps complete details block intact', () => {
		// Simulates after streaming completes: full block with closing tag
		const complete = streamingOpen + streamingEvents + streamingClose;
		const result = stripIncompleteDetails(complete);
		expect(result).toContain('<details');
		expect(result).toContain('</details>');
	});

	it('keeps complete block + final answer intact', () => {
		const full = streamingOpen + streamingEvents + streamingClose + separator + finalAnswer;
		const result = stripIncompleteDetails(full);
		expect(result).toContain('<details');
		expect(result).toContain('</details>');
		expect(result).toContain('## Results');
	});

	it('processResponseContent strips incomplete tags during streaming', () => {
		const partial = streamingOpen + streamingEvents;
		const result = processResponseContent(partial);
		expect(result).not.toContain('<details');
	});

	it('processResponseContent preserves complete content', () => {
		const full = streamingOpen + streamingEvents + streamingClose + separator + finalAnswer;
		const result = processResponseContent(full);
		expect(result).toContain('<details');
		expect(result).toContain('## Results');
	});

	it('handles the exact output seen on dev (raw XML bug)', () => {
		// This is the exact pattern that was rendered as raw text on dev
		const devOutput =
			'<details type="streaming">\n' +
			'<summary>🔄 Real-time Agent Execution</summary>\n' +
			'\n🚀 Starting real-time workflow execution...\n' +
			'\n🚀 [Orchestrator] Starting query analysis...\n' +
			'\n💭 [Orchestrator] Thinking: Calling tool\n' +
			'\n⚡ [Orchestrator] Action: execute_plan\n' +
			'📝 Input: {}\n' +
			'\n🚀 [JiraAnalysisAgent] Starting...\n' +
			'\n🚀 [PowerBIAgent] Starting...\n';
		// No closing </details> — this is what the user sees during streaming

		const result = processResponseContent(devOutput);
		// Should NOT contain raw <details> tag
		expect(result).not.toContain('<details');
		expect(result).not.toContain('<summary>');
	});
});
