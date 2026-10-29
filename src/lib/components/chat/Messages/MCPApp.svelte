<script context="module" lang="ts">
	import type { CallToolResult } from '@modelcontextprotocol/client';

	export type MCPAppEmbed = {
		type: 'mcp_app';
		server_id: string;
		tool_name: string;
		binding: string;
		arguments: Record<string, unknown>;
		result: CallToolResult;
	};
</script>

<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { AppBridge, PostMessageTransport } from '@modelcontextprotocol/ext-apps/app-bridge';
	import { WEBUI_API_BASE_URL, WEBUI_VERSION } from '$lib/constants';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { injectCsp } from '$lib/utils/csp';

	export let app: MCPAppEmbed;
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const lifetime = new AbortController();
	let iframe: HTMLIFrameElement;
	let bridge: AppBridge | undefined;
	let initialized = false;
	let closing = false;
	let status = 'Loading widget…';
	let link = '';
	let showConfirmation = false;
	let confirmationText = '';
	let confirmCall: ((accept: boolean) => void) | undefined;
	let observer: ResizeObserver | undefined;
	let loadTimeout: ReturnType<typeof setTimeout>;

	async function rpc(method: string, params: object, signal?: AbortSignal) {
		if (closing) throw new Error('Widget closed');
		const response = await fetch(
			`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(`server:mcp:${app.server_id}`)}/mcp/app/rpc`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ tool_name: app.tool_name, binding: app.binding, method, params }),
				signal: AbortSignal.any([
					lifetime.signal,
					AbortSignal.timeout(60000),
					...(signal ? [signal] : [])
				])
			}
		);
		if (!response.ok) {
			const error = await response.json().catch(() => null);
			throw new Error(
				typeof error?.detail === 'string'
					? error.detail
					: `Widget request failed (${response.status})`
			);
		}
		return response.json();
	}

	function confirmTool(name: string, args: object, signal: AbortSignal): Promise<boolean> {
		return new Promise((resolve) => {
			if (confirmCall || closing || signal.aborted) return resolve(false);
			const abort = () => finish(false);
			const finish = (accept: boolean) => {
				signal.removeEventListener('abort', abort);
				showConfirmation = false;
				confirmCall = undefined;
				resolve(accept);
			};
			signal.addEventListener('abort', abort, { once: true });
			confirmationText = `${app.server_id}: ${name}\n${JSON.stringify(args, null, 2)}`;
			confirmCall = finish;
			showConfirmation = true;
		});
	}

	async function start() {
		const resource = await rpc('ui/resource', {});
		if (closing) return;
		bridge = new AppBridge(
			null,
			{ name: 'Open WebUI', version: WEBUI_VERSION },
			{
				openLinks: {},
				serverTools: {},
				serverResources: {},
				sandbox: { csp: resource.ui.csp ?? {} }
			},
			{
				hostContext: {
					theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
					platform: 'web',
					displayMode: 'inline',
					availableDisplayModes: ['inline'],
					locale: navigator.language,
					timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
					toolInfo: { tool: resource.tool },
					containerDimensions: { width: iframe.clientWidth, maxHeight: 10000 }
				}
			}
		);
		bridge.oncalltool = async ({ name, arguments: args }, extra) => {
			const signal = AbortSignal.any([
				lifetime.signal,
				extra.mcpReq.signal,
				AbortSignal.timeout(120000)
			]);
			if (!(await confirmTool(name, args ?? {}, signal))) throw new Error('Tool call cancelled');
			return rpc('tools/call', { name, arguments: args ?? {} }, signal);
		};
		bridge.onreadresource = (params, extra) =>
			rpc('resources/read', { uri: params.uri }, extra.mcpReq.signal);
		bridge.onlistresources = (params, extra) =>
			rpc('resources/list', params?.cursor ? { cursor: params.cursor } : {}, extra.mcpReq.signal);
		bridge.onopenlink = async ({ url }) => {
			const parsed = new URL(url);
			if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password)
				throw new Error('Invalid link');
			link = parsed.href;
			window.open(link, '_blank', 'noopener,noreferrer');
			return {};
		};
		bridge.onrequestdisplaymode = async () => ({ mode: 'inline' });
		bridge.onsizechange = ({ height }) => {
			if (height !== undefined && Number.isFinite(height))
				iframe.style.height = `${Math.max(100, Math.min(10000, height))}px`;
		};
		bridge.oninitialized = () => {
			initialized = true;
			clearTimeout(loadTimeout);
			status = '';
			void bridge!.sendToolInput({ arguments: app.arguments });
			void bridge!.sendToolResult(app.result);
		};
		bridge.onerror = () => {
			status = 'Widget communication failed';
		};
		observer = new ResizeObserver(() => {
			if (initialized)
				bridge?.sendHostContextChange({
					containerDimensions: { width: iframe.clientWidth, maxHeight: 10000 }
				});
		});
		observer.observe(iframe);
		await bridge.connect(new PostMessageTransport(iframe.contentWindow!, iframe.contentWindow!));
		if (closing) {
			await bridge.close();
			return;
		}
		// shortcut: apps needing browser storage require a separate origin; keep srcdoc opaque.
		iframe.srcdoc =
			injectCsp('', resource.csp) +
			injectCsp('', resource.additional_csp) +
			'<style>*{scrollbar-width:none}::-webkit-scrollbar{display:none}</style>' +
			resource.html;
	}

	function stop() {
		if (closing) return;
		closing = true;
		clearTimeout(loadTimeout);
		observer?.disconnect();
		confirmCall?.(false);
		lifetime.abort();
		if (initialized) {
			void bridge
				?.teardownResource({}, { timeout: 1000 })
				.catch(() => {})
				.finally(() => bridge?.close());
		} else {
			void bridge?.close();
		}
	}

	// Keep the frame mounted briefly so the app can acknowledge teardown before removal.
	function teardown(node: HTMLElement) {
		node.inert = true;
		stop();
		return { duration: initialized ? 1100 : 0 };
	}

	onMount(() => {
		loadTimeout = setTimeout(() => {
			status = 'Widget did not initialize';
			stop();
		}, 30000);
		void start().catch((error) => {
			if (!closing) {
				status = error.message;
				stop();
			}
		});
	});
	onDestroy(stop);
</script>

<div out:teardown|global>
	{#if status}<p role="status" class="text-sm text-gray-500">{$i18n.t(status)}</p>{/if}
	<iframe
		bind:this={iframe}
		title={app.tool_name}
		class="w-full border-0 rounded-xl"
		style="height:300px"
		sandbox="allow-scripts allow-downloads allow-popups"
		referrerpolicy="no-referrer"
	></iframe>
	{#if link}<a href={link} target="_blank" rel="noopener noreferrer" class="text-sm underline"
			>{$i18n.t('Open link')}</a
		>{/if}
</div>
{#if showConfirmation}
	<ConfirmDialog
		bind:show={showConfirmation}
		title={$i18n.t('Tool call')}
		on:confirm={() => confirmCall?.(true)}
		on:cancel={() => confirmCall?.(false)}
	>
		<pre class="whitespace-pre-wrap break-words text-sm">{confirmationText}</pre>
	</ConfirmDialog>
{/if}
