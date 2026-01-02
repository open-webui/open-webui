/**
 * Scene Spec Extension for Marked
 *
 * Handles <scene_spec>...</scene_spec> blocks containing JSON scene specifications.
 * Used to render spatial scenes with entities, relations, and annotations.
 */

export interface EntityAppearance {
	type: 'svg' | 'icon' | 'shape';
	viewBox?: string;
	svg?: string;
	icon?: string;
	shape?: 'circle' | 'rectangle' | 'triangle';
	color?: string;
}

export interface SceneEntity {
	id: string;
	kind: string;
	label: string;
	appearance?: EntityAppearance;
	position?: { x: number; y: number };
}

export interface SceneRelation {
	type: 'distance' | 'motion' | 'angle' | 'force' | 'connection';
	from?: string;
	to?: string;
	entity?: string;
	value?: string;
	direction?: string;
	label?: string;
}

export interface SceneAnnotation {
	type: 'value' | 'label' | 'formula';
	text: string;
	attachTo: string;
	position: 'top' | 'bottom' | 'left' | 'right';
	offset?: { x: number; y: number };
}

export interface SceneView {
	projection: '2d_side' | '2d_top' | '3d_isometric';
	orientation: 'left_to_right' | 'right_to_left' | 'top_to_bottom';
	zoom?: number;
}

export interface SceneSpec {
	type: 'scene';
	entities: SceneEntity[];
	relations?: SceneRelation[];
	annotations?: SceneAnnotation[];
	view?: SceneView;
	background?: string;
}

export interface SceneSpecToken {
	type: 'sceneSpec';
	raw: string;
	spec: SceneSpec | null;
	error?: string;
}

function sceneSpecTokenizer(src: string): SceneSpecToken | undefined {
	const regex = /^<scene_spec>\n?([\s\S]*?)\n?<\/scene_spec>/;
	const match = regex.exec(src);

	if (match) {
		let jsonContent = match[1].trim();
		let spec: SceneSpec | null = null;
		let error: string | undefined;

		console.log('[SceneSpec Tokenizer] Raw JSON:', jsonContent);

		try {
			spec = JSON.parse(jsonContent);
			console.log('[SceneSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[SceneSpec Tokenizer] Parse error:', error);
			console.error('[SceneSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'sceneSpec',
			raw: match[0],
			spec,
			error
		};
	}
}

function sceneSpecStart(src: string): number {
	const index = src.indexOf('<scene_spec>');
	return index !== -1 ? index : -1;
}

function sceneSpecRenderer(token: SceneSpecToken): string {
	if (token.error) {
		return `<div class="scene-spec-error">Scene Spec Error: ${token.error}</div>`;
	}
	return `<div class="scene-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function sceneSpecExtension() {
	return {
		name: 'sceneSpec',
		level: 'block' as const,
		start: sceneSpecStart,
		tokenizer: sceneSpecTokenizer,
		renderer: sceneSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [sceneSpecExtension()]
	};
}
