<!-- TODO:
 1. Last Exported Time
 2. Download as Zip Mockup: Question: how to make sure conversation download is controlled?
 *. Instructor: homework has start and end date -> download at the last day -> able to see the student interactions like how many days, time of conversation "40minutes?" 
 3. Export as CSV;
 4. Select One Students' all homework;
 5. Select the status of all info related to one single homework;
 6. Preview of Conversation History;

 Starting with the homework: see who is participating; -> What they've done, click one of the students -> preview the chat ->multiple homeworks, see one student's multiple chats; -> Export it;

 To summarize Start with a multi-student homework overview, then drill down into all student questions for one homework, and finally show a granular view of one student’s interactions across multiple homeworks.
 -->

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	export let show = false;
	export let users = [];
	export let group = null;

	let loading = false;
	let memberStats = [];
	let selectedMembers = new Set();
	let selectAll = false;
	let actionDropdownOpen = false;
	let modelDropdownOpen = false;
	let availableModels = [];

	let actionDropdownRef;
	let modelDropdownRef;

	// Sample math questions for placeholders
	const sampleQuestions = [
		'What is 2 + 2?',
		'Solve for x: 3x + 5 = 14',
		'What is the area of a circle with radius 5?',
		'Factor x² - 9',
		'What is the derivative of x²?',
		'Solve: 2x + 3y = 12, x - y = 1',
		'What is sin(30°)?',
		'Find the slope of y = 3x + 2',
		'What is 15% of 200?',
		'Simplify: √(16x⁴)'
	];

	// Generate placeholder data when no real data is available
	const generatePlaceholderData = () => {
		const placeholderCount = 15;
		const memberAmount = 7;
		return Array.from({ length: placeholderCount }, (_, index) => ({
			id: `placeholder-${index}`,
			name: `Member ${Math.floor(Math.random() * memberAmount)}`,
			email: `member${index + 1}@example.com`,
			model: ['Math Ally - HW01', 'Math Ally - HW02', 'Math Ally - HW03', 'Math Ally - HW04'][
				index % 4
			],
			messageCount: Math.floor(Math.random() * 30) + 50,
			questionsAsked: Math.floor(Math.random() * 20) + 10,
			questions: Array.from(
				{ length: Math.floor(Math.random() * 5) + 3 },
				() => sampleQuestions[Math.floor(Math.random() * sampleQuestions.length)]
			),
			lastUpdated: new Date(
				Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000
			).toLocaleDateString(),
			timeTaken: `${Math.floor(Math.random() * 120) + 15}min`
		}));
	};

	// Fetch conversation data for the group
	const fetchConversationData = async () => {
		if (!group) return;

		loading = true;
		try {
			// TODO: Replace with actual API call
			// const response = await getGroupConversationStats(group.id);

			// Mock data based on group users - replace with actual API response
			if (group.user_ids && group.user_ids.length > 0) {
				memberStats = group.user_ids.map((userId, index) => {
					const user = users.find((u) => u.id === userId) || {
						name: `User ${userId}`,
						email: `user${userId}@example.com`
					};
					return {
						id: userId,
						name: user.name || `User ${userId}`,
						email: user.email || `user${userId}@example.com`,
						model: ['GPT-4', 'Claude-3', 'Gemini', 'Llama-2'][index % 4],
						messageCount: Math.floor(Math.random() * 200) + 10,
						questionsAsked: Math.floor(Math.random() * 50) + 5,
						questions: Array.from(
							{ length: Math.floor(Math.random() * 5) + 3 },
							() => sampleQuestions[Math.floor(Math.random() * sampleQuestions.length)]
						),
						lastUpdated: new Date(
							Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000
						).toLocaleDateString(),
						timeTaken: `${Math.floor(Math.random() * 120) + 10}min`
					};
				});
			} else {
				// Generate placeholder data when no users are available
				memberStats = generatePlaceholderData();
			}
		} catch (error) {
			toast.error('Failed to fetch conversation data');
			console.error(error);
			// Generate placeholder data on error
			memberStats = generatePlaceholderData();
		} finally {
			loading = false;
		}
	};

	// Handle select all checkbox
	const handleSelectAll = () => {
		if (selectAll) {
			selectedMembers = new Set(memberStats.map((member) => member.id));
		} else {
			selectedMembers = new Set();
		}
	};

	// Handle individual member selection
	const handleMemberSelect = (memberId) => {
		if (selectedMembers.has(memberId)) {
			selectedMembers.delete(memberId);
		} else {
			selectedMembers.add(memberId);
		}
		selectedMembers = selectedMembers; // Trigger reactivity
		selectAll = selectedMembers.size === memberStats.length;
	};

	// Export functionality
	const handleExport = () => {
		if (selectedMembers.size === 0) return;

		const selectedData = memberStats.filter((member) => selectedMembers.has(member.id));
		console.log('Exporting data for:', selectedData);
		toast.success(`Exporting data for ${selectedMembers.size} members`);
		// TODO: Implement actual export functionality
	};

	// Action dropdown options
	const handleAction = (action) => {
		console.log('Action:', action, 'for', selectedMembers.size, 'members');
		actionDropdownOpen = false;
		// TODO: Implement actions
	};

	// Get unique models from memberStats
	const updateAvailableModels = () => {
		availableModels = [...new Set(memberStats.map((member) => member.model))];
	};

	// Select all members with a specific model
	const selectByModel = (model) => {
		const membersWithModel = memberStats
			.filter((member) => member.model === model)
			.map((member) => member.id);

		// Add these members to selection
		membersWithModel.forEach((id) => selectedMembers.add(id));
		selectedMembers = selectedMembers; // Trigger reactivity

		// Update selectAll state
		selectAll = selectedMembers.size === memberStats.length;

		modelDropdownOpen = false;
		toast.success(`Selected ${membersWithModel.length} members with ${model}`);
	};

	// Update available models when memberStats changes
	$: if (memberStats.length > 0) {
		updateAvailableModels();
	}

	$: selectAll = selectedMembers.size === memberStats.length && memberStats.length > 0;

	// Click outside handler
	const handleClickOutside = (event) => {
		// Close action dropdown if clicked outside
		if (actionDropdownRef && !actionDropdownRef.contains(event.target)) {
			actionDropdownOpen = false;
		}

		// Close model dropdown if clicked outside
		if (modelDropdownRef && !modelDropdownRef.contains(event.target)) {
			modelDropdownOpen = false;
		}
	};

	// Add event listener when component mounts
	onMount(() => {
		document.addEventListener('click', handleClickOutside);

		if (group) {
			fetchConversationData();
		}

		// Cleanup event listener
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<Modal size="9xl" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 mb-4">
			<div class="flex items-center gap-4">
				<div class="flex flex-col">
					<div class="text-lg font-medium font-primary">
						{group?.name || 'Group'}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Conversation History</div>
				</div>
				<!-- <button
					class="px-4 py-2 text-sm font-medium transition rounded-lg {selectedMembers.size > 0
						? 'bg-gray-700 hover:bg-gray-600 text-white'
						: 'bg-gray-300 text-gray-500 cursor-not-allowed'}"
					disabled={selectedMembers.size === 0}
					on:click={handleExport}
				>
					Export ({selectedMembers.size})
				</button> -->
				<div class="relative" bind:this={actionDropdownRef}>
					<button
						class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-2"
						on:click|stopPropagation={() => {
							actionDropdownOpen = !actionDropdownOpen;
							modelDropdownOpen = false; // Close other dropdown
						}}
					>
						<span
							class="text-xs font-bold text-gray-700 dark:text-gray-400 uppercase tracking-wider"
						>
							Export
						</span>
						<ChevronDown className="size-3.5" />
					</button>
					{#if actionDropdownOpen}
						<div
							class="absolute top-full left-0 mt-1 w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10"
						>
							<button
								class="block w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
								on:click={() => handleAction('export')}
							>
								Export as .txt
							</button>
							<button
								class="block w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
								on:click={() => handleAction('delete')}
							>
								Export as .json
							</button>
							<button
								class="block w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
								on:click={() => handleAction('archive')}
							>
								Export as .pdf
							</button>
						</div>
					{/if}
				</div>
				<!-- Dropdown for Exporting -->
			</div>
			<button
				class="self-start"
				on:click={() => {
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

		<div class="px-5 pb-4">
			{#if loading}
				<div class="flex justify-center items-center h-32">
					<div
						class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"
					></div>
				</div>
			{:else}
				<!-- Table - Always show, with placeholder data if needed -->
				<div class="overflow-x-auto">
					<div
						class="max-h-96 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg"
					>
						<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
							<thead class="bg-gray-50 dark:bg-gray-800 sticky top-0">
								<tr>
									<!-- Actions dropdown column -->
									<th scope="col" class="px-4 py-3 text-left">
										<div class="flex items-center gap-2">
											<input
												type="checkbox"
												bind:checked={selectAll}
												on:change={handleSelectAll}
												class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
											/>
											<!-- <div class="relative" bind:this={actionDropdownRef}>
												<button
													class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200"
													on:click|stopPropagation={() => {
														actionDropdownOpen = !actionDropdownOpen;
														modelDropdownOpen = false; // Close other dropdown
													}}
												>
													<ChevronDown className="size-3.5" />
												</button>
												{#if actionDropdownOpen}
													<div
														class="absolute top-full left-0 mt-1 w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10"
													>
														<button
															class="block w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
															on:click={() => handleAction('export')}
														>
															Export
														</button>
														<button
															class="block w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
															on:click={() => handleAction('delete')}
														>
															Delete
														</button>
														<button
															class="block w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700"
															on:click={() => handleAction('archive')}
														>
															Archive
														</button>
													</div>
												{/if}
											</div> -->
											<!-- Dropdown for Exporting -->
										</div>
									</th>

									<th
										scope="col"
										class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
									>
										Members
									</th>
									<th
										scope="col"
										class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
									>
										Email
									</th>

									<!-- Model dropdown column -->
									<th scope="col" class="px-4 py-3 text-left">
										<div class="flex items-center gap-2">
											<span
												class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
											>
												Model
											</span>
											<div class="relative" bind:this={modelDropdownRef}>
												<button
													class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
													on:click|stopPropagation={() => {
														modelDropdownOpen = !modelDropdownOpen;
														actionDropdownOpen = false; // Close other dropdown
													}}
												>
													<ChevronDown className="size-3.5" />
												</button>
												{#if modelDropdownOpen}
													<div
														class="absolute top-full left-0 mt-1 w-max bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10 max-h-72 overflow-y-auto"
													>
														{#each availableModels as model}
															<button
																class="block w-full text-left px-2 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-600 last:border-b-0"
																on:click={() => selectByModel(model)}
															>
																<div class="font-medium flex items-center gap-1">
																	<span class="text-gray-400 text-[10px]">Select</span>
																	<span
																		class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100"
																	>
																		{model}
																	</span>
																	<span class="text-gray-400 text-[10px]">
																		({memberStats.filter((m) => m.model === model).length})
																	</span>
																</div>
															</button>
														{/each}
														{#if availableModels.length === 0}
															<div class="px-3 py-2 text-xs text-gray-500">No models available</div>
														{/if}
													</div>
												{/if}
											</div>
										</div>
									</th>

									<th
										scope="col"
										class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider min-w-32"
										style="min-width: 140px;"
									>
										Number of Messages
									</th>
									<th
										scope="col"
										class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider min-w-32"
									>
										Questions Asked
									</th>
									<th
										scope="col"
										class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
									>
										Last Updated
									</th>
									<th
										scope="col"
										class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
									>
										Time Taken
									</th>
								</tr>
							</thead>
							<tbody
								class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700"
							>
								{#each memberStats as member}
								<!-- List Items -->
									<tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
										<td class="px-4 py-4 whitespace-nowrap">
											<input
												type="checkbox"
												checked={selectedMembers.has(member.id)}
												on:change={() => handleMemberSelect(member.id)}
												class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
											/>
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100"
										>
											{member.name}
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
										>
											{member.email}
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
										>
											<span
												class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100"
											>
												{member.model}
											</span>
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											style="min-width: 140px;"
										>
											{member.messageCount.toLocaleString()}
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
										>
											<div class="relative">
												<button class="text-blue-600 hover:text-blue-800 hover:underline">
													{member.questionsAsked} ▼
												</button>
												<!-- Questions dropdown - you can implement this as needed -->
												<div
													class="hidden absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10"
												>
													{#each member.questions as question}
														<div
															class="px-3 py-2 text-xs border-b border-gray-100 dark:border-gray-700 last:border-b-0"
														>
															{question}
														</div>
													{/each}
												</div>
											</div>
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
										>
											{member.lastUpdated}
										</td>
										<td
											class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
										>
											{member.timeTaken}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
				<!-- Summary Stats -->
				<div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 min-h-48">
					{#if selectedMembers.size === 0}
						<!-- Blank when no selection -->
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							Select chats to view statistics
						</div>
					{:else}
						{@const selectedData = memberStats.filter((member) => selectedMembers.has(member.id))}
						{@const uniqueMembers = [...new Set(selectedData.map((m) => m.name))]}
						{@const uniqueModels = [...new Set(selectedData.map((m) => m.model))]}
						{@const showMemberStats = uniqueMembers.length === 1}
						{@const showModelStats = uniqueModels.length === 1}

						<div
							class="grid {showMemberStats && showModelStats ? 'grid-cols-2' : 'grid-cols-1'} gap-6"
						>
							<!-- About This Member Section -->
							{#if showMemberStats}
								{@const memberName = uniqueMembers[0]}
								{@const memberData = selectedData.filter((m) => m.name === memberName)}
								{@const totalMessages = memberData.reduce((sum, m) => sum + m.messageCount, 0)}
								{@const totalQuestions = memberData.reduce((sum, m) => sum + m.questionsAsked, 0)}
								{@const avgTime = Math.round(
									memberData.reduce((sum, m) => sum + parseInt(m.timeTaken), 0) / memberData.length
								)}
								{@const allMemberChats = memberStats.filter((m) => m.name === memberName)}
								{@const allMemberChatsSelected = allMemberChats.every((chat) =>
									selectedMembers.has(chat.id)
								)}

								<div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
									<div class="text-sm font-semibold text-green-800 dark:text-green-200 mb-3">
										About This Member: {memberName}
									</div>
									<div class="grid grid-cols-3 gap-4 text-center mb-4">
										<div>
											<div class="text-lg font-semibold text-green-900 dark:text-green-100">
												{totalMessages.toLocaleString()}
											</div>
											<div class="text-xs text-green-600 dark:text-green-300">Total Messages</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-green-900 dark:text-green-100">
												{totalQuestions}
											</div>
											<div class="text-xs text-green-600 dark:text-green-300">Total Questions</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-green-900 dark:text-green-100">
												{avgTime}min
											</div>
											<div class="text-xs text-green-600 dark:text-green-300">Avg Time</div>
										</div>
									</div>
									<button
										class="w-full px-3 py-2 text-xs font-medium transition rounded-md {allMemberChatsSelected
											? 'bg-red-600 hover:bg-red-700'
											: 'bg-green-600 hover:bg-green-700'} text-white"
										on:click={() => {
											if (allMemberChatsSelected) {
												// Unselect all chats from this member
												allMemberChats.forEach((chat) => selectedMembers.delete(chat.id));
												selectedMembers = selectedMembers;
												selectAll = selectedMembers.size === memberStats.length;
												toast.success(
													`Unselected all ${allMemberChats.length} chats from ${memberName}`
												);
											} else {
												// Select all chats from this member
												allMemberChats.forEach((chat) => selectedMembers.add(chat.id));
												selectedMembers = selectedMembers;
												selectAll = selectedMembers.size === memberStats.length;
												toast.success(
													`Selected all ${allMemberChats.length} chats from ${memberName}`
												);
											}
										}}
									>
										{allMemberChatsSelected ? 'Unselect' : 'Select'} All Chats of This Member ({allMemberChats.length})
									</button>
								</div>
							{/if}

							<!-- About This Model Section -->
							{#if showModelStats}
								{@const modelName = uniqueModels[0]}
								{@const modelData = selectedData.filter((m) => m.model === modelName)}
								{@const totalMessages = modelData.reduce((sum, m) => sum + m.messageCount, 0)}
								{@const totalQuestions = modelData.reduce((sum, m) => sum + m.questionsAsked, 0)}
								{@const avgTime = Math.round(
									modelData.reduce((sum, m) => sum + parseInt(m.timeTaken), 0) / modelData.length
								)}
								{@const uniqueUsers = [...new Set(modelData.map((m) => m.name))].length}
								{@const allModelChats = memberStats.filter((m) => m.model === modelName)}
								{@const allModelChatsSelected = allModelChats.every((chat) =>
									selectedMembers.has(chat.id)
								)}

								<div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
									<div class="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-3">
										About This Model: {modelName}
									</div>
									<div class="grid grid-cols-3 gap-3 text-center mb-4">
										<div>
											<div class="text-lg font-semibold text-blue-900 dark:text-blue-100">
												{totalMessages.toLocaleString()}
											</div>
											<div class="text-xs text-blue-600 dark:text-blue-300">Total Messages</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-blue-900 dark:text-blue-100">
												{totalQuestions}
											</div>
											<div class="text-xs text-blue-600 dark:text-blue-300">Total Questions</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-blue-900 dark:text-blue-100">
												{avgTime}min
											</div>
											<div class="text-xs text-blue-600 dark:text-blue-300">Avg Time</div>
										</div>
									</div>
									<button
										class="w-full px-3 py-2 text-xs font-medium transition rounded-md {allModelChatsSelected
											? 'bg-red-600 hover:bg-red-700'
											: 'bg-blue-600 hover:bg-blue-700'} text-white"
										on:click={() => {
											if (allModelChatsSelected) {
												// Unselect all chats from this model
												allModelChats.forEach((chat) => selectedMembers.delete(chat.id));
												selectedMembers = selectedMembers;
												selectAll = selectedMembers.size === memberStats.length;
												toast.success(
													`Unselected all ${allModelChats.length} chats from ${modelName}`
												);
											} else {
												// Select all chats from this model
												allModelChats.forEach((chat) => selectedMembers.add(chat.id));
												selectedMembers = selectedMembers;
												selectAll = selectedMembers.size === memberStats.length;
												toast.success(
													`Selected all ${allModelChats.length} chats from ${modelName}`
												);
											}
										}}
									>
										{allModelChatsSelected ? 'Unselect' : 'Select'} All Chats of This Model ({allModelChats.length})
									</button>
								</div>
							{/if}

							<!-- Multiple Selection Summary (when multiple members AND models are selected) -->
							{#if !showMemberStats && !showModelStats}
								<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
									<div class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
										Selection Summary
									</div>
									<div class="grid grid-cols-4 gap-4 text-center mb-4">
										<div>
											<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
												{selectedData.length}
											</div>
											<div class="text-xs text-gray-500 dark:text-gray-400">Selected Chats</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
												{uniqueMembers.length}
											</div>
											<div class="text-xs text-gray-500 dark:text-gray-400">Unique Members</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
												{uniqueModels.length}
											</div>
											<div class="text-xs text-gray-500 dark:text-gray-400">Unique Models</div>
										</div>
										<div>
											<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
												{selectedData.reduce((sum, m) => sum + m.messageCount, 0).toLocaleString()}
											</div>
											<div class="text-xs text-gray-500 dark:text-gray-400">Total Messages</div>
										</div>
									</div>
									<div class="text-xs text-gray-600 dark:text-gray-400 text-center">
										Select chats from a single member or model to view detailed statistics
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</Modal>
