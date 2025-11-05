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



	// State for expanded dropdowns/accordions
	let expandedScenarios: Record<string, boolean> = {};
	let expandedVersions: Record<string, boolean> = {};
	
	// Force reactivity with a counter
	let expansionCounter = 0;

	// Custom scenario detection
	const CUSTOM_SCENARIO_MARKER = "[Create Your Own Scenario]";

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

	const groupWithinSessionByChild = (items: any[], childProfiles: any[]) => {
		// Group by child first
		const byChild: Record<string, any[]> = {};
		for (const s of items) {
			const childId = s.child_id || 'unknown';
			(byChild[childId] ||= []).push(s);
		}
		
		return Object.entries(byChild).map(([childId, sessions]) => {
			// Lookup child name from profiles
			const profile = childProfiles.find((p: any) => p.id === childId);
			const childName = profile?.name || 'Unknown';
			
			// Then group by scenario within this child
			const byScenario: Record<string, any[]> = {};
			for (const s of sessions) {
				const scenarioKey = `${s.scenario_index ?? -1}`;
				(byScenario[scenarioKey] ||= []).push(s);
			}
			
			const scenarios = Object.entries(byScenario).map(([k, list]) => {
				const scenarioIndex = Number(k);
				return {
					scenario_index: scenarioIndex,
					versions: list.sort((a, b) => (a.version_number ?? 0) - (b.version_number ?? 0)),
					// Get first version's prompt and response (all should be same)
					scenario_prompt: list[0]?.scenario_prompt || '',
					original_response: list[0]?.original_response || ''
				};
			});
			
		return {
			child_id: childId,
			child_name: childName,
			scenarios: scenarios.sort((a, b) => a.scenario_index - b.scenario_index)
		};
	});
};

const isCustomScenario = (scenarioIndex: number, allScenarios: any[]) => {
	// Custom scenarios are always the last scenario in the list
	// They are typically at index 8 (after 8 personality-based scenarios)
	// but can be at higher indices if there are more scenarios
	if (allScenarios.length === 0) return false;
	const maxIndex = Math.max(...allScenarios.map(s => s.scenario_index));
	return scenarioIndex === maxIndex;
};

function toggleScenarioDropdown(childId: string, scenarioIndex: number) {
		const key = `${childId}::${scenarioIndex}`;
		const currentValue = expandedScenarios[key];
		expandedScenarios = { ...expandedScenarios, [key]: !currentValue };
		expansionCounter++;
	}

	function isScenarioExpanded(childId: string, scenarioIndex: number) {
		const key = `${childId}::${scenarioIndex}`;
		return expandedScenarios[key] === true;
	}

	function toggleVersionAccordion(versionId: string) {
		const currentValue = expandedVersions[versionId];
		expandedVersions = { ...expandedVersions, [versionId]: !currentValue };
		expansionCounter++;
	}

	function isVersionExpanded(versionId: string) {
		return expandedVersions[versionId] === true;
	}

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

	const getAttentionCheckStats = (scenarios: any[]) => {
		const attentionChecks = scenarios.flatMap(s => s.versions)
			.filter(v => v.is_attention_check);
		const passed = attentionChecks.filter(v => v.attention_check_passed).length;
		return { total: attentionChecks.length, passed };
	};

	const parseExitQuizAnswers = (answers: any) => {
		if (!answers) return null;
		
		// Helper to format parenting style
		const formatParentingStyle = (style: string) => {
			if (!style) return 'Not answered';
			const styles: Record<string, string> = {
				'A': 'I set clear rules and follow through, but I explain my reasons, listen to my child\'s point of view, and encourage independence.',
				'B': 'I set strict rules and expect obedience; I rarely negotiate and use firm consequences when rules aren\'t followed.',
				'C': 'I\'m warm and supportive with few rules or demands; my child mostly sets their own routines and limits.',
				'D': 'I give my child a lot of freedom and usually take a hands-off approach unless safety or basic needs require me to step in.',
				'E': 'None of these fits me / It depends on the situation.',
				// Legacy values for backward compatibility
				'authoritative': 'I set clear rules and follow through, but I explain my reasons, listen to my child\'s point of view, and encourage independence.',
				'authoritarian': 'I set strict rules and expect obedience; I rarely negotiate and use firm consequences when rules aren\'t followed.',
				'permissive': 'I\'m warm and supportive with few rules or demands; my child mostly sets their own routines and limits.',
				'neglectful': 'I give my child a lot of freedom and usually take a hands-off approach unless safety or basic needs require me to step in.'
			};
			return styles[style] || style;
		};
		
		return {
			genai_familiarity: answers['1'] || answers['genaiFamiliarity'] || answers['genai_familiarity'] || 'Not answered',
			usage_frequency: answers['2'] || answers['genaiUsageFrequency'] || answers['usage_frequency'] || 'Not answered',
			parenting_style: formatParentingStyle(answers['parentingStyle'] || answers['parenting_style']),
			raw: answers
		};
	};

	const formatTimeSpent = (ms: number) => {
		if (!ms || ms === 0) return 'No data';
		const totalSeconds = Math.floor(ms / 1000);
		const hours = Math.floor(totalSeconds / 3600);
		const minutes = Math.floor((totalSeconds % 3600) / 60);
		const seconds = totalSeconds % 60;
		
		if (hours > 0) {
			return `${hours}h ${minutes}m ${seconds}s`;
		} else if (minutes > 0) {
			return `${minutes}m ${seconds}s`;
		} else {
			return `${seconds}s`;
		}
	};

	const getSessionTime = (userId: string, childId: string, sessionNumber: number) => {
		if (!submissionsData?.session_activity_totals) return 0;
		const key = `${userId}::${childId}::${sessionNumber}`;
		return submissionsData.session_activity_totals[key] || 0;
	};

	const getAssignmentTime = (userId: string, childId: string, attemptNumber: number) => {
		if (!submissionsData?.assignment_time_totals) return 0;
		const key = `${userId}::${childId}::${attemptNumber}`;
		return submissionsData.assignment_time_totals[key] || 0;
	};

	const getTotalSessionAssignmentTime = (sessionNumber: number) => {
		if (!submissionsData?.assignment_time_totals) return 0;
		let total = 0;
		// Sum all assignment times for this session across all children
		for (const [key, ms] of Object.entries(submissionsData.assignment_time_totals)) {
			const [userId, childId, attempt] = key.split('::');
			if (Number(attempt) === sessionNumber) {
				total += ms;
			}
		}
		return total;
	};

	const getSessionAssignmentTimeByChild = (sessionNumber: number) => {
		if (!submissionsData?.assignment_time_totals) return {};
		const byChild: Record<string, number> = {};
		for (const [key, ms] of Object.entries(submissionsData.assignment_time_totals)) {
			const [userId, childId, attempt] = key.split('::');
			if (Number(attempt) === sessionNumber) {
				byChild[childId] = ms;
			}
		}
		return byChild;
	};

	const groupAllDataBySession = () => {
		if (!submissionsData) return [];
		
		// Get all unique session numbers from moderation sessions
		const sessionNumbers = new Set<number>();
		submissionsData.moderation_sessions.forEach(s => {
			const sn = getSessionNumber(s);
			if (Number.isFinite(sn)) sessionNumbers.add(sn);
		});
		
		// Also check child profiles and exit quiz for session numbers
		submissionsData.child_profiles.forEach(p => {
			if (p.session_number) sessionNumbers.add(Number(p.session_number));
		});
		
		// Sort sessions descending (latest first)
		const sortedSessions = Array.from(sessionNumbers).sort((a, b) => b - a);
		
		return sortedSessions.map(sessionNum => {
			// Get child profiles for this session
			const childProfiles = submissionsData.child_profiles.filter(
				p => Number(p.session_number) === sessionNum
			);
			
			// Get moderation sessions for this session
			const moderationSessions = submissionsData.moderation_sessions.filter(
				s => getSessionNumber(s) === sessionNum
			);
			
			// Get exit quiz responses for this session (match by child_id and attempt_number)
			const exitQuizResponses = submissionsData.exit_quiz_responses.filter(
				r => {
					// Match if the child profile exists in this session and attempt matches
					return childProfiles.some(p => 
						p.id === r.child_id && Number(r.attempt_number) === sessionNum
					);
				}
			);
			
			return {
				session_number: sessionNum,
				child_profiles: childProfiles,
				moderation_sessions: moderationSessions,
				exit_quiz_responses: exitQuizResponses
			};
		});
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

			<!-- Sessions Grouped View -->
			<div class="space-y-6">
				{#each groupAllDataBySession() as sessionData}
					{@const totalAssignmentTime = getTotalSessionAssignmentTime(sessionData.session_number)}
					{@const assignmentTimeByChild = getSessionAssignmentTimeByChild(sessionData.session_number)}
					
					<div class="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
						<!-- Session Header -->
						<div class="px-6 py-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 border-b border-gray-300 dark:border-gray-600">
							<div class="flex items-center justify-between">
								<h2 class="text-xl font-bold text-gray-900 dark:text-white">
									Session {sessionData.session_number}
								</h2>
								<div class="flex items-center gap-3">
									<!-- Total Assignment Time Badge -->
									<div class="px-3 py-1.5 bg-blue-100 dark:bg-blue-900 rounded-lg">
										<span class="text-xs font-semibold text-blue-800 dark:text-blue-200">
											Total Assignment Time: {formatTimeSpent(totalAssignmentTime)}
										</span>
									</div>
								</div>
							</div>
							
							<!-- Per-Child Assignment Time Breakdown -->
							{#if Object.keys(assignmentTimeByChild).length > 0}
								<div class="mt-3 flex flex-wrap gap-2">
									{#each Object.entries(assignmentTimeByChild) as [childId, ms]}
										{@const childProfile = sessionData.child_profiles.find(p => p.id === childId)}
										<span class="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded">
											{childProfile?.name || childId}: {formatTimeSpent(ms)}
										</span>
									{/each}
								</div>
							{/if}
						</div>
						
						<!-- Session Content -->
						<div class="p-6 space-y-6">
							<!-- Child Profiles in this session -->
							<div>
								<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
									Child Profiles ({sessionData.child_profiles.length})
								</h3>
								{#if sessionData.child_profiles.length === 0}
									<p class="text-gray-500 dark:text-gray-400 italic">No child profiles in this session</p>
								{:else}
									<div class="space-y-3">
										{#each sessionData.child_profiles as profile}
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
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Session:</span>
											<p class="text-gray-900 dark:text-white">{profile.session_number}</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Only Child:</span>
											<p class="text-gray-900 dark:text-white">
												{profile.is_only_child === true ? 'Yes' : profile.is_only_child === false ? 'No' : 'Not specified'}
											</p>
										</div>
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Child AI Use:</span>
											<p class="text-gray-900 dark:text-white">{profile.child_has_ai_use || 'Not specified'}</p>
										</div>
										{#if profile.child_ai_use_contexts && profile.child_ai_use_contexts.length > 0}
											<div class="md:col-span-2">
												<span class="text-sm text-gray-600 dark:text-gray-400">AI Use Contexts:</span>
												<p class="text-gray-900 dark:text-white">{profile.child_ai_use_contexts.join(', ')}</p>
											</div>
										{/if}
										<div>
											<span class="text-sm text-gray-600 dark:text-gray-400">Parent Monitoring Level:</span>
											<p class="text-gray-900 dark:text-white">{profile.parent_llm_monitoring_level || 'Not specified'}</p>
										</div>
										{#if profile.child_characteristics}
											<div class="md:col-span-2">
												<span class="text-sm text-gray-600 dark:text-gray-400">Characteristics:</span>
												<p class="text-gray-900 dark:text-white">{profile.child_characteristics}</p>
											</div>
										{/if}
										<div class="md:col-span-2">
											<span class="text-sm text-gray-600 dark:text-gray-400">Created:</span>
											<p class="text-gray-900 dark:text-white">{formatTimestamp(profile.created_at)}</p>
										</div>
									</div>
								</div>
							{/each}
									</div>
								{/if}
							</div>
							
							<!-- Moderation Sessions in this session -->
							<div>
								<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
									Moderation Scenarios ({sessionData.moderation_sessions.length})
								</h3>
								{#if sessionData.moderation_sessions.length === 0}
									<p class="text-gray-500 dark:text-gray-400 italic">No moderation sessions</p>
								{:else}
									<div class="mt-2 space-y-4">
										{#each groupWithinSessionByChild(sessionData.moderation_sessions, sessionData.child_profiles) as childGroup}
											{@const attnStats = getAttentionCheckStats(childGroup.scenarios)}
											{@const timeSpent = getSessionTime(submissionsData.user_info.id, childGroup.child_id, sessionData.session_number)}
											<div class="rounded border border-gray-200 dark:border-gray-700">
												<div class="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 flex items-center justify-between">
													<div class="flex items-center gap-2">
														<span class="text-sm font-semibold text-gray-900 dark:text-white">Child: {childGroup.child_name} ({childGroup.child_id})</span>
														<span class="px-2 py-0.5 text-xs rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
															⏱️ {formatTimeSpent(timeSpent)}
														</span>
														{#if attnStats.total > 0}
															{#if attnStats.passed === attnStats.total}
																<span class="px-2 py-0.5 text-xs rounded bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
																	Attention: {attnStats.passed}/{attnStats.total} passed
																</span>
															{:else}
																<span class="px-2 py-0.5 text-xs rounded bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200">
																	Attention: {attnStats.passed}/{attnStats.total} passed
																</span>
															{/if}
														{/if}
													</div>
												</div>
												<div class="p-3 space-y-3">
													{#each childGroup.scenarios as scenario}
														<div class="rounded border border-gray-200 dark:border-gray-700">
															<div class="px-3 py-2 bg-white dark:bg-gray-900 flex items-center justify-between">
																<div class="flex items-center gap-3 flex-1 min-w-0">
																	<div class="flex items-center gap-2">
																		<span class="text-sm font-medium text-gray-900 dark:text-white">Scenario {scenario.scenario_index}</span>
																		{#if isCustomScenario(scenario.scenario_index, childGroup.scenarios)}
																			<span class="px-2 py-0.5 text-xs rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
																				Custom
																			</span>
																		{/if}
																	</div>
																	{#if scenario.scenario_prompt}
																		<span class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md">
																			{scenario.scenario_prompt.substring(0, 80)}{scenario.scenario_prompt.length > 80 ? '...' : ''}
																		</span>
																	{/if}
																</div>
																<button
																	on:click={() => toggleScenarioDropdown(childGroup.child_id, scenario.scenario_index)}
																	class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-xs whitespace-nowrap ml-2"
																>
																	{isScenarioExpanded(childGroup.child_id, scenario.scenario_index) ? '▼' : '▶'} View Full Prompt
																</button>
															</div>
															{#if isScenarioExpanded(childGroup.child_id, scenario.scenario_index) && expansionCounter >= 0}
																<div class="px-3 py-2 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
																	<div class="mb-2">
																		<span class="text-xs font-semibold text-gray-700 dark:text-gray-300">
																			{isCustomScenario(scenario.scenario_index, childGroup.scenarios) ? 'Custom Prompt:' : 'Scenario Prompt:'}
																		</span>
																		<p class="text-sm text-gray-900 dark:text-white mt-1">{scenario.scenario_prompt || 'No prompt available'}</p>
																	</div>
																	<div>
																		<span class="text-xs font-semibold text-gray-700 dark:text-gray-300">Original Response:</span>
																		<p class="text-sm text-gray-900 dark:text-white mt-1">{scenario.original_response || 'No response available'}</p>
																	</div>
																</div>
															{/if}
															<div class="overflow-x-auto">
																<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
																	<thead class="text-xs text-gray-700 dark:text-gray-300 uppercase bg-gray-50 dark:bg-gray-800">
																		<tr>
																			<th class="px-3 py-2">Attempt</th>
																			<th class="px-3 py-2">Version</th>
																			<th class="px-3 py-2">Decision</th>
																			<th class="px-3 py-2">Attn Check</th>
																			<th class="px-3 py-2">Final</th>
																			<th class="px-3 py-2">Created</th>
																			<th class="px-3 py-2">Details</th>
																		</tr>
																	</thead>
																	<tbody>
																		{#each scenario.versions as row}
																			<tr class="bg-white dark:bg-gray-900 border-t dark:border-gray-800">
																				<td class="px-3 py-2">{row.attempt_number}</td>
																				<td class="px-3 py-2">{row.version_number}</td>
																				<td class="px-3 py-2">{row.initial_decision || 'N/A'}</td>
																				<td class="px-3 py-2">
																					{#if row.is_attention_check}
																						<span class="text-yellow-600 dark:text-yellow-400">✓</span>
																					{/if}
																				</td>
																				<td class="px-3 py-2">
																					{#if row.is_final_version}
																						<span class="px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded">Final</span>
																					{:else}
																						<span class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded">Draft</span>
																					{/if}
																				</td>
																				<td class="px-3 py-2">{formatTimestamp(row.created_at)}</td>
																				<td class="px-3 py-2">
																					<button
																						on:click={() => toggleVersionAccordion(row.id)}
																						class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-xs"
																					>
																						{isVersionExpanded(row.id) ? 'Hide' : 'Show'}
																					</button>
																				</td>
																			</tr>
																			{#if isVersionExpanded(row.id) && expansionCounter >= 0}
																				<tr class="bg-gray-50 dark:bg-gray-800">
																					<td colspan="7" class="px-4 py-3">
																						<div class="space-y-3">
																							{#if row.is_attention_check}
																								<div class="p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
																									<div class="text-xs font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
																										Attention Check
																									</div>
																									<div class="space-y-1 text-sm">
																										<div>Selected "I read the instructions": 
																											{#if row.attention_check_selected}
																												<span class="text-green-600">✓ Yes</span>
																											{:else}
																												<span class="text-red-600">✗ No</span>
																											{/if}
																										</div>
																										<div>Status: 
																											{#if row.attention_check_passed}
																												<span class="text-green-600">✓ PASSED</span>
																											{:else}
																												<span class="text-red-600">✗ FAILED</span>
																											{/if}
																										</div>
																									</div>
																								</div>
																							{/if}
																							{#if row.strategies && row.strategies.length > 0}
																								<div>
																									<span class="text-xs font-semibold text-gray-700 dark:text-gray-300">Strategies:</span>
																									<ul class="mt-1 space-y-1">
																										{#each row.strategies as strategy}
																											<li class="text-sm text-gray-900 dark:text-white">• {strategy}</li>
																										{/each}
																									</ul>
																								</div>
																							{/if}
																							{#if row.custom_instructions && row.custom_instructions.length > 0}
																								<div>
																									<span class="text-xs font-semibold text-gray-700 dark:text-gray-300">Custom Instructions:</span>
																									<ul class="mt-1 space-y-1">
																										{#each row.custom_instructions as instruction}
																											<li class="text-sm text-gray-900 dark:text-white">• {instruction}</li>
																										{/each}
																									</ul>
																								</div>
																							{/if}
																							{#if row.highlighted_texts && row.highlighted_texts.length > 0}
																								<div>
																									<span class="text-xs font-semibold text-gray-700 dark:text-gray-300">Highlighted Texts:</span>
																									<ul class="mt-1 space-y-1">
																										{#each row.highlighted_texts as text}
																											<li class="text-sm text-gray-900 dark:text-white">• {text}</li>
																										{/each}
																									</ul>
																								</div>
																							{/if}
																							{#if row.refactored_response}
																								<div>
																									<span class="text-xs font-semibold text-gray-700 dark:text-gray-300">Refactored Response:</span>
																									<p class="text-sm text-gray-900 dark:text-white mt-1">{row.refactored_response}</p>
																								</div>
																							{/if}
																							{#if !row.strategies?.length && !row.custom_instructions?.length && !row.highlighted_texts?.length && !row.refactored_response}
																								<div class="text-xs text-gray-500 italic">No moderation details available for this version</div>
																							{/if}
																						</div>
																					</td>
																				</tr>
																			{/if}
																		{/each}
																	</tbody>
																</table>
															</div>
														</div>
													{/each}
												</div>
											</div>
										{/each}
									</div>
								{/if}
							</div>
							
							<!-- Exit Quiz Responses in this session -->
							<div>
								<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
									Exit Quiz Responses ({sessionData.exit_quiz_responses.length})
								</h3>
								{#if sessionData.exit_quiz_responses.length === 0}
									<p class="text-gray-500 dark:text-gray-400 italic">No exit quiz responses</p>
								{:else}
									<div class="space-y-3">
										{#each sessionData.exit_quiz_responses as response}
								{@const parsed = parseExitQuizAnswers(response.answers)}
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

									{#if parsed}
										<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
											<div>
												<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">GenAI Familiarity:</span>
												<p class="text-gray-900 dark:text-white">{parsed.genai_familiarity}</p>
											</div>
											<div>
												<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">Usage Frequency:</span>
												<p class="text-gray-900 dark:text-white">{parsed.usage_frequency}</p>
											</div>
											<div>
												<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">Parenting Style:</span>
												<p class="text-gray-900 dark:text-white">{parsed.parenting_style}</p>
											</div>
										</div>
									{/if}
									
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
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
