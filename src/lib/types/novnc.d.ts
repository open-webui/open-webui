declare module '@novnc/novnc' {
	export default class RFB extends EventTarget {
		constructor(target: HTMLElement, channel: WebSocket);
		// shortcut: noVNC 1.7 has no public cursor container option; recheck on upgrades.
		_cursor: { _canvas: HTMLCanvasElement; detach(): void };
		scaleViewport: boolean;
		resizeSession: boolean;
		qualityLevel: number;
		viewOnly: boolean;
		disconnect(): void;
		clipboardPasteFrom(text: string): void;
		sendKey(keysym: number, code: string, down?: boolean): void;
	}
}
