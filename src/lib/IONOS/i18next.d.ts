/* Type augmentations for i18next and Svelte
 */

export type I18NextOptions = {
	ns?: string;
	[key: string]: unknown;
}

export interface I18Next {
	t(key: string, options?: I18NextOptions): string;
}
