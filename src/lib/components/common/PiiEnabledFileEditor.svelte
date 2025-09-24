<script lang="ts">
	/**
	 * PiiEnabledFileEditor.svelte
	 *
	 * A reusable component that provides PII-enabled file content editing.
	 * Used for PDF (non-preview) and Word files with complex PII detection,
	 * highlighting, and modifier functionality.
	 */

	import { getContext } from 'svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import { config } from '$lib/stores';
	import {
		PiiSessionManager,
		createPiiPayloadFromEntities,
		type ExtendedPiiEntity
	} from '$lib/utils/pii';
	import { updateFileDataContentById } from '$lib/apis/files';
	import type { i18n as i18nType } from 'i18next';
	import type { Writable } from 'svelte/store';
	import Spinner from './Spinner.svelte';

	// Get i18n context for translations
	const i18n = getContext<Writable<i18nType>>('i18n');

	// Component props - these are the "inputs" to our component
	export let pageContents: string[] = []; // Array of text content for each page
	export let conversationId: string | undefined = undefined; // Chat context for PII state
	export let isFileProcessing: boolean = false; // Whether file is still being processed
	export let fileId: string | undefined = undefined; // File ID for API updates
	export let originalFileContent: string = ''; // Original unmasked file content

	// Optional callback for when PII detection is in progress
	export let onPiiDetectionProgress: ((inProgress: boolean) => void) | undefined = undefined;

	// TypeScript type annotation: This tells TypeScript what type this variable should hold
	// "any[]" means "an array that can hold any type of values"
	let editors: any[] = [];

	// TypeScript: This uses a "union type" - the variable can be either boolean OR undefined
	let isPiiDetectionInProgress: boolean | undefined = false;

	// Reactive statement ($ prefix): This code runs whenever isPiiDetectionInProgress changes
	$: if (onPiiDetectionProgress) {
		onPiiDetectionProgress(isPiiDetectionInProgress || false);
	}

	// Array of PII modifier labels that users can select from
	const piiModifierLabels = [
		'PERSON',
		'EMAIL',
		'PHONE_NUMBER',
		'ADDRESS',
		'SSN',
		'CREDIT_CARD',
		'DATE_TIME',
		'IP_ADDRESS',
		'URL',
		'IBAN',
		'MEDICAL_LICENSE',
		'US_PASSPORT',
		'US_DRIVER_LICENSE'
	];

	/**
	 * Handler for when PII entities are toggled (masked/unmasked) in one editor.
	 * This syncs the change across all other editors so they stay consistent.
	 *
	 * @param entities - Array of PII entities that were updated
	 * @param currentEditorIndex - Index of the editor where the toggle happened
	 */
	function handlePiiToggled(entities: ExtendedPiiEntity[], currentEditorIndex: number) {
		// Prevent PII toggling during file processing
		if (isFileProcessing) {
			console.log('PiiEnabledFileEditor: PII toggling blocked - file is still processing');
			return;
		}

		// Sync all other editors to show the same PII state
		// TypeScript: forEach is a method that runs a function for each item in the array
		editors.forEach((editor, editorIndex) => {
			// Skip the editor where the change originated
			if (editorIndex !== currentEditorIndex && editor && editor.commands?.syncWithSessionManager) {
				// setTimeout creates a small delay to ensure the state update completes first
				setTimeout(() => {
					editor.commands.syncWithSessionManager();
				}, 10);
			}
		});
	}

	/**
	 * Handler for when PII modifiers are changed. This triggers re-detection
	 * of PII across the entire document with the new modifier rules.
	 *
	 * This is an "async function" - it can perform operations that take time
	 * without blocking the user interface.
	 */
	async function handlePiiModifiersChanged() {
		// Prevent modifier changes during file processing
		if (isFileProcessing) {
			console.log('PiiEnabledFileEditor: Modifier changes blocked - file is still processing');
			return;
		}

		// Make sure we have the necessary data to proceed
		if (!fileId || !pageContents || pageContents.length === 0) return;

		try {
			// Get API key from configuration
			// TypeScript: The "?." is called "optional chaining" - it safely accesses nested properties
			const apiKey = $config?.pii?.api_key;
			if (!apiKey) return;

			// Set loading state to show spinner
			isPiiDetectionInProgress = true;

			// Get PII session manager (singleton pattern - only one instance exists)
			const piiSessionManager = PiiSessionManager.getInstance();
			const modifiers = piiSessionManager.getModifiersForApi(conversationId);

			// Get existing entities with their original text positions
			const piiEntities = piiSessionManager.getEntitiesForApiWithOriginalPositions(conversationId);

			// Import the PII API function dynamically (loads code only when needed)
			const { updatePiiMasking } = await import('$lib/apis/pii');

			// Join all pages into one string for API processing
			const completeText = pageContents.join('');

			// Call the PII API to re-detect with new modifiers
			const response = await updatePiiMasking(apiKey, completeText, piiEntities, modifiers, false);

			if (response.pii && response.pii.length > 0) {
				// Convert API response to our internal entity format
				// TypeScript: "ExtendedPiiEntity[]" means "an array of ExtendedPiiEntity objects"
				const allEntities: ExtendedPiiEntity[] = [];

				for (const entity of response.pii) {
					allEntities.push({
						...entity, // Spread operator: copies all properties from entity
						shouldMask: true,
						// Store original positions for consistent mapping
						originalOccurrences: entity.occurrences.map((o) => ({
							start_idx: o.start_idx,
							end_idx: o.end_idx
						}))
					});
				}

				// Create payload for backend storage
				const piiPayload = createPiiPayloadFromEntities(allEntities);

				// Get current PII state for storage
				let state: Record<string, any> | undefined;
				if (conversationId) {
					state = piiSessionManager.getConversationState(conversationId) || undefined;
				} else {
					state = piiSessionManager.getTemporaryState() || undefined;
				}

				// Update session manager with new entities
				if (conversationId && conversationId.trim() !== '') {
					piiSessionManager.setConversationWorkingEntitiesWithMaskStates(
						conversationId,
						allEntities
					);
				} else {
					// For new chats without conversationId, update temporary state
					piiSessionManager.setTemporaryStateEntities(allEntities);
				}

				// Update the file in the backend with new PII data
				await updateFileDataContentById(localStorage.token, fileId, originalFileContent, {
					pii: piiPayload,
					piiState: state
				});

				// Sync all editors to show the updated highlights
				syncAllEditors();
			}
		} catch (e) {
			console.error('PiiEnabledFileEditor: Failed to re-detect PII with modifiers:', e);
		} finally {
			// Always clear loading state, even if there was an error
			isPiiDetectionInProgress = false;
		}
	}

	/**
	 * Utility function to sync all editors with the current PII state.
	 * This refreshes the PII highlights without changing the text content.
	 */
	function syncAllEditors() {
		editors.forEach((editor) => {
			try {
				if (!editor || !editor.commands) return;

				// Call various sync methods if they exist
				// TypeScript: "typeof" checks if a property is a function before calling it
				if (typeof editor.commands.reloadConversationState === 'function') {
					editor.commands.reloadConversationState(conversationId);
				}
				if (typeof editor.commands.syncWithSessionManager === 'function') {
					editor.commands.syncWithSessionManager();
				}
				if (typeof editor.commands.forceEntityRemapping === 'function') {
					editor.commands.forceEntityRemapping();
				}
			} catch (e) {
				// Silently handle any errors during sync
			}
		});
	}

	// Export this function so parent components can trigger a sync
	export { syncAllEditors };
