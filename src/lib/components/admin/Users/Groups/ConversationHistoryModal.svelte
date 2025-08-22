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

<!-- 
 1. Add Chat Titles

 -->
<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Cross from '$lib/components/icons/Cross.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import QuestionsAskedModal from './QuestionsAskedModal.svelte';

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

	// Search functionality
	let isSearching = false;
	let searchQuery = '';
	let searchInputRef;

	// Model filtering
	let filteredModel = null; // null means show all, string means show only this model

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
			chatName: `Chat ${index + 1}`,
			name: `Member ${Math.floor(Math.random() * memberAmount)}`,
			email: `membername${index + 1}@example.com`,
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
						chatName: `Chat ${index + 1}`,
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

	// Filtered member stats based on search and model filter
	$: filteredMemberStats = memberStats.filter((chat) => {
		// Apply search filter
		const matchesSearch =
			!searchQuery ||
			chat.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			chat.chatName.toLowerCase().includes(searchQuery.toLowerCase()) ||
			chat.email.toLowerCase().includes(searchQuery.toLowerCase());

		// Apply model filter
		const matchesModel = !filteredModel || chat.model === filteredModel;

		return matchesSearch && matchesModel;
	});

	// Handle select all checkbox
	const handleSelectAll = () => {
		if (selectAll) {
			selectedMembers = new Set(filteredMemberStats.map((chat) => chat.id));
		} else {
			selectedMembers = new Set();
		}
	};

	// Handle individual chat selection
	const handleMemberSelect = (memberId) => {
		if (selectedMembers.has(memberId)) {
			selectedMembers.delete(memberId);
		} else {
			selectedMembers.add(memberId);
		}
		selectedMembers = selectedMembers; // Trigger reactivity
		selectAll =
			selectedMembers.size === filteredMemberStats.length && filteredMemberStats.length > 0;
	};

	// Search functionality
	const toggleSearch = () => {
		isSearching = !isSearching;
		if (isSearching) {
			// Focus the search input after a tick
			setTimeout(() => {
				if (searchInputRef) {
					searchInputRef.focus();
				}
			}, 0);
		} else {
			// Clear search when hiding
			searchQuery = '';
		}
	};

	const handleSearchKeydown = (event) => {
		if (event.key === 'Escape') {
			toggleSearch();
		}
	};

	// Export functionality
	const handleExport = () => {
		if (selectedMembers.size === 0) return;

		const selectedData = filteredMemberStats.filter((chat) => selectedMembers.has(chat.id));
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
		availableModels = [...new Set(memberStats.map((chat) => chat.model))];
	};

	// Show only chats with a specific model
	const showOnlyModel = (model) => {
		filteredModel = model;
		modelDropdownOpen = false;
		toast.success(`Showing only ${model} chats`);
	};

	// Clear model filter
	const clearModelFilter = () => {
		filteredModel = null;
		modelDropdownOpen = false;
		toast.success('Showing all models');
	};

	// Update available models when memberStats changes
	$: if (memberStats.length > 0) {
		updateAvailableModels();
	}

	$: selectAll =
		selectedMembers.size === filteredMemberStats.length && filteredMemberStats.length > 0;

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

	// Questions modal state
	let showQuestionsModal = false;
	let selectedMemberForQuestions = null;

	// Show questions modal
	const showQuestions = (chat) => {
		selectedMemberForQuestions = chat;
		showQuestionsModal = true;
	};
</script>

