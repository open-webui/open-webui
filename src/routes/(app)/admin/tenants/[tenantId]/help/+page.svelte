<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import {
		getTenantById,
		updateTenant,
		type TenantInfo,
		type TenantUpdatePayload
	} from '$lib/apis/tenants';

	export let data: { tenantId: string };

	const i18n = getContext('i18n');

	let tenant: TenantInfo | null = null;
	let helpText = '';
let loading = true;
let saving = false;
let loadError: string | null = null;
let activeTab: 'edit' | 'preview' = 'edit';

	const formatDate = (timestamp?: number) => {
		if (!timestamp) return '—';
		return new Date(timestamp * 1000).toLocaleString();
	};

		const fetchTenant = async () => {
		if (typeof localStorage === 'undefined' || !localStorage.token) {
			loadError = $i18n.t('You must be signed in to view tenants.');
			loading = false;
			return;
		}

		loading = true;
		loadError = null;

		try {
			const info = await getTenantById(localStorage.token, data.tenantId);
			tenant = info;
			helpText = info.help_text ?? '';
		} catch (error) {
			const message = typeof error === 'string' ? error : (error?.detail ?? 'Failed to load tenant.');
			loadError = message;
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		fetchTenant();
	});

		const saveHelpText = async () => {
		if (!tenant) {
			toast.error($i18n.t('Select a tenant first.'));
			return;
		}

		if (typeof localStorage === 'undefined' || !localStorage.token) {
			toast.error($i18n.t('You must be signed in for this action.'));
			return;
		}

		saving = true;
		try {
			const payload: TenantUpdatePayload = {
				help_text: helpText ?? ''
			};
			const updated = await updateTenant(localStorage.token, tenant.id, payload);
			tenant = updated;
			helpText = updated.help_text ?? '';
			toast.success($i18n.t('Help text updated'));
		} catch (error) {
			const message =
				typeof error === 'string' ? error : ($i18n.t(error?.detail) ?? $i18n.t('Failed to update help text.'));
			toast.error(message);
		} finally {
			saving = false;
		}
		};

</script>

<svelte:head>
	<title>{$i18n.t('Edit Help Text')}</title>
</svelte:head>

<main class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 lg:px-8">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<p class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
				{$i18n.t('Tenant Help')}
			</p>
			<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Edit Help Text')}
			</h1>
			{#if tenant}
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('Updating help for')}: <span class="font-medium">{tenant.name}</span>
				</p>
			{/if}
		</div>
		<button
			type="button"
			class="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
			on:click={() => goto('/admin/tenants')}
		>
			{$i18n.t('Back to Tenants')}
		</button>
	</div>

	{#if loading}
		<div class="flex min-h-[40vh] items-center justify-center">
			<Spinner className="size-8" />
		</div>
	{:else if loadError}
		<div class="rounded-2xl border border-red-200 bg-red-50/80 p-6 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100">
			<p>{loadError}</p>
			<button
				class="mt-4 rounded-full bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500"
				on:click={fetchTenant}
			>
				{$i18n.t('Retry')}
			</button>
		</div>
	{:else if tenant}
		<section class="space-y-6">
			<div class="rounded-2xl border border-gray-100 bg-white/80 p-4 text-sm text-gray-600 dark:border-gray-800 dark:bg-gray-900/70 dark:text-gray-300">
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<p class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
							{$i18n.t('Prompt Storage')}
						</p>
						<p class="font-mono text-xs text-gray-900 dark:text-gray-100">{tenant.s3_bucket}</p>
					</div>
					<div>
						<p class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
							{$i18n.t('Last Updated')}
						</p>
						<p class="text-sm text-gray-900 dark:text-gray-100">{formatDate(tenant.updated_at)}</p>
					</div>
				</div>
			</div>

			<form
				class="space-y-4 rounded-2xl border border-gray-100 bg-white/80 p-6 dark:border-gray-800 dark:bg-gray-900/70"
				on:submit|preventDefault={saveHelpText}
			>
				<div>
					<label class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
						{$i18n.t('Help Text Markdown')}
					</label>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('Use markdown to describe how this tenant should use the assistant.')}
					</p>
				</div>

				<div>
					<div class="flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 p-1 text-xs font-semibold dark:border-gray-700 dark:bg-gray-900/60">
						<button
							type="button"
							class={`flex-1 rounded-full px-3 py-1.5 transition ${
								activeTab === 'edit'
									? 'bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-gray-100'
									: 'text-gray-500 dark:text-gray-400'
							}`}
							on:click={() => (activeTab = 'edit')}
						>
							{$i18n.t('Edit Markdown')}
						</button>
						<button
							type="button"
							class={`flex-1 rounded-full px-3 py-1.5 transition ${
								activeTab === 'preview'
									? 'bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-gray-100'
									: 'text-gray-500 dark:text-gray-400'
							}`}
							on:click={() => (activeTab = 'preview')}
						>
							{$i18n.t('Preview')}
						</button>
					</div>

					<div class="mt-4">
						{#if activeTab === 'edit'}
							<Textarea
								bind:value={helpText}
								minSize={360}
								className="w-full rounded-2xl border border-gray-200 bg-transparent px-4 py-3 text-sm font-mono text-gray-900 outline-hidden focus:border-blue-500 dark:border-gray-700 dark:text-gray-100"
								placeholder={$i18n.t('Enter markdown...')}
								required
							/>
						{:else}
							<div class="min-h-[18rem] rounded-2xl border border-gray-200 bg-white/80 px-4 py-3 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-100">
								{#if helpText.trim().length === 0}
									<p class="text-sm text-gray-500 dark:text-gray-400">
										{$i18n.t('Nothing to preview yet.')}
									</p>
								{:else}
									<div class="markdown-prose max-w-none">
										<Markdown
											id="tenant-help-preview"
											content={helpText}
											done={true}
											save={false}
											preview={true}
											editCodeBlock={false}
										/>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				</div>

				<div class="flex flex-wrap items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">
					<span>
						{$i18n.t('Characters')}: {helpText.length}
					</span>
					<div class="flex gap-2">
						<button
							type="button"
							class="rounded-full border border-gray-200 px-4 py-2 font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
							on:click={() => goto('/admin/tenants')}
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							type="submit"
							class="inline-flex items-center rounded-full bg-black px-4 py-2 font-semibold text-white transition hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-100"
							disabled={saving}
						>
							{$i18n.t('Save Help Text')}
							{#if saving}
								<span class="ml-2">
									<Spinner className="size-4" />
								</span>
							{/if}
						</button>
					</div>
				</div>
			</form>
		</section>
	{/if}
</main>
