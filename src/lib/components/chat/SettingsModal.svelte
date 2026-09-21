<script lang="ts">
	import english from '$lib/i18n/locales/en-US/translation.json';
	import {
		buildSettingsSearchIndex,
		searchSettingsTabs,
		type SettingsTab
	} from '$lib/utils/settings-search';
	import { browser } from '$app/environment';
	import { getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { config, models, settings, user } from '$lib/stores';
	import type { SettingsModalRequest } from '$lib/stores';
	import { getUserSettings, updateUserSettings } from '$lib/apis/users';
	import { getBackendConfig, getModels as _getModels } from '$lib/apis';

	import Modal from '../common/Modal.svelte';
	import Account from './Settings/Account.svelte';
	import About from './Settings/About.svelte';
	import General from './Settings/General.svelte';
	import Interface from './Settings/Interface.svelte';
	import Notifications from './Settings/Notifications.svelte';
	import Shortcuts from './Settings/Shortcuts.svelte';
	import Audio from './Settings/Audio.svelte';
	import DataControls from './Settings/DataControls.svelte';
	import Usage from './Settings/Usage.svelte';
	import ArchivedChats from './Settings/ArchivedChats.svelte';
	import Personalization from './Settings/Personalization.svelte';
	import Search from '../icons/Search.svelte';
	import Connections from './Settings/Connections.svelte';
	import Integrations from './Settings/Integrations.svelte';
	import DatabaseSettings from '../icons/DatabaseSettings.svelte';
	import SettingsAlt from '../icons/SettingsAlt.svelte';
	import Link from '../icons/Link.svelte';
	import UserCircle from '../icons/UserCircle.svelte';
	import SoundHigh from '../icons/SoundHigh.svelte';
	import InfoCircle from '../icons/InfoCircle.svelte';
	import WrenchAlt from '../icons/WrenchAlt.svelte';
	import Face from '../icons/Face.svelte';
	import AppNotification from '../icons/AppNotification.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import ArchiveBox from '../icons/ArchiveBox.svelte';
	import ChevronLeft from '../icons/ChevronLeft.svelte';
	import Keyboard from '../icons/Keyboard.svelte';
	import UsageIcon from '../icons/UsageIcon.svelte';
	import AdminTabIcon from '$lib/components/admin/Settings/AdminTabIcon.svelte';
	import AdminGeneral from '$lib/components/admin/Settings/General.svelte';
	import AdminAuthentication from '$lib/components/admin/Settings/Authentication.svelte';
	import AdminConnections from '$lib/components/admin/Settings/Connections.svelte';
	import AdminModels from '$lib/components/admin/Settings/Models.svelte';
	import AdminSubagents from '$lib/components/admin/Settings/Subagents.svelte';
	import AdminEvaluations from '$lib/components/admin/Settings/Evaluations.svelte';
	import AdminAnalytics from '$lib/components/admin/Analytics.svelte';
	import AdminIntegrations from '$lib/components/admin/Settings/Integrations.svelte';
	import AdminDocuments from '$lib/components/admin/Settings/Documents.svelte';
	import AdminWebSearch from '$lib/components/admin/Settings/WebSearch.svelte';
	import AdminCodeExecution from '$lib/components/admin/Settings/CodeExecution.svelte';
	import AdminInterface from '$lib/components/admin/Settings/Interface.svelte';
	import AdminAudio from '$lib/components/admin/Settings/Audio.svelte';
	import AdminImages from '$lib/components/admin/Settings/Images.svelte';
	import AdminPipelines from '$lib/components/admin/Settings/Pipelines.svelte';
	import AdminDatabase from '$lib/components/admin/Settings/Database.svelte';

	const i18n: Writable<any> = getContext('i18n');

	export let show: boolean | string | SettingsModalRequest = false;
	let modalShow = false;
	let lastShow: boolean | string | SettingsModalRequest = false;
	let tabState: Record<string, unknown> | null = null;
	let personalUiSettings: Record<string, any> = {};

	const mergeUiSettings = (defaults: Record<string, any>, userSettings: Record<string, any>) => {
		const merged = { ...defaults };
		for (const [key, value] of Object.entries(userSettings)) {
			const defaultValue = merged[key];
			merged[key] =
				defaultValue &&
				value &&
				typeof defaultValue === 'object' &&
				typeof value === 'object' &&
				!Array.isArray(defaultValue) &&
				!Array.isArray(value)
					? mergeUiSettings(defaultValue, value)
					: value;
		}
		return merged;
	};

	const loadPersonalUiSettings = async () => {
		const userSettings = await getUserSettings(localStorage.token, true).catch((error) => {
			console.error(error);
			return null;
		});
		personalUiSettings =
			userSettings?.ui && typeof userSettings.ui === 'object' && !Array.isArray(userSettings.ui)
				? userSettings.ui
				: {};
	};

	$: if (show !== lastShow) {
		lastShow = show;
		search = '';
		if (show && typeof show === 'object') {
			selectedTab = show.tab;
			tabState = show.state ?? null;
			show = true;
			lastShow = true;
			modalShow = true;
			loadPersonalUiSettings();
		} else if (typeof show === 'string') {
			selectedTab = show;
			show = true;
			lastShow = true;
			modalShow = true;
			loadPersonalUiSettings();
		} else {
			modalShow = show;
			if (show) {
				loadPersonalUiSettings();
			}
			if (!show) {
				selectedTab = 'general';
				tabState = null;
			}
		}
	}

	$: if (!modalShow && show !== false) {
		show = false;
		search = '';
		lastShow = false;
		selectedTab = 'general';
		tabState = null;
	}

	const isAdminTab = (tabId: string) => tabId.startsWith('admin:');
	const adminTabSegment = (tabId: string) => tabId.replace('admin:', '');
	const adminTabPanelId = (tabId: string) => `tab-${tabId.replace(':', '-')}`;
	let personalSettingGroups: Record<string, string> = {};
	let adminSettingGroups: Record<string, string> = {};

	$: personalSettingGroups = {
		general: $i18n.t('Basics'),
		interface: $i18n.t('Basics'),
		notifications: $i18n.t('Basics'),
		shortcuts: $i18n.t('Basics'),
		connections: $i18n.t('Services'),
		tools: $i18n.t('Services'),
		personalization: $i18n.t('Preferences'),
		audio: $i18n.t('Preferences'),
		data_controls: $i18n.t('Data'),
		usage: $i18n.t('Data'),
		archived_chats: $i18n.t('Data'),
		account: $i18n.t('Profile'),
		about: $i18n.t('Profile')
	};
	$: adminSettingGroups = {
		'admin:general': $i18n.t('System'),
		'admin:authentication': $i18n.t('System'),
		'admin:connections': $i18n.t('AI'),
		'admin:models': $i18n.t('AI'),
		'admin:subagents': $i18n.t('AI'),
		'admin:evaluations': $i18n.t('Quality'),
		'admin:analytics': $i18n.t('Quality'),
		'admin:integrations': $i18n.t('Tools'),
		'admin:documents': $i18n.t('Tools'),
		'admin:web': $i18n.t('Tools'),
		'admin:code-execution': $i18n.t('Tools'),
		'admin:pipelines': $i18n.t('Tools'),
		'admin:interface': $i18n.t('Experience'),
		'admin:audio': $i18n.t('Experience'),
		'admin:images': $i18n.t('Experience'),
		'admin:db': $i18n.t('Data')
	};
	const settingGroupTitle = (tabId: string) =>
		(isAdminTab(tabId) ? adminSettingGroups[tabId] : personalSettingGroups[tabId]) ??
		$i18n.t('General');
	const shouldShowSettingGroup = (tabIds: string[], index: number) =>
		index === 0 || settingGroupTitle(tabIds[index]) !== settingGroupTitle(tabIds[index - 1]);
	const settingGroupHeadingClass = (first: boolean) =>
		`hidden md:block shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 ${
			first ? 'mt-0.5' : 'mt-2'
		} mb-0.5`;

	let allSettings: SettingsTab[];
	$: allSettings = [
		{
			id: 'general',
			titleKey: 'settings.personal.general.title',
			title: $i18n.t('settings.personal.general.title'),
			searchPrefixes: ['settings.personal.general.']
		},
		{
			id: 'interface',
			titleKey: 'settings.personal.interface.title',
			title: $i18n.t('settings.personal.interface.title'),
			searchPrefixes: ['settings.personal.interface.']
		},
		{
			id: 'notifications',
			titleKey: 'settings.personal.notifications.title',
			title: $i18n.t('settings.personal.notifications.title'),
			searchPrefixes: ['settings.personal.notifications.']
		},
		{
			id: 'shortcuts',
			titleKey: 'settings.personal.shortcuts.title',
			title: $i18n.t('settings.personal.shortcuts.title'),
			searchPrefixes: ['settings.personal.shortcuts.']
		},
		{
			id: 'connections',
			titleKey: 'settings.personal.connections.title',
			title: $i18n.t('settings.personal.connections.title'),
			searchPrefixes: ['settings.personal.connections.']
		},
		{
			id: 'tools',
			titleKey: 'settings.personal.tools.title',
			title: $i18n.t('settings.personal.tools.title'),
			searchPrefixes: ['settings.personal.tools.']
		},
		{
			id: 'personalization',
			titleKey: 'settings.personal.personalization.title',
			title: $i18n.t('settings.personal.personalization.title'),
			searchPrefixes: ['settings.personal.personalization.']
		},
		{
			id: 'audio',
			titleKey: 'settings.personal.audio.title',
			title: $i18n.t('settings.personal.audio.title'),
			searchPrefixes: ['settings.personal.audio.']
		},
		{
			id: 'data_controls',
			titleKey: 'settings.personal.dataControls.title',
			title: $i18n.t('settings.personal.dataControls.title'),
			searchPrefixes: ['settings.personal.dataControls.']
		},
		{
			id: 'usage',
			titleKey: 'settings.personal.usage.title',
			title: $i18n.t('settings.personal.usage.title'),
			searchPrefixes: ['settings.personal.usage.']
		},
		{
			id: 'archived_chats',
			titleKey: 'settings.personal.archivedChats.title',
			title: $i18n.t('settings.personal.archivedChats.title'),
			searchPrefixes: ['settings.personal.archivedChats.']
		},
		{
			id: 'account',
			titleKey: 'settings.personal.account.title',
			title: $i18n.t('settings.personal.account.title'),
			searchPrefixes: ['settings.personal.account.']
		},
		{
			id: 'about',
			titleKey: 'settings.personal.about.title',
			title: $i18n.t('settings.personal.about.title'),
			searchPrefixes: ['settings.personal.about.']
		}
	];
	let adminSettings: SettingsTab[];
	$: adminSettings = [
		{
			id: 'admin:general',
			titleKey: 'settings.admin.general.title',
			title: $i18n.t('settings.admin.general.title'),
			searchPrefixes: ['settings.admin.general.', 'settings.personal.interface.']
		},
		{
			id: 'admin:authentication',
			titleKey: 'settings.admin.authentication.title',
			title: $i18n.t('settings.admin.authentication.title'),
			searchPrefixes: ['settings.admin.authentication.']
		},
		{
			id: 'admin:connections',
			titleKey: 'settings.admin.connections.title',
			title: $i18n.t('settings.admin.connections.title'),
			searchPrefixes: ['settings.admin.connections.']
		},
		{
			id: 'admin:models',
			titleKey: 'settings.admin.models.title',
			title: $i18n.t('settings.admin.models.title'),
			searchPrefixes: ['settings.admin.models.', 'settings.personal.general.parameters.']
		},
		{
			id: 'admin:subagents',
			titleKey: 'settings.admin.subagents.title',
			title: $i18n.t('settings.admin.subagents.title'),
			searchPrefixes: ['settings.admin.subagents.']
		},
		{
			id: 'admin:interface',
			titleKey: 'settings.admin.interface.title',
			title: $i18n.t('settings.admin.interface.title'),
			searchPrefixes: ['settings.admin.interface.', 'settings.personal.general.parameters.']
		},
		{
			id: 'admin:audio',
			titleKey: 'settings.admin.audio.title',
			title: $i18n.t('settings.admin.audio.title'),
			searchPrefixes: ['settings.admin.audio.']
		},
		{
			id: 'admin:images',
			titleKey: 'settings.admin.images.title',
			title: $i18n.t('settings.admin.images.title'),
			searchPrefixes: ['settings.admin.images.']
		},
		{
			id: 'admin:evaluations',
			titleKey: 'settings.admin.evaluations.title',
			title: $i18n.t('settings.admin.evaluations.title'),
			searchPrefixes: ['settings.admin.evaluations.']
		},
		{
			id: 'admin:analytics',
			titleKey: 'settings.admin.analytics.title',
			title: $i18n.t('settings.admin.analytics.title'),
			searchPrefixes: ['settings.admin.analytics.']
		},
		{
			id: 'admin:integrations',
			titleKey: 'settings.admin.integrations.title',
			title: $i18n.t('settings.admin.integrations.title'),
			searchPrefixes: ['settings.admin.integrations.']
		},
		{
			id: 'admin:documents',
			titleKey: 'settings.admin.documents.title',
			title: $i18n.t('settings.admin.documents.title'),
			searchPrefixes: ['settings.admin.documents.']
		},
		{
			id: 'admin:web',
			titleKey: 'settings.admin.web.title',
			title: $i18n.t('settings.admin.web.title'),
			searchPrefixes: ['settings.admin.web.']
		},
		{
			id: 'admin:code-execution',
			titleKey: 'settings.admin.codeExecution.title',
			title: $i18n.t('settings.admin.codeExecution.title'),
			searchPrefixes: ['settings.admin.codeExecution.']
		},
		{
			id: 'admin:pipelines',
			titleKey: 'settings.admin.pipelines.title',
			title: $i18n.t('settings.admin.pipelines.title'),
			searchPrefixes: ['settings.admin.pipelines.']
		},
		{
			id: 'admin:db',
			titleKey: 'settings.admin.db.title',
			title: $i18n.t('settings.admin.db.title'),
			searchPrefixes: ['settings.admin.db.']
		}
	];
	let availableSettings: SettingsTab[] = [];
	let filteredSettings: string[] = [];
	let filteredPersonalSettings: string[] = [];
	let filteredAdminSettings: string[] = [];

	let search = '';
	let englishRequested = false;
	$: if (modalShow && !englishRequested) {
		englishRequested = true;
		$i18n.loadLanguages('en-US').catch((error: unknown) => {
			console.error(error);
		});
	}

	const getAvailableSettings = (personalTabs: SettingsTab[], administratorTabs: SettingsTab[]) => {
		const personalSettings = personalTabs.filter((tab) => {
			if (tab.id === 'connections') {
				return $config?.features?.enable_direct_connections;
			}

			if (tab.id === 'tools') {
				return (
					$config?.features?.enable_direct_integrations === true &&
					($user?.role === 'admin' ||
						($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers))
				);
			}

			if (tab.id === 'interface') {
				return $user?.role === 'admin' || ($user?.permissions?.settings?.interface ?? true);
			}

			if (tab.id === 'personalization') {
				return (
					$config?.features?.enable_memories &&
					($user?.role === 'admin' || ($user?.permissions?.features?.memories ?? true))
				);
			}

			return true;
		});

		return (
			$user?.role === 'admin' ? [...personalSettings, ...administratorTabs] : personalSettings
		).filter(
			(tab) => tab.id !== 'admin:analytics' || ($config?.features?.enable_admin_analytics ?? true)
		);
	};

	$: searchIndex = buildSettingsSearchIndex(availableSettings, english, $i18n, {
		user: $user,
		config: $config
	});
	$: filteredSettings = searchSettingsTabs(searchIndex, search);
	$: filteredPersonalSettings = filteredSettings.filter((id) => !isAdminTab(id));
	$: filteredAdminSettings = filteredSettings.filter(isAdminTab);

	const selectTab = (id: string) => {
		if (!availableSettings.some((tab) => tab.id === id)) return;
		selectedTab = id;
	};

	const searchKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && search) {
			event.preventDefault();
			event.stopPropagation();
			search = '';
		} else if (event.key === 'Enter') {
			event.preventDefault();
			if (filteredSettings.length) selectTab(filteredSettings[0]);
		}
	};

	const saveSettings = async (updated: Record<string, any>) => {
		const saved = await updateUserSettings(localStorage.token, {
			ui: updated
		}).catch((error) => {
			toast.error(`${error}`);
			throw error;
		});
		personalUiSettings =
			saved?.ui && typeof saved.ui === 'object' && !Array.isArray(saved.ui) ? saved.ui : {};
		await settings.set(
			mergeUiSettings($config?.ui?.default_interface_settings ?? {}, personalUiSettings)
		);
		await models.set(await getModels());
	};

	const getModels = async () => {
		return await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null
		);
	};

	const adminConfigSaveHandler = async () => {
		toast.success($i18n.t('Settings saved successfully!'));
		await tick();
		await config.set(await getBackendConfig());
	};

	const tabButtonClass = (active: boolean) =>
		`flex items-center gap-1.5 h-7 px-2 md:w-full shrink-0 rounded-lg text-xs text-left transition-colors duration-75 ${
			active
				? 'font-medium text-gray-900 dark:text-white bg-gray-50 dark:bg-white/[0.04]'
				: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
		}`;

	let selectedTab = 'general';
	const scrollToSelectedTab = async () => {
		if (!browser || !modalShow || !selectedTab) {
			return;
		}

		await tick();
		const tabElement = document.querySelector<HTMLElement>(
			'#settings-tabs-container [role="tab"][aria-selected="true"]'
		);
		tabElement?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
	};

	$: if ($user?.role !== 'admin' && isAdminTab(selectedTab)) {
		selectedTab = 'general';
	}

	$: if (
		$config &&
		$user &&
		availableSettings.length &&
		!availableSettings.some((tab) => tab.id === selectedTab)
	) {
		selectedTab = 'general';
	}

	$: if (modalShow && selectedTab) {
		scrollToSelectedTab();
	}

	$: if ($config && $user) {
		availableSettings = getAvailableSettings(allSettings, adminSettings);
	}
