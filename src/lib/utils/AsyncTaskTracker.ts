import { getContext, setContext } from 'svelte';

/**
 * Context key for {@link AsyncTaskTracker} when provided via Svelte `setContext`.
 * Use {@link getContextAsyncTaskTracker} to retrieve the tracker in component code.
 */
const ASYNC_TASK_TRACKER_CONTEXT = 'open-webui:async-task-tracker';

/**
 * Options for {@link AsyncTaskTracker.waitForSettled}.
 */
export type WaitForSettledOptions = {
	/** Maximum time to wait before throwing (ms). Default `10_000`. */
	timeoutMs?: number;
	/** Time after last pending change to consider "settled" (ms). Default `250`. */
	quietWindowMs?: number;
	/** Interval between pending checks while there are active tasks (ms). Default `50`. */
	pollIntervalMs?: number;
	/** Optional abort signal to cancel waiting. */
	signal?: AbortSignal;
};

const createAbortError = (): Error => {
	const error = new Error('Async task wait cancelled');
	error.name = 'AbortError';
	return error;
};

const throwIfAborted = (signal?: AbortSignal): void => {
	if (signal?.aborted) {
		throw createAbortError();
	}
};

const sleep = (ms: number): Promise<void> => {
	return new Promise((resolve) => setTimeout(resolve, ms));
};

/**
 * Tracks async tasks and supports waiting until the queue is idle and stable
 * (e.g. for PDF export after KaTeX / Mermaid / Vega have finished rendering).
 * Can be provided via Svelte context using {@link ASYNC_TASK_TRACKER_CONTEXT}.
 */
export class AsyncTaskTracker {
	private pendingCount = 0;
	private version = 0;

	/**
	 * Register a task start. Returns a function to call when the task finishes.
	 * Prefer {@link track} for promise-based work.
	 * @param _label - Optional label for debugging (not used by wait logic).
	 * @returns Call this to mark the task as finished.
	 */
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	begin(label?: string): () => void {
		this.pendingCount += 1;
		this.version += 1;

		let closed = false;
		return () => {
			if (closed) {
				return;
			}
			closed = true;
			this.pendingCount = Math.max(0, this.pendingCount - 1);
			this.version += 1;
		};
	}

	/**
	 * Run an async workload and count it as one task (start on call, end when the promise settles).
	 * @param work - Promise or no-arg function returning a promise.
	 * @param label - Optional label for debugging.
	 * @returns The result of the promise.
	 */
	async track<T>(work: Promise<T> | (() => Promise<T>), label?: string): Promise<T> {
		const end = this.begin(label);
		try {
			return await (typeof work === 'function' ? work() : work);
		} finally {
			end();
		}
	}

	/** Current number of tasks that have started but not yet finished. */
	getPendingCount(): number {
		return this.pendingCount;
	}

	/** True if there is at least one active task. */
	hasPendingTasks(): boolean {
		return this.pendingCount > 0;
	}

	/**
	 * Wait until there are no pending tasks and no new task has been registered
	 * for the duration of `quietWindowMs`. Handles late-registering tasks (e.g.
	 * components that mount and then start work after a tick).
	 * @param options - Timeouts and optional abort signal.
	 * @throws Error if timeout is reached or signal is aborted.
	 */
	async waitForSettled(options: WaitForSettledOptions = {}): Promise<void> {
		const timeoutMs = options.timeoutMs ?? 15_000;
		const quietWindowMs = options.quietWindowMs ?? 250;
		const pollIntervalMs = options.pollIntervalMs ?? 50;
		const deadline = Date.now() + timeoutMs;

		while (Date.now() <= deadline) {
			throwIfAborted(options.signal);

			if (!this.hasPendingTasks()) {
				const versionAtIdle = this.version;
				await sleep(Math.min(quietWindowMs, Math.max(1, deadline - Date.now())));
				throwIfAborted(options.signal);

				if (!this.hasPendingTasks() && this.version === versionAtIdle) {
					return;
				}
				continue;
			}

			await sleep(Math.min(pollIntervalMs, Math.max(1, deadline - Date.now())));
		}

		throw new Error('Timed out while waiting for async tasks to settle');
	}
}

/**
 * Get the {@link AsyncTaskTracker} from Svelte context, if one was provided
 * (e.g. by a parent that called `setContext(ASYNC_TASK_TRACKER_CONTEXT, tracker)`).
 * Must be called during component initialisation.
 * @returns The tracker instance or `undefined` if not in a tree that provides it.
 */
export function getContextAsyncTaskTracker(): AsyncTaskTracker | undefined {
	return getContext<AsyncTaskTracker | undefined>(ASYNC_TASK_TRACKER_CONTEXT);
}

/**
 * Set the {@link AsyncTaskTracker} in Svelte context.
 * @param tracker - The tracker instance.
 * @returns The tracker instance.
 */
export function setupContextAsyncTaskTracker() {
	const tracker = new AsyncTaskTracker();
	setContext(ASYNC_TASK_TRACKER_CONTEXT, tracker);
	return tracker;
}
