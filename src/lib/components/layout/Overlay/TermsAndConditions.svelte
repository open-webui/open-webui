<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import { acceptTerms } from '$lib/apis/users';
	import { user as userStore } from '$lib/stores';
	import type { Readable } from 'svelte/store';

	const i18n = getContext<Readable<any>>('i18n');

	let checked = false;
	let loading = false;

	const DATA_RISK_POLICY_URL =
		'https://www.nyu.edu/about/policies-guidelines-compliance/policies-and-guidelines/data-risk-classification-policy.html?challenge=d06e90d7-4d8f-4b88-9d8c-10b73beb60f1';

	const onAccept = async () => {
		if (!checked || loading) return;
		loading = true;
		try {
			await acceptTerms(localStorage.token, 1);
			// Reload to refresh session user (role should flip from pending -> user)
			location.reload();
		} catch (err) {
			console.error(err);
			const msg =
				typeof err === 'string'
					? err
					: (err as any)?.detail ?? (err as any)?.message ?? 'Failed to accept terms.';
			toast.error(msg);
		} finally {
			loading = false;
		}
	};
</script>

<div class="fixed w-full h-full flex z-999">
	<div class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center">
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-2xl w-[92vw]">
				<div class="text-center dark:text-white text-2xl font-medium z-50">
					{$i18n.t('NYU Pilot GenAI Terms & Conditions')}
				</div>

				<div class="mt-4 text-sm dark:text-gray-200 w-full">
					<div class="rounded-xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/70 p-4 max-h-[50vh] overflow-auto">
						<div class="space-y-4 text-base leading-relaxed">
							<p>
								Large Language Models[LLMs] have a usage cost.
							</p>

							<p>
								Conversations with the LLMs must be used for learning and instruction only.
							</p>

							<p>
								NYU PilotGenAI has been approved for usage of low risk data as defined by NYU's
								<a
									class="underline dark:text-gray-200"
									href={DATA_RISK_POLICY_URL}
									target="_blank"
									rel="noopener noreferrer"
								>
									Data Risk Classification Policy
								</a>
								.
							</p>

							<p>
								By clicking “Accept”, you agree to comply with NYU’s acceptable use policies and any NYU Pilot GenAI usage guidelines.
							</p>

							<ul class="space-y-1">
								<li>- Do not enter sensitive personal data</li>
								<li>- Do not share confidential or restricted data.</li>
								<li>- Use the system responsibly and for approved purposes only.</li>
							</ul>
						</div>
					</div>
				</div>

				<div class="mt-4 flex items-start gap-2 text-sm dark:text-gray-200">
					<input
						id="pilot-terms-check"
						type="checkbox"
						class="mt-0.5"
						bind:checked
					/>
					<label for="pilot-terms-check" class="select-none">
						{$i18n.t('I have read and agree to the Terms & Conditions.')}
					</label>
				</div>

				<div class="mt-6 mx-auto w-fit flex flex-col items-center gap-2">
					<button
						class="relative z-20 flex px-5 py-2 rounded-full bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={!checked || loading}
						on:click={onAccept}
					>
						{loading ? $i18n.t('Loading...') : $i18n.t('Accept')}
					</button>

					<button
						class="text-xs text-center w-full text-gray-400 underline"
						on:click={() => {
							localStorage.removeItem('token');
							location.href = '/auth';
						}}
					>
						{$i18n.t('Sign Out')}
					</button>
				</div>
			</div>
		</div>
	</div>
</div>




