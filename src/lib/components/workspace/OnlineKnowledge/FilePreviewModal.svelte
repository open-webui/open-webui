<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Modal from '../../common/Modal.svelte';
	import XMark from '../../icons/XMark.svelte';
	import Document from '../../icons/Document.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let show = false;
	export let file: {
		id: string;
		folderId: string;
		name: string;
		size: number;
		type: string;
		content: string | null;
		createdAt: number;
	} | null = null;
	export let formatFileSize: (bytes: number) => string;

	// Get file type
	const getFileType = (mimeType: string): 'pdf' | 'txt' | 'csv' | 'image' | 'unknown' => {
		if (mimeType === 'application/pdf') return 'pdf';
		if (mimeType === 'text/plain') return 'txt';
		if (mimeType === 'text/csv') return 'csv';
		if (mimeType.startsWith('image/')) return 'image';
		return 'unknown';
	};

	// Get file type label
	const getFileTypeLabel = (mimeType: string): string => {
		const typeMap: Record<string, string> = {
			'application/pdf': 'PDF 문서',
			'text/plain': '텍스트 파일',
			'text/csv': 'CSV 스프레드시트',
			'image/png': 'PNG 이미지',
			'image/jpeg': 'JPEG 이미지',
			'image/jpg': 'JPG 이미지'
		};
		return typeMap[mimeType] || '파일';
	};

	$: fileType = file ? getFileType(file.type) : 'unknown';
</script>

<Modal bind:show size="lg">
	{#if file}
		<div class="flex flex-col max-h-[85vh]">
			<!-- Header -->
			<div class="flex justify-between items-start p-4 border-b border-gray-100 dark:border-gray-800 shrink-0">
				<div class="min-w-0 flex-1 pr-4">
					<h2 class="text-lg font-medium dark:text-white truncate">{file.name}</h2>
					<p class="text-sm text-gray-500 mt-0.5">
						{formatFileSize(file.size)} • {getFileTypeLabel(file.type)}
					</p>
				</div>
				<button
					class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition shrink-0"
					on:click={() => show = false}
				>
					<XMark className="size-5" />
				</button>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-auto p-4">
				{#if fileType === 'pdf'}
					<!-- PDF: Placeholder -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-8 text-center min-h-[300px] flex flex-col items-center justify-center">
						<div class="size-16 flex items-center justify-center bg-error-100 dark:bg-error-500/20 text-error-500 rounded-xl mb-4">
							<Document className="size-8" />
						</div>
						<p class="text-lg font-medium dark:text-white mb-1">{$i18n.t('PDF 미리보기')}</p>
						<p class="text-sm text-gray-500">{file.name}</p>
						<p class="text-xs text-gray-400 mt-2">{$i18n.t('실제 구현 시 PDF 뷰어로 표시됩니다.')}</p>
					</div>
				{:else if fileType === 'txt' || fileType === 'csv'}
					<!-- Text/CSV: Show content -->
					{#if file.content}
						<div class="bg-gray-50 dark:bg-gray-850 rounded-xl overflow-hidden">
							<div class="px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
								<span class="text-xs font-medium text-gray-500 uppercase">{fileType === 'csv' ? 'CSV' : 'TEXT'}</span>
							</div>
							<pre class="p-4 overflow-x-auto text-sm font-mono whitespace-pre-wrap dark:text-gray-300 max-h-[50vh]">{file.content}</pre>
						</div>
					{:else}
						<div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-8 text-center">
							<p class="text-gray-500">{$i18n.t('내용을 불러올 수 없습니다.')}</p>
						</div>
					{/if}
				{:else if fileType === 'image'}
					<!-- Image: Show image -->
					{#if file.content}
						<div class="flex justify-center">
							<img
								src={file.content}
								alt={file.name}
								class="max-w-full h-auto rounded-xl shadow-md"
								style="max-height: 60vh;"
							/>
						</div>
					{:else}
						<div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-8 text-center">
							<p class="text-gray-500">{$i18n.t('이미지를 불러올 수 없습니다.')}</p>
						</div>
					{/if}
				{:else}
					<!-- Unknown: Placeholder -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-8 text-center min-h-[200px] flex flex-col items-center justify-center">
						<div class="size-16 flex items-center justify-center bg-gray-200 dark:bg-gray-700 text-gray-500 rounded-xl mb-4">
							<Document className="size-8" />
						</div>
						<p class="text-gray-500">{$i18n.t('이 파일 형식은 미리보기를 지원하지 않습니다.')}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex justify-end gap-2 p-4 border-t border-gray-100 dark:border-gray-800 shrink-0">
				<button
					class="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition text-sm font-medium dark:text-white"
					on:click={() => show = false}
				>
					{$i18n.t('닫기')}
				</button>
			</div>
		</div>
	{/if}
</Modal>
