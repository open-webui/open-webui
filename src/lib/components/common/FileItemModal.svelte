<script lang="ts">
	import { getContext, onMount, tick, afterUpdate } from 'svelte';
	import { formatFileSize, getLineCount } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getKnowledgeById } from '$lib/apis/knowledge';
	import { getFileById, updateFilePiiStateById, updateFileDataContentById } from '$lib/apis/files';
	import {
		createPiiHighlightStyles,
		PiiSessionManager,
		type ExtendedPiiEntity
	} from '$lib/utils/pii';
	import type { PiiEntity } from '$lib/apis/pii';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import { config } from '$lib/stores';
	import type { i18n as i18nType } from 'i18next';
	import type { Writable } from 'svelte/store';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';
	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';
	import Mask from '../icons/Mask.svelte';
	import dayjs from 'dayjs';
	import Spinner from './Spinner.svelte';

	export let item: any;
	export let show = false;
	export let edit = false;
	export let conversationId: string | undefined = undefined; // chat conversation context to store known entities/modifiers

	let enableFullContent = false;

	// Debounced PII state saver for uploaded files
	let savePiiTimeout: any = null;
	const savePiiStateDebounced = (fileId: string) => {
		if (savePiiTimeout) clearTimeout(savePiiTimeout);
		savePiiTimeout = setTimeout(async () => {
			try {
				const state = PiiSessionManager.getInstance().getConversationState(conversationId || '');
				if (state && fileId) {
					await updateFilePiiStateById(localStorage.token, fileId, state);
				}
			} catch (e) {
				// silent
			}
		}, 400);
	};

	// Handle PII detection results - save PII entities but keep original text
	const handlePiiDetected = async (entities: ExtendedPiiEntity[], maskedText: string) => {
		if (!item?.id) return;

		try {
			// Prepare PII payload in the format expected by the backend
			const piiPayload: Record<string, any> = {};
			entities.forEach((entity) => {
				const key = entity.raw_text || entity.label;
				if (!key) return;
				piiPayload[key] = {
					id: entity.id,
					label: entity.label,
					type: entity.type || 'PII',
					text: (entity.text || entity.label).toLowerCase(),
					raw_text: entity.raw_text || entity.label,
					occurrences: (entity.occurrences || []).map((o) => ({
						start_idx: o.start_idx,
						end_idx: o.end_idx
					}))
				};
			});

			// Get current PII state
			const state = PiiSessionManager.getInstance().getConversationState(conversationId || '');

			// Get the original unmasked text from the file
			const originalText = item?.file?.data?.content || '';

			// Update file with PII entities but keep original text
			await updateFileDataContentById(localStorage.token, item.id, originalText, {
				pii: piiPayload,
				piiState: (state as Record<string, any>) || undefined
			});
		} catch (e) {
			// silent
		}
	};

	// Get the display name and masking status for the modal title
	$: ({ displayName, isFilenameMasked } = (() => {
		const name = item?.name;
		if (!name) {
			return { displayName: 'File', isFilenameMasked: false };
		}

		// Only try to unmask if PII detection is available
		try {
			// Safe config access - use ?? false to handle missing properties
			const piiEnabled = $config?.features?.enable_pii_detection ?? false;
			if (!piiEnabled) {
				return { displayName: name, isFilenameMasked: false };
			}

			// Check if name looks like a UUID or file ID (indicating it's masked)
			const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
			const shortIdPattern = /^[a-zA-Z0-9_-]{8,32}$/;

			const looksLikeMaskedId =
				uuidPattern.test(name) || (shortIdPattern.test(name) && !name.includes('.'));

			if (looksLikeMaskedId) {
				const piiSessionManager = PiiSessionManager.getInstance();
				let mapping = null;

				// Try conversation-specific mappings first
				if (conversationId) {
					const mappings = piiSessionManager.getFilenameMappingsForDisplay(conversationId);
					mapping = mappings.find((m) => m.fileId === name || m.maskedFilename === name);
				}

				// For new chats without conversation ID, check temporary state
				if (!mapping) {
					const tempMappings = piiSessionManager.getTemporaryFilenameMappings();
					mapping = tempMappings.find((m) => m.fileId === name || m.maskedFilename === name);
				}

				// Also check if the item itself has the original name stored
				if (!mapping && item?.meta?.name && item.meta.name !== name) {
					return { displayName: item.meta.name, isFilenameMasked: true };
				}

				if (mapping && mapping.originalFilename) {
					return { displayName: mapping.originalFilename, isFilenameMasked: true };
				}
			}

			return { displayName: name, isFilenameMasked: looksLikeMaskedId };
		} catch (e) {
			// If anything fails, just return the name as-is
			console.log('FileItemModal: displayName computation failed:', e);
			return { displayName: name, isFilenameMasked: false };
		}
	})());

	let isPdf = false;
	let isDocx = false;
	let isAudio = false;
	let loading = false;
	let contextMenuEl: HTMLElement | null = null; // legacy, will be removed

	// Scroll locking to prevent viewport jumps while backend updates arrive
	let scrollContainerEl: HTMLElement | null = null;
	let cachedScrollTop = 0;
	let isScrollLocked = false;
	let hasRestoredScroll = false;
	function handleScroll() {
		// Allow user scrolling; do not override while user scrolls
		if (scrollContainerEl) {
			cachedScrollTop = scrollContainerEl.scrollTop;
		}
	}

	afterUpdate(() => {
		// Apply one-time restoration after initial content lock, then release
		if (isScrollLocked && scrollContainerEl && !hasRestoredScroll) {
			scrollContainerEl.scrollTop = cachedScrollTop;
			hasRestoredScroll = true;
			isScrollLocked = false;
		}
	});

	// Detect file types we render as extracted text (pdf, docx)
	// Use original filename from meta if available (for PII-masked files)
	$: actualFileName = item?.meta?.name || item?.name || '';
	$: isPdf =
		item?.meta?.content_type === 'application/pdf' ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.pdf'));

	$: isDocx =
		item?.meta?.content_type ===
			'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.docx'));

	$: isAudio =
		(item?.meta?.content_type ?? '').startsWith('audio/') ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.mp3')) ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.wav')) ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.ogg')) ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.m4a')) ||
		(actualFileName && actualFileName.toLowerCase().endsWith('.webm'));

	const loadContent = async () => {
		if (item?.type === 'collection') {
			loading = true;

			const knowledge = await getKnowledgeById(localStorage.token, item.id).catch((e) => {
				console.error('Error fetching knowledge base:', e);
				return null;
			});

			if (knowledge) {
				item.files = knowledge.files || [];
			}
			loading = false;
		} else if (item?.id) {
			// Refresh file metadata/data to ensure page_content and pii are present
			try {
				loading = true;
				const fresh = await getFileById(localStorage.token, item.id).catch(() => null);
				if (fresh) {
					item.file = fresh;
				}
			} catch (e) {
				// ignore
			} finally {
				loading = false;
			}
		}

		await tick();
	};

	$: if (show) {
		loadContent();
	}

	// Inject highlight styles once when modal mounts and PII preview is relevant
	let stylesInjected = false;
	function ensureHighlightStyles() {
		if (stylesInjected) return;
		const styleElement = document.createElement('style');
		styleElement.textContent = createPiiHighlightStyles();
		document.head.appendChild(styleElement);
		stylesInjected = true;
	}

	onMount(() => {
		if (item?.context === 'full') {
			enableFullContent = true;
		}
		ensureHighlightStyles();

		// No custom context menu needed; TipTap handles clicks/menus
	});

	// All entity interactions handled by TipTap extensions; remove custom menu

	// Compute external URL for non-previewable types
	$: externalUrl = item?.url ? (item.type === 'file' ? `${item.url}/content` : `${item.url}`) : '';

	// Build extended entities from backend detections (shape from retrieval.py)
	$: extendedEntities = (() => {
		const detections: any = item?.file?.data?.pii || null;
		if (!detections) return [] as ExtendedPiiEntity[];
		// detections is a dict keyed by raw text; values carry id,label,type,occurrences
		const values = Object.values(detections) as any[];
		const entities: ExtendedPiiEntity[] = values
			.map((e) => ({
				id: e.id,
				label: e.label,
				type: e.type || e.entity_type || 'PII',
				text: e.text || e.raw_text || e.name || '', // Add required 'text' field
				raw_text: e.raw_text || e.text || e.name || '',
				occurrences: (e.occurrences || []).map((o: any) => ({
					start_idx: o.start_idx,
					end_idx: o.end_idx
				})),
				shouldMask: true
			}))
			.filter((e) => e.raw_text && e.raw_text.trim() !== '');
		return entities;
	})();

	// Track changes in entities to trigger editor re-sync without changing content
	let lastEntitiesKey = '';
	function makeEntitiesKey(entities: ExtendedPiiEntity[]): string {
		if (!Array.isArray(entities)) return '';
		try {
			return entities
				.map((e) => `${e.label}:${e.type}:${e.raw_text}:${(e.occurrences || []).length}`)
				.sort()
				.join('|');
		} catch {
			return '';
		}
	}

	// When modal opens, seed PII session so RichTextInput-like behavior is possible in chat
	$: if (show) {
		try {
			const manager = PiiSessionManager.getInstance();
			if (Array.isArray(extendedEntities) && extendedEntities.length > 0) {
				if (conversationId && conversationId.trim() !== '') {
					// Persist entities for this conversation as known entities
					manager.setConversationEntitiesFromLatestDetection(conversationId, extendedEntities);
				} else {
					// New chat without conversationId: seed temporary state so extensions can render
					if (!manager.isTemporaryStateActive()) {
						manager.activateTemporaryState();
					}
					manager.setTemporaryStateEntities(extendedEntities);
				}
			}
		} catch (e) {}
	}

	// Determine pages to render; freeze after first successful load to avoid content shifts
	let initialPageContents: string[] = [];
	let hasLockedPageContents = false;

	function computePageContents(): string[] {
		const pc = item?.file?.data?.page_content;
		if (Array.isArray(pc) && pc.length > 0) return pc as string[];
		const content = item?.file?.data?.content || '';
		return content ? [content] : [];
	}

	$: {
		const next = computePageContents();
		if (!hasLockedPageContents && next.length > 0) {
			initialPageContents = next;
			hasLockedPageContents = true;
			// prepare one-time scroll restore once content is available
			if (scrollContainerEl) cachedScrollTop = scrollContainerEl.scrollTop;
			isScrollLocked = true;
			hasRestoredScroll = false;
		}
	}

	$: pageContents = hasLockedPageContents ? initialPageContents : computePageContents();

	// No precomputed HTML highlights; TipTap handles decorations

	// Keep per-page editor refs to sync PII entities from session
	let editors: any[] = [];
	let hasInitialSynced = false;

	// PII detection loading state
	let isPiiDetectionInProgress = false;

	function syncEditorsNow() {
		editors.forEach((ed) => {
			try {
				if (!ed || !ed.commands) return;
				if (typeof ed.commands.reloadConversationState === 'function') {
					ed.commands.reloadConversationState(conversationId);
				}
				if (typeof ed.commands.syncWithSessionManager === 'function') {
					ed.commands.syncWithSessionManager();
				}
				if (typeof ed.commands.forceEntityRemapping === 'function') {
					ed.commands.forceEntityRemapping();
				}
			} catch (e) {}
		});
	}

	// When extendedEntities change (PII detections update), re-sync editors to update highlights
	$: {
		const key = makeEntitiesKey(extendedEntities);
		if (key && key !== lastEntitiesKey) {
			lastEntitiesKey = key;
			// Do not touch pageContents; only refresh decorations via commands
			setTimeout(() => {
				syncEditorsNow();
			}, 0);
		}
	}

	// Reset sync flag when modal closes
	$: if (!show) {
		hasInitialSynced = false;
		hasLockedPageContents = false;
		initialPageContents = [];
		isScrollLocked = false;
	}

	// After showing modal, extended entities seeded (conv or temp), and editors mounted → sync once
	$: if (
		show &&
		Array.isArray(editors) &&
		editors.length > 0 &&
		extendedEntities.length > 0 &&
		!hasInitialSynced
	) {
		hasInitialSynced = true;
		setTimeout(() => {
			syncEditorsNow();
		}, 100);
	}
</script>

<Modal bind:show size="lg">
	<div
		class="font-primary px-6 py-5 w-full flex flex-col justify-center dark:text-gray-400 relative"
	>
		<div class=" pb-2">
			<div class="flex items-start justify-between">
				<div class="flex-1 min-w-0">
					<div class="font-medium text-lg dark:text-gray-100 flex items-center">
						<a
							href={externalUrl || undefined}
							rel="noopener noreferrer"
							target="_blank"
							class="hover:underline line-clamp-1 inline-flex items-center gap-1.5"
							on:click|preventDefault={() => {
								// Keep external open behavior only for non-previewable types
								if (!(isPdf || isDocx) && externalUrl) {
									window.open(externalUrl, '_blank');
								}
							}}
						>
							<span>{displayName}</span>
							{#if isFilenameMasked}
								<Tooltip content={$i18n.t('Filename masked for privacy')} placement="top">
									<div
										class="flex items-center justify-center size-5 bg-sky-50 dark:bg-sky-200/10 text-sky-600 dark:text-sky-400 rounded-full flex-shrink-0"
									>
										<Mask className="size-3" />
									</div>
								</Tooltip>
							{/if}
							{#if isPiiDetectionInProgress}
								<div
									class="flex items-center gap-1 bg-gray-50 dark:bg-gray-850 px-2 py-1 rounded-md shadow-sm border border-gray-200 dark:border-gray-700 ml-2"
								>
									<Spinner className="size-3" />
									<span class="text-xs text-gray-600 dark:text-gray-400">Scanning for PII...</span>
								</div>
							{/if}
						</a>
					</div>
				</div>

				<div>
					<button
						on:click={() => {
							show = false;
						}}
					>
						<XMark />
					</button>
				</div>
			</div>

			<div>
				<div class="flex flex-col items-center md:flex-row gap-1 justify-between w-full">
					<div class=" flex flex-wrap text-sm gap-1 text-gray-500">
						{#if item?.type === 'collection'}
							{#if item?.type}
								<div class="capitalize shrink-0">{item.type}</div>
								•
							{/if}

							{#if item?.description}
								<div class="line-clamp-1">{item.description}</div>
								•
							{/if}

							{#if item?.created_at}
								<div class="capitalize shrink-0">
									{dayjs(item.created_at * 1000).format('LL')}
								</div>
							{/if}
						{/if}

						{#if item.size}
							<div class="capitalize shrink-0">{formatFileSize(item.size)}</div>
							•
						{/if}

						{#if item?.file?.data?.content}
							<div class="capitalize shrink-0">
								{getLineCount(item?.file?.data?.content ?? '')} extracted lines
							</div>

							<div class="flex items-center gap-1 shrink-0">
								<Info />

								Formatting may be inconsistent from source.
							</div>
						{/if}

						{#if item?.file?.meta?.processing?.status === 'processing'}
							<div class="flex items-center gap-3 shrink-0">
								<div class="h-1.5 bg-gray-200 dark:bg-gray-800 rounded w-44 overflow-hidden">
									<div
										class="h-full bg-sky-500 transition-all duration-300"
										style={`width: ${Math.min(100, Math.max(0, item?.file?.meta?.processing?.progress ?? 0))}%`}
									/>
								</div>
								{#if item?.file?.meta?.processing?.stage === 'extracting'}
									<span>Extracting text…</span>
								{:else if item?.file?.meta?.processing?.stage === 'pii_detection'}
									<span>Masking PII…</span>
								{:else}
									<span>Processing…</span>
								{/if}
							</div>
						{/if}

						{#if item?.knowledge}
							<div class="capitalize shrink-0">
								{$i18n.t('Knowledge Base')}
							</div>
						{/if}
					</div>

					{#if edit}
						<div>
							<Tooltip
								content={enableFullContent
									? $i18n.t(
											'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
										)
									: $i18n.t(
											'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
										)}
							>
								<div class="flex items-center gap-1.5 text-xs">
									{#if enableFullContent}
										{$i18n.t('Using Entire Document')}
									{:else}
										{$i18n.t('Using Focused Retrieval')}
									{/if}
									<Switch
										bind:state={enableFullContent}
										on:change={(e) => {
											item.context = e.detail ? 'full' : undefined;
										}}
									/>
								</div>
							</Tooltip>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class="max-h-[75vh] overflow-auto" bind:this={scrollContainerEl} on:scroll={handleScroll}>
			{#if !loading}
				{#if item?.type === 'collection'}
					<div>
						{#each item?.files as file}
							<div class="flex items-center gap-2 mb-2">
								<div class="flex-shrink-0 text-xs">
									{file?.meta?.name}
								</div>
							</div>
						{/each}
					</div>
				{:else}
					{#if isAudio}
						<audio
							src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
							class="w-full border-0 rounded-lg mb-2"
							controls
							playsinline
						/>
					{/if}

					{#if isPdf || isDocx}
						<!-- Render extracted text with TipTap editors per page (PII + Modifiers like RichTextInput) -->
						{#if pageContents.length > 0}
							<div class="space-y-6 mt-3">
								{#each pageContents as pageText, idx}
									<div
										class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850"
									>
										<div
											class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between"
										>
											<div>Page {idx + 1}</div>
											{#if item?.file?.meta?.processing?.status === 'processing'}
												<div class="flex items-center gap-2 w-48">
													<div
														class="h-1.5 bg-gray-200 dark:bg-gray-800 rounded w-full overflow-hidden"
													>
														<div
															class="h-full bg-sky-500 transition-all duration-300"
															style={`width: ${Math.min(100, Math.max(0, item?.file?.meta?.processing?.progress ?? 0))}%`}
														/>
													</div>
													{#if item?.file?.meta?.processing?.stage === 'extracting'}
														<span>Extracting</span>
													{:else if item?.file?.meta?.processing?.stage === 'pii_detection'}
														<span>Masking PII</span>
													{:else}
														<span>Processing</span>
													{/if}
												</div>
											{/if}
										</div>
										<div class="p-3">
											<RichTextInput
												bind:editor={editors[idx]}
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
												enablePiiModifiers={true}
												disableModifierTriggeredDetection={true}
												onPiiToggled={(entities) => {
													// When PII is toggled on one page, sync all other pages
													editors.forEach((ed, edIdx) => {
														if (edIdx !== idx && ed && ed.commands?.syncWithSessionManager) {
															setTimeout(() => {
																ed.commands.syncWithSessionManager();
															}, 10);
														}
													});
												}}
												onPiiModifiersChanged={async () => {
													// When modifiers change, trigger re-detection on all pages
													if (!item?.id || !pageContents || pageContents.length === 0) return;

													try {
														const apiKey = $config?.pii?.api_key;
														if (!apiKey) return;

														// Set loading state
														isPiiDetectionInProgress = true;

														const piiSessionManager = PiiSessionManager.getInstance();
														const knownEntities = piiSessionManager.getKnownEntitiesForApi(conversationId);
														const modifiers = piiSessionManager.getModifiersForApi(conversationId);

														// Send complete document text as one string to PII API
														const { maskPiiText } = await import('$lib/apis/pii');
														const completeText = pageContents.join('\n'); // Join all pages with double newlines
														
														const response = await maskPiiText(
															apiKey,
															[completeText],
															knownEntities,
															modifiers,
															false,
															false
														);

														if (response.pii && response.pii[0] && response.pii[0].length > 0) {
															// Process entities from complete document
															const allEntities = response.pii[0];

															// Create PII payload for complete document
															const piiPayload = {};
															allEntities.forEach((entity) => {
																const key = entity.raw_text || entity.label;
																if (!key) return;
																// @ts-ignore - Dynamic object key assignment
																piiPayload[key] = {
																	id: entity.id,
																	label: entity.label,
																	type: entity.type || 'PII',
																	text: (entity.text || entity.label).toLowerCase(),
																	raw_text: entity.raw_text || entity.label,
																	occurrences: (entity.occurrences || []).map((o) => ({
																		start_idx: o.start_idx,
																		end_idx: o.end_idx
																	}))
																};
															});

															// Get current PII state including modifiers
															const state = piiSessionManager.getConversationState(conversationId || '');
															
														// Update session manager with all entities
														if (conversationId && conversationId.trim() !== '') {
															piiSessionManager.setConversationEntitiesFromLatestDetection(conversationId, allEntities);
														} else {
															// For new chats without conversationId, update temporary state
															piiSessionManager.setTemporaryStateEntities(allEntities);
														}
															
															// Get the original unmasked text from the file
															const originalText = item?.file?.data?.content || '';
															
															// Update file with new PII entities and modifiers
															await updateFileDataContentById(localStorage.token, item.id, originalText, {
																pii: piiPayload,
																piiState: state || undefined
															});

															// Sync all editors to show the updated highlights
															syncEditorsNow();
															
														}
													} catch (e) {
														console.error('FileItemModal: Failed to re-detect PII with modifiers:', e);
													} finally {
														// Clear loading state
														isPiiDetectionInProgress = false;
													}
												}}
												onPiiDetected={handlePiiDetected}
												piiModifierLabels={[
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
												]}
												messageInput={false}
											/>
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<div class="flex items-center justify-center py-6 text-sm text-gray-500">
								No extracted text available yet.
							</div>
						{/if}
					{:else if item?.file?.data}
						<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
							{item?.file?.data?.content ?? 'No content'}
						</div>
					{/if}
				{/if}
			{:else}
				<div class="flex items-center justify-center py-6">
					<Spinner className="size-5" />
				</div>
			{/if}
		</div>
	</div>
</Modal>

<style>
	/* Ensure text selection is enabled and visible in read-only PII editors */
	:global(.pii-selectable .tiptap) {
		user-select: text !important;
		-webkit-user-select: text !important;
		-moz-user-select: text !important;
		-ms-user-select: text !important;
	}

	:global(.pii-selectable .tiptap::selection),
	:global(.pii-selectable .tiptap *::selection) {
		background-color: rgba(100, 108, 255, 0.3) !important;
	}

	:global(.pii-selectable .tiptap::-moz-selection),
	:global(.pii-selectable .tiptap *::-moz-selection) {
		background-color: rgba(100, 108, 255, 0.3) !important;
	}
</style>
