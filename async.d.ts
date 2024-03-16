declare module 'async/queue' {
	export default function queue(
		worker: (...params) => Promise<void>,
		concurrency?: number | null,
		payload?: unknown
	);
}
