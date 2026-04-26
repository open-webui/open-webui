<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	$: googleActive = !!($config?.features?.enable_google_drive_integration || $config?.oauth?.providers?.google);

	let connecting: string | null = null;

	async function connect(provider: string) {
		if (connecting) return;
		connecting = provider;
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/integrations/connect-url/${provider}`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				if (data.url) { window.location.href = data.url; return; }
			} else {
				window.location.href = `mailto:hola@clapnclaw.com?subject=${encodeURIComponent(provider + ' integration')}`;
				return;
			}
		} catch {}
		connecting = null;
	}

	const googleIcon = `<svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>`;

	const slackIcon = `<svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.122a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#E01E5A"/></svg>`;

	const notionIcon = `<svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z" fill="#000"/></svg>`;

	const msIcon = `<svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M11.5 2H2v9.5h9.5V2z" fill="#F25022"/><path d="M22 2h-9.5v9.5H22V2z" fill="#7FBA00"/><path d="M11.5 12.5H2V22h9.5v-9.5z" fill="#00A4EF"/><path d="M22 12.5h-9.5V22H22v-9.5z" fill="#FFB900"/></svg>`;

	const githubIcon = `<svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" fill="#181717"/></svg>`;

	const hubspotIcon = `<svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M18.164 7.93V5.084a2.198 2.198 0 0 0 1.27-1.978V3.06A2.198 2.198 0 0 0 17.24.862h-.047a2.198 2.198 0 0 0-2.193 2.198v.046a2.198 2.198 0 0 0 1.27 1.978V7.93a6.232 6.232 0 0 0-2.962 1.307L5.028 3.544a2.457 2.457 0 1 0-.999 1.386l8.142 5.62a6.232 6.232 0 0 0-.928 3.28c0 1.18.328 2.28.9 3.213l-2.456 2.456a1.854 1.854 0 0 0-.54-.083 1.875 1.875 0 1 0 1.875 1.875 1.854 1.854 0 0 0-.083-.54l2.425-2.425A6.243 6.243 0 1 0 18.164 7.93zm-.97 9.386a3.535 3.535 0 1 1 0-7.07 3.535 3.535 0 0 1 0 7.07z" fill="#FF7A59"/></svg>`;
</script>

<div class="rounded-2xl px-5 py-4 border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
	<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40 mb-4">
		{$i18n.t('Integrations')}
	</p>

	<!-- Available now -->
	<div class="flex flex-wrap gap-3 mb-4">

		<!-- Google Workspace -->
		<div class="flex items-center gap-3 px-4 py-3 rounded-xl border border-black/[.07] dark:border-white/[.07] transition-all">
			{@html googleIcon}
			<div>
				<p class="text-xs font-semibold text-gray-800 dark:text-white leading-tight">Google Workspace</p>
				<p class="text-[10px] text-gray-500 dark:text-gray-400">Gmail · Drive · Calendar</p>
			</div>
			{#if googleActive}
				<span class="text-[10px] font-semibold ml-2 px-2 py-0.5 rounded-full" style="background:#0D5C3F;color:#F5F0E8">
					{$i18n.t('Active')}
				</span>
			{:else}
				<button
					class="text-[10px] font-semibold ml-2 px-2.5 py-1 rounded-full border border-black/[.12] dark:border-white/[.12] text-gray-600 dark:text-gray-300 hover:bg-black/[.05] dark:hover:bg-white/[.05] transition cursor-pointer disabled:opacity-40"
					disabled={connecting === 'google'}
					on:click={() => connect('google')}
				>
					{connecting === 'google' ? '...' : $i18n.t('Connect')}
				</button>
			{/if}
		</div>

		<!-- Slack -->
		<div class="flex items-center gap-3 px-4 py-3 rounded-xl border border-black/[.07] dark:border-white/[.07] transition-all">
			{@html slackIcon}
			<div>
				<p class="text-xs font-semibold text-gray-800 dark:text-white leading-tight">Slack</p>
				<p class="text-[10px] text-gray-500 dark:text-gray-400">{$i18n.t('Messages · Channels')}</p>
			</div>
			<button
				class="text-[10px] font-semibold ml-2 px-2.5 py-1 rounded-full border border-black/[.12] dark:border-white/[.12] text-gray-600 dark:text-gray-300 hover:bg-black/[.05] dark:hover:bg-white/[.05] transition cursor-pointer disabled:opacity-40"
				disabled={connecting === 'slack'}
				on:click={() => connect('slack')}
			>
				{connecting === 'slack' ? '...' : $i18n.t('Connect')}
			</button>
		</div>

		<!-- Notion -->
		<div class="flex items-center gap-3 px-4 py-3 rounded-xl border border-black/[.07] dark:border-white/[.07] transition-all">
			{@html notionIcon}
			<div>
				<p class="text-xs font-semibold text-gray-800 dark:text-white leading-tight">Notion</p>
				<p class="text-[10px] text-gray-500 dark:text-gray-400">{$i18n.t('Pages · Databases')}</p>
			</div>
			<button
				class="text-[10px] font-semibold ml-2 px-2.5 py-1 rounded-full border border-black/[.12] dark:border-white/[.12] text-gray-600 dark:text-gray-300 hover:bg-black/[.05] dark:hover:bg-white/[.05] transition cursor-pointer disabled:opacity-40"
				disabled={connecting === 'notion'}
				on:click={() => connect('notion')}
			>
				{connecting === 'notion' ? '...' : $i18n.t('Connect')}
			</button>
		</div>
	</div>

	<!-- Coming soon -->
	<div>
		<p class="text-[9px] font-semibold uppercase tracking-[.1em] text-gray-300 dark:text-gray-600 mb-2">{$i18n.t('Coming Soon')}</p>
		<div class="flex flex-wrap gap-2">

			<!-- Microsoft 365 -->
			<div class="flex items-center gap-2 px-3 py-2 rounded-lg border border-black/[.05] dark:border-white/[.05] opacity-50">
				{@html msIcon}
				<div>
					<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 leading-tight">Microsoft 365</p>
					<p class="text-[10px] text-gray-400">Outlook · SharePoint · Teams</p>
				</div>
			</div>

			<!-- GitHub -->
			<div class="flex items-center gap-2 px-3 py-2 rounded-lg border border-black/[.05] dark:border-white/[.05] opacity-50">
				{@html githubIcon}
				<div>
					<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 leading-tight">GitHub</p>
					<p class="text-[10px] text-gray-400">{$i18n.t('Repositories · Issues')}</p>
				</div>
			</div>

			<!-- HubSpot -->
			<div class="flex items-center gap-2 px-3 py-2 rounded-lg border border-black/[.05] dark:border-white/[.05] opacity-50">
				{@html hubspotIcon}
				<div>
					<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 leading-tight">HubSpot</p>
					<p class="text-[10px] text-gray-400">CRM · Contacts</p>
				</div>
			</div>
		</div>
	</div>
</div>
