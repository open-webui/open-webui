/**
 * Registry of in-flight data-viz widget render handlers, keyed by
 * `${messageId}:${overrideKey}`. The backend's show_widget tool calls
 * `__event_call__({type: 'data_viz:render', ...})`, which arrives at the
 * frontend's chat events socket listener; that listener delegates to
 * `dispatchWidgetRender(...)`, which finds the right DataVizWidget instance
 * and asks it to render-and-report.
 *
 * Why register by (messageId, overrideKey) instead of tool_call_id:
 * - The backend hashes the original widget_code to produce overrideKey, and
 *   the frontend's DataVizWidget computes the same hash on its arguments.
 *   That gives us a stable correlation that survives reloads and doesn't
 *   require plumbing tool_call_id into the tool's execution context.
 * - On the same message, multiple widgets with different code get distinct
 *   keys naturally.
 */

export type WidgetRenderRequest = {
	request_id: string;
	title: string;
	widget_code: string;
	attempt: number;
	is_repair: boolean;
	loading_messages: string[];
	override_key: string;
};

export type WidgetRenderResponse = {
	status: 'ok' | 'error';
	error_message?: string;
	error_stack?: string;
};

export type WidgetRenderHandler = (req: WidgetRenderRequest) => Promise<WidgetRenderResponse>;

const handlers = new Map<string, WidgetRenderHandler>();

const composeKey = (messageId: string, overrideKey: string) => `${messageId}:${overrideKey}`;

/**
 * DataVizWidget instances call this on mount. Returns an unregister function
 * to call on destroy.
 */
export function registerWidgetHandler(
	messageId: string,
	overrideKey: string,
	handler: WidgetRenderHandler
): () => void {
	const k = composeKey(messageId, overrideKey);
	handlers.set(k, handler);
	return () => {
		if (handlers.get(k) === handler) {
			handlers.delete(k);
		}
	};
}

/**
 * Called by the chat events socket listener when a `data_viz:render` event
 * arrives. Looks up the matching widget handler. If none is registered yet
 * (race during streaming — widget hasn't mounted), waits briefly. If still
 * absent, returns `{status: 'ok'}` so the model can proceed (better than
 * stalling).
 */
export async function dispatchWidgetRender(
	messageId: string | undefined,
	req: WidgetRenderRequest
): Promise<WidgetRenderResponse> {
	if (!messageId || !req?.override_key) {
		return { status: 'ok' };
	}
	const k = composeKey(messageId, req.override_key);

	let handler = handlers.get(k);
	if (!handler) {
		const startedAt = Date.now();
		while (!handler && Date.now() - startedAt < 5000) {
			await new Promise((r) => setTimeout(r, 100));
			handler = handlers.get(k);
		}
	}
	if (!handler) {
		console.warn('[dataViz] no widget handler registered for', k);
		return { status: 'ok' };
	}

	try {
		return await handler(req);
	} catch (err: any) {
		return {
			status: 'error',
			error_message: String(err?.message ?? err ?? 'handler threw')
		};
	}
}
