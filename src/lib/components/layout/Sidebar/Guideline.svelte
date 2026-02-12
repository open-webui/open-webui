  <script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
</script>

<div class="w-full h-full overflow-y-auto px-4 sm:px-6 py-6">
	<!-- Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
			{$i18n.t('Guideline')}
		</h1>
		<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
			Please read the following guidelines to use the system properly.
		</p>
	</div>

	<!-- Main Card -->
	<div
		class="rounded-2xl border border-gray-200 dark:border-gray-800
		bg-white dark:bg-gray-900 shadow-sm p-5 sm:p-6 space-y-6"
	>
		<!-- Guideline Image -->
		<div class="flex justify-center">
			<img
				src="/guideline/guideline-user.png"
				alt="Guideline illustration"
				class="w-full max-w-md rounded-xl bg-gray-50
				dark:bg-gray-800 p-4 object-contain"
			/>
		</div>

		<!-- Section 1 -->
		<div>
			<h2 class="text-base font-semibold text-gray-900 dark:text-white mb-2">
				📌 General Rules
			</h2>
			<ul class="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
				<li>Use the system responsibly</li>
				<li>Do not share personal or sensitive information</li>
				<li>Respect community and platform rules</li>
			</ul>
		</div>

		<!-- Section 2 -->
		<div>
			<h2 class="text-base font-semibold text-gray-900 dark:text-white mb-2">
				💬 Chat Usage
			</h2>
			<ul class="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
				<li>Ask clear and meaningful questions</li>
				<li>Avoid spam or repeated messages</li>
				<li>Do not attempt to bypass system restrictions</li>
			</ul>
		</div>

		<!-- Section 3 -->
		<div>
			<h2 class="text-base font-semibold text-gray-900 dark:text-white mb-2">
				🔐 Account & Security
			</h2>
			<p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
				Keep your account secure. Never share your password or access token.
				If you notice suspicious behavior, please sign out and contact support.
			</p>
		</div>

		<!-- Tip Box -->
		<div
			class="rounded-xl border border-blue-200 dark:border-blue-900
			bg-blue-50 dark:bg-blue-950/30 p-4"
		>
			<p class="text-sm text-blue-800 dark:text-blue-300">
				💡 Tip: Following these guidelines ensures a better and safer experience for everyone.
			</p>
		</div>
	</div>
</div>
