// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	class AudioWorkletProcessor {
		readonly port: MessagePort;
	}
	function registerProcessor(name: string, processor: typeof AudioWorkletProcessor): void;

	const APP_VERSION: string;
	const APP_BUILD_HASH: string;
	const APP_BUILD_CHANNEL: 'main' | 'dev' | 'unknown';

	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}
}

export {};
