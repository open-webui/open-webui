<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';

	import { config, user } from '$lib/stores';
	import { imageGenerations, imageEdits, getGeneratedImages } from '$lib/apis/images';
	import { deleteFileById } from '$lib/apis/files';
	import { chatExists } from '$lib/apis/chats';
	import {
		resolveFileUrl,
		readFileAsDataUrl,
		copyImageToClipboard,
		downloadImage,
		getFileModel,
		getFileSize
	} from '$lib/utils/image';
	import type { GalleryImageFile } from '$lib/utils/image';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ImagePreview from '$lib/components/common/ImagePreview.svelte';

	const i18n = getContext('i18n');


	let loaded = false;
	let loading = false;

	let prompt = '';
	let sourceImages: string[] = [];

	let previewSrc = '';
	let showPreview = false;

	const openPreview = (url: string) => {
		previewSrc = resolveFileUrl(url);
		showPreview = true;
	};

	let galleryImages: GalleryImageFile[] = [];
	let galleryLoading = false;
	let galleryHasMore = true;
	let galleryOffset = 0;
	const GALLERY_PAGE_SIZE = 20;
	let validChatIds: Set<string> = new Set();

	let showDeleteConfirm = false;
	let deleteTargetId: string | null = null;

	let promptTextareaElement: HTMLTextAreaElement;
	let fileInputElement: HTMLInputElement;


	const resizePromptTextarea = () => {
		if (promptTextareaElement) {
			promptTextareaElement.style.height = '';
			promptTextareaElement.style.height = Math.min(promptTextareaElement.scrollHeight, 150) + 'px';
		}
	};

	const handleFileUpload = async (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (input.files) {
			const urls = await Promise.all(
				Array.from(input.files).map((file) => readFileAsDataUrl(file))
			);
			sourceImages = [...sourceImages, ...urls];
		}
	};

	const handleDrop = async (event: DragEvent) => {
		event.preventDefault();
		const files = event.dataTransfer?.files;
		if (files) {
			const imageFiles = Array.from(files).filter((f) => f.type.startsWith('image/'));
			const urls = await Promise.all(imageFiles.map((file) => readFileAsDataUrl(file)));
			sourceImages = [...sourceImages, ...urls];
		}
	};

	const removeImage = (index: number) => {
		sourceImages = sourceImages.filter((_, i) => i !== index);
	};

	const submitHandler = async () => {
		if (!prompt.trim()) {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}

		loading = true;
		try {
			let result;
			if (sourceImages.length > 0) {
				result = await imageEdits(
					localStorage.token,
					sourceImages.length === 1 ? sourceImages[0] : sourceImages,
					prompt
				);
			} else {
				result = await imageGenerations(localStorage.token, prompt);
			}

			if (result) {
				await refreshGallery();
			}
		} catch (error) {
			console.error('Image generation/edit error:', error);
			const errorMessage = typeof error === 'string' ? error : `${error}`;
			toast.error(errorMessage);
		} finally {
			loading = false;
		}
	};

	const chatLinkFor = (file: GalleryImageFile) => {
		const data = file.meta?.data as Record<string, unknown> | undefined;
		const chatId = data?.chat_id as string;
		const messageId = data?.message_id as string;

		return messageId
			? `/c/${chatId}?message=${encodeURIComponent(messageId)}&image=${encodeURIComponent(file.id)}`
			: `/c/${chatId}`;
	};

	const syncChatLinks = async (files: GalleryImageFile[]) => {
		const chatIds = new Set<string>();
		for (const f of files) {
			const chatId = (f.meta?.data as Record<string, unknown>)?.chat_id as string;
			if (chatId && !validChatIds.has(chatId)) {
				chatIds.add(chatId);
			}
		}
		if (chatIds.size === 0) return;

		await Promise.all(
			[...chatIds].map(async (id) => {
				if (await chatExists(localStorage.token, id)) {
					validChatIds.add(id);
				} else {
					validChatIds.delete(id);
				}
			})
		);
		validChatIds = validChatIds;
	};

	const loadGalleryPage = async () => {
		galleryLoading = true;
		try {
			const files = await getGeneratedImages(localStorage.token, galleryOffset, GALLERY_PAGE_SIZE);
			if (files && files.length > 0) {
				galleryOffset += files.length;
				const existingIds = new Set(galleryImages.map((f) => f.id));
				galleryImages = [
					...galleryImages,
					...files.filter((f: GalleryImageFile) => !existingIds.has(f.id))
				];
				galleryHasMore = files.length === GALLERY_PAGE_SIZE;

				await syncChatLinks(files);
			} else {
				galleryHasMore = false;
			}
		} catch (error) {
			galleryHasMore = false;
			toast.error(`${error}`);
		}
		galleryLoading = false;
	};

	const refreshGallery = async () => {
		if (galleryLoading || !loaded) return;

		try {
			const latestFiles = await getGeneratedImages(localStorage.token, 0, GALLERY_PAGE_SIZE);
			if (!latestFiles || latestFiles.length === 0) return;

			const existingIds = new Set(galleryImages.map((f) => f.id));
			const newFiles = latestFiles.filter((f: GalleryImageFile) => !existingIds.has(f.id));

			if (newFiles.length > 0) {
				galleryImages = [...newFiles, ...galleryImages];
				galleryOffset += newFiles.length;
			}

			await syncChatLinks(galleryImages);
		} catch {
		}
	};

	const handleVisibilityChange = () => {
		if (document.visibilityState === 'visible') {
			refreshGallery();
		}
	};

	const copyGalleryImage = async (url: string) => {
		try {
			await copyImageToClipboard(url, localStorage.token);
			toast.success($i18n.t('Image copied to clipboard'));
		} catch (error) {
			console.error('Failed to copy image:', error);
			toast.error($i18n.t('Failed to copy image'));
		}
	};

	const downloadGalleryImage = async (url: string, fileId: string) => {
		try {
			await downloadImage(url, `generated-image-${fileId}.png`, localStorage.token);
		} catch (error) {
			console.error('Failed to download image:', error);
			toast.error($i18n.t('Failed to download image'));
		}
	};

	const deleteGalleryImage = async (fileId: string) => {
		try {
			await deleteFileById(localStorage.token, fileId);
			galleryImages = galleryImages.filter((f) => f.id !== fileId);
			galleryOffset = Math.max(0, galleryOffset - 1);
			toast.success($i18n.t('Image deleted'));

			if (galleryImages.length === 0 && galleryHasMore) {
				galleryOffset = 0;
				await loadGalleryPage();
			}
		} catch {
			toast.error($i18n.t('Failed to delete image'));
		}
		deleteTargetId = null;
	};

	onMount(async () => {
		await loadGalleryPage();

		loaded = true;
		await tick();
		promptTextareaElement?.focus();

		document.addEventListener('visibilitychange', handleVisibilityChange);
	});

	onDestroy(() => {
		document.removeEventListener('visibilitychange', handleVisibilityChange);
	});
