<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import { showFacilitiesOverlay, showControls, models, chatId, chats, currentChatPage } from '$lib/stores';
	import { slide } from 'svelte/transition';
	import { generateFacilitiesResponse, getFacilitiesSections } from '$lib/apis/facilities';
	import { updateChatById, getChatList } from '$lib/apis/chats';
	import { toast } from 'svelte-sonner';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let submitPrompt: Function | null = null;
	export let modelId: string = '';
	export let history: any = null;
	export let addMessages: Function | null = null;
	export let initChatHandler: Function | null = null; 
	export let webSearchEnabled: boolean = false;
	
	// Local storage key - unique per chat
	$: STORAGE_KEY = `facilities-overlay-form-${$chatId || 'new'}`;
	
	// Get the current web search state from the chat interface
	$: currentWebSearchEnabled = webSearchEnabled;

	let selectedSponsor = '';
	let formData: Record<string, string> = {
		projectTitle: '',
		researchSpaceFacilities: '',
		coreInstrumentation: '',
		computingDataResources: '',
		internalFacilitiesNYU: '',
		externalFacilitiesOther: '',
		specialInfrastructure: '',
		equipment: ''
	};

	let generating = false;
	let dynamicSections: string[] = [];

	const nsfSections = [
		{ id: 'projectTitle', label: '1. Project Title', required: true },
		{ id: 'researchSpaceFacilities', label: '2. Research Space and Facilities', required: true },
		{ id: 'coreInstrumentation', label: '3. Core Instrumentation', required: true },
		{ id: 'computingDataResources', label: '4. Computing and Data Resources', required: true },
		{ id: 'internalFacilitiesNYU', label: '5a. Internal Facilities (NYU)', required: true },
		{ id: 'externalFacilitiesOther', label: '5b. External Facilities (Other Institutions)', required: true },
		{ id: 'specialInfrastructure', label: '6. Special Infrastructure', required: true }
	];

	const nihSections = [
		...nsfSections,
		{ id: 'equipment', label: '7. Equipment', required: true }
	];

	// Create dynamic sections based on backend response
	$: currentSections = dynamicSections.length > 0 ? 
		dynamicSections.map((sectionLabel, index) => {
			const sectionId = getSectionIdFromLabel(sectionLabel);
			console.log(`Mapping section ${index}: "${sectionLabel}" to ID "${sectionId}"`);
			return { id: sectionId, label: sectionLabel, required: true };
		}) : 
		(selectedSponsor === 'NSF' ? nsfSections : nihSections);
	
	// Helper function to map backend section labels to form field IDs
	function getSectionIdFromLabel(label: string): string {
		const mapping: Record<string, string> = {
			'1. Project Title': 'projectTitle',
			'2. Research Space and Facilities': 'researchSpaceFacilities',
			'3. Core Instrumentation': 'coreInstrumentation',
			'4. Computing and Data Resources': 'computingDataResources',
			'5a. Internal Facilities (NYU)': 'internalFacilitiesNYU',
			'5b. External Facilities (Other Institutions)': 'externalFacilitiesOther',
			'6. Special Infrastructure': 'specialInfrastructure',
			'7. Equipment': 'equipment'
		};
		return mapping[label] || label.toLowerCase().replace(/[^a-zA-Z0-9]/g, '');
	}
	
	// Save form data to localStorage whenever it changes
	// Only save if we have a valid chatId (not for new chats)
	$: if ($chatId && (selectedSponsor || Object.values(formData).some(v => v.trim() !== ''))) {
		saveToLocalStorage();
	}

	function saveToLocalStorage() {
		// Only save if we have a valid chatId
		if (!$chatId) {
			console.log('Skipping save - no chatId yet (new chat)');
			return;
		}
		
		try {
			const dataToSave = {
				selectedSponsor,
				formData,
				dynamicSections,
				chatId: $chatId,
				timestamp: Date.now()
			};
			localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave));
			console.log(`Saved form data to localStorage for chat: ${$chatId}`);
		} catch (error) {
			console.error('Error saving to localStorage:', error);
		}
	}

	function loadFromLocalStorage() {
		// Only load if we have a valid chatId
		if (!$chatId) {
			console.log('Skipping load - no chatId yet (new chat)');
			return;
		}
		
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			if (saved) {
				const parsed = JSON.parse(saved);
				
				// Only load if it matches current chat (safety check)
				if (parsed.chatId === $chatId) {
					selectedSponsor = parsed.selectedSponsor || '';
					formData = parsed.formData || formData;
					dynamicSections = parsed.dynamicSections || [];
					
					console.log(`Loaded form data from localStorage for chat: ${$chatId}`, {
						sponsor: selectedSponsor,
						hasData: Object.values(formData).some(v => v.trim() !== ''),
						sectionsCount: dynamicSections.length,
						savedAt: new Date(parsed.timestamp).toLocaleString()
					});
				}
			}
		} catch (error) {
			console.error('Error loading from localStorage:', error);
		}
	}

	function clearLocalStorage() {
		// Only clear if we have a valid chatId
		if (!$chatId) {
			return;
		}
		
		try {
			localStorage.removeItem(STORAGE_KEY);
			console.log(`Cleared form data from localStorage for chat: ${$chatId}`);
		} catch (error) {
			console.error('Error clearing localStorage:', error);
		}
	}

	// Load saved data when component mounts or chat changes
	onMount(() => {
		loadFromLocalStorage();
	});
	
	// Reload form data when chat ID changes
	$: if ($chatId) {
		loadFromLocalStorage();
	}

	// DIRECT CHAT HISTORY MANIPULATION - BYPASS submitPrompt entirely
	async function addFacilitiesResponseToChat(content: string, sources: any[], error: string | null = null) {
		console.log('addFacilitiesResponseToChat called with:', {
			contentLength: content.length,
			sourcesCount: sources.length,
			history: !!history,
			addMessages: !!addMessages,
			historyCurrentId: history?.currentId
		});

		if (!history || !addMessages || !initChatHandler) {
			console.error('History or addMessages not available:', {
				history: !!history,
				addMessages: !!addMessages,
				initChatHandler: !!initChatHandler
			});
			return;
		}

		// Create user message from form data
		const userMessageContent = `Facilities Request for ${selectedSponsor}:\n\n` + 
			Object.entries(formData)
				.filter(([key, value]) => value.trim() !== '')
				.map(([key, value]) => {
					const section = currentSections.find(s => s.id === key);
					return `${section?.label || key}: ${value}`;
				})
				.join('\n\n');

		// Create user message
		const userMessage = {
			id: crypto.randomUUID(),
			parentId: history.currentId || null,
			childrenIds: [],
			role: 'user',
			content: userMessageContent,
			timestamp: Math.floor(Date.now() / 1000),
			models: [modelId]
		};

		// Get the actual model object to get the proper name
		const model = $models.find(m => m.id === modelId);
		const modelName = model?.name || modelId;

		// Create facilities response message (matching existing chat system structure)
		const responseMessage = {
			id: crypto.randomUUID(),
			parentId: userMessage.id,
			childrenIds: [],
			role: 'assistant',
			content: content,
			model: modelId,
			modelName: modelName,
			modelIdx: 0,
			userContext: null,
			timestamp: Math.floor(Date.now() / 1000),
			done: true,
			sources: sources,
			error: error ? {
				content: error
			} : null
		};

		// Use the addMessages function properly with error handling
		try {
			// Check if we need to create a new chat first
			let parentId = history.currentId;

			console.log('Chat state check:', {
				chatId: $chatId,
				historyMessagesCount: Object.keys(history.messages).length,
				historyCurrentId: history.currentId
			});

			if (!$chatId || Object.keys(history.messages).length === 0) {
				console.log('No chat exists, creating new chat first');
				const newChatId = await initChatHandler(history);
				console.log('Created new chat with ID:', newChatId);
				parentId = null;
			}

			console.log('Calling addMessages with parentId:', parentId);
			await addMessages({
				modelId: modelId,
				parentId: userMessage.parentId,
				messages: [
					{
						role: 'user',
						content: userMessageContent,
						models: [modelId]
					},
					{
						role: 'assistant',
						content: content,
						model: modelId,
						modelName: modelName,
						modelIdx: 0,
						userContext: null,
						done: true,
						sources: sources,
						error: error ? {
							content: error
						} : null
					}
				]
			});

			// Generate a proper title for the facilities chat
			try {
				const token = localStorage.getItem('token');
				if (token && $chatId) {
					// Create a meaningful title based on the sponsor and project
					const projectTitle = formData.projectTitle || 'Facilities Response';
					const title = `Facilities Response - ${selectedSponsor} - ${projectTitle}`;
					
					// Update the chat title
					await updateChatById(token, $chatId, {
						title: title
					});
					
					// Update the chat list to reflect the new title
					currentChatPage.set(1);
					await chats.set(await getChatList(token, $currentChatPage));
					
					console.log('Updated chat title to:', title);
				}
			} catch (error) {
				console.error('Error updating chat title:', error);
			}
		} catch (error) {
			console.error('Error in addMessages:', error);
			// Fallback: manually add to history if addMessages fails
			const userMsgId = crypto.randomUUID();
			const responseMsgId = crypto.randomUUID();
			
			history.messages[userMsgId] = {
				id: userMsgId,
				parentId: userMessage.parentId,
				childrenIds: [responseMsgId],
				role: 'user',
				content: userMessageContent,
				timestamp: Math.floor(Date.now() / 1000),
				models: [modelId]
			};
			
			history.messages[responseMsgId] = {
				id: responseMsgId,
				parentId: userMsgId,
				childrenIds: [],
				role: 'assistant',
				content: content,
				model: modelId,
				modelName: modelName,
				modelIdx: 0,
				userContext: null,
				timestamp: Math.floor(Date.now() / 1000),
				done: true,
				sources: sources,
				error: error ? {
					content: error
				} : null
			};
			
			history.currentId = responseMsgId;
		}

		console.log('Added facilities response to chat using addMessages:', {
			contentLength: content.length,
			sourcesCount: sources.length,
			historyCurrentId: history.currentId,
			totalMessages: Object.keys(history.messages).length
		});
	}

	async function handleSponsorChange(sponsor: string) {
		selectedSponsor = sponsor;
		// Don't reset form data - keep existing data
		// Just update the equipment field visibility based on sponsor
		
		// Fetch sections from backend
		try {
			const token = localStorage.getItem('token');
			if (token) {
				const response = await getFacilitiesSections(token, sponsor);
				if (response.success) {
					dynamicSections = response.sections;
					console.log(`Loaded ${dynamicSections.length} sections for ${sponsor}:`, dynamicSections);
				} else {
					console.error('Failed to fetch sections:', response);
					// Fallback to hardcoded sections
					dynamicSections = sponsor === 'NSF' ? 
						nsfSections.map(s => s.label) : 
						nihSections.map(s => s.label);
				}
			}
		} catch (error) {
			console.error('Error fetching sections:', error);
			// Fallback to hardcoded sections
			dynamicSections = sponsor === 'NSF' ? 
				nsfSections.map(s => s.label) : 
				nihSections.map(s => s.label);
		}
		
		// Save after sponsor change (only if chatId exists)
		if ($chatId) {
			saveToLocalStorage();
		}
	}

	async function generateSection() {
		if (!selectedSponsor) {
			toast.error('Please select a sponsor (NSF or NIH)');
			return;
		}

		// Check if at least one field is filled
		const hasInput = Object.values(formData).some(value => value.trim() !== '');
		if (!hasInput) {
			toast.error('Please fill in at least one form field');
			return;
		}

		generating = true;

		try {
			// Get token from localStorage
			const token = localStorage.getItem('token');
			if (!token) {
				toast.error('Authentication required');
				return;
			}

			console.log('Calling facilities API with:', {
				sponsor: selectedSponsor,
				form_data: formData,
				model: modelId,
				web_search_enabled: webSearchEnabled
			});
			console.log('Web search enabled value:', webSearchEnabled);

			// Call the facilities API
			const response = await generateFacilitiesResponse(token, {
				sponsor: selectedSponsor,
				form_data: formData,
				model: modelId,  
				web_search_enabled: webSearchEnabled  
			});

			console.log('Facilities API response:', response);

			if (response && response.success) {
				// Use the pre-formatted content from the backend
				const responseMessage = response.content;
				
				// Sources are already formatted by the backend
				const sources = response.sources || [];

				console.log('Adding to chat:', {
					contentLength: responseMessage.length,
					sourcesCount: sources.length,
					contentPreview: responseMessage.substring(0, 100) + '...'
				});

				await addFacilitiesResponseToChat(responseMessage, sources, null);
			} else {
				console.error('Facilities API failed:', response.error);
				// Add error to chat like regular chat does
				await addFacilitiesResponseToChat('', [], response.error || 'Failed to generate facilities response');
				toast.error(response.error || 'Failed to generate facilities response');
			}

		} catch (error: any) {
			console.error('Error generating facilities response:', error);
			console.error('Error details:', {
				message: error?.message,
				detail: error?.detail,
				status: error?.status,
				response: error?.response
			});
			
			// Add error to chat like regular chat does - use the same error handling as regular chat
			const errorMessage = `${error}`;
			await addFacilitiesResponseToChat('', [], errorMessage);
			toast.error(errorMessage);
		} finally {
			generating = false;
		}
	}

	function closeOverlay() {
		// Don't clear localStorage on close - keep the draft
		showFacilitiesOverlay.set(false);
		showControls.set(false);
		dispatch('close');
	}
