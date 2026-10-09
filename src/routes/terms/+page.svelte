
<script lang="ts">
	import { getI18n } from '$lib/utils/context';
	import { goto } from '$app/navigation';
	import { acceptTerms, getTermsStatus } from '$lib/apis/terms';
	import {
		TERMS_SUPPORT_EMAIL,
		TERMS_MAX_RETRY_ATTEMPTS,
		TERMS_RETRY_DELAY_MS,
		TERMS_VERSION,
		TERMS_VERSION_DATE
	} from '$lib/constants';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';
	import { getRequestToken } from '$lib/services/auth';

	// Markdown rendering
	import termsMarkdown from '$lib/content/terms/en.md?raw';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	const i18n = getI18n();

	// Render repository-controlled Markdown safely.
	const termsHtml = DOMPurify.sanitize(
		marked.parse(termsMarkdown) as string
	);

	let accepting = false;
	let accepted = false;
	let checkingTermsStatus = true;
	let termsStatusUnavailable = false;
	let acceptTermsFailureCount = 0;

	const sleep = (ms: number) =>
		new Promise<void>((resolve) => setTimeout(resolve, ms));

	const runWithRetry = async <T,>(
		operation: (attempt: number) => Promise<T>,
		maxAttempts = TERMS_MAX_RETRY_ATTEMPTS
	): Promise<T> => {
		let lastError: unknown;

		for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
			try {
				return await operation(attempt);
			} catch (error) {
				lastError = error;
				if (attempt < maxAttempts) {
					await sleep(TERMS_RETRY_DELAY_MS * attempt);
				}
			}
		}

		if (lastError instanceof Error) {
			throw lastError;
		}

		throw new Error(`Operation failed after ${maxAttempts} retries`);
	};

	const loadTermsStatus = async () => {
		checkingTermsStatus = true;
		termsStatusUnavailable = false;

		try {
			const status = await runWithRetry(
				() => getTermsStatus(getRequestToken()),
				TERMS_MAX_RETRY_ATTEMPTS
			);
			accepted = !!status?.accepted_at;
		} catch (e) {
			termsStatusUnavailable = true;
		} finally {
			checkingTermsStatus = false;
		}
	};

	const handleAccept = async () => {
		accepting = true;

		try {
			await runWithRetry(
				() => acceptTerms(getRequestToken()),
				TERMS_MAX_RETRY_ATTEMPTS
			);

			acceptTermsFailureCount = 0;
			toast.success('Terms accepted. Redirecting to CANChat.');
			await goto('/');
		} catch (e) {
			acceptTermsFailureCount += 1;

			if (acceptTermsFailureCount >= TERMS_MAX_RETRY_ATTEMPTS) {
				toast.error(
					'Repeated attempts to record acceptance have failed. Please wait a few minutes before retrying.'
				);
			} else {
				toast.error('Failed to record acceptance. Please try again.');
			}
		} finally {
			accepting = false;
		}
	};

	onMount(async () => {
		await $i18n.changeLanguage('en-GB');
		await loadTermsStatus();
	});
</script>