</script>


<div class="flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class="flex flex-col h-full px-2.5">
			{#if !$config?.features?.enable_image_generation}
				<div class="h-full flex flex-col items-center justify-center gap-3">
					<div class="p-4 rounded-full bg-gray-50 dark:bg-gray-850">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="size-8 text-gray-400 dark:text-gray-600"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
							<circle cx="9" cy="9" r="2" />
							<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
							<line x1="2" y1="2" x2="22" y2="22" />
						</svg>
					</div>
					<div class="text-center">
						<p class="text-sm font-medium text-gray-600 dark:text-gray-400">
							{$i18n.t('Image generation is not enabled')}
						</p>
						<p class="text-xs text-gray-400 dark:text-gray-600 mt-1">
							{$i18n.t('Contact your administrator to enable image generation')}
						</p>
					</div>
				</div>
			{:else}
				<div
					class="pt-0.5 pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
					id="images-container"
				>
					<div class="h-full w-full flex flex-col">
						<div class="flex-1 p-1">
							{#if galleryImages.length > 0}
								<div class="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
									{#each galleryImages as file (file.id)}
										{@const fileUrl = `/api/v1/files/${file.id}/content`}
										{@const filePrompt = file.meta?.data?.prompt}
										{@const fileSize = getFileSize(file.meta?.data)}
										{@const fileModel = getFileModel(file.meta?.data)}
										<div
											class="relative group cursor-pointer"
											on:click={() => openPreview(fileUrl)}
											on:keydown={(e) => {
												if (e.key === 'Enter' || e.key === ' ') {
													e.preventDefault();
													openPreview(fileUrl);
												}
											}}
											role="button"
											tabindex="0"
										>
											<img
												src={resolveFileUrl(fileUrl)}
												alt=""
												class="w-full aspect-square object-cover rounded-xl border border-gray-100/30 dark:border-gray-850/30 transition"
												loading="lazy"
											/>

											{#if fileModel || fileSize}
												<div
													class="absolute bottom-1.5 left-1.5 right-1.5 flex items-center gap-1 pointer-events-none"
												>
													{#if fileModel}
														<span
															class="min-w-0 truncate text-[10px] text-white/90 bg-black/50 backdrop-blur-sm rounded px-1.5 py-0.5 font-medium"
															title={fileModel}
														>
															{fileModel}
														</span>
													{/if}
													{#if fileSize}
														<span
															class="shrink-0 whitespace-nowrap text-[10px] text-white/90 bg-black/50 backdrop-blur-sm rounded px-1.5 py-0.5 font-medium"
														>
															{fileSize}
														</span>
													{/if}
												</div>
											{/if}

											{#if filePrompt}
												<div
													class="absolute top-0 left-0 right-0 p-2 bg-gradient-to-b from-black/60 to-transparent rounded-t-xl opacity-0 group-hover:opacity-100 transition-opacity"
												>
													<p
														class="text-[11px] text-white/90 line-clamp-2 leading-tight"
														title={filePrompt}
													>
														{filePrompt}
													</p>
												</div>
											{/if}

											<div
												class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity rounded-xl flex items-end justify-center pb-3"
											>
												<div
													class="flex items-center gap-1 bg-black/60 backdrop-blur-sm rounded-lg px-1.5 py-1"
												>
													{#if file.meta?.data?.chat_id && validChatIds.has(file.meta.data.chat_id)}
														<Tooltip content={$i18n.t('Open in Chat')} placement="top">
															<button
																class="p-1.5 hover:bg-white/20 rounded-md transition-colors"
																type="button"
																aria-label={$i18n.t('Open in Chat')}
																on:click|stopPropagation={() => goto(chatLinkFor(file))}
															>
																<ChatBubbleOval className="size-4 text-white" strokeWidth="2" />
															</button>
														</Tooltip>
													{/if}

													<Tooltip content={$i18n.t('Copy')} placement="top">
														<button
															class="p-1.5 hover:bg-white/20 rounded-md transition-colors"
															type="button"
															aria-label={$i18n.t('Copy')}
															on:click|stopPropagation={() => copyGalleryImage(fileUrl)}
														>
															<DocumentDuplicate className="size-4 text-white" strokeWidth="2" />
														</button>
													</Tooltip>

													<Tooltip content={$i18n.t('Download')} placement="top">
														<button
															class="p-1.5 hover:bg-white/20 rounded-md transition-colors"
															type="button"
															aria-label={$i18n.t('Download')}
															on:click|stopPropagation={() =>
																downloadGalleryImage(fileUrl, file.id)}
														>
															<Download className="size-4 text-white" strokeWidth="2" />
														</button>
													</Tooltip>

													<Tooltip content={$i18n.t('Delete')} placement="top">
														<button
															class="p-1.5 hover:bg-red-500/30 rounded-md transition-colors"
															type="button"
															aria-label={$i18n.t('Delete')}
															on:click|stopPropagation={() => {
																deleteTargetId = file.id;
																showDeleteConfirm = true;
															}}
														>
															<GarbageBin className="size-4 text-white" strokeWidth="2" />
														</button>
													</Tooltip>
												</div>
											</div>
										</div>
									{/each}
								</div>

								{#if galleryHasMore}
									<div class="flex justify-center mt-4">
										<button
											class="px-4 py-2 text-sm text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition-colors flex items-center gap-2"
											type="button"
											on:click={loadGalleryPage}
											disabled={galleryLoading}
										>
											{#if galleryLoading}
												<Spinner className="size-4" />
											{/if}
											{$i18n.t('Load more')}
										</button>
									</div>
								{/if}
							{:else if galleryLoading}
								<div class="flex justify-center py-8">
									<Spinner className="size-6" />
								</div>
							{:else}
								<div class="h-full flex flex-col items-center justify-center gap-4 select-none">
									<div class="p-4 rounded-2xl bg-gray-50 dark:bg-gray-850">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="size-10 text-gray-300 dark:text-gray-700"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
											<circle cx="9" cy="9" r="2" />
											<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
										</svg>
									</div>
									<div class="text-center">
										<p class="text-sm font-medium text-gray-500 dark:text-gray-500">
											{$i18n.t('Create something amazing')}
										</p>
										<p class="text-xs text-gray-400 dark:text-gray-600 mt-1">
											{$i18n.t('Describe an image and bring your vision to life')}
										</p>
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<div class="pb-3">
					<div
						class="border border-gray-100/30 dark:border-gray-850/30 w-full rounded-xl overflow-hidden"
					>
						<div class="px-3 py-2.5">
							{#if sourceImages.length > 0}
								<div class="flex flex-wrap gap-2 mb-2">
									{#each sourceImages as image, index}
										<div class="relative group">
											<div class="relative flex items-center">
												<img src={image} alt="" class="size-10 rounded-xl object-cover" />
											</div>
											<div class="absolute -top-1 -right-1">
												<button
													class="bg-white text-black border border-white rounded-full hover-reveal transition"
													type="button"
													aria-label={$i18n.t('Remove image')}
													on:click={() => removeImage(index)}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														aria-hidden="true"
														class="size-4"
													>
														<path
															d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
														/>
													</svg>
												</button>
											</div>
										</div>
									{/each}
								</div>
							{/if}

							<div class="py-0.5">
								<textarea
									bind:this={promptTextareaElement}
									bind:value={prompt}
									class="w-full h-full bg-transparent resize-none outline-hidden text-sm"
									placeholder={sourceImages.length > 0
										? $i18n.t('Describe the edit...')
										: $i18n.t('Describe the image...')}
									on:input={resizePromptTextarea}
									on:focus={resizePromptTextarea}
									on:paste={async (e) => {
										const items = e.clipboardData?.items;
										if (!items) return;
										for (const item of items) {
											if (item.type.startsWith('image/')) {
												e.preventDefault();
												const file = item.getAsFile();
												if (!file) continue;
												const dataUrl = await readFileAsDataUrl(file);
												sourceImages = [...sourceImages, dataUrl];
											}
										}
									}}
									on:keydown={(e) => {
										if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !loading) {
											e.preventDefault();
											submitHandler();
										}
									}}
									rows="2"
								/>
							</div>

							<div class="flex justify-between items-center gap-2 mt-2">
								<div class="flex items-center gap-2 shrink-0">
									<input
										type="file"
										accept="image/*"
										multiple
										class="hidden"
										bind:this={fileInputElement}
										on:change={handleFileUpload}
									/>
									<button
										type="button"
										class="px-3.5 py-1.5 text-sm font-normal bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg"
										on:click={() => fileInputElement?.click()}
										on:dragover|preventDefault
										on:drop={handleDrop}
									>
										{$i18n.t('Add Image')}
									</button>
								</div>

								<div class="flex gap-2 shrink-0">
									{#if !loading}
										<button
											disabled={prompt.trim() === ''}
											class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
											on:click={submitHandler}
										>
											{$i18n.t('Generate')}
										</button>
									{:else}
										<button
											class="px-3.5 py-1.5 text-sm font-normal bg-gray-300 text-black transition rounded-lg flex items-center gap-2"
											disabled
										>
											<Spinner className="size-4" />
											{$i18n.t('Generating...')}
										</button>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>

<ImagePreview bind:show={showPreview} src={previewSrc} alt="" />

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Image')}
	on:confirm={() => {
		if (deleteTargetId) {
			deleteGalleryImage(deleteTargetId);
		}
	}}
>
	<div class="text-sm text-gray-500">
		{$i18n.t('Are you sure you want to delete this image? This action cannot be undone.')}
	</div>
</ConfirmDialog>
