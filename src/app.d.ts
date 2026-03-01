// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	interface Window {
		umami?: {
			track: (eventName?: string | Record<string, unknown>, data?: Record<string, unknown>) => void;
			identify: (
				idOrData: string | Record<string, unknown>,
				data?: Record<string, unknown>
			) => void;
		};
	}

	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}
}

export {};
