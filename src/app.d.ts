// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}
}

export {};

// Svelte context typing
declare module 'svelte' {
	interface ContextMap {
		i18n: import('svelte/store').Readable<import('i18next').i18n>;
	}
}
