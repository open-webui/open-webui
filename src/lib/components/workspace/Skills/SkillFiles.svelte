<script lang="ts">
	import { onDestroy, getContext, tick, type Snippet } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { createFocusTrap } from 'focus-trap';
	import { mobile } from '$lib/stores';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import ResizableSidePanel from '$lib/components/common/ResizableSidePanel.svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { downloadSkillBlob as saveAs } from '$lib/apis/skills';
	import FileTypeIcon from '$lib/components/chat/FileNav/FileTypeIcon.svelte';
	import FileEntryRow from '$lib/components/chat/FileNav/FileEntryRow.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import FileCodeEditor from '$lib/components/chat/FileNav/FileCodeEditor.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import {
		getSkillFiles,
		getSkillFile,
		skillError,
		type SkillFile,
		type SkillFileSummary,
		type SkillFileOperation
	} from '$lib/apis/skills';
	import type { FileEntry } from '$lib/apis/terminal';

	export let version: Snippet;
	export let exports: Snippet;
	export let skillId = '';
	export let versionId: string | null = null;
	export let initialContent = '';
	export let initialFiles: SkillFile[] | null = null;
	export let readOnly = false;
	export let canExport = false;
	export let dirty = false;
	export let reloadKey = 0;
	export let initialPath = 'SKILL.md';
	export let onSave: () => Promise<void> = async () => {};
	export let onContentChange: (path: string, content: string) => void = () => {};
	const i18n = getContext<any>('i18n');
	type Draft = SkillFileSummary & {
		sourcePath?: string;
		content?: string;
		upload?: File;
		changed?: boolean;
	};
	let files: Draft[] = [];

	let emptyFolders: string[] = [];
	let currentPath = '';
	let expandedFolders = new Set<string>();
	let selected = 'SKILL.md';
	let showFileDrawer = false;
	let sidebarWidth = 256;
	let codeEditor: FileCodeEditor | undefined;
	let value = '';
	let loadedValue = '';
	let loadedPath = '';
	let objectUrl = '';
	let previewHtml = '';
	let preview = false;
	let resourceUrls: string[] = [];
	let loading = false;
	let loadError = '';
	let loadKey = '';
	let requestId = 0;
	let folderInput: HTMLInputElement;
	let uploadInput: HTMLInputElement;
	let selectedPaths = new Set<string>();
	let creating: 'file' | 'directory' | null = null;
	let newName = '';
	let newNameInput: HTMLInputElement;
	let dialog = { show: false, title: '', input: false, value: '', action: (_: string) => {} };
	const dragType = `application/x-skill-file-${crypto.randomUUID()}`;

	const ask = (title: string, input: boolean, action: (value: string) => void, value = '') => {
		dialog = { show: true, title, input, value, action };
	};
	const validPath = (path: string) =>
		!!path && !/[\\\x00:]/.test(path) && path.split('/').every((p) => p && p !== '.' && p !== '..');
	const validatePaths = (paths: string[]) => {
		if (
			new Set(paths).size !== paths.length ||
			paths.some(
				(p) => !validPath(p) || paths.some((other) => other !== p && p.startsWith(other + '/'))
			)
		)
			throw new Error('Invalid or conflicting file path');
	};
	const cancelCreate = () => {
		creating = null;
		newName = '';
	};
	const startCreate = async (type: 'file' | 'directory') => {
		if (readOnly) return;
		creating = type;
		newName = '';
		await tick();
		newNameInput?.focus();
	};
	const submitCreate = () => {
		if (!creating) return;
		if (readOnly || !newName.trim()) {
			cancelCreate();
			return;
		}
		const path = currentPath + newName.trim();
		try {
			validatePaths([...files.map((file) => file.path), path]);
			if (emptyFolders.some((folder) => folder === path || folder.startsWith(path + '/')))
				throw new Error('A file or folder already exists at this path');
			const type = creating;
			cancelCreate();
			expandParents(path);
			if (type === 'directory') emptyFolders = [...emptyFolders, path];
			else {
				files = [...files, { path, content: '', size: 0, changed: true }];
				dirty = true;
				open(path);
			}
		} catch (error) {
			toast.error(skillError(error));
		}
	};
	const clearUrls = () => {
		if (objectUrl) URL.revokeObjectURL(objectUrl);
		resourceUrls.forEach((url) => URL.revokeObjectURL(url));
		objectUrl = '';
		resourceUrls = [];
		previewHtml = '';
	};
	const flush = () => {
		if (loadedPath && codeEditor) value = codeEditor.getValue();
		const file = files.find((f) => f.path === loadedPath);
		if (file && !readOnly && value !== loadedValue) {
			onContentChange(loadedPath, value);
			file.content = value;
			file.changed = true;
			file.size = new TextEncoder().encode(value).length;
			files = [...files];
			loadedValue = value;
			dirty = true;
		}
	};
	const fileDrawer = (node: HTMLElement) => {
		const trap = createFocusTrap(node, { escapeDeactivates: false });
		trap.activate();
		return {
			destroy: () => {
				flush();
				trap.deactivate();
			}
		};
	};
	$: if (!$mobile) showFileDrawer = false;
	$: if (loadedPath && value !== loadedValue && !readOnly) {
		dirty = true;
		onContentChange(loadedPath, value);
	}
	const blobFor = async (file: Draft) => {
		if (file.content !== undefined)
			return new Blob([
				file.encoding === 'base64'
					? Uint8Array.from(atob(file.content), (c) => c.charCodeAt(0))
					: file.content
			]);
		if (file.upload) return file.upload;
		return getSkillFile(localStorage.token, skillId, versionId!, file.sourcePath || file.path);
	};
	const resolveRelative = (href: string, base: string) => {
		if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('/') || href.startsWith('#'))
			return null;
		const parts = base.split('/').slice(0, -1);
		let decoded: string;
		try {
			decoded = decodeURIComponent(href.split(/[?#]/)[0]);
		} catch {
			return null;
		}
		for (const part of decoded.split('/')) {
			if (part === '..') {
				if (!parts.length) return null;
				parts.pop();
			} else if (part && part !== '.') parts.push(part);
		}
		return parts.join('/');
	};
	const renderPreview = async () => {
		flush();
		const request = requestId;
		const document = new DOMParser().parseFromString(
			DOMPurify.sanitize(await marked.parse(value)),
			'text/html'
		);
		for (const image of Array.from(document.querySelectorAll('img'))) {
			const path = resolveRelative(image.getAttribute('src') || '', selected);
			image.removeAttribute('src');
			const file = files.find((f) => f.path === path);
			if (file && /\.(png|jpe?g|gif|webp|avif)$/i.test(file.path)) {
				const url = URL.createObjectURL(await blobFor(file));
				if (request !== requestId) {
					URL.revokeObjectURL(url);
					return;
				}
				resourceUrls.push(url);
				image.src = url;
			}
		}
		for (const link of Array.from(document.querySelectorAll('a'))) {
			const href = link.getAttribute('href') || '';
			const path = resolveRelative(href, selected);
			if (path) {
				link.dataset.skillPath = path;
				link.href = '#';
			} else if (/^https?:\/\//i.test(href)) {
				link.target = '_blank';
				link.rel = 'noopener noreferrer';
			} else link.removeAttribute('href');
		}
		if (request === requestId) previewHtml = document.body.innerHTML;
	};
	const expandParents = (path: string) => {
		const parts = path.split('/');
		for (let index = 1; index < parts.length; index++)
			expandedFolders.add(parts.slice(0, index).join('/'));
		expandedFolders = new Set(expandedFolders);
	};
	const open = async (path: string, reveal = true) => {
		flush();
		clearUrls();
		preview = false;
		selected = path;
		loadedPath = '';
		value = '';
		loadedValue = '';
		loadError = '';
		const file = files.find((f) => f.path === path);
		if (!file) return;
		expandParents(path);
		currentPath = path.includes('/') ? path.slice(0, path.lastIndexOf('/') + 1) : '';
		if (reveal && $mobile) showFileDrawer = true;
		const request = ++requestId;
		loading = true;
		try {
			const blob = await blobFor(file);
			if (request !== requestId) return;
			if (file.encoding === 'base64') objectUrl = URL.createObjectURL(blob);
			else {
				const text = await blob.text();
				if (request !== requestId) return;
				value = text;
				loadedValue = text;
				loadedPath = path;
			}
		} catch (error) {
			loadError = skillError(error);
		} finally {
			if (request === requestId) loading = false;
		}
	};
	const load = async () => {
		showFileDrawer = false;
		cancelCreate();
		++requestId;
		clearUrls();
		loadedPath = '';
		value = '';
		loadedValue = '';
		files = [];
		emptyFolders = [];
		dirty = false;
		loadError = '';
		loading = true;
		const key = loadKey;
		try {
			if (versionId) {
				const result = await getSkillFiles(localStorage.token, skillId, versionId);
				if (key !== loadKey) return;
				files = result.files.map((file: SkillFileSummary) => ({ ...file, sourcePath: file.path }));
			} else
				files = (initialFiles || [{ path: 'SKILL.md', content: initialContent }]).map((file) => ({
					...file,
					size: 0,
					changed: true
				}));
			currentPath = '';
			expandedFolders = new Set();
			selectedPaths = new Set();
			await open(files.some((f) => f.path === initialPath) ? initialPath : 'SKILL.md', false);
		} catch (error) {
			loadError = skillError(error);
			loading = false;
		}
	};
	$: if (`${versionId ? skillId : 'new'}:${versionId}:${reloadKey}` !== loadKey) {
		loadKey = `${versionId ? skillId : 'new'}:${versionId}:${reloadKey}`;
		load();
	}
	const toggleFolder = (path: string) => {
		cancelCreate();
		path = path.replace(/\/$/, '');
		if (expandedFolders.has(path)) {
			expandedFolders.delete(path);
			currentPath = path.includes('/') ? path.slice(0, path.lastIndexOf('/') + 1) : '';
		} else {
			expandedFolders.add(path);
			currentPath = path + '/';
		}
		expandedFolders = new Set(expandedFolders);
	};
	$: rows = (() => {
		const directories = new Map<string, Map<string, FileEntry>>();
		for (const file of [...files, ...emptyFolders.map((path) => ({ path: path + '/', size: 0 }))]) {
			const parts = file.path.split('/');
			parts.forEach((name, index) => {
				if (!name) return;
				const parent = parts.slice(0, index).join('/');
				if (!directories.has(parent)) directories.set(parent, new Map());
				directories.get(parent)!.set(name, {
					name,
					type: index < parts.length - 1 ? 'directory' : 'file',
					size: file.size,
					modified: 0,
					writable: !readOnly
				});
			});
		}
		const result: { entry: FileEntry; path: string; depth: number }[] = [];
		const append = (parent: string, depth: number) => {
			const entries = [...(directories.get(parent)?.values() || [])].sort((a, b) =>
				a.type !== b.type ? (a.type === 'directory' ? -1 : 1) : a.name.localeCompare(b.name)
			);
			for (const entry of entries) {
				const path = parent ? `${parent}/${entry.name}` : entry.name;
				result.push({ entry, path, depth });
				if (entry.type === 'directory' && expandedFolders.has(path)) append(path, depth + 1);
			}
		};
		append('', 0);
		return result;
	})();

	const rename = (path: string, destination: string) => {
		if (readOnly || path === 'SKILL.md') return;
		flush();
		try {
			if (!validPath(destination) || destination.startsWith(path + '/'))
				throw new Error('Invalid destination');
			const moved = files.map((file) =>
				file.path === path || file.path.startsWith(path + '/')
					? { ...file, path: destination + file.path.slice(path.length) }
					: file
			);
			validatePaths(moved.map((f) => f.path));
			files = moved;
			expandedFolders = new Set(
				[...expandedFolders].map((folder) =>
					folder === path || folder.startsWith(path + '/')
						? destination + folder.slice(path.length)
						: folder
				)
			);
			if (currentPath.startsWith(path + '/'))
				currentPath = destination + currentPath.slice(path.length);
			emptyFolders = emptyFolders.map((p) =>
				p === path || p.startsWith(path + '/') ? destination + p.slice(path.length) : p
			);
			if (selected === path || selected.startsWith(path + '/')) {
				selected = destination + selected.slice(path.length);
				loadedPath = selected;
			}
			dirty = true;
		} catch (error) {
			toast.error(skillError(error));
		}
	};
	const remove = (path: string) => {
		if (readOnly || path === 'SKILL.md') return;
		flush();
		files = files.filter((f) => f.path !== path && !f.path.startsWith(path + '/'));
		emptyFolders = emptyFolders.filter((p) => p !== path && !p.startsWith(path + '/'));
		expandedFolders = new Set(
			[...expandedFolders].filter((p) => p !== path && !p.startsWith(path + '/'))
		);
		if (currentPath.startsWith(path + '/')) currentPath = '';
		dirty = true;
		if (!files.some((f) => f.path === selected)) open('SKILL.md');
	};
	const upload = async (uploads: File[]) => {
		if (readOnly) return;
		flush();
		try {
			const drafts: Draft[] = [];
			for (const file of uploads) {
				if (file.size > 10 * 1024 * 1024) throw new Error('Files must be at most 10 MiB');
				const path = currentPath + (file.webkitRelativePath || file.name);
				const bytes = new Uint8Array(await file.arrayBuffer());
				let text: string | undefined;
				try {
					text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
					if (text.includes('\0')) text = undefined;
				} catch {}
				if (path === 'SKILL.md' && text === undefined) throw new Error('SKILL.md must be UTF-8');
				drafts.push({
					path,
					size: file.size,
					upload: file,
					content: text,
					encoding: text === undefined ? 'base64' : undefined,
					changed: true
				});
			}
			validatePaths([...files.map((f) => f.path), ...drafts.map((f) => f.path)]);
			files = [...files, ...drafts];
			dirty = true;
		} catch (error) {
			toast.error(skillError(error));
		}
	};
	const download = async (path: string) => {
		flush();
		const file = files.find((f) => f.path === path);
		if (file)
			try {
				saveAs(await blobFor(file), path.split('/').pop() || 'file');
			} catch (error) {
				toast.error(skillError(error));
			}
	};
	const encoded = async (file: Draft): Promise<SkillFile> => {
		if (file.encoding !== 'base64')
			return { path: file.path, content: file.content ?? (await (await blobFor(file)).text()) };
		const blob = await blobFor(file);
		const content = await new Promise<string>((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result).split(',')[1]);
			reader.onerror = reject;
			reader.readAsDataURL(blob);
		});
		return { path: file.path, content, encoding: 'base64' };
	};
	export const getFiles = async () => {
		flush();
		return Promise.all(files.map(encoded));
	};
	export const getOperations = async (): Promise<SkillFileOperation[]> => {
		flush();
		// Reconcile structural edits against original paths. New draft files never reach the server until save.
		const original = new Set(files.map((f) => f.sourcePath).filter(Boolean));
		const baseline = versionId
			? (await getSkillFiles(localStorage.token, skillId, versionId)).files
			: [];
		const changes: SkillFileOperation[] = baseline
			.filter((f: SkillFileSummary) => !original.has(f.path) && f.path !== 'SKILL.md')
			.map((f: SkillFileSummary) => ({ op: 'delete', path: f.path }));
		// Put moved files from their immutable source, then remove old paths. This also supports swaps.
		for (const file of files)
			if (file.changed || file.sourcePath !== file.path)
				changes.push({ op: 'put', ...(await encoded(file)) });
		for (const file of files)
			if (
				file.sourcePath &&
				file.sourcePath !== file.path &&
				!files.some((f) => f.path === file.sourcePath)
			)
				changes.push({ op: 'delete', path: file.sourcePath });
		return changes;
	};
	onDestroy(() => {
		++requestId;
		clearUrls();
	});
