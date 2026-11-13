// This function is serialized into the opaque iframe. Keep it independent of module globals.
export function visualizationRuntime(safeCut: (source: string) => number) {
	type Context = {
		theme: string;
		language: string;
		direction: string;
		reducedMotion: boolean;
		textScale: string;
	};
	const win = window as typeof window & {
		DOMPurify: { sanitize: (source: string, options: object) => DocumentFragment };
		Chart?: {
			defaults: { color: () => string; borderColor: () => string };
			instances: Record<string, { update: (mode: 'none') => void }>;
		};
		openwebui: {
			context: Context;
			sendMessage: (text: string) => Promise<{ sent: boolean }>;
		};
	};
	const root = document.getElementById('visualization-root')!;
	let port: MessagePort | undefined;
	let initialized = false,
		initializing = false,
		prepared = false;
	let heightFrame = 0,
		lastHeight = 0,
		requestSequence = 0;
	const requests = new Map<string, (value: { sent: boolean }) => void>();
	const send = (data: object) => port?.postMessage(data);
	const fail = (message: string) => send({ type: 'error', message: String(message).slice(0, 500) });

	function appendScript(source: string, placeholder?: Element) {
		const script = document.createElement('script');
		script.textContent = source;
		if (placeholder) placeholder.replaceWith(script);
		else document.head.append(script);
	}

	function contextChanged(context: Context) {
		win.openwebui.context = Object.freeze({ ...context });
		document.documentElement.dataset.theme = context.theme;
		document.documentElement.style.setProperty('--owui-text-scale', context.textScale);
		document.documentElement.lang = context.language;
		document.documentElement.dir = context.direction;
		document.documentElement.dataset.reducedMotion = String(context.reducedMotion);
		if (win.Chart) {
			// Chart.js copies scale defaults at construction; callbacks keep those copies theme-aware.
			win.Chart.defaults.color = () =>
				getComputedStyle(document.documentElement).getPropertyValue('--owui-muted').trim();
			win.Chart.defaults.borderColor = () =>
				getComputedStyle(document.documentElement).getPropertyValue('--owui-border').trim();
			for (const chart of Object.values(win.Chart.instances)) chart.update('none');
		}
		window.dispatchEvent(
			new CustomEvent('openwebui:contextchange', { detail: win.openwebui.context })
		);
	}

	win.openwebui = {
		context: {
			theme: 'light',
			language: 'en',
			direction: 'ltr',
			reducedMotion: false,
			textScale: '1'
		},
		sendMessage(text) {
			if (
				!initialized ||
				requests.size ||
				typeof text !== 'string' ||
				!text.trim() ||
				text.length > 16000
			) {
				return Promise.resolve({ sent: false });
			}
			const requestId = String(++requestSequence);
			return new Promise((resolve) => {
				requests.set(requestId, resolve);
				send({ type: 'send-message', requestId, text });
			});
		}
	};

	function scheduleHeight() {
		if (heightFrame) return;
		heightFrame = requestAnimationFrame(() => {
			heightFrame = 0;
			let bottom = Math.max(root.getBoundingClientRect().bottom, root.scrollHeight);
			for (const svg of root.querySelectorAll('svg')) {
				try {
					const box = svg.getBBox();
					const matrix = svg.getScreenCTM();
					if (matrix)
						bottom = Math.max(
							bottom,
							new DOMPoint(box.x + box.width, box.y + box.height).matrixTransform(matrix).y
						);
				} catch {
					/* Hidden SVGs have no bounding box. */
				}
			}
			const height = Math.ceil(bottom + window.scrollY);
			if (height !== lastHeight && Number.isFinite(height)) {
				lastHeight = height;
				send({ type: 'height', value: height });
			}
		});
	}

	function prepare(source: string, final: boolean) {
		const doc = new DOMParser().parseFromString(source, 'text/html');
		const scripts: string[] = [];
		// Only placeholders created here may select executable source.
		for (const node of doc.querySelectorAll('[data-owui-script]'))
			node.removeAttribute('data-owui-script');
		for (const script of doc.querySelectorAll('script')) {
			if (final) {
				const type = (script.getAttribute('type') ?? '').trim().toLowerCase();
				if (
					script.hasAttribute('src') ||
					script.hasAttribute('href') ||
					script.hasAttribute('xlink:href') ||
					!['', 'text/javascript', 'application/javascript'].includes(type)
				) {
					throw new Error('Use classic inline scripts and bundled libraries only.');
				}
				const placeholder = doc.createElement('template');
				placeholder.dataset.owuiScript = String(scripts.length);
				scripts.push(script.textContent ?? '');
				script.replaceWith(placeholder);
			} else script.remove();
		}
		const head = Array.from(
			doc.head.querySelectorAll('style, template[data-owui-script]'),
			(node) => node.outerHTML
		).join('');
		const fragment = win.DOMPurify.sanitize(head + doc.body.innerHTML, {
			RETURN_DOM_FRAGMENT: true,
			// This opaque frame runs authored scripts; keep IDs such as "reset" usable by them.
			SANITIZE_DOM: false,
			FORCE_BODY: true, // Retain leading styles and script placeholders in the fragment.
			USE_PROFILES: { html: true, svg: true, svgFilters: true },
			ADD_TAGS: ['style'],
			FORBID_TAGS: [
				'script',
				'iframe',
				'object',
				'embed',
				'base',
				'meta',
				'link',
				'form',
				'foreignObject'
			],
			FORBID_ATTR: ['srcdoc', 'autofocus', 'target', 'download']
		});
		// Navigation is not a capability of the generated fragment.
		for (const anchor of fragment.querySelectorAll('a')) {
			anchor.removeAttribute('href');
			anchor.removeAttribute('xlink:href');
		}
		return { fragment, scripts };
	}

	function reconcile(existing: Node, incoming: Node) {
		const wanted = Array.from(incoming.childNodes);
		for (let index = 0; index < wanted.length; index++) {
			const next = wanted[index];
			const old = existing.childNodes[index];
			if (!old) {
				existing.appendChild(next.cloneNode(true));
				continue;
			}
			if (
				old.nodeType !== next.nodeType ||
				old.nodeName !== next.nodeName ||
				(old instanceof Element &&
					next instanceof Element &&
					(old.namespaceURI !== next.namespaceURI || old.id !== next.id))
			) {
				existing.replaceChild(next.cloneNode(true), old);
				continue;
			}
			if (old.nodeType === Node.TEXT_NODE || old.nodeType === Node.COMMENT_NODE) {
				if (old.nodeValue !== next.nodeValue) old.nodeValue = next.nodeValue;
			} else if (old instanceof Element && next instanceof Element) {
				for (const attr of Array.from(old.attributes))
					if (!next.hasAttributeNS(attr.namespaceURI, attr.localName))
						old.removeAttributeNS(attr.namespaceURI, attr.localName);
				for (const attr of Array.from(next.attributes))
					if (old.getAttributeNS(attr.namespaceURI, attr.localName) !== attr.value)
						old.setAttributeNS(attr.namespaceURI, attr.name, attr.value);
				reconcile(old, next);
			}
		}
		while (existing.childNodes.length > wanted.length) existing.lastChild?.remove();
	}

	function receive(event: MessageEvent) {
		const data = event.data;
		try {
			if (data?.type === 'init' && !prepared) {
				appendScript(data.purifierSource);
				if (!win.DOMPurify) throw new Error('Visualization sanitizer could not load.');
				prepared = true;
				contextChanged(data.context);
				send({ type: 'ready' });
			} else if (data?.type === 'context' && prepared) {
				contextChanged(data.context);
			} else if (data?.type === 'preview' && prepared && !initialized && !initializing) {
				const { fragment } = prepare(data.html.slice(0, safeCut(data.html)), false);
				reconcile(root, fragment);
				scheduleHeight();
			} else if (data?.type === 'finalize' && prepared && !initialized && !initializing) {
				initializing = true;
				const { fragment, scripts } = prepare(data.html, true);
				reconcile(root, fragment);
				if (data.executeScripts) {
					if (data.chartSource) {
						appendScript(data.chartSource);
						if (!win.Chart) throw new Error('Chart.js could not load.');
						contextChanged(win.openwebui.context);
					}
					// Set before running user code so its callbacks can use the bridge.
					initialized = true;
					root.inert = false;
					// Keep currentScript and sibling/container lookups consistent with the authored HTML.
					for (const placeholder of root.querySelectorAll<HTMLTemplateElement>(
						'template[data-owui-script]'
					)) {
						appendScript(scripts[Number(placeholder.dataset.owuiScript)], placeholder);
					}
				}
				initialized = true;
				initializing = false;
				send({ type: 'initialized' });
				scheduleHeight();
			} else if (data?.type === 'send-message-result') {
				requests.get(data.requestId)?.({ sent: data.sent === true });
				requests.delete(data.requestId);
			}
		} catch (error) {
			initializing = false;
			fail(error instanceof Error ? error.message : 'Visualization failed.');
		}
	}

	function connect(event: MessageEvent) {
		if (
			event.source !== parent ||
			event.data?.type !== 'visualization:connect' ||
			!event.ports[0] ||
			port
		)
			return;
		port = event.ports[0];
		port.onmessage = receive;
		window.removeEventListener('message', connect);
	}
	window.addEventListener('message', connect);
	window.addEventListener('error', (event) => fail(event.message));
	window.addEventListener('unhandledrejection', (event) => fail(String(event.reason)));
	new ResizeObserver(scheduleHeight).observe(root);
	document.addEventListener('toggle', scheduleHeight, true);
	window.addEventListener('resize', scheduleHeight);
	parent.postMessage({ type: 'visualization:connect-ready' }, '*');
}
