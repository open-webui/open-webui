<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { user, config } from '$lib/stores';
	import { WEBUI_NAME } from '$lib/stores';
	
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	
	let selectedRole = localStorage.getItem('selectedRole') || 'kids';
	let activeTab = 'overview'; // Default to overview tab
	let sexualExplicitness = 5; // Default value for the slider (0-10 range)
	
	// Graph state
	let plotPoints = [];
	let graphContainer;
	let isDrawing = false;
	let hoveredCoord = null;
	
	onMount(() => {
		// Check if user is authenticated
		if (!$user) {
			goto('/auth');
			return;
		}
		
		// Check if user has parent role
		if (selectedRole !== 'parents') {
			goto('/');
			return;
		}
	});
	
	function switchToKidsMode() {
		localStorage.setItem('selectedRole', 'kids');
		goto('/');
	}
	
	function goToAdmin() {
		goto('/admin');
	}
	
	function handleTabClick(tab) {
		activeTab = tab;
	}
	
	function handleSliderChange(event) {
		sexualExplicitness = parseInt(event.target.value);
	}
	
	// Graph interaction functions
	function handleGraphClick(event) {
		if (!graphContainer) return;
		const rect = graphContainer.getBoundingClientRect();
		const x = event.clientX - rect.left;
		const y = event.clientY - rect.top;
		const colCount = 5;
		const rowCount = 11;
		const colWidth = rect.width / colCount;
		const rowHeight = rect.height / (rowCount - 1);
		// Find the nearest column and row
		let graphX = Math.floor((x / rect.width) * colCount);
		let graphY = Math.round(((rect.height - y) / rect.height) * 10);
		// Only allow plotting for columns 1-4 (x=1,2,3,4)
		if (graphX < 1 || graphX > 4) return;
		if (graphY < 0 || graphY > 10) return;
		// Calculate the center of the nearest coordinate
		const centerX = (graphX) * colWidth;
		const centerY = rect.height - (graphY * rowHeight);
		const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
		if (distance > 30 || distance < -30) return; // Only plot if click is within 30px of the center
		const idx = plotPoints.findIndex(p => p.x === graphX && p.y === graphY);
		if (idx !== -1) {
			plotPoints = [...plotPoints.slice(0, idx), ...plotPoints.slice(idx + 1)];
		} else {
			plotPoints = [...plotPoints, { x: graphX, y: graphY }];
		}
	}
	
	function clearGraph() {
		plotPoints = [];
	}
	
	function removeLastPoint() {
		plotPoints = plotPoints.slice(0, -1);
	}
	
	function handleCoordinateHover(x, y) {
		console.log('Hovering over coordinate:', x, y);
		hoveredCoord = { x, y };
	}
	
	function handleCoordinateLeave() {
		console.log('Leaving coordinate');
		hoveredCoord = null;
	}
</script>