</script>

<style>
	/* Enhanced scrollbar styles for better visibility */
	.custom-scrollbar {
		scrollbar-width: thin;
		scrollbar-color: #9ca3af #f3f4f6;
	}
	
	.dark .custom-scrollbar {
		scrollbar-color: #6b7280 #374151;
	}

	/* Webkit browsers (Chrome, Safari, Edge) */
	.custom-scrollbar::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	.custom-scrollbar::-webkit-scrollbar-track {
		background: #f3f4f6;
		border-radius: 4px;
	}

	.dark .custom-scrollbar::-webkit-scrollbar-track {
		background: #374151;
	}

	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: #9ca3af;
		border-radius: 4px;
		border: 1px solid #f3f4f6;
	}

	.dark .custom-scrollbar::-webkit-scrollbar-thumb {
		background: #6b7280;
		border-color: #374151;
	}

	.custom-scrollbar::-webkit-scrollbar-thumb:hover {
		background: #6b7280;
	}

	.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
		background: #9ca3af;
	}

	/* Textarea focus styles for better accessibility */
	.textarea-enhanced:focus {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
	}

	/* Animation for expand/collapse */
	.expand-button {
		transition: transform 0.2s ease-in-out;
	}

	.expand-button.expanded {
		transform: rotate(180deg);
	}
