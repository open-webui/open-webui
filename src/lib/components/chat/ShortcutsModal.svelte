<script lang="ts">
	import Modal from '../common/Modal.svelte';

	export let show = false;

	const faqs = [
  {
    id: 1,
    question: "What's the best thing about Switzerland?",
    answer:
      "I don't know, but the flag is a big plus. Lorem ipsum dolor sit amet consectetur adipisicing elit. Quas cupiditate laboriosam fugiat.",
  },
  // More questions...
]

</script>

<Modal bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 py-4">
			<div class=" text-lg font-medium self-center">Shortcuts</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<hr class=" dark:border-gray-800" />

		<div class="flex flex-col md:flex-row w-full p-5 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<div class="flex flex-col space-y-3 w-full self-start">
					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Neuen Chat öffnen</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Strg /⌘
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Shift
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								O
							</div>
						</div>
					</div>

					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Chat Input fokussieren</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Shift
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Esc
							</div>
						</div>
					</div>

					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Letzten Code kopieren</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
							Strg/⌘
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Shift
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								;
							</div>
						</div>
					</div>

					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Letzte Antwort kopieren</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
							Strg /⌘
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Shift
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								C
							</div>
						</div>
					</div>
				</div>

				<div class="flex flex-col space-y-3 w-full self-start">
					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Einstellungen aufrufen</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
							Strg /⌘
							</div>
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								.
							</div>
						</div>
					</div>

					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Sidebar ein-/ausblenden</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
							Strg /⌘
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Shift
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								S
							</div>
						</div>
					</div>

					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Chat löschen</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
							Strg /⌘
							</div>
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								Shift
							</div>

							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								⌫
							</div>
						</div>
					</div>

					<div class="w-full flex justify-between items-center">
						<div class=" text-sm">Shortcuts anzeigen</div>

						<div class="flex space-x-1 text-xs">
							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
							Strg /⌘
							</div>


							<div
								class=" h-fit py-1 px-2 flex items-center justify-center rounded border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
							>
								/
							</div>
							
						</div>
						
					</div>
				</div>
				
			</div>
			
		</div>
		<!--
		<div class=" flex justify-between dark:text-gray-300 px-1 py-1">
				<div class="mx-auto max-w-7xl divide-y divide-gray-900/10 px-1 py-1">
				  <h2 class="text-2xl font-bold leading-10 tracking-tight text-gray-900">Frequently asked questions</h2>
				  <dl class="mt-10 space-y-8 divide-y divide-gray-900/10">
					<div class="pt-8 lg:grid lg:grid-cols-12 lg:gap-8">
					  <dt class="text-base font-semibold leading-7 text-gray-900 lg:col-span-5">Warum ist die Antwortgenerierung teilweise langsam?</dt>
					  <dd class="mt-4 lg:col-span-7 lg:mt-0">
						<p class="text-base leading-7 text-gray-600">Da die LLM (Large Language Modelle) derzeit aus Konzeptgründen nur auf CPU Processing zurückgreifen können, ist die Geschwindigkeit eingeschränkt.</p>
					  </dd>
					  <dt class="text-base font-semibold leading-7 text-gray-900 lg:col-span-5">Welches Modell ist für was gut?</dt>
					  <dd class="mt-4 lg:col-span-7 lg:mt-0">
						<p class="text-base leading-7 text-gray-600">Es gibt unterschiedliche Open Source Modelle die für unterschiedliche zwecke trainiert wurden. LLama2 Modelle (von Meta) verstehen in der Regel am besten deutsch. Mistral ist für seine kompakte größe (um die 4GB) sehr gut, schneidet besser ab als Llama2 hat aber manchmal Schwierigkeiten deutsch zu verstehen. Codellama ist für Code spezifische Tasks (z.B. Codegenerieruing) bestens geeignet. Mixtral das größere Model von Mistral und derzeit eines der besten Modelle, braucht aufgrund seiner Größe aber mehr Rechenleistung -> langsamere Antworten.</p>
					  </dd>
					  <dt class="text-base font-semibold leading-7 text-gray-900 lg:col-span-5">Läuft die Anwendung wirklch 100% bei der FI-TS?</dt>
					  <dd class="mt-4 lg:col-span-7 lg:mt-0">
						<p class="text-base leading-7 text-gray-600">Ja! Sowohl das Frontend als auch der bedeutende Backend (Das Sprachmodell) läuft zu 100% auf FI-TS Rechenzentren.</p>
					  </dd>
			  
					 More questions... 
				  </dl>
				</div>
			  </div>
			-->
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
