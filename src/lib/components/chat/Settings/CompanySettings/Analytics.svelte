<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import InfoIcon from '$lib/components/icons/InfoIcon.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Chart from './Chart.svelte';
	import { getModelIcon } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getMonths } from '$lib/utils';
	import { onClickOutside } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import dayjs from 'dayjs';
	import { getTopModels } from '$lib/apis/analytics';
	import { getMonthRange } from '$lib/utils';

	const i18n = getContext('i18n');
	export let analytics = {};
	export let analyticsLoading = false;
	let activeTab = 'messages';

	let showUsersSortDropdown = false;
	let usersSortRef;

	let sortOptions = [
		{ value: 'credits', label: 'By Credits Used' },
		{ value: 'assistants', label: 'By Assistants Created' },
		{ value: 'messages', label: 'By Messages Sent' }
	];
	let selectedSortOrder = sortOptions[0];

	let showMonthsDropdown = false;
	let monthsRef;

	const monthsBack = 12;
	const monthOptions = Array.from({ length: monthsBack }, (_, i) => {
		const date = dayjs().subtract(i, 'month');
		return {
			label: date.format('MMMM YYYY'),
			value: {
				year: date.year(),
				month: date.month() + 1
			}
		};
	});

	let selectedMonth = monthOptions[0];
	let chartMessagesData = null;
	let chartChatsData = null;

	let users = [];
	$: {
		if (analytics?.topUsers?.top_by_credits?.length > 0) {
			users = analytics?.topUsers?.top_by_credits;
		} 
	}
	$: {
		if (analytics?.totalMessages?.monthly_messages) {
			chartMessagesData = {
				labels: analytics?.totalMessages?.monthly_messages
					? getMonths(analytics?.totalMessages?.monthly_messages)
					: [],
				datasets: [
					{
						label: 'Total Messages',
						// data: ['N/A', 'N/A', 15, 20, 24, 25, 40, 48, 50, 62, 60, 70, 80],
						data: Object.values(analytics?.totalMessages?.monthly_messages),
						backgroundColor: ['#305BE4'],
						borderColor: ['#305BE4']
					}
				]
			};
		}
		if (analytics?.totalChats?.monthly_chats) {
			chartChatsData = {
				labels: analytics?.totalChats?.monthly_chats
					? getMonths(analytics?.totalChats?.monthly_chats)
					: [],
				datasets: [
					{
						label: 'Total Chats',
						// data: ['N/A', 'N/A', 15, 20, 24, 25, 40, 48, 50, 62, 60, 70, 80],
						data: Object.values(analytics?.totalChats?.monthly_chats),
						backgroundColor: ['#305BE4'],
						borderColor: ['#305BE4']
					}
				]
			};
		}
	}

	

	const chartOptions = {
		responsive: true,
		plugins: {
			legend: {
				display: false
			}
		}
		// scales: {
		// 	y: {
		// 		ticks: {
		// 			callback: function (value) {
		// 				return value + '%';
		// 			}
		// 		}
		// 	}
		// }
	};
</script>

