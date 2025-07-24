<script>
	import { goto } from '$app/navigation';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	function goBack() {
		goto('/auth');
	}
</script>

<div class="w-full min-h-screen dark bg-[#010E1D] flex items-start justify-center p-6 pt-16">
	<!-- Back arrow for small devices -->
	<button
		on:click={goBack}
		class="fixed top-4 left-4 z-10 p-2 text-white hover:text-gray-300 transition-colors md:hidden"
		aria-label="Go back"
	>
		<ChevronLeft className="w-6 h-6" strokeWidth="2" />
	</button>

	<div class="max-w-4xl text-left">
		<h1 class="text-2xl text-white mb-4">Terms & conditions</h1>
		<p
			class="mb-4 font-inter text-xs font-normal leading-4 tracking-[0.12px]"
			style="color: var(--Typography-Body-subtext, #979EAD);"
		>
			By accessing and using GovGPT, you agree to use the platform responsibly and in accordance
			with applicable government policies and data privacy laws. GovGPT is an AI-powered assistant
			designed to support government employees with general information, internal knowledge, and
			services. It is intended for professional use only and should not be used to make final
			decisions without human verification or consultation with authorized personnel.
		</p>
		<p
			class="mb-4 font-inter text-xs font-normal leading-4 tracking-[0.12px]"
			style="color: var(--Typography-Body-subtext, #979EAD);"
		>
			Please note that GovGPT may generate content based on patterns in data and language models.
			While we strive for accuracy, the responses may occasionally contain outdated, incomplete, or
			incorrect information. Users are advised to verify critical details through official
			government sources or department heads before taking action. GovGPT does not store or retain
			any personal data beyond what is necessary for session continuity, in line with government
			data protection policies.
		</p>
		<p
			class="mb-4 font-inter text-xs font-normal leading-4 tracking-[0.12px]"
			style="color: var(--Typography-Body-subtext, #979EAD);"
		>
			The use of GovGPT must align with your department's acceptable use guidelines. Any misuse,
			including attempts to extract sensitive information, manipulate responses, or breach internal
			security protocols, will be subject to investigation and disciplinary action. By continuing to
			use the platform, you acknowledge these terms and accept full responsibility for the
			appropriate and ethical use of the system. By accessing and using GovGPT, you agree to use the
			platform responsibly and in accordance with applicable government policies and data privacy
			laws. GovGPT is an AI-powered assistant designed to support government employees with general
			information, internal knowledge, and services. It is intended for professional use only and
			should not be used to make final decisions without human verification or consultation with
			authorized personnel.
		</p>
		<p
			class="mb-4 font-inter text-xs font-normal leading-4 tracking-[0.12px]"
			style="color: var(--Typography-Body-subtext, #979EAD);"
		>
			Please note that GovGPT may generate content based on patterns in data and language models.
			While we strive for accuracy, the responses may occasionally contain outdated, incomplete, or
			incorrect information. Users are advised to verify critical details through official
			government sources or department heads before taking action. GovGPT does not store or retain
			any personal data beyond what is necessary for session continuity, in line with government
			data protection policies.
		</p>
		<p
			class="mb-4 font-inter text-xs font-normal leading-4 tracking-[0.12px]"
			style="color: var(--Typography-Body-subtext, #979EAD);"
		>
			The use of GovGPT must align with your department's acceptable use guidelines. Any misuse,
			including attempts to extract sensitive information, manipulate responses, or breach internal
			security protocols, will be subject to investigation and disciplinary action. By continuing to
			use the platform, you acknowledge these terms and accept full responsibility for the
			appropriate and ethical use of the system.
		</p>
	</div>
</div>
