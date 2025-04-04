<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Chart from 'chart.js/auto';
	import {
		getDailyPrompts,
		getDailyTokens,
		getDailyUsers,
		getDomains,
		getTotalPrompts,
		getTotalTokens,
		getTotalUsers
	} from '$lib/apis/metrics';

	const i18n = getContext('i18n');

	let domains: string[] = [];
	let totalUsers: number = 0,
		totalPrompts: number = 0,
		totalTokens: number = 0,
		dailyUsers: number = 0,
		dailyPrompts: number = 0,
		dailyTokens: number = 0;
	let selectedDomain: string | null = null; // Allow null for "no domain"
	// let dailyActiveUsersChart, dailyPromptsChart, dailyTokensChart;

	// let dailyActiveUsersData = {}; // Replace with actual data
	// let dailyPromptsData = {}; // Replace with actual data
	// let dailyTokensData = {}; // Replace with actual data

	async function updateCharts(selectedDomain: string | null) {
		let updatedDomains = selectedDomain ?? undefined;
		totalUsers = await getTotalUsers(localStorage.token, updatedDomains);
		totalPrompts = await getTotalPrompts(localStorage.token, updatedDomains);
		dailyUsers = await getDailyUsers(localStorage.token, updatedDomains);
		totalTokens = await getTotalTokens(localStorage.token, updatedDomains);
		dailyPrompts = await getDailyPrompts(localStorage.token, updatedDomains);
		dailyTokens = await getDailyTokens(localStorage.token, updatedDomains);
		// dailyActiveUsersData = await getDailyActiveUsersData(localStorage.token, updatedDomains);
		// dailyPromptsData = await getDailyPromptsData(localStorage.token, updatedDomains);
		// dailyTokensData = await getdailyTokensData(localStorage.token, updatedDomains);
	}

	onMount(async () => {
		domains = await getDomains(localStorage.token);
		updateCharts(selectedDomain);

		// 	const ctx1 = document.getElementById('dailyActiveUsersChart').getContext('2d');
		// 	dailyActiveUsersChart = new Chart(ctx1, {
		// 		type: 'line',
		// 		data: {
		// 			labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'], // Updated to 7 days
		// 			datasets: [
		// 				{
		// 					label: 'Daily Active Users',
		// 					data: dailyActiveUsersData[selectedDomain] || [],
		// 					borderColor: 'blue',
		// 					borderWidth: 1
		// 				}
		// 			]
		// 		}
		// 	});

		// 	const ctx2 = document.getElementById('dailyPromptsChart').getContext('2d');
		// 	dailyPromptsChart = new Chart(ctx2, {
		// 		type: 'line',
		// 		data: {
		// 			labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'], // Updated to 7 days
		// 			datasets: [
		// 				{
		// 					label: 'Daily Prompts Sent',
		// 					data: dailyPromptsData[selectedDomain] || [],
		// 					borderColor: 'green',
		// 					borderWidth: 1
		// 				}
		// 			]
		// 		}
		// 	});

		// 	const ctx3 = document.getElementById('dailyTokensChart').getContext('2d');
		// 	dailyTokensChart = new Chart(ctx3, {
		// 		type: 'line',
		// 		data: {
		// 			labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'], // Updated to 7 days
		// 			datasets: [
		// 				{
		// 					label: 'Daily Costs',
		// 					data: dailyTokensData[selectedDomain] || [],
		// 					borderColor: 'red',
		// 					borderWidth: 1
		// 				}
		// 			]
		// 		}
		// 	});
	});
</script>

<div class="container mx-auto p-6">
	<div class="mb-4 flex justify-between items-center">
		<h2 class="text-3xl font-extrabold text-gray-900 dark:text-gray-100">
			{$i18n.t('Metrics Dashboard')}
		</h2>
		<div>
			<label
				for="domain-select"
				class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
				>{$i18n.t('Select Domain:')}</label
			>
			<select
				id="domain-select"
				bind:value={selectedDomain}
				on:change={(event) => updateCharts(event.target.value || null)}
				class="block w-48 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
			>
				<option value={null}>{$i18n.t('All')}</option>
				{#each domains as domain}
					<option value={domain}>{domain}</option>
				{/each}
			</select>
		</div>
	</div>

	<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
				{$i18n.t('Total Users')}
			</h5>
			<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{totalUsers}</h4>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
				{$i18n.t('Total Prompts')}
			</h5>
			<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{totalPrompts}</h4>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
				{$i18n.t('Total Tokens')}
			</h5>
			<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">{totalTokens}</h4>
		</div>
	</div>

	<div class="mb-10">
		<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Users')}
				</h5>
				<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{dailyUsers}</h4>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Prompts')}
				</h5>
				<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{dailyPrompts}</h4>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Tokens')}
				</h5>
				<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">{dailyTokens}</h4>
			</div>
		</div>
	</div>

	<!-- <hr class="border-gray-400 dark:border-gray-600 my-8" />

	<div class="space-y-8">
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				Daily Active Users
				<span class="text-sm font-medium text-green-600 dark:text-green-400 ml-2">+5%</span>
			</h5>
			<canvas id="dailyActiveUsersChart" height="50"></canvas>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				Daily Prompts Sent
				<span class="text-sm font-medium text-red-600 dark:text-red-400 ml-2">-3%</span>
			</h5>
			<canvas id="dailyPromptsChart" height="50"></canvas>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				Daily Tokens Used
				<span class="text-sm font-medium text-green-600 dark:text-green-400 ml-2">+2%</span>
			</h5>
			<canvas id="dailyTokensChart" height="50"></canvas>
		</div>
	</div> -->
</div>
