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
	let groupForm = {
		name: '',
		models: [],
		limit: 1000000,
		resetTime: '00:00',
		resetTimezone: 'UTC'
	};

	// Scheduling Options
	const timezoneOptions = [
		'UTC', 'EST', 'PST', 'GMT', 'CET', 'JST', 'CST', 'MST'
	];

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
		console.log('🔍 ModelLimits: Available models loaded:', availableModels.length, availableModels.slice(0, 3));
	}

	const loadTokenGroups = async () => {
		try {
			const response = await fetch('/api/usage/groups', {
				headers: {
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				}
			});
			
			if (response.ok) {
				const data = await response.json();
				tokenGroups = Object.entries(data.groups || {}).map(([name, groupData]) => ({
					name,
					...groupData,
					resetTime: groupData.resetTime || '00:00',
					resetTimezone: groupData.resetTimezone || 'UTC'
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
		if (percentage < 50) return 'bg-green-500';
		if (percentage < 80) return 'bg-yellow-500';
		return 'bg-red-500';
	};

	const openCreateGroupModal = () => {
		console.log('🔍 ModelLimits: Opening create modal, available models:', availableModels.length);
		groupForm = {
			name: '',
			models: [],
			limit: 1000000,
			resetTime: '00:00',
			resetTimezone: 'UTC'
		};
		editingGroup = null;
		showCreateGroupModal = true;
	};

	const openEditGroupModal = (group) => {
		console.log('🔍 ModelLimits: Opening edit modal, available models:', availableModels.length, 'group models:', group.models);
		groupForm = {
			name: group.name,
			models: [...(group.models || [])],
			limit: group.limit,
			resetTime: group.resetTime || '00:00',
			resetTimezone: group.resetTimezone || 'UTC'
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
			
			const response = await fetch(url, {
				method,
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify({
					name: groupForm.name,
					models: groupForm.models,
					limit: groupForm.limit,
					resetTime: groupForm.resetTime,
					resetTimezone: groupForm.resetTimezone
				})
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
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				toast.success('Token group deleted!');
				await loadTokenGroups();
				dispatch('save');
			} else {
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
					'Authorization': `Bearer ${localStorage.getItem('token')}`
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
			groupForm.models = groupForm.models.filter(m => m !== modelId);
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
				<p class="text-gray-600 dark:text-gray-400">Manage token usage limits and reset schedules for model groups</p>
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
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			{#each tokenGroups as group}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
					<div class="flex justify-between items-start mb-4">
						<div>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white">{group.name}</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								Resets at {group.resetTime} {group.resetTimezone}
							</p>
						</div>
						<div class="flex gap-2">
							<button
								class="text-blue-500 hover:text-blue-700 text-sm"
								on:click={() => openEditGroupModal(group)}
							>
								Edit
							</button>
							<button
								class="text-red-500 hover:text-red-700 text-sm"
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
							<span class="text-sm text-gray-500 dark:text-gray-400">
								{formatNumber(group.usage.total || 0)} / {formatNumber(group.limit || 0)}
							</span>
						</div>
						<div class="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
							<div 
								class="{getProgressColor(getProgressPercentage(group.usage.total || 0, group.limit))} h-2 rounded-full transition-all duration-300"
								style="width: {getProgressPercentage(group.usage.total || 0, group.limit)}%"
							></div>
						</div>
					</div>

					<!-- Token Breakdown -->
					<div class="grid grid-cols-3 gap-3 mb-4 text-center">
						<div class="bg-gray-50 dark:bg-gray-700 rounded p-3">
							<div class="text-lg font-semibold text-green-600">{formatNumber(group.usage.in || 0)}</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">Input</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700 rounded p-3">
							<div class="text-lg font-semibold text-blue-600">{formatNumber(group.usage.out || 0)}</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">Output</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700 rounded p-3">
							<div class="text-lg font-semibold text-purple-600">{formatNumber(group.usage.total || 0)}</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">Total</div>
						</div>
					</div>

					<!-- Models in Group -->
					<div class="mb-4">
						<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">Models ({group.models?.length || 0})</h4>
						<div class="flex flex-wrap gap-1">
							{#each (group.models || []) as model}
								<span class="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-xs">
									{model}
								</span>
							{/each}
						</div>
					</div>

					<!-- Reset Button -->
					<button
						class="w-full px-3 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
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
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
			<div class="px-6 py-4 border-b dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
					{editingGroup ? 'Edit' : 'Create'} Token Group
				</h3>
			</div>
			
			<div class="px-6 py-4 space-y-6">
				<!-- Group Name -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Group Name
					</label>
					<input
						bind:value={groupForm.name}
						type="text"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						placeholder="e.g., GPT-4 Models"
						disabled={editingGroup}
					/>
				</div>

				<!-- Token Limit -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Token Limit
					</label>
					<input
						bind:value={groupForm.limit}
						type="number"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						placeholder="1000000"
						min="1"
					/>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Current: {formatNumber(groupForm.limit)} tokens
					</p>
				</div>

				<!-- Reset Schedule -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Reset Time
						</label>
						<input
							bind:value={groupForm.resetTime}
							type="time"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Timezone
						</label>
						<select
							bind:value={groupForm.resetTimezone}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						>
							{#each timezoneOptions as timezone}
								<option value={timezone}>{timezone}</option>
							{/each}
						</select>
					</div>
				</div>

				<!-- Model Selection -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Select Models ({groupForm.models.length} selected)
					</label>
					<div class="max-h-48 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-md p-3 space-y-2">
						{#if availableModels.length === 0}
							<div class="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
								{#if loading}
									Loading models...
								{:else}
									No models available. Make sure you have models configured in your OpenWebUI instance.
								{/if}
							</div>
						{:else}
							{#each availableModels as model}
								<label class="flex items-center">
									<input
										type="checkbox"
										class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
										checked={groupForm.models.includes(model.id)}
										on:change={() => toggleModel(model.id)}
									/>
									<span class="ml-2 text-sm text-gray-900 dark:text-white">{model.name || model.id}</span>
								</label>
							{/each}
						{/if}
					</div>
				</div>
			</div>

			<div class="px-6 py-4 border-t dark:border-gray-700 flex justify-end gap-3">
				<button
					class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors"
					on:click={closeModal}
				>
					Cancel
				</button>
				<button
					class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
					on:click={saveTokenGroup}
					disabled={!groupForm.name || groupForm.models.length === 0}
				>
					{editingGroup ? 'Update' : 'Create'} Group
				</button>
			</div>
		</div>
	</div>
{/if}