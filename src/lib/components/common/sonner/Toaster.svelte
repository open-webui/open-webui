<script>import { onDestroy, onMount } from 'svelte';
import { toastState } from './state.js';
import Toast from './Toast.svelte';
import Loader from './Loader.svelte';
import Icon from './Icon.svelte';
// Visible toasts amount
const VISIBLE_TOASTS_AMOUNT = 3;
// Viewport padding
const VIEWPORT_OFFSET = '32px';
// Default toast width
const TOAST_WIDTH = 356;
// Default gap between toasts
const GAP = 14;
const DARK = 'dark';
const LIGHT = 'light';
function getInitialTheme(t) {
    if (t !== 'system') {
        return t;
    }
    if (typeof window !== 'undefined') {
        if (window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return DARK;
        }
        return LIGHT;
    }
    return LIGHT;
}
function getDocumentDirection() {
    if (typeof window === 'undefined')
        return 'ltr';
    if (typeof document === 'undefined')
        return 'ltr'; // For Fresh purpose
    const dirAttribute = document.documentElement.getAttribute('dir');
    if (dirAttribute === 'auto' || !dirAttribute) {
        return window.getComputedStyle(document.documentElement)
            .direction;
    }
    return dirAttribute;
}
export let invert = false;
export let theme = 'light';
export let position = 'bottom-right';
export let hotkey = ['altKey', 'KeyT'];
export let containerAriaLabel = 'Notifications';
export let richColors = false;
export let expand = false;
export let duration = 4000;
export let visibleToasts = VISIBLE_TOASTS_AMOUNT;
export let closeButton = false;
export let toastOptions = {};
export let offset = null;
export let dir = getDocumentDirection();
const { toasts, heights, reset } = toastState;
$: possiblePositions = Array.from(new Set([
    position,
    ...$toasts
        .filter((toast) => toast.position)
        .map((toast) => toast.position)
].filter(Boolean)));
// Custom behavior:
// - Expand/collapse on click instead of hover.
// - Keep hover from changing expanded state to avoid accidental expansion.
let expanded = false;
let interacting = false;
let actualTheme = getInitialTheme(theme);
let listRef;
let lastFocusedElementRef = null;
let isFocusWithinRef = false;
$: hotkeyLabel = hotkey.join('+').replace(/Key/g, '').replace(/Digit/g, '');
$: if ($toasts.length <= 1) {
    expanded = false;
}
// Check for dismissed toasts and remove them. We need to do this to have dismiss animation.
$: {
    const toastsToDismiss = $toasts.filter((toast) => toast.dismiss && !toast.delete);
    if (toastsToDismiss.length > 0) {
        const updatedToasts = $toasts.map((toast) => {
            const matchingToast = toastsToDismiss.find((dismissToast) => dismissToast.id === toast.id);
            if (matchingToast) {
                return { ...toast, delete: true };
            }
            return toast;
        });
        toasts.set(updatedToasts);
    }
}
onDestroy(() => {
    if (listRef && lastFocusedElementRef) {
        lastFocusedElementRef.focus({ preventScroll: true });
        lastFocusedElementRef = null;
        isFocusWithinRef = false;
    }
});
onMount(() => {
    reset();
    const handleKeydown = (event) => {
        const isHotkeyPressed = hotkey.every((key) => 
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        event[key] || event.code === key);
        if (isHotkeyPressed) {
            expanded = true;
            listRef?.focus();
        }
        if (event.code === 'Escape' &&
            (document.activeElement === listRef ||
                listRef?.contains(document.activeElement))) {
            expanded = false;
        }
    };
    document.addEventListener('keydown', handleKeydown);
    return () => {
        document.removeEventListener('keydown', handleKeydown);
    };
});
$: {
    if (theme !== 'system') {
        actualTheme = theme;
    }
    if (typeof window !== 'undefined') {
        if (theme === 'system') {
            // check if current preference is dark
            if (window.matchMedia &&
                window.matchMedia('(prefers-color-scheme: dark)').matches) {
                // it's currently dark
                actualTheme = DARK;
            }
            else {
                // it's not dark
                actualTheme = LIGHT;
            }
        }
        const mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');
        const changeHandler = ({ matches }) => {
            actualTheme = matches ? DARK : LIGHT;
        };
        if ('addEventListener' in mediaQueryList) {
            mediaQueryList.addEventListener('change', changeHandler);
        }
        else {
            // @ts-expect-error deprecated API
            mediaQueryList.addListener(changeHandler);
        }
    }
}
function handleBlur(event) {
    if (isFocusWithinRef &&
        !event.currentTarget.contains(event.relatedTarget)) {
        isFocusWithinRef = false;
        if (lastFocusedElementRef) {
            lastFocusedElementRef.focus({ preventScroll: true });
            lastFocusedElementRef = null;
        }
    }
}
function handleFocus(event) {
    if (!isFocusWithinRef) {
        isFocusWithinRef = true;
        lastFocusedElementRef = event.relatedTarget;
    }
}
</script>

{#if $toasts.length > 0}
	<section aria-label={`${containerAriaLabel} ${hotkeyLabel}`} tabIndex={-1}>
		{#each possiblePositions as position, index}
			<ol
				tabIndex={-1}
				bind:this={listRef}
				class={$$props.class}
				data-sonner-toaster
				data-theme={actualTheme}
				data-rich-colors={richColors}
				dir={dir === 'auto' ? getDocumentDirection() : dir}
				data-y-position={position.split('-')[0]}
				data-x-position={position.split('-')[1]}
				on:blur={handleBlur}
				on:focus={handleFocus}
				on:click={(event) => {
					// Only toggle when clicking the toast body, not the close button.
					if (event.target?.closest?.('[data-close-button]')) return;
					expanded = !expanded;
				}}
				on:pointerdown={() => (interacting = true)}
				on:pointerup={() => (interacting = false)}
				style:--front-toast-height={`${$heights[0]?.height}px`}
				style:--offset={typeof offset === 'number'
					? `${offset}px`
					: offset || VIEWPORT_OFFSET}
				style:--width={`${TOAST_WIDTH}px`}
				style:--gap={`${GAP}px`}
				style={$$props.style}
				{...$$restProps}
			>
				{#each $toasts.filter((toast) => (!toast.position && index === 0) || toast.position === position) as toast, index (toast.id)}
					<Toast
						{index}
						{toast}
						{invert}
						{visibleToasts}
						{closeButton}
						{interacting}
						{position}
						expandByDefault={expand}
						{expanded}
						actionButtonStyle={toastOptions?.actionButtonStyle ||
							''}
						cancelButtonStyle={toastOptions?.cancelButtonStyle ||
							''}
						class={toastOptions?.class || ''}
						descriptionClass={toastOptions?.descriptionClass || ''}
						classes={toastOptions.classes || {}}
						duration={toastOptions?.duration ?? duration}
						unstyled={toastOptions.unstyled || false}
					>
						<slot name="loading-icon" slot="loading-icon">
							<Loader visible={toast.type === 'loading'} />
						</slot>
						<slot name="success-icon" slot="success-icon">
							<Icon type="success" />
						</slot>
						<slot name="error-icon" slot="error-icon">
							<Icon type="error" />
						</slot>
						<slot name="warning-icon" slot="warning-icon">
							<Icon type="warning" />
						</slot>
						<slot name="info-icon" slot="info-icon">
							<Icon type="info" />
						</slot>
					</Toast>
				{/each}
			</ol>
		{/each}
	</section>
{/if}

<style global>
	:global(:where(html[dir='ltr'])),
	:global(:where([data-sonner-toaster][dir='ltr'])) {
		--toast-icon-margin-start: -3px;
		--toast-icon-margin-end: 4px;
		--toast-svg-margin-start: -1px;
		--toast-svg-margin-end: 0px;
		--toast-button-margin-start: auto;
		--toast-button-margin-end: 0;
		--toast-close-button-start: 0;
		--toast-close-button-end: unset;
		--toast-close-button-transform: translate(-35%, -35%);
	}

	:global(:where(html[dir='rtl'])),
	:global(:where([data-sonner-toaster][dir='rtl'])) {
		--toast-icon-margin-start: 4px;
		--toast-icon-margin-end: -3px;
		--toast-svg-margin-start: 0px;
		--toast-svg-margin-end: -1px;
		--toast-button-margin-start: 0;
		--toast-button-margin-end: auto;
		--toast-close-button-start: unset;
		--toast-close-button-end: 0;
		--toast-close-button-transform: translate(35%, -35%);
	}

	:global(:where([data-sonner-toaster])) {
		position: fixed;
		width: var(--width);
		font-family:
			ui-sans-serif,
			system-ui,
			-apple-system,
			BlinkMacSystemFont,
			Segoe UI,
			Roboto,
			Helvetica Neue,
			Arial,
			Noto Sans,
			sans-serif,
			Apple Color Emoji,
			Segoe UI Emoji,
			Segoe UI Symbol,
			Noto Color Emoji;
		--gray1: hsl(0, 0%, 99%);
		--gray2: hsl(0, 0%, 97.3%);
		--gray3: hsl(0, 0%, 95.1%);
		--gray4: hsl(0, 0%, 93%);
		--gray5: hsl(0, 0%, 90.9%);
		--gray6: hsl(0, 0%, 88.7%);
		--gray7: hsl(0, 0%, 85.8%);
		--gray8: hsl(0, 0%, 78%);
		--gray9: hsl(0, 0%, 56.1%);
		--gray10: hsl(0, 0%, 52.3%);
		--gray11: hsl(0, 0%, 43.5%);
		--gray12: hsl(0, 0%, 9%);
		--border-radius: 8px;
		box-sizing: border-box;
		padding: 0;
		margin: 0;
		list-style: none;
		outline: none;
		z-index: 999999999;
	}

	:global(:where([data-sonner-toaster][data-x-position='right'])) {
		right: max(var(--offset), env(safe-area-inset-right));
	}

	:global(:where([data-sonner-toaster][data-x-position='left'])) {
		left: max(var(--offset), env(safe-area-inset-left));
	}

	:global(:where([data-sonner-toaster][data-x-position='center'])) {
		left: 50%;
		transform: translateX(-50%);
	}

	:global(:where([data-sonner-toaster][data-y-position='top'])) {
		top: max(var(--offset), env(safe-area-inset-top));
	}

	:global(:where([data-sonner-toaster][data-y-position='bottom'])) {
		bottom: max(var(--offset), env(safe-area-inset-bottom));
	}

	:global(:where([data-sonner-toast])) {
		--y: translateY(100%);
		--lift-amount: calc(var(--lift) * var(--gap));
		z-index: var(--z-index);
		position: absolute;
		opacity: 0;
		transform: var(--y);
		filter: blur(0);
		/* https://stackoverflow.com/questions/48124372/pointermove-event-not-working-with-touch-why-not */
		touch-action: none;
		transition:
			transform 400ms,
			opacity 400ms,
			height 400ms,
			box-shadow 200ms;
		box-sizing: border-box;
		outline: none;
		overflow-wrap: anywhere;
	}

	:global(:where([data-sonner-toast][data-styled='true'])) {
		padding: 16px;
		background: var(--normal-bg);
		border: 1px solid var(--normal-border);
		color: var(--normal-text);
		border-radius: var(--border-radius);
		box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
		width: var(--width);
		font-size: 13px;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	:global(:where([data-sonner-toast]:focus-visible)) {
		box-shadow:
			0px 4px 12px rgba(0, 0, 0, 0.1),
			0 0 0 2px rgba(0, 0, 0, 0.2);
	}

	:global(:where([data-sonner-toast][data-y-position='top'])) {
		top: 0;
		--y: translateY(-100%);
		--lift: 1;
		--lift-amount: calc(1 * var(--gap));
	}

	:global(:where([data-sonner-toast][data-y-position='bottom'])) {
		bottom: 0;
		--y: translateY(100%);
		--lift: -1;
		--lift-amount: calc(var(--lift) * var(--gap));
	}

	:global(:where([data-sonner-toast])) :global(:where([data-description])) {
		font-weight: 400;
		line-height: 1.4;
		color: inherit;
	}

	:global(:where([data-sonner-toast])) :global(:where([data-title])) {
		font-weight: 500;
		line-height: 1.5;
		color: inherit;
	}

	:global(:where([data-sonner-toast])) :global(:where([data-icon])) {
		display: flex;
		height: 16px;
		width: 16px;
		position: relative;
		justify-content: flex-start;
		align-items: center;
		flex-shrink: 0;
		margin-left: var(--toast-icon-margin-start);
		margin-right: var(--toast-icon-margin-end);
	}

	:global(:where([data-sonner-toast][data-promise='true'])) :global(:where([data-icon])) > :global(svg) {
		opacity: 0;
		transform: scale(0.8);
		transform-origin: center;
		animation: sonner-fade-in 300ms ease forwards;
	}

	:global(:where([data-sonner-toast])) :global(:where([data-icon])) > :global(*) {
		flex-shrink: 0;
	}

	:global(:where([data-sonner-toast])) :global(:where([data-icon])) :global(svg) {
		margin-left: var(--toast-svg-margin-start);
		margin-right: var(--toast-svg-margin-end);
	}

	:global(:where([data-sonner-toast])) :global(:where([data-content])) {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	:global([data-sonner-toast][data-styled='true']) :global([data-button]) {
		border-radius: 4px;
		padding-left: 8px;
		padding-right: 8px;
		height: 24px;
		font-size: 12px;
		color: var(--normal-bg);
		background: var(--normal-text);
		margin-left: var(--toast-button-margin-start);
		margin-right: var(--toast-button-margin-end);
		border: none;
		cursor: pointer;
		outline: none;
		display: flex;
		align-items: center;
		flex-shrink: 0;
		transition:
			opacity 400ms,
			box-shadow 200ms;
	}

	:global(:where([data-sonner-toast])) :global(:where([data-button]):focus-visible) {
		box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.4);
	}

	:global(:where([data-sonner-toast])) :global(:where([data-button]):first-of-type) {
		margin-left: var(--toast-button-margin-start);
		margin-right: var(--toast-button-margin-end);
	}

	:global(:where([data-sonner-toast])) :global(:where([data-cancel])) {
		color: var(--normal-text);
		background: rgba(0, 0, 0, 0.08);
	}

	:global(:where([data-sonner-toast][data-theme='dark'])) :global(:where([data-cancel])) {
		background: rgba(255, 255, 255, 0.3);
	}

	:global(:where([data-sonner-toast])) :global(:where([data-close-button])) {
		position: absolute;
		left: var(--toast-close-button-start);
		right: var(--toast-close-button-end);
		top: 0;
		height: 20px;
		width: 20px;
		display: flex;
		justify-content: center;
		align-items: center;
		padding: 0;
		background: var(--gray1);
		color: var(--gray12);
		border: 1px solid var(--gray4);
		transform: var(--toast-close-button-transform);
		border-radius: 50%;
		cursor: pointer;
		z-index: 1;
		transition:
			opacity 100ms,
			background 200ms,
			border-color 200ms;
	}

	:global(:where([data-sonner-toast])) :global(:where([data-close-button]):focus-visible) {
		box-shadow:
			0px 4px 12px rgba(0, 0, 0, 0.1),
			0 0 0 2px rgba(0, 0, 0, 0.2);
	}

	:global(:where([data-sonner-toast])) :global(:where([data-disabled='true'])) {
		cursor: not-allowed;
	}

	:global(:where([data-sonner-toast]):hover) :global(:where([data-close-button]):hover) {
		background: var(--gray2);
		border-color: var(--gray5);
	}

	/* Leave a ghost div to avoid setting hover to false when swiping out */
	:global(:where([data-sonner-toast][data-swiping='true'])::before) {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		height: 100%;
		z-index: -1;
	}

	:global(:where(
			[data-sonner-toast][data-y-position='top'][data-swiping='true']
		)::before) {
		/* y 50% needed to distribute height additional height evenly */
		bottom: 50%;
		transform: scaleY(3) translateY(50%);
	}

	:global(:where(
			[data-sonner-toast][data-y-position='bottom'][data-swiping='true']
		)::before) {
		/* y -50% needed to distribute height additional height evenly */
		top: 50%;
		transform: scaleY(3) translateY(-50%);
	}

	/* Leave a ghost div to avoid setting hover to false when transitioning out */
	:global(:where(
			[data-sonner-toast][data-swiping='false'][data-removed='true']
		)::before) {
		content: '';
		position: absolute;
		inset: 0;
		transform: scaleY(2);
	}

	/* Needed to avoid setting hover to false when inbetween toasts */
	:global(:where([data-sonner-toast])::after) {
		content: '';
		position: absolute;
		left: 0;
		height: calc(var(--gap) + 1px);
		bottom: 100%;
		width: 100%;
	}

	:global(:where([data-sonner-toast][data-mounted='true'])) {
		--y: translateY(0);
		opacity: 1;
	}

	:global(:where([data-sonner-toast][data-expanded='false'][data-front='false'])) {
		--scale: var(--toasts-before) * 0.05 + 1;
		--y: translateY(calc(var(--lift-amount) * var(--toasts-before)))
			scale(calc(-1 * var(--scale)));
		height: var(--front-toast-height);
	}

	:global(:where([data-sonner-toast])) > :global(*) {
		transition: opacity 400ms;
	}

	:global(:where(
			[data-sonner-toast][data-expanded='false'][data-front='false'][data-styled='true']
		)
		)> :global(*) {
		opacity: 0;
	}

	:global(:where([data-sonner-toast][data-visible='false'])) {
		opacity: 0;
		pointer-events: none;
	}

	:global(:where([data-sonner-toast][data-mounted='true'][data-expanded='true'])) {
		--y: translateY(calc(var(--lift) * var(--offset)));
		height: var(--initial-height);
	}

	:global(:where(
			[data-sonner-toast][data-removed='true'][data-front='true'][data-swipe-out='false']
		)) {
		--y: translateY(calc(var(--lift) * -100%));
		opacity: 0;
	}

	:global(:where(
			[data-sonner-toast][data-removed='true'][data-front='false'][data-swipe-out='false'][data-expanded='true']
		)) {
		--y: translateY(
			calc(var(--lift) * var(--offset) + var(--lift) * -100%)
		);
		opacity: 0;
	}

	:global(:where(
			[data-sonner-toast][data-removed='true'][data-front='false'][data-swipe-out='false'][data-expanded='false']
		)) {
		--y: translateY(40%);
		opacity: 0;
		transition:
			transform 500ms,
			opacity 200ms;
	}

	/* Bump up the height to make sure hover state doesn't get set to false */
	:global(:where(
			[data-sonner-toast][data-removed='true'][data-front='false']
		)::before) {
		height: calc(var(--initial-height) + 20%);
	}

	:global([data-sonner-toast][data-swiping='true']) {
		transform: var(--y) translateY(var(--swipe-amount, 0px));
		transition: none;
	}

	:global([data-sonner-toast][data-swipe-out='true'][data-y-position='bottom']),
	:global([data-sonner-toast][data-swipe-out='true'][data-y-position='top']) {
		animation: swipe-out 200ms ease-out forwards;
	}

	@keyframes -global-swipe-out {
		from {
			transform: translateY(
				calc(var(--lift) * var(--offset) + var(--swipe-amount))
			);
			opacity: 1;
		}

		to {
			transform: translateY(
				calc(
					var(--lift) * var(--offset) + var(--swipe-amount) +
						var(--lift) * -100%
				)
			);
			opacity: 0;
		}
	}

	@media (max-width: 600px) {
		:global([data-sonner-toaster]) {
			position: fixed;
			--mobile-offset: 16px;
			right: var(--mobile-offset);
			left: var(--mobile-offset);
			width: 100%;
		}

		:global([data-sonner-toaster]) :global([data-sonner-toast]) {
			left: 0;
			right: 0;
			width: calc(100% - var(--mobile-offset) * 2);
		}

		:global([data-sonner-toaster][data-x-position='left']) {
			left: var(--mobile-offset);
		}

		:global([data-sonner-toaster][data-y-position='bottom']) {
			bottom: 20px;
		}

		:global([data-sonner-toaster][data-y-position='top']) {
			top: 20px;
		}

		:global([data-sonner-toaster][data-x-position='center']) {
			left: var(--mobile-offset);
			right: var(--mobile-offset);
			transform: none;
		}
	}

	:global([data-sonner-toaster][data-theme='light']) {
		--normal-bg: #fff;
		--normal-border: var(--gray4);
		--normal-text: var(--gray12);

		--success-bg: hsl(143, 85%, 96%);
		--success-border: hsl(145, 92%, 91%);
		--success-text: hsl(140, 100%, 27%);

		--info-bg: hsl(208, 100%, 97%);
		--info-border: hsl(221, 91%, 91%);
		--info-text: hsl(210, 92%, 45%);

		--warning-bg: hsl(49, 100%, 97%);
		--warning-border: hsl(49, 91%, 91%);
		--warning-text: hsl(31, 92%, 45%);

		--error-bg: hsl(359, 100%, 97%);
		--error-border: hsl(359, 100%, 94%);
		--error-text: hsl(360, 100%, 45%);
	}

	:global([data-sonner-toaster][data-theme='light']
		[data-sonner-toast][data-invert='true']) {
		--normal-bg: #000;
		--normal-border: hsl(0, 0%, 20%);
		--normal-text: var(--gray1);
	}

	:global([data-sonner-toaster][data-theme='dark']
		[data-sonner-toast][data-invert='true']) {
		--normal-bg: #fff;
		--normal-border: var(--gray3);
		--normal-text: var(--gray12);
	}

	:global([data-sonner-toaster][data-theme='dark']) {
		--normal-bg: #000;
		--normal-border: hsl(0, 0%, 20%);
		--normal-text: var(--gray1);

		--success-bg: hsl(150, 100%, 6%);
		--success-border: hsl(147, 100%, 12%);
		--success-text: hsl(150, 86%, 65%);

		--info-bg: hsl(215, 100%, 6%);
		--info-border: hsl(223, 100%, 12%);
		--info-text: hsl(216, 87%, 65%);

		--warning-bg: hsl(64, 100%, 6%);
		--warning-border: hsl(60, 100%, 12%);
		--warning-text: hsl(46, 87%, 65%);

		--error-bg: hsl(358, 76%, 10%);
		--error-border: hsl(357, 89%, 16%);
		--error-text: hsl(358, 100%, 81%);
	}

	:global([data-rich-colors='true']) :global([data-sonner-toast][data-type='success']) {
		background: var(--success-bg);
		border-color: var(--success-border);
		color: var(--success-text);
	}

	:global([data-theme='dark']
		[data-sonner-toast][data-type='default']
		[data-close-button]) {
		background: var(--normal-bg);
		border-color: var(--normal-border);
		color: var(--normal-text);
	}

	:global([data-rich-colors='true']
		[data-sonner-toast][data-type='success']
		[data-close-button]) {
		background: var(--success-bg);
		border-color: var(--success-border);
		color: var(--success-text);
	}

	:global([data-rich-colors='true']) :global([data-sonner-toast][data-type='info']) {
		background: var(--info-bg);
		border-color: var(--info-border);
		color: var(--info-text);
	}

	:global([data-rich-colors='true']
		[data-sonner-toast][data-type='info']
		[data-close-button]) {
		background: var(--info-bg);
		border-color: var(--info-border);
		color: var(--info-text);
	}

	:global([data-rich-colors='true']) :global([data-sonner-toast][data-type='warning']) {
		background: var(--warning-bg);
		border-color: var(--warning-border);
		color: var(--warning-text);
	}

	:global([data-rich-colors='true']
		[data-sonner-toast][data-type='warning']
		[data-close-button]) {
		background: var(--warning-bg);
		border-color: var(--warning-border);
		color: var(--warning-text);
	}

	:global([data-rich-colors='true']) :global([data-sonner-toast][data-type='error']) {
		background: var(--error-bg);
		border-color: var(--error-border);
		color: var(--error-text);
	}

	:global([data-rich-colors='true']
		[data-sonner-toast][data-type='error']
		[data-close-button]) {
		background: var(--error-bg);
		border-color: var(--error-border);
		color: var(--error-text);
	}

	:global(.sonner-loading-wrapper) {
		--size: 16px;
		height: var(--size);
		width: var(--size);
		position: absolute;
		inset: 0;
		z-index: 10;
	}

	:global(.sonner-loading-wrapper[data-visible='false']) {
		transform-origin: center;
		animation: sonner-fade-out 0.2s ease forwards;
	}

	:global(.sonner-spinner) {
		position: relative;
		top: 50%;
		left: 50%;
		height: var(--size);
		width: var(--size);
	}

	:global(.sonner-loading-bar) {
		animation: sonner-spin 1.2s linear infinite;
		background: var(--gray11);
		border-radius: 6px;
		height: 8%;
		left: -10%;
		position: absolute;
		top: -3.9%;
		width: 24%;
	}

	:global(.sonner-loading-bar:nth-child(1)) {
		animation-delay: -1.2s;
		transform: rotate(0.0001deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(2)) {
		animation-delay: -1.1s;
		transform: rotate(30deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(3)) {
		animation-delay: -1s;
		transform: rotate(60deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(4)) {
		animation-delay: -0.9s;
		transform: rotate(90deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(5)) {
		animation-delay: -0.8s;
		transform: rotate(120deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(6)) {
		animation-delay: -0.7s;
		transform: rotate(150deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(7)) {
		animation-delay: -0.6s;
		transform: rotate(180deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(8)) {
		animation-delay: -0.5s;
		transform: rotate(210deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(9)) {
		animation-delay: -0.4s;
		transform: rotate(240deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(10)) {
		animation-delay: -0.3s;
		transform: rotate(270deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(11)) {
		animation-delay: -0.2s;
		transform: rotate(300deg) translate(146%);
	}

	:global(.sonner-loading-bar:nth-child(12)) {
		animation-delay: -0.1s;
		transform: rotate(330deg) translate(146%);
	}

	@keyframes -global-sonner-fade-in {
		0% {
			opacity: 0;
			transform: scale(0.8);
		}
		100% {
			opacity: 1;
			transform: scale(1);
		}
	}

	@keyframes -global-sonner-fade-out {
		0% {
			opacity: 1;
			transform: scale(1);
		}
		100% {
			opacity: 0;
			transform: scale(0.8);
		}
	}

	@keyframes -global-sonner-spin {
		0% {
			opacity: 1;
		}
		100% {
			opacity: 0.15;
		}
	}

	@media (prefers-reduced-motion) {
		:global([data-sonner-toast]),
		:global([data-sonner-toast]) > :global(*),
		:global(.sonner-loading-bar) {
			transition: none !important;
			animation: none !important;
		}
	}

	:global(.sonner-loader) {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		transform-origin: center;
		transition:
			opacity 200ms,
			transform 200ms;
	}

	:global(.sonner-loader[data-visible='false']) {
		opacity: 0;
		transform: scale(0.8) translate(-50%, -50%);
	}
</style>
