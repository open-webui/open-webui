import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export const APPROX_CHARS_PER_CONTEXT_TOKEN = 4;
export const TARGET_LONG_CONTEXT_TOKENS = 1_000_000;
export const TARGET_LONG_CHAT_CHARS = TARGET_LONG_CONTEXT_TOKENS * APPROX_CHARS_PER_CONTEXT_TOKEN;

const WORDS =
	'alpha beta gamma delta epsilon zeta eta theta markdown renderer tool call browser context'.split(
		' '
	);

const escapeAttr = (value) => {
	return value
		.replaceAll('&', '&amp;')
		.replaceAll('"', '&quot;')
		.replaceAll('<', '&lt;')
		.replaceAll('>', '&gt;');
};

const paragraph = (idx) => {
	const words = Array.from({ length: 80 }, (_, wordIdx) => WORDS[(idx + wordIdx) % WORDS.length]);
	return `### Section ${idx}

${words.join(' ')}.

- [ ] task ${idx}.1
- [x] task ${idx}.2
- item ${idx}.3 with \`inline_code_${idx}\`

> quoted markdown with **strong**, _emphasis_, and a [link](https://example.com/${idx}).
`;
};

const codeBlock = (idx, lines = 120) => {
	const body = Array.from({ length: lines }, (_, line) => {
		return `const value_${idx}_${line} = ${line}; if (value_${idx}_${line} % 7 === 0) console.log("row", value_${idx}_${line});`;
	}).join('\n');

	return `\n\`\`\`javascript\n${body}\n\`\`\`\n`;
};

const pythonBlock = (idx, lines = 80) => {
	const body = Array.from({ length: lines }, (_, line) => {
		return `value_${idx}_${line} = ${line}\nif value_${idx}_${line} % 5 == 0:\n    print("row", value_${idx}_${line})`;
	}).join('\n');

	return `\n\`\`\`python\n${body}\n\`\`\`\n`;
};

const resultRows = (idx, rows = 160) => {
	return Array.from({ length: rows }, (_, row) => ({
		row,
		id: `tool-${idx}-${row}`,
		title: `Result ${idx}.${row}`,
		body: 'abcdefghijklmnopqrstuvwxyz '.repeat(6),
		nested: {
			score: row / (idx + 1),
			flags: ['markdown', 'tool_calls', 'long_context', row % 2 ? 'odd' : 'even']
		}
	}));
};

const toolCall = (idx, { rows = 160, done = true, embeds = false } = {}) => {
	const args = escapeAttr(
		JSON.stringify({
			query: `stress renderer tool call ${idx}`,
			limit: rows,
			filters: ['markdown', 'tool_calls', 'browser_perf'],
			nested: {
				include_code: idx % 2 === 0,
				include_tables: true,
				cursor: `cursor-${idx}`
			}
		})
	);
	const attrs = [
		'type="tool_calls"',
		`name="stress_tool_${idx % 11}"`,
		`arguments="${args}"`,
		`done="${done ? 'true' : 'false'}"`
	];

	if (embeds) {
		attrs.push(
			`embeds="${escapeAttr(
				JSON.stringify([{ type: 'iframe', url: 'https://example.com/embed', name: `embed-${idx}` }])
			)}"`
		);
	}

	const result = done
		? JSON.stringify({ id: idx, rows: resultRows(idx, rows), summary: paragraph(idx) }, null, 2)
		: '';

	return `<details ${attrs.join(' ')}>
<summary>Tool call ${idx}</summary>
${result}
</details>`;
};

const markdownKitchenSink = () => {
	return `# Markdown Kitchen Sink

Text with **bold**, _italic_, ~~strikethrough~~, \`inline code\`, autolinks, and escaped HTML.

| Browser | Renderer path | Expected pressure |
| --- | --- | --- |
| Chromium | V8 + DOM | syntax highlighting and layout |
| Firefox | SpiderMonkey + DOM | parser and DOM churn |
| Tor Browser | hardened Firefox ESR | JS and DOM work under slower privacy settings |

1. ordered item
2. ordered item with nested unordered content
3. ordered item with a long inline segment ${'0123456789 '.repeat(20)}

<details>
<summary>Regular non-tool details</summary>

${paragraph(7)}

</details>

![image alt](https://example.com/image.png)

${codeBlock(1, 80)}

${pythonBlock(2, 60)}

\`\`\`mermaid
flowchart TD
  A[Start] --> B{Renderer}
  B --> C[Markdown]
  B --> D[Tool calls]
\`\`\`

\`\`\`json
${JSON.stringify({ json: true, rows: resultRows(3, 8) }, null, 2)}
\`\`\`
`;
};

