<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { showFacilitiesOverlay, showControls, models } from '$lib/stores';
	import { slide } from 'svelte/transition';
	import { generateFacilitiesResponse, getFacilitiesSections } from '$lib/apis/facilities';
	import { toast } from 'svelte-sonner';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let submitPrompt: Function | null = null;
	export let modelId: string = '';
	export let history: any = null;
	export let addMessages: Function | null = null;
	export let webSearchEnabled: boolean = false;
	
	// Get the current web search state from the chat interface
	$: currentWebSearchEnabled = webSearchEnabled;

	let selectedSponsor = '';
	// Web search is now controlled by the existing web search button, not this form
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
		{ id: 'projectTitle', label: 'Project Title', required: true },
		{ id: 'researchSpaceFacilities', label: 'Research Space and Facilities', required: true },
		{ id: 'coreInstrumentation', label: 'Core Instrumentation', required: true },
		{ id: 'computingDataResources', label: 'Computing and Data Resources', required: true },
		{ id: 'internalFacilitiesNYU', label: 'Internal Facilities (NYU)', required: true },
		{ id: 'externalFacilitiesOther', label: 'External Facilities (Other Institutions)', required: true },
		{ id: 'specialInfrastructure', label: 'Special Infrastructure', required: true }
	];

	const nihSections = [
		...nsfSections,
		{ id: 'equipment', label: 'Equipment', required: true }
	];

	// Create dynamic sections based on backend response
	$: currentSections = dynamicSections.length > 0 ? 
		dynamicSections.map((sectionLabel, index) => {
			// Map backend section labels to form field IDs
			const sectionId = getSectionIdFromLabel(sectionLabel);
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
	
	// Helper function to remove numbers from section labels for placeholders
	function getCleanLabel(label: string): string {
		// Remove patterns like "1. ", "2. ", "5a. ", "5b. ", "6. ", "7. " from the beginning
		return label.replace(/^\d+[a-z]?\.\s*/, '');
	}

	// DIRECT CHAT HISTORY MANIPULATION - BYPASS submitPrompt entirely
	async function addFacilitiesResponseToChat(content: string, sources: any[]) {
		console.log('addFacilitiesResponseToChat called with:', {
			contentLength: content.length,
			sourcesCount: sources.length,
			history: !!history,
			addMessages: !!addMessages,
			historyCurrentId: history?.currentId
		});

		if (!history || !addMessages) {
			console.error('History or addMessages not available:', {
				history: !!history,
				addMessages: !!addMessages
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
			sources: sources
		};

		// Use the addMessages function properly with error handling
		try {
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
						sources: sources
					}
				]
			});
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
				sources: sources
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
		// Reset form data when sponsor changes
		formData = {
			projectTitle: '',
			researchSpaceFacilities: '',
			coreInstrumentation: '',
			computingDataResources: '',
			internalFacilitiesNYU: '',
			externalFacilitiesOther: '',
			specialInfrastructure: '',
			equipment: ''
		};
		
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
				model: modelId,  // Pass the user's selected model
				web_search_enabled: webSearchEnabled  // Pass web search status
			});

			console.log('Facilities API response:', response);

			if (response.success) {
				// Use the pre-formatted content from the backend
				const responseMessage = response.content;
				
				// Sources are already formatted by the backend
				const sources = response.sources || [];

				console.log('Adding to chat:', {
					contentLength: responseMessage.length,
					sourcesCount: sources.length,
					contentPreview: responseMessage.substring(0, 100) + '...'
				});

				// DIRECTLY ADD TO CHAT HISTORY - BYPASS submitPrompt entirely
				await addFacilitiesResponseToChat(responseMessage, sources);

				// Keep the overlay open - user must manually toggle off
				// closeOverlay(); // Removed automatic closing
				
				toast.success(`Generated ${Object.keys(response.sections).length} sections for ${selectedSponsor}.`);
			} else {
				console.error('Facilities API failed:', response.error);
				toast.error(response.error || 'Failed to generate facilities response');
			}

		} catch (error: any) {
			console.error('Error generating facilities response:', error);
			toast.error(error?.message || 'Failed to generate facilities response');
		} finally {
			generating = false;
		}
	}

	function closeOverlay() {
		showFacilitiesOverlay.set(false);
		showControls.set(false);
		dispatch('close');
	}
</script>

{#if $showFacilitiesOverlay}
	<div 
		class="max-w-lg w-full h-full max-h-[100dvh] flex flex-col justify-between p-3 md:p-6 bg-white dark:bg-gray-850 text-gray-700 dark:text-gray-300"
		transition:slide={{ duration: 300 }}
	>
		<!-- Header -->
		<div class="flex justify-between items-center mb-6">
			<h2 class="text-xl font-bold text-gray-900 dark:text-white">Facilities Form</h2>
			<button
				on:click={closeOverlay}
				class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition"
				aria-label="Close"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
					<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
				</svg>
			</button>
		</div>

		<!-- Sponsor Selection -->
		<div class="mb-6">
			<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-white">Select Document Type:</h3>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-4 flex items-center gap-2">
				Choose document type by Sponsor:
				<button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
						<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
					</svg>
				</button>
			</p>
			
			<div class="space-y-3">
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="radio"
						name="sponsor"
						value="NSF"
						bind:group={selectedSponsor}
						on:change={() => handleSponsorChange('NSF')}
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					/>
					<span class="text-sm font-medium">NSF (National Science Foundation)</span>
				</label>
				
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="radio"
						name="sponsor"
						value="NIH"
						bind:group={selectedSponsor}
						on:change={() => handleSponsorChange('NIH')}
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					/>
					<span class="text-sm font-medium">NIH (National Institutes of Health)</span>
				</label>
			</div>
		</div>


		<!-- Form Sections -->
		{#if selectedSponsor}
			<div class="flex-1 overflow-y-auto">
				<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Fill in the details below:</h3>
				
				<div class="space-y-4">
					{#each currentSections as section, index}
						<div class="space-y-2">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								{section.label}
								{#if section.required}
									<span class="text-red-500">*</span>
								{/if}
							</label>
							<textarea
								bind:value={formData[section.id]}
								placeholder="Enter {getCleanLabel(section.label).toLowerCase()}..."
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
								rows="3"
							></textarea>
						</div>
					{/each}
				</div>
			</div>

			<!-- Generate Button -->
			<div class="pt-4 border-t border-gray-200 dark:border-gray-700">
				<button
					on:click={generateSection}
					disabled={generating}
					class="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
				>
					{#if generating}
						<svg class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
							<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"></circle>
							<path fill="currentColor" class="opacity-75" d="m12 2 A10 10 0 0 1 22 12"></path>
						</svg>
						Generating...
					{:else}
						Generate Sections
					{/if}
				</button>
			</div>
		{:else}
			<div class="flex-1 flex items-center justify-center">
				<p class="text-gray-500 dark:text-gray-400 text-center">
					Please select a sponsor to view the form sections
				</p>
			</div>
		{/if}
	</div>
{/if}
