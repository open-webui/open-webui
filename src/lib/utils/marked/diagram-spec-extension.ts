/**
 * Diagram Spec Extension for Marked
 *
 * Handles <diagram-spec>...</diagram-spec> blocks containing JSON diagram specifications.
 * Used to render diagrams with nodes (rectangle, rounded_rectangle, diamond, ellipse) and edges.
 */

export interface DiagramNode {
	id: string;
	label: string;
	shape: 'rectangle' | 'rounded_rectangle' | 'diamond' | 'ellipse';
}

export interface DiagramEdge {
	from: string;
	to: string;
	label?: string;
	style?: 'solid' | 'dashed' | 'dotted';
}

export interface DiagramLayout {
	direction: 'TB' | 'LR' | 'BT' | 'RL';
}

export interface DiagramSpec {
	nodes: DiagramNode[];
	edges: DiagramEdge[];
	layout?: DiagramLayout;
}

export interface DiagramSpecToken {
	type: 'diagramSpec';
	raw: string;
	spec: DiagramSpec | null;
	error?: string;
}

function diagramSpecTokenizer(src: string): DiagramSpecToken | undefined {
	const regex = /^<diagram_spec>\n?([\s\S]*?)\n?<\/diagram_spec>/;
	const match = regex.exec(src);

	if (match) {
		let jsonContent = match[1].trim();
		let spec: DiagramSpec | null = null;
		let error: string | undefined;

		console.log('[DiagramSpec Tokenizer] Raw JSON:', jsonContent);

		try {
			spec = JSON.parse(jsonContent);
			console.log('[DiagramSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[DiagramSpec Tokenizer] Parse error:', error);
			console.error('[DiagramSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'diagramSpec',
			raw: match[0],
			spec,
			error
		};
	}
}

function diagramSpecStart(src: string): number {
	const index = src.indexOf('<diagram_spec>');
	return index !== -1 ? index : -1;
}

function diagramSpecRenderer(token: DiagramSpecToken): string {
	// The actual rendering is handled by the Svelte component
	// This renderer returns a placeholder that will be replaced
	if (token.error) {
		return `<div class="diagram-spec-error">Diagram Spec Error: ${token.error}</div>`;
	}
	return `<div class="diagram-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function diagramSpecExtension() {
	return {
		name: 'diagramSpec',
		level: 'block' as const,
		start: diagramSpecStart,
		tokenizer: diagramSpecTokenizer,
		renderer: diagramSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [diagramSpecExtension()]
	};
}
