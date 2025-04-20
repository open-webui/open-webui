<script lang="ts">
	import Modal from './common/Modal.svelte';
	import { Confetti } from 'svelte-confetti';
	import { showHowToUse } from '$lib/stores';

	export let show = false;
</script>

<Modal bind:show size="lg">
	<div class="px-5 pt-4 dark:text-gray-300 text-gray-700">
		<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
		<div class="flex justify-between items-center">
			<div class="text-xl font-semibold">
				HKUST Open WebUI - [Open Beta]
			</div>
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
	</div>

	<div class="w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class="overflow-y-scroll max-h-96 scrollbar-hidden">
			<div class="mb-3 text-center">
				<p class="mb-4">
					<b>HKUST Open WebUI</b> 오픈베타에 참여해주셔서 감사합니다. 
				</p>
				<p class="mb-4">
					<b>HKUST Open WebUI</b>는 <span class="underline">학교의 공식 문서를 자연어로 검색 할 수 있는 기능과</span>
				</p>
				<p class="mb-4">
					<span class="underline">Open AI에서 제공하는 GPT-4o, GPT-4o-mini 모델</span>을 UST에서 제공하는 API를 통해 제공합니다.
				</p>
				<p class="mb-4">
					서비스 이용 방법에 대한 안내는 화면 오른쪽 상단의 <b>"이용 방법"</b> 섹션을 참고해 주세요.
				</p>
				<p class="mb-4">
					UST 재학생 여러분의 편의를 위해 제작된 서비스인 만큼, <b>피드백</b>을 주시면 적극 반영하도록 하겠습니다.
				</p>

				<div class="pt-4">
					<button
						on:click={() => {
							showHowToUse.set(true);
							show = false;
						}}
						class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
					>
						How to Use
					</button>
				</div>

				<p class="mt-6 text-sm text-gray-500 dark:text-gray-400">
					KSA MergeFeat
				</p>
			</div>
		</div>
	</div>
</Modal> 