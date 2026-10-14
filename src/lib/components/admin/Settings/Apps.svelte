<script lang="ts">
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getApps, updateAppById, type App } from '$lib/apis/apps';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import AppModal from './Apps/AppModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ExperimentalBadge from '$lib/components/common/ExperimentalBadge.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Grid from '$lib/components/icons/Grid.svelte';
	const i18n = getContext<any>('i18n');
	let apps: App[] | null = null;
	let selected: App | null = null;
	let show = false;
	let busy = '';
	async function load(silent = false) {
		try {
			apps = await getApps(localStorage.token);
		} catch (error) {
			if (!silent) {
				toast.error(String(error));
				apps = [];
			}
		}
	}
	function configure(app: App | null) {
		selected = app;
		show = true;
	}
	async function toggle(app: App) {
		if (!app.is_active) {
			configure(app);
			return;
		}
		busy = app.id;
		try {
			await updateAppById(localStorage.token, app.id, { is_active: false });
			await load();
		} catch (error) {
			toast.error(String(error));
		} finally {
			busy = '';
		}
	}
	onMount(() => {
		load();
		const interval = setInterval(() => load(true), 5000);
		return () => clearInterval(interval);
	});
</script>

<AppModal bind:show app={selected} onChange={load} />
<div class="flex h-full flex-col text-sm">
	<div class="flex items-center gap-2 mb-4">
		<h2 class="text-sm font-medium text-gray-900 dark:text-white">{$i18n.t('Apps')}</h2>
		<ExperimentalBadge />
	</div>
	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<AdminSettingSection first>
			<div>
				<div class="mb-2 flex items-center justify-between">
					<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Connected apps')}</div>
					<Tooltip content={$i18n.t('Add app')}
						><button
							type="button"
							aria-label={$i18n.t('Add app')}
							class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
							on:click={() => configure(null)}><Plus /></button
						></Tooltip
					>
				</div>
				{#if apps === null}<div class="flex justify-center py-4">
						<Spinner className="size-5" />
					</div>
				{:else}<div class="flex flex-col gap-1.5">
						{#each apps as app (app.id)}
							<div class="flex w-full items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
								<div
									class="flex min-w-0 flex-1 items-center gap-1.5 {app.is_active
										? ''
										: 'opacity-50'}"
								>
									{#if app.data.manifest.profile_image_url}
										<ProfileImage
											src={app.data.manifest.profile_image_url}
											allowExternal
											className="size-4 shrink-0 rounded!"
										/>
									{:else}<Grid className="size-4 shrink-0" strokeWidth="1.5" />{/if}
									<span class="truncate"
										>{app.name}
										<span class="text-gray-400 dark:text-gray-600">{app.slug}</span></span
									>
								</div>
								{#if app.is_active}
									<span class="text-gray-400 dark:text-gray-500"
										>{app.connection_status === 'connected'
											? $i18n.t('Connected')
											: app.connection_status === 'connecting'
												? $i18n.t('Connecting')
												: $i18n.t('Disconnected')}</span
									>
								{/if}
								<div class="flex shrink-0 items-center gap-1">
									<Tooltip content={$i18n.t('Configure')}
										><button
											type="button"
											aria-label={`${$i18n.t('Configure')} ${app.name}`}
											class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
											on:click={() => configure(app)}><Cog6 /></button
										></Tooltip
									>
									<Tooltip
										content={app.is_active
											? $i18n.t('Enabled')
											: app.configured
												? $i18n.t('Disabled')
												: $i18n.t('Uninstalled')}
									>
										{#key `${app.is_active}-${show}-${busy}`}<Switch
												state={app.is_active}
												disabled={busy === app.id}
												ariaLabel={`${$i18n.t('Enable')} ${app.name}`}
												on:change={() => toggle(app)}
											/>{/key}
									</Tooltip>
								</div>
							</div>
						{:else}<p class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t('No apps connected.')}
							</p>{/each}
					</div>{/if}
				<p class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
					{$i18n.t('Connect external apps to Open WebUI.')}
				</p>
			</div>
		</AdminSettingSection>
	</div>
</div>
