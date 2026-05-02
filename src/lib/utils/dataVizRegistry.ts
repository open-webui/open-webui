/**
 * Live data-viz render dispatch.
 *
 * Why this isn't a registry of mounted DataVizWidgets:
 * - The backend's show_widget tool calls __event_call__('data_viz:render', ...)
 *   while the chat completion stream is still mid-flight. The streaming
 *   `<details done="false">` block that mounts the visible DataVizWidget may
 *   not reach the frontend until AFTER the tool's __event_call__ has already
 *   arrived. A registry-based dispatch that waits for the widget to mount
 *   races and times out, returning {status: 'ok'} to the backend even when
 *   the iframe later throws — the user sees a broken widget while the model
 *   thinks everything rendered fine.
 * - Instead, every render request gets its own hidden iframe (via
 *   liveRenderWidget). It's independent of widget mounting and always
 *   available. The visible DataVizWidget mounts later and renders the final
 *   widget_code (possibly with override applied for the persisted fix).
 */

import {
	liveRenderWidget,
	type WidgetRenderRequest,
	type WidgetRenderResponse
} from './dataVizLiveRender';

export type { WidgetRenderRequest, WidgetRenderResponse };

export type WidgetRenderHandler = (req: WidgetRenderRequest) => Promise<WidgetRenderResponse>;

/**
 * No-op kept for back-compat with DataVizWidget which still calls this on
 * mount. The actual live verification happens via liveRenderWidget regardless
 * of whether a widget is mounted.
 */
export function registerWidgetHandler(
	_messageId: string,
	_overrideKey: string,
	_handler: WidgetRenderHandler
): () => void {
	return () => {};
}

/**
 * Called by Chat.svelte's chatEventHandler when a `data_viz:render` event
 * arrives from the backend's show_widget tool. Spins up a hidden iframe,
 * renders, captures errors, and returns the outcome. Decoupled from any
 * visible widget — works whether or not DataVizWidget has mounted yet.
 */
export async function dispatchWidgetRender(
	_messageId: string | undefined,
	req: WidgetRenderRequest
): Promise<WidgetRenderResponse> {
	if (!req || typeof req.widget_code !== 'string') {
		return { status: 'ok' };
	}
	try {
		return await liveRenderWidget(req);
	} catch (err: any) {
		return {
			status: 'error',
			error_message: String(err?.message ?? err ?? 'live render threw')
		};
	}
}