</script>

<Modal
	size="full"
	containerClassName="p-4 sm:p-6 lg:p-8"
	className="!w-[calc(100vw-2rem)] sm:!w-[calc(100vw-3rem)] lg:!w-[calc(100vw-4rem)] !max-w-[80rem] h-[min(max(54rem,80dvh),calc(100dvh-4rem))] max-h-[calc(100dvh-4rem)] flex flex-col md:flex-row bg-white dark:bg-gray-900 rounded-4xl overflow-hidden"
	bind:show={modalShow}
>
	<nav
		id="settings-tabs-container"
		class="shrink-0 min-w-0 md:min-h-0 flex flex-col border-b md:border-b-0 md:border-r border-gray-100/30 dark:border-white/[0.02] md:w-[15rem]"
	>
		<button
			class="flex items-center gap-1.5 h-7 px-2 m-1 md:mb-0 md:w-[calc(100%-0.5rem)] shrink-0 rounded-lg text-xs text-gray-400 dark:text-gray-600 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75"
			type="button"
			on:click={() => {
				show = false;
			}}
		>
			<ChevronLeft className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Back')}</span>
		</button>

		<div
			class="flex items-center gap-1.5 h-7 px-2 mx-1 mt-1 mb-0.5 shrink-0 rounded-lg text-xs bg-gray-50/70 dark:bg-white/[0.03]"
		>
			<div class="self-center rounded-l-xl bg-transparent">
				<Search className="size-3.5" strokeWidth="1.5" />
			</div>
			<label class="sr-only" for="search-input-settings-modal">{$i18n.t('Search')}</label>
			<input
				data-settings-search
				class="w-full text-xs bg-transparent py-1 outline-hidden dark:text-gray-300"
				bind:value={search}
				id="search-input-settings-modal"
				on:keydown={searchKeydown}
				placeholder={$i18n.t('Search')}
			/>
		</div>

		<div class="sr-only" role="status" aria-live="polite">
			{search
				? filteredSettings.length
					? $i18n.t('Matching tabs: {{count}}', { count: filteredSettings.length })
					: $i18n.t('No matches')
				: ''}
		</div>

		<div
			class="tabs scrollbar-none max-h-32 md:max-h-none flex min-w-0 flex-1 min-h-0 overflow-x-auto md:overflow-x-hidden md:overflow-y-auto md:flex-col p-1 pl-0 md:pl-1 gap-px"
		>
			<span
				class="hidden md:block text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 mt-1.5 mb-0.5"
			>
				{$i18n.t('Personal')}
			</span>

			{#if filteredPersonalSettings.length > 0}
				{#each filteredPersonalSettings as tabId, index (tabId)}
					{#if shouldShowSettingGroup(filteredPersonalSettings, index)}
						<span class={settingGroupHeadingClass(index === 0)}>
							{settingGroupTitle(tabId)}
						</span>
					{/if}

					{#if tabId === 'general'}
						<button
							role="tab"
							aria-controls="tab-general"
							aria-selected={selectedTab === 'general'}
							class={tabButtonClass(selectedTab === 'general')}
							on:click={() => {
								selectTab('general');
							}}
						>
							<SettingsAlt className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.general.title')}</span>
						</button>
					{:else if tabId === 'interface'}
						<button
							role="tab"
							aria-controls="tab-interface"
							aria-selected={selectedTab === 'interface'}
							class={tabButtonClass(selectedTab === 'interface')}
							on:click={() => {
								selectTab('interface');
							}}
						>
							<AdjustmentsHorizontal className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.interface.title')}</span>
						</button>
					{:else if tabId === 'notifications'}
						<button
							role="tab"
							aria-controls="tab-notifications"
							aria-selected={selectedTab === 'notifications'}
							class={tabButtonClass(selectedTab === 'notifications')}
							on:click={() => {
								selectTab('notifications');
							}}
						>
							<AppNotification className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.notifications.title')}</span>
						</button>
					{:else if tabId === 'shortcuts'}
						<button
							role="tab"
							aria-controls="tab-shortcuts"
							aria-selected={selectedTab === 'shortcuts'}
							class={tabButtonClass(selectedTab === 'shortcuts')}
							on:click={() => {
								selectTab('shortcuts');
							}}
						>
							<Keyboard className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.shortcuts.title')}</span>
						</button>
					{:else if tabId === 'connections'}
						{#if $user?.role === 'admin' || ($user?.role === 'user' && $config?.features?.enable_direct_connections)}
							<button
								role="tab"
								aria-controls="tab-connections"
								aria-selected={selectedTab === 'connections'}
								class={tabButtonClass(selectedTab === 'connections')}
								on:click={() => {
									selectTab('connections');
								}}
							>
								<Link className="size-3.5" strokeWidth="2" />
								<span>{$i18n.t('settings.personal.connections.title')}</span>
							</button>
						{/if}
					{:else if tabId === 'tools'}
						{#if $user?.role === 'admin' || ($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)}
							<button
								role="tab"
								aria-controls="tab-tools"
								aria-selected={selectedTab === 'tools'}
								class={tabButtonClass(selectedTab === 'tools')}
								on:click={() => {
									selectTab('tools');
								}}
							>
								<WrenchAlt className="size-3.5" strokeWidth="2" />
								<span>{$i18n.t('settings.personal.tools.title')}</span>
							</button>
						{/if}
					{:else if tabId === 'personalization'}
						<button
							role="tab"
							aria-controls="tab-personalization"
							aria-selected={selectedTab === 'personalization'}
							class={tabButtonClass(selectedTab === 'personalization')}
							on:click={() => {
								selectTab('personalization');
							}}
						>
							<Face className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.personalization.title')}</span>
						</button>
					{:else if tabId === 'audio'}
						<button
							role="tab"
							aria-controls="tab-audio"
							aria-selected={selectedTab === 'audio'}
							class={tabButtonClass(selectedTab === 'audio')}
							on:click={() => {
								selectTab('audio');
							}}
						>
							<SoundHigh className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.audio.title')}</span>
						</button>
					{:else if tabId === 'data_controls'}
						<button
							role="tab"
							aria-controls="tab-data-controls"
							aria-selected={selectedTab === 'data_controls'}
							class={tabButtonClass(selectedTab === 'data_controls')}
							on:click={() => {
								selectTab('data_controls');
							}}
						>
							<DatabaseSettings className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.dataControls.title')}</span>
						</button>
					{:else if tabId === 'usage'}
						<button
							role="tab"
							aria-controls="tab-usage"
							aria-selected={selectedTab === 'usage'}
							class={tabButtonClass(selectedTab === 'usage')}
							on:click={() => {
								selectTab('usage');
							}}
						>
							<UsageIcon className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.usage.title')}</span>
						</button>
					{:else if tabId === 'archived_chats'}
						<button
							role="tab"
							aria-controls="tab-archived-chats"
							aria-selected={selectedTab === 'archived_chats'}
							class={tabButtonClass(selectedTab === 'archived_chats')}
							on:click={() => {
								selectTab('archived_chats');
							}}
						>
							<ArchiveBox className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.archivedChats.title')}</span>
						</button>
					{:else if tabId === 'account'}
						<button
							role="tab"
							aria-controls="tab-account"
							aria-selected={selectedTab === 'account'}
							class={tabButtonClass(selectedTab === 'account')}
							on:click={() => {
								selectTab('account');
							}}
						>
							<UserCircle className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.account.title')}</span>
						</button>
					{:else if tabId === 'about'}
						<button
							role="tab"
							aria-controls="tab-about"
							aria-selected={selectedTab === 'about'}
							class={tabButtonClass(selectedTab === 'about')}
							on:click={() => {
								selectTab('about');
							}}
						>
							<InfoCircle className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('settings.personal.about.title')}</span>
						</button>
					{/if}
				{/each}
			{/if}

			{#if $user?.role === 'admin' && filteredAdminSettings.length > 0}
				<div
					class="hidden md:block shrink-0 self-stretch h-px mx-1 my-2 bg-gray-100/40 dark:bg-white/[0.025]"
				></div>
				<span class="hidden md:block text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 mb-0.5">
					{$i18n.t('Admin')}
				</span>

				{#each filteredAdminSettings as tabId, index (tabId)}
					{#if shouldShowSettingGroup(filteredAdminSettings, index)}
						<span class={settingGroupHeadingClass(index === 0)}>
							{settingGroupTitle(tabId)}
						</span>
					{/if}

					{@const tab = adminSettings.find((setting) => setting.id === tabId)}
					{#if tab}
						<button
							role="tab"
							aria-controls={adminTabPanelId(tab.id)}
							aria-selected={selectedTab === tab.id}
							class={tabButtonClass(selectedTab === tab.id)}
							on:click={() => {
								selectTab(tab.id);
							}}
						>
							<AdminTabIcon id={adminTabSegment(tab.id)} className="size-3.5" strokeWidth="2" />
							<span>{tab.title}</span>
						</button>
					{/if}
				{/each}
			{/if}

			{#if filteredSettings.length === 0}
				<div class="px-2 py-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('No matches')}
				</div>
			{/if}
		</div>
	</nav>

	<div class="flex-1 min-w-0 min-h-0 p-4 md:px-5 flex flex-col">
		<div class="flex-1 min-h-0 overflow-hidden">
			{#if selectedTab === 'general'}
				<General
					{getModels}
					{saveSettings}
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'interface'}
				<Interface
					{saveSettings}
					personalSettingsValue={personalUiSettings}
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'notifications'}
				<Notifications {saveSettings} />
			{:else if selectedTab === 'shortcuts'}
				<Shortcuts {saveSettings} />
			{:else if selectedTab === 'connections'}
				<Connections
					saveSettings={async (updated: Record<string, any>) => {
						await saveSettings(updated);
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'tools'}
				<Integrations
					saveSettings={async (updated: Record<string, any>) => {
						await saveSettings(updated);
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'personalization'}
				<Personalization
					{saveSettings}
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'audio'}
				<Audio
					{saveSettings}
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'data_controls'}
				<DataControls {saveSettings} />
			{:else if selectedTab === 'usage'}
				<Usage />
			{:else if selectedTab === 'archived_chats'}
				<ArchivedChats />
			{:else if selectedTab === 'account'}
				<Account
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'about'}
				<About />
			{:else if selectedTab === 'admin:general'}
				<AdminGeneral saveHandler={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:authentication'}
				<AdminAuthentication />
			{:else if selectedTab === 'admin:connections'}
				<AdminConnections
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:models'}
				<AdminModels bind:tabState />
			{:else if selectedTab === 'admin:subagents'}
				<AdminSubagents />
			{:else if selectedTab === 'admin:evaluations'}
				<AdminEvaluations />
			{:else if selectedTab === 'admin:analytics'}
				<AdminAnalytics />
			{:else if selectedTab === 'admin:integrations'}
				<AdminIntegrations {saveSettings} />
			{:else if selectedTab === 'admin:documents'}
				<AdminDocuments on:save={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:web'}
				<AdminWebSearch saveHandler={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:code-execution'}
				<AdminCodeExecution saveHandler={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:interface'}
				<AdminInterface
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:audio'}
				<AdminAudio
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:images'}
				<AdminImages
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:db'}
				<AdminDatabase
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:pipelines'}
				<AdminPipelines
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{/if}
		</div>
	</div>
</Modal>