const buildLongChat = (targetChars) => {
	const chunks = [];
	let idx = 0;
	let size = 0;

	while (size < targetChars) {
		const chunk =
			paragraph(idx) +
			(idx % 5 === 0 ? codeBlock(idx, 35) : '') +
			(idx % 7 === 0 ? toolCall(idx, { rows: 24 }) : '');
		chunks.push(chunk);
		size += chunk.length;
		idx += 1;
	}

	return chunks.join('\n\n');
};

export function createRendererStressCases({ longChatChars = TARGET_LONG_CHAT_CHARS } = {}) {
	const cases = [
		{
			name: 'markdown-kitchen-sink',
			done: true,
			settings: { expandDetails: true, collapseCodeBlocks: false },
			description: 'All common markdown constructs plus code, tables, images, details, and diagrams.',
			content: markdownKitchenSink()
		},
		{
			name: 'tool-calls-collapsed-heavy',
			done: true,
			settings: { expandDetails: false, collapseCodeBlocks: false },
			description: 'Many completed tool calls with large JSON results kept collapsed.',
			content: Array.from({ length: 160 }, (_, idx) => toolCall(idx, { rows: 120 })).join('\n\n')
		},
		{
			name: 'tool-calls-expanded-heavy',
			done: true,
			settings: { expandDetails: true, collapseCodeBlocks: false },
			description: 'Completed tool calls opened so result decoding and JSON formatting are hot.',
			content: Array.from({ length: 48 }, (_, idx) => toolCall(idx, { rows: 220, embeds: true })).join(
				'\n\n'
			)
		},
		{
			name: 'streaming-code-and-tools',
			done: false,
			settings: { expandDetails: false, collapseCodeBlocks: false },
			description: 'Streaming response with long code blocks and in-flight tool calls.',
			content:
				Array.from({ length: 48 }, (_, idx) => codeBlock(idx, 120)).join('\n\n') +
				Array.from({ length: 80 }, (_, idx) => toolCall(idx, { rows: 0, done: false })).join('\n\n')
		},
		{
			name: 'mixed-long-chat-1m-context',
			done: true,
			settings: { expandDetails: false, collapseCodeBlocks: false },
			description:
				'Mixed markdown, code, and tool-call content grown to approximately 1M context tokens.',
			content: buildLongChat(longChatChars)
		}
	];

	return cases.map((testCase) => ({
		...testCase,
		characters: testCase.content.length,
		approxContextTokens: Math.ceil(testCase.content.length / APPROX_CHARS_PER_CONTEXT_TOKEN)
	}));
}

export function writeRendererStressCases(outputDir, options = {}) {
	mkdirSync(outputDir, { recursive: true });
	const cases = createRendererStressCases(options);
	const manifest = cases.map(({ content, ...metadata }) => metadata);

	writeFileSync(join(outputDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
	for (const testCase of cases) {
		writeFileSync(join(outputDir, `${testCase.name}.md`), testCase.content);
	}

	return { cases, manifest };
}

const isCli = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isCli) {
	const outputDir = process.argv[2] ?? 'renderer-stress-cases';
	const longChatChars = Number(
		process.env.RENDERER_STRESS_LONG_CHARS ??
			Number(process.env.RENDERER_STRESS_LONG_TOKENS ?? TARGET_LONG_CONTEXT_TOKENS) *
				APPROX_CHARS_PER_CONTEXT_TOKEN
	);
	const { manifest } = writeRendererStressCases(outputDir, { longChatChars });
	console.log(JSON.stringify(manifest, null, 2));
}
