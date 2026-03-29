import panzoom, { type PanZoom, type PanZoomOptions } from 'panzoom';

const defaultOpts: PanZoomOptions = {
	bounds: true,
	boundsPadding: 0.1,
	zoomSpeed: 0.065
};

/**
 * Per-component-instance panzoom helper: call once in a Svelte `<script>`,
 * then use `action` with `use:`, and `reset` / `dispose` for imperative control.
 */
export function createPanzoomAction(opts?: Partial<PanZoomOptions>) {
	let instance: PanZoom | undefined;

	const action = (node: HTMLElement) => {
		const local = panzoom(node, { ...defaultOpts, ...opts });
		instance = local;
		return {
			destroy() {
				local.dispose();
				if (instance === local) {
					instance = undefined;
				}
			}
		};
	};

	const reset = () => {
		instance?.moveTo(0, 0);
		instance?.zoomAbs(0, 0, 1);
	};

	const dispose = () => {
		instance?.dispose();
		instance = undefined;
	};

	return { action, reset, dispose };
}
