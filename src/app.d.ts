// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
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
