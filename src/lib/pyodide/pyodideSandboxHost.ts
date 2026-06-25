// Worker-shaped Pyodide host in a sandboxed opaque-origin iframe. Never postMessage a token into it.
type Listener = (event: MessageEvent) => void;

const READY = '__pyodide_sandbox_ready__';

export class PyodideSandboxHost {
	private iframe: HTMLIFrameElement;
	private ready = false;
	private queue: { msg: unknown; transfer: Transferable[] }[] = [];
	private listeners = new Set<Listener>();
	public onmessage: Listener | null = null;
	public onerror: ((event: unknown) => void) | null = null;
	private onWindowMessage: (e: MessageEvent) => void;

	constructor(src = '/pyodide-sandbox.html') {
		const iframe = document.createElement('iframe');
		iframe.setAttribute('sandbox', 'allow-scripts');
		iframe.setAttribute('aria-hidden', 'true');
		iframe.setAttribute('title', 'pyodide-sandbox');
		iframe.style.display = 'none';
		iframe.src = src;
		this.iframe = iframe;

		this.onWindowMessage = (e: MessageEvent) => {
			if (e.source !== iframe.contentWindow) return;
			const data = e.data;
			if (data && data.type === READY) {
				this.ready = true;
				for (const item of this.queue) this.post(item.msg, item.transfer);
				this.queue = [];
				return;
			}
			const event = { data } as MessageEvent;
			this.onmessage?.(event);
			for (const listener of this.listeners) listener(event);
		};

		window.addEventListener('message', this.onWindowMessage);
		document.body.appendChild(iframe);
	}

	private post(msg: unknown, transfer: Transferable[]) {
		this.iframe.contentWindow?.postMessage(msg, '*', transfer);
	}

	postMessage(msg: unknown, transfer: Transferable[] = []) {
		if (this.ready) this.post(msg, transfer);
		else this.queue.push({ msg, transfer });
	}

	addEventListener(_type: 'message', listener: Listener) {
		this.listeners.add(listener);
	}

	removeEventListener(_type: 'message', listener: Listener) {
		this.listeners.delete(listener);
	}

	terminate() {
		window.removeEventListener('message', this.onWindowMessage);
		this.listeners.clear();
		this.onmessage = null;
		this.iframe.remove();
	}
}
