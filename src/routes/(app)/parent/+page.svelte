<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	
	const i18n = getContext<Writable<i18nType>>('i18n');
	
	import { user, config, models, type Model } from '$lib/stores';
	import { WEBUI_NAME } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';
	import { updateModelById, getModels as getWorkspaceModels } from '$lib/apis/models';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { applyModeration, type ModerationResponse } from '$lib/apis/moderation';
	import { toast } from 'svelte-sonner';
	
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	
	// Type definitions
	interface PlotPoint {
		x: number;
		y: number;
	}

	interface ChatMessage {
		role: 'user' | 'assistant';
		content: string;
		timestamp: string;
		loading?: boolean;
	}

	type PoliticsOption = 'objectively' | 'noSpecific' | 'noPolitics';
	type SecondQuestionOption = 'option1' | 'option2' | 'option3';
	type Tab =
		| 'overview'
		| 'child_profile'
		| 'activity'
		| 'conversations'
		| 'users'
		| 'policy'
		| 'childgpt'
		| 'graph'
		| 'playground'
		| 'parent_quiz_ii';

	let selectedRole: string = localStorage.getItem('selectedRole') || 'kids';
	let activeTab: Tab = 'overview'; // Default to overview tab
	let sexualExplicitness: number = 5; // Default value for the slider (0-10 range)
	let sidebarCollapsed: boolean = false; // State for sidebar collapse
	
	// Child profile data
	let childAge: string = '';
	let childGender: string = '';
	let childCharacteristics: string = '';
	let parentGender: string = '';
	let parentAge: string = '';
	let parentPreference: string = '';
	let parentingStyle: string = '';
	let profileSubmitted: boolean = false; // Track if profile has been submitted
	let isEditingProfile: boolean = false; // Track if in edit mode

	// Graph state
	let plotPoints: PlotPoint[] = [];
	let graphContainer: HTMLDivElement;
	let isDrawing: boolean = false;
	let hoveredCoord: PlotPoint | null = null;

	// Policy questions state
	let showObjectiveExample: boolean = false;
	let showNoSpecificExample: boolean = false;
	let showNoPoliticsExample: boolean = false;
	let currentPolicyQuestion: number = 0; // Track which policy question is currently shown
	const totalPolicyQuestions: number = 2; // Total number of policy questions

	// Hover state for interactive examples
	let hoveredPoliticsOption: PoliticsOption | null = null;
	let hoveredSecondOption: SecondQuestionOption | null = null;

	// Policy questions with choices and instructions
	const politicsChoices = {
		objectively: {
			title: "Objectively",
			description: "Provide factual information about political figures and topics while acknowledging different viewpoints exist.",
			example: "Hi there! Donald Trump is a well-known businessman and was the 45th President of the United States. People have different opinions about him, just like with many leaders. Some people think he did a good job, while others have different thoughts. It's important to learn about different leaders and make up your own mind about what you think. If you want to learn more about him, you can ask your family or look for information from different places.",
			instruction: "child_demographics : Age 7, boy."
		},
		noSpecific: {
			title: "No Mentions of Specific Political Figures/Viewpoints",
			description: "Avoid discussing specific political figures or viewpoints while still acknowledging the question.",
			example: "It's great that you're curious and asking questions! Donald Trump is a person who was a leader in the United States. People have different opinions about him, just like how people might feel differently about characters in stories or movies. If you want to know more about what he did, it might be helpful to talk to your parents or another trusted adult who can give you a little more information that's right for you. If you have any other questions, feel free to ask!",
			instruction: "parent_rules: Do not mention politics. child_demographics : Age 7, boy."
		},
		noPolitics: {
			title: "No Mentions of Politics in General",
			description: "Redirect the conversation away from political topics entirely to other engaging subjects.",
			example: "Hello! Let's find something really amazing to talk about. How about I tell you about some cool animals or fun science facts instead? Just let me know what you're curious about or if there's something else you'd like to learn!",
			instruction: "parent_rules: It is important to not mention ANYTHING regarding politics, political figures, political rules, or political structure..                              child_demographics : Age 7, boy."
		}
	};

	// Second policy question choices (placeholder content)
	const secondQuestionChoices = {
		option1: {
			title: "[Option 1 Title]",
			description: "[Option 1 description placeholder text]",
			example: "[Example response placeholder for option 1]",
			instruction: "[Instruction for option 1]"
		},
		option2: {
			title: "[Option 2 Title]",
			description: "[Option 2 description placeholder text]",
			example: "[Example response placeholder for option 2]",
			instruction: "[Instruction for option 2]"
		},
		option3: {
			title: "[Option 3 Title]",
			description: "[Option 3 description placeholder text]",
			example: "[Example response placeholder for option 3]",
			instruction: "[Instruction for option 3]"
		}
	};

	// Selected values for radio buttons
	let selectedPoliticsResponse: PoliticsOption | null = null;
	let selectedSecondQuestion: SecondQuestionOption | null = null; // For the second policy question

	// Policy system prompt state
	let policySystemPrompt: string = '';
	let showPolicyPreview = false;
	let savingPolicies = false;
	
	// My Child's GPT state
	let selectedChildGPTModel = '';
	let childGPTModelId = '';
	let loadingChildGPT = false;
	
	// Playground chat state
	let chatMessages: ChatMessage[] = [];
	let currentMessage = '';
	let sendingMessage = false;
	let childGPTName = '';
	
	const moderationOptions = [
		'Refuse Response and Explain',
		'Remove Harmful Phrases',
		'Omit Unprompted Suggestions',
		'Do Not Suggest Workarounds',
		'Clarify Child\'s Intent',
		'Emphasize Emotional Support',
		'Explain Problems in Prompt',
		'Emphasize Risk Awareness',
		'Redirect with Alternatives',
		'Remind Model is Not Human',
		'Encourage Introspection',
		'Tailor to Age Group',
		'Defer to Parents',
		'Defer to Resources'
	];

	// Moderation state
	let moderationResult: ModerationResponse | null = null;
	let moderationLoading: boolean = false;

	async function handleModerationClick(option: string) {
		console.log(`Moderation option selected: ${option}`);
		moderationLoading = true;
		moderationResult = null;

		try {
			const result = await applyModeration(
				localStorage.token,
				option,
				'Who is Trump? Is he a good guy?' // Using the example prompt from the interaction
			);
			
			if (result) {
				moderationResult = result;
				toast.success(`Moderation applied: ${option}`);
			} else {
				toast.error('Failed to apply moderation');
			}
		} catch (error: any) {
			console.error('Error applying moderation:', error);
			toast.error(`Error: ${error.detail || error.message || 'Failed to apply moderation'}`);
		} finally {
			moderationLoading = false;
		}
	}
	
	onMount(() => {
		const init = async () => {
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
			
			// Load models and child GPT model
			await loadModels();
			await loadChildGPTModel();
			
			// Check for saved sidebar state
			const savedSidebarState = localStorage.getItem('parentDashboardSidebarCollapsed');
			if (savedSidebarState !== null) {
				sidebarCollapsed = savedSidebarState === 'true';
			}
			
			// Load child profile data
			loadChildProfile();
		};
		init();
		
		// Add responsive behavior for mobile
		const handleResize = () => {
			if (window.innerWidth < 768) {
				sidebarCollapsed = true;
			}
		};
		
		// Initial check
		handleResize();
		
		// Add event listener
		window.addEventListener('resize', handleResize);
		
		// Cleanup
		return () => {
			window.removeEventListener('resize', handleResize);
		};
	});
	
	function switchToKidsMode() {
		localStorage.setItem('selectedRole', 'kids');
		goto('/');
	}
	
	function goToAdmin() {
		goto('/admin');
	}
	
	function handleTabClick(tab: Tab) {
		// If navigating away from playground tab, clear the chat
		if (activeTab === 'playground' && tab !== 'playground') {
			chatMessages = [];
			currentMessage = '';
		}
		
		activeTab = tab;
		if (sidebarCollapsed) {
			// Auto-expand sidebar when changing tabs on mobile
			sidebarCollapsed = false;
		}
	}
	
	function toggleSidebar() {
		sidebarCollapsed = !sidebarCollapsed;
		// Save sidebar state to localStorage
		localStorage.setItem('parentDashboardSidebarCollapsed', String(sidebarCollapsed));
	}
	
	// Child profile functions
	function saveChildProfile() {
		const childProfile = {
			childAge,
			childGender,
			childCharacteristics,
			parentGender,
			parentAge,
			parentPreference,
			parentingStyle,
			profileSubmitted: true
		};
		localStorage.setItem('childProfile', JSON.stringify(childProfile));
		profileSubmitted = true;
		isEditingProfile = false;
		toast.success('Child profile saved successfully!');
	}
	
	function loadChildProfile() {
		const saved = localStorage.getItem('childProfile');
		if (saved) {
			const profile = JSON.parse(saved);
			childAge = profile.childAge || '';
			childGender = profile.childGender || '';
			childCharacteristics = profile.childCharacteristics || '';
			parentGender = profile.parentGender || '';
			parentAge = profile.parentAge || '';
			parentPreference = profile.parentPreference || '';
			parentingStyle = profile.parentingStyle || '';
			profileSubmitted = profile.profileSubmitted || false;
		}
	}
	
	function startEditingProfile() {
		isEditingProfile = true;
	}
	
	// Helper function to format display values
	function formatDisplayValue(value: string, type: string): string {
		if (!value) return 'Not specified';
		
		switch (type) {
			case 'age':
				return value === '60+' ? '60+' : `${value} years old`;
			case 'gender':
				return value.charAt(0).toUpperCase() + value.slice(1);
			case 'ageRange':
				return value;
			default:
				return value;
		}
	}
	
	function handleSliderChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target) {
			sexualExplicitness = parseInt(target.value);
		}
	}
	
	// Graph interaction functions
	function handleGraphClick(event: MouseEvent) {
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
		const centerX = graphX * colWidth;
		const centerY = rect.height - graphY * rowHeight;
		const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
		if (distance > 30 || distance < -30) return; // Only plot if click is within 30px of the center
		const idx = plotPoints.findIndex((p) => p.x === graphX && p.y === graphY);
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
	
	function handleCoordinateHover(x: number, y: number) {
		console.log('Hovering over coordinate:', x, y);
		hoveredCoord = { x, y };
	}
	
	function handleCoordinateLeave() {
		console.log('Leaving coordinate');
		hoveredCoord = null;
	}
	
	// Politics question functions
	function toggleObjectiveExample() {
		showObjectiveExample = !showObjectiveExample;
	}
	
	function toggleNoSpecificExample() {
		showNoSpecificExample = !showNoSpecificExample;
	}
	
	function toggleNoPoliticsExample() {
		showNoPoliticsExample = !showNoPoliticsExample;
	}
	
	// Radio button toggle functions
	function togglePoliticsResponse(value: PoliticsOption) {
		selectedPoliticsResponse = selectedPoliticsResponse === value ? null : value;
		hoveredPoliticsOption = selectedPoliticsResponse;
		buildPolicySystemPrompt();
	}

	function toggleSecondQuestion(value: SecondQuestionOption) {
		selectedSecondQuestion = selectedSecondQuestion === value ? null : value;
		hoveredSecondOption = selectedSecondQuestion;
		buildPolicySystemPrompt();
	}
	
	// Navigation functions for policy questions
	function nextPolicyQuestion() {
		if (currentPolicyQuestion < totalPolicyQuestions - 1) {
			currentPolicyQuestion++;
		}
	}
	
	function prevPolicyQuestion() {
		if (currentPolicyQuestion > 0) {
			currentPolicyQuestion--;
		}
	}
	
	// Policy system prompt functions
	function buildPolicySystemPrompt() {
		const instructions: string[] = [];
		let instructionNumber = 1;
		
		// Add politics instruction if selected
		if (selectedPoliticsResponse && politicsChoices[selectedPoliticsResponse]) {
			instructions.push(`${instructionNumber}. ${politicsChoices[selectedPoliticsResponse].instruction}`);
			instructionNumber++;
		}
		
		// Add second question instruction if selected
		if (selectedSecondQuestion && secondQuestionChoices[selectedSecondQuestion]) {
			instructions.push(`${instructionNumber}. ${secondQuestionChoices[selectedSecondQuestion].instruction}`);
			instructionNumber++;
		}
		
		// Future policy questions will be added here
		// Example: if (selectedContentFilter) { instructions.push(`${instructionNumber}. ${contentFilterChoices[selectedContentFilter].instruction}`); instructionNumber++; }
		
		policySystemPrompt = instructions.join('\n');
	}
	
	async function openPolicyPreview() {
		// Validate that a child's GPT model is selected
		if (!childGPTModelId) {
			toast.error('Please select a model for "My Child\'s GPT" first');
			return;
		}
		
		// Validate that at least one policy choice is made
		if (!selectedPoliticsResponse && !selectedSecondQuestion) {
			toast.error('Please select at least one policy choice');
			return;
		}
		
		buildPolicySystemPrompt();
		showPolicyPreview = true;
	}
	
	async function confirmPolicies() {
		if (!childGPTModelId) {
			toast.error('No child\'s GPT model selected');
			return;
		}
		
		if (!policySystemPrompt) {
			toast.error('No policy instructions to apply');
			return;
		}
		
		savingPolicies = true;
		
		try {
			// Get the workspace models (custom models) instead of general models
			const workspaceModels = await getWorkspaceModels(localStorage.token);
			const childModel = workspaceModels.find((model: Model) => model.id === childGPTModelId);
			
			if (!childModel) {
				toast.error("Selected child's GPT model not found in workspace models");
				return;
			}
			
			console.log('Child model structure:', childModel);
			
			// Update the model's system prompt in the params field
			const updatedModel = {
				id: childModel.id,
				base_model_id: childModel.base_model_id,
				name: childModel.name,
				meta: childModel.meta,
				params: {
					...childModel.params,
					system: policySystemPrompt
				},
				access_control: childModel.access_control,
				is_active: childModel.is_active
			};
			
			console.log('Updated model structure:', updatedModel);
			
			// Save the updated model
			const res = await updateModelById(localStorage.token, childModel.id, updatedModel);
			
			if (res) {
				toast.success("Policy settings applied successfully to your child's GPT!");
				showPolicyPreview = false;
			} else {
				toast.error('Failed to apply policy settings');
			}
		} catch (error) {
			console.error('Error applying policy settings:', error);
			toast.error('Failed to apply policy settings');
		}
		
		savingPolicies = false;
	}
	
	// My Child's GPT functions
	async function loadModels() {
		if ($models.length === 0) {
			models.set(await getModels(localStorage.token));
		}
	}
	
	async function saveChildGPTModel() {
		if (!selectedChildGPTModel) {
			toast.error('Please select a model first');
			return;
		}
		
		loadingChildGPT = true;
		
		try {
			// Get current config
			const currentConfig = await getModelsConfig(localStorage.token);
			
			// Save the selected model as "My Child's GPT"
			const res = await setModelsConfig(localStorage.token, {
				...currentConfig,
				CHILD_GPT_MODEL: selectedChildGPTModel
			});
			
			if (res) {
				childGPTModelId = selectedChildGPTModel;
				toast.success('My Child\'s GPT model saved successfully!');
			} else {
				toast.error('Failed to save My Child\'s GPT model');
			}
		} catch (error) {
			console.error('Error saving Child GPT model:', error);
			toast.error('Failed to save My Child\'s GPT model');
		}
		
		loadingChildGPT = false;
	}
	
	async function loadChildGPTModel() {
		try {
			const config = await getModelsConfig(localStorage.token);
			if (config?.CHILD_GPT_MODEL) {
				childGPTModelId = config.CHILD_GPT_MODEL;
				selectedChildGPTModel = config.CHILD_GPT_MODEL;
				
				// Get the model name for display in chat
				const model = $models.find(m => m.id === childGPTModelId);
				if (model) {
					childGPTName = model.name;
				} else {
					childGPTName = "My Child's GPT";
				}
			}
		} catch (error) {
			console.error('Error loading Child GPT model:', error);
		}
	}
	
	// Playground chat functions
	async function sendMessage() {
		if (!currentMessage.trim() || sendingMessage) return;
		if (!childGPTModelId) {
			toast.error('Please set up "My Child\'s GPT" model first');
			return;
		}
		
		const userMessage: ChatMessage = {
			role: 'user',
			content: currentMessage,
			timestamp: new Date().toISOString()
		};
		
		chatMessages = [...chatMessages, userMessage];
		const messageToSend = currentMessage;
		currentMessage = '';
		sendingMessage = true;
		
		// Add a temporary assistant message with loading state
		const tempAssistantMessage: ChatMessage = {
			role: 'assistant',
			content: '...',
			loading: true,
			timestamp: new Date().toISOString()
		};
		
		chatMessages = [...chatMessages, tempAssistantMessage];
		
		try {
			// Create message history for the API call
			const messageHistory = chatMessages
				.slice(0, -1) // Exclude the temporary loading message
				.map((msg) => ({
					role: msg.role,
					content: msg.content
				}));
			
			// Call the OpenAI-compatible API endpoint with the selected child's GPT model
			const response = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: childGPTModelId,
					messages: messageHistory,
					stream: false
				}
			);
			
			if (!response) {
				throw new Error('No response received');
			}
			
			if (response.error) {
				throw new Error(response.error);
			}
			
			// Extract the assistant's response
			const content = response.choices?.[0]?.message?.content || 'No response content';
			
			// Replace the temporary message with the actual response
			const assistantMessage: ChatMessage = {
				role: 'assistant',
				content: content,
				timestamp: new Date().toISOString()
			};
			
			chatMessages = [...chatMessages.slice(0, -1), assistantMessage];
		} catch (error: any) {
			console.error('Error sending message:', error);
			toast.error(`Failed to send message: ${error.message || 'Unknown error'}`);
			
			// Remove the loading message
			chatMessages = chatMessages.slice(0, -1);
		}
		
		sendingMessage = false;
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
			
			<!-- Mobile Sidebar Toggle -->
			<button
				on:click={toggleSidebar}
				class="md:hidden flex items-center space-x-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
			>
				{#if sidebarCollapsed}
					<ChevronRight className="size-4" />
					<span>Show Menu</span>
				{:else}
					<ChevronLeft className="size-4" />
					<span>Hide Menu</span>
				{/if}
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
		<div class="{sidebarCollapsed ? 'w-0 md:w-16 border-0 md:border-r' : 'w-64'} relative flex flex-col transition-all duration-300 ease-in-out border-r border-gray-200 dark:border-gray-800">
			<!-- Toggle Button (hidden on mobile) -->
			<button 
				on:click={toggleSidebar}
				class="absolute -right-3 top-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full p-1 z-10 shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors hidden md:block"
			>
				{#if sidebarCollapsed}
					<ChevronRight className="size-4 text-gray-600 dark:text-gray-300" />
				{:else}
					<ChevronLeft className="size-4 text-gray-600 dark:text-gray-300" />
				{/if}
			</button>
			
			<div class="{sidebarCollapsed ? 'hidden md:block' : ''} p-6 space-y-6 flex-1 overflow-y-auto">
				<div class="{sidebarCollapsed ? 'items-center' : ''}">
					<h2 class="text-lg font-semibold mb-4 {sidebarCollapsed ? 'sr-only' : ''}">Parent Dashboard</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400 {sidebarCollapsed ? 'sr-only' : ''}">
						Monitor and manage your child's AI learning experience
					</p>
				</div>
				
				<nav class="space-y-2">
					<button
						on:click={() => handleTabClick('overview')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'overview' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Overview"
					>
						<Eye className="size-4" />
						{#if !sidebarCollapsed}
							<span>Overview</span>
						{/if}
					</button>
					
					<button
						on:click={() => handleTabClick('child_profile')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'child_profile' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Child Profile"
					>
						<UserGroup className="size-4" />
						{#if !sidebarCollapsed}
							<span>Child Profile</span>
						{/if}
					</button>
					
					<button
						on:click={() => handleTabClick('activity')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'activity' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Activity History"
					>
						<Calendar className="size-4" />
						{#if !sidebarCollapsed}
							<span>Activity History</span>
						{/if}
					</button>
					
					<button
						on:click={() => handleTabClick('conversations')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'conversations' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Conversations"
					>
						<ChatBubble className="size-4" />
						{#if !sidebarCollapsed}
							<span>Conversations</span>
						{/if}
					</button>
					
					<button
						on:click={() => handleTabClick('users')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'users' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="User Management"
					>
						<UserGroup className="size-4" />
						{#if !sidebarCollapsed}
							<span>User Management</span>
						{/if}
					</button>
					
					<button
						on:click={() => handleTabClick('policy')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'policy' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Policy Making"
					>
						<Settings className="size-4" />
						{#if !sidebarCollapsed}
							<span>Policy Making</span>
						{/if}
					</button>

					<button
						on:click={() => handleTabClick('childgpt')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'childgpt' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="My Child's GPT"
					>
						<ChatBubble className="size-4" />
						{#if !sidebarCollapsed}
							<span>My Child's GPT</span>
						{/if}
					</button>

					<button
						on:click={() => handleTabClick('graph')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'graph' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Graphs"
					>
						<ChartBar className="size-4" />
						{#if !sidebarCollapsed}
							<span>Graphs</span>
						{/if}
					</button>
					
					<button
						on:click={() => handleTabClick('playground')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'playground' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Playground"
					>
						<Sparkles className="size-4" />
						{#if !sidebarCollapsed}
							<span>Playground</span>
						{/if}
					</button>

					<button
						on:click={() => handleTabClick('parent_quiz_ii')}
						class="w-full flex items-center {sidebarCollapsed ? 'justify-center' : 'space-x-3'} px-3 py-2 rounded-lg text-sm font-medium transition-colors {activeTab === 'parent_quiz_ii' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						title="Parent Quiz II"
					>
						<Sparkles className="size-4" />
						{#if !sidebarCollapsed}
							<span>Parent Quiz II</span>
						{/if}
					</button>
				</nav>
			</div>
		</div>
		
		<!-- Main Content Area -->
		<div class="flex-1 p-6 md:p-12">
			<div class="max-w-4xl mx-auto">
				{#if activeTab === 'overview'}
					<!-- Welcome Section -->
					<div class="mb-4 mt-2">
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
				{:else if activeTab === 'child_profile'}
					<!-- Child Profile Tab -->
					<div class="mb-4 mt-2">
						<h1 class="text-3xl font-bold mb-2">Child Profile</h1>
						<p class="text-gray-600 dark:text-gray-400">
							{#if profileSubmitted && !isEditingProfile}
								View and manage your child's profile information.
							{:else}
								Collect and manage your child's information to personalize their AI learning experience.
							{/if}
						</p>
					</div>
					
					{#if profileSubmitted && !isEditingProfile}
						<!-- Profile Display View -->
						<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
							<!-- Header with Edit Button -->
							<div class="flex justify-between items-center mb-6">
								<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Child Profile Information</h2>
								<button
									on:click={startEditingProfile}
									class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
								>
									Change Profile
								</button>
							</div>
							
							<!-- Profile Display -->
							<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
								<!-- Child Information -->
								<div class="space-y-6">
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
										Child Information
									</h3>
									
									<div class="space-y-4">
										<div>
											<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Age:</span>
											<p class="text-gray-900 dark:text-white">{formatDisplayValue(childAge, 'age')}</p>
										</div>
										
										<div>
											<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Gender:</span>
											<p class="text-gray-900 dark:text-white">{formatDisplayValue(childGender, 'gender')}</p>
										</div>
										
										<div>
											<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Characteristics:</span>
											<p class="text-gray-900 dark:text-white whitespace-pre-wrap">{childCharacteristics || 'Not specified'}</p>
										</div>
									</div>
								</div>
								
								<!-- Parent Information -->
								<div class="space-y-6">
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
										Parent Information
									</h3>
									
									<div class="space-y-4">
										<div>
											<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Parent Gender:</span>
											<p class="text-gray-900 dark:text-white">{formatDisplayValue(parentGender, 'gender')}</p>
										</div>
										
										<div>
											<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Parent Age Range:</span>
											<p class="text-gray-900 dark:text-white">{formatDisplayValue(parentAge, 'ageRange')}</p>
										</div>
										
										<div>
											<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Parent Preferences:</span>
											<p class="text-gray-900 dark:text-white whitespace-pre-wrap">{parentPreference || 'Not specified'}</p>
										</div>
									</div>
								</div>
							</div>
							
							<!-- Parenting Style -->
							<div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
								<div>
									<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Parenting Style:</span>
									<p class="text-gray-900 dark:text-white whitespace-pre-wrap mt-2">{parentingStyle || 'Not specified'}</p>
								</div>
							</div>
						</div>
					{:else}
						<!-- Profile Form View -->
						<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
							<form on:submit|preventDefault={saveChildProfile} class="space-y-6">
							<!-- Child Information Section -->
							<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
								<!-- Left Column: Child Data -->
								<div class="space-y-4">
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Child Information</h3>
									
									<!-- Age -->
									<div>
										<label for="child-age" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											A. Age
										</label>
										<select
											id="child-age"
											bind:value={childAge}
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="">Select age</option>
											<option value="3">3 years old</option>
											<option value="4">4 years old</option>
											<option value="5">5 years old</option>
											<option value="6">6 years old</option>
											<option value="7">7 years old</option>
											<option value="8">8 years old</option>
											<option value="9">9 years old</option>
											<option value="10">10 years old</option>
											<option value="11">11 years old</option>
											<option value="12">12 years old</option>
											<option value="13">13 years old</option>
											<option value="14">14 years old</option>
											<option value="15">15 years old</option>
											<option value="16">16 years old</option>
											<option value="17">17 years old</option>
										</select>
									</div>
									
									<!-- Gender -->
									<div>
										<label for="child-gender" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											B. Gender
										</label>
										<select
											id="child-gender"
											bind:value={childGender}
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="">Select gender</option>
											<option value="male">Male</option>
											<option value="female">Female</option>
											<option value="non-binary">Non-binary</option>
											<option value="prefer-not-to-say">Prefer not to say</option>
										</select>
									</div>
									
									<!-- Characteristics -->
									<div>
										<label for="child-characteristics" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											C. Characteristics
										</label>
										<textarea
											id="child-characteristics"
											bind:value={childCharacteristics}
											placeholder="Describe your child's personality, interests, learning style, strengths, challenges, etc."
											rows="4"
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
										></textarea>
									</div>
								</div>
								
								<!-- Right Column: Parent Data -->
								<div class="space-y-4">
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Parent Information</h3>
									
									<!-- Parent Gender -->
									<div>
										<label for="parent-gender" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											Parent Gender
										</label>
										<select
											id="parent-gender"
											bind:value={parentGender}
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="">Select gender</option>
											<option value="male">Male</option>
											<option value="female">Female</option>
											<option value="non-binary">Non-binary</option>
											<option value="prefer-not-to-say">Prefer not to say</option>
										</select>
									</div>
									
									<!-- Parent Age -->
									<div>
										<label for="parent-age" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											Parent Age
										</label>
										<select
											id="parent-age"
											bind:value={parentAge}
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="">Select age range</option>
											<option value="20-25">20-25</option>
											<option value="26-30">26-30</option>
											<option value="31-35">31-35</option>
											<option value="36-40">36-40</option>
											<option value="41-45">41-45</option>
											<option value="46-50">46-50</option>
											<option value="51-55">51-55</option>
											<option value="56-60">56-60</option>
											<option value="60+">60+</option>
										</select>
									</div>
									
									<!-- Parent Preference -->
									<div>
										<label for="parent-preference" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											Parent Preference?
										</label>
										<textarea
											id="parent-preference"
											bind:value={parentPreference}
											placeholder="Any specific preferences for your child's AI interactions, content filtering, educational focus, etc."
											rows="3"
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
										></textarea>
									</div>
								</div>
							</div>
							
							<!-- Parenting Style Section -->
							<div class="mt-6">
								<label for="parenting-style" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									D. Describe your parenting style
								</label>
								<textarea
									id="parenting-style"
									bind:value={parentingStyle}
									placeholder="Describe your approach to parenting, values you want to instill, discipline style, educational philosophy, etc."
									rows="4"
									class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
								></textarea>
							</div>
							
							<!-- Submit Button -->
							<div class="flex justify-end pt-6">
								<button
									type="submit"
									class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-medium transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
								>
									SUBMIT
								</button>
							</div>
							</form>
						</div>
						
						<!-- Contextual Factors Note -->
						<div class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
							<p class="text-sm text-blue-800 dark:text-blue-200">
								<strong>Note:</strong> This information will be used to collect possible contextual factors that help personalize your child's AI learning experience. The data is stored locally and can be updated at any time.
							</p>
						</div>
					{/if}
				{:else if activeTab === 'policy'}
					<!-- Policy Making Tab -->
					<div class="mb-4 mt-4 px-4 md:px-8">
						<div class="pl-9">
							<h1 class="text-3xl font-bold mb-2">Content Policy Configuration</h1>
							<p class="text-gray-600 dark:text-gray-400">
								Configure how the AI should respond to your child's interactions.
							</p>
						</div>
					</div>
					
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 md:p-8 mx-auto w-full max-w-6xl shadow-lg">
						<div class="w-full mx-auto">
							<!-- Question Progress Indicator -->
							<div class="mb-6 flex items-center">
								<div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
									<div 
										class="h-full bg-blue-500 rounded-full transition-all duration-300"
										style="width: {((currentPolicyQuestion + 1) / totalPolicyQuestions) * 100}%"
									></div>
								</div>
								<span class="ml-4 text-sm font-medium text-gray-600 dark:text-gray-300">
									{currentPolicyQuestion + 1}/{totalPolicyQuestions}
								</span>
							</div>
							
							<!-- Politics Question -->
							{#if currentPolicyQuestion === 0}
								<div class="mb-8">
									<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
										If your child asks about politics, how do you want us to respond?
									</h3>
									
									<!-- Two-column layout -->
									<div class="flex flex-col lg:flex-row gap-6">
										<!-- Left column: Options -->
										<div class="lg:w-2/5 space-y-3">
											<!-- Option 1: Objectively -->
											<div 
												role="button"
												tabindex="0"
												class="p-4 rounded-lg border {selectedPoliticsResponse === 'objectively'
													? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
													: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'} transition-colors cursor-pointer"
												on:click={() => togglePoliticsResponse('objectively')}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														togglePoliticsResponse('objectively');
													}
												}}
												on:mouseenter={() => (hoveredPoliticsOption = 'objectively')}
												on:mouseleave={() => (hoveredPoliticsOption = selectedPoliticsResponse)}
											>
												<label class="flex items-start space-x-3 cursor-pointer">
													<input 
														type="radio" 
														name="politicsResponse" 
														value="objectively" 
														checked={selectedPoliticsResponse === 'objectively'}
														class="mt-1 accent-blue-500" 
													/>
													<div>
														<span class="font-medium text-gray-900 dark:text-white">Objectively</span>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
															Provide factual information about political figures and topics while acknowledging different viewpoints exist.
														</p>
													</div>
												</label>
											</div>
											
											<!-- Option 2: No Specific Mentions -->
											<div 
												role="button"
												tabindex="0"
												class="p-4 rounded-lg border {selectedPoliticsResponse === 'noSpecific'
													? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
													: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'} transition-colors cursor-pointer"
												on:click={() => togglePoliticsResponse('noSpecific')}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														togglePoliticsResponse('noSpecific');
													}
												}}
												on:mouseenter={() => (hoveredPoliticsOption = 'noSpecific')}
												on:mouseleave={() => (hoveredPoliticsOption = selectedPoliticsResponse)}
											>
												<label class="flex items-start space-x-3 cursor-pointer">
													<input 
														type="radio" 
														name="politicsResponse" 
														value="noSpecific" 
														checked={selectedPoliticsResponse === 'noSpecific'}
														class="mt-1 accent-blue-500" 
													/>
													<div>
														<span class="font-medium text-gray-900 dark:text-white">No Mentions of Specific Political Figures/Viewpoints</span>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
															Avoid discussing specific political figures or viewpoints while still acknowledging the question.
														</p>
													</div>
												</label>
											</div>
											
											<!-- Option 3: No Politics -->
											<div 
												role="button"
												tabindex="0"
												class="p-4 rounded-lg border {selectedPoliticsResponse === 'noPolitics'
													? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
													: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'} transition-colors cursor-pointer"
												on:click={() => togglePoliticsResponse('noPolitics')}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														togglePoliticsResponse('noPolitics');
													}
												}}
												on:mouseenter={() => (hoveredPoliticsOption = 'noPolitics')}
												on:mouseleave={() => (hoveredPoliticsOption = selectedPoliticsResponse)}
											>
												<label class="flex items-start space-x-3 cursor-pointer">
													<input 
														type="radio" 
														name="politicsResponse" 
														value="noPolitics" 
														checked={selectedPoliticsResponse === 'noPolitics'}
														class="mt-1 accent-blue-500" 
													/>
													<div>
														<span class="font-medium text-gray-900 dark:text-white">No Mentions of Politics in General</span>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
															Redirect the conversation away from political topics entirely to other engaging subjects.
														</p>
													</div>
												</label>
											</div>
										</div>
										
										<!-- Right column: Chat Preview -->
										<div class="lg:w-3/5 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
											<!-- Chat header -->
											<div class="bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 py-2 px-4">
												<div class="text-sm font-medium text-black dark:text-black">Example Interaction</div>
											</div>
											
											<!-- Chat messages -->
											<div class="p-4 space-y-4 bg-white dark:bg-gray-800 min-h-[300px]">
												<!-- Child message -->
												<div class="flex justify-end">
													<div class="bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-[80%] shadow-sm">
														<p class="text-sm">Who is Trump? Is he a good guy?</p>
													</div>
												</div>
												
												<!-- AI response based on selected/hovered option -->
												<div class="flex">
													<div class="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-gray-800 dark:text-gray-200 shadow-sm max-w-[80%]">
														{#if hoveredPoliticsOption === 'objectively' || (hoveredPoliticsOption === null && selectedPoliticsResponse === 'objectively')}
															<p class="text-sm">Hi there! Donald Trump is a well-known businessman and was the 45th President of the United States. People have different opinions about him, just like with many leaders. Some people think he did a good job, while others have different thoughts. It's important to learn about different leaders and make up your own mind about what you think. If you want to learn more about him, you can ask your family or look for information from different places.</p>
														{:else if hoveredPoliticsOption === 'noSpecific' || (hoveredPoliticsOption === null && selectedPoliticsResponse === 'noSpecific')}
															<p class="text-sm">It's great that you're curious and asking questions! Donald Trump is a person who was a leader in the United States. People have different opinions about him, just like how people might feel differently about characters in stories or movies. If you want to know more about what he did, it might be helpful to talk to your parents or another trusted adult who can give you a little more information that's right for you. If you have any other questions, feel free to ask!</p>
														{:else if hoveredPoliticsOption === 'noPolitics' || (hoveredPoliticsOption === null && selectedPoliticsResponse === 'noPolitics')}
															<p class="text-sm">Hello! Let's find something really amazing to talk about. How about I tell you about some cool animals or fun science facts instead? Just let me know what you're curious about or if there's something else you'd like to learn!</p>
														{:else}
															<p class="text-sm">(Please select a response option to see an example.)</p>
														{/if}
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							{:else if currentPolicyQuestion === 1}
								<!-- Second Policy Question (placeholder) -->
								<div class="mb-8">
									<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
										[Second Policy Question Title]
									</h3>
									
									<!-- Two-column layout -->
									<div class="flex flex-col lg:flex-row gap-6">
										<!-- Left column: Options -->
										<div class="lg:w-2/5 space-y-3">
											<!-- Option 1 -->
											<div 
												role="button"
												tabindex="0"
												class="p-4 rounded-lg border {selectedSecondQuestion === 'option1'
													? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
													: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'} transition-colors cursor-pointer"
												on:click={() => toggleSecondQuestion('option1')}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														toggleSecondQuestion('option1');
													}
												}}
												on:mouseenter={() => (hoveredSecondOption = 'option1')}
												on:mouseleave={() => (hoveredSecondOption = selectedSecondQuestion)}
											>
												<label class="flex items-start space-x-3 cursor-pointer">
													<input 
														type="radio" 
														name="secondQuestion" 
														value="option1" 
														checked={selectedSecondQuestion === 'option1'}
														class="mt-1 accent-blue-500" 
													/>
													<div>
														<span class="font-medium text-gray-900 dark:text-white">{secondQuestionChoices.option1.title}</span>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
															{secondQuestionChoices.option1.description}
														</p>
													</div>
												</label>
											</div>
											
											<!-- Option 2 -->
											<div 
												role="button"
												tabindex="0"
												class="p-4 rounded-lg border {selectedSecondQuestion === 'option2'
													? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
													: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'} transition-colors cursor-pointer"
												on:click={() => toggleSecondQuestion('option2')}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														toggleSecondQuestion('option2');
													}
												}}
												on:mouseenter={() => (hoveredSecondOption = 'option2')}
												on:mouseleave={() => (hoveredSecondOption = selectedSecondQuestion)}
											>
												<label class="flex items-start space-x-3 cursor-pointer">
													<input 
														type="radio" 
														name="secondQuestion" 
														value="option2" 
														checked={selectedSecondQuestion === 'option2'}
														class="mt-1 accent-blue-500" 
													/>
													<div>
														<span class="font-medium text-gray-900 dark:text-white">{secondQuestionChoices.option2.title}</span>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
															{secondQuestionChoices.option2.description}
														</p>
													</div>
												</label>
											</div>
											
											<!-- Option 3 -->
											<div 
												role="button"
												tabindex="0"
												class="p-4 rounded-lg border {selectedSecondQuestion === 'option3'
													? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
													: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'} transition-colors cursor-pointer"
												on:click={() => toggleSecondQuestion('option3')}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														toggleSecondQuestion('option3');
													}
												}}
												on:mouseenter={() => (hoveredSecondOption = 'option3')}
												on:mouseleave={() => (hoveredSecondOption = selectedSecondQuestion)}
											>
												<label class="flex items-start space-x-3 cursor-pointer">
													<input 
														type="radio" 
														name="secondQuestion" 
														value="option3" 
														checked={selectedSecondQuestion === 'option3'}
														class="mt-1 accent-blue-500" 
													/>
													<div>
														<span class="font-medium text-gray-900 dark:text-white">{secondQuestionChoices.option3.title}</span>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
															{secondQuestionChoices.option3.description}
														</p>
													</div>
												</label>
											</div>
										</div>
										
										<!-- Right column: Chat Preview -->
										<div class="lg:w-3/5 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
											<!-- Chat header -->
											<div class="bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 py-2 px-4">
												<div class="text-sm font-medium text-black dark:text-black">Example Interaction</div>
											</div>
											
											<!-- Chat messages -->
											<div class="p-4 space-y-4 bg-white dark:bg-gray-800 min-h-[300px]">
												<!-- Child message -->
												<div class="flex justify-end">
													<div class="bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-[80%] shadow-sm">
														<p class="text-sm">[Example question for second policy]</p>
													</div>
												</div>
												
												<!-- AI response based on selected/hovered option -->
												<div class="flex">
													<div class="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-gray-800 dark:text-gray-200 shadow-sm max-w-[80%]">
														{#if hoveredSecondOption === 'option1' || (hoveredSecondOption === null && selectedSecondQuestion === 'option1')}
															<p class="text-sm">{secondQuestionChoices.option1.example}</p>
														{:else if hoveredSecondOption === 'option2' || (hoveredSecondOption === null && selectedSecondQuestion === 'option2')}
															<p class="text-sm">{secondQuestionChoices.option2.example}</p>
														{:else if hoveredSecondOption === 'option3' || (hoveredSecondOption === null && selectedSecondQuestion === 'option3')}
															<p class="text-sm">{secondQuestionChoices.option3.example}</p>
														{:else}
															<p class="text-sm">Please select a response option to see an example.</p>
														{/if}
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							{/if}
							
							<!-- Navigation Buttons -->
							<div class="flex justify-between pt-6">
								{#if currentPolicyQuestion > 0}
									<button
										on:click={prevPolicyQuestion}
										class="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white px-6 py-2 rounded-lg font-medium transition-colors"
									>
										Previous Question
									</button>
								{:else}
									<div></div> <!-- Empty div to maintain flex layout -->
								{/if}
								
								{#if currentPolicyQuestion < totalPolicyQuestions - 1}
									<button
										on:click={nextPolicyQuestion}
										class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
									>
										Next Question
									</button>
								{:else}
									<button
										on:click={openPolicyPreview}
										class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
									>
										Save Policy Settings
									</button>
								{/if}
							</div>
						</div>
					</div>
				{:else if activeTab === 'childgpt'}
					<!-- My Child's GPT Tab -->
					<div class="mb-4 mt-4 px-4 md:px-8">
						<h1 class="text-3xl font-bold mb-2">My Child's GPT</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Select and save a model that will be used as your child's primary AI assistant.
						</p>
					</div>
					
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 md:p-8 mx-auto w-full max-w-6xl shadow-lg">
						<div class="w-full mx-auto">
							<!-- Model Selection -->
							<div class="mb-8">
								<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
									Select Your Child's AI Model
								</h3>
								<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
									Choose the AI model that will be used as your child's primary assistant. This model will be automatically selected when your child starts a new conversation.
								</p>
								
								<div class="space-y-4">
									<!-- Model Dropdown -->
									<div>
										<label
											for="child-gpt-model-select"
											class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
										>
											Available Models
										</label>
										<select
											id="child-gpt-model-select"
											bind:value={selectedChildGPTModel}
											class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="">Select a model...</option>
											{#each $models as model}
												<option value={model.id} class="bg-white dark:bg-gray-700">
													{model.name}
												</option>
											{/each}
										</select>
									</div>
									
									<!-- Current Selection Display -->
									{#if childGPTModelId}
										<div class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
											<div class="flex items-center space-x-2">
												<div class="w-2 h-2 bg-green-500 rounded-full"></div>
												<div>
													<p class="text-sm font-medium text-green-800 dark:text-green-200">
														Current Child's GPT Model
													</p>
													<p class="text-sm text-green-600 dark:text-green-400">
														{$models.find(m => m.id === childGPTModelId)?.name || childGPTModelId}
													</p>
												</div>
											</div>
										</div>
									{/if}
									
									<!-- Save Button -->
									<div class="flex justify-end pt-6">
										<button
											on:click={saveChildGPTModel}
											disabled={loadingChildGPT || !selectedChildGPTModel}
											class="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2"
										>
											{#if loadingChildGPT}
												<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
												<span>Saving...</span>
											{:else}
												<span>Save as My Child's GPT</span>
											{/if}
										</button>
									</div>
								</div>
							</div>
						</div>
					</div>
				{:else if activeTab === 'graph'}
					<!-- Graphs Section -->
					<div class="mb-4 mt-4 px-4 md:px-8">
						<h1 class="text-3xl font-bold mb-2">Interactive Graph</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Click anywhere on the graph to place plot points. The graph spans from 0 to 10 on both X and Y axes.
						</p>
					</div>
					
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 md:p-8 mx-auto max-w-4xl shadow-lg">
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
								role="application"
								tabindex="-1"
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
												role="button"
												tabindex="0"
												class="absolute w-2 h-2 rounded-full cursor-pointer bg-blue-400 bg-opacity-30 hover:bg-blue-500 hover:bg-opacity-60 border-2 border-blue-300 transition-colors duration-150"
												style="left: {(coordX * 100) / 5}%; top: {100 - (coordY * 100) / 10}%; transform: translate(-4px, -4px);"
												on:mouseenter={() => handleCoordinateHover(coordX, coordY)}
												on:mouseleave={handleCoordinateLeave}
												on:click={(e) => {
													e.stopPropagation();
													handleGraphClick(e);
												}}
												on:keydown={(e) => {
													if (e.key === ' ' || e.key === 'Enter') {
														e.preventDefault();
														e.stopPropagation();
														const idx = plotPoints.findIndex((p) => p.x === coordX && p.y === coordY);
														if (idx !== -1) {
															plotPoints = [
																...plotPoints.slice(0, idx),
																...plotPoints.slice(idx + 1)
															];
														} else {
															plotPoints = [...plotPoints, { x: coordX, y: coordY }];
														}
													}
												}}
											></div>
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
				{:else if activeTab === 'playground'}
					<!-- Playground Tab -->
					<div class="mb-4 mt-4 px-4 md:px-8">
						<h1 class="text-3xl font-bold mb-2">Chat with your child's GPT!</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Test how your child's AI assistant responds with your current policy settings.
						</p>
					</div>
					
					<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 md:p-8 mx-auto max-w-3xl shadow-lg">
						<div class="max-w-2xl mx-auto">
							{#if !childGPTModelId}
								<!-- No Child GPT model selected -->
								<div class="flex flex-col items-center justify-center py-12 text-center">
									<div class="text-gray-400 dark:text-gray-500 mb-4">
										<Sparkles className="size-12" />
									</div>
									<h3 class="text-lg font-semibold mb-2 text-gray-900 dark:text-white">
										No Child's GPT Model Selected
									</h3>
									<p class="text-sm text-gray-600 dark:text-gray-400 mb-6 max-w-md">
										Please go to the "My Child's GPT" tab first and select a model to use for your child's AI assistant.
									</p>
									<button
										on:click={() => handleTabClick('childgpt')}
										class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
									>
										Go to My Child's GPT
									</button>
								</div>
							{:else}
								<!-- Chat Interface -->
								<div class="flex flex-col h-[60vh] md:h-[70vh]">
									<!-- Chat Header -->
									<div class="border-b border-gray-200 dark:border-gray-700 pb-4 mb-4">
										<div class="flex items-center justify-between">
											<div class="flex items-center">
												<div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center mr-3">
													<Sparkles className="size-5 text-blue-500 dark:text-blue-300" />
												</div>
												<div>
													<h3 class="font-medium text-gray-900 dark:text-white">
														{childGPTName || "My Child's GPT"}
													</h3>
													<p class="text-xs text-gray-500 dark:text-gray-400">
														Model ID: {childGPTModelId}
													</p>
												</div>
											</div>
											<button
												on:click={() => handleTabClick('policy')}
												class="px-4 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors flex items-center space-x-1.5"
											>
												<Settings className="size-3.5" />
												<span>Adjust Policies</span>
											</button>
										</div>
									</div>
									
									<!-- Chat Messages -->
									<div class="flex-1 overflow-y-auto mb-4 space-y-4 pr-2" style="scrollbar-width: thin;">
										{#if chatMessages.length === 0}
											<div class="flex items-center justify-center h-full">
												<p class="text-gray-500 dark:text-gray-400 text-center">
													Send a message to start chatting with {childGPTName || "My Child's GPT"}
												</p>
											</div>
										{:else}
											{#each chatMessages as message}
												<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
													<div class="{message.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'} rounded-lg px-4 py-3 max-w-[80%]">
														{#if message.loading}
															<div class="flex items-center space-x-1">
																<div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 0ms;"></div>
																<div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 150ms;"></div>
																<div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 300ms;"></div>
															</div>
														{:else}
															<p class="whitespace-pre-wrap break-words">{message.content}</p>
															<div class="text-xs opacity-70 mt-1 text-right">
																{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
															</div>
														{/if}
													</div>
												</div>
											{/each}
										{/if}
									</div>
									
									<!-- Message Input -->
									<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
										<form 
											class="flex items-end gap-2"
											on:submit|preventDefault={sendMessage}
										>
											<div class="flex-1">
												<textarea
													bind:value={currentMessage}
													placeholder="Type a message..."
													class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
													rows="3"
												></textarea>
											</div>
											<button
												type="submit"
												disabled={sendingMessage || !currentMessage.trim()}
												class="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed text-white p-3 rounded-lg transition-colors"
											>
												{#if sendingMessage}
													<div class="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
												{:else}
													<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
														<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
													</svg>
												{/if}
											</button>
										</form>
										<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
											This chat simulates how your child would interact with the AI based on your policy settings.
										</p>
									</div>
								</div>
							{/if}
						</div>
					</div>
				{:else if activeTab === 'parent_quiz_ii'}
					<!-- Parent Quiz II Tab -->
					<div class="mb-4 mt-4 px-4 md:px-8">
						<h1 class="text-3xl font-bold mb-2">Parent Moderation Quiz</h1>
						<p class="text-gray-600 dark:text-gray-400">
							Review the interaction below. If you see something you'd like to change, select a moderation strategy.
						</p>
					</div>

					<div
						class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 md:p-8 mx-auto w-full max-w-6xl shadow-lg"
					>
						<!-- Chat Preview -->
						<div class="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden mb-8">
							<!-- Chat header -->
							<div class="bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 py-2 px-4">
								<div class="text-sm font-medium text-black dark:text-black">Example Interaction</div>
							</div>

							<!-- Chat messages -->
							<div class="p-4 space-y-4 bg-white dark:bg-gray-800 min-h-[200px]">
								<!-- Child message -->
								<div class="flex justify-end">
									<div class="bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-[80%] shadow-sm">
										<p class="text-sm">Who is Trump? Is he a good guy?</p>
									</div>
								</div>

								<!-- AI response -->
								<div class="flex">
									<div
										class="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-gray-800 dark:text-gray-200 shadow-sm max-w-[80%]"
									>
										<p class="text-sm">
											Hi there! Donald Trump is a well-known businessman and was the 45th President of the United
											States. People have different opinions about him, just like with many leaders. Some people
											think he did a good job, while others have different thoughts. It's important to learn about
											different leaders and make up your own mind about what you think. If you want to learn more
											about him, you can ask your family or look for information from different places.
										</p>
									</div>
								</div>
							</div>
						</div>

					<!-- Moderation Buttons -->
					<div>
						<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
							How would you like to update the interaction?
						</h3>
						<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
							{#each moderationOptions as option}
								<button
									on:click={() => handleModerationClick(option)}
									disabled={moderationLoading}
									class="p-3 text-sm font-medium text-center bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:bg-gray-300 disabled:dark:bg-gray-800 disabled:cursor-not-allowed rounded-lg transition-colors"
								>
									{option}
								</button>
							{/each}
						</div>

						<!-- Loading State -->
						{#if moderationLoading}
							<div class="flex items-center justify-center p-8">
								<div class="flex items-center space-x-3">
									<div
										class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"
									></div>
									<span class="text-gray-600 dark:text-gray-400">Applying moderation...</span>
								</div>
							</div>
						{/if}

						<!-- Moderation Result -->
						{#if moderationResult && !moderationLoading}
							<div class="mt-6">
								<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
									Backend Response (Raw JSON)
								</h3>
								<div
									class="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4 overflow-auto max-h-96"
								>
									<pre
										class="text-xs text-gray-800 dark:text-gray-200 font-mono whitespace-pre-wrap">{JSON.stringify(
											moderationResult,
											null,
											2
										)}</pre>
								</div>

								<!-- Clear Button -->
								<div class="mt-4 flex justify-end">
									<button
										on:click={() => (moderationResult = null)}
										class="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors"
									>
										Clear Result
									</button>
								</div>
							</div>
						{/if}
					</div>
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

<!-- Policy Preview Modal -->
{#if showPolicyPreview}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
			<div class="p-6">
				<div class="flex justify-between items-center mb-4">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
						Preview Policy Settings
					</h2>
					<button
						on:click={() => showPolicyPreview = false}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
				
				<div class="mb-6">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-3">
						System Prompt Preview
					</h3>
					<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
						<pre class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono">{policySystemPrompt || 'No policy instructions selected'}</pre>
					</div>
				</div>
				
				<div class="mb-6">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-3">
					Target Model
					</h3>
					<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-700">
						<p class="text-sm text-blue-800 dark:text-blue-200">
							<strong>My Child's GPT:</strong> {childGPTModelId || 'No model selected'}
						</p>
					</div>
				</div>
				
				<div class="flex justify-end space-x-3">
					<button
						on:click={() => showPolicyPreview = false}
						class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
					>
						Cancel
					</button>
					<button
						on:click={async () => {
							await confirmPolicies();
							if (!savingPolicies) {
								showPolicyPreview = false;
								handleTabClick('playground');
							}
						}}
						disabled={savingPolicies}
						class="px-6 py-2 bg-green-500 hover:bg-green-600 disabled:bg-green-300 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
					>
						{#if savingPolicies}
							<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<span>Applying...</span>
						{:else}
							<span>Confirm & Test Policies</span>
						{/if}
					</button>
					<button
						on:click={confirmPolicies}
						disabled={savingPolicies}
						class="px-6 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
					>
						{#if savingPolicies}
							<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<span>Applying...</span>
						{:else}
							<span>Confirm Policies</span>
						{/if}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if} 