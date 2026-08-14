<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	type AskUserOption = {
		label: string;
		description: string;
	};

	type AskUserQuestion = {
		id: string;
		header: string;
		question: string;
		options: AskUserOption[];
		allow_other?: boolean;
	};

	type DraftAnswer =
		| {
				type: 'option';
				option_index: number;
				label: string;
				description: string;
		  }
		| {
				type: 'other';
				text: string;
		  };

	export let show = false;
	export let questions: AskUserQuestion[] = [];
	export let allowOther = true;

	let answers: Record<string, DraftAnswer> = {};
	let questionIndex = 0;
	let wasOpen = false;

	$: if (show && !wasOpen) {
		answers = {};
		questionIndex = 0;
		wasOpen = true;
	}

	$: if (!show && wasOpen) {
		wasOpen = false;
	}

	const questionAllowsOther = (question: AskUserQuestion) => question.allow_other ?? allowOther;

	$: question = questions[questionIndex];
	$: selectedAnswer = question ? answers[question.id] : undefined;

	const hasAnswers = (selected = answers) =>
		questions.length > 0 &&
		questions.every((question) => {
			const answer = selected[question.id];
			return answer?.type === 'option' || (answer?.type === 'other' && answer.text.trim() !== '');
		});

	$: complete = hasAnswers();

	const submit = (selected = answers) => {
		if (!hasAnswers(selected)) {
			return;
		}

		const normalized: Record<string, DraftAnswer> = {};
		for (const question of questions) {
			const answer = selected[question.id];
			if (answer?.type === 'option') {
				normalized[question.id] = answer;
			} else if (answer?.type === 'other') {
				normalized[question.id] = {
					type: 'other',
					text: answer.text.trim()
				};
			}
		}

		show = false;
		dispatch('confirm', {
			status: 'answered',
			answers: normalized
		});
	};

	const advance = (selected = answers) => {
		if (questionIndex < questions.length - 1) {
			questionIndex += 1;
		} else if (hasAnswers(selected)) {
			submit(selected);
		}
	};

	const selectOption = (question: AskUserQuestion, option: AskUserOption, index: number) => {
		const selected: Record<string, DraftAnswer> = {
			...answers,
			[question.id]: {
				type: 'option',
				option_index: index,
				label: option.label,
				description: option.description
			}
		};
		answers = selected;
		advance(selected);
	};

	const selectOther = (question: AskUserQuestion) => {
		const existing = answers[question.id];
		answers = {
			...answers,
			[question.id]: {
				type: 'other',
				text: existing?.type === 'other' ? existing.text : ''
			}
		};
	};

	const updateOther = (question: AskUserQuestion, text: string) => {
		answers = {
			...answers,
			[question.id]: {
				type: 'other',
				text
			}
		};
	};

	const isSelectedOption = (question: AskUserQuestion, index: number) => {
		const answer = answers[question.id];
		return answer?.type === 'option' && answer.option_index === index;
	};

	const isSelectedOther = (question: AskUserQuestion) => answers[question.id]?.type === 'other';

	const otherText = (question: AskUserQuestion) => {
		const answer = answers[question.id];
		return answer?.type === 'other' ? answer.text : '';
	};
</script>

