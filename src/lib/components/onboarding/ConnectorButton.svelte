<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let provider: string;
	export let label: string;
	export let icon: string;
	export let connected = false;
	export let optional = false;
	export let onConnect: () => void = () => {};
	export let onSkip: (() => void) | null = null;

	let connecting = false;

	async function handleConnect() {
		connecting = true;
		try {
			const res = await fetch(
				`${WEBUI_BASE_URL}/api/v1/clapnclaw/integrations/connect-url/${provider}`
			);
			const data = await res.json();

			if (data.url) {
				const popup = window.open(data.url, `connect-${provider}`, 'width=600,height=700');

				const handler = (event: MessageEvent) => {
					if (event.data?.type === 'oauth-callback' && event.data?.provider === provider) {
						connected = true;
						connecting = false;
						window.removeEventListener('message', handler);
						onConnect();
					}
				};
				window.addEventListener('message', handler);

				const pollTimer = setInterval(() => {
					if (popup?.closed) {
						clearInterval(pollTimer);
						connecting = false;
					}
				}, 500);
			}
		} catch {
			connecting = false;
		}
	}
</script>

<div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50">
	<div class="text-3xl">{icon}</div>
	<div class="flex-1">
		<div class="font-medium text-gray-900 dark:text-white">
			{label}
			{#if optional}
				<span class="text-xs text-gray-400 ml-1">(opcional)</span>
			{/if}
		</div>
	</div>
	<div>
		{#if connected}
			<span
				class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm font-medium"
			>
				Conectado
			</span>
		{:else if connecting}
			<span
				class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-claw-100 dark:bg-claw-900/30 text-claw-600 dark:text-claw-400 text-sm font-medium animate-pulse"
			>
				Conectando...
			</span>
		{:else}
			<div class="flex gap-2">
				<button
					class="px-4 py-1.5 rounded-lg bg-claw-500 hover:bg-claw-600 text-white text-sm font-medium transition"
					on:click={handleConnect}
				>
					Conectar
				</button>
				{#if optional && onSkip}
					<button
						class="px-3 py-1.5 rounded-lg text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-sm transition"
						on:click={onSkip}
					>
						Omitir
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>
