type RequestFrame = (callback: FrameRequestCallback) => number;
type CancelFrame = (handle: number) => void;

const requestBrowserFrame: RequestFrame = (callback) => requestAnimationFrame(callback);
const cancelBrowserFrame: CancelFrame = (handle) => cancelAnimationFrame(handle);

export const resolveMarkdownDone = (
	fadeStreamingText: boolean | null | undefined,
	messageDone: boolean | null | undefined
) => ((fadeStreamingText ?? true) ? (messageDone ?? false) : true);

export const createMarkdownUpdateScheduler = (
	parseTokens: () => void,
	requestFrame: RequestFrame = requestBrowserFrame,
	cancelFrame: CancelFrame = cancelBrowserFrame
) => {
	let pendingUpdate: number | null = null;

	return {
		update(content: unknown) {
			if (!content || pendingUpdate !== null) return;

			pendingUpdate = requestFrame(() => {
				pendingUpdate = null;
				parseTokens();
			});
		},
		cancel() {
			if (pendingUpdate === null) return;

			cancelFrame(pendingUpdate);
			pendingUpdate = null;
		}
	};
};
