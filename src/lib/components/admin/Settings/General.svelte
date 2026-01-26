<script lang="ts">
	import { getVersionUpdates, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		updateAdminConfig,
		updateLdapConfig,
		updateLdapServer
	} from '$lib/apis/auths';
	import { getGroups } from '$lib/apis/groups';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_VERSION } from '$lib/constants';
	import {
		config,
		showChangelog,
		versionUpdatesCache,
		adminConfigCache,
		webhookUrlCache,
		groupsCache,
		ldapServerCache,
		ldapConfigCache
	} from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	let adminConfig = null;
	let webhookUrl = '';
	let groups = [];

	// LDAP
	let ENABLE_LDAP = false;
	let LDAP_SERVER = {
		label: '',
		host: '',
		port: '',
		attribute_for_mail: 'mail',
		attribute_for_username: 'uid',
		app_dn: '',
		app_dn_password: '',
		search_base: '',
		search_filters: '',
		use_tls: false,
		certificate_path: '',
		ciphers: ''
	};

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		// Use cached version if available
		if ($versionUpdatesCache) {
			version = $versionUpdatesCache;
			updateAvailable = compareVersion(version.latest, version.current);
			return;
		}
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.info(version);
		// Cache the result
		versionUpdatesCache.set(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.info(updateAvailable);
	};

	const updateLdapServerHandler = async () => {
		if (!ENABLE_LDAP) return;
		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('LDAP server updated'));
		}
	};

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		webhookUrlCache.set(webhookUrl);
		const res = await updateAdminConfig(localStorage.token, adminConfig);
		if (res) {
			adminConfigCache.set(adminConfig);
		}
		await updateLdapConfig(localStorage.token, ENABLE_LDAP);
		ldapConfigCache.set({ ENABLE_LDAP });
		await updateLdapServerHandler();
		if (LDAP_SERVER) {
			ldapServerCache.set(LDAP_SERVER);
		}

		if (res) {
			saveHandler();
		} else {
			toast.error($i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}

		await Promise.all([
			(async () => {
				if ($adminConfigCache) {
					adminConfig = JSON.parse(JSON.stringify($adminConfigCache));
				} else {
					adminConfig = await getAdminConfig(localStorage.token);
					adminConfigCache.set(adminConfig);
				}
			})(),

			(async () => {
				if ($webhookUrlCache !== null) {
					webhookUrl = $webhookUrlCache;
				} else {
					webhookUrl = await getWebhookUrl(localStorage.token);
					webhookUrlCache.set(webhookUrl);
				}
			})(),
			(async () => {
				if ($ldapServerCache) {
					LDAP_SERVER = JSON.parse(JSON.stringify($ldapServerCache));
				} else {
					LDAP_SERVER = await getLdapServer(localStorage.token);
					ldapServerCache.set(LDAP_SERVER);
				}
			})(),
			(async () => {
				if ($groupsCache) {
					groups = $groupsCache;
				} else {
					groups = await getGroups(localStorage.token);
					groupsCache.set(groups);
				}
			})()
		]);

		if ($ldapConfigCache !== null) {
			ENABLE_LDAP = $ldapConfigCache.ENABLE_LDAP;
		} else {
			const ldapConfig = await getLdapConfig(localStorage.token);
			ldapConfigCache.set(ldapConfig);
			ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class="space-y-4 overflow-y-auto scrollbar-hidden h-full">
		{#if adminConfig !== null}
			<div class="max-w-5xl mx-auto">
				<div class="mb-3.5">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

					<!-- 苹果风格的版本和关于区域 -->
					<div class="bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-850 dark:to-gray-900/50 rounded-2xl p-6 border border-gray-100/80 dark:border-gray-800/50 shadow-sm mb-6">
						<!-- 顶部：版本信息 -->
						<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-6">
							<div class="flex items-center gap-4">
								<div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-7 h-7 text-white">
										<path d="M11.7 2.805a.75.75 0 01.6 0A60.65 60.65 0 0122.83 8.72a.75.75 0 01-.231 1.337 49.949 49.949 0 00-9.902 3.912l-.003.002-.34.18a.75.75 0 01-.707 0A50.009 50.009 0 007.5 12.174v-.224c0-.131.067-.248.172-.311a54.614 54.614 0 014.653-2.52.75.75 0 00-.65-1.352 56.129 56.129 0 00-4.78 2.589 1.858 1.858 0 00-.859 1.228 49.803 49.803 0 00-4.634-1.527.75.75 0 01-.231-1.337A60.653 60.653 0 0111.7 2.805z" />
										<path d="M13.06 15.473a48.45 48.45 0 017.666-3.282c.134 1.414.22 2.843.255 4.285a.75.75 0 01-.46.71 47.878 47.878 0 00-8.105 4.342.75.75 0 01-.832 0 47.877 47.877 0 00-8.104-4.342.75.75 0 01-.461-.71c.035-1.442.121-2.87.255-4.286A48.4 48.4 0 016 13.18v1.27a1.5 1.5 0 00-.14 2.508c-.09.38-.222.753-.397 1.11.452.213.901.434 1.346.661a6.729 6.729 0 00.551-1.608 1.5 1.5 0 00.14-2.67v-.645a48.549 48.549 0 013.44 1.668 2.25 2.25 0 002.12 0z" />
										<path d="M4.462 19.462c.42-.419.753-.89 1-1.394.453.213.902.434 1.347.661a6.743 6.743 0 01-1.286 1.794.75.75 0 11-1.06-1.06z" />
									</svg>
								</div>
								<div>
									<div class="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
										Open WebUI
									</div>
									<div class="flex items-center gap-2 mt-1">
										<span class="text-lg font-semibold text-gray-600 dark:text-gray-300">v{WEBUI_VERSION}</span>
										{#if updateAvailable === false}
											<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
												{$i18n.t('Latest')}
											</span>
										{:else if updateAvailable}
											<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
												{$i18n.t('Update Available')}
											</span>
										{/if}
									</div>
								</div>
							</div>

							<div class="flex flex-col sm:flex-row gap-2">
								{#if $config?.features?.enable_version_update_check}
									<button
										class="px-5 py-2.5 text-sm font-medium bg-gray-900 text-white dark:bg-white dark:text-gray-900 rounded-xl transition-all hover:opacity-90 hover:shadow-lg active:scale-[0.98] flex items-center justify-center gap-2"
										on:click={() => checkForVersionUpdates()}
										type="button"
									>
										{#if updateAvailable === null}
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
												<path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" />
											</svg>
											{$i18n.t('Check for updates')}
										{:else if updateAvailable}
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
												<path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
												<path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
											</svg>
											{$i18n.t('Update to v{{version}}', { version: version.latest })}
										{:else}
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
												<path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" />
											</svg>
											{$i18n.t('Up to date')}
										{/if}
									</button>
								{/if}
								<button
									class="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl transition-all hover:bg-gray-50 dark:hover:bg-gray-750 hover:shadow active:scale-[0.98] flex items-center justify-center gap-2"
									on:click={() => showChangelog.set(true)}
									type="button"
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
										<path fill-rule="evenodd" d="M10 2c-1.716 0-3.408.106-5.07.31C3.806 2.45 3 3.414 3 4.517V17.25a.75.75 0 001.075.676L10 15.082l5.925 2.844A.75.75 0 0017 17.25V4.517c0-1.103-.806-2.068-1.93-2.207A41.403 41.403 0 0010 2z" clip-rule="evenodd" />
									</svg>
									{$i18n.t("See what's new")}
								</button>
							</div>
						</div>

						<!-- 分隔线 -->
						<div class="border-t border-gray-200/60 dark:border-gray-700/40 my-5"></div>

						<!-- 底部：快速链接和关于 -->
						<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
							<a
								href="https://docs.openwebui.cn/"
								target="_blank"
								class="group flex flex-col items-center gap-2 p-4 rounded-xl bg-white/60 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-700/50 hover:border-blue-200 dark:hover:border-blue-800/50 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all"
							>
								<div class="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-blue-600 dark:text-blue-400">
										<path d="M11.25 4.533A9.707 9.707 0 006 3a9.735 9.735 0 00-3.25.555.75.75 0 00-.5.707v14.25a.75.75 0 001 .707A8.237 8.237 0 016 18.75c1.995 0 3.823.707 5.25 1.886V4.533zM12.75 20.636A8.214 8.214 0 0118 18.75c.966 0 1.89.166 2.75.47a.75.75 0 001-.708V4.262a.75.75 0 00-.5-.707A9.735 9.735 0 0018 3a9.707 9.707 0 00-5.25 1.533v16.103z" />
									</svg>
								</div>
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Documentation')}</span>
							</a>

							<a
								href="https://github.com/ztx888/open-webui"
								target="_blank"
								class="group flex flex-col items-center gap-2 p-4 rounded-xl bg-white/60 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100/50 dark:hover:bg-gray-700/30 transition-all"
							>
								<div class="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center group-hover:scale-110 transition-transform">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-700 dark:text-gray-300">
										<path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd" />
									</svg>
								</div>
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('GitHub')}</span>
							</a>

							<a
								href="https://discord.gg/5rJgQTnV4s"
								target="_blank"
								class="group flex flex-col items-center gap-2 p-4 rounded-xl bg-white/60 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-700/50 hover:border-indigo-200 dark:hover:border-indigo-800/50 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/10 transition-all"
							>
								<div class="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-indigo-600 dark:text-indigo-400">
										<path d="M20.317 4.492c-1.53-.69-3.17-1.2-4.885-1.49a.075.075 0 0 0-.079.036c-.21.369-.444.85-.608 1.23a18.566 18.566 0 0 0-5.487 0 12.36 12.36 0 0 0-.617-1.23A.077.077 0 0 0 8.562 3c-1.714.29-3.354.8-4.885 1.491a.07.07 0 0 0-.032.027C.533 9.093-.32 13.555.099 17.961a.08.08 0 0 0 .031.055 20.03 20.03 0 0 0 5.993 2.98.078.078 0 0 0 .084-.026 13.83 13.83 0 0 0 1.226-1.963.074.074 0 0 0-.041-.104 13.201 13.201 0 0 1-1.872-.878.075.075 0 0 1-.008-.125c.126-.093.252-.19.372-.287a.075.075 0 0 1 .078-.01c3.927 1.764 8.18 1.764 12.061 0a.075.075 0 0 1 .079.009c.12.098.245.195.372.288a.075.075 0 0 1-.006.125c-.598.344-1.22.635-1.873.877a.075.075 0 0 0-.041.105c.36.687.772 1.341 1.225 1.962a.077.077 0 0 0 .084.028 19.963 19.963 0 0 0 6.002-2.981.076.076 0 0 0 .032-.054c.5-5.094-.838-9.52-3.549-13.442a.06.06 0 0 0-.031-.028zM8.02 15.278c-1.182 0-2.157-1.069-2.157-2.38 0-1.312.956-2.38 2.157-2.38 1.21 0 2.176 1.077 2.157 2.38 0 1.312-.956 2.38-2.157 2.38zm7.975 0c-1.183 0-2.157-1.069-2.157-2.38 0-1.312.955-2.38 2.157-2.38 1.21 0 2.176 1.077 2.157 2.38 0 1.312-.946 2.38-2.157 2.38z"/>
									</svg>
								</div>
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Community')}</span>
							</a>

							<a
								href="https://github.com/ztx888/open-webui/issues"
								target="_blank"
								class="group flex flex-col items-center gap-2 p-4 rounded-xl bg-white/60 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-700/50 hover:border-orange-200 dark:hover:border-orange-800/50 hover:bg-orange-50/50 dark:hover:bg-orange-900/10 transition-all"
							>
								<div class="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-orange-600 dark:text-orange-400">
										<path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm11.378-3.917c-.89-.777-2.366-.777-3.255 0a.75.75 0 01-.988-1.129c1.454-1.272 3.776-1.272 5.23 0 1.513 1.324 1.513 3.518 0 4.842a3.75 3.75 0 01-.837.552c-.676.328-1.028.774-1.028 1.152v.75a.75.75 0 01-1.5 0v-.75c0-1.279 1.06-2.107 1.875-2.502.182-.088.351-.199.503-.331.83-.727.83-1.857 0-2.584zM12 18a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
									</svg>
								</div>
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Feedback')}</span>
							</a>
						</div>
					</div>
				</div>

				<!-- Identity & Security -->
				<div class="mb-4">
					<div class="flex flex-col gap-4">
						<div
							class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
						>
							<div class="flex items-center gap-2.5 mb-5">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="currentColor"
									class="w-5 h-5 text-gray-500 dark:text-gray-400"
								>
									<path
										fill-rule="evenodd"
										d="M12 1.5a5.25 5.25 0 00-5.25 5.25v3a3 3 0 00-3 3v6.75a3 3 0 003 3h10.5a3 3 0 003-3v-6.75a3 3 0 00-3-3v-3c0-2.9-2.35-5.25-5.25-5.25zm3.75 8.25v-3a3.75 3.75 0 10-7.5 0v3h7.5z"
										clip-rule="evenodd"
									/>
								</svg>
								<div class="text-base font-medium text-gray-800 dark:text-gray-100">
									{$i18n.t('Identity & Security')}
								</div>
							</div>

							<div class="flex flex-col gap-5">
								<!-- 用户注册设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('User Registration')}
									</div>
									<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
										<div
											class="bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
										>
											<div class="flex items-center justify-between">
												<div class="text-sm font-medium">{$i18n.t('Default User Role')}</div>
												<select
													class="dark:bg-gray-800 w-fit pr-8 rounded-lg px-2 py-1 text-sm bg-gray-50 outline-none focus:ring-0 border border-gray-200 dark:border-gray-700 text-right cursor-pointer"
													bind:value={adminConfig.DEFAULT_USER_ROLE}
													placeholder={$i18n.t('Select a role')}
												>
													<option value="pending">{$i18n.t('pending')}</option>
													<option value="user">{$i18n.t('user')}</option>
													<option value="admin">{$i18n.t('admin')}</option>
												</select>
											</div>
										</div>
										<div
											class="bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
										>
											<div class="flex items-center justify-between">
												<div class="text-sm font-medium">{$i18n.t('Default Group')}</div>
												<select
													class="dark:bg-gray-800 w-fit pr-8 rounded-lg px-2 py-1 text-sm bg-gray-50 outline-none focus:ring-0 border border-gray-200 dark:border-gray-700 text-right cursor-pointer"
													bind:value={adminConfig.DEFAULT_GROUP_ID}
													placeholder={$i18n.t('Select a group')}
												>
													<option value={''}>None</option>
													{#each groups as group}
														<option value={group.id}>{group.name}</option>
													{/each}
												</select>
											</div>
										</div>
										<div
											class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-sm font-medium">{$i18n.t('Enable New Sign Ups')}</div>
											<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
										</div>
										<div
											class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-sm font-medium">
												{$i18n.t('Show Admin Details in Account Pending Overlay')}
											</div>
											<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
										</div>
									</div>

									{#if adminConfig.SHOW_ADMIN_DETAILS}
										<div
											class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Admin Contact Email')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
												type="email"
												placeholder={$i18n.t('Leave empty to use first admin user')}
												bind:value={adminConfig.ADMIN_EMAIL}
											/>
										</div>
									{/if}

									<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
										<div
											class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Pending User Overlay Title')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
												placeholder={$i18n.t(
													'Enter a title for the pending user info overlay. Leave empty for default.'
												)}
												bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
											/>
										</div>
										<div
											class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Pending User Overlay Content')}
											</div>
											<Textarea
												placeholder={$i18n.t(
													'Enter content for the pending user info overlay. Leave empty for default.'
												)}
												bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
											/>
										</div>
									</div>
								</div>

								<!-- API 密钥设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('API Keys')}
									</div>
									<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
										<div
											class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-sm font-medium">{$i18n.t('Enable API Keys')}</div>
											<Switch bind:state={adminConfig.ENABLE_API_KEYS} />
										</div>
										{#if adminConfig?.ENABLE_API_KEYS}
											<div
												class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
											>
												<div class="text-sm font-medium">
													{$i18n.t('API Key Endpoint Restrictions')}
												</div>
												<Switch bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS} />
											</div>
										{/if}
									</div>

									{#if adminConfig?.ENABLE_API_KEYS && adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
										<div
											class="ml-0 md:ml-4 bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
										>
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Allowed Endpoints')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
												type="text"
												placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
												bind:value={adminConfig.API_KEYS_ALLOWED_ENDPOINTS}
											/>
											<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
												<a
													href="https://docs.openwebui.cn/getting-started/api-endpoints"
													target="_blank"
													class="text-gray-500 dark:text-gray-400 font-medium underline hover:text-blue-500"
												>
													{$i18n.t(
														'To learn more about available endpoints, visit our documentation.'
													)}
												</a>
											</div>
										</div>
									{/if}
								</div>

								<!-- JWT 设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('Session Security')}
									</div>
									<div
										class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-xs font-medium text-gray-500 mb-1.5">
											{$i18n.t('JWT Expiration')}
										</div>
										<input
											class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
											type="text"
											placeholder={`e.g.) "30m","1h", "10d". `}
											bind:value={adminConfig.JWT_EXPIRES_IN}
										/>
										<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
											{$i18n.t('Valid time units:')}
											<span class="text-gray-500 dark:text-gray-400 font-medium"
												>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
											>
										</div>

										{#if adminConfig.JWT_EXPIRES_IN === '-1'}
											<div
												class="mt-3 bg-yellow-500/10 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3 text-xs flex items-center gap-2"
											>
												<span class="font-medium">{$i18n.t('Warning')}:</span>
												<span>
													<a
														href="https://docs.openwebui.cn/getting-started/env-configuration#jwt_expires_in"
														target="_blank"
														class="underline hover:text-yellow-800 dark:hover:text-yellow-100"
													>
														{$i18n.t('No expiration can pose security risks.')}
													</a>
												</span>
											</div>
										{/if}
									</div>
								</div>

								<!-- LDAP 设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('LDAP Authentication')}
									</div>
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">{$i18n.t('LDAP')}</div>
										<Switch bind:state={ENABLE_LDAP} />
									</div>

									{#if ENABLE_LDAP}
										<div class="pl-0 md:pl-2 space-y-4 pt-2">
											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('Server Config')}
												</div>
												<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
													<div class="w-full">
														<input
															class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
															required
															placeholder={$i18n.t('Label (e.g. My LDAP)')}
															bind:value={LDAP_SERVER.label}
														/>
													</div>
													<div class="w-full">
														<input
															class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
															required
															placeholder={$i18n.t('Host (e.g. ldap.example.com)')}
															bind:value={LDAP_SERVER.host}
														/>
													</div>
													<div class="w-full">
														<Tooltip
															content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
															placement="top-start"
															className="w-full"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																type="number"
																placeholder={$i18n.t('Port')}
																bind:value={LDAP_SERVER.port}
															/>
														</Tooltip>
													</div>
												</div>
											</div>

											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('Authentication')}
												</div>
												<div class="grid grid-cols-1 gap-3">
													<div class="w-full">
														<Tooltip
															content={$i18n.t(
																'The Application Account DN you bind with for search'
															)}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t('Application DN')}
																bind:value={LDAP_SERVER.app_dn}
															/>
														</Tooltip>
													</div>
													<div class="w-full">
														<SensitiveInput
															placeholder={$i18n.t('Application DN Password')}
															bind:value={LDAP_SERVER.app_dn_password}
														/>
													</div>
												</div>
											</div>

											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('User Mapping')}
												</div>
												<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
													<div class="w-full">
														<Tooltip
															content={$i18n.t(
																'The LDAP attribute that maps to the mail that users use to sign in.'
															)}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t('Mail Attribute (e.g. mail)')}
																bind:value={LDAP_SERVER.attribute_for_mail}
															/>
														</Tooltip>
													</div>
													<div class="w-full">
														<Tooltip
															content={$i18n.t(
																'The LDAP attribute that maps to the username that users use to sign in.'
															)}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t('Username Attribute (e.g. uid)')}
																bind:value={LDAP_SERVER.attribute_for_username}
															/>
														</Tooltip>
													</div>
												</div>
											</div>

											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('Search')}
												</div>
												<div class="space-y-3">
													<div class="w-full">
														<Tooltip
															content={$i18n.t('The base to search for users')}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t(
																	'Search Base (e.g. ou=users,dc=example,dc=com)'
																)}
																bind:value={LDAP_SERVER.search_base}
															/>
														</Tooltip>
													</div>
													<div class="w-full">
														<input
															class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
															placeholder={$i18n.t(
																'Search Filters (e.g. (&(objectClass=inetOrgPerson)(uid=%s)))'
															)}
															bind:value={LDAP_SERVER.search_filters}
														/>
													</div>
													<div class="text-xs text-gray-400 dark:text-gray-500 text-right">
														<a
															class="hover:text-gray-700 dark:hover:text-gray-300 transition underline"
															href="https://ldap.com/ldap-filters/"
															target="_blank"
														>
															{$i18n.t('Click here for filter guides.')}
														</a>
													</div>
												</div>
											</div>

											<!-- TLS Settings -->
											<div class="pt-2">
												<div class="flex justify-between items-center mb-3">
													<div class="text-sm font-medium">{$i18n.t('TLS Encryption')}</div>
													<Switch bind:state={LDAP_SERVER.use_tls} />
												</div>

												{#if LDAP_SERVER.use_tls}
													<div class="pl-2 space-y-3">
														<div class="flex justify-between items-center">
															<div class="text-xs font-medium">
																{$i18n.t('Validate certificate')}
															</div>
															<Switch bind:state={LDAP_SERVER.validate_cert} />
														</div>

														<div class="w-full">
															<div class="text-xs font-medium text-gray-500 mb-1.5">
																{$i18n.t('Certificate Path')}
															</div>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																placeholder={$i18n.t('Enter certificate path')}
																bind:value={LDAP_SERVER.certificate_path}
															/>
														</div>

														<div class="w-full">
															<div class="text-xs font-medium text-gray-500 mb-1.5">
																{$i18n.t('Ciphers')}
															</div>
															<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
																<input
																	class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																	placeholder={$i18n.t('Example: ALL')}
																	bind:value={LDAP_SERVER.ciphers}
																/>
															</Tooltip>
														</div>
													</div>
												{/if}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Application Features -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2.5 mb-5">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="currentColor"
								class="w-5 h-5 text-gray-500 dark:text-gray-400"
							>
								<path
									fill-rule="evenodd"
									d="M3 6a3 3 0 013-3h2.25a3 3 0 013 3v2.25a3 3 0 01-3 3H6a3 3 0 01-3-3V6zm9.75 0a3 3 0 013-3H18a3 3 0 013 3v2.25a3 3 0 01-3 3h-2.25a3 3 0 01-3-3V6zM3 15.75a3 3 0 013-3h2.25a3 3 0 013 3V18a3 3 0 01-3 3H6a3 3 0 01-3-3v-2.25zm9.75 0a3 3 0 013-3H18a3 3 0 013 3V18a3 3 0 01-3 3h-2.25a3 3 0 01-3-3v-2.25z"
									clip-rule="evenodd"
								/>
							</svg>
							<div class="text-base font-medium text-gray-800 dark:text-gray-100">
								{$i18n.t('App Features')}
							</div>
						</div>

						<div class="flex flex-col gap-5">
							<!-- 社区与互动 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Community & Interaction')}
								</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">{$i18n.t('Enable Community Sharing')}</div>
										<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
									</div>
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">{$i18n.t('Enable Message Rating')}</div>
										<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
									</div>
								</div>
							</div>

							<!-- 内容管理 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Content Management')}
								</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">{$i18n.t('Enable Folders')}</div>
										<Switch bind:state={adminConfig.ENABLE_FOLDERS} />
									</div>
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">
											{$i18n.t('Enable Notes')}
											<span
												class="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded"
												>{$i18n.t('Beta')}</span
											>
										</div>
										<Switch bind:state={adminConfig.ENABLE_NOTES} />
									</div>
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">
											{$i18n.t('Enable Channels')}
											<span
												class="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded"
												>{$i18n.t('Beta')}</span
											>
										</div>
										<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
									</div>
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">
											{$i18n.t('Enable Memories')}
											<span
												class="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded"
												>{$i18n.t('Beta')}</span
											>
										</div>
										<Switch bind:state={adminConfig.ENABLE_MEMORIES} />
									</div>
								</div>

								{#if adminConfig.ENABLE_FOLDERS}
									<div
										class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-xs font-medium text-gray-500 mb-1.5">
											{$i18n.t('Folder Max File Count')}
										</div>
										<input
											class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
											type="number"
											min="0"
											placeholder={$i18n.t('Leave empty for unlimited')}
											bind:value={adminConfig.FOLDER_MAX_FILE_COUNT}
										/>
										<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
											{$i18n.t('Maximum number of files allowed per folder.')}
										</div>
									</div>
								{/if}
							</div>

							<!-- 用户功能 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('User Features')}
								</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">{$i18n.t('Enable User Webhooks')}</div>
										<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
									</div>
									<div
										class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800"
									>
										<div class="text-sm font-medium">{$i18n.t('Enable User Status')}</div>
										<Switch bind:state={adminConfig.ENABLE_USER_STATUS} />
									</div>
								</div>
							</div>

							<!-- 其他设置 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Other Settings')}
								</div>
								<div
									class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
								>
									<div class="text-xs font-medium text-gray-500 mb-1.5">
										{$i18n.t('Response Watermark')}
									</div>
									<input
										class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
										placeholder={$i18n.t(
											'Enter a watermark for the response. Leave empty for none.'
										)}
										bind:value={adminConfig.RESPONSE_WATERMARK}
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- System Settings -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2.5 mb-5">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="currentColor"
								class="w-5 h-5 text-gray-500 dark:text-gray-400"
							>
								<path
									fill-rule="evenodd"
									d="M2.25 6a3 3 0 013-3h13.5a3 3 0 013 3v12a3 3 0 01-3 3H5.25a3 3 0 01-3-3V6zm3.97.97a.75.75 0 011.06 0l2.25 2.25a.75.75 0 010 1.06l-2.25 2.25a.75.75 0 01-1.06-1.06l1.72-1.72-1.72-1.72a.75.75 0 010-1.06zm4.28 4.28a.75.75 0 000 1.5h3a.75.75 0 000-1.5h-3z"
									clip-rule="evenodd"
								/>
							</svg>
							<div class="text-base font-medium text-gray-800 dark:text-gray-100">
								{$i18n.t('System Connections')}
							</div>
						</div>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div
								class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
							>
								<div class="flex items-center gap-2 mb-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="w-5 h-5 opacity-70 text-gray-600 dark:text-gray-400"
									>
										<path
											fill-rule="evenodd"
											d="M19.902 4.098a3.75 3.75 0 00-5.304 0l-4.5 4.5a3.75 3.75 0 001.035 6.037.75.75 0 01-.646 1.353 5.25 5.25 0 01-1.449-8.45l4.5-4.5a5.25 5.25 0 117.424 7.424l-1.757 1.757a.75.75 0 11-1.06-1.06l1.757-1.757a3.75 3.75 0 000-5.304zm-7.389 4.267a.75.75 0 011-.353 5.25 5.25 0 011.449 8.45l-4.5 4.5a5.25 5.25 0 11-7.424-7.424l1.757-1.757a.75.75 0 111.06 1.06l-1.757 1.757a3.75 3.75 0 105.304 5.304l4.5-4.5a3.75 3.75 0 00-1.035-6.037.75.75 0 01-.354-1z"
											clip-rule="evenodd"
										/>
									</svg>
									<div class="text-xs font-medium text-gray-500">{$i18n.t('WebUI URL')}</div>
								</div>
								<div>
									<input
										class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
										type="text"
										placeholder={`e.g.) "http://localhost:3000"`}
										bind:value={adminConfig.WEBUI_URL}
									/>
									<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
										{$i18n.t(
											'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
										)}
									</div>
								</div>
							</div>

							<div
								class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
							>
								<div class="flex items-center gap-2 mb-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="w-5 h-5 opacity-70 text-gray-600 dark:text-gray-400"
									>
										<path
											fill-rule="evenodd"
											d="M5.337 21.718a6.707 6.707 0 01-.533-.074.75.75 0 01-.44-1.223 3.73 3.73 0 00.814-1.686c.023-.115-.022-.317-.254-.543C3.274 16.587 2.25 14.41 2.25 12c0-5.03 4.428-9 9.75-9s9.75 3.97 9.75 9c0 5.03-4.428 9-9.75 9-.833 0-1.643-.097-2.417-.279a6.721 6.721 0 01-4.246.997z"
											clip-rule="evenodd"
										/>
									</svg>
									<div class="text-xs font-medium text-gray-500">{$i18n.t('Webhook URL')}</div>
								</div>
								<div>
									<input
										class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
										type="text"
										placeholder={`https://example.com/webhook`}
										bind:value={webhookUrl}
									/>
									<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
										{$i18n.t('Configure webhook endpoint for system notifications')}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
