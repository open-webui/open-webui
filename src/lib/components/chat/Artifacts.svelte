<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import {
		artifactCode,
		chatId,
		config,
		settings,
		showArtifacts,
		showControls,
		artifactContents
	} from '$lib/stores';
	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import { exportArtifactToExcel } from '$lib/apis/utils';
	import { saveAs } from 'file-saver';
	import { injectCsp } from '$lib/utils/csp';

	import XMark from '../icons/XMark.svelte';
	import ArrowsPointingOut from '../icons/ArrowsPointingOut.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import ArrowLeft from '../icons/ArrowLeft.svelte';
	import Download from '../icons/Download.svelte';

	export let overlay = false;

	let contents: Array<{ type: string; content: string }> = [];
	let selectedContentIdx = 0;

	let copied = false;
	let iframeElement: HTMLIFrameElement;

	function navigateContent(direction: 'prev' | 'next') {
		selectedContentIdx =
			direction === 'prev'
				? Math.max(selectedContentIdx - 1, 0)
				: Math.min(selectedContentIdx + 1, contents.length - 1);
	}

	const iframeLoadHandler = () => {
		iframeElement.contentWindow.addEventListener(
			'click',
			function (e) {
				const target = e.target.closest('a');
				if (target && target.href) {
					e.preventDefault();
					const url = new URL(target.href, iframeElement.baseURI);
					if (url.origin === window.location.origin) {
						iframeElement.contentWindow.history.pushState(
							null,
							'',
							url.pathname + url.search + url.hash
						);
					} else {
						console.info('External navigation blocked:', url.href);
					}
				}
			},
			true
		);

		// Cancel drag when hovering over iframe
		iframeElement.contentWindow.addEventListener('mouseenter', function (e) {
			e.preventDefault();
			iframeElement.contentWindow.addEventListener('dragstart', (event) => {
				event.preventDefault();
			});
		});
	};

	const showFullScreen = () => {
		if (iframeElement.requestFullscreen) {
			iframeElement.requestFullscreen();
		} else if (iframeElement.webkitRequestFullscreen) {
			iframeElement.webkitRequestFullscreen();
		} else if (iframeElement.msRequestFullscreen) {
			iframeElement.msRequestFullscreen();
		}
	};

	const parseCsvToTable = (csvContent: string): { headers: string[]; rows: string[][] } | null => {
		try {
			const lines = csvContent.trim().split('\n');
			if (lines.length === 0) return null;

			// Parse CSV (simple implementation, handles basic cases)
			const parseRow = (line: string): string[] => {
				const result = [];
				let current = '';
				let inQuotes = false;

				for (let i = 0; i < line.length; i++) {
					const char = line[i];
					if (char === '"') {
						if (inQuotes && line[i + 1] === '"') {
							current += '"';
							i++; // Skip next quote
						} else {
							inQuotes = !inQuotes;
						}
					} else if (char === ',' && !inQuotes) {
						result.push(current.trim());
						current = '';
					} else {
						current += char;
					}
				}
				result.push(current.trim());
				return result;
			};

			const headers = parseRow(lines[0]);
			const rows = lines.slice(1).map(parseRow);

			return { headers, rows };
		} catch (e) {
			console.error('Error parsing CSV:', e);
			return null;
		}
	};

	const parseJsonToTable = (
		jsonContent: string
	): { headers: string[]; rows: string[][] } | null => {
		try {
			const data = JSON.parse(jsonContent);
			if (!Array.isArray(data) || data.length === 0) {
				return null;
			}

			const headers = Object.keys(data[0]);
			const rows = data.map((row) => headers.map((header) => String(row[header] ?? '')));

			return { headers, rows };
		} catch (e) {
			console.error('Error parsing JSON:', e);
			return null;
		}
	};

	const convertJsonToCsv = (jsonContent: string): string => {
		try {
			const data = JSON.parse(jsonContent);
			if (!Array.isArray(data) || data.length === 0) {
				return jsonContent; // Fallback to raw content
			}

			// Extract headers from first object
			const headers = Object.keys(data[0]);
			const csvRows = [];

			// Add header row
			csvRows.push(headers.join(','));

			// Add data rows
			for (const row of data) {
				const values = headers.map((header) => {
					const value = row[header];
					// Escape quotes and wrap in quotes if contains comma/quote/newline
					const stringValue = String(value ?? '');
					if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
						return `"${stringValue.replace(/"/g, '""')}"`;
					}
					return stringValue;
				});
				csvRows.push(values.join(','));
			}

			return csvRows.join('\n');
		} catch (e) {
			console.error('Error converting JSON to CSV:', e);
			return jsonContent; // Fallback to raw content
		}
	};

	const downloadArtifact = () => {
		const artifact = contents[selectedContentIdx];
		let blob: Blob;
		let filename: string;

		if (artifact.type === 'csv') {
			blob = new Blob([artifact.content], { type: 'text/csv' });
			filename = `data-${$chatId}-${selectedContentIdx}.csv`;
		} else if (artifact.type === 'json') {
			// Option 1: Download as JSON
			blob = new Blob([artifact.content], { type: 'application/json' });
			filename = `data-${$chatId}-${selectedContentIdx}.json`;
			
			// Option 2: Convert to CSV (uncomment to use)
			// const csvContent = convertJsonToCsv(artifact.content);
			// blob = new Blob([csvContent], { type: 'text/csv' });
			// filename = `data-${$chatId}-${selectedContentIdx}.csv`;
		} else if (artifact.type === 'svg') {
			blob = new Blob([artifact.content], { type: 'image/svg+xml' });
			filename = `artifact-${$chatId}-${selectedContentIdx}.svg`;
		} else {
			// Default: HTML/iframe
			blob = new Blob([artifact.content], { type: 'text/html' });
			filename = `artifact-${$chatId}-${selectedContentIdx}.html`;
		}

		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	};

	const downloadAsExcel = async () => {
		const artifact = contents[selectedContentIdx];
		
		if (!['csv', 'json'].includes(artifact.type)) {
			toast.error($i18n.t('Only CSV and JSON artifacts can be exported to Excel'));
			return;
		}

		try {
			const result = await exportArtifactToExcel(
				localStorage.token,
				artifact.type,
				artifact.content,
				`data-${$chatId}-${selectedContentIdx}.xlsx`
			);

			if (result?.blob) {
				saveAs(result.blob, result.filename);
				toast.success($i18n.t('Excel file downloaded successfully'));
			} else {
				toast.error($i18n.t('Failed to generate Excel file'));
			}
		} catch (error) {
			console.error('Error exporting to Excel:', error);
			toast.error($i18n.t('Error exporting to Excel'));
		}
	};

	onMount(() => {
		const unsubscribeArtifactCode = artifactCode.subscribe((value) => {
			if (contents) {
				const codeIdx = contents.findIndex((content) => content.content.includes(value));
				selectedContentIdx = codeIdx !== -1 ? codeIdx : 0;
			}
		});

		const unsubscribeArtifactContents = artifactContents.subscribe((value) => {
			const newContents = value ?? [];
			console.log('Artifact contents updated:', newContents);

			if (newContents.length === 0) {
				showControls.set(false);
				showArtifacts.set(false);
				selectedContentIdx = 0;
			} else if (newContents.length > contents.length) {
				selectedContentIdx = newContents.length - 1;
			}

			contents = newContents;
		});

		return () => {
			unsubscribeArtifactCode();
			unsubscribeArtifactContents();
		};
	});
