import { encode } from 'html-entities';
import { render } from 'svelte/server';
import { readable } from 'svelte/store';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';

import ToolCallDisplay from '$lib/components/common/ToolCallDisplay.svelte';

import StructuredOutputRenderer from './StructuredOutputRenderer.svelte';
import type { OutputItem } from './structuredOutput';

const EMBED_HTML = '<html><body><p>&quot;</p></body></html>';
const context = new Map([['i18n', readable({ t: (value: string) => value })]]);

beforeAll(() => {
	vi.stubGlobal('window', {
		addEventListener: () => {},
		removeEventListener: () => {}
	});
});

afterAll(() => {
	vi.unstubAllGlobals();
});

function renderOutput(output: OutputItem[]) {
	return render(StructuredOutputRenderer, {
		props: {
			id: 'message',
			output,
			done: true,
			renderMarkdown: false
		},
		context
	}).body;
}

function toolCall(callId: string): OutputItem {
	return {
		type: 'function_call',
		call_id: callId,
		name: 'rich_ui',
		status: 'completed',
		arguments: '{}'
	};
}

function toolOutput(callId: string): OutputItem {
	return {
		type: 'function_call_output',
		call_id: callId,
		embeds: [EMBED_HTML]
	};
}

describe('StructuredOutputRenderer', () => {
	it('keeps decoding legacy HTML-encoded embed attributes', () => {
		const body = render(ToolCallDisplay, {
			props: {
				id: 'legacy',
				attributes: {
					name: 'rich_ui',
					done: 'true',
					embeds: encode(JSON.stringify([EMBED_HTML]))
				}
			},
			context
		}).body;

		expect(body).toContain('legacy-tool-call-embed-0');
	});

	it('renders a structured embed containing an HTML entity', () => {
		const body = renderOutput([toolCall('call-1'), toolOutput('call-1')]);

		expect(body).toContain('tool-call-embed-0');
	});

	it('renders grouped structured embeds containing HTML entities', () => {
		const body = renderOutput([
			toolCall('call-1'),
			toolOutput('call-1'),
			toolCall('call-2'),
			toolOutput('call-2')
		]);

		expect(body).toContain('detail-group-0-embed-0');
		expect(body).toContain('detail-group-0-embed-1');
	});
});
