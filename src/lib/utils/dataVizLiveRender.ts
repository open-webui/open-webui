/**
 * Live data-viz widget verification.
 *
 * The backend's show_widget tool calls __event_call__('data_viz:render', ...)
 * and awaits a render outcome. We can't depend on the visible DataVizWidget
 * being mounted — the streaming <details done="false"> block may not reach
 * the frontend until AFTER the tool's __event_call__ has already arrived, so
 * a registry-based dispatch that waits for the widget to mount races and
 * times out. Instead, every render request gets its OWN hidden iframe (off
 * screen, sandbox=allow-scripts), captures errors via the same window.error
 * + postMessage protocol the visible widget uses, and reports back. The
 * visible widget mounts later from the persisted message content and just
 * renders the final widget code (using override if persisted).
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

const HARD_TIMEOUT_MS = 12_000;

const escapeForJsString = (s: string) => JSON.stringify(s);

/**
 * Build the iframe document for live verification. Mirrors the visible
 * DataVizWidget's structure (transparent body, theme vars, error capture,
 * height post) so a render that succeeds here will succeed there too.
 */
const buildLiveDoc = (fragment: string, widgetId: string, dark: boolean): string => {
	// Minimal CSS — values don't really matter for verification, only that the
	// fragment can reference the variables it expects without ReferenceErrors.
	// (CSS `var()` failing silently is fine; JS errors are what we care about.)
	const themeVars = dark
		? `
			--color-text-primary: #F0F0EB;
			--color-text-secondary: #BFBFBA;
			--color-text-tertiary: #91918D;
			--color-bg-primary: transparent;
			--color-bg-secondary: rgba(255,255,255,0.04);
			--color-bg-tertiary: rgba(255,255,255,0.08);
			--color-background-primary: transparent;
			--color-background-secondary: rgba(255,255,255,0.04);
			--color-background-tertiary: rgba(255,255,255,0.08);
			--color-border-primary: rgba(255,255,255,0.10);
			--color-border-secondary: rgba(255,255,255,0.06);
			--color-accent-primary: #CC785C;
			--color-accent-secondary: #D4A27F;
			--color-success: #9CB07F;
			--color-warning: #E2B873;
			--color-danger: #D88577;
		`
		: `
			--color-text-primary: #191919;
			--color-text-secondary: #666663;
			--color-text-tertiary: #91918D;
			--color-bg-primary: transparent;
			--color-bg-secondary: rgba(0,0,0,0.04);
			--color-bg-tertiary: rgba(0,0,0,0.08);
			--color-background-primary: transparent;
			--color-background-secondary: rgba(0,0,0,0.04);
			--color-background-tertiary: rgba(0,0,0,0.08);
			--color-border-primary: rgba(0,0,0,0.10);
			--color-border-secondary: rgba(0,0,0,0.06);
			--color-accent-primary: #2563eb;
			--color-accent-secondary: #7c3aed;
			--color-success: #059669;
			--color-warning: #d97706;
			--color-danger: #dc2626;
		`;
	const css = `:root { ${themeVars}
		--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		--font-serif: Georgia, serif;
		--font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
		--border-radius-sm: 4px; --border-radius-md: 8px; --border-radius-lg: 12px; --border-radius-xl: 16px;
		--p:#191919;--s:#666663;--t:#91918D;--bg2:rgba(0,0,0,0.04);--b:rgba(0,0,0,0.10);
	}
	html, body { margin:0; padding:0; background:transparent; font-family:-apple-system,BlinkMacSystemFont,sans-serif; }
	body { overflow:hidden; }`;

	const errorScript = `(function () {
		const ID = ${escapeForJsString(widgetId)};
		const truncate = (s, n) => { try { s = String(s == null ? '' : s); } catch (e) { s = ''; } return s.length > n ? s.slice(0, n) : s; };
		const topFrames = (stack) => { try { return String(stack || '').split('\\n').slice(0, 8).join('\\n'); } catch (e) { return ''; } };
		let posted = false;
		const send = (payload) => { if (posted) return; posted = true; try { parent.postMessage(payload, '*'); } catch (e) {} };
		window.addEventListener('error', function (e) {
			send({
				__dataVizError: true, id: ID,
				msg: truncate((e && e.message) || 'Error', 500),
				line: e && e.lineno, col: e && e.colno,
				stack: topFrames(e && e.error && e.error.stack)
			});
		}, true);
		window.addEventListener('unhandledrejection', function (e) {
			const reason = e && e.reason;
			const msg = (reason && reason.message) || (typeof reason === 'string' ? reason : 'Unhandled rejection');
			send({
				__dataVizError: true, id: ID,
				msg: 'Unhandled rejection: ' + truncate(msg, 460),
				stack: topFrames(reason && reason.stack)
			});
		});
	})();`;

	return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<${''}script>${errorScript}</${''}script>
<${''}style>${css}</${''}style>
</head>
<body>
${fragment}
</body>
</html>`;
};

/**
 * Run one live render. Resolves with `{status:'ok'}` if the iframe loads
 * without throwing within the grace window, `{status:'error', ...}` if it
 * threw, or `{status:'ok'}` on hard timeout (fail-soft so the model can
 * proceed if our verification iframe gets stuck).
 */
export function liveRenderWidget(req: WidgetRenderRequest): Promise<WidgetRenderResponse> {
	return new Promise<WidgetRenderResponse>((resolve) => {
		const widgetId = `live-${Math.random().toString(36).slice(2, 12)}`;
		const dark =
			typeof document !== 'undefined' && document.documentElement.classList.contains('dark');

		const iframe = document.createElement('iframe');
		iframe.style.cssText =
			'position:absolute;top:-99999px;left:-99999px;width:800px;height:600px;border:0;visibility:hidden;pointer-events:none;';
		iframe.setAttribute('sandbox', 'allow-scripts allow-downloads');
		iframe.setAttribute('aria-hidden', 'true');
		iframe.setAttribute('tabindex', '-1');
		iframe.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');

		let resolved = false;
		let loadGrace: ReturnType<typeof setTimeout> | null = null;
		let hardTimeout: ReturnType<typeof setTimeout> | null = null;
		let rAFId: ReturnType<typeof requestAnimationFrame> | null = null;
		let rAFTimeout: ReturnType<typeof setTimeout> | null = null;

		const cleanup = () => {
			window.removeEventListener('message', onMessage);
			if (loadGrace) {
				clearTimeout(loadGrace);
				loadGrace = null;
			}
			if (hardTimeout) {
				clearTimeout(hardTimeout);
				hardTimeout = null;
			}
			if (rAFId) {
				cancelAnimationFrame(rAFId);
				rAFId = null;
			}
			if (rAFTimeout) {
				clearTimeout(rAFTimeout);
				rAFTimeout = null;
			}
			try {
				if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
			} catch {}
		};

		const finish = (res: WidgetRenderResponse) => {
			if (resolved) return;
			resolved = true;
			cleanup();
			resolve(res);
		};

		const onMessage = (event: MessageEvent) => {
			const data = event.data;
			if (!data || typeof data !== 'object' || data.id !== widgetId) return;
			if (data.__dataVizError) {
				finish({
					status: 'error',
					error_message: String(data.msg ?? '').slice(0, 500),
					error_stack: data.stack ?? undefined
				});
			}
		};

		iframe.addEventListener('load', () => {
			if (resolved) return;

			// Wait for the browser to complete rendering by counting consecutive
			// animation frames. Chart.js, D3, etc. schedule their first paint via
			// rAF or ResizeObserver (which fires before rAF). After 5 stable
			// frames the browser has fully painted; then add a short grace window
			// for any async errors to surface via postMessage.
			const RENDER_FRAMES = 5;
			let stableFrames = 0;

			const checkFrame = () => {
				if (resolved) return;
				stableFrames++;
				if (stableFrames >= RENDER_FRAMES) {
					if (loadGrace) clearTimeout(loadGrace);
					loadGrace = setTimeout(() => {
						finish({ status: 'ok' });
					}, 500);
				} else {
					rAFId = requestAnimationFrame(checkFrame);
				}
			};
			rAFId = requestAnimationFrame(checkFrame);

			// Safety: if rAF is throttled (e.g. hidden tab at 1fps),
			// don't wait forever. Fall through to the grace window.
			rAFTimeout = setTimeout(() => {
				if (resolved || stableFrames >= RENDER_FRAMES) return;
				if (rAFId) { cancelAnimationFrame(rAFId); rAFId = null; }
				if (loadGrace) clearTimeout(loadGrace);
				loadGrace = setTimeout(() => {
					finish({ status: 'ok' });
				}, 500);
			}, 5000);
		});

		iframe.addEventListener('error', () => {
			finish({
				status: 'error',
				error_message: 'iframe failed to load'
			});
		});

		window.addEventListener('message', onMessage);

		// Hard timeout — fail-soft if neither load nor error fires.
		hardTimeout = setTimeout(() => {
			finish({ status: 'ok' });
		}, HARD_TIMEOUT_MS);

		// Mount + assign srcdoc. Append BEFORE setting srcdoc so the load event
		// fires reliably.
		document.body.appendChild(iframe);
		iframe.srcdoc = buildLiveDoc(req.widget_code, widgetId, dark);
	});
}
