<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	$: googleActive = !!($config?.features?.enable_google_drive_integration || $config?.oauth?.providers?.google);

	let googleConnecting = false;
	let slackConnecting = false;
	let notionConnecting = false;

	async function connect(provider: string, setLoading: (v: boolean) => void) {
		setLoading(true);
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/integrations/connect-url/${provider}`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				if (data.url) { window.location.href = data.url; return; }
			} else {
				// Provider not configured yet — redirect to contact
				window.location.href = `mailto:hola@clapnclaw.com?subject=${encodeURIComponent(provider + ' integration')}`;
				return;
			}
		} catch { /* fall through */ }
		setLoading(false);
	}
</script>

<div class="flex items-center justify-center gap-2 px-2 py-1.5 flex-wrap">

	<!-- Google Workspace -->
	{#if googleActive}
		<div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-black/10 dark:border-white/10 text-gray-500 dark:text-gray-400 bg-black/[.02] dark:bg-white/[.03]">
			<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
				<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
				<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
				<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
				<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
			</svg>
			Google
			<span class="size-1.5 rounded-full bg-emerald-500 ml-0.5" />
		</div>
	{:else}
		<button
			class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-black/10 dark:border-white/10 text-gray-500 dark:text-gray-400 bg-transparent hover:bg-black/[.04] dark:hover:bg-white/[.05] transition-all disabled:opacity-40 cursor-pointer"
			disabled={googleConnecting}
			on:click={() => connect('google', (v) => googleConnecting = v)}
		>
			<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
				<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
				<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
				<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
				<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
			</svg>
			{googleConnecting ? '...' : 'Google'}
		</button>
	{/if}

	<!-- Slack -->
	<button
		class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-black/10 dark:border-white/10 text-gray-500 dark:text-gray-400 bg-transparent hover:bg-black/[.04] dark:hover:bg-white/[.05] transition-all disabled:opacity-40 cursor-pointer"
		disabled={slackConnecting}
		on:click={() => connect('slack', (v) => slackConnecting = v)}
	>
		<svg viewBox="0 0 24 24" width="13" height="13" xmlns="http://www.w3.org/2000/svg">
			<path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.122a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#E01E5A"/>
		</svg>
		{slackConnecting ? '...' : 'Slack'}
	</button>

	<!-- Notion -->
	<button
		class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-black/10 dark:border-white/10 text-gray-500 dark:text-gray-400 bg-transparent hover:bg-black/[.04] dark:hover:bg-white/[.05] transition-all disabled:opacity-40 cursor-pointer"
		disabled={notionConnecting}
		on:click={() => connect('notion', (v) => notionConnecting = v)}
	>
		<svg viewBox="0 0 24 24" width="13" height="13" xmlns="http://www.w3.org/2000/svg">
			<path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z" fill="#000"/>
		</svg>
		{notionConnecting ? '...' : 'Notion'}
	</button>

</div>
