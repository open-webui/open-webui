<script lang="ts">
	import { learningSession } from '$lib/stores/learning';
	import QuizResultCard from './Messages/QuizResultCard.svelte';

	// 목업 퀴즈 데이터
	const quizData = [
		{
			question: '다음 중 라플라스 변환이 옳은 것은?',
			choices: ['L{e^at} = 1/(s−a)', 'L{sin(t)} = s/(s²+1)', 'L{t} = 1/s²', 'L{1} = s'],
			correctIndex: 0,
			explanation: 'L{e^at} = 1/(s−a) 는 지수함수의 라플라스 변환 기본 공식입니다. 단, s > a 조건이 필요합니다.'
		},
		{
			question: '푸리에 급수에서 짝함수(even function) f(x)의 사인 계수 bₙ은?',
			choices: ['bₙ = 0', 'bₙ = aₙ', 'bₙ = 2/L ∫f(x)sin(nπx/L)dx', 'bₙ = 1/π'],
			correctIndex: 0,
			explanation: '짝함수는 f(−x) = f(x)이므로 sin 항은 모두 소거되어 bₙ = 0입니다.'
		},
		{
			question: '벡터 A와 B의 외적 A×B의 크기는?',
			choices: ['|A||B|sinθ', '|A||B|cosθ', '|A|+|B|', '|A|−|B|'],
			correctIndex: 0,
			explanation: '외적의 크기는 두 벡터가 이루는 평행사변형의 넓이, 즉 |A||B|sinθ입니다.'
		}
	];

	let currentIndex = 0;
	let selectedChoice: number | null = null;
	let submitted = false;

	$: question = quizData[currentIndex];
	$: progress = ((currentIndex) / quizData.length) * 100;

	function select(i: number) {
		if (submitted) return;
		selectedChoice = i;
	}

	function submit() {
		if (selectedChoice === null) return;
		submitted = true;
	}

	function next() {
		if (currentIndex < quizData.length - 1) {
			currentIndex++;
			selectedChoice = null;
			submitted = false;
		} else {
			learningSession.update((s) => ({ ...s, mode: 'default', quizActive: false }));
		}
	}

	function exitQuiz() {
		learningSession.update((s) => ({ ...s, mode: 'default', quizActive: false }));
	}
</script>

<div class="rounded-xl border border-purple-200 dark:border-purple-800/50 overflow-hidden mb-3">
	<!-- 헤더 -->
	<div class="bg-purple-50 dark:bg-purple-950/30 px-4 py-2.5 flex items-center gap-2 border-b border-purple-200 dark:border-purple-800/40">
		<span class="text-purple-500">📝</span>
		<span class="text-sm font-semibold text-purple-900 dark:text-purple-200">퀴즈 모드</span>
		<span class="ml-auto text-xs text-purple-500 dark:text-purple-400">문제 {currentIndex + 1} / {quizData.length}</span>
		<button class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition ml-2" on:click={exitQuiz}>나가기</button>
	</div>

	<!-- 진행 바 -->
	<div class="h-1 bg-purple-100 dark:bg-purple-900/30">
		<div class="h-full bg-purple-400 dark:bg-purple-500 transition-all duration-500" style="width: {progress}%"></div>
	</div>

	{#if !submitted}
		<!-- 문제 -->
		<div class="px-4 py-4 bg-white dark:bg-gray-900/50">
			<p class="text-sm font-medium text-gray-800 dark:text-gray-200 mb-3">Q. {question.question}</p>
			<div class="flex flex-col gap-2">
				{#each question.choices as choice, i}
					<button
						class="text-left text-sm px-3 py-2.5 rounded-lg border transition
							{selectedChoice === i
								? 'bg-purple-600 border-purple-600 text-white'
								: 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-purple-50 dark:hover:bg-purple-950/20 hover:border-purple-300'}"
						on:click={() => select(i)}
					>
						<span class="font-medium mr-1.5 opacity-70">{['①', '②', '③', '④'][i]}</span>{choice}
					</button>
				{/each}
			</div>
		</div>
		<div class="px-4 py-3 bg-purple-50 dark:bg-purple-950/20 border-t border-purple-100 dark:border-purple-800/30 flex justify-end">
			<button
				class="px-4 py-1.5 rounded-lg text-sm font-medium transition
					{selectedChoice !== null ? 'bg-purple-600 hover:bg-purple-700 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'}"
				disabled={selectedChoice === null}
				on:click={submit}
			>
				제출
			</button>
		</div>
	{:else}
		<!-- 결과 -->
		<div class="p-4 bg-white dark:bg-gray-900/50">
			<QuizResultCard
				isCorrect={selectedChoice === question.correctIndex}
				explanation={question.explanation}
				correctIndex={question.correctIndex}
				{selectedChoice}
				choices={question.choices}
				onNext={next}
				onExit={exitQuiz}
				isLast={currentIndex === quizData.length - 1}
			/>
		</div>
	{/if}
</div>
