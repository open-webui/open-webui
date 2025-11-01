<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import * as FocusTrap from 'focus-trap';
	
	export let show = true;
	export let onConsent: () => void = () => {};
	export let onDecline: () => void = () => {};
	export let consentVersion: string = '1.0.0';
	export let consentDate: string = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
	
	let modalElement = null;
	let mounted = false;
	let focusTrap: FocusTrap.FocusTrap | null = null;
	
	// Debug logging
	$: {
		console.log('[CONSENT MODAL DEBUG] show prop changed to:', show);
		console.log('[CONSENT MODAL DEBUG] modalElement exists:', !!modalElement);
	}
	
	// Prevent closing the modal - it must be blocking
	const handleKeyDown = (event: KeyboardEvent) => {
		// Prevent Escape key from closing modal
		if (event.key === 'Escape') {
			event.preventDefault();
			event.stopPropagation();
		}
	};
	
	const handleConsent = () => {
		onConsent();
	};
	
	const handleDecline = () => {
		onDecline();
	};
	
	onMount(() => {
		console.log('[CONSENT MODAL DEBUG] ConsentModal component mounted, show =', show);
		mounted = true;
	});
	
	$: if (show && modalElement) {
		console.log('[CONSENT MODAL DEBUG] Activating modal - show=true, modalElement exists');
		try {
			focusTrap = FocusTrap.createFocusTrap(modalElement);
			focusTrap.activate();
			console.log('[CONSENT MODAL DEBUG] Focus trap activated');
			window.addEventListener('keydown', handleKeyDown);
			document.body.style.overflow = 'hidden';
			console.log('[CONSENT MODAL DEBUG] Modal should now be visible in DOM');
		} catch (error) {
			console.error('[CONSENT MODAL DEBUG] Error activating modal:', error);
		}
	} else if (!show && modalElement) {
		console.log('[CONSENT MODAL DEBUG] Deactivating modal - show=false');
		focusTrap?.deactivate();
		window.removeEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'unset';
	}
	
	onDestroy(() => {
		console.log('[CONSENT MODAL DEBUG] Component destroying');
		if (focusTrap) {
			focusTrap.deactivate();
		}
		window.removeEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'unset';
	});
</script>