{#if show}
	<section class="my-1 rounded-2xl bg-gray-100/70 px-3.5 py-3 dark:bg-white/[0.055]">
		<div class="mb-3 flex items-center justify-between gap-3">
			<div class="text-[0.6875rem] font-medium tracking-wide text-gray-500 dark:text-gray-400">
				{$i18n.t('Planning question')}
			</div>
			<div class="text-[0.6875rem] text-gray-500 dark:text-gray-400">
				{$i18n.t('Question')}
				{questionIndex + 1}
				{$i18n.t('of')}
				{questions.length} ·
				{$i18n.t('Paused while visible')}
			</div>
		</div>

		<div class="space-y-2.5">
			{#if question}
				{#key question.id}
					<div class="space-y-2.5">
						<div>
							<div class="text-sm font-medium tracking-[-0.01em] text-gray-900 dark:text-gray-100">
								{question.header}
							</div>
							<div class="mt-1 text-xs leading-relaxed text-gray-600 dark:text-gray-300">
								{question.question}
							</div>
						</div>

						<div class="space-y-0.5">
							{#each question.options || [] as option, optionIndex}
								<!-- svelte-ignore a11y_click_events_have_key_events -->
								<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
								<label
									class="flex cursor-pointer items-start gap-2.5 rounded-xl px-2.5 py-1.5 transition-colors {isSelectedOption(
										question,
										optionIndex
									)
										? 'bg-white shadow-sm dark:bg-white/[0.1]'
										: 'hover:bg-white/70 dark:hover:bg-white/[0.06]'}"
									on:click={() => isSelectedOption(question, optionIndex) && advance()}
								>
									<input
										class="sr-only"
										type="radio"
										name={question.id}
										value={option.label}
										checked={isSelectedOption(question, optionIndex)}
										on:change={() => selectOption(question, option, optionIndex)}
									/>
									<span
										class="mt-1 flex size-3.5 shrink-0 items-center justify-center rounded-full border {isSelectedOption(
											question,
											optionIndex
										)
											? 'border-gray-900 dark:border-white'
											: 'border-gray-300 dark:border-white/25'}"
									>
										{#if isSelectedOption(question, optionIndex)}
											<span class="size-1.5 rounded-full bg-gray-900 dark:bg-white"></span>
										{/if}
									</span>
									<span class="min-w-0 text-xs">
										<span class="text-gray-800 dark:text-gray-100">{option.label}</span>
										{#if optionIndex === 0}
											<span class="ml-1.5 text-[0.625rem] text-gray-400 dark:text-gray-500">
												{$i18n.t('Recommended')}
											</span>
										{/if}
										<span class="mt-0.5 block leading-relaxed text-gray-500 dark:text-gray-400">
											{option.description}
										</span>
									</span>
								</label>
							{/each}

							{#if questionAllowsOther(question)}
								<label
									class="flex cursor-pointer items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-xs transition-colors {isSelectedOther(
										question
									)
										? 'bg-white shadow-sm dark:bg-white/[0.1]'
										: 'hover:bg-white/70 dark:hover:bg-white/[0.06]'}"
								>
									<input
										class="sr-only"
										type="radio"
										name={question.id}
										value="__other__"
										checked={isSelectedOther(question)}
										on:change={() => selectOther(question)}
									/>
									<span
										class="flex size-3.5 shrink-0 items-center justify-center rounded-full border {isSelectedOther(
											question
										)
											? 'border-gray-900 dark:border-white'
											: 'border-gray-300 dark:border-white/25'}"
									>
										{#if selectedAnswer?.type === 'other'}
											<span class="size-1.5 rounded-full bg-gray-900 dark:bg-white"></span>
										{/if}
									</span>
									<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Other')}</span>
								</label>
								{#if selectedAnswer?.type === 'other'}
									<input
										class="w-full rounded-xl bg-transparent px-2.5 py-1.5 text-xs text-gray-800 outline-none placeholder:text-gray-400 dark:text-gray-100 dark:placeholder:text-gray-500"
										placeholder={$i18n.t('Type your answer')}
										value={otherText(question)}
										on:input={(event) =>
											updateOther(question, (event.currentTarget as HTMLInputElement).value)}
									/>
								{/if}
							{/if}
						</div>
					</div>
				{/key}
			{/if}

			<div class="flex items-center justify-between gap-2 pt-0.5">
				<button
					type="button"
					class="rounded-lg px-2.5 py-1.5 text-xs text-gray-500 transition-colors hover:bg-white/70 hover:text-gray-800 disabled:opacity-30 dark:text-gray-400 dark:hover:bg-white/10 dark:hover:text-gray-100"
					disabled={questionIndex === 0}
					on:click={() => (questionIndex -= 1)}
				>
					{$i18n.t('Previous')}
				</button>
				{#if questionIndex < questions.length - 1}
					<button
						type="button"
						class="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-gray-800 active:scale-[0.98] dark:bg-white dark:text-black dark:hover:bg-white/90"
						on:click={() => (questionIndex += 1)}
					>
						{$i18n.t('Next')}
					</button>
				{:else}
					<button
						type="button"
						class="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-gray-800 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-black dark:hover:bg-white/90"
						disabled={!complete}
						on:click={() => submit()}
					>
						{$i18n.t('Submit answers')}
					</button>
				{/if}
			</div>
		</div>
	</section>
{/if}
