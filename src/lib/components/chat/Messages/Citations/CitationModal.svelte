<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { settings, config, models } from '$lib/stores';
	import { injectCsp } from '$lib/utils/csp';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import VideoPlayerWithTimeline from './VideoPlayerWithTimeline.svelte';
	import { getFileById, generateChapters } from '$lib/apis/files';

	const i18n = getContext('i18n');
	
	/**
	 * Get video URL for a document, deriving it from file_id if not explicitly set.
	 * This provides backward compatibility for files indexed before video_url was added.
	 */
	function getVideoUrl(doc: any): string | null {
		// Use explicit video_url if available
		if (doc.metadata?.video_url) {
			return doc.metadata.video_url;
		}
		// Derive from file_id if we have video_segment_url (indicates it's a video)
		if (doc.metadata?.video_segment_url && doc.metadata?.file_id) {
			return `/api/v1/files/${doc.metadata.file_id}/video`;
		}
		return null;
	}
	
	// UI State
	let copySuccess = false;
	let emailSending = false;
	let emailSuccess = false;
	let emailError = '';
	
	// Chapter state
	let fileChapters: Record<string, any[]> = {}; // Cache chapters by file_id
	let chaptersLoading: Record<string, boolean> = {};
	let chaptersGenerating: Record<string, boolean> = {};
	let chaptersError: Record<string, string> = {};
	
	/**
	 * Fetch file data to get chapters
	 */
	async function fetchFileChapters(fileId: string) {
		if (fileChapters[fileId] || chaptersLoading[fileId]) return;
		
		chaptersLoading[fileId] = true;
		try {
			const token = localStorage.getItem('token') ?? '';
			if (!token) return;
			const file = await getFileById(token, fileId);
			if (file?.meta?.chapters) {
				fileChapters[fileId] = file.meta.chapters;
				fileChapters = fileChapters; // Trigger reactivity
			}
		} catch (err) {
			console.error('Failed to fetch file chapters:', err);
		} finally {
			chaptersLoading[fileId] = false;
			chaptersLoading = chaptersLoading;
		}
	}
	
	/**
	 * Generate chapters for a file using LLM
	 */
	async function handleGenerateChapters(fileId: string) {
		if (chaptersGenerating[fileId]) return;
		
		// Get default model from store
		const modelList = $models || [];
		const defaultModel = modelList.find(m => m.id) || modelList[0];
		if (!defaultModel) {
			chaptersError[fileId] = 'No model available';
			chaptersError = chaptersError;
			return;
		}
		
		chaptersGenerating[fileId] = true;
		chaptersError[fileId] = '';
		chaptersGenerating = chaptersGenerating;
		chaptersError = chaptersError;
		
		try {
			const token = localStorage.getItem('token') ?? '';
			if (!token) {
				chaptersError[fileId] = 'Not authenticated';
				return;
			}
			const result = await generateChapters(token, fileId, defaultModel.id);
			if (result?.chapters) {
				fileChapters[fileId] = result.chapters;
				fileChapters = fileChapters;
			}
		} catch (err: any) {
			console.error('Failed to generate chapters:', err);
			chaptersError[fileId] = err.message || 'Failed to generate chapters';
			chaptersError = chaptersError;
		} finally {
			chaptersGenerating[fileId] = false;
			chaptersGenerating = chaptersGenerating;
		}
	}
	
	/**
	 * Get chapters for a file, fetching if needed
	 */
	function getChaptersForFile(fileId: string | undefined): any[] {
		if (!fileId) return [];
		
		// Trigger fetch if not cached
		if (!fileChapters[fileId] && !chaptersLoading[fileId]) {
			fetchFileChapters(fileId);
		}
		
		return fileChapters[fileId] || [];
	}
	
	// Shared utilities for report generation
	function getReportContent(): string {
		return mergedDocuments.map(d => d.document).join('\n\n---\n\n');
	}
	
	function getReportSubject(): string {
		return `Report: ${citation?.source?.name || 'Citation'}`;
	}
	
	/**
	 * Copy full citation content to clipboard
	 */
	async function copyToClipboard() {
		try {
			await navigator.clipboard.writeText(getReportContent());
			copySuccess = true;
			setTimeout(() => copySuccess = false, 2000);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	}
	
	/**
	 * Send report via Gmail API (full content, no truncation)
	 */
	async function sendViaGmail() {
		emailSending = true;
		emailError = '';
		emailSuccess = false;
		
		try {
			const token = localStorage.getItem('token');
			const res = await fetch(`${WEBUI_API_BASE_URL}/gmail/send`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${token}`
				},
				body: JSON.stringify({
					subject: getReportSubject(),
					body: getReportContent(),
					is_markdown: true
				})
			});
			
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || 'Failed to send email');
			}
			
			emailSuccess = true;
			setTimeout(() => emailSuccess = false, 3000);
		} catch (err: any) {
			console.error('Email send failed:', err);
			emailError = err.message || 'Failed to send email';
			setTimeout(() => emailError = '', 5000);
		} finally {
			emailSending = false;
		}
	}
	
	// Shared class for markdown prose styling with tighter spacing
	const PROSE_CLASS = 'prose dark:prose-invert prose-sm max-w-full prose-headings:mt-4 prose-headings:mb-2 prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-hr:my-3';
	
	/**
	 * Detect if content contains markdown formatting.
	 * Checks for common markdown patterns like headers, bold, lists, etc.
	 */
	function isMarkdownContent(text: string): boolean {
		if (!text) return false;
		const markdownPatterns = [
			/^#{1,6}\s/m,           // Headers
			/\*\*[^*]+\*\*/,        // Bold
			/\*[^*]+\*/,            // Italic
			/^\s*[-*+]\s/m,         // Unordered lists
			/^\s*\d+\.\s/m,         // Ordered lists
			/^>\s/m,                // Blockquotes
			/```[\s\S]*?```/,       // Code blocks
			/`[^`]+`/,              // Inline code
			/\[.+\]\(.+\)/,         // Links
			/^---+$/m,              // Horizontal rules
			/^\|.+\|$/m,            // Tables
		];
		return markdownPatterns.some(pattern => pattern.test(text));
	}
	
	// Audio blob URLs for authenticated requests
	let audioBlobUrls = {};

	const CONTENT_PREVIEW_LIMIT = 10000;
	let expandedDocs: Set<number> = new Set();

	export let show = false;
	export let citation;
	export let showPercentage = false;
	export let showRelevance = true;

	let mergedDocuments = [];

	function calculatePercentage(distance: number) {
		if (typeof distance !== 'number') return null;
		if (distance < 0) return 0;
		if (distance > 1) return 100;
		return Math.round(distance * 10000) / 100;
	}

	function getRelevanceColor(percentage: number) {
		// Lower percentage = higher relevance (inverted scale)
		if (percentage <= 20)
			return 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200';
		if (percentage <= 40)
			return 'bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200';
		if (percentage <= 60)
			return 'bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200';
		return 'bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200';
	}
	
	function getRelevanceLabel(percentage: number) {
		// Lower percentage = higher relevance
		if (percentage <= 20) return 'Highly Relevant';
		if (percentage <= 40) return 'Relevant';
		if (percentage <= 60) return 'Moderately Relevant';
		return 'Low Relevance';
	}

	$: if (citation) {
		expandedDocs = new Set();
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i],
				distance: citation.distances?.[i]
			};
		});
		if (mergedDocuments.every((doc) => doc.distance !== undefined)) {
			mergedDocuments = mergedDocuments.sort(
				(a, b) => (b.distance ?? Infinity) - (a.distance ?? Infinity)
			);
		}
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch {
			return str;
		}
	};

    // Fetch media (audio/video) with authentication and create blob URL
	const loadMediaBlob = async (mediaUrl: string) => {
		if (audioBlobUrls[mediaUrl]) {
			return audioBlobUrls[mediaUrl];
		}
		
		try {
			const token = localStorage.getItem('token');
			const response = await fetch(`${WEBUI_BASE_URL}${mediaUrl}`, {
				method: 'GET',
				headers: {
					'Authorization': `Bearer ${token}`
				},
				credentials: 'include'
			});
			
			if (!response.ok) {
				throw new Error(`Failed to load media: ${response.statusText}`);
			}
			
			const blob = await response.blob();
			const blobUrl = URL.createObjectURL(blob);
			audioBlobUrls[mediaUrl] = blobUrl;
			return blobUrl;
		} catch (error) {
			console.error('Error loading media:', error);
			return null;
		}
    };

	const getTextFragmentUrl = (doc: any): string | null => {
		const { metadata, source, document: content } = doc ?? {};
		const { file_id, page } = metadata ?? {};
		const sourceUrl = source?.url;

		const baseUrl = file_id
			? `${WEBUI_API_BASE_URL}/files/${file_id}/content${page !== undefined ? `#page=${page + 1}` : ''}`
			: sourceUrl?.includes('http')
				? sourceUrl
				: null;

		if (!baseUrl || !content) return baseUrl;

		// Extract first and last words for text fragment, filtering out URLs and emojis
		const words = content
			.trim()
			.replace(/\s+/g, ' ')
			.split(' ')
			.filter((w: string) => w.length > 0 && !/https?:\/\/|[\u{1F300}-\u{1F9FF}]/u.test(w));

		if (words.length === 0) return baseUrl;

		const clean = (w: string) => w.replace(/[^\w]/g, '');
		const first = clean(words[0]);
		const last = clean(words.at(-1));
		const fragment = words.length === 1 ? first : `${first},${last}`;

		return fragment ? `${baseUrl}#:~:text=${fragment}` : baseUrl;
	};
