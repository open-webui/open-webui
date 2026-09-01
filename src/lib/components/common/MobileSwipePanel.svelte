<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	const UNSAFE_EDGE = 16;
	const SWIPE_SLOP = 8;
	const AXIS_RATIO = 1.2;
	const FLICK_VELOCITY = 0.55;
	const SETTLE_MS = 210;

	export let open = false;
	export let enabled = false;
	export let width = 245;
	export let onOpenChange: (open: boolean) => void = () => {};

	let mounted = false;
	let active = false;
	let locked = false;
	let direction: 'open' | 'close' | null = null;
	let startX = 0;
	let startY = 0;
	let lastX = 0;
	let lastTime = 0;
	let velocity = 0;
	let startProgress = 0;
	let swipeProgress = 0;
	let settling = false;
	let settleTimer: ReturnType<typeof setTimeout> | null = null;
	let settleFrame: ReturnType<typeof requestAnimationFrame> | null = null;
	let scrollLocked = false;
	let lastOpen: boolean | null = null;
	let lastEnabled: boolean | null = null;

	$: panelWidth = width || 245;
	$: progress = enabled ? Math.max(0, Math.min(1, swipeProgress)) : 1;
	$: visible = open || (enabled && mounted);
	$: panelStyle = enabled
		? `transform: translateX(${(progress - 1) * 100}%); transition: ${
				settling ? `transform ${SETTLE_MS}ms cubic-bezier(0.22, 1, 0.36, 1)` : 'none'
			};`
		: '';
	$: backdropStyle = enabled
		? `opacity: ${progress * 0.6}; transition: ${
				settling ? `opacity ${SETTLE_MS}ms cubic-bezier(0.22, 1, 0.36, 1)` : 'none'
			};`
		: '';

	$: if (open !== lastOpen || enabled !== lastEnabled) {
		lastOpen = open;
		lastEnabled = enabled;

		if (enabled) {
			animate(open);
		} else {
			mounted = false;
			swipeProgress = open ? 1 : 0;
			settling = false;
			setScrollLock(false);
		}
	}

	const shouldSkipSwipe = (target: EventTarget | null) => {
		return (
			target instanceof Element &&
			!!target.closest(
				'input, textarea, select, [role="dialog"], [role="menu"], [contenteditable="true"], [data-sidebar-no-gesture]'
			)
		);
	};

	const hasTextSelection = () => {
		if (typeof window === 'undefined') {
			return false;
		}

		const selection = window.getSelection();
		return !!selection && !selection.isCollapsed;
	};

	const canScrollHorizontally = (target: EventTarget | null, dx: number) => {
		if (!(target instanceof Element) || dx === 0 || typeof window === 'undefined') {
			return false;
		}

		let element: Element | null = target;
		while (element && element !== document.documentElement && element !== document.body) {
			const node = element as HTMLElement;
			const overflowX = window.getComputedStyle(node).overflowX;
			const isScrollable =
				/(auto|scroll|overlay)/.test(overflowX) && node.scrollWidth > node.clientWidth + 1;

			if (isScrollable) {
				const maxScrollLeft = node.scrollWidth - node.clientWidth;
				return dx > 0 ? node.scrollLeft > 0 : node.scrollLeft < maxScrollLeft - 1;
			}

			element = element.parentElement;
		}

		return false;
	};

	const setScrollLock = (locked: boolean) => {
		if (scrollLocked === locked || typeof document === 'undefined') {
			return;
		}

		scrollLocked = locked;
		document.documentElement.classList.toggle('mobile-swipe-panel-active', locked);
		document.body.classList.toggle('mobile-swipe-panel-active', locked);
	};

	const clearTimer = () => {
		if (settleTimer) {
			clearTimeout(settleTimer);
			settleTimer = null;
		}
	};

	const clearFrame = () => {
		if (settleFrame) {
			cancelAnimationFrame(settleFrame);
			settleFrame = null;
		}
	};

	const prefersReducedMotion = () =>
		typeof window !== 'undefined' &&
		window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

	const animate = (nextOpen: boolean) => {
		clearTimer();
		clearFrame();
		mounted = nextOpen || mounted;

		const finish = () => {
			settling = false;
			settleTimer = null;
		};

		const settle = () => {
			settling = !prefersReducedMotion();
			swipeProgress = nextOpen ? 1 : 0;
			settleTimer = setTimeout(finish, settling ? SETTLE_MS : 0);
		};

		if (nextOpen && swipeProgress <= 0.01) {
			swipeProgress = 0;
			settling = false;
			settleFrame = requestAnimationFrame(() => {
				settleFrame = null;
				settle();
			});
			return;
		}

		settle();
	};

	const resetSwipe = () => {
		active = false;
		locked = false;
		direction = null;
		velocity = 0;
		setScrollLock(false);
	};

	const cancelSwipe = () => {
		resetSwipe();
		animate(open);
	};

	const onTouchStart = (e: TouchEvent) => {
		if (!enabled || e.touches.length !== 1 || shouldSkipSwipe(e.target) || hasTextSelection()) {
			return;
		}

		const touch = e.touches[0];
		const x = touch.clientX;

		if (!open) {
			if (x < UNSAFE_EDGE) {
				return;
			}

			direction = 'open';
			startProgress = 0;
			mounted = true;
			swipeProgress = 0;
		} else {
			direction = 'close';
			startProgress = swipeProgress || 1;
		}

		clearTimer();
		settling = false;
		active = true;
		locked = false;
		startX = x;
		startY = touch.clientY;
		lastX = x;
		lastTime = e.timeStamp;
		velocity = 0;
	};

	const onTouchMove = (e: TouchEvent) => {
		if (!active || !direction || e.touches.length !== 1) {
			return;
		}

		const touch = e.touches[0];
		const dx = touch.clientX - startX;
		const dy = touch.clientY - startY;
		const absX = Math.abs(dx);
		const absY = Math.abs(dy);

		if (!locked) {
			if (hasTextSelection()) {
				cancelSwipe();
				return;
			}

			if ((direction === 'open' && dx > 0) || (direction === 'close' && dx < 0)) {
				swipeProgress = Math.max(0, Math.min(1, startProgress + dx / panelWidth));
			}

			if (absX < SWIPE_SLOP && absY < SWIPE_SLOP) {
				return;
			}

			if (absX > absY && canScrollHorizontally(e.target, dx)) {
				cancelSwipe();
				return;
			}

			if (absY > absX || absX < absY * AXIS_RATIO) {
				cancelSwipe();
				return;
			}

			locked = true;
			setScrollLock(true);
		}

		e.preventDefault();

		const now = e.timeStamp;
		const elapsed = Math.max(1, now - lastTime);
		velocity = (touch.clientX - lastX) / elapsed;
		lastX = touch.clientX;
		lastTime = now;

		swipeProgress = Math.max(0, Math.min(1, startProgress + dx / panelWidth));
	};

	const onTouchEnd = () => {
		if (!active) {
			return;
		}

		if (!locked) {
			cancelSwipe();
			return;
		}

		let shouldOpen = direction === 'open' ? swipeProgress > 0.35 : swipeProgress > 0.65;

		if (velocity > FLICK_VELOCITY) {
			shouldOpen = true;
		} else if (velocity < -FLICK_VELOCITY) {
			shouldOpen = false;
		}

		resetSwipe();
		animate(shouldOpen);
		onOpenChange(shouldOpen);
	};

	const onTouchCancel = () => {
		if (active) {
			cancelSwipe();
		}
	};

	onMount(() => {
		window.addEventListener('touchstart', onTouchStart, { passive: true });
		window.addEventListener('touchmove', onTouchMove, { passive: false });
		window.addEventListener('touchend', onTouchEnd);
		window.addEventListener('touchcancel', onTouchCancel);
	});

	onDestroy(() => {
		window.removeEventListener('touchstart', onTouchStart);
		window.removeEventListener('touchmove', onTouchMove);
		window.removeEventListener('touchend', onTouchEnd);
		window.removeEventListener('touchcancel', onTouchCancel);
		clearTimer();
		clearFrame();
		setScrollLock(false);
	});
</script>

<slot {visible} {progress} {panelStyle} {backdropStyle} />

<style>
	:global(html),
	:global(body) {
		overflow-x: hidden;
		overscroll-behavior-x: contain;
	}

	:global(html.mobile-swipe-panel-active),
	:global(body.mobile-swipe-panel-active) {
		touch-action: pan-y;
	}
</style>