{#if show}
	<!-- Blocking modal - cannot be dismissed by clicking outside -->
	<div
		bind:this={modalElement}
		aria-modal="true"
		role="dialog"
		aria-labelledby="consent-title"
		aria-describedby="consent-content"
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black/30 dark:bg-black/60 w-full h-screen max-h-[100dvh] p-3 flex justify-center z-[99999] overflow-y-auto overscroll-contain"
		in:fade={{ duration: 200 }}
	>
		<div
			class="m-auto max-w-full w-[56rem] mx-2 shadow-3xl min-h-fit scrollbar-hidden bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm rounded-4xl border border-white dark:border-gray-850"
			in:flyAndScale
		>
			<div class="p-8 max-h-[90vh] overflow-y-auto" id="consent-content">
				<div class="mb-4">
					<h2 id="consent-title" class="text-2xl font-bold dark:text-gray-100">
						Consent to Participate in Research (Information Sheet)
					</h2>
				</div>
				
				<div class="text-xs text-gray-600 dark:text-gray-400 mb-6 pb-4 border-b border-gray-300 dark:border-gray-700">
					Version: {consentVersion} • Date: {consentDate}
				</div>
				
				<div class="space-y-6 text-base dark:text-gray-200 leading-relaxed">
					<div>
						<p class="font-semibold mb-2">Study Title.</p>
						<p>Parents' Moderation Preferences for Children's Use of Generative AI</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Principal Investigator.</p>
						<p>Haojian Jin, Ph.D., Assistant Professor, Halıcıoğlu Data Science Institute, UC San Diego</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Contact.</p>
						<p>
							<a href="mailto:childai.research.ucsd@gmail.com" class="text-blue-600 dark:text-blue-400 underline">childai.research.ucsd@gmail.com</a>
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">IRB.</p>
						<p>
							UC San Diego Office of IRB Administration: 
							<a href="tel:858-246-4777" class="text-blue-600 dark:text-blue-400 underline">858-246-4777</a>
							{' • '}
							<a href="mailto:irb@ucsd.edu" class="text-blue-600 dark:text-blue-400 underline">irb@ucsd.edu</a>
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">What is this study about?</p>
						<p>
							We study how parents want to moderate their children's interactions with generative AI (e.g., ChatGPT). 
							You are eligible because you are a parent or legal guardian of a child aged <strong>9–18</strong>.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">What will I do?</p>
						<p>
							You will complete a <strong>web survey (~15–20 minutes)</strong> hosted in this app. 
							You will see brief scenarios of children using AI and indicate how you would want the AI to respond or be moderated. 
							You may answer a few open-ended questions and brief demographics.
						</p>
						<p class="mt-2">
							You <strong>may optionally repeat</strong> the survey <strong>once per day for up to 5 days</strong>; 
							each day is a separate, voluntary session.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">What data do you collect?</p>
						<ul class="list-disc list-inside space-y-1 ml-2">
							<li>Your survey responses and interactions in the tool (e.g., choices, typed text, timestamps).</li>
							<li>Your <strong>Prolific ID</strong> (passed via the URL) to manage payment and prevent duplicate entries.</li>
							<li>We <strong>do not</strong> ask for your name. <strong>Please do not include names or other identifying details about you or your child</strong> in any free-text responses.</li>
						</ul>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Risks and discomforts</p>
						<p>
							Risks are <strong>minimal</strong> (similar to everyday online questionnaires). 
							Some scenarios may mention sensitive themes (e.g., violence, sex, self-harm) and could feel uncomfortable. 
							You may skip any question or stop at any time.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Benefits</p>
						<p>
							You will not directly benefit. Findings may inform safer, more parent-aligned AI moderation tools.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Compensation</p>
						<p>
							For each completed daily session, you will receive <strong>$4.00 base</strong> via Prolific. 
							You <strong>may earn up to an additional $2.00 bonus</strong> for thoughtful, complete answers and engaged use of the moderation tool, 
							as described on the study page. Each day's payment (base + any bonus) is processed <strong>separately</strong> via Prolific.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Confidentiality</p>
						<p>
							We label study data with a code (not your name). We store data on secure UC San Diego systems and restrict access to the research team. 
							We will report results in aggregate and may share <strong>de-identified</strong> data for research and publication. 
							We retain data per UC San Diego policy and sponsor requirements.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Voluntary participation</p>
						<p>
							Participation is <strong>voluntary</strong>. You may decline or withdraw at any time without penalty or loss of benefits. 
							If you choose <strong>not</strong> to participate, select <strong>"I Do Not Consent"</strong> to return to Prolific.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Questions</p>
						<p>
							If you have questions about the study, contact us at 
							<a href="mailto:childai.research.ucsd@gmail.com" class="text-blue-600 dark:text-blue-400 underline">childai.research.ucsd@gmail.com</a>. 
							For questions about your rights as a participant, contact the <strong>UCSD IRB</strong> at 
							<a href="tel:858-246-4777" class="text-blue-600 dark:text-blue-400 underline">858-246-4777</a> or 
							<a href="mailto:irb@ucsd.edu" class="text-blue-600 dark:text-blue-400 underline">irb@ucsd.edu</a>.
						</p>
					</div>
					
					<div>
						<p class="font-semibold mb-2">Electronic consent (California)</p>
						<p>
							You may request or retain a copy of this consent in non-electronic form. You may provide consent in non-electronic form. 
							If you later withdraw your electronic consent, a copy of it will be kept for regulatory purposes.
						</p>
						<p class="mt-2">
							You can request a document version of this consent form and a receipt of your consent by emailing us at 
							<a href="mailto:childai.research.ucsd@gmail.com" class="text-blue-600 dark:text-blue-400 underline">childai.research.ucsd@gmail.com</a>.
						</p>
					</div>
					
					<div class="border-t border-gray-300 dark:border-gray-700 pt-6 mt-6">
						<p class="font-semibold mb-4 text-base">Do you consent to participate?</p>
						
						<div class="flex flex-col sm:flex-row gap-4">
							<button
								on:click={handleConsent}
								class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors"
							>
								I Consent, Begin
							</button>
							<button
								on:click={handleDecline}
								class="flex-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 font-medium py-3 px-6 rounded-lg transition-colors"
							>
								I Do Not Consent
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