</style>

{#if $showFacilitiesOverlay}
	<div class="flex flex-col h-full bg-white dark:bg-gray-850 border border-gray-100 dark:border-gray-850 rounded-xl shadow-lg dark:shadow-lg">
		<!-- Header -->
		<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex-1">
				<h1 class="text-lg font-semibold text-gray-900 dark:text-white">
					{('NYU Research Facilities Draft Generator')}
				</h1>		
			</div>
			
			<button
				class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
				on:click={closeOverlay}
				type="button"
				aria-label="Close research facilities form"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5" aria-hidden="true">
					<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
				</svg>
			</button>
		</div>

		<!-- Main content area - scrollable -->
		<div class="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 space-y-6">
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
					<b>Description</b><br>
					This tool assists in developing the DRAFT section related to  Facilities & Equipment for grant proposals where sponsors are NSF (National Science Foundation) and NIH (National Institute of Health).<br><br>
					Users should complete only those sections that are applicable to their research; any sections left blank will be omitted from the final document. Large Language Model (LLM) will generate responses in a template form.<br><br>
					<b>Disclaimer</b><br>
					The Al-generated text is intended as a DRAFT.<br><br>
					As LLMs are inherently non-deterministic, the output is not guaranteed to be consistent or predictable. As a result, all content must be carefully reviewed, verified, and revised by the researcher to ensure accuracy and compliance with the sponsor's requirements, and adherence to institutional policies. Researchers are solely responsible for the final submitted materials.
				</p>

			<!-- Sponsor Selection -->
			<div>
				<label for="sponsor-select" class="block text-sm font-medium text-gray-900 dark:text-white mb-3">
					{('Sponsor Selection')} <span class="text-red-500" aria-label="required">*</span>
				</label>
				<select
					id="sponsor-select"
					class="w-full rounded-lg py-2.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
					bind:value={selectedSponsor}
					on:change={() => handleSponsorChange(selectedSponsor)}
					aria-label="Select Sponsor"
					aria-describedby="sponsor-help"
					required
				>
					<option value="">{('Choose a sponsor...')}</option>
					<option value="NSF">NSF</option>
					<option value="NIH">NIH</option>
				</select>
			</div>


			<!-- Form Inputs -->
			{#if selectedSponsor && currentSections.length > 0}
				<div>
					<fieldset>
						<legend class="block text-sm font-medium text-gray-900 dark:text-white mb-4">
							{('Section Details')}
						</legend>
						
						<div class="space-y-6">
							{#each currentSections as section, index}
								<div class="relative">
									<label for="section-{index}" class="block text-s font-medium mb-2 text-gray-700 dark:text-gray-300">
										{section.label}
									</label>
									<textarea
										id="section-{index}"
										class="textarea-enhanced textarea-auto-resize w-full rounded-lg py-2.5 px-3 text-sm text-gray-700 bg-gray-50 dark:text-gray-300 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 outline-none focus:border-blue resize-vertical pointer-events-auto custom-scrollbar placeholder-gray-600 dark:placeholder-gray-400"
										rows="4"
										placeholder="Enter details for {section.label}..."
										bind:value={formData[section.id]}
										aria-describedby="section-{index}-help"
									></textarea>
								</div>
							{/each}
						</div>

						<button
							type="button"
							class="w-full mt-6 px-4 py-3 bg-[#57068C] hover:bg-[#8900E1] text-white dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 dark:disabled:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium text-sm transition-colors"
							on:click={generateSection}
							disabled={generating}
							aria-describedby="generate-help"
						>
							{#if generating}
								<svg class="animate-spin h-4 w-4 inline mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
									<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"></circle>
									<path fill="currentColor" class="opacity-75" d="m12 2 A10 10 0 0 1 22 12"></path>
								</svg>
								Generating...
							{:else}
								{('Generate')}
							{/if}
						</button>

					</fieldset>
				</div>
			{/if}
		</div>
	</div>
{/if}