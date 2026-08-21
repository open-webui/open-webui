<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { getPluginApp, getPluginPage, pluginAssetUrl, type PluginApp } from '$lib/apis/plugins';

	export let pluginId: string;
	export let pageId: string;
	export let token = '';

	type PluginModule = {
		mount: (target: HTMLElement, context: PluginContext) => void | Promise<void>;
		unmount?: () => void | Promise<void>;
	};

	export type PluginContext = {
		plugin: Pick<PluginApp, 'id' | 'title' | 'revision'>;
		assetUrl: (path: string) => string;
	};

	let target: HTMLDivElement;
	let error = '';
	let loading = true;
	let mountedModule: PluginModule | null = null;
	let disposed = false;

	const isSafeAssetPath = (path: string) =>
		!!path && !path.startsWith('/') && !path.includes('://') && !path.split('/').some((part) => !part || part === '.' || part === '..');

	const createContext = (app: PluginApp, entryUrl: string): PluginContext => ({
		plugin: { id: app.id, title: app.title, revision: app.revision },
		assetUrl: (path) => {
			if (!isSafeAssetPath(path)) throw new Error('Plugin asset paths must be relative');
			const resolved = new URL(path, entryUrl);
			if (!isPluginUrl(resolved, entryUrl)) throw new Error('Plugin asset must stay within its namespace');
			return resolved.href;
		}
	});

	const isPluginUrl = (url: URL, entryUrl: string) => url.href.startsWith(entryUrl.slice(0, entryUrl.lastIndexOf('/') + 1));

	const resolveRelativeAssets = (parsedDocument: Document, entryUrl: string) => {
		for (const element of parsedDocument.querySelectorAll<HTMLElement>('[src], link[href]')) {
			const attribute = element.hasAttribute('src') ? 'src' : 'href';
			const value = element.getAttribute(attribute);
			if (!value || value.startsWith('#') || value.startsWith('data:')) continue;
			const resolved = new URL(value, entryUrl);
			if (!isPluginUrl(resolved, entryUrl)) {
				element.remove();
				continue;
			}
			element.setAttribute(attribute, resolved.href);
		}
	};

	const mountHtml = async (app: PluginApp, entryUrl: string) => {
		const response = await fetch(entryUrl, { headers: token ? { authorization: `Bearer ${token}` } : {} });
		if (!response.ok) throw new Error(`Failed to load plugin page (${response.status})`);

		const parsedDocument = new DOMParser().parseFromString(await response.text(), 'text/html');
		for (const base of parsedDocument.querySelectorAll('base')) base.remove();
		resolveRelativeAssets(parsedDocument, entryUrl);

		const scripts = [...parsedDocument.querySelectorAll('script')];
		for (const script of scripts) script.remove();
		const stylesheets = [...parsedDocument.head.querySelectorAll('link[rel="stylesheet"]')];
		target.replaceChildren(...stylesheets, ...Array.from(parsedDocument.body.childNodes));

		for (const source of scripts) {
			const src = source.getAttribute('src');
			if (!src) continue; // Inline scripts conflict with CSP; use an external relative file.
			const resolved = new URL(src, entryUrl);
			if (!isPluginUrl(resolved, entryUrl)) continue;
			const script = window.document.createElement('script');
			if (source.type) script.type = source.type;
			script.src = resolved.href;
			await new Promise<void>((resolve, reject) => {
				script.addEventListener('load', () => resolve(), { once: true });
				script.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), {
					once: true
				});
				target.append(script);
			});
		}
	};

	onMount(async () => {
		try {
			const app = await getPluginApp(token, pluginId);
			if (!app) throw new Error('Plugin page is unavailable');
			const page = getPluginPage(app, pageId);
			if (!page) throw new Error('Plugin page is unavailable');
			const entryUrl = pluginAssetUrl(app, page.entrypoint);

			if (page.entrypoint.endsWith('.html')) {
				await mountHtml(app, entryUrl);
			} else {
				const module = (await import(/* @vite-ignore */ entryUrl)) as PluginModule;
				if (typeof module.mount !== 'function') throw new Error('Plugin module must export mount(target, context)');
				if (!disposed) {
					mountedModule = module;
					await module.mount(target, createContext(app, entryUrl));
				}
			}
		} catch (err) {
			console.error('Failed to mount plugin page:', err);
			error = err instanceof Error ? err.message : 'Failed to load plugin page';
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		disposed = true;
		void mountedModule?.unmount?.();
		target?.replaceChildren();
	});
</script>

{#if loading}
	<div class="flex h-full items-center justify-center text-sm text-gray-500">Loading app…</div>
{:else if error}
	<div class="flex h-full items-center justify-center p-6 text-sm text-red-600 dark:text-red-400">{error}</div>
{/if}

<div bind:this={target} class="ow-plugin-page min-h-full" aria-busy={loading}></div>
