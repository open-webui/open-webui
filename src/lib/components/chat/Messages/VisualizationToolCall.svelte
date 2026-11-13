<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { get } from 'svelte/store';
	import { chatId as activeChatId, config, settings } from '$lib/stores';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ToolCallDisplay from '$lib/components/common/ToolCallDisplay.svelte';
	import { buildToolCallToken, getToolResultText, type OutputItem } from './structuredOutput';
	import {
		createVisualizationArgumentDecoder,
		parseVisualizationArguments,
		type VisualizationArguments
	} from '$lib/utils/visualizations/arguments';
	import {
		getVisualizationVendor,
		visualizationDocument,
		repairVisualizationHtml
	} from '$lib/utils/visualizations/frame';

	export let call: OutputItem;
	export let result: OutputItem | undefined = undefined;
	export let chatId = '';
	export let messageId = '';
	export let messageDone = false;
	export let allowEmbeds = false;
	export let compactPreview = false;
	export let resolvable = false;
	export let resolving = false;
	export let onResolve: (approved: boolean) => void = () => {};
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const decoder = createVisualizationArgumentDecoder();
	let ready = false,
		initialized = false;
	let runtimeError = '',
		frameRevision = 0,
		generation = 0,
		submittedKey = '';
	let port: MessagePort | undefined;
	let timer: ReturnType<typeof setTimeout> | undefined;
	let latest: {
		source: string;
		args: VisualizationArguments | null;
		accepted: boolean;
		execute: boolean;
	};
	let confirmationText = '',
		showConfirmation = false;
	let confirmCall: ((accept: boolean) => void) | undefined;

	function acceptedResult(item: OutputItem | undefined) {
		try {
			return (
				item?.status === 'completed' && JSON.parse(getToolResultText(item)).status === 'accepted'
			);
		} catch {
			return false;
		}
	}

	$: raw =
		typeof call.arguments === 'string' ? call.arguments : JSON.stringify(call.arguments ?? {});
	$: decoded = decoder.update(raw);
	$: args = parseVisualizationArguments(call.arguments);
	$: source = args?.html ?? decoded.html;
	$: accepted = acceptedResult(result);
	$: enabled = allowEmbeds && !compactPreview;
	$: execute = $settings?.iframeSandboxAllowScripts ?? true;
	$: finalKey = accepted && args ? JSON.stringify([args.html, args.libraries, execute]) : '';
	$: if (submittedKey && submittedKey !== finalKey) {
		submittedKey = '';
		frameRevision++;
	}
	$: token = buildToolCallToken(call, result ? { [call.call_id ?? call.id ?? '']: result } : {});
	$: needsToolDetails =
		['pending', 'queued', 'requires_approval', 'failed', 'rejected', 'incomplete'].includes(
			call.status ?? ''
		) || result?.status === 'failed';
	$: title = args?.title ?? decoded.title ?? $i18n.t('Visualization');
	$: srcdoc = visualizationDocument($config?.ui?.iframe_csp ?? '');
	$: queue(source, args, accepted, execute, ready);
	$: if (ready) sendContext($i18n.language);

	function context(language = $i18n.language) {
		return {
			theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
			textScale:
				getComputedStyle(document.documentElement).getPropertyValue('--app-text-scale').trim() ||
				'1',
			language: language || document.documentElement.lang || navigator.language,
			direction: $i18n.dir?.() ?? document.documentElement.dir ?? 'ltr',
			reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
		};
	}
	function sendContext(language?: string) {
		port?.postMessage({ type: 'context', context: context(language) });
	}

	function queue(
		source: string,
		args: VisualizationArguments | null,
		accepted: boolean,
		execute: boolean,
		ready: boolean
	) {
		latest = { source, args, accepted, execute };
		if (!ready) return;
		if (accepted && args) {
			clearTimeout(timer);
			timer = undefined;
			void flush();
		} else if (!timer) {
			timer = setTimeout(() => {
				timer = undefined;
				void flush();
			}, 100);
		}
	}
	async function flush() {
		if (!ready || !port || !latest) return;
		const current = generation;
		const channel = port;
		const { source, args, accepted, execute } = latest;
		if (!accepted || !args) {
			channel.postMessage({ type: 'preview', html: source });
			return;
		}
		const key = JSON.stringify([args.html, args.libraries, execute]);
		if (submittedKey === key) return;
		submittedKey = key;
		try {
			const chartSource =
				execute && args.libraries?.includes('chartjs')
					? await getVisualizationVendor('chartjs')
					: undefined;
			if (generation !== current || submittedKey !== key) return;
			channel.postMessage({
				type: 'finalize',
				html: repairVisualizationHtml(args.html),
				chartSource,
				executeScripts: execute
			});
		} catch (error) {
			if (generation === current) runtimeError = String(error);
		}
	}

	function requestMessage(
		data: { requestId: string; text: string },
		channel: MessagePort,
		current: number
	) {
		const reply = (sent: boolean) => {
			if (generation === current)
				channel.postMessage({ type: 'send-message-result', requestId: data.requestId, sent });
		};
		if (
			!initialized ||
			!execute ||
			confirmCall ||
			get(activeChatId) !== chatId ||
			typeof data.requestId !== 'string' ||
			data.requestId.length > 80 ||
			typeof data.text !== 'string' ||
			!data.text.trim() ||
			data.text.length > 16000
		) {
			reply(false);
			return;
		}
		confirmationText = data.text;
		showConfirmation = true;
		confirmCall = (accept) => {
			showConfirmation = false;
			confirmCall = undefined;
			const sent = accept && current === generation && get(activeChatId) === chatId;
			if (sent) window.postMessage({ type: 'input:prompt:submit', text: data.text }, window.origin);
			reply(sent);
		};
	}

	function mountFrame(node: HTMLIFrameElement) {
		const current = ++generation;
		ready = false;
		initialized = false;
		runtimeError = '';
		submittedKey = '';
		let connected = false,
			loads = 0;
		let reportedHeight = 1;
		const resize = () => {
			node.style.height = `${Math.max(1, reportedHeight)}px`;
		};
		const timeout = setTimeout(() => {
			if (!ready && generation === current)
				runtimeError = $i18n.t('Visualization could not start.');
		}, 10000);
		const receiveHandshake = async (event: MessageEvent) => {
			if (
				event.source !== node.contentWindow ||
				event.data?.type !== 'visualization:connect-ready' ||
				connected
			)
				return;
			connected = true;
			const channel = new MessageChannel();
			port = channel.port1;
			channel.port1.onmessage = (event) => {
				if (generation !== current) return;
				const data = event.data;
				if (data?.type === 'ready') {
					clearTimeout(timeout);
					ready = true;
				} else if (data?.type === 'initialized') initialized = true;
				else if (
					data?.type === 'height' &&
					typeof data.value === 'number' &&
					Number.isFinite(data.value)
				) {
					reportedHeight = data.value;
					resize();
				} else if (data?.type === 'error') runtimeError = String(data.message).slice(0, 500);
				else if (data?.type === 'send-message') requestMessage(data, channel.port1, current);
			};
			node.contentWindow?.postMessage({ type: 'visualization:connect' }, '*', [channel.port2]);
			try {
				const purifierSource = await getVisualizationVendor('purifier');
				if (generation === current)
					channel.port1.postMessage({ type: 'init', purifierSource, context: context() });
			} catch (error) {
				if (generation === current) runtimeError = String(error);
			}
		};
		const onLoad = () => {
			if (++loads > 1) {
				port?.close();
				ready = false;
				confirmCall?.(false);
				runtimeError = $i18n.t('Visualization stopped after navigation.');
			}
		};
		node.addEventListener('load', onLoad);
		window.addEventListener('message', receiveHandshake);
		const observer = new MutationObserver(() => sendContext());
		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class', 'dir', 'lang', 'style']
		});
		const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
		const onMotion = () => sendContext();
		motion.addEventListener('change', onMotion);
		const unsubscribe = activeChatId.subscribe((id) => {
			if (id !== chatId) confirmCall?.(false);
		});
		resize();
		return {
			destroy() {
				confirmCall?.(false);
				generation++;
				port?.close();
				port = undefined;
				ready = false;
				initialized = false;
				submittedKey = '';
				clearTimeout(timeout);
				clearTimeout(timer);
				timer = undefined;
				observer.disconnect();
				unsubscribe();
				motion.removeEventListener('change', onMotion);
				node.removeEventListener('load', onLoad);
				window.removeEventListener('message', receiveHandshake);
			}
		};
	}

	onDestroy(() => confirmCall?.(false));
