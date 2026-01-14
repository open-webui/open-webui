<script lang="ts">
	import { toast } from 'svelte-sonner';
import {
	uploadDocument,
	ingestUploadedDocument,
	rebuildTenantArtifact,
	rebuildUserArtifact,
	type UploadDocumentResponse,
	type UploadVisibility
} from '$lib/apis/uploads';
import { getUploadTenants, type TenantInfo } from '$lib/apis/tenants';
	import { WEBUI_NAME, user, showArchivedChats, showSidebar, mobile } from '$lib/stores';
	import { onMount, getContext, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import Files from '$lib/components/upload/Files.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { getFiles } from '$lib/apis/uploads';
	import { fade } from 'svelte/transition';
	const i18n = getContext('i18n');
	let activeTab = 'all';
	let visibility: UploadVisibility = 'public';
	let selectedFiles: File[] = [];
	let isUploading = false;
	let uploadResults: UploadDocumentResponse[] = [];
	let fileInput: HTMLInputElement | null = null;
	let tenants: TenantInfo[] = [];
	let tenantsLoading = false;
	let selectedTenantId: string | null = null;
	let tenantsInitialized = false;
	let selectedTenant: TenantInfo | null = null;
	let isRebuildingTenant = false;
	let isRebuildingPrivate = false;
	let publicCount: number = 0;
	let privateCount: number = 0;
	let isPrivate = (typeof visibility !== 'undefined') ? (visibility === 'private') : true;
	let filesRefreshKey = 0;

	const loadTenants = async () => {
		if (
			tenantsLoading ||
			tenantsInitialized ||
			!browser ||
			!localStorage.token ||
			$user?.role !== 'admin'
		) {
			return;
		}
		tenantsLoading = true;
		try {
			const list = await getUploadTenants(localStorage.token);
			tenants = list;
			const defaultId = $user?.tenant_id ?? list[0]?.id ?? null;
			selectedTenantId = defaultId;
		} catch (err) {
			const message = typeof err === 'string' ? err : (err?.detail ?? $i18n.t('Failed to load tenants.'));
			toast.error(message);
		} finally {
			tenantsLoading = false;
			tenantsInitialized = true;
		}
	};

	onMount(() => {
		if (browser) {
			loadTenants();
		}
	});

	$: if ($user?.role === 'admin' && browser && !tenantsInitialized) {
		loadTenants();
	}

	const handleFileChange = (event: Event) => {
		const target = event.target as HTMLInputElement;
		const incoming = target.files ? Array.from(target.files) : [];
		if (incoming.length === 0) {
			return;
		}
		const seen = new Set(
			selectedFiles.map((file) => `${file.name}:${file.size}:${file.lastModified}`)
		);
		const merged = [...selectedFiles];
		for (const file of incoming) {
			const key = `${file.name}:${file.size}:${file.lastModified}`;
			if (!seen.has(key)) {
				seen.add(key);
				merged.push(file);
			}
		}
		selectedFiles = merged;
		if (fileInput) {
			fileInput.value = '';
		}
	};

	const formatBytes = (bytes: number) => {
		if (!bytes) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, exponent);
		return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[exponent]}`;
	};

	const handleSubmit = async (event: SubmitEvent) => {
		event.preventDefault();
		if (selectedFiles.length === 0) {
			toast.error($i18n.t('Please choose at least one file to upload.'));
			return;
		}

		if (!tenantBucket) {
			toast.error($i18n.t('Your tenant does not have an S3 bucket configured.'));
			return;
		}

		if (!localStorage.token) {
			toast.error($i18n.t('You must be signed in to upload files.'));
			return;
		}

		isUploading = true;
		uploadResults = [];

		const tenantOverride =
			$user?.role === 'admin' ? (selectedTenantId ?? $user?.tenant_id ?? undefined) : undefined;

		try {
			const settled = await Promise.allSettled(
				selectedFiles.map((file) =>
					uploadDocument(localStorage.token, file, visibility, tenantOverride)
				)
			);

			const successes = settled
				.filter((result): result is PromiseFulfilledResult<UploadDocumentResponse> => result.status === 'fulfilled')
				.map((result) => result.value);
			const failures = settled
				.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
				.map((result) => result.reason)
				.filter(Boolean);

			if (successes.length > 0) {
				uploadResults = successes;
				toast.success(`${$i18n.t("Upload complete")} (${successes.length}).`);
			}

			if (failures.length > 0) {
				toast.error(
					`${failures.length} ${$i18n.t('file(s) failed to upload.')}`
				);
			}

			if (successes.length > 0) {
				if (visibility === 'public') {
					try {
						await ingestUploadedDocument(
							localStorage.token,
							successes.map((item) => item.key)
						);
						toast.success($i18n.t('Digitization requested.'));
					} catch (err) {
						const message =
							typeof err === 'string'
								? err
								: (err?.detail ?? $i18n.t('Failed to trigger digitization of the uploaded files.'));
						toast.error(message);
					}
				} else {
					if (tenantBucket && $user?.id) {
						try {
							await rebuildUserArtifact(localStorage.token, tenantBucket, $user.id);
							toast.success($i18n.t('Private artifact rebuild requested.'));
						} catch (err) {
							const message =
								typeof err === 'string'
									? err
									: (err?.detail ?? $i18n.t('Failed to rebuild private artifact.'));
							toast.error(message);
						}
					}
				}
			}

			selectedFiles = [];
			if (fileInput) {
				fileInput.value = '';
			}
			await refreshCounts();
			filesRefreshKey += 1;
		} finally {
			isUploading = false;
		}
	};

	const ensureToken = () => {
		if (!localStorage.token) {
			toast.error($i18n.t('You must be signed in for this action.'));
			return null;
		}
		return localStorage.token;
	};

	const handleRebuildTenant = async () => {
		if (!selectedTenant?.s3_bucket) {
			toast.error($i18n.t('Select a tenant to rebuild.'));
			return;
		}
		const token = ensureToken();
		if (!token) return;

		isRebuildingTenant = true;
		try {
			await rebuildTenantArtifact(token, selectedTenant.s3_bucket);
			toast.success($i18n.t('Tenant artifact rebuild requested.'));
		} catch (err) {
			const message =
				typeof err === 'string'
					? err
					: (err?.detail ?? $i18n.t('Failed to rebuild tenant artifact.'));
			toast.error(message);
		} finally {
			isRebuildingTenant = false;
		}
	};

	const handleRebuildPrivate = async () => {
		if (!tenantBucket || !$user?.id) {
			toast.error($i18n.t('Tenant information unavailable.'));
			return;
		}
		const token = ensureToken();
		if (!token) return;

		isRebuildingPrivate = true;
		try {
			await rebuildUserArtifact(token, tenantBucket, $user.id);
			toast.success($i18n.t('Private artifact rebuild requested.'));
		} catch (err) {
			const message =
				typeof err === 'string'
					? err
					: (err?.detail ?? $i18n.t('Failed to rebuild private artifact.'));
			toast.error(message);
		} finally {
			isRebuildingPrivate = false;
		}
	};

	$: selectedTenant =
		$user?.role === 'admin'
			? (tenants.find((t) => t.id === (selectedTenantId ?? $user?.tenant_id)) ?? null)
			: null;

	$: tenantBucket =
		$user?.role === 'admin'
			? (selectedTenant?.s3_bucket ?? null)
			: ($user?.tenant_s3_bucket ?? null);

	const joinPath = (base: string, suffix: string) => {
		const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base;
		const normalizedSuffix = suffix.startsWith('/') ? suffix.slice(1) : suffix;
		return `${normalizedBase}/${normalizedSuffix}`;
	};

	$: publicPath = tenantBucket ?? null;
	$: privatePath = tenantBucket && $user?.id ? joinPath(tenantBucket, `/users/${$user.id}`) : null;
	$: destinationPreview = tenantBucket
		? `${tenantBucket}${visibility === 'private' ? `/users/${$user?.id}` : ''}/${
				selectedFiles[0]?.name ?? 'your-file.ext'
			}`
		: null;
	
	$: tabs = [
		{ id: 'all', label: `${$i18n.t("All")} (${publicCount + privateCount})` },
		{ id: 'public', label: `${$i18n.t("Teams")} (${publicCount})` },
		{ id: 'private', label: `${$i18n.t("Personal")} (${privateCount})` }
	];

	let _countCallId = 0;

	function _getTenantIdParamForCounts() {
		return $user?.role === 'admin'
			? (selectedTenantId ?? $user?.tenant_id ?? null)
			: undefined;
	}

	async function refreshCounts() {
		if (typeof window === 'undefined' || !localStorage?.token) {
			publicCount = 0;
			privateCount = 0;
			return;
		}

		_countCallId += 1;
		const myCall = _countCallId;

		const token = localStorage.token;
		const tenantIdParam = _getTenantIdParamForCounts();

		try {
			const publicPromise = publicPath ? getFiles(token, publicPath, tenantIdParam).catch((e) => { console.warn('public count fail', e); return []; }) : Promise.resolve([]);
			const privatePromise = privatePath ? getFiles(token, privatePath, tenantIdParam).catch((e) => { console.warn('private count fail', e); return []; }) : Promise.resolve([]);

			const [pubList, privList] = await Promise.all([publicPromise, privatePromise]);

			if (myCall === _countCallId) {
			publicCount = Array.isArray(pubList) ? pubList.length : 0;
			privateCount = Array.isArray(privList) ? privList.length : 0;
			}
		} catch (err) {
			console.error('refreshCounts error', err);
			if (myCall === _countCallId) {
			publicCount = 0;
			privateCount = 0;
			}
		}
	}

	$: if (typeof window !== 'undefined') {
		const _p = publicPath;
		const _q = privatePath;
		const _t = selectedTenantId;
		const _u = $user?.id;        // sign-in change
		const _ur = $user?.role;    // role change (admin vs user)
		refreshCounts();
	}

	$: if (isPrivate && visibility !== 'private') {
		visibility = 'private';
	} else if (!isPrivate && visibility !== 'public') {
		visibility = 'public';
	}

	$: accessIcon   = isPrivate ? '/icons/private.png' : '/icons/public.png';
	$: accessLabel  = isPrivate ? $i18n.t('Personal') + ':' : $i18n.t('Teams') + ':';
	$: accessDesc   = isPrivate ? $i18n.t('Only you can access this file') : $i18n.t('This file is accessible to the team');
	$: accessStyle  = isPrivate ? 'text-blue-600 font-semibold' : 'text-gray-900 font-semibold';

	const AUTO_HIDE_MS = 4000;
	let uploadResultTimeoutId: number | null = null;

	$: if (uploadResults.length > 0) {
		if (uploadResultTimeoutId !== null) {
			clearTimeout(uploadResultTimeoutId);
			uploadResultTimeoutId = null;
		}

		uploadResultTimeoutId = window.setTimeout(() => {
			uploadResults = [];
			uploadResultTimeoutId = null;
		}, AUTO_HIDE_MS);
	} else {
		if (uploadResultTimeoutId !== null) {
			clearTimeout(uploadResultTimeoutId);
			uploadResultTimeoutId = null;
		}
	}

	onDestroy(() => {
		if (uploadResultTimeoutId !== null) {
			clearTimeout(uploadResultTimeoutId);
			uploadResultTimeoutId = null;
		}
	});
</script>

<svelte:head>
	<title>{$i18n.t("Uploads")} • {$WEBUI_NAME}</title>
</svelte:head>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class=" flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<a class="min-w-fit transition" href="/notes">
							{$i18n.t('Uploads')}
						</a>
					</div>
				</div>

				<div class=" self-center flex items-center gap-1">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</nav>

	<div class="mx-auto w-full flex max-w-4xl flex-col gap-6">
		<div class="flex flex-col gap-4">
			<div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 w-full">
				<h1 class="text-3xl font-bold leading-tight">{$i18n.t("Uploads")}</h1>

				{#if $user?.role === 'admin'}
				<div class="md:flex-shrink-0 md:w-60 flex flex-col items-start">
					<span class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t("Admin User Only")}
					</span>

					{#if tenantsLoading}
					<div class="rounded-lg border border-gray-200 bg-gray-100 px-4 py-1 text-sm text-gray-600 shadow-sm dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300 w-full">
						{$i18n.t("Loading tenant list…")}
					</div>
					{:else if tenants.length === 0}
					<div class="rounded-lg border border-gray-200 bg-gray-100 px-4 py-1 text-sm text-gray-600 shadow-sm dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300 w-full">
						{$i18n.t("No tenants available")}
					</div>
					{:else}
					<div class="relative rounded-lg border border-gray-200 bg-gray-100 px-2 py-0.5 shadow-sm dark:border-gray-800 dark:bg-gray-900/60 w-full">
						<div class="flex items-center gap-2 flex-nowrap">
							<span class="inline-flex items-center h-7 text-[13px] font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap leading-[28px]">
								{$i18n.t("Tenant")}:
							</span>

							<div class="flex-1 min-w-0">
								<select
								id="tenant-select"
								bind:value={selectedTenantId}
								aria-label={$i18n.t("Target Tenant Bucket")}
								class="w-full bg-transparent text-[13px] font-semibold text-gray-900 dark:text-gray-50 h-7 leading-[28px] py-0 pl-0 -ml-1"
								>
								{#each tenants as tenant}
									<option value={tenant.id}>
									{tenant.name}
									</option>
								{/each}
								</select>
							</div>
						</div>
					</div>
					{/if}
				</div>
				{/if}
			</div>

			<p class={"text-sm text-gray-600 dark:text-gray-400" + ($user?.role === 'admin' ? ' md:max-w-[80%]' : '')}>
				{@html $i18n.t(
					'Upload documents {{pdf}} to use as references. {{product}} will read them and you will be able to reference them in your questions.',
					{
						pdf: '<span class="font-mono">(.pdf)</span>',
						product: '<span class="font-semibold">LUXOR</span>'
					}
				)}
			</p>
		</div>

		<div class="flex flex-col gap-6">
			{#if !$user}
				<div
					class="rounded-2xl border border-gray-100 bg-white/60 p-5 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900"
				>
					{$i18n.t("Loading your profile")}…
				</div>
			{:else if !tenantBucket}
				<div
					class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
				>
					{$i18n.t("Your tenant does not have an S3 bucket configured yet. Please contact an administrator before using this page.")}
				</div>
			{:else}
				<form
					class="space-y-5 rounded-2xl border border-gray-100 bg-white/80 p-5 shadow-sm dark:border-gray-850 dark:bg-gray-900/80"
					on:submit|preventDefault={handleSubmit}
				>
					<div class="space-y-2">
						<div class="rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-4">
							<label class="flex items-center gap-4 cursor-pointer select-none">
								<span class="bg-gray-600 text-white rounded-md px-3 py-1.5 font-medium text-sm">{$i18n.t("Choose Files")}</span>

								<input
									type="file"
									multiple
									on:change={handleFileChange}
									bind:this={fileInput}
									class="hidden"
								/>

								<span class="text-sm text-gray-600 dark:text-gray-300">
									{#if selectedFiles.length > 0}
										{selectedFiles.length} {$i18n.t("file(s) selected")}
									{:else}
										{$i18n.t("No file chosen")}
									{/if}
								</span>
							</label>
						</div>

						{#if selectedFiles.length > 0}
							<div class="mt-2 space-y-1 text-xs text-gray-500 dark:text-gray-400">
								{#each selectedFiles as file}
									<div class="flex items-center gap-2">
										<span class="font-medium text-gray-700 dark:text-gray-200">{file.name}</span>
										<span>• {formatBytes(file.size)}</span>
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<div class="flex items-center justify-between mt-2">
						<div class="flex items-center gap-3">
							<img src={accessIcon} alt={isPrivate ? 'Private' : 'Public'} class="w-6 h-6 flex-shrink-0" />

							<div>
								<div class="flex items-baseline gap-2">
									<span class={accessStyle + ' text-lg'}>{accessLabel}</span>
									<span class={isPrivate ? 'text-blue-600' : 'text-gray-700'}>{accessDesc}</span>
								</div>
							</div>
						</div>

						<div class="flex items-center gap-3">
							<span class="text-gray-700 font-medium mr-2">{$i18n.t("Access")}:</span>

							<label class="relative inline-flex items-center cursor-pointer select-none">
								<input
									type="checkbox"
									class="sr-only"
									bind:checked={isPrivate}
									aria-label={$i18n.t("Toggle file access (Private / Public)")}
								/>

								<div
									class={`w-12 h-6 rounded-full transition-colors ${isPrivate ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-700'}`}
								></div>

								<div
									class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform"
									class:translate-x-6={isPrivate}
								></div>
							</label>
						</div>
					</div>

					<div class="flex items-center justify-between gap-4 mt-4">
						<button
							type="submit"
							class="flex-1 rounded-xl text-white text-lg font-medium py-3 px-6 bg-gradient-to-r from-black via-slate-700 to-teal-500 hover:opacity-95 transition disabled:opacity-60 disabled:cursor-not-allowed"
							disabled={selectedFiles.length === 0 || isUploading}
						>
							{#if isUploading}
								<span class="animate-pulse">{$i18n.t("Uploading")}…</span>
							{:else}
								{$i18n.t("Upload")}
							{/if}
						</button>

						<button
							type="button"
							class="rounded-xl border-1 border-black px-6 py-3 text-sm font-medium text-gray-700 transition hover:text-gray-900 dark:text-gray-200 min-w-[140px]"
							on:click={() => {
								selectedFiles = [];
								uploadResults = [];
								if (fileInput) fileInput.value = '';
							}}
							>
							{$i18n.t("Reset")}
						</button>
					</div>
				</form>
			{/if}

			{#if uploadResults.length > 0}
				<div
					in:fade={{ duration: 200 }} out:fade={{ duration: 200 }}
					class="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-5 text-sm text-emerald-900 shadow-sm dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-100"
				>
					<h2 class="text-lg font-semibold text-emerald-900 dark:text-emerald-100">
						{$i18n.t("Upload complete")} ({uploadResults.length})
					</h2>
					<div class="mt-3 space-y-3">
						{#each uploadResults as result}
							<div class="rounded-xl border border-emerald-100 bg-white/70 p-3 dark:border-emerald-900/40 dark:bg-emerald-950/20">
								<div class="text-sm font-semibold text-emerald-900 dark:text-emerald-100">
									{result.original_filename}
								</div>
								<div class="mt-2 space-y-1 text-xs text-emerald-800/90 dark:text-emerald-200/80">
									<div class="font-mono break-all">{$i18n.t("Key")}: {result.key}</div>
									<div class="font-mono break-all">{$i18n.t("URL")}: {result.url}</div>
									<div class="capitalize">{$i18n.t("Visibility")}: {$i18n.t(result.visibility)}</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<div class="mt-4 flex items-center justify-between w-full gap-4">
			<h2 class="text-2xl font-bold leading-tight">{$i18n.t("Uploads List")}</h2>

			<div class="flex items-center gap-4">
				<div class="flex items-center gap-2">
					{#if $user?.role === 'admin' && activeTab === 'public'}
						<div class="flex justify-end">
							<button
								class="inline-flex items-center justify-center rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200 disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-500"
								type="button"
								on:click={handleRebuildTenant}
								disabled={!selectedTenant?.s3_bucket || isRebuildingTenant}
							>
								{#if isRebuildingTenant}
									<span class="animate-pulse">{$i18n.t("Rebuilding")}…</span>
								{:else}
									{$i18n.t("Rebuild Tenant Artifact")}
								{/if}
							</button>
						</div>
					{:else if activeTab === 'private'}
					<div class="flex justify-end">
						<button
							class="inline-flex items-center justify-center rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200 disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-500"
							type="button"
							on:click={handleRebuildPrivate}
							disabled={!tenantBucket || !$user?.id || isRebuildingPrivate}
						>
							{#if isRebuildingPrivate}
								<span class="animate-pulse">{$i18n.t("Rebuilding")}…</span>
							{:else}
								{$i18n.t("Rebuild Private Artifact")}
							{/if}
						</button>
					</div>
					{/if}
				</div>

				<div class="inline-flex flex-nowrap gap-2 rounded-2xl border border-gray-100 bg-white/70 p-2 shadow-sm dark:border-gray-850 dark:bg-gray-900/50">
					{#each tabs as tab}
						<button
							class={`rounded-xl px-4 py-2 text-sm font-medium transition ${
								activeTab === tab.id
								? 'bg-black text-white shadow'
								: 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850'
							}`}
							type="button"
							on:click={() => { activeTab = tab.id; }}
						>
							{tab.label}
						</button>
					{/each}
				</div>
			</div>
		</div>

		{#if activeTab === 'all'}
			{#if publicPath || privatePath}
				<Files
					paths={[publicPath, privatePath]}
					tenantId={$user?.role === 'admin'
						? (selectedTenantId ?? $user?.tenant_id ?? null)
						: undefined}
					tenantBucket={tenantBucket}
					refreshKey={filesRefreshKey}
					on:filesChanged={() => refreshCounts()}
				/>
			{:else}
				<div
					class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 shadow-sm dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
					>
					Select a tenant to view its public or private files.
				</div>
			{/if}
		{:else if activeTab === 'public'}
			{#if publicPath}
				<Files
					path={publicPath}
					tenantId={$user?.role === 'admin'
						? (selectedTenantId ?? $user?.tenant_id ?? null)
						: undefined}
					tenantBucket={tenantBucket}
					refreshKey={filesRefreshKey}
					on:filesChanged={() => refreshCounts()}
				/>
			{:else}
				<div
					class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 shadow-sm dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
				>
					{$i18n.t("Select a tenant to view its public files.")}
				</div>
			{/if}
		{:else if activeTab === 'private'}
			{#if privatePath}
				<Files
					path={privatePath}
					tenantId={$user?.role === 'admin'
						? (selectedTenantId ?? $user?.tenant_id ?? null)
						: undefined}
					tenantBucket={tenantBucket}
					refreshKey={filesRefreshKey}
					on:filesChanged={() => refreshCounts()}
				/>
			{:else}
				<div
					class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 shadow-sm dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
				>
					{$i18n.t("Select a tenant to view private files.")}
				</div>
			{/if}
		{/if}
	</div>
</div>
