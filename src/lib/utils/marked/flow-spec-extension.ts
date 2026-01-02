/**
 * Flow Spec Extension for Marked
 *
 * Handles <flow-spec>...</flow-spec> blocks containing JSON flowchart specifications.
 * Used to render flowcharts with nodes (oval, rectangle, diamond) and edges.
 */

export interface FlowNode {
	id: string;
	label: string;
	shape: 'oval' | 'rectangle' | 'diamond';
}

export interface FlowEdge {
	from: string;
	to: string;
	label?: string;
	condition?: string;
}

export interface FlowLayout {
	direction: 'TB' | 'LR' | 'BT' | 'RL';
}

export interface FlowSpec {
	nodes: FlowNode[];
	edges: FlowEdge[];
	layout?: FlowLayout;
}

export interface FlowSpecToken {
	type: 'flowSpec';
	raw: string;
	spec: FlowSpec | null;
	error?: string;
}

function flowSpecTokenizer(src: string): FlowSpecToken | undefined {
	const regex = /^<flow_spec>\n?([\s\S]*?)\n?<\/flow_spec>/;
	const match = regex.exec(src);

	if (match) {
		let jsonContent = match[1].trim();
		let spec: FlowSpec | null = null;
		let error: string | undefined;

		console.log('[FlowSpec Tokenizer] Raw JSON:', jsonContent);

		try {
			spec = JSON.parse(jsonContent);
			console.log('[FlowSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[FlowSpec Tokenizer] Parse error:', error);
			console.error('[FlowSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'flowSpec',
			raw: match[0],
			spec,
			error
		};
	}
}

function flowSpecStart(src: string): number {
	const index = src.indexOf('<flow_spec>');
	return index !== -1 ? index : -1;
}

function flowSpecRenderer(token: FlowSpecToken): string {
	// The actual rendering is handled by the Svelte component
	// This renderer returns a placeholder that will be replaced
	if (token.error) {
		return `<div class="flow-spec-error">Flow Spec Error: ${token.error}</div>`;
	}
	return `<div class="flow-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function flowSpecExtension() {
	return {
		name: 'flowSpec',
		level: 'block' as const,
		start: flowSpecStart,
		tokenizer: flowSpecTokenizer,
		renderer: flowSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [flowSpecExtension()]
	};
}
