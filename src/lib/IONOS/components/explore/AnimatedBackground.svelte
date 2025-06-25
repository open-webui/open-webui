<!--
Animates two blurred background gradients with rotating animation.
Both "blobs" change shape, rotation.
Two different blobs rotate with two different rates and rotation
offsets to create a "beating" effect.
-->
<div class="overflow-hidden">
	<div class="animated"></div>
	<div class="animated config-2"></div>
</div>

<style>
	@property --blob-color-1 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --blob-color-2 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --blob-color-3 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --blob-color-4 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	/* Inspired by https://codepen.io/wilvander/pen/KKQrGgP */
	.animated {
		--blob-offset-x: 10vw;
		--blob-offset-y: 5vh;
		--blob-rotation-offset: 90deg;
		--speed: 50s;

		--blob-color-1: hsla(311.26deg 100% 34.33% / 10%);
		--blob-color-2: hsla(222.68deg 59.99% 36.91% / 10%);
		--blob-color-3: hsla(186deg 60% 37% / 10%);
		--blob-color-4: hsla(0deg 100% 100% / 100%);

		--size: 500px;
		--easing: cubic-bezier(0.8, 0.2, 0.2, 0.8);

		user-select: none;
		position: absolute;
		top: var(--blob-offset-y);
		right: var(--blob-offset-x);
		width: 900px;
		height: 900px;
		z-index: -1;

		background-image: radial-gradient(var(--blob-color-4), var(--blob-color-1), #fff, var(--blob-color-2), var(--blob-color-3), var(--blob-color-4));

		animation: rotate var(--speed) var(--easing) alternate infinite;

		filter: blur(calc(var(--size) / 8));
		border-radius: 10% 60% 90% 10% / 10% 20% 90% 90%;

		transition: all 0.5s ease-out;
	}

	.config-2 {
		--blob-offset-x: 5vw;
		--blob-offset-y: 5vh;
		--blob-rotation-offset: 150deg;
		--speed: 65s;
		width: 700px;
		height: 1000px;
	}

	@keyframes rotate {
		0% {
			transform: rotate(calc(0deg + var(--blob-rotation-offset)));
			height: min(60vw, 700px);
		}
		50% {
			transform: rotate(calc(180deg + var(--blob-rotation-offset)));
			height: min(50vw, 500px);
		}
		100% {
			transform: rotate(calc(360deg + var(--blob-rotation-offset)));
			height: min(60vw, 700px);
		}
	}
</style>