</script>

<ConfirmDialog
	bind:show={dialog.show}
	title={dialog.title}
	input={dialog.input}
	inputValue={dialog.value}
	on:confirm={(event) => dialog.action(event.detail)}
/>
<input
	type="file"
	multiple
	webkitdirectory
	bind:this={folderInput}
	hidden
	on:change={() => {
		upload(Array.from(folderInput.files || []));
		folderInput.value = '';
	}}
/>
<input
	type="file"
	multiple
	hidden
	bind:this={uploadInput}
	on:change={() => {
		if (!readOnly) upload(Array.from(uploadInput.files || []));
		uploadInput.value = '';
	}}
/>
<div class="flex h-full min-h-0 flex-col">
	<div class="flex min-h-0 flex-1 flex-col md:flex-row">
		{#if $mobile}
			{@render fileList()}
		{:else}
			<ResizableSidePanel
				open
				side="left"
				bind:width={sidebarWidth}
				minWidth={180}
				maxWidth={480}
				minSiblingWidth={320}
				className="min-h-0"
				resizerId="skill-files-resizer"
			>
				{@render fileList()}
			</ResizableSidePanel>
			{@render fileContent()}
		{/if}
	</div>
</div>

{#if $mobile}
	<Drawer bind:show={showFileDrawer} className="h-full" onClose={flush}>
		<div
			class="h-full"
			role="dialog"
			aria-modal="true"
			aria-label={selected}
			tabindex="-1"
			use:fileDrawer
		>
			{@render fileContent()}
		</div>
	</Drawer>
{/if}

{#snippet fileContent()}
	<div
		class="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white dark:bg-gray-900"
	>
		<div class="flex shrink-0 items-center gap-1 px-2.5 py-1.5 text-xs dark:bg-black">
			{#if $mobile}
				<button
					type="button"
					aria-label={$i18n.t('Back to files')}
					class="flex shrink-0 items-center gap-1 whitespace-nowrap py-0.5 pr-1 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => {
						flush();
						showFileDrawer = false;
					}}
				>
					<ChevronLeft className="size-3.5" />{$i18n.t('Back')}
				</button>
			{/if}
			<span class="min-w-0 flex-1 truncate text-gray-500" title={selected}>{selected}</span>
			{#if /\.md$/i.test(selected) && !loading}<button
					type="button"
					class="rounded-lg px-1.5 py-0.5 text-gray-500 transition hover:text-gray-900 dark:hover:text-gray-100"
					on:click={async () => {
						preview = !preview;
						if (preview) await renderPreview();
					}}>{preview ? 'Edit' : 'Preview'}</button
				>{/if}
			<button
				type="button"
				class="rounded-lg px-1.5 py-0.5 text-gray-500 transition hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => download(selected)}>Download</button
			>
		</div>
		{#if loadError}<p role="alert" class="p-3 text-red-500">{loadError}</p>
		{:else if loading}<p class="p-3 text-xs">{$i18n.t('Loading...')}</p>
		{:else if objectUrl}
			{#if /\.(png|jpe?g|gif|webp|avif)$/i.test(selected)}<img
					src={objectUrl}
					alt={selected}
					class="min-h-0 object-contain p-3"
				/>
			{:else if /\.pdf$/i.test(selected)}<iframe
					title={selected}
					src={objectUrl}
					sandbox=""
					class="min-h-0 flex-1"
				></iframe>
			{:else}<p class="p-3 text-xs text-gray-500">Binary file. Download to open.</p>{/if}
		{:else if preview}
			<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
			<div
				class="prose dark:prose-invert min-h-0 max-w-none flex-1 overflow-auto p-4"
				on:click={(event) => {
					const link = (event.target as Element).closest('a[data-skill-path]') as HTMLAnchorElement;
					if (link) {
						event.preventDefault();
						const path = link.dataset.skillPath!;
						if (files.some((f) => f.path === path)) open(path);
						else toast.error('File not found');
					}
				}}
			>
				{@html previewHtml}
			</div>
		{:else}<div class="min-h-0 flex-1">
				<FileCodeEditor
					bind:this={codeEditor}
					bind:value
					filePath={selected}
					{readOnly}
					onSave={async () => {
						flush();
						await onSave();
					}}
				/>
			</div>{/if}
	</div>
{/snippet}

{#snippet createInput()}
	{#if creating && !readOnly}
		<div
			class="flex h-7 items-center gap-1.5 pr-2"
			style:padding-left={`${26 + currentPath.split('/').filter(Boolean).length * 16}px`}
		>
			<FileTypeIcon name={newName} type={creating} size={14} />
			<input
				bind:this={newNameInput}
				bind:value={newName}
				class="min-w-0 flex-1 bg-transparent py-0.5 text-xs outline-hidden"
				placeholder={$i18n.t(creating === 'file' ? 'File name' : 'Folder name')}
				aria-label={$i18n.t(creating === 'file' ? 'File name' : 'Folder name')}
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						event.preventDefault();
						event.stopPropagation();
						submitCreate();
					}
					if (event.key === 'Escape') {
						event.preventDefault();
						event.stopPropagation();
						cancelCreate();
					}
				}}
				on:blur={submitCreate}
			/>
		</div>
	{/if}
{/snippet}

{#snippet fileList()}
	<div class="h-full min-h-0 w-full overflow-auto p-1.5">
		<div class="mb-1 flex w-full items-center gap-1">
			<div class="min-w-0 flex-1">{@render version()}</div>
			{#if readOnly}
				<Tooltip content={$i18n.t('Read Only')}>
					<span
						class="flex items-center px-0.5 text-gray-400"
						role="img"
						aria-label={$i18n.t('Read Only')}><LockClosed className="size-3" /></span
					>
				</Tooltip>
			{/if}
			{#if !readOnly || canExport}
				<Dropdown closeOnSelect align="end">
					<button
						type="button"
						aria-label={$i18n.t('Actions')}
						class="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl px-2 text-gray-500 transition hover:text-gray-900 dark:hover:text-gray-100"
					>
						<EllipsisHorizontal className="size-4" />
					</button>
					<div slot="content">
						<DropdownMenu className="min-w-[10.625rem]">
							{#if !readOnly}
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => startCreate('file')}
									><Plus className="size-3.5" />{$i18n.t('New File')}</button
								>
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => startCreate('directory')}
									><Folder className="size-3.5" />{$i18n.t('New Folder')}</button
								>
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => uploadInput.click()}
									><ArrowUpTray className="size-3.5" />{$i18n.t('Upload')}</button
								>
								<button
									type="button"
									class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
									on:click={() => folderInput.click()}
									><Folder className="size-3.5" />{$i18n.t('Upload Folder')}</button
								>
							{/if}
							{#if canExport}
								{#if !readOnly}<hr class="border-gray-100 dark:border-gray-800" />{/if}
								{@render exports()}
							{/if}
						</DropdownMenu>
					</div>
				</Dropdown>
			{/if}
		</div>
		{#if $mobile && !showFileDrawer && loadError}
			<p role="alert" class="p-3 text-xs text-red-500">{loadError}</p>
		{/if}
		{#if selectedPaths.size && !readOnly}<button
				type="button"
				class="px-2 text-xs"
				on:click={() =>
					ask('Delete selected files?', false, () => {
						selectedPaths.forEach(remove);
						selectedPaths = new Set();
					})}>Delete selected</button
			>{/if}
		{#if !currentPath}{@render createInput()}{/if}
		<ul>
			{#each rows as { entry, path, depth } (path)}
				<FileEntryRow
					variant="workspace"
					{entry}
					currentPath=""
					fullPath={path}
					{depth}
					expanded={expandedFolders.has(path)}
					{dragType}
					active={entry.type === 'file' && selected === path}
					selected={selectedPaths.has(path)}
					selectionMode={selectedPaths.size > 0}
					parentWritable={!readOnly && path !== 'SKILL.md'}
					{selectedPaths}
					onOpen={(entry) => (entry.type === 'directory' ? toggleFolder(path) : open(path))}
					onSelect={(_, __, path) => {
						path = path.replace(/\/$/, '');
						selectedPaths.has(path) ? selectedPaths.delete(path) : selectedPaths.add(path);
						selectedPaths = new Set(selectedPaths);
					}}
					onToggleExpand={toggleFolder}
					onRename={(path, name) => rename(path, path.slice(0, path.lastIndexOf('/') + 1) + name)}
					onDelete={(path) =>
						ask('Delete this file or folder?', false, () => remove(path.replace(/\/$/, '')))}
					onMove={(paths, destination) =>
						paths.forEach((path) => {
							path = path.replace(/\/$/, '');
							rename(path, destination + (path.split('/').pop() || 'file'));
						})}
					onDownload={download}
				/>
				{#if creating && !readOnly && entry.type === 'directory' && currentPath === path + '/'}
					<li>{@render createInput()}</li>
				{/if}
			{/each}
		</ul>
		{#if !rows.length}<p class="p-3 text-xs text-gray-500">
				Empty folders are saved when they contain files.
			</p>{/if}
	</div>
{/snippet}
