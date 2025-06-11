// Copy from https://gist.github.com/MattiasBuelens/496fc1d37adb50a733edd43853f2f60e
(ReadableStream.prototype as any)[Symbol.asyncIterator] ??= function ({
	preventCancel = false
} = {}) {
	const reader = this.getReader();
	return {
		async next() {
			try {
				const result = await reader.read();
				if (result.done) {
					reader.releaseLock();
				}
				return result;
			} catch (e) {
				reader.releaseLock();
				throw e;
			}
		},
		async return(value: any) {
			if (!preventCancel) {
				const cancelPromise = reader.cancel(value);
				reader.releaseLock();
				await cancelPromise;
			} else {
				reader.releaseLock();
			}
			return { done: true, value };
		},
		[Symbol.asyncIterator]() {
			return this;
		}
	};
};
