<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { user } from '$lib/stores';
	import { getUserSubmissions, type UserSubmissionsResponse } from '$lib/apis/workflow';
import { getAllUsers } from '$lib/apis/users';

	// State
	let selectedUserId: string = '';
	let submissionsData: UserSubmissionsResponse | null = null;
	let users: any[] = [];
	let loading = false;
 let error: string = '';

	// Panel states
	let showChildProfiles = true;
	let showModerationSessions = true;
	let showExitQuizResponses = true;

	// Helpers to support multi-session displays (session_number optional)
	const getSessionNumber = (obj: any) => Number(obj?.session_number);

	const groupModerationBySession = (sessions: any[]) => {
		const bySession: Record<string, any[]> = {};
		for (const s of sessions || []) {
			const sn = getSessionNumber(s);
			if (!Number.isFinite(sn)) continue; // require session_number
			const key = String(sn);
			(bySession[key] ||= []).push(s);
		}
		// Sort sessions numerically descending (latest first)
		return Object.entries(bySession)
			.sort((a, b) => Number(b[0]) - Number(a[0]))
			.map(([sessionKey, list]) => ({
				session_number: Number(sessionKey),
				items: list.sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0))
			}));
	};

	const groupWithinSessionByScenario = (items: any[]) => {
		const byScenario: Record<string, any[]> = {};
		for (const s of items) {
			const scenarioKey = `${s.child_id || 'unknown'}::${s.scenario_index ?? -1}`;
			(byScenario[scenarioKey] ||= []).push(s);
		}
		return Object.entries(byScenario).map(([k, list]) => {
			const [child_id, scenario_index] = k.split('::');
			return {
				child_id,
				scenario_index: Number(scenario_index),
				versions: list.sort((a, b) => (a.version_number ?? 0) - (b.version_number ?? 0))
			};
		});
	};

		onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}

		try {
			// Load all users for dropdown
			const token = localStorage.getItem('token');
			if (token) {
				const usersResponse = await getAllUsers(token);
				users = usersResponse?.users || [];
			}
		} catch (err) {
			console.error('Error loading users:', err);
			toast.error('Failed to load users');
		}
	});

	const loadUserSubmissions = async () => {
		if (!selectedUserId) return;

		loading = true;
    error = '';
		submissionsData = null;

		try {
			const token = localStorage.getItem('token');
			if (token) {
				submissionsData = await getUserSubmissions(token, selectedUserId);
				toast.success('User submissions loaded successfully');
			}
    } catch (err: any) {
      error = err?.message || 'Failed to load user submissions';
			toast.error(error);
		} finally {
			loading = false;
		}
	};

	const exportData = () => {
		if (!submissionsData) return;

		const dataStr = JSON.stringify(submissionsData, null, 2);
		const blob = new Blob([dataStr], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `user-${selectedUserId}-submissions-${Date.now()}.json`;
		a.click();
		URL.revokeObjectURL(url);
		toast.success('Data exported successfully');
	};

	const formatTimestamp = (timestamp: number) => {
		if (!timestamp) return '';
		// Detect unit: ns (~1e18), ms (~1e12), s (~1e9)
		let ts = Number(timestamp);
		if (!Number.isFinite(ts)) return '';
		if (ts > 1e15) {
			// nanoseconds -> milliseconds
			ts = Math.floor(ts / 1e6);
		} else if (ts > 1e12) {
			// already milliseconds
			// leave as is
		} else if (ts > 1e10) {
			// microseconds -> milliseconds
			ts = Math.floor(ts / 1e3);
		} else if (ts > 1e9) {
			// seconds -> milliseconds
			ts = ts * 1000;
		}
		return new Date(ts).toLocaleString();
	};

	const getSelectedUser = () => {
		return users.find(u => u.id === selectedUserId);
	};
</script>

<svelte:head>
	<title>Admin Submissions • Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-screen max-h-[100dvh] flex-1">
	<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">User Submissions</h1>
				<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
					View child profiles, moderation responses, and exit quiz data for any user
				</p>
			</div>
			{#if submissionsData}
				<button
					on:click={exportData}
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
				>
					Export Data
				</button>
			{/if}
		</div>
	</div>

	<div class="flex-1 overflow-auto p-6">
		<!-- User Selection -->
		<div class="mb-6">
			<label for="user-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
				Select User
			</label>
			<div class="flex gap-4">
				<select
					id="user-select"
					bind:value={selectedUserId}
					on:change={loadUserSubmissions}
					class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
				>
					<option value="">Choose a user...</option>
					{#each users as user}
						<option value={user.id}>{user.name} ({user.email})</option>
					{/each}
				</select>
				{#if selectedUserId}
					<button
						on:click={loadUserSubmissions}
						disabled={loading}
						class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
					>
						{loading ? 'Loading...' : 'Load Data'}
					</button>
				{/if}
			</div>
		</div>

		{#if error}
			<div class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
				<p class="text-red-800 dark:text-red-200">{error}</p>
			</div>
		{/if}

		{#if submissionsData}
			<!-- User Info -->
			<div class="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">User Information</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<div>
						<span class="text-sm text-gray-600 dark:text-gray-400">Name:</span>
						<p class="font-medium text-gray-900 dark:text-white">{submissionsData.user_info.name}</p>
					</div>
					<div>
						<span class="text-sm text-gray-600 dark:text-gray-400">Email:</span>
						<p class="font-medium text-gray-900 dark:text-white">{submissionsData.user_info.email}</p>
					</div>
					<div>
						<span class="text-sm text-gray-600 dark:text-gray-400">User ID:</span>
						<p class="font-medium text-gray-900 dark:text-white font-mono text-sm">{submissionsData.user_info.id}</p>
					</div>
				</div>
			</div>

			<!-- Child Profiles Panel -->
			<div class="mb-6">
				<button
					on:click={() => showChildProfiles = !showChildProfiles}
					class="w-full flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						Child Profiles ({submissionsData.child_profiles.length})
					</h2>
					<span class="text-gray-500 dark:text-gray-400">
						{showChildProfiles ? '▼' : '▶'}
					</span>
				</button>
				
				{#if showChildProfiles}
					<div class="mt-2 space-y-4">
						{#if submissionsData.child_profiles.length === 0}
							<p class="text-gray-500 dark:text-gray-400 italic">No child profiles found</p>
						{:else}
							{#each submissionsData.child_profiles as profile}
								<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
									<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Name:</span>
											<p class="font-medium text-gray-900 dark:text-white">{profile.name}</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Age:</span>
											<p class="text-gray-900 dark:text-white">{profile.child_age || 'Not specified'}</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Gender:</span>
											<p class="text-gray-900 dark:text-white">{profile.child_gender || 'Not specified'}</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Attempt:</span>
											<p class="text-gray-900 dark:text-white">{profile.attempt_number}</p>
										</div>
										{#if profile.child_characteristics}
											<div class="md:col-span-2">
												<span class="text-sm text-gray-600 dark:text-gray-400">Characteristics:</span>
												<p class="text-gray-900 dark:text-white">{profile.child_characteristics}</p>
											</div>
										{/if}
										{#if profile.parenting_style}
											<div class="md:col-span-2">
												<span class="text-sm text-gray-600 dark:text-gray-400">Parenting Style:</span>
												<p class="text-gray-900 dark:text-white">{profile.parenting_style}</p>
											</div>
										{/if}
										<div class="md:col-span-2">
											<span class="text-sm text-gray-600 dark:text-gray-400">Created:</span>
											<p class="text-gray-900 dark:text-white">{formatTimestamp(profile.created_at)}</p>
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				{/if}
			</div>

			<!-- Moderation Sessions Panel (supports multi-session) -->
			<div class="mb-6">
				<button
					on:click={() => showModerationSessions = !showModerationSessions}
					class="w-full flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						Moderation Sessions ({submissionsData.moderation_sessions.length})
					</h2>
					<span class="text-gray-500 dark:text-gray-400">
						{showModerationSessions ? '▼' : '▶'}
					</span>
				</button>
				{#if showModerationSessions}
					<div class="mt-2 space-y-3">
						{#if submissionsData.moderation_sessions.length === 0}
							<p class="text-gray-500 dark:text-gray-400 italic">No moderation sessions found</p>
						{:else}
							{#each groupModerationBySession(submissionsData.moderation_sessions) as sessionBlock}
								<div class="border border-gray-200 dark:border-gray-700 rounded-lg">
									<div class="px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-t-lg flex items-center justify-between">
										<div class="flex items-center gap-2">
											<span class="text-sm text-gray-600 dark:text-gray-300">Session</span>
											<span class="px-2 py-0.5 text-xs rounded bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200">{sessionBlock.session_number}</span>
										</div>
										<div class="text-xs text-gray-500 dark:text-gray-400">{sessionBlock.items.length} rows</div>
									</div>
									<div class="p-3 space-y-3">
										{#each groupWithinSessionByScenario(sessionBlock.items) as group}
											<div class="rounded border border-gray-100 dark:border-gray-800">
												<div class="px-3 py-2 bg-white dark:bg-gray-900 flex items-center justify-between">
													<div class="flex items-center gap-3">
														<span class="text-xs text-gray-500 dark:text-gray-400">Child</span>
														<span class="font-mono text-xs">{group.child_id}</span>
														<span class="text-xs text-gray-500 dark:text-gray-400">Scenario</span>
														<span class="text-sm">{group.scenario_index}</span>
													</div>
												</div>
												<div class="overflow-x-auto">
													<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
														<thead class="text-xs text-gray-700 dark:text-gray-300 uppercase bg-gray-50 dark:bg-gray-800">
															<tr>
																<th class="px-3 py-2">Attempt</th>
																<th class="px-3 py-2">Version</th>
																<th class="px-3 py-2">Decision</th>
																<th class="px-3 py-2">Final</th>
																<th class="px-3 py-2">Created</th>
														</tr>
													</thead>
													<tbody>
														{#each group.versions as row}
															<tr class="bg-white dark:bg-gray-900 border-t dark:border-gray-800">
																<td class="px-3 py-2">{row.attempt_number}</td>
																<td class="px-3 py-2">{row.version_number}</td>
																<td class="px-3 py-2">{row.initial_decision || 'N/A'}</td>
																<td class="px-3 py-2">
																	{#if row.is_final_version}
																		<span class="px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded">Final</span>
																	{:else}
																		<span class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded">Draft</span>
																	{/if}
																</td>
																<td class="px-3 py-2">{formatTimestamp(row.created_at)}</td>
															</tr>
														{/each}
													</tbody>
												</table>
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/each}
						{/if}
					</div>
				{/if}
			</div>

			<!-- Exit Quiz Responses Panel -->
			<div class="mb-6">
				<button
					on:click={() => showExitQuizResponses = !showExitQuizResponses}
					class="w-full flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						Exit Quiz Responses ({submissionsData.exit_quiz_responses.length})
					</h2>
					<span class="text-gray-500 dark:text-gray-400">
						{showExitQuizResponses ? '▼' : '▶'}
					</span>
				</button>
				
				{#if showExitQuizResponses}
					<div class="mt-2 space-y-4">
						{#if submissionsData.exit_quiz_responses.length === 0}
							<p class="text-gray-500 dark:text-gray-400 italic">No exit quiz responses found</p>
						{:else}
							{#each submissionsData.exit_quiz_responses as response}
								<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
									<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Child ID:</span>
											<p class="font-mono text-sm text-gray-900 dark:text-white">{response.child_id}</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Attempt:</span>
											<p class="text-gray-900 dark:text-white">{response.attempt_number}</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Created:</span>
											<p class="text-gray-900 dark:text-white">{formatTimestamp(response.created_at)}</p>
										</div>
									</div>
									
									{#if response.score}
										<div class="mb-4">
											<span class="text-sm text-gray-600 dark:text-gray-400">Score:</span>
											<pre class="mt-1 p-2 bg-white dark:bg-gray-900 rounded text-xs overflow-x-auto">{JSON.stringify(response.score, null, 2)}</pre>
										</div>
									{/if}
									
									<div class="mb-4">
										<span class="text-sm text-gray-600 dark:text-gray-400">Answers:</span>
										<pre class="mt-1 p-2 bg-white dark:bg-gray-900 rounded text-xs overflow-x-auto">{JSON.stringify(response.answers, null, 2)}</pre>
									</div>
									
									{#if response.meta}
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Metadata:</span>
											<pre class="mt-1 p-2 bg-white dark:bg-gray-900 rounded text-xs overflow-x-auto">{JSON.stringify(response.meta, null, 2)}</pre>
										</div>
									{/if}
								</div>
							{/each}
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