</script>

<section class="my-1 min-w-0" aria-label={title} data-visualization-call={call.call_id ?? call.id}>
	<div class="mb-0.5 text-xs font-medium">{title}</div>
	{#if needsToolDetails}
		<div>
			<ToolCallDisplay
				attributes={token.attributes}
				resultContent={token.text}
				{resolvable}
				{resolving}
				{onResolve}
			/>
		</div>
	{/if}
	{#if enabled}
		{#key `${chatId}:${messageId}:${frameRevision}`}
			<iframe
				use:mountFrame
				{srcdoc}
				{title}
				sandbox="allow-scripts"
				referrerpolicy="no-referrer"
				class="block w-full border-0"
			></iframe>
		{/key}
	{/if}

	{#if runtimeError || decoded.malformed}
		<p role="status" class="mt-1 text-xs text-red-600 dark:text-red-400">
			{runtimeError || $i18n.t('Visualization arguments are incomplete or invalid.')}
		</p>
	{:else if enabled && !initialized}
		<p role="status" class="mt-1 text-xs text-gray-500">
			{messageDone && !accepted
				? $i18n.t('Visualization incomplete.')
				: accepted
					? $i18n.t('Preparing visualization…')
					: $i18n.t('Drawing preview…')}
		</p>
	{:else if enabled && !execute}
		<p class="mt-1 text-xs text-gray-500">{$i18n.t('Interactive scripts are disabled.')}</p>
	{/if}
</section>

{#if showConfirmation}
	<ConfirmDialog
		bind:show={showConfirmation}
		title={$i18n.t('Confirm Prompt from Embed')}
		on:confirm={() => confirmCall?.(true)}
		on:cancel={() => confirmCall?.(false)}
	>
		<div class="whitespace-pre-wrap">{confirmationText}</div>
	</ConfirmDialog>
{/if}