</script>

<!-- 
	The template section defines what gets rendered in the HTML.
	Svelte uses {#each} for loops, {#if} for conditionals, and {} for expressions.
-->

{#if pageContents.length > 0}
	<div class="space-y-6 mt-3">
		{#each pageContents as pageText, pageIndex}
			<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850">
				<div
					class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between"
				>
					<div>{$i18n.t('Page {{number}}', { number: pageIndex + 1 })}</div>
					{#if isFileProcessing}
						<div class="flex items-center gap-2 w-48">
							<div class="h-1.5 bg-gray-200 dark:bg-gray-800 rounded w-full overflow-hidden">
								<!-- Progress bar would go here if we had progress data -->
								<div class="h-full bg-sky-500 transition-all duration-300" style="width: 50%"></div>
							</div>
							<span>{$i18n.t('Processing')}</span>
						</div>
					{/if}
					{#if isPiiDetectionInProgress}
						<div
							class="flex items-center gap-1 bg-gray-50 dark:bg-gray-850 px-2 py-1 rounded-md shadow-sm border border-gray-200 dark:border-gray-700"
						>
							<Spinner className="size-3" />
							<span class="text-xs text-gray-600 dark:text-gray-400">Scanning for PII...</span>
						</div>
					{/if}
				</div>
				<div class="p-3">
					<!-- 
						The {#key} block ensures the RichTextInput re-renders when isFileProcessing changes.
						This is important for maintaining proper editor state.
					-->
					{#key `${isFileProcessing}-${pageIndex}`}
						<RichTextInput
							bind:editor={editors[pageIndex]}
							className="input-prose-sm pii-selectable"
							value={pageText}
							preserveBreaks={false}
							raw={false}
							editable={true}
							preventDocEdits={true}
							showFormattingToolbar={false}
							enablePiiDetection={true}
							piiApiKey={$config?.pii?.api_key || 'preview-only'}
							{conversationId}
							piiMaskingEnabled={true}
							enablePiiModifiers={!isFileProcessing}
							disableModifierTriggeredDetection={true}
							usePiiMarkdownMode={true}
							onPiiToggled={(entities) => handlePiiToggled(entities, pageIndex)}
							onPiiModifiersChanged={handlePiiModifiersChanged}
							{piiModifierLabels}
							messageInput={false}
						/>
					{/key}
				</div>
			</div>
		{/each}
	</div>
{:else}
	<div class="flex items-center justify-center py-6 text-sm text-gray-500">
		{$i18n.t('No extracted text available yet.')}
	</div>
{/if}
