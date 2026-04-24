<script lang="ts">
	import { config } from '$lib/stores';

	$: googleActive = !!($config?.features?.enable_google_drive_integration || $config?.oauth?.providers?.google);
	$: microsoftActive = !!$config?.oauth?.providers?.microsoft;
	$: googleAvailable = true;

	const googleIcon = `<svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>`;

	const msIcon = `<svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg"><path d="M11.5 2H2v9.5h9.5V2z" fill="#F25022"/><path d="M22 2h-9.5v9.5H22V2z" fill="#7FBA00"/><path d="M11.5 12.5H2V22h9.5v-9.5z" fill="#00A4EF"/><path d="M22 12.5h-9.5V22H22v-9.5z" fill="#FFB900"/></svg>`;

	const slackIcon = `<svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg"><path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.122a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#E01E5A"/></svg>`;
</script>

<div class="rounded-2xl px-5 py-4 border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
	<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40 mb-3">
		Integraciones
	</p>

	<div class="flex flex-wrap gap-3">
		<!-- Google -->
		<div
			class="flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all"
			style={googleActive
				? 'background:rgba(13,92,63,.07);border-color:rgba(13,92,63,.25)'
				: 'background:rgba(66,133,244,.04);border-color:rgba(66,133,244,.25)'}
		>
			{@html googleIcon}
			<div>
				<p class="text-xs font-semibold text-gray-800 dark:text-white leading-tight">Google Workspace</p>
				<p class="text-[10px] text-gray-500 dark:text-gray-400">Gmail · Drive · Calendar</p>
			</div>
			{#if googleActive}
				<span class="text-[10px] font-mono font-semibold ml-2 px-2 py-0.5 rounded-full" style="background:#0D5C3F;color:#F5F0E8">
					Activo
				</span>
			{:else}
				<button class="text-[10px] font-mono font-semibold ml-2 px-2 py-1 rounded-full cursor-pointer hover:opacity-80 transition-opacity" style="background:#4285F4;color:white">
					Conectar
				</button>
			{/if}
		</div>

		<!-- Microsoft — activo si OAuth configurado -->
		<div
			class="flex items-center gap-2 px-3 py-2 rounded-xl border transition-all
			{microsoftActive
				? 'border-transparent'
				: 'border-black/[.06] dark:border-white/[.06] opacity-45'}"
			style={microsoftActive ? 'background:rgba(0,114,239,.06);border-color:rgba(0,114,239,.18)' : ''}
		>
			{@html msIcon}
			<div>
				<p class="text-xs font-semibold text-gray-800 dark:text-white leading-tight">Microsoft 365</p>
				<p class="text-[10px] text-gray-400 dark:text-gray-500">Outlook · SharePoint · Teams</p>
			</div>
			{#if microsoftActive}
				<span class="text-[10px] font-mono font-semibold ml-1 px-1.5 py-0.5 rounded-full" style="background:#0D5C3F;color:#F5F0E8">
					Activo
				</span>
			{:else}
				<span class="text-[10px] font-mono text-gray-300 dark:text-gray-600 ml-1">Próximamente</span>
			{/if}
		</div>

		<!-- Slack — siempre próximamente -->
		<div class="flex items-center gap-2 px-3 py-2 rounded-xl border border-black/[.06] dark:border-white/[.06] opacity-45">
			{@html slackIcon}
			<div>
				<p class="text-xs font-semibold text-gray-800 dark:text-white leading-tight">Slack</p>
				<p class="text-[10px] text-gray-400 dark:text-gray-500">Mensajes · Canales</p>
			</div>
			<span class="text-[10px] font-mono text-gray-300 dark:text-gray-600 ml-1">Próximamente</span>
		</div>
	</div>
</div>
