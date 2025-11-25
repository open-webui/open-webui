<script>
	import { createEventDispatcher, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { models } from '$lib/stores';

	const dispatch = createEventDispatcher();

	// Token Groups Data
	let tokenGroups = [];
	let availableModels = [];
	let loading = true;

	// Form State
	let showCreateGroupModal = false;
	let editingGroup = null;
	let resetStrategy = 'daily'; // 'daily' or 'window'
	let groupForm = {
		name: '',
		models: [],
		limit: 1000000,
		resetTime: '00:00',
		resetTimezone: 'UTC',
		windowDuration: 24 // Hours
	};

	// Scheduling Options
	const timezoneOptions = ['UTC', 'EST', 'PST', 'GMT', 'CET', 'JST', 'CST', 'MST'];

	onMount(async () => {
		await loadData();
	});

	const loadData = async () => {
		try {
			loading = true;

			// Load existing token groups
			await loadTokenGroups();
		} catch (error) {
			console.error('Error loading data:', error);
			toast.error('Failed to load data');
		} finally {
			loading = false;
		}
	};

	// Reactive statement to get models from the store
	$: {
		availableModels = $models || [];
	}

	const loadTokenGroups = async () => {
		try {
			const response = await fetch('/api/usage/groups', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				tokenGroups = Object.entries(data.groups || {}).map(([name, groupData]) => ({
					name,
					...groupData,
					resetTime: groupData.resetTime || '00:00',
					resetTimezone: groupData.resetTimezone || 'UTC',
					window_duration: groupData.window_duration
				}));
			}
		} catch (error) {
			console.error('Error loading token groups:', error);
		}
	};

	const formatNumber = (num) => {
		if (num >= 1000000) {
			return (num / 1000000).toFixed(1) + 'M';
		} else if (num >= 1000) {
			return (num / 1000).toFixed(0) + 'K';
		}
		return num.toString();
	};

	const getProgressPercentage = (usage, limit) => {
		if (!limit) return 0;
		return Math.min((usage / limit) * 100, 100);
	};

	const getProgressColor = (percentage) => {
		if (percentage < 50) return 'bg-emerald-500';
		if (percentage < 80) return 'bg-amber-500';
		return 'bg-rose-500';
	};

	const openCreateGroupModal = () => {
		resetStrategy = 'daily';
		groupForm = {
			name: '',
			models: [],
			limit: 1000000,
			resetTime: '00:00',
			resetTimezone: 'UTC',
			windowDuration: 24
		};
		editingGroup = null;
		showCreateGroupModal = true;
	};

	const openEditGroupModal = (group) => {
		resetStrategy = group.window_duration ? 'window' : 'daily';
		groupForm = {
			name: group.name,
			models: [...(group.models || [])],
			limit: group.limit,
			resetTime: group.resetTime || '00:00',
			resetTimezone: group.resetTimezone || 'UTC',
			windowDuration: group.window_duration ? group.window_duration / 3600 : 24
		};
		editingGroup = group.name;
		showCreateGroupModal = true;
	};

	const closeModal = () => {
		showCreateGroupModal = false;
		editingGroup = null;
	};

	const saveTokenGroup = async () => {
		try {
			const url = editingGroup ? `/api/usage/groups/${editingGroup}` : '/api/usage/groups';
			const method = editingGroup ? 'PUT' : 'POST';

			const payload = {
				name: groupForm.name,
				models: groupForm.models,
				limit: groupForm.limit,
				resetTime: resetStrategy === 'daily' ? groupForm.resetTime : '00:00',
				resetTimezone: resetStrategy === 'daily' ? groupForm.resetTimezone : 'UTC',
				window_duration:
					resetStrategy === 'window' ? Math.round(groupForm.windowDuration * 3600) : null
			};

			const response = await fetch(url, {
				method,
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(payload)
			});

			if (response.ok) {
				toast.success(editingGroup ? 'Token group updated!' : 'Token group created!');
				closeModal();
				await loadTokenGroups();
				dispatch('save');
			} else {
				const error = await response.json();
				toast.error(error.detail || 'Failed to save token group');
			}
		} catch (error) {
			console.error('Error saving token group:', error);
			toast.error('Failed to save token group');
		}
	};

	const deleteTokenGroup = async (groupName) => {
		if (!confirm(`Are you sure you want to delete the "${groupName}" token group?`)) return;

		try {
			const response = await fetch(`/api/usage/groups/${groupName}`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				toast.success('Token group deleted!');
				await loadTokenGroups();
				dispatch('save');
			} else {
				const error = await response.json();
				toast.error('Failed to delete token group');
			}
		} catch (error) {
			console.error('Error deleting token group:', error);
			toast.error('Failed to delete token group');
		}
	};

	const resetUsage = async (groupName = null) => {
		const confirmMessage = groupName
			? `Reset usage for "${groupName}" token group?`
			: 'Reset usage for ALL token groups?';

		if (!confirm(confirmMessage)) return;

		try {
			const url = groupName ? `/api/usage/groups/${groupName}/reset` : '/api/usage/reset';
			const response = await fetch(url, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				toast.success('Usage reset successfully!');
				await loadTokenGroups();
			} else {
				toast.error('Failed to reset usage');
			}
		} catch (error) {
			console.error('Error resetting usage:', error);
			toast.error('Failed to reset usage');
		}
	};

	const toggleModel = (modelId) => {
		if (groupForm.models.includes(modelId)) {
			groupForm.models = groupForm.models.filter((m) => m !== modelId);
		} else {
			groupForm.models = [...groupForm.models, modelId];
		}
	};
</script>

<div class="flex flex-col h-full">
	<div class="mb-6">
		<div class="flex justify-between items-center mb-4">
			<div>
				<h2 class="text-2xl font-semibold text-gray-900 dark:text-white">Token Limits</h2>
				<p class="text-gray-600 dark:text-gray-400">
					Manage token usage limits and reset schedules for model groups
				</p>
			</div>
			<div class="flex gap-3">
				<button
					class="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
					on:click={() => resetUsage()}
				>
					Reset All Usage
				</button>
				<button
					class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
					on:click={openCreateGroupModal}
				>
					Create Token Group
				</button>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center items-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
		</div>
	{:else if tokenGroups.length === 0}
		<div class="text-center py-12">
			<p class="text-gray-500 dark:text-gray-400 mb-4">No token groups configured</p>
			<button
				class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
				on:click={openCreateGroupModal}
			>
				Create Your First Token Group
			</button>
		</div>
	{:else}
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 transition-all">
			{#each tokenGroups as group}
				<div
					class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-100 dark:border-gray-700 transition-all hover:shadow-lg"
				>
					<div class="flex justify-between items-start mb-4">
						<div>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white">{group.name}</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{#if group.window_duration}
									Rolling Window: {(group.window_duration / 3600).toFixed(1)} Hours
								{:else}
									Resets at {group.resetTime} {group.resetTimezone}
								{/if}
							</p>
						</div>
						<div class="flex gap-2">
							<button
								class="text-blue-500 hover:text-blue-700 text-sm font-medium px-2 py-1 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
								on:click={() => openEditGroupModal(group)}
							>
								Edit
							</button>
							<button
								class="text-red-500 hover:text-red-700 text-sm font-medium px-2 py-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
								on:click={() => deleteTokenGroup(group.name)}
							>
								Delete
							</button>
						</div>
					</div>

					<!-- Usage Progress Bar -->
					<div class="mb-4">
						<div class="flex justify-between items-center mb-2">
							<span class="text-sm font-medium text-gray-900 dark:text-white">Token Usage</span>
							<span class="text-sm text-gray-500 dark:text-gray-400 font-mono">
								{formatNumber(group.usage.total || 0)} / {formatNumber(group.limit || 0)}
							</span>
						</div>
						<div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 overflow-hidden">
							<div
								class="{getProgressColor(
									getProgressPercentage(group.usage.total || 0, group.limit)
								)} h-2.5 rounded-full transition-all duration-500 ease-out"
								style="width: {getProgressPercentage(group.usage.total || 0, group.limit)}%"
							></div>
						</div>
					</div>

					<!-- Token Breakdown -->
					<div class="grid grid-cols-3 gap-3 mb-4 text-center">
						<div
							class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 border border-gray-100 dark:border-gray-700"
						>
							<div class="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
								{formatNumber(group.usage.in || 0)}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mt-1"
							>
								Input
							</div>
						</div>
						<div
							class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 border border-gray-100 dark:border-gray-700"
						>
							<div class="text-lg font-semibold text-blue-600 dark:text-blue-400">
								{formatNumber(group.usage.out || 0)}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mt-1"
							>
								Output
							</div>
						</div>
						<div
							class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 border border-gray-100 dark:border-gray-700"
						>
							<div class="text-lg font-semibold text-purple-600 dark:text-purple-400">
								{formatNumber(group.usage.total || 0)}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mt-1"
							>
								Total
							</div>
						</div>
					</div>

					<!-- Models in Group -->
					<div class="mb-4">
						<h4
							class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2"
						>
							Models ({group.models?.length || 0})
						</h4>
						<div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
							{#each group.models || [] as model}
								<span
									class="px-2.5 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md text-xs font-medium border border-gray-200 dark:border-gray-600"
								>
									{model}
								</span>
							{/each}
						</div>
					</div>

					<!-- Reset Button -->
					<button
						class="w-full px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-white rounded-lg text-sm font-medium transition-colors"
						on:click={() => resetUsage(group.name)}
					>
						Reset Usage for This Group
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Create/Edit Group Modal -->
{#if showCreateGroupModal}
	<div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm p-4">
		<div
			class="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto flex flex-col border border-gray-200 dark:border-gray-700 animate-in fade-in zoom-in duration-200"
		>
			<div
				class="px-6 py-5 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center"
			>
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white">
					{editingGroup ? 'Edit' : 'Create'} Token Group
				</h3>
				<button
					on:click={closeModal}
					class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="size-5"
					>
						<path
							fill-rule="evenodd"
							d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</div>

			<div class="px-6 py-6 space-y-6 flex-1 overflow-y-auto">
				<!-- Group Name -->
				<div>
					<label class="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1.5">
						Group Name
					</label>
					<input
						bind:value={groupForm.name}
						type="text"
						class="w-full px-3 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all placeholder-gray-400 dark:placeholder-gray-500"
						placeholder="e.g., GPT-4 Models"
						disabled={!!editingGroup}
					/>
					{#if editingGroup}
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5 flex items-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-3 h-3 mr-1"
							>
								<path
									fill-rule="evenodd"
									d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
									clip-rule="evenodd"
								/>
							</svg>
							Name cannot be changed once created
						</p>
					{/if}
				</div>

				<!-- Token Limit -->
				<div>
					<label class="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1.5">
						Token Limit
					</label>
					<div class="relative">
						<input
							bind:value={groupForm.limit}
							type="number"
							class="w-full px-3 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all pr-20 placeholder-gray-400 dark:placeholder-gray-500"
							placeholder="1000000"
							min="1"
						/>
						<div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
							<span class="text-gray-500 dark:text-gray-400 text-sm font-medium">tokens</span>
						</div>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
						Approx. {formatNumber(groupForm.limit)} tokens
					</p>
				</div>

				<div class="border-t border-gray-100 dark:border-gray-700 pt-4">
					<label class="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
						Reset Strategy
					</label>

					<div class="grid grid-cols-2 gap-2 bg-gray-100 dark:bg-gray-800 p-1.5 rounded-xl mb-4">
						<button
							class="py-2 text-sm font-medium rounded-lg transition-all {resetStrategy === 'daily'
								? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm ring-1 ring-gray-200 dark:ring-gray-600'
								: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-200/50 dark:hover:bg-gray-700/50'}"
							on:click={() => (resetStrategy = 'daily')}
						>
							Daily Reset
						</button>
						<button
							class="py-2 text-sm font-medium rounded-lg transition-all {resetStrategy === 'window'
								? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm ring-1 ring-gray-200 dark:ring-gray-600'
								: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-200/50 dark:hover:bg-gray-700/50'}"
							on:click={() => (resetStrategy = 'window')}
						>
							Rolling Window
						</button>
					</div>

					{#if resetStrategy === 'daily'}
						<!-- Reset Schedule -->
						<div class="grid grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-2 duration-200">
							<div>
								<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
									Reset Time
								</label>
								<input
									bind:value={groupForm.resetTime}
									type="time"
									class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
								/>
							</div>
							<div>
								<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
									Timezone
								</label>
								<div class="relative">
									<select
										bind:value={groupForm.resetTimezone}
										class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500/50 outline-none appearance-none transition-all"
									>
										{#each timezoneOptions as timezone}
											<option value={timezone}>{timezone}</option>
										{/each}
									</select>
									<div
										class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-gray-500"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
								</div>
							</div>
						</div>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 flex items-start gap-1.5">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-3.5 h-3.5 mt-0.5 shrink-0"
							>
								<path
									fill-rule="evenodd"
									d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
									clip-rule="evenodd"
								/>
							</svg>
							<span
								>Tokens reset automatically every day at {groupForm.resetTime}
								{groupForm.resetTimezone}.</span
							>
						</p>
					{:else}
						<!-- Rolling Window -->
						<div class="animate-in fade-in slide-in-from-top-2 duration-200">
							<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
								Window Duration (Hours)
							</label>
							<div class="relative">
								<input
									bind:value={groupForm.windowDuration}
									type="number"
									min="1"
									class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500/50 outline-none transition-all pr-16"
								/>
								<div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
									<span class="text-gray-500 dark:text-gray-400 text-sm font-medium">hours</span>
								</div>
							</div>
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 flex items-start gap-1.5">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3.5 h-3.5 mt-0.5 shrink-0"
								>
									<path
										fill-rule="evenodd"
										d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
										clip-rule="evenodd"
									/>
								</svg>
								<span
									>Usage resets individually for each user {groupForm.windowDuration} hours after their
									first request in the window.</span
								>
							</p>
						</div>
					{/if}
				</div>

				<!-- Model Selection -->
				<div>
					<div class="flex justify-between items-center mb-2">
						<label class="block text-sm font-semibold text-gray-900 dark:text-gray-100">
							Select Models
						</label>
						<span
							class="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300 px-2 py-0.5 rounded-full font-medium"
						>
							{groupForm.models.length} selected
						</span>
					</div>

					<div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
						<div
							class="max-h-48 overflow-y-auto bg-gray-50 dark:bg-gray-800 p-1 space-y-0.5 custom-scrollbar"
						>
							{#if availableModels.length === 0}
								<div
									class="text-sm text-gray-500 dark:text-gray-400 py-8 text-center flex flex-col items-center gap-2"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="size-6 opacity-50"
									>
										<path
											fill-rule="evenodd"
											d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
											clip-rule="evenodd"
										/>
									</svg>
									{#if loading}
										<div class="animate-pulse">Loading available models...</div>
									{:else}
										No models detected.
									{/if}
								</div>
							{:else}
								{#each availableModels as model}
									<label
										class="flex items-center p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer group transition-colors select-none"
									>
										<input
											type="checkbox"
											class="rounded border-gray-300 text-blue-600 shadow-sm focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:checked:bg-blue-500"
											checked={groupForm.models.includes(model.id)}
											on:change={() => toggleModel(model.id)}
										/>
										<div class="ml-3 flex flex-col">
											<span
												class="text-sm font-medium text-gray-700 dark:text-gray-200 group-hover:text-gray-900 dark:group-hover:text-white transition-colors"
											>
												{model.name || model.id}
											</span>
											<span class="text-[10px] text-gray-500 font-mono">{model.id}</span>
										</div>
									</label>
								{/each}
							{/if}
						</div>
					</div>
				</div>
			</div>

			<div
				class="px-6 py-5 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 flex justify-end gap-3 rounded-b-xl"
			>
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
					on:click={closeModal}
				>
					Cancel
				</button>
				<button
					class="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm shadow-blue-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-md"
					on:click={saveTokenGroup}
					disabled={!groupForm.name || groupForm.models.length === 0}
				>
					{editingGroup ? 'Save Changes' : 'Create Group'}
				</button>
			</div>
		</div>
	</div>
{/if}