<svelte:head>
	<title>Parent Dashboard - {$WEBUI_NAME}</title>
	<style>
		.slider::-webkit-slider-thumb {
			appearance: none;
			height: 20px;
			width: 20px;
			border-radius: 50%;
			background: #3b82f6;
			cursor: pointer;
			box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
		}
		
		.slider::-moz-range-thumb {
			height: 20px;
			width: 20px;
			border-radius: 50%;
			background: #3b82f6;
			cursor: pointer;
			border: none;
			box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
		}
		
		.slider::-webkit-slider-track {
			background: linear-gradient(to right, #3b82f6 0%, #3b82f6 {sexualExplicitness * 10}%, #e5e7eb {sexualExplicitness * 10}%, #e5e7eb 100%);
		}
		
		.dark .slider::-webkit-slider-track {
			background: linear-gradient(to right, #3b82f6 0%, #3b82f6 {sexualExplicitness * 10}%, #374151 {sexualExplicitness * 10}%, #374151 100%);
		}
	</style>
</svelte:head>

<div class="w-full h-screen max-h-[100dvh] bg-white dark:bg-black text-black dark:text-white">
	<!-- Header -->
	<div class="w-full h-16 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-6">
		<div class="flex items-center space-x-4">
			<button
				on:click={switchToKidsMode}
				class="flex items-center space-x-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
			>
				<ArrowLeft className="size-4" />
				<span>Switch to Kids Mode</span>
			</button>
		</div>
		
		<div class="flex items-center space-x-4">
			<div class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
				<LockClosed className="size-4" />
				<span>Parent Mode</span>
			</div>
			
			{#if $user?.role === 'admin'}
				<button
					on:click={goToAdmin}
					class="flex items-center space-x-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
				>
					<Settings className="size-4" />
					<span>Admin Panel</span>
				</button>
			{/if}
		</div>
	</div>
	
	<!-- Main Content -->
	<div class="w-full h-full flex">
		<!-- Sidebar -->
		<div class="w-64 border-r border-gray-200 dark:border-gray-800 p-6">
			<div class="space-y-6">
				<div>
					<h2 class="text-lg font-semibold mb-4">Parent Dashboard</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Monitor and manage your child's AI learning experience
					</p>
				</div>
				
				<nav class="space-y-2">
					<button
						on:click={() => handleTabClick('overview')}
						class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'overview' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						<Eye className="size-4" />
						<span>Overview</span>
					</button>
					
					<button
						on:click={() => handleTabClick('activity')}
						class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'activity' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						<Calendar className="size-4" />
						<span>Activity History</span>
					</button>
					
					<button
						on:click={() => handleTabClick('conversations')}
						class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'conversations' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						<ChatBubble className="size-4" />
						<span>Conversations</span>
					</button>
					
					<button
						on:click={() => handleTabClick('users')}
						class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'users' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						<UserGroup className="size-4" />
						<span>User Management</span>
					</button>
					
					<button
						on:click={() => handleTabClick('policy')}
						class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'policy' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						<Settings className="size-4" />
						<span>Policy Making</span>
					</button>

					<button
						on:click={() => handleTabClick('graph')}
						class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'graph' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					>
						<ChartBar className="size-4" />
						<span>Graphs</span>
					</button>
				</nav>
			</div>
		</div>
		
		<!-- Main Content Area -->
		<div class="flex-1 p-6 md:p-12">
			<div class="max-w-4xl mx-auto">
				{#if activeTab === 'overview'}
					<!-- Welcome Section -->
					<div class="mb-8">
						<h1 class="text-3xl font-bold mb-2">Welcome to Parent Dashboard</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Monitor your child's learning progress and manage their AI interactions safely.
						</p>
					</div>
					
					<!-- Stats Grid -->
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
						<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Sessions</p>
									<p class="text-2xl font-bold">24</p>
								</div>
								<Calendar className="size-8 text-blue-500" />
							</div>
						</div>
						
						<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Active Users</p>
									<p class="text-2xl font-bold">3</p>
								</div>
								<UserGroup className="size-8 text-green-500" />
							</div>
						</div>
						
						<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Messages Today</p>
									<p class="text-2xl font-bold">156</p>
								</div>
								<ChatBubble className="size-8 text-purple-500" />
							</div>
						</div>
						
						<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Safety Score</p>
									<p class="text-2xl font-bold">98%</p>
								</div>
								<LockClosed className="size-8 text-yellow-500" />
							</div>
						</div>
					</div>
					
					<!-- Quick Actions -->
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-8">
						<h3 class="text-lg font-semibold mb-4">Quick Actions</h3>
						<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
							<button
								on:click={() => goto('/admin/users')}
								class="flex items-center space-x-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
							>
								<UserGroup className="size-5 text-blue-500" />
								<span class="text-sm font-medium">Manage Users</span>
							</button>
							
							<button
								on:click={() => goto('/admin/settings')}
								class="flex items-center space-x-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
							>
								<Settings className="size-5 text-green-500" />
								<span class="text-sm font-medium">System Settings</span>
							</button>
							
							<button
								on:click={() => goto('/')}
								class="flex items-center space-x-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
							>
								<ChatBubble className="size-5 text-purple-500" />
								<span class="text-sm font-medium">View Chats</span>
							</button>
						</div>
					</div>
					
					<!-- Recent Activity -->
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
						<h3 class="text-lg font-semibold mb-4">Recent Activity</h3>
						<div class="space-y-4">
							<div class="flex items-center space-x-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
								<div class="w-2 h-2 bg-green-500 rounded-full"></div>
								<div class="flex-1">
									<p class="text-sm font-medium">New user session started</p>
									<p class="text-xs text-gray-600 dark:text-gray-400">2 minutes ago</p>
								</div>
							</div>
							
							<div class="flex items-center space-x-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
								<div class="w-2 h-2 bg-blue-500 rounded-full"></div>
								<div class="flex-1">
									<p class="text-sm font-medium">Safety filter triggered</p>
									<p class="text-xs text-gray-600 dark:text-gray-400">15 minutes ago</p>
								</div>
							</div>
							
							<div class="flex items-center space-x-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
								<div class="w-2 h-2 bg-yellow-500 rounded-full"></div>
								<div class="flex-1">
									<p class="text-sm font-medium">Daily usage limit reached</p>
									<p class="text-xs text-gray-600 dark:text-gray-400">1 hour ago</p>
								</div>
							</div>
						</div>
					</div>
				{:else if activeTab === 'policy'}
					<!-- Policy Making Survey -->
					<div class="mb-8 mt-10 md:mt-16 px-4 md:px-8">
						<h1 class="text-3xl font-bold mb-4">Content Policy Configuration</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Configure how the AI should respond to sensitive topics for your child's safety.
						</p>
					</div>
					<!-- Make the survey box scrollable and add extra bottom margin -->
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 md:p-12 mx-auto max-w-3xl shadow-lg flex flex-col max-h-[70vh] min-h-[400px] overflow-y-auto mb-24">
						<div class="max-w-2xl mx-auto">
							<!-- Question 1: Sexual Content Explicitness -->
							<div class="mb-10 mt-10">
								<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
									How explicit would you like responses regarding sexual topics to be?
								</h3>
								<div class="space-y-4">
									<!-- Slider -->
									<div class="relative">
										<input
											type="range"
											min="0"
											max="10"
											value={sexualExplicitness}
											on:input={handleSliderChange}
											class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 slider"
										/>
										<!-- Slider Labels -->
										<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-2">
											<span>0 - Very Conservative</span>
											<span>5 - Moderate</span>
											<span>10 - Very Explicit</span>
										</div>
									</div>
									<!-- Current Value Display -->
									<div class="text-center">
										<span class="inline-block bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-sm font-medium">
											Current Setting: {sexualExplicitness}/10
										</span>
									</div>
									<!-- Description -->
									<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
										<p class="text-sm text-gray-600 dark:text-gray-400">
											This setting controls how detailed and explicit the AI can be when discussing sexual topics, 
											anatomy, relationships, and related subjects. Lower values provide more conservative, 
											age-appropriate responses, while higher values allow for more detailed explanations.
										</p>
									</div>
								</div>
							</div>
							<hr class="my-10 border-t border-gray-300 dark:border-gray-700" />
							<!-- Question 2: Ideal Example Response Selection -->
							<div class="mb-8 mt-10">
								<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
									Which of these responses do you feel is ideal for the following child-given prompt: <span class="italic">XXX</span>
								</h3>
								<div class="space-y-4">
									<label class="flex items-start space-x-3 cursor-pointer p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition">
										<input type="radio" name="idealResponse" class="mt-1 accent-blue-500" />
										<span class="text-gray-800 dark:text-gray-200">insert example response</span>
									</label>
									<label class="flex items-start space-x-3 cursor-pointer p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition">
										<input type="radio" name="idealResponse" class="mt-1 accent-blue-500" />
										<span class="text-gray-800 dark:text-gray-200">insert example response</span>
									</label>
									<label class="flex items-start space-x-3 cursor-pointer p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition">
										<input type="radio" name="idealResponse" class="mt-1 accent-blue-500" />
										<span class="text-gray-800 dark:text-gray-200">insert example response</span>
									</label>
								</div>
							</div>
							
							<hr class="my-10 border-t border-gray-300 dark:border-gray-700" />
							
							<!-- Question 3: Violence Content Tolerance -->
							<div class="mb-8 mt-10">
								<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
									How much violence content tolerance would you like for your child?
								</h3>
								<div class="space-y-4">
									<!-- Slider -->
									<div class="relative">
										<input
											type="range"
											min="0"
											max="10"
											value="3"
											class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 slider"
										/>
										<!-- Slider Labels -->
										<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-2">
											<span>0 - No Violence</span>
											<span>5 - Moderate</span>
											<span>10 - High Tolerance</span>
										</div>
									</div>
									<!-- Current Value Display -->
									<div class="text-center">
										<span class="inline-block bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200 px-3 py-1 rounded-full text-sm font-medium">
											Current Setting: 3/10
										</span>
									</div>
									<!-- Description -->
									<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
										<p class="text-sm text-gray-600 dark:text-gray-400">
											This setting controls how much violence, conflict, or aggressive content the AI can include in responses. 
											Lower values ensure more peaceful, non-violent interactions, while higher values allow for more realistic 
											discussions about conflicts and historical events.
										</p>
									</div>
								</div>
							</div>
							
							<hr class="my-10 border-t border-gray-300 dark:border-gray-700" />
							
							<!-- Question 4: Educational Content Depth -->
							<div class="mb-8 mt-10">
								<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
									How detailed should educational explanations be?
								</h3>
								<div class="space-y-4">
									<!-- Slider -->
									<div class="relative">
										<input
											type="range"
											min="0"
											max="10"
											value="7"
											class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 slider"
										/>
										<!-- Slider Labels -->
										<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-2">
											<span>0 - Simple</span>
											<span>5 - Balanced</span>
											<span>10 - Very Detailed</span>
										</div>
									</div>
									<!-- Current Value Display -->
									<div class="text-center">
										<span class="inline-block bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-200 px-3 py-1 rounded-full text-sm font-medium">
											Current Setting: 7/10
										</span>
									</div>
									<!-- Description -->
									<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
										<p class="text-sm text-gray-600 dark:text-gray-400">
											This setting determines how in-depth educational explanations should be. Lower values provide simple, 
											age-appropriate explanations, while higher values include more complex concepts, examples, and detailed 
											explanations suitable for advanced learners.
										</p>
									</div>
								</div>
							</div>
							
							<!-- Save Button -->
							<div class="flex justify-end">
								<button
									class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
								>
									Save Policy Settings
								</button>
							</div>
						</div>
					</div>
				{:else if activeTab === 'graph'}
					<!-- Graphs Section -->
					<div class="mb-8 mt-10 md:mt-16 px-4 md:px-8">
						<h1 class="text-3xl font-bold mb-4">Interactive Graph</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Click anywhere on the graph to place plot points. The graph spans from 0 to 10 on both X and Y axes.
						</p>
					</div>
					
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 md:p-12 mx-auto max-w-4xl shadow-lg">
						<!-- Graph Controls -->
						<div class="flex justify-between items-center mb-6">
							<div class="flex space-x-4">
								<button
									on:click={clearGraph}
									class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors"
								>
									Clear All Points
								</button>
								<button
									on:click={removeLastPoint}
									class="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg font-medium transition-colors"
									disabled={plotPoints.length === 0}
								>
									Remove Last Point
								</button>
							</div>
							<div class="text-sm text-gray-600 dark:text-gray-400">
								Points placed: {plotPoints.length}
							</div>
						</div>
						
						<!-- Top column labels with title and divider -->
						<div class="relative w-full mb-2" style="height: 40px;">
							<!-- Title cell -->
							<div class="absolute left-0 top-0 h-full flex items-center justify-center" style="left: 5px; width: 120px; z-index: 10;">
								<span class="font-bold text-center w-full text-sm mb-3">Example Prompt</span>
							</div>
							<!-- Divider -->
							<div class="absolute" style="left: 132px; top: 0%; height: 70%; width: 1px; background: #d1d5db; z-index: 10;"></div>
							<!-- Label above X=1 column (second column, 20% from left) -->
							<div class="absolute" style="left: 20%; transform: translateX(-50%);">
								<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
									"What is sexual reproduction?"
								</span>
							</div>
							<!-- Label above X=2 column (third column, 40% from left) -->
							<div class="absolute" style="left: 40%; transform: translateX(-50%);">
								<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
									[insert topic]
								</span>
							</div>
							<!-- Label above X=3 column (fourth column, 60% from left) -->
							<div class="absolute" style="left: 60%; transform: translateX(-50%);">
								<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
									[insert topic]
								</span>
							</div>
							<!-- Label above X=4 column (fifth column, 80% from left) -->
							<div class="absolute" style="left: 80%; transform: translateX(-50%);">
								<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
									[insert topic]
								</span>
							</div>
						</div>

						<!-- Interactive Graph -->
						<div class="relative bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
							<div
								bind:this={graphContainer}
								class="relative w-full h-96 cursor-crosshair"
								on:click={handleGraphClick}
							>
								<!-- Grid Lines -->
								<svg class="absolute inset-0 w-full h-full pointer-events-none">
									<!-- Vertical grid lines -->
									{#each Array(5 + 1) as _, i}
										<line
											x1={(i * 100) / 5}%
											y1="0"
											x2={(i * 100) / 5}%
											y2="100%"
											stroke="currentColor"
											stroke-width="1"
											class="text-gray-300 dark:text-gray-700"
										/>
									{/each}
									<!-- Horizontal grid lines -->
									{#each Array(11) as _, i}
										<line
											x1="0"
											y1={(i * 100) / 10}%
											x2="100%"
											y2={(i * 100) / 10}%
											stroke="currentColor"
											stroke-width="1"
											class="text-gray-300 dark:text-gray-700"
										/>
									{/each}
									<!-- Axes -->
									<line x1="0" y1="100%" x2="100%" y2="100%" stroke="currentColor" stroke-width="2" class="text-gray-800 dark:text-gray-200" />
									<line x1="0" y1="0" x2="0" y2="100%" stroke="currentColor" stroke-width="2" class="text-gray-800 dark:text-gray-200" />
								</svg>
								
								<!-- Interactive Coordinate Hover Areas -->
								{#each Array(4) as _, x}
									{#each Array(11) as _, y}
										{@const coordX = x + 1}
										{@const coordY = y}
										{#if coordY !== 0 && coordY !== 10}
										<div
											class="absolute w-2 h-2 rounded-full cursor-pointer bg-blue-400 bg-opacity-30 hover:bg-blue-500 hover:bg-opacity-60 border-2 border-blue-300 transition-colors duration-150"
											style="left: {(coordX * 100) / 5}%; top: {100 - (coordY * 100) / 10}%; transform: translate(-4px, -4px);"
											on:mouseenter={() => handleCoordinateHover(coordX, coordY)}
											on:mouseleave={handleCoordinateLeave}
											on:click={(e) => {
												e.stopPropagation();
												handleGraphClick(e);
											}}
										>
										</div>
										{/if}
									{/each}
								{/each}
								
								<!-- Global Tooltip -->
								{#if hoveredCoord}
									<div 
										class="absolute bg-red-600 text-white text-xs px-2 py-1 rounded pointer-events-none z-50 border border-white"
										style="left: {(hoveredCoord.x * 100) / 5}%; top: {100 - (hoveredCoord.y * 100) / 10 - 8}%; max-width: 25ch; transform: translateX(5%);"
									>
										insert example response here
									</div>
								{/if}
								
								<!-- Plot Points -->
								{#each plotPoints as point, index}
									<div
										class="absolute w-2 h-2 bg-blue-500 rounded-full border-2 border-white dark:border-gray-800 pointer-events-none z-20"
										style="left: {(point.x * 100) / 5}%; top: {100 - (point.y * 100) / 10}%; transform: translate(-4px, -4px);"
									>
									</div>
								{/each}
								
								<!-- Axis Labels -->
							</div>
							<!-- Bottom column labels with title and divider -->
							<div class="relative w-full mt-2" style="height: 35px;">
								<!-- Title cell -->
								<div class="absolute left-0 top-0 h-full flex items-center justify-center" style="left: 5px; width: 120px; z-index: 10;">
									<span class="font-bold text-center w-full text-sm mb-2">Topic</span>
								</div>
								<!-- Divider -->
								<div class="absolute" style="left: 130px; top: 5%; height: 70%; width: 1px; background: #d1d5db; z-index: 10;"></div>
								<!-- Label under X=1 column (second column, 20% from left) -->
								<div class="absolute" style="left: 20%; transform: translateX(-50%);">
									<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
										Sex
									</span>
								</div>
								<!-- Label under X=2 column (third column, 40% from left) -->
								<div class="absolute" style="left: 40%; transform: translateX(-50%);">
									<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
										[insert topic]
									</span>
								</div>
								<!-- Label under X=3 column (fourth column, 60% from left) -->
								<div class="absolute" style="left: 60%; transform: translateX(-50%);">
									<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
										[insert topic]
									</span>
								</div>
								<!-- Label under X=4 column (fifth column, 80% from left) -->
								<div class="absolute" style="left: 80%; transform: translateX(-50%);">
									<span class="text-sm text-gray-600 dark:text-gray-400 break-words inline-block text-center" style="max-width: 20ch;">
										[insert topic]
									</span>
								</div>
							</div>
						</div>
						
						<!-- Points List -->
						{#if plotPoints.length > 0}
							<div class="mt-6">
								<h3 class="text-lg font-semibold mb-3">Plotted Points:</h3>
								<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
									{#each plotPoints as point, index}
										<div class="bg-gray-100 dark:bg-gray-700 rounded px-3 py-2 text-sm">
											Point {index + 1}: ({point.x}, {point.y})
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<!-- Placeholder for other tabs -->
					<div class="text-center py-12">
						<h2 class="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
							{activeTab === 'activity' ? 'Activity History' : 
							 activeTab === 'conversations' ? 'Conversations' : 
							 activeTab === 'users' ? 'User Management' : 'Coming Soon'}
						</h2>
						<p class="text-gray-600 dark:text-gray-400">
							This feature is under development and will be available soon.
						</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div> 