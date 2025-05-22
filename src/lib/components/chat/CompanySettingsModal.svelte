<script lang="ts">
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { models, settings, user, mobile } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { getModels as _getModels } from '$lib/apis';
	import { goto } from '$app/navigation';

	import Modal from '../common/Modal.svelte';
	import ProfileIcon from '../icons/ProfileIcon.svelte';
    import GeneralSettings from '$lib/components/chat/Settings/CompanySettings/General.svelte';
	import GroupIcon from '../icons/GroupIcon.svelte';
	import UserManagement from './Settings/CompanySettings/UserManagement.svelte';
	import ModelControlIcon from '../icons/ModelControlIcon.svelte';
	import ModelControl from './Settings/CompanySettings/ModelControl.svelte';
	import { getUsers } from '$lib/apis/users';
	import AnalyticsIcon from '../icons/AnalyticsIcon.svelte';
	import Analytics from './Settings/CompanySettings/Analytics.svelte';
	import { getTopModels, getTotalUsers, getTotalMessages, getAdoptionRate, getPowerUsers, getSavedTimeInSeconds, getTopUsers, getTotalBilling, getTotalChats, getTotalAssistants } from '$lib/apis/analytics';
	import BillingIcon from '../icons/BillingIcon.svelte';
	import Billing from './Settings/CompanySettings/Billing.svelte';
	import { getMonthRange } from '$lib/utils';
	import { page } from '$app/stores';
	import {
		getCurrentSubscription,
		getSubscriptionPlans
	} from '$lib/apis/payments';
	import { subscription } from '$lib/stores';
	import BackIcon from '../icons/BackIcon.svelte';
	
	const i18n = getContext('i18n');

	export let show = false;
	let selectedTab = 'general-settings';
	let plans = [];

	interface SettingsTab {
		id: string;
		title: string;
		keywords: string[];
	}

	function updateTabParam(tab) {
		const url = new URL(window.location.href);
		url.searchParams.set('tab', tab);
		url.searchParams.set('modal', 'company-settings'); 
		window.history.replaceState({}, '', url); 
	}

	const searchData: SettingsTab[] = [
		{
			id: 'general-settings',
			title: 'General Settings',
			keywords: [	
			]
		},
		{
			id: 'user-management',
			title: 'User Management',
			keywords: [	
			]
		},
		{
			id: 'model-control',
			title: 'Model Control',
			keywords: [	
			]
		},
		{
			id: 'analytics',
			title: 'Analitics',
			keywords: [

			]
		},
		{
			id: 'billing',
			title: 'Billing',
			keywords: [
		
			]
		}
		];

	let search = '';
	let visibleTabs = searchData.map((tab) => tab.id);
	let searchDebounceTimeout;

	const searchSettings = (query: string): string[] => {
		const lowerCaseQuery = query.toLowerCase().trim();
		return searchData
			.filter(
				(tab) =>
					tab.title.toLowerCase().includes(lowerCaseQuery) ||
					tab.keywords.some((keyword) => keyword.includes(lowerCaseQuery))
			)
			.map((tab) => tab.id);
	};

	const searchDebounceHandler = () => {
		clearTimeout(searchDebounceTimeout);
		searchDebounceTimeout = setTimeout(() => {
			visibleTabs = searchSettings(search);
			if (visibleTabs.length > 0 && !visibleTabs.includes(selectedTab)) {
				selectedTab = visibleTabs[0];
			}
		}, 100);
	};

	const saveSettings = async (updated) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const getModels = async () => {
		return await _getModels(localStorage.token);
	};


	// Function to handle sideways scrolling
	const scrollHandler = (event) => {
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			event.preventDefault(); // Prevent default vertical scrolling
			settingsTabsContainer.scrollLeft += event.deltaY; // Scroll sideways
		}
	};

	const addScrollListener = async () => {
		await tick();
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			settingsTabsContainer.addEventListener('wheel', scrollHandler);
		}
	};

	const removeScrollListener = async () => {
		await tick();
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			settingsTabsContainer.removeEventListener('wheel', scrollHandler);
		}
	};

	$: if (show) {
		addScrollListener();
	} else {
		removeScrollListener();
	}
	let users = [];
	const getUsersHandler = async () => {
		users = await getUsers(localStorage.token);
	};

	let analytics = null;
	let analyticsLoading = false;

	async function fetchAnalytics() {
	const token = localStorage.token;
	const now = new Date();
	const year = now.getFullYear();
	const month = now.getMonth() + 1;
	const { start, end } = getMonthRange(year, month);
	console.log(start, end)
	try {
		analyticsLoading = true;
		const [
			topModels,
			totalUsers,
			totalMessages,
			adoptionRate,
			powerUsers,
			savedTime,
			topUsers,
			totalBilling,
			totalChats,
			totalAssistants
		] = await Promise.allSettled([
			getTopModels(token, start, end),
			getTotalUsers(token),
			getTotalMessages(token),
			getAdoptionRate(token),
			getPowerUsers(token),
			getSavedTimeInSeconds(token),
			getTopUsers(token, start, end),
			getTotalBilling(token),
			getTotalChats(token),
			getTotalAssistants(token),
		]);
		
		analytics = {
			topModels: topModels?.status === 'fulfilled' && !topModels?.value?.message ? topModels?.value : [],
			totalUsers: totalUsers?.status === 'fulfilled' ? totalUsers?.value : {},
			totalMessages: totalMessages?.status === 'fulfilled' ? totalMessages?.value : {},
			adoptionRate: adoptionRate?.status === 'fulfilled' ? adoptionRate?.value : {},
			powerUsers: powerUsers?.status === 'fulfilled' ? powerUsers?.value : {},
			savedTime: savedTime?.status === 'fulfilled' ? savedTime?.value : {},
			topUsers: topUsers?.status === 'fulfilled' ? topUsers?.value : {},
			totalBilling: totalBilling?.status === 'fulfilled' ? totalBilling?.value : {},
			totalChats: totalChats?.status === 'fulfilled' ? totalChats?.value : {},
			totalAssistants: totalAssistants?.status === 'fulfilled' ? totalAssistants?.value : {},
		}
		console.log(analytics)
		} catch (error) {
			console.error('Error fetching analytics:', error);
		} finally {
			analyticsLoading = false;
		}
	}
	let autoRecharge = false;
	let subscriptionLoading = false;
	async function getSubscription() {
		subscriptionLoading = true;
		const sub = await getCurrentSubscription(localStorage.token).catch(error => {
			console.log(error);
			subscriptionLoading = false;
		});
		if(sub){
			subscription.set(sub);
			autoRecharge = sub?.auto_recharge ? sub?.auto_recharge : false;
			subscriptionLoading = false;
		}
	}
	async function getPlans() {
		const res = await getSubscriptionPlans(localStorage.token).catch((error) => console.log(error));
		if (res) {
			plans = res;
		}
	}


	$: if(show){
		getUsersHandler();
		getSubscription();
		getPlans();
		fetchAnalytics();
		const tabParam = $page.url.searchParams.get('tab');
		const resetTabs = $page.url.searchParams.get('resetTabs');
		console.log(resetTabs, 'if statement')
		if(resetTabs) {
			selectedTab = null;
		} else {
			selectedTab = tabParam || 'general-settings';
		}	
	}