<Modal size="12xl" bind:show>
	<div class="h-[85vh] flex flex-col">
		<!-- Header -->
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 mb-4 flex-shrink-0">
			<div class="flex items-center gap-4">
				<div class="flex flex-col">
					<div class="text-lg font-medium font-primary">
						{group?.name || 'Group'}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Conversation History</div>
				</div>
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
			</div>
			<button
				class="self-start"
				on:click={() => {
					show = false;
				}}
			>
				<Cross className="size-4.5" />
			</button>
		</div>

		<!-- Table Container with fixed height -->
		<div class="px-5 pb-4 flex-1 flex flex-col min-h-0">
			{#if loading}
				<div class="flex justify-center items-center flex-1">
					<div
						class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"
					></div>
				</div>
			{:else}
				<!-- Table - Always show, with placeholder data if needed -->
				<div class="flex-1 flex flex-col min-h-0">
					<div
						class="flex-1 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
					>
						<div class="h-full overflow-auto">
							<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700 table-fixed">
								<thead class="bg-gray-50 dark:bg-gray-800 sticky top-0">
									<tr>
										<!-- Actions dropdown column - Fixed width -->
										<th scope="col" class="px-4 py-3 text-left w-[60px]">
											<div class="flex items-center gap-2">
												<input
													type="checkbox"
													bind:checked={selectAll}
													on:change={handleSelectAll}
													class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
												/>
											</div>
										</th>

										<!-- Chat column - Fixed width -->
										<th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[120px]"
										>
											Chat
										</th>

										<!-- Members column with search - Fixed width with consistent container -->
										<th scope="col" class="px-4 py-3 text-left w-[160px]">
											<div class="w-[130px]">
												<!-- Fixed width container -->
												<div class="flex items-center gap-2 w-full">
													{#if isSearching}
														<input
															bind:this={searchInputRef}
															bind:value={searchQuery}
															on:keydown={handleSearchKeydown}
															placeholder="Search..."
															class="text-xs font-medium bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 flex-1 min-w-0"
														/>
														<button
															class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 flex-shrink-0"
															on:click={toggleSearch}
															aria-label="Close search"
														>
															<svg
																class="w-3 h-3"
																fill="none"
																stroke="currentColor"
																viewBox="0 0 20 20"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M6 18L18 6M6 6l12 12"
																/>
															</svg>
														</button>
													{:else}
														<button
															class="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 w-full justify-start"
															on:click={toggleSearch}
														>
															<span class="truncate">Members</span>
															<Search className="size-3.5 flex-shrink-0" />
														</button>
													{/if}
												</div>
											</div>
										</th>

										<!-- Email column - Fixed width -->
										<th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[200px]"
										>
											Email
										</th>

										<!-- Model column - Fixed width with conditional clear button -->
										<th scope="col" class="px-4 py-3 text-left w-[180px]">
											<div class="w-[150px]">
												<!-- Fixed width container -->
												<div class="flex items-center gap-2 w-full">
													<span
														class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
													>
														Model
													</span>
													<div class="relative flex-shrink-0" bind:this={modelDropdownRef}>
														{#if filteredModel}
															<!-- Clear filter button when filtered -->
															<button
																class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
																on:click={clearModelFilter}
																title="Clear {filteredModel} filter"
															>
																<Cross className="size-3.5" />
															</button>
														{:else}
															<!-- Normal dropdown button when not filtered -->
															<button
																class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
																on:click|stopPropagation={() => {
																	modelDropdownOpen = !modelDropdownOpen;
																	actionDropdownOpen = false; // Close other dropdown
																}}
															>
																<ChevronDown className="size-3.5" />
															</button>
														{/if}

														{#if modelDropdownOpen && !filteredModel}
															<div
																class="absolute top-full left-0 mt-1 w-max bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10 max-h-72 overflow-y-auto"
															>
																{#each availableModels as model}
																	<button
																		class="block w-full text-left px-2 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-600 last:border-b-0"
																		on:click={() => showOnlyModel(model)}
																	>
																		<div class="font-medium flex items-center gap-1">
																			<span class="text-gray-400 text-[10px]">Show</span>
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
																	<div class="px-3 py-2 text-xs text-gray-500">
																		No models available
																	</div>
																{/if}
															</div>
														{/if}
													</div>
												</div>
											</div>
										</th>

										<!-- Messages column - Fixed width -->
										<th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[140px]"
										>
											Messages
										</th>

										<!-- Questions column - Fixed width with container -->
										<th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[120px]"
										>
											<div class="w-[90px]">
												<!-- Fixed width container -->
												Questions
											</div>
										</th>

										<!-- Last Updated column - Fixed width -->
										<th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[120px]"
										>
											Updated
										</th>

										<!-- Time Taken column - Fixed width -->
										<th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[100px]"
										>
											Duration
										</th>
									</tr>
								</thead>
								<tbody
									class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700"
								>
									{#each filteredMemberStats as chat}
										<tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
											<td class="px-4 py-4 whitespace-nowrap">
												<input
													type="checkbox"
													checked={selectedMembers.has(chat.id)}
													on:change={() => handleMemberSelect(chat.id)}
													class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
												/>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 truncate"
											>
												{chat.chatName}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 truncate"
											>
												{chat.name}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 truncate"
											>
												{chat.email}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												<div class="w-[150px]">
													<!-- Fixed width container matching header -->
													<span
														class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100 truncate"
													>
														{chat.model}
													</span>
												</div>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												{chat.messageCount.toLocaleString()}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												<div class="w-[90px] flex justify-center">
													<!-- Fixed width container matching header -->
													<button
														class="flex items-center gap-2 px-2 py-1"
														on:click|stopPropagation={() => showQuestions(chat)}
														aria-label="View questions asked by {chat.name}"
													>
														<span class="min-w-[20px] text-center">{chat.questionsAsked}</span>
														<div
															class=" rounded p-1 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
														>
															<Eye className="size-3.5 flex-shrink-0" />
														</div>
													</button>
												</div>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 truncate"
											>
												{chat.lastUpdated}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												{chat.timeTaken}
											</td>
										</tr>
									{/each}

									{#if filteredMemberStats.length === 0}
										<tr>
											<td
												colspan="9"
												class="px-4 py-8 text-center text-gray-500 dark:text-gray-400"
											>
												{#if searchQuery}
													No chats found matching "{searchQuery}"
												{:else if filteredModel}
													No chats found for {filteredModel}
												{:else}
													No conversation data available
												{/if}
											</td>
										</tr>
									{/if}
								</tbody>
							</table>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</Modal>

<!-- Questions Asked Modal -->
<QuestionsAskedModal bind:show={showQuestionsModal} member={selectedMemberForQuestions} />
