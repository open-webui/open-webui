<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	export let show = true;
	export let getStartedHandler = () => {};

	let videoElement;
	let playOnInteractionRegistered = false;

	function playBackgroundVideo() {
		if (!videoElement) {
			return;
		}

		videoElement.play().catch(() => {
			if (playOnInteractionRegistered) {
				return;
			}

			playOnInteractionRegistered = true;

			const playOnInteraction = () => {
				videoElement.play().catch(() => {});
				document.removeEventListener('click', playOnInteraction);
				document.removeEventListener('touchstart', playOnInteraction);
				playOnInteractionRegistered = false;
			};

			document.addEventListener('click', playOnInteraction);
			document.addEventListener('touchstart', playOnInteraction);
		});
	}

	$: if (show && videoElement) {
		playBackgroundVideo();
	}
</script>

{#if show}
	<div class="relative h-screen max-h-[100dvh] w-full overflow-hidden text-white">
		<div class="fixed top-6 left-6 z-50 sm:top-10 sm:left-10">
			<img
				id="logo"
				crossorigin="anonymous"
				src="/static/favicon.png"
				class="size-6 rounded-full"
				alt="logo"
			/>
		</div>

		<video
			bind:this={videoElement}
			class="absolute inset-0 h-full w-full object-cover"
			src="/assets/welcome.mp4"
			autoplay
			muted
			loop
			playsinline
			preload="auto"
			poster="/assets/welcome.webp"
			aria-hidden="true"
		></video>

		<div class="absolute inset-0 bg-linear-to-t from-black/80 via-black/20 to-transparent"></div>
		<div class="absolute inset-0 bg-linear-to-r from-black/50 via-black/10 to-transparent"></div>

		<div class="relative z-10 flex h-screen max-h-[100dvh] w-full">
			<div class="flex w-full flex-col justify-end px-6 pb-8 sm:px-10 sm:pb-10 lg:px-16 lg:pb-14">
				<div class="max-w-3xl">
					<div class="mb-4 text-[11px] font-medium tracking-[0.18em] uppercase opacity-35">
						Open WebUI
					</div>

					<h1 class="m-0 max-w-3xl text-2xl leading-[1.15] font-light tracking-tight lg:text-4xl">
						{$i18n.t('Welcome to your AI home.')}
					</h1>

					<p class="mt-6 max-w-xl text-sm leading-relaxed font-light text-white/60 lg:text-base">
						{$i18n.t(
							'Run AI on your own terms. Connect any model, extend with code, and protect what matters without compromise. Your models, your data, your machine, wherever you open it.'
						)}
					</p>

					<div class="mt-8 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:gap-7">
						<button
							aria-label={$i18n.t('Get started')}
							class="group relative z-20 inline-flex min-w-40 items-center justify-center gap-2 bg-white px-8 py-3 text-sm font-normal text-black transition hover:bg-white/90 focus:ring-2 focus:ring-white/50 focus:outline-hidden"
							on:click={() => {
								getStartedHandler();
							}}
						>
							{$i18n.t('Get started')}
							<svg
								class="h-4 w-4 transition group-hover:translate-x-0.5"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="1.5"
								aria-hidden="true"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
							</svg>
						</button>

						<a
							class="inline-flex items-center text-sm text-white/60 transition hover:text-white"
							href="https://docs.openwebui.com/"
							target="_blank"
							rel="noopener noreferrer"
						>
							{$i18n.t('Read the docs')}
						</a>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