<div class="w-full h-screen max-h-[100dvh] overflow-y-auto bg-white dark:bg-gray-950">
	<div class="max-w-5xl mx-auto px-4 py-6 text-black dark:text-white">

		<!-- Header -->
		<div class="flex flex-col md:flex-row items-start md:items-center justify-between">
			<h1 class="text-3xl font-bold mb-2 md:mb-0 md:mr-4 dark:text-white">
				CANChat – Terms of Use
			</h1>

			<div>
				{#if accepted}
					<a
						href="/"
						class="px-4 py-2 mr-2 bg-purple-800 text-white rounded-md hover:bg-purple-800/80 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-600 focus-visible:ring-offset-2 dark:focus-visible:ring-purple-300"
						on:click={() => goto('/')}
					>
						Return to CANChat
					</a>
				{/if}

				<a
					href="/conditions"
					class="px-4 py-2 bg-purple-800 text-white rounded-md hover:bg-purple-800/80 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-600 focus-visible:ring-offset-2 dark:focus-visible:ring-purple-300"
				>
					Français
				</a>
			</div>
		</div>

		<!-- Terms version -->
		<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 pl-1">
			Effective Date: {TERMS_VERSION_DATE.toLocaleDateString('en-GB', {
				day: 'numeric',
				month: 'long',
				year: 'numeric'
			})} | Version: {TERMS_VERSION}
		</p>

		<!-- Markdown Terms of Use -->
		<div
			class="mt-2 p-3 w-full rounded-lg border border-neutral-500 text-neutral-900 dark:text-neutral-100 dark:bg-gray-900 shadow"
		>
			<article class="terms-markdown prose dark:prose-invert max-w-none">
				{@html termsHtml}
			</article>
		</div>

		<!-- Terms acceptance -->
		<div class="mt-3 flex justify-center">
			{#if accepted}
				<button
					type="button"
					on:click={() => goto('/')}
					disabled={accepting || checkingTermsStatus}
					aria-busy={accepting || checkingTermsStatus}
					class="px-4 py-2 bg-purple-800 text-white rounded-md hover:bg-purple-800/80 disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-600 focus-visible:ring-offset-2 dark:focus-visible:ring-purple-300"
				>
					{#if checkingTermsStatus}
						Checking terms...
					{:else}
						Return to CANChat
					{/if}
				</button>
			{:else}
				<div
					class="flex w-full max-w-4xl flex-col items-center justify-center gap-2 sm:flex-row sm:flex-wrap sm:gap-3"
				>
					{#if !termsStatusUnavailable}
						<button
							type="button"
							on:click={handleAccept}
							disabled={accepting || checkingTermsStatus}
							aria-busy={accepting || checkingTermsStatus}
							class="px-4 py-2 bg-purple-800 text-white rounded-md hover:bg-purple-800/80 disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-600 focus-visible:ring-offset-2 dark:focus-visible:ring-purple-300"
						>
							{#if checkingTermsStatus}
								Checking terms...
							{:else if accepting}
								Updating...
							{:else}
								I Accept Terms
							{/if}
						</button>
					{/if}

					{#if termsStatusUnavailable}
						<div
							role="alert"
							class="inline-flex max-w-xl items-start gap-2 rounded-md border border-red-700/90 bg-white px-3 py-2 text-sm text-red-900 shadow-sm dark:border-red-400 dark:bg-gray-950 dark:text-red-200"
						>
							<span
								class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold"
							>!</span>
							<p>
								Unable to verify terms status. Please contact
								<a
									class="font-semibold underline underline-offset-2"
									href={`mailto:${TERMS_SUPPORT_EMAIL}`}
								>CANChat Support</a>.
							</p>
						</div>
					{/if}

					{#if acceptTermsFailureCount >= TERMS_MAX_RETRY_ATTEMPTS}
						<div
							role="alert"
							class="inline-flex max-w-xl items-start gap-2 rounded-md border border-red-700/90 bg-white px-3 py-2 text-sm text-red-900 shadow-sm dark:border-red-400 dark:bg-gray-950 dark:text-red-200"
						>
							<span
								class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold"
							>!</span>
							<p>
								Repeated attempts to record acceptance have failed.
								Please wait a few minutes before retrying.
							</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	:global(.terms-markdown h1),
	:global(.terms-markdown h2),
	:global(.terms-markdown h3) {
		color: #7e22ce;
		font-weight: 600;
		margin-top: 1.25rem;
		margin-bottom: 0.75rem;
	}

	:global(.terms-markdown h1) {
		font-size: 1.5rem;
	}

	:global(.terms-markdown h2) {
		font-size: 1.25rem;
	}

	:global(.terms-markdown > h2:first-child) {
		margin-top: 0;
	}


	:global(.terms-markdown h3) {
		font-size: 1.125rem;
	}

	:global(.terms-markdown p) {
		margin-bottom: 0.75rem;
	}

	:global(.terms-markdown ul) {
		list-style-type: disc;
		padding-left: 1.5rem;
		margin-bottom: 1rem;
	}

	:global(.terms-markdown ol) {
		list-style-type: decimal;
		padding-left: 1.5rem;
		margin-bottom: 1rem;
	}

	:global(.terms-markdown li) {
		margin-bottom: 0.5rem;
	}

	:global(.terms-markdown a) {
		text-decoration: underline;
	}

	:global(.dark .terms-markdown h1),
	:global(.dark .terms-markdown h2),
	:global(.dark .terms-markdown h3) {
		color: #c084fc;
	}
</style>
