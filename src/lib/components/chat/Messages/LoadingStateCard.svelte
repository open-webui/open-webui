<script lang="ts">
	export let state: 'analyzing' | 'explaining' | 'graphing' = 'analyzing';

	const STATE_CONFIG = {
		analyzing: {
			icon: '⚫',
			title: '요청 해석 중',
			subtitle: '어떤 내용을 물어보셨는지 파악하고 있어요'
		},
		explaining: {
			icon: '📝',
			title: '해설 생성 중',
			subtitle: '단계별 풀이와 개념 설명을 작성하고 있어요'
		},
		graphing: {
			icon: '📊',
			title: '그래프 생성 중',
			subtitle: '개념을 시각화한 그래프를 그리고 있어요'
		}
	} as const;

	$: config = STATE_CONFIG[state];
</script>

<div
	class="flex flex-col gap-1 px-4 py-3
		bg-white/70 dark:bg-gray-800/70
		border border-gray-200/30 dark:border-gray-200/20
		shadow-sm backdrop-blur-md rounded-2xl
		w-fit min-w-[15rem]"
>
	<!-- Top row: icon + title + animated dots -->
	<div class="flex items-center justify-between gap-3">
		<div class="flex items-center gap-2">
			<span class="text-base leading-none">{config.icon}</span>
			<span class="text-sm font-semibold text-gray-900 dark:text-gray-50">
				{config.title}
			</span>
		</div>
		<div class="dots-indicator flex items-center gap-[3px]">
			<span class="dot"></span>
			<span class="dot"></span>
			<span class="dot"></span>
		</div>
	</div>
	<!-- Subtitle -->
	<p class="text-xs text-gray-500 dark:text-gray-400 pl-[1.625rem]">
		{config.subtitle}
	</p>
</div>

<style>
	.dot {
		display: inline-block;
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background-color: #8d96ad;
		opacity: 0.3;
		animation: dot-pulse 1.4s ease-in-out infinite;
	}

	:global(.dark) .dot {
		background-color: #9ca3af;
	}

	.dot:nth-child(1) {
		animation-delay: 0s;
	}
	.dot:nth-child(2) {
		animation-delay: 0.22s;
	}
	.dot:nth-child(3) {
		animation-delay: 0.44s;
	}

	@keyframes dot-pulse {
		0%,
		80%,
		100% {
			opacity: 0.25;
			transform: scale(0.85);
		}
		40% {
			opacity: 1;
			transform: scale(1);
		}
	}
</style>
