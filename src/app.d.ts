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

// mammoth.js ships no @types/mammoth; declare the browser entry we use for
// docx text extraction in temporary chats.
declare module 'mammoth/mammoth.browser' {
	export function extractRawText(input: {
		arrayBuffer: ArrayBuffer;
	}): Promise<{ value: string; messages: any[] }>;
}

export {};