</script>

<Modal size="md-plus" bind:show blockBackdropClick={true} className="dark:bg-customGray-800 rounded-2xl" containerClassName="bg-lightGray-250/50 dark:bg-[#1D1A1A]/50 backdrop-blur-[7.44px]">
	<div class="text-lightGray-100 dark:text-customGray-100 bg-lightGray-550 dark:bg-customGray-800 rounded-xl min-h-[calc(100dvh-24px)] md:h-auto">
		<div class="px-4 md:px-7">
			<div class=" flex justify-between dark:text-white pt-5 pb-4 border-b dark:border-customGray-700">
				{#if selectedTab && $mobile}
					<button class="capitalize flex items-center" on:click={() => selectedTab = null}>
						<BackIcon className="mr-1 size-4 shrink-0"/>
						<div class="shrink-0">{$i18n.t(searchData?.find(item => item?.id === selectedTab).title)}</div>
					</button>
				{:else}
					<div class="self-center">{$i18n.t('Company Settings')}</div>
				{/if}
				<button
					class="self-center"
					on:click={() => {
						const url = new URL(window.location.href);
						url.search = ''; 
						goto(url.pathname, { replaceState: true });
						show = false;	
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-5 h-5"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</button>
			</div>
		</div>

		<div class="flex flex-col md:flex-row w-full pl-4 pr-4 md:pl-4 md:pr-7 md:space-x-4">
			{#if selectedTab === null || !$mobile}
				<div
					id="settings-tabs-container"
					class="rounded-bl-lg md:pl-4 md:pt-5 pr-2 tabs flex flex-col md:dark:bg-customGray-900 md:gap-1 w-full md:w-[252px] dark:text-gray-200 text-sm font-medium text-left mb-1 md:mb-0"
				>
					{#if visibleTabs.length > 0}
						{#each visibleTabs as tabId (tabId)}
						{#if tabId === 'general-settings'}
						<button
							class="md:px-3 py-5 md:py-2.5 border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 md:flex-none text-left transition {selectedTab ===
							'general-settings'
								? 'bg-lightGray-700 dark:bg-customGray-800'
								: ' text-lightGray-100 dark:text-customGray-100 hover:bg-lightGray-700 dark:hover:text-white'}"
							on:click={() => {
								selectedTab = 'general-settings';
								updateTabParam(selectedTab);
							}}
						>
							<div class="flex items-center md:mb-1">
								<div class=" self-center mr-2">
									<ProfileIcon/>
								</div>
								<div class=" self-center">{$i18n.t('General Settings')}</div>
							</div>
						</button>
						{:else if tabId === 'user-management'}
						<button
							class="md:px-3 py-5 md:py-2.5 border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 md:flex-none text-left transition {selectedTab ===
							'user-management'
								? 'bg-lightGray-700 dark:bg-customGray-800'
								: 'text-lightGray-100 dark:text-customGray-100 hover:bg-lightGray-700 dark:hover:text-white'}"
							on:click={() => {
								selectedTab = 'user-management';
								updateTabParam(selectedTab);
							}}
						>
							<div class="flex items-center md:mb-1">
								<div class=" self-center mr-2">
									<GroupIcon/>
								</div>
								<div class=" self-center">{$i18n.t('User management')}</div>
							</div>
						</button>
						{:else if tabId === 'model-control'}
						<button
							class="md:px-3 py-5 md:py-2.5 border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 md:flex-none text-left transition {selectedTab ===
							'model-control'
								? 'bg-lightGray-700 dark:bg-customGray-800'
								: ' text-lightGray-100 dark:text-customGray-100 hover:bg-lightGray-700 dark:hover:text-white'}"
							on:click={() => {
								selectedTab = 'model-control';
								updateTabParam(selectedTab);
							}}
						>
							<div class="flex items-center md:mb-1">
								<div class=" self-center mr-2">
									<ModelControlIcon/>
								</div>
								<div class=" self-center">{$i18n.t('Model Control')}</div>
							</div>
						</button>
						{:else if tabId === 'analytics'}
						<button
							class="md:px-3 py-5 md:py-2.5 border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 md:flex-none text-left transition {selectedTab ===
							'analytics'
								? 'bg-lightGray-700 dark:bg-customGray-800'
								: ' text-lightGray-100 dark:text-customGray-100 hover:bg-lightGray-700 dark:hover:text-white'}"
							on:click={() => {
								selectedTab = 'analytics';
								updateTabParam(selectedTab);
							}}
						>
							<div class="flex items-center md:mb-1">
								<div class=" self-center mr-2">
									<AnalyticsIcon/>
								</div>
								<div class=" self-center">{$i18n.t('Analytics')}</div>
							</div>
						</button>
						{:else if tabId === 'billing'}
						<button
							class="md:px-3 py-5 md:py-2.5 border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 md:flex-none text-left transition {selectedTab ===
							'billing'
								? 'bg-lightGray-700 dark:bg-customGray-800'
								: ' text-lightGray-100 dark:text-customGray-100 hover:bg-lightGray-700 dark:hover:text-white'}"
							on:click={() => {
								selectedTab = 'billing';
								updateTabParam(selectedTab);
							}}
						>
							<div class="flex items-center md:mb-1">
								<div class=" self-center mr-2">
									<BillingIcon/>
								</div>
								<div class=" self-center">{$i18n.t('Billing')}</div>
							</div>
						</button>
						{/if}
						{/each}
					{:else}
						<div class="text-center text-gray-500 mt-4">
							{$i18n.t('No results found')}
						</div>
					{/if}
				</div>
			{/if}
			<div class="flex-1 md:min-h-[32rem]">
				{#if selectedTab === 'general-settings'}
                    <GeneralSettings
                    {getModels}
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
                    />
					
				{:else if selectedTab === 'user-management'}
					<UserManagement
						{users}
						{getSubscription}
						{getUsersHandler}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'model-control'}
					<ModelControl/>
				{:else if selectedTab === 'analytics'}
					<Analytics {analytics} {analyticsLoading}/>
				{:else if selectedTab === 'billing'}
					<Billing bind:autoRecharge bind:subscriptionLoading {plans}/>
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