</script>

<div
	class=" w-full h-full relative flex flex-col bg-white dark:bg-gray-850"
	id="artifacts-container"
>
	<div class="w-full h-full flex flex-col flex-1 relative">
		{#if contents.length > 0}
			<div
				class="pointer-events-auto z-20 flex justify-between items-center p-2.5 font-primar text-gray-900 dark:text-white"
			>
				<div class="flex-1 flex items-center justify-between pr-1">
					<div class="flex items-center space-x-2">
						<div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
							<button
								class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition disabled:cursor-not-allowed"
								on:click={() => navigateContent('prev')}
								disabled={contents.length <= 1}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
									stroke-width="2.5"
									class="size-3.5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M15.75 19.5 8.25 12l7.5-7.5"
									/>
								</svg>
							</button>

							<div class="text-xs self-center dark:text-gray-100 min-w-fit">
								{$i18n.t('Version {{selectedVersion}} of {{totalVersions}}', {
									selectedVersion: selectedContentIdx + 1,
									totalVersions: contents.length
								})}
							</div>

							<button
								class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition disabled:cursor-not-allowed"
								on:click={() => navigateContent('next')}
								disabled={contents.length <= 1}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
									stroke-width="2.5"
									class="size-3.5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="m8.25 4.5 7.5 7.5-7.5 7.5"
									/>
								</svg>
							</button>
						</div>
					</div>

					<div class="flex items-center gap-1.5">
						<button
							class="copy-code-button bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
							on:click={() => {
								copyToClipboard(contents[selectedContentIdx].content);
								copied = true;

								setTimeout(() => {
									copied = false;
								}, 2000);
							}}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
						>

					<Tooltip content={$i18n.t('Download')}>
						<button
							class=" bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md p-0.5"
							on:click={downloadArtifact}
						>
							<Download className="size-3.5" />
						</button>
					</Tooltip>

					{#if ['csv', 'json'].includes(contents[selectedContentIdx].type)}
						<Tooltip content={$i18n.t('Export to Excel')}>
							<button
								class=" bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5 font-medium"
								on:click={downloadAsExcel}
							>
								📊 Excel
							</button>
						</Tooltip>
					{/if}

					{#if contents[selectedContentIdx].type === 'iframe'}
							<Tooltip content={$i18n.t('Open in full screen')}>
								<button
									class=" bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md p-0.5"
									on:click={showFullScreen}
								>
									<ArrowsPointingOut className="size-3.5" />
								</button>
							</Tooltip>
						{/if}
					</div>
				</div>

				<button
					class="self-center pointer-events-auto p-1 rounded-full bg-white dark:bg-gray-850"
					on:click={() => {
						dispatch('close');
						showControls.set(false);
						showArtifacts.set(false);
					}}
				>
					<XMark className="size-3.5 text-gray-900 dark:text-white" />
				</button>
			</div>
		{/if}

		{#if overlay}
			<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
		{/if}

		<div class="flex-1 w-full h-full">
			<div class=" h-full flex flex-col">
				{#if contents.length > 0}
					<div class="max-w-full w-full h-full">
						{#if contents[selectedContentIdx].type === 'iframe'}
							<iframe
								bind:this={iframeElement}
								title="Content"
								srcdoc={injectCsp(
									contents[selectedContentIdx].content,
									$config?.ui?.iframe_csp ?? ''
								)}
								class="w-full border-0 h-full rounded-none"
								sandbox="allow-scripts allow-downloads{($settings?.iframeSandboxAllowForms ?? false)
									? ' allow-forms'
									: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false)
									? ' allow-same-origin'
									: ''}"
								on:load={iframeLoadHandler}
							></iframe>
						{:else if contents[selectedContentIdx].type === 'svg'}
							<SvgPanZoom
								className=" w-full h-full max-h-full overflow-hidden"
								svg={contents[selectedContentIdx].content}
							/>
						{:else if contents[selectedContentIdx].type === 'csv'}
							{@const tableData = parseCsvToTable(contents[selectedContentIdx].content)}
							{#if tableData}
								<div class="overflow-auto h-full p-4 bg-white dark:bg-gray-850">
									<table
										class="min-w-full border-collapse border border-gray-300 dark:border-gray-700 text-sm"
									>
										<thead>
											<tr class="bg-gray-100 dark:bg-gray-800">
												{#each tableData.headers as header}
													<th
														class="border border-gray-300 dark:border-gray-700 px-4 py-2 text-left font-semibold"
													>
														{header}
													</th>
												{/each}
											</tr>
										</thead>
										<tbody>
											{#each tableData.rows as row}
												<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50">
													{#each row as cell}
														<td class="border border-gray-300 dark:border-gray-700 px-4 py-2">
															{cell}
														</td>
													{/each}
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{:else}
								<div class="p-4 text-gray-500 dark:text-gray-400">
									<p>{$i18n.t('Unable to parse CSV data')}</p>
									<pre class="mt-2 text-xs overflow-auto">{contents[selectedContentIdx].content}</pre>
								</div>
							{/if}
						{:else if contents[selectedContentIdx].type === 'json'}
							{@const tableData = parseJsonToTable(contents[selectedContentIdx].content)}
							{#if tableData}
								<div class="overflow-auto h-full p-4 bg-white dark:bg-gray-850">
									<table
										class="min-w-full border-collapse border border-gray-300 dark:border-gray-700 text-sm"
									>
										<thead>
											<tr class="bg-gray-100 dark:bg-gray-800">
												{#each tableData.headers as header}
													<th
														class="border border-gray-300 dark:border-gray-700 px-4 py-2 text-left font-semibold"
													>
														{header}
													</th>
												{/each}
											</tr>
										</thead>
										<tbody>
											{#each tableData.rows as row}
												<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50">
													{#each row as cell}
														<td class="border border-gray-300 dark:border-gray-700 px-4 py-2">
															{cell}
														</td>
													{/each}
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{:else}
								<div class="p-4 text-gray-500 dark:text-gray-400">
									<p>{$i18n.t('Unable to parse JSON data')}</p>
									<pre class="mt-2 text-xs overflow-auto">{contents[selectedContentIdx].content}</pre>
								</div>
							{/if}
						{/if}
					</div>
				{:else}
					<div class="m-auto font-medium text-xs text-gray-900 dark:text-white">
						{$i18n.t('No HTML, CSS, or JavaScript content found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
