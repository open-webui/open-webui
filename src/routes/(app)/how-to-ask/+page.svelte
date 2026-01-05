<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import TenantSelector from '$lib/components/chat/TenantSelector.svelte';

import {
	getTenantById,
	getUploadTenants,
	type TenantInfo
} from '$lib/apis/tenants';
import { user } from '$lib/stores';

	const i18n = getContext('i18n');
	const TENANT_OVERRIDE_STORAGE_KEY = 'luxor_tenant_override';

	let helpHtml = '';
	let helpLoading = true;
	let helpError: string | null = null;

	let tenantOptions: TenantInfo[] = [];
	let tenantOptionsLoading = false;
	let tenantLoadError: string | null = null;
	let tenantListInitialized = false;

	let selectedOverrideId: string | null = null;
	let lastLoadedKey: string | null = null;
	let currentLoadKey: string | null = null;

	let userReady = false;
	let initialized = false;

	const isBrowser = typeof window !== 'undefined';

	const sanitizeMarkdown = (text: string) =>
		DOMPurify.sanitize(marked.parse(text ?? '', { mangle: false, headerIds: false }));

	const getStoredOverride = () => {
		if (!isBrowser) return null;
		return window.localStorage.getItem(TENANT_OVERRIDE_STORAGE_KEY);
	};

	const persistOverride = (value: string | null) => {
		if (!isBrowser) return;
		if (value) {
			window.localStorage.setItem(TENANT_OVERRIDE_STORAGE_KEY, value);
		} else {
			window.localStorage.removeItem(TENANT_OVERRIDE_STORAGE_KEY);
		}
	};

	const getActiveTenantId = (): string | null => {
		if (!userReady) return null;
		if ($user?.role === 'admin') {
			return selectedOverrideId ?? ($user?.tenant_id ?? null);
		}
		return $user?.tenant_id ?? null;
	};

	const applyHelpText = (text: string | null | undefined) => {
		const content = text && text.trim().length > 0 ? text : '';
		helpHtml = sanitizeMarkdown(content);
	};

	const loadHelpForTenant = async (tenantId: string | null) => {
		const loadKey = tenantId ?? '__default__';
		currentLoadKey = loadKey;
		helpLoading = true;
		helpError = null;

		let helpText: string | null = null;
		const hasToken = typeof localStorage !== 'undefined' && !!localStorage.token;

		if (tenantId && hasToken) {
			try {
				const tenant = await getTenantById(localStorage.token, tenantId);
				helpText = tenant?.help_text ?? null;
			} catch (error) {
				const message =
					typeof error === 'string'
						? error
						: error?.detail ?? $i18n.t('Failed to load tenant help content.');
				helpError = message;
			}
		} else if (tenantId && !hasToken) {
			helpError = $i18n.t('You must be signed in to view tenant help.');
		}

		if (currentLoadKey === loadKey) {
			applyHelpText(helpText);
			helpLoading = false;
		}
	};

	const loadTenantOptions = async () => {
		if (!userReady || $user?.role !== 'admin') {
			return;
		}
		if (tenantOptionsLoading) {
			return;
		}
		if (typeof localStorage === 'undefined' || !localStorage.token) {
			return;
		}

		tenantOptionsLoading = true;
		tenantLoadError = null;
		try {
			tenantOptions = await getUploadTenants(localStorage.token);
		} catch (error) {
			const message =
				typeof error === 'string' ? error : error?.detail ?? $i18n.t('Failed to load tenants.');
			tenantLoadError = message;
		} finally {
			tenantOptionsLoading = false;
		}
	};

	const refreshHelp = () => {
		const activeTenantId = getActiveTenantId();
		const key = activeTenantId ?? '__default__';
		if (key !== lastLoadedKey) {
			lastLoadedKey = key;
			loadHelpForTenant(activeTenantId);
		}
	};

	const handleTenantScopeChange = (event: CustomEvent<string | null>) => {
		selectedOverrideId = event.detail;
		persistOverride(selectedOverrideId);
		refreshHelp();
	};

	onMount(async () => {
		refreshHelp();
	});

	$: userReady = $user !== undefined;

	$: if (userReady && !initialized) {
		if ($user?.role === 'admin') {
			selectedOverrideId = getStoredOverride();
		} else {
			selectedOverrideId = null;
		}
		initialized = true;
		refreshHelp();
	}

	$: if (userReady && $user?.role === 'admin' && !tenantListInitialized) {
		tenantListInitialized = true;
		loadTenantOptions();
	}

	$: if (userReady) {
		const key = (getActiveTenantId() ?? '__default__');
		if (key !== lastLoadedKey) {
			refreshHelp();
		}
	}
</script>

<svelte:head>
	<title>{$i18n.t('How to Ask Luxor')}</title>
</svelte:head>

<main class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 lg:px-8">
	{#if $user?.role === 'admin'}
		<div class="rounded-2xl border border-gray-100 bg-white/80 p-4 dark:border-gray-800 dark:bg-gray-900/60">
			<TenantSelector
				tenants={tenantOptions}
				selectedTenantId={selectedOverrideId}
				loading={tenantOptionsLoading}
				error={tenantLoadError}
				on:change={handleTenantScopeChange}
			/>
			<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Select a tenant to preview their help experience.')}
			</p>
		</div>
	{/if}
	

	<section class="rounded-2xl border border-gray-100 bg-white/90 p-6 dark:border-gray-800 dark:bg-gray-900/70">
		{#if helpLoading}
			<div class="flex min-h-[40vh] items-center justify-center">
				<Spinner className="size-8" />
			</div>
		{:else}
			{#if helpError}
				<div class="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/60 dark:text-amber-100">
					{helpError}
				</div>
			{/if}
			<div class="markdown-prose max-w-none text-gray-900 dark:text-gray-100">
				{@html helpHtml}
			</div>
		{/if}
	</section>
</main>