<div class="pb-20">
	{#if !analyticsLoading}
		<div
			class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
		>
			<div class="flex w-full justify-between items-center">
				<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('Key Summary')}</div>
			</div>
		</div>
		<div class="grid grid-cols-2 md:grid-cols-4 gap-[6px]">
			<div class="rounded-2xl bg-lightGray-300 dark:bg-customGray-900 pt-4 pb-2 flex flex-col items-center">
				<div class="text-2xl text-lightGray-100 dark:text-customGray-100 mb-2.5">
					{analytics?.totalUsers?.total_users}
				</div>
				<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mb-1">{$i18n.t('Total Users')}</div>
				<Tooltip content="">
					<div
						class="ml-1 cursor-pointer group relative flex justify-center items-center w-[18px] h-[18px] rounded-full text-white dark:text-white bg-customBlue-600 dark:bg-customGray-700"
					>
						<InfoIcon className="size-6" />
					</div>
				</Tooltip>
			</div>
			<div class="rounded-2xl bg-lightGray-300 dark:bg-customGray-900 pt-4 pb-2 flex flex-col items-center">
				<div class="text-2xl text-lightGray-100 dark:text-customGray-100 mb-2.5">
					{analytics?.adoptionRate?.adoption_rate}%
				</div>
				<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mb-1">{$i18n.t('Adoption Rate')}</div>
				<Tooltip content="">
					<div
						class="ml-1 cursor-pointer group relative flex justify-center items-center w-[18px] h-[18px] rounded-full text-white dark:text-white bg-customBlue-600 dark:bg-customGray-700"
					>
						<InfoIcon className="size-6" />
					</div>
				</Tooltip>
			</div>
			<div class="rounded-2xl text-lightGray-100 bg-lightGray-300 dark:bg-customGray-900 pt-4 pb-2 flex flex-col items-center">
				<div class="text-2xl dark:text-customGray-100 mb-2.5">
					{analytics?.powerUsers?.power_users_count}
				</div>
				<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mb-1">{$i18n.t('Power Users')}</div>
				<Tooltip content="">
					<div
						class="ml-1 cursor-pointer group relative flex justify-center items-center w-[18px] h-[18px] rounded-full text-white dark:text-white bg-customBlue-600 dark:bg-customGray-700"
					>
						<InfoIcon className="size-6" />
					</div>
				</Tooltip>
			</div>
			<div class="rounded-2xl text-lightGray-100 bg-lightGray-300 dark:bg-customGray-900 pt-4 pb-2 flex flex-col items-center">
				<div class="text-2xl dark:text-customGray-100 mb-2.5">
					{analytics?.totalAssistants?.total_assistants}
				</div>
				<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mb-1">{$i18n.t('Assistants Created')}</div>
				<Tooltip content="">
					<div
						class="ml-1 cursor-pointer group relative flex justify-center items-center w-[18px] h-[18px] rounded-full text-white dark:text-white bg-customBlue-600 dark:bg-customGray-700"
					>
						<InfoIcon className="size-6" />
					</div>
				</Tooltip>
			</div>
		</div>
		<div class="bg-lightGray-300 dark:bg-customGray-900 rounded-2xl p-4 pb-1 mt-5">
			<div
				class="flex w-full justify-between items-center pb-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('Top Users')}</div>
				</div>
				<div use:onClickOutside={() => (showUsersSortDropdown = false)}>
					<div class="relative" bind:this={usersSortRef}>
						<button
							type="button"
							class="flex items-center min-w-40 justify-end text-sm border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer"
							on:click={() => (showUsersSortDropdown = !showUsersSortDropdown)}
						>
							<div class="flex items-center">
								<div class="text-xs dark:text-customGray-200 max-w-[15rem] text-left">
									{selectedSortOrder?.label}
								</div>
								<ChevronDown className="size-2 ml-1" />
							</div>
						</button>

						{#if showUsersSortDropdown}
							<div
								class="max-h-60 min-w-40 overflow-y-auto absolute top-6 -right-2 z-50 bg-lightGray-300 dark:bg-customGray-900 border border-lightGray-400 dark:border-customGray-700 rounded-md shadow"
							>
								<div class="px-1 py-1">
									{#each sortOptions?.filter?.((item) => item?.value !== selectedSortOrder?.value) as option}
										<div
											role="button"
											tabindex="0"
											on:click={() => {
												selectedSortOrder = option;
												if (option.value === 'credits') {
													users = analytics?.topUsers?.top_by_credits;
												} else if (option.value === 'messages') {
													users = analytics?.topUsers?.top_by_messages;
												} else {
													users = analytics?.topUsers?.top_by_assistants;
												}
												showUsersSortDropdown = false;
											}}
											class="flex items-center justify-end w-full cursor-pointer text-xs text-lightGray-100 dark:text-customGray-100 px-2 py-2 hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md"
										>
											{option?.label}
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>

			{#each users as user}
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center">
						<img
							class=" rounded-full w-3 h-3 object-cover mr-2.5"
							src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
							user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
							user.profile_image_url.startsWith('data:')
								? user.profile_image_url
								: `/user.png`}
							alt="user"
						/>

						<div class="text-xs dark:text-customGray-100 mr-1 whitespace-nowrap">
							{user.first_name}
							{user.last_name}
						</div>

						<Tooltip content={user.email} className=" w-fit overflow-hidden" placement="top-end">
							<div
								class="text-xs dark:text-customGray-590 mr-1 truncate text-ellipsis whitespace-nowrap"
							>
								{user.email}
							</div>
						</Tooltip>
					</div>
					{#if selectedSortOrder.value === 'credits'}
						<div class="text-xs dark:text-customGray-590">
							€{(user?.total_credits_used).toFixed(2)}
						</div>
					{:else if selectedSortOrder.value === 'messages'}
						<div class="text-xs dark:text-customGray-590">
							{user?.message_count} {$i18n.t('messages')}
						</div>
					{:else}
						<div class="text-xs dark:text-customGray-590">
							{user?.assistant_count} {$i18n.t('assistants')}
						</div>
					{/if}
				</div>
			{/each}
		</div>
		<div class="bg-lightGray-300 dark:bg-customGray-900 rounded-2xl p-4 pb-1 mt-5">
			<div
				class="flex w-full justify-between items-center pb-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('Top 3 models Used')}</div>
				</div>
				<div use:onClickOutside={() => (showMonthsDropdown = false)}>
					<div class="relative" bind:this={monthsRef}>
						<button
							type="button"
							class="flex items-center min-w-40 justify-end text-sm border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer"
							on:click={() => (showMonthsDropdown = !showMonthsDropdown)}
						>
							<div class="flex items-center">
								<div class="text-xs text-lightGray-100 dark:text-customGray-200 max-w-[15rem] text-left">
									{selectedMonth?.label}
								</div>
								<ChevronDown className="size-2 ml-1" />
							</div>
						</button>

						{#if showMonthsDropdown}
							<div
								class="max-h-60 min-w-40 overflow-y-auto absolute top-6 -right-2 z-50 bg-lightGray-300 dark:bg-customGray-900 border border-gray-300 dark:border-customGray-700 rounded-md shadow"
							>
								<div class="px-1 py-1">
									{#each monthOptions as option}
										<div
											role="button"
											tabindex="0"
											on:click={async () => {
												selectedMonth = option;
												const { start, end } = getMonthRange(
													selectedMonth.value.year,
													selectedMonth.value.month
												);
												const res = await getTopModels(localStorage.token, start, end);
												analytics = {
													...analytics,
													topModels: res?.length > 0 ? res : []
												};
												showMonthsDropdown = false;
											}}
											class="flex items-center justify-end w-full cursor-pointer text-xs dark:text-customGray-100 px-2 py-2 hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md"
										>
											{option?.label}
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
			{#each analytics?.topModels as model}
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center">
						<img
							class=" rounded-full w-3 h-3 object-cover mr-2.5"
							src={getModelIcon(model?.model)}
							alt="user"
						/>

						<div class="text-xs dark:text-customGray-100 mr-1 whitespace-nowrap">
							{model?.model}
						</div>
					</div>
					<div class="text-xs dark:text-customGray-590">€{(model?.usage_count).toFixed(2)}</div>
				</div>
			{/each}
		</div>
		<div class="mt-5">
			<div
				class="flex w-full justify-between items-center pb-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('User Activity Insights')}</div>
				</div>
			</div>
			<div class="w-fit flex bg-lightGray-700 dark:bg-customGray-900 rounded-md mx-auto mb-2.5">
				<button
					on:click={() => (activeTab = 'messages')}
					class="{activeTab === 'messages'
						? 'text-lightGray-100 bg-lightGray-300 border-lightGray-400 dark:bg-customGray-900 rounded-md border dark:border-customGray-700'
						: 'text-lightGray-100/70'} px-6 py-2 flex-shrink-0 text-xs font-medium leading-none dark:text-customGray-100"
					>{$i18n.t('Messages')}</button
				>
				<button
					on:click={() => (activeTab = 'chats')}
					class="{activeTab === 'chats'
						? 'text-lightGray-100 bg-lightGray-300 border-lightGray-400 dark:bg-customGray-900 rounded-md border dark:border-customGray-700'
						: 'text-lightGray-100/70'} px-6 py-2 flex-shrink-0 text-xs font-medium leading-none  dark:text-customGray-100"
					>{$i18n.t('Chats')}</button
				>
			</div>
			<div>
				{#if activeTab === 'messages'}
					<div class="dark:bg-customGray-900 rounded-2xl p-4">
						<Chart type="line" data={chartMessagesData} options={chartOptions} />
					</div>
				{:else if activeTab === 'chats'}
					<div class="dark:bg-customGray-900 rounded-2xl p-4">
						<Chart type="line" data={chartChatsData} options={chartOptions} />
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<div class="h-[20rem] w-full flex justify-center items-center">
			<Spinner />
		</div>
	{/if}
</div>