</script>

<Modal size="xl" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4.5 pt-3 pb-2">
			<div class=" text-lg font-medium self-center flex items-center">
				{#if citation?.source?.name}
					{@const document = mergedDocuments?.[0]}
					{#if document?.metadata?.file_id || document.source?.url?.includes('http')}
						<Tooltip
							className="w-fit"
							content={document.source?.url?.includes('http')
								? $i18n.t('Open link')
								: $i18n.t('Open file')}
							placement="top-start"
							tippyOptions={{ duration: [500, 0] }}
						>
							<a
								class="hover:text-gray-500 dark:hover:text-gray-100 underline grow line-clamp-1"
								href={document?.metadata?.file_id
									? `${WEBUI_API_BASE_URL}/files/${document?.metadata?.file_id}/content${document?.metadata?.page !== undefined ? `#page=${document.metadata.page + 1}` : ''}`
									: document.source?.url?.includes('http')
										? document.source.url
										: `#`}
								target="_blank"
							>
								{decodeString(citation?.source?.name)}
							</a>
						</Tooltip>
					{:else}
						{decodeString(citation?.source?.name)}
					{/if}
				{:else}
					{$i18n.t('Citation')}
				{/if}
			</div>

			<div class="flex items-center gap-2">
				<Tooltip content={copySuccess ? $i18n.t('Copied!') : $i18n.t('Copy to clipboard')}>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={copyToClipboard}
					>
						{#if copySuccess}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5 text-green-500">
								<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
							</svg>
						{/if}
					</button>
				</Tooltip>

				<Tooltip content={emailSuccess ? $i18n.t('Sent!') : emailError || $i18n.t('Email report to yourself')}>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
						on:click={sendViaGmail}
						disabled={emailSending}
					>
						{#if emailSending}
							<svg class="animate-spin size-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
						{:else if emailSuccess}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5 text-green-500">
								<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
							</svg>
						{:else if emailError}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5 text-red-500">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
							</svg>
						{/if}
					</button>
				</Tooltip>

				<button
					class="self-center p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					aria-label={$i18n.t('Close citation modal')}
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-5'} />
				</button>
			</div>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-5 md:space-x-4">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[36rem] scrollbar-thin gap-4"
			>
				{#each mergedDocuments as document, documentIdx}
					<div class="flex flex-col w-full gap-3 pb-4 border-b border-gray-200 dark:border-gray-700 last:border-b-0 last:pb-0">
						{#if document.metadata?.parameters}
							<div>
								<div class="text-sm font-medium dark:text-gray-300 mb-1">
									{$i18n.t('Parameters')}
								</div>

								<Textarea readonly value={JSON.stringify(document.metadata.parameters, null, 2)}
								></Textarea>
							</div>
						{/if}

						<div>
							<div
								class=" text-sm font-medium dark:text-gray-300 flex items-center gap-2 w-fit mb-1"
							>
								{#if document.source?.url?.includes('http')}
									{@const snippetUrl = getTextFragmentUrl(document)}
									{#if snippetUrl}
										<a
											href={snippetUrl}
											target="_blank"
											class="underline hover:text-gray-500 dark:hover:text-gray-100"
											>{$i18n.t('Content')}</a
										>
									{:else}
										{$i18n.t('Content')}
									{/if}
								{:else}
									{$i18n.t('Content')}
								{/if}

								{#if showRelevance && document.distance !== undefined}
									<Tooltip
										className="w-fit"
										content="Relevance score: Lower percentage = more relevant to your query"
										placement="top-start"
										tippyOptions={{ duration: [500, 0] }}
									>
										<div class="text-sm my-1 dark:text-gray-400 flex items-center gap-2 w-fit">
											{#if showPercentage}
												{@const percentage = calculatePercentage(document.distance)}

												{#if typeof percentage === 'number'}
													<span
														class={`px-2 py-0.5 rounded-md font-medium text-xs flex items-center gap-1.5 ${getRelevanceColor(percentage)}`}
													>
														<span>{getRelevanceLabel(percentage)}</span>
														<span class="opacity-75">({percentage.toFixed(1)}%)</span>
													</span>
												{/if}
											{:else if typeof document?.distance === 'number'}
												<span class="text-gray-500 dark:text-gray-500">
													({(document?.distance ?? 0).toFixed(4)})
												</span>
											{/if}
										</div>
									</Tooltip>
								{/if}

								{#if Number.isInteger(document?.metadata?.page)}
									<span class="text-sm text-gray-500 dark:text-gray-400">
										({$i18n.t('page')}
										{document.metadata.page + 1})
									</span>
								{/if}
							</div>

							{#if getVideoUrl(document)}
								{@const fileId = document.metadata?.file_id}
								{@const chapters = getChaptersForFile(fileId)}
								<!-- Enhanced video player with timeline highlighting (full video with seek) -->
								<div class="flex flex-col gap-3 p-4 bg-gray-50 dark:bg-gray-850 rounded-lg">
									<VideoPlayerWithTimeline
										src={`${WEBUI_BASE_URL}${getVideoUrl(document)}`}
										startTime={document.metadata?.timestamp_start || 0}
										endTime={document.metadata?.timestamp_end}
										totalDuration={document.metadata?.transcript_duration}
										{chapters}
									/>
									
									<!-- Chapter generation button (if no chapters) -->
									{#if fileId && chapters.length === 0 && !chaptersLoading[fileId]}
										<div class="flex items-center gap-2 mt-1">
											{#if chaptersGenerating[fileId]}
												<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
													<svg class="animate-spin size-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
														<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
														<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
													</svg>
													<span>Generating chapters...</span>
												</div>
											{:else}
												<Tooltip content="Use AI to identify chapters in this video">
													<button
														class="flex items-center gap-1.5 px-2 py-1 text-xs rounded bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-800/50 transition-colors"
														on:click={() => handleGenerateChapters(fileId)}
													>
														<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-3.5">
															<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
														</svg>
														Generate Chapters
													</button>
												</Tooltip>
											{/if}
											{#if chaptersError[fileId]}
												<span class="text-xs text-red-500">{chaptersError[fileId]}</span>
											{/if}
										</div>
									{/if}
								</div>
								<!-- Text content below video -->
								{#if isMarkdownContent(document.document)}
									<div class="{PROSE_CLASS} mt-2">
										<Markdown content={document.document} id={`citation-video-${documentIdx}`} />
									</div>
								{:else}
									<pre class="text-sm dark:text-gray-400 whitespace-pre-line mt-2">{document.document}</pre>
								{/if}
							{:else if document.metadata?.audio_segment_url}
								<!-- Audio-only segment player -->
								<div class="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-gray-850 rounded-lg">
									<div class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-4"
										>
											<!-- Audio icon -->
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
											/>
										</svg>
										{#if document.metadata?.timestamp_start !== undefined && document.metadata?.timestamp_end !== undefined}
											<span>
												{Math.floor(document.metadata.timestamp_start / 60)}:{String(Math.floor(document.metadata.timestamp_start % 60)).padStart(2, '0')}
												-
												{Math.floor(document.metadata.timestamp_end / 60)}:{String(Math.floor(document.metadata.timestamp_end % 60)).padStart(2, '0')}
											</span>
										{/if}
										{#if document.metadata?.duration !== undefined}
											<span class="text-gray-500 dark:text-gray-500">
												({Math.floor(document.metadata.duration)}s)
											</span>
										{/if}
									</div>
									
									{#await loadMediaBlob(document.metadata.audio_segment_url)}
										<div class="flex items-center justify-center py-4 text-gray-500">
											<span class="text-sm">Loading audio...</span>
										</div>
									{:then blobUrl}
										{#if blobUrl}
											<audio
												controls
												preload="metadata"
												class="w-full"
												src={blobUrl}
											>
												Your browser does not support audio playback.
											</audio>
										{:else}
											<div class="text-sm text-red-500">Failed to load audio</div>
										{/if}
									{:catch error}
										<div class="text-sm text-red-500">Error: {error.message}</div>
									{/await}
								</div>
								<!-- Text content below media -->
								{#if isMarkdownContent(document.document)}
									<div class="{PROSE_CLASS} mt-2">
										<Markdown content={document.document} id={`citation-media-${documentIdx}`} />
									</div>
								{:else}
									<pre class="text-sm dark:text-gray-400 whitespace-pre-line mt-2">{document.document}</pre>
								{/if}
							{:else if document.metadata?.html}
								<iframe
									class="w-full border-0 h-auto rounded-none"
									sandbox="allow-scripts allow-forms{($settings?.iframeSandboxAllowSameOrigin ??
									false)
										? ' allow-same-origin'
										: ''}"
									srcdoc={injectCsp(document.document, $config?.ui?.iframe_csp ?? '')}
									title={$i18n.t('Content')}
								></iframe>
							{:else if isMarkdownContent(document.document)}
								<div class={PROSE_CLASS}>
									<Markdown content={document.document} id={`citation-${documentIdx}`} />
								</div>
							{:else}
								{@const rawContent = document.document.trim().replace(/\n\n+/g, '\n\n')}
								{@const isTruncated =
									($settings?.renderMarkdownInPreviews ?? true) &&
									rawContent.length > CONTENT_PREVIEW_LIMIT &&
									!expandedDocs.has(documentIdx)}
								{#if $settings?.renderMarkdownInPreviews ?? true}
									<div
										class="text-sm prose dark:prose-invert markdown-prose-sm min-w-full max-w-full"
									>
										<Markdown
											content={isTruncated
												? rawContent.slice(0, CONTENT_PREVIEW_LIMIT)
												: rawContent}
											id="citation-{documentIdx}"
										/>
									</div>
									{#if isTruncated}
										<button
											class="mt-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
											on:click={() => {
												expandedDocs.add(documentIdx);
												expandedDocs = expandedDocs;
											}}
										>
											{$i18n.t('Show all ({{COUNT}} characters)', {
												COUNT: rawContent.length.toLocaleString()
											})}
										</button>
									{/if}
								{:else}
									<pre class="text-sm dark:text-gray-400 whitespace-pre-line">{rawContent}</pre>
								{/if}
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
</Modal>
