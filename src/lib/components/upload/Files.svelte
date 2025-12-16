<script lang="ts">
	import { browser } from '$app/environment';
	import { deleteUpload, getFiles, rebuildUserArtifact, type StoredFile } from '$lib/apis/uploads';
	import { getTenantPromptFiles, deleteTenantPromptFile } from '$lib/apis/tenants';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';

	export let tenantId: string | null = null;
	export let path: string | null = null;
	export let tenantBucket: string | null = null;
	export let useTenantPromptApi: boolean = false;
	export let paths: string[] | null = null;

	let files: StoredFile[] = [];
	let loading = false;
	let error: string | null = null;
	let lastParams = '';
	let deletingKey: string | null = null;

	const dispatch = createEventDispatcher();

	const formatSize = (bytes: number) => {
		if (!bytes) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, exponent);
		return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[exponent]}`;
	};
	const normalizePath = (value: string) => (value.endsWith('/') ? value : `${value}/`);

	const displayName = (key: string) => {
		if (!key) return key;

		if (key.includes('/users/') || key.startsWith('users/')) {
			// Always return the final path segment
			const parts = key.split('/');
			return parts[parts.length - 1] ?? key;
		}

		if (paths && paths.length > 0) {
			for (const p of paths) {
			if (!p) continue;
			const prefix = normalizePath(p);
			if (key.startsWith(prefix)) return key.slice(prefix.length);
			}
		}

		if (!paths && path) {
			const prefix = normalizePath(path);
			if (key.startsWith(prefix)) return key.slice(prefix.length);
		}

		const parts = key.split('/');
		return parts[parts.length - 1] ?? key;
	};

	async function loadFilesForSinglePath(token: string, aPath: string, sourceHint?: 'public' | 'private') {
		try {
			if (useTenantPromptApi) {
				if (!tenantId) {
					throw 'Tenant ID is required to load prompts.';
				}
				const promptFiles = await getTenantPromptFiles(token, tenantId);
				return promptFiles.map((file) => ({
					key: file.key,
					size: file.size,
					last_modified: file.last_modified ?? new Date().toISOString(),
					url: file.url,
					tenant_id: tenantId,
					source: sourceHint ?? 'public'
				}));
			} else {
				const res = await getFiles(token, aPath, tenantId ?? undefined);
				const filesWithSource = (res ?? []).map((f) => ({
					...f,
					source: sourceHint ?? (f.key?.includes('/users/') ? 'private' : 'public')
				}));
				return filesWithSource;
			}
		} catch (err) {
			console.warn('[Files] loadFilesForSinglePath error for path', aPath, err);
			return [];
		}
	}

	function mergeAndSortLists(lists: StoredFile[][]) {
		const map = new Map<string, StoredFile>();

		for (const lst of lists) {
			for (const f of lst || []) {
				const existing = map.get(f.key);
				if (!existing) {
					map.set(f.key, f);
				} else {
					// prefer the fresher last_modified
					const a = new Date(existing.last_modified || 0).getTime();
					const b = new Date(f.last_modified || 0).getTime();
					if (b > a) {
						map.set(f.key, f);
					}
				}
			}
		}

		const merged = Array.from(map.values());
		merged.sort((a, b) => new Date(b.last_modified).getTime() - new Date(a.last_modified).getTime());
		return merged;
	}

	const loadFiles = async () => {
		if (!browser || !localStorage.token) {
			files = [];
			error = path || (paths && paths.length > 0) ? null : 'No path selected.';
			return;
		}

		loading = true;
		error = null;
		try {
			const token = localStorage.token;

			if (paths && paths.length > 0) {
				const validPaths = paths.filter((p) => p && p.length > 0) as string[];
				if (validPaths.length === 0) {
					files = [];
				} else {
					const promises = validPaths.map((p, idx) =>
						loadFilesForSinglePath(token, p, idx === 0 ? 'public' : idx === 1 ? 'private' : 'public')
					);
					const results = await Promise.all(promises);
					files = mergeAndSortLists(results);
				}

				if (useTenantPromptApi) {
					if (!tenantId) throw 'Tenant ID is required to load prompts.';
					const promptFiles = await getTenantPromptFiles(token, tenantId);
					files = promptFiles.map((file) => ({
						key: file.key,
						size: file.size,
						last_modified: file.last_modified ?? new Date().toISOString(),
						url: file.url,
						tenant_id: tenantId
					}));
				} else if (validPaths.length === 0) {
					files = [];
				} else {
					const promises = validPaths.map((p) => loadFilesForSinglePath(token, p));
					const results = await Promise.all(promises);
					files = mergeAndSortLists(results);
				}
			} else {
				if (!path) {
					files = [];
					error = 'No path selected.';
					return;
				}

				if (useTenantPromptApi) {
					const promptFiles = await getTenantPromptFiles(token, tenantId);
					files = promptFiles.map((file) => ({
						key: file.key,
						size: file.size,
						last_modified: file.last_modified ?? new Date().toISOString(),
						url: file.url,
						tenant_id: tenantId,
						source: 'public'
					}));
				} else {
					const res = await getFiles(token, path, tenantId ?? undefined);
					// Infer source: if path or key contains users/, treat as private
					files = (res ?? []).map((f) => ({
						...f,
						source: (f.key?.includes('/users/') || (path && path.includes('/users/'))) ? 'private' : 'public'
					}));
				}
			}
		} catch (err) {
			const message = typeof err === 'string' ? err : err?.detail ?? 'Failed to load files.';
			error = message;
			toast.error(message);
			files = [];
		} finally {
			loading = false;
		}
	};

	$: paramsKey = (() => {
		if (paths && paths.length > 0) {
			const joined = paths.filter(Boolean).join('|');
			return `${tenantId ?? 'self'}|paths:${joined}`;
		}
		return path ? `${tenantId ?? 'self'}|${path}` : '';
	})();

	$: if (browser && paramsKey && paramsKey !== lastParams) {
		lastParams = paramsKey;
		loadFiles();
	}

	const deleteFileHandler = async (file: StoredFile) => {
		if (!browser) return;
		if (!localStorage.token) {
			toast.error('You must be signed in to delete files.');
			return;
		}

		const name = displayName(file.key);
		const confirmed = window.confirm(`Delete ${name}? This cannot be undone.`);
		if (!confirmed) return;

		const parts = file.key.split('/');
		const derivedBucket = tenantBucket ?? (parts[0] ?? null);
		const derivedUserId = parts.length >= 3 && parts[1] === 'users' ? parts[2] : null;

		deletingKey = file.key;
		try {
			const token = localStorage.token;
			if (useTenantPromptApi) {
				if (!tenantId) {
					throw 'Tenant ID is required to delete prompts.';
				}
				await deleteTenantPromptFile(token, tenantId, file.key);
			} else {
				await deleteUpload(token, file.key);
			}
			files = files.filter((item) => item.key !== file.key);
			toast.success('File deleted.');

			dispatch('filesChanged', { key: file.key });

			if (derivedBucket && derivedUserId) {
				try {
					await rebuildUserArtifact(token, derivedBucket, derivedUserId);
					toast.success('Private artifact rebuild requested.');
				} catch (err) {
					const message =
						typeof err === 'string'
							? err
							: (err?.detail ?? 'Failed to rebuild private artifact.');
					toast.error(message);
				}
			}
		} catch (err) {
			const message = typeof err === 'string' ? err : err?.detail ?? 'Failed to delete file.';
			toast.error(message);
		} finally {
			deletingKey = null;
		}
	};

	export function refresh() {
		loadFiles();
	}

	function formatDateMinutes(dateLike: string | number | Date | null | undefined): string {
		if (dateLike === undefined || dateLike === null || dateLike === '') return '';
		const d = new Date(dateLike as string | number | Date);
		if (Number.isNaN(d.getTime())) return '';
		return d.toLocaleString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
			// hour12: false // uncomment to force 24-hour format
		});
	}
</script>

{#if loading}
	<div class="rounded-2xl border border-gray-100 bg-white/60 p-5 text-sm shadow-sm dark:border-gray-850 dark:bg-gray-900/70">
		Loading files…
	</div>
{:else if error}
	<div class="rounded-2xl border border-red-200 bg-red-50/70 p-5 text-sm text-red-900 shadow-sm dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
		{error}
	</div>
{:else if files.length === 0}
	<div class="rounded-2xl border border-gray-100 bg-white/70 p-5 text-sm text-gray-600 shadow-sm dark:border-gray-850 dark:bg-gray-900/70 dark:text-gray-300">
		{#if paths && paths.length > 0}
			No files found for these paths.
		{:else}
			No files found for this path.
		{/if}
	</div>
{:else}
	<div class="overflow-x-auto rounded-2xl border border-gray-100 bg-white/70 shadow-sm dark:border-gray-850 dark:bg-gray-900/70">
		<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-sm">
			<thead class="bg-gray-50 dark:bg-gray-900/80 text-gray-600 dark:text-gray-300">
				<tr>
					<th class="px-4 py-3 text-left font-semibold min-w-0">File</th>
					<th class="px-4 py-3 text-left font-semibold min-w-[7rem] whitespace-nowrap">Size</th>
					<th class="px-4 py-3 text-left font-semibold">Date Added</th>
					<th class="px-4 py-3 text-left font-semibold">Actions</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-100 dark:divide-gray-850 text-gray-800 dark:text-gray-100">
				{#each files as file}
					<tr>
						<td class="px-4 py-3 font-mono text-xs sm:text-sm">
							<div class="flex items-center gap-3">
								<img
									src={file.source === 'private' ? '/icons/private.png' : '/icons/public.png'}
									alt={file.source === 'private' ? 'Private file' : 'Public file'}
									class="w-5 h-5 flex-shrink-0"
									aria-hidden="false"
								/>

								<div class="min-w-0">
									<span class="block break-all whitespace-normal">
										{displayName(file.key)}
									</span>
								</div>
							</div>
						</td>
						<td class="px-4 py-3 whitespace-nowrap min-w-[7rem]">{formatSize(file.size)}</td>
						<td class="px-4 py-3">{formatDateMinutes(file.last_modified)}</td>
						<td class="px-4 py-3">
							<div class="inline-flex flex-col gap-2">
								<!-- TODO Downloading does not work locally.... might fix itself live?-->
								<a
									href={file.url}
									target="_blank"
									rel="noreferrer"
									class="inline-flex w-28 items-center justify-center rounded-lg border border-blue-600 px-3 py-1.5 text-xs font-medium text-blue-600 transition hover:bg-blue-50 dark:hover:bg-blue-950/30"
								>
									Download
								</a>
								<button
									type="button"
									on:click={() => deleteFileHandler(file)}
									disabled={deletingKey === file.key}
									class="inline-flex w-28 items-center justify-center rounded-lg border border-red-600 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-70 dark:hover:bg-red-950/30"
								>
									{deletingKey === file.key ? 'Deleting...' : 'Delete'}
								</button>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
