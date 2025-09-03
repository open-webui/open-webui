<!-- NAME:
 1. Currently name might be missing? Using netID instead
  -->

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	import { user } from '$lib/stores'; // This is how you get user data

	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Cross from '$lib/components/icons/Cross.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import QuestionsAskedModal from './QuestionsAskedModal.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let show = false;
	export let users = [];
	export let group = null;

	// Simplified API function for debugging
	const fetchGroupChatData = async (groupId) => {
		try {
			console.log('Group ID:', groupId);

			// Minimal filter to test what data exists
			const filterData = {
				group_id: groupId,
				skip: 0,
				limit: 100
				// Remove all other filters temporarily
			};

			console.log('📤 Minimal filter request:', filterData);

			const response = await fetch('/api/v1/chats/filter/meta', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(filterData)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const chatData = await response.json();
			console.log('✅ Received chat data:', chatData);

			return chatData;
		} catch (error) {
			console.error('💥 Error:', error);
			throw error;
		}
	};

	$: groupedChats = (() => {
		const map = new Map();
		for (const chat of filteredMemberStats) {
			const key = chat.name + '||' + chat.model;
			if (!map.has(key)) {
				map.set(key, {
					name: chat.name,
					model: chat.model,
					email: chat.email,
					ids: [],
					messageCount: 0,
					questionsAsked: 0,
					lastUpdated: chat.lastUpdated,
					chats: []
				});
			}
			const group = map.get(key);
			group.ids.push(chat.id);
			group.messageCount += Number(chat.messageCount) || 0;

			const qCount = Array.isArray(chat.questionsAsked)
				? chat.questionsAsked.length
				: typeof chat.questionsAsked === 'number'
					? chat.questionsAsked
					: 0;
			group.questionsAsked += qCount;

			if (new Date(chat.lastUpdated) > new Date(group.lastUpdated)) {
				group.lastUpdated = chat.lastUpdated;
			}
			group.chats.push(chat);
		}
		return Array.from(map.values());
	})();
	// Transform API response to match your data structure
	// Fixed transform function
	const transformChatData = (apiChats) => {
		return apiChats.map((chat, index) => {
			// Find user info from the users array
			const user = users.find((u) => u.id === chat.user_id) || {
				name: `User ${chat.user_id}`,
				email: `user${chat.user_id}@example.com`
			};

			// console.log('Transforming chat:', chat);

			// Extract questions properly from meta
			const questionsArray = chat.meta?.questions_asked || [];
			const questionsCount = Array.isArray(questionsArray) ? questionsArray.length : 0;
			console.log('Extracted questions:', questionsArray);
			return {
				id: chat.id,
				chatName: chat.title || `Chat ${index + 1}`,
				name: user.name || `User ${chat.user_id}`,
				email: user.email || `user${chat.user_id}@example.com`,
				model: chat.meta?.model_name || chat.meta?.base_model_name || 'Unknown',
				messageCount: chat.meta?.num_of_messages || 0,
				questionsAsked: questionsCount, // This should be a number (count)
				questions: questionsArray, // This should be the array of question texts
				lastUpdated: new Date(chat.updated_at * 1000).toLocaleDateString(),
				timeTaken: formatTimeTaken(chat.meta?.total_time_taken)
			};
		});
	};

	// Helper function to format time taken
	const formatTimeTaken = (timeInSeconds) => {
		if (!timeInSeconds) return '0min';
		const minutes = Math.floor(timeInSeconds / 60);
		return `${minutes}min`;
	};

	let loading = false;
	let memberStats = [];
	let selectedMembers = new Set();
	let selectAll = false;
	let actionDropdownOpen = false;
	let modelDropdownOpen = false;
	let availableModels = [];

	// Search functionality for Members
	let isSearching = false;
	let searchQuery = '';
	let searchInputRef;

	// Add chat search functionality
	let isChatSearching = false;
	let chatSearchQuery = '';
	let chatSearchInputRef;

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

	// Pagination state
	let currentPage = 1;
	const itemsPerPage = 10;

	// Calculate pagination
	$: totalItems = filteredGroupedChats.length;
	$: totalPages = Math.ceil(totalItems / itemsPerPage);
	$: startIndex = (currentPage - 1) * itemsPerPage;
	$: endIndex = startIndex + itemsPerPage;
	$: paginatedChats = filteredGroupedChats.slice(startIndex, endIndex);

	// Reset to page 1 when filters change
	$: if (searchQuery || chatSearchQuery || filteredModel) {
		currentPage = 1;
	}

	// Pagination functions
	const goToPage = (page) => {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
		}
	};

	const nextPage = () => {
		if (currentPage < totalPages) {
			currentPage++;
		}
	};

	const prevPage = () => {
		if (currentPage > 1) {
			currentPage--;
		}
	};

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

	// Update fetchConversationData to pass user IDs
	const fetchConversationData = async () => {
		if (!group) {
			toast.warning('No group selected');
			return;
		}

		console.log('🚀 Group object:', group);
		console.log('🚀 Group ID:', group.id);

		loading = true;
		try {
			// Test 1: Try your current approach
			console.log('Testing current filter approach...');
			let chatData = await fetchGroupChatData(group.id);

			if (chatData.length === 0) {
				console.log('❌ No data with group filter, testing without group filter...');

				// Test 2: Try without group filter to see if ANY chats exist
				const testResponse = await fetch('/api/v1/chats/filter/meta', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.token}`
					},
					body: JSON.stringify({
						skip: 0,
						limit: 10
						// No group_id filter
					})
				});

				if (testResponse.ok) {
					const allChats = await testResponse.json();
					console.log('📊 Total chats in system:', allChats.length);
					console.log('📊 Sample chat data:', allChats[0] || 'No chats exist');
				}
			}

			memberStats = transformChatData(chatData);

			if (memberStats.length === 0) {
				toast.warning('No conversation data found, showing placeholder data');
				memberStats = generatePlaceholderData();
			} else {
				toast.success(`Successfully loaded ${memberStats.length} conversations`);
			}
		} catch (error) {
			console.error('Failed to fetch chat data:', error);
			toast.error('Failed to fetch conversation data, showing demo data');
			memberStats = generatePlaceholderData();
		} finally {
			loading = false;
		}
	};
	// Filtered member stats based on search and model filter
	$: filteredMemberStats = memberStats.filter((chat) => {
		// Apply member search filter
		const matchesSearch =
			!searchQuery || chat.name.toLowerCase().includes(searchQuery.toLowerCase());

		// Apply model filter
		const matchesModel = !filteredModel || chat.model === filteredModel;

		return matchesSearch && matchesModel;
	});

	$: filteredGroupedChats = (() => {
		const map = new Map();
		for (const chat of filteredMemberStats) {
			const key = chat.name + '||' + chat.model;
			if (!map.has(key)) {
				map.set(key, {
					name: chat.name,
					model: chat.model,
					email: chat.email,
					ids: [],
					messageCount: 0,
					questionsAsked: 0, // This will be the total count
					questions: [], // This will be all questions combined
					lastUpdated: chat.lastUpdated,
					chats: []
				});
			}
			const group = map.get(key);

			// Add chat ID
			group.ids.push(chat.id);

			// Add message count
			group.messageCount += Number(chat.messageCount) || 0;

			// Add questions count (questionsAsked should be a number)
			const chatQuestionsCount =
				typeof chat.questionsAsked === 'number'
					? chat.questionsAsked
					: Array.isArray(chat.questionsAsked)
						? chat.questionsAsked.length
						: 0;
			group.questionsAsked += chatQuestionsCount;

			// Combine all questions from all chats (questions should be arrays)
			if (Array.isArray(chat.questions)) {
				group.questions.push(...chat.questions);
			}

			// Update last updated time
			if (new Date(chat.lastUpdated) > new Date(group.lastUpdated)) {
				group.lastUpdated = chat.lastUpdated;
			}

			// Store the original chat for reference
			group.chats.push(chat);
		}
		return Array.from(map.values());
	})();

	// Update handleMemberSelect to work with grouped chats
	const handleMemberSelect = (groupIds) => {
		// Handle both single ID and array of IDs
		const ids = Array.isArray(groupIds) ? groupIds : [groupIds];

		// Check if all IDs in this group are currently selected
		const allSelected = ids.every((id) => selectedMembers.has(id));

		if (allSelected) {
			// Remove all IDs from selection
			ids.forEach((id) => selectedMembers.delete(id));
		} else {
			// Add all IDs to selection
			ids.forEach((id) => selectedMembers.add(id));
		}

		selectedMembers = selectedMembers; // Trigger reactivity
		updateSelectAllState();
	};

	// Fixed handleSelectAll function
	const handleSelectAll = () => {
		if (selectAll || isPartialSelection) {
			// Unselect all (across all pages)
			selectedMembers = new Set();
		} else {
			// Select all (across all pages)
			selectedMembers = new Set();
			filteredGroupedChats.forEach((group) => {
				group.ids.forEach((id) => selectedMembers.add(id));
			});
		}
		selectedMembers = selectedMembers;
		updateSelectAllState();
	};

	// Add partial selection state
	let isPartialSelection = false;

	// Update selection functions to work with all items (not just current page)
	const updateSelectAllState = () => {
		const allGroupIds = filteredGroupedChats.flatMap((group) => group.ids); // All filtered items
		const selectedCount = allGroupIds.filter((id) => selectedMembers.has(id)).length;

		if (selectedCount === 0) {
			selectAll = false;
			isPartialSelection = false;
		} else if (selectedCount === allGroupIds.length) {
			selectAll = true;
			isPartialSelection = false;
		} else {
			selectAll = false;
			isPartialSelection = true;
		}
	};

	// Update reactivity
	$: if (filteredGroupedChats.length > 0) {
		updateSelectAllState();
	}

	// Also update when selectedMembers changes
	$: if (selectedMembers) {
		updateSelectAllState();
	}

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

	// Chat search functionality
	const toggleChatSearch = () => {
		isChatSearching = !isChatSearching;
		if (isChatSearching) {
			// Focus the chat search input after a tick
			setTimeout(() => {
				if (chatSearchInputRef) {
					chatSearchInputRef.focus();
				}
			}, 0);
		} else {
			// Clear chat search when hiding
			chatSearchQuery = '';
		}
	};

	const handleChatSearchKeydown = (event) => {
		if (event.key === 'Escape') {
			toggleChatSearch();
		}
	};

	// Export functionality
	const handleExportPDF = async () => {
		if (selectedMembers.size === 0) {
			toast.error('Please select at least one conversation to export as PDF');
			return;
		}

		try {
			toast.info(`Preparing PDF export for ${selectedMembers.size} conversations...`);

			const response = await fetch('/api/v1/chats/export/zip', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					group_id: group.id,
					chat_ids: Array.from(selectedMembers) // This now contains all selected chat IDs
				})
			});

			if (!response.ok) {
				throw new Error(`Export failed: ${response.status}`);
			}

			const blob = await response.blob();
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;

			// Create filename with timestamp
			const timestamp = new Date().toISOString().split('T')[0];
			link.download = `conversations_${group.id}_${timestamp}.zip`;

			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);

			toast.success(`Successfully exported ${selectedMembers.size} conversations`);
		} catch (error) {
			console.error('PDF export failed:', error);
			toast.error(`Failed to export PDF: ${error.message}`);
		}
	};

	const handleExportCSV = async () => {
		if (!group) {
			toast.error('No group selected');
			return;
		}

		try {
			toast.info('Preparing CSV export...');

			const filterData = {
				group_id: group.id,
				model_name: filteredModel || '',
				skip: 0,
				limit: 1000
			};

			const response = await fetch('/api/v1/chats/export/csv', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(filterData)
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}

			// Get the CSV content and filename
			const csvContent = await response.text();
			const contentDisposition = response.headers.get('Content-Disposition');
			const filename = contentDisposition
				? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
				: `group-${group.id}-conversations-filtered.csv`;

			// Create and download the CSV file
			const blob = new Blob([csvContent], { type: 'text/csv' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = filename;

			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);

			// Enhanced success message
			const filterInfo = [];
			if (searchQuery) filterInfo.push(`search: "${searchQuery}"`);
			if (filteredModel) filterInfo.push(`model: "${filteredModel}"`);

			const filterText = filterInfo.length > 0 ? ` (${filterInfo.join(', ')})` : '';
			toast.success(`Successfully exported filtered CSV: ${filename}${filterText}`);
		} catch (error) {
			console.error('CSV export failed:', error);
			toast.error(`Failed to export CSV: ${error.message}`);
		}
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
	const showQuestions = (group) => {
		console.log('Showing questions for group:', group);

		// Add safety check for group structure
		if (!group.chats || !Array.isArray(group.chats)) {
			console.error('Invalid group.chats:', group);
			toast.error('Unable to load questions - invalid data structure');
			return;
		}

		// Create a combined member object with all questions from all chats in the group
		const combinedMember = {
			name: group.name,
			model: group.model,
			email: group.email,
			questionsAsked: group.questionsAsked, // This is now the correct total count
			questions: group.chats.flatMap((chat) => chat.questions), // This is now the combined array of all questions
			chatCount: group.chats.length,
			chatNames: group.chats.map((chat) => chat.chatName || 'Unnamed Chat'),
			totalMessageCount: group.messageCount
		};

		console.log('Combined member for questions modal:', combinedMember);
		selectedMemberForQuestions = combinedMember;
		showQuestionsModal = true;
	};

	// Column resizing state
	let isResizing = false;
	let resizingColumn = null;
	let startX = 0;
	let startWidth = 0;

	// Default column widths (in pixels)
	let columnWidths = {
		checkbox: 60,
		members: 160,
		email: 200,
		model: 180,
		messages: 140,
		questions: 120,
		updated: 120
	};

	// Column resizing functions
	const startResize = (event, columnKey) => {
		isResizing = true;
		resizingColumn = columnKey;
		startX = event.clientX;
		startWidth = columnWidths[columnKey];

		// Prevent text selection during resize
		document.body.style.userSelect = 'none';
		document.body.style.cursor = 'col-resize';

		// Add global mouse event listeners
		document.addEventListener('mousemove', handleResize);
		document.addEventListener('mouseup', stopResize);

		event.preventDefault();
	};

	const handleResize = (event) => {
		if (!isResizing || !resizingColumn) return;

		const deltaX = event.clientX - startX;
		const newWidth = Math.max(60, startWidth + deltaX); // Minimum width of 60px

		columnWidths[resizingColumn] = newWidth;
		columnWidths = { ...columnWidths }; // Trigger reactivity
	};

	const stopResize = () => {
		isResizing = false;
		resizingColumn = null;

		// Restore normal cursor and text selection
		document.body.style.userSelect = '';
		document.body.style.cursor = '';

		// Remove global mouse event listeners
		document.removeEventListener('mousemove', handleResize);
		document.removeEventListener('mouseup', stopResize);
	};

	// Cleanup on component destroy
	onMount(() => {
		// ... existing onMount code ...

		return () => {
			// ... existing cleanup ...
			document.removeEventListener('mousemove', handleResize);
			document.removeEventListener('mouseup', stopResize);
		};
	});

	// ... rest of existing code ...
</script>

<Modal size="6xl" bind:show>
	<div class="h-[93.5vh] flex flex-col">
		<!-- Header -->
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 mb-4 flex-shrink-0">
			<!-- Replace the current export button section with this -->
			<div class="flex items-center gap-4">
				<div class="flex flex-col">
					<div class="text-lg font-medium font-primary">
						{group?.name || 'Group'}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Conversation History</div>
				</div>

				<!-- Export Buttons - Two Parallel Buttons -->
				<div class="flex items-center gap-3">
					<button
						class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
						on:click={handleExportPDF}
						disabled={selectedMembers.size === 0}
						class:opacity-50={selectedMembers.size === 0}
						class:cursor-not-allowed={selectedMembers.size === 0}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
						<span class="font-bold">Export as PDF</span>
					</button>

					<button
						class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
						on:click={handleExportCSV}
						disabled={filteredMemberStats.length === 0}
						class:opacity-50={filteredMemberStats.length === 0}
						class:cursor-not-allowed={filteredMemberStats.length === 0}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
						<span class="font-bold">Export as CSV</span>
					</button>
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
													checked={selectAll || isPartialSelection}
													indeterminate={isPartialSelection}
													on:change={handleSelectAll}
													class="rounded border-gray-300 text-gray-600 focus:ring-gray-500"
													title={isPartialSelection
														? `${Array.from(selectedMembers).length} of ${filteredGroupedChats.flatMap((g) => g.ids).length} conversations selected (click to unselect all)`
														: selectAll
															? 'All conversations selected (click to unselect all)'
															: 'No conversations selected (click to select all)'}
												/>
											</div>
										</th>

										<!-- Chat column - Fixed width -->
										<!-- <th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[120px]"
										>
											<div class="w-[90px]">
												<div class="flex items-center gap-2 w-full">
													{#if isChatSearching}
														<input
															bind:this={chatSearchInputRef}
															bind:value={chatSearchQuery}
															on:keydown={handleChatSearchKeydown}
															placeholder="Search..."
															class="text-xs font-medium bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 flex-1 min-w-0"
														/>
														<button
															class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 flex-shrink-0"
															on:click={toggleChatSearch}
															aria-label="Close chat search"
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
															on:click={toggleChatSearch}
														>
															<span class="truncate">Chat</span>
															<Search className="size-3.5 flex-shrink-0" />
														</button>
													{/if}
												</div>
											</div>
										</th> -->

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

										<!-- Model column - Updated header to show filtered model -->
										<th scope="col" class="px-4 py-3 text-left w-[180px]">
											<div class="w-[150px]">
												<!-- Fixed width container -->
												<div class="flex items-center gap-2 w-full">
													<div class="flex items-center gap-2 min-w-0 flex-1">
														<span
															class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
														>
															Model
														</span>
														{#if filteredModel}
															<!-- Show the filtered model in the header -->
															<span
																class="inline-flex items-center px-2.5 py-0 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 truncate"
															>
																{filteredModel}
															</span>
														{/if}
													</div>
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
																				class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
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
										<!-- <th
											scope="col"
											class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[100px]"
										>
											Duration
										</th> -->
									</tr>
								</thead>
								<tbody
									class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700"
								>
									{#each paginatedChats as group}
										<tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
											<td class="px-4 py-4 whitespace-nowrap">
												<input
													type="checkbox"
													checked={group.ids.every((id) => selectedMembers.has(id))}
													on:change={() => handleMemberSelect(group.ids)}
													class="rounded border-gray-300 text-gray-600 focus:ring-gray-500"
												/>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100"
											>
												<div class="w-[90px] truncate">{group.name}</div>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 truncate"
											>
												{group.email}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												<div class="w-[150px]">
													<!-- Fixed width container matching header -->
													<span
														class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 truncate"
													>
														{group.model}
													</span>
												</div>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												{group.messageCount.toLocaleString()}
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												<div class="w-[90px] flex justify-center">
													<!-- Fix this line in the tbody: -->
													<button
														class="flex items-center gap-2 px-2 py-1"
														on:click|stopPropagation={() => showQuestions(group)}
														aria-label="View questions asked by {group.name}"
													>
														<span class="min-w-[20px] text-center">{group.questionsAsked}</span>
														<div
															class="rounded p-1 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
														>
															<Eye className="size-3.5 flex-shrink-0" />
														</div>
													</button>
												</div>
											</td>
											<td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 truncate"
											>
												{group.lastUpdated}
											</td>
											<!-- <td
												class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
											>
												{group.timeTaken}
											</td> -->
										</tr>
									{/each}

									<!-- Fill empty rows to maintain consistent height for 10 items -->
									{#each Array(Math.max(0, itemsPerPage - paginatedChats.length)) as _}
										<tr class="h-16">
											<!-- Fixed row height matching data rows -->
											<td colspan="7" class="px-4 py-4"></td>
										</tr>
									{/each}
									<!-- No data message -->
									{#if paginatedChats.length === 0}
										<tr>
											<td
												colspan="7"
												class="px-4 py-8 text-center text-gray-500 dark:text-gray-400 h-32"
											>
												{#if searchQuery || chatSearchQuery}
													No conversations found matching search criteria
												{:else if filteredModel}
													No conversations found for {filteredModel}
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
		<!-- Pagination section -->
		<div class="px-5 py-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
			<div class="flex items-center justify-between">
				<!-- Left side - Items info -->
				<div class="text-sm text-gray-600 dark:text-gray-400">
					{#if totalItems > 0}
						Showing <span class="font-medium">{startIndex + 1}</span> to
						<span class="font-medium">{Math.min(endIndex, totalItems)}</span>
						of <span class="font-medium">{totalItems}</span> conversations
					{:else}
						No conversations to display
					{/if}
				</div>

				<!-- Center - Page navigation -->
				<div class="flex items-center gap-3">
					<!-- Previous button -->
					<button
						class="p-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
						disabled={currentPage <= 1}
						on:click={prevPage}
						title="Previous page"
					>
						<ChevronLeft className="size-4" />
					</button>
					<!-- Page indicator -->
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
							Page {currentPage} of {totalPages}
						</span>
					</div>

					<!-- Next button -->
					<button
						class="p-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
						disabled={currentPage >= totalPages}
						on:click={nextPage}
						title="Next page"
					>
						<ChevronRight className="size-4" />
					</button>
				</div>

				<!-- Right side - Quick page jump (optional) -->
				<div class="flex items-center gap-2">
					{#if totalPages > 1}
						<label class="text-sm text-gray-600 dark:text-gray-400">Go to:</label>
						<select
							bind:value={currentPage}
							class="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
						>
							{#each Array(totalPages) as _, i}
								<option value={i + 1}>Page {i + 1}</option>
							{/each}
						</select>
					{/if}
				</div>
			</div>
		</div>
	</div>
</Modal>

<!-- Questions Asked Modal -->
<QuestionsAskedModal bind:show={showQuestionsModal} member={selectedMemberForQuestions} />

<style>
	.column-resizer {
		position: absolute;
		top: 0;
		right: -2px;
		width: 4px;
		height: 100%;
		cursor: col-resize;
		background: transparent;
		z-index: 10;
		border-right: 1px solid transparent;
		transition: border-color 0.2s ease;
	}

	.column-resizer:hover {
		border-right-color: #3b82f6;
		background: rgba(59, 130, 246, 0.1);
	}

	.column-resizer.resizing {
		border-right-color: #3b82f6;
		background: rgba(59, 130, 246, 0.2);
	}

	.table-container {
		overflow-x: auto;
	}

	.resizable-table {
		table-layout: fixed;
		min-width: 100%;
	}
</style>
