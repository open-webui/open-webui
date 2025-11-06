<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { user } from '$lib/stores';
	import { get } from 'svelte/store';
	import { postAssignmentActivity } from '$lib/apis/assignment-time';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let userId: string = '';
	export let sessionNumber: number = 1;
	export let enabled: boolean = true;

	let assignmentActiveMs: number = 0;
	let lastActivityAt: number = Date.now();
	let activityInterval: ReturnType<typeof setInterval> | null = null;
	let syncInterval: ReturnType<typeof setInterval> | null = null;
	const IDLE_THRESHOLD_MS = 60_000; // 60 seconds
	const SYNC_INTERVAL_MS = 30_000; // 30 seconds

	function markActivity() {
		lastActivityAt = Date.now();
	}

	function isActiveWindow(): boolean {
		return typeof document !== 'undefined' && document.visibilityState === 'visible';
	}

	function activityKeyFor(uId: string, session: number) {
		return `assignmentActiveMs_${uId}_${session}`;
	}

	async function syncActivity() {
		if (!enabled) return;
		const currentUserId = userId || get(user)?.id || 'unknown';
		if (!currentUserId || !Number.isFinite(sessionNumber)) return;
		
		try {
			await postAssignmentActivity(localStorage.token || '', {
				user_id: currentUserId,
				session_number: sessionNumber,
				active_ms_cumulative: assignmentActiveMs,
			});
		} catch (e) {
			console.warn('Assignment activity sync failed', e);
		}
	}

	function startActivityTracking() {
		if (!enabled) return;
		
		const currentUserId = userId || get(user)?.id || 'unknown';
		if (!currentUserId || !Number.isFinite(sessionNumber)) return;
		
		// Restore from localStorage
		try {
			const k = activityKeyFor(currentUserId, sessionNumber);
			const saved = localStorage.getItem(k);
			if (saved) {
				assignmentActiveMs = Number(saved) || 0;
			}
		} catch (e) {
			console.warn('Failed to restore assignment activity from localStorage', e);
		}

		// Start activity interval
		if (!activityInterval) {
			activityInterval = setInterval(() => {
				if (!enabled) return;
				if (!isActiveWindow()) return;
				const now = Date.now();
				if (now - lastActivityAt <= IDLE_THRESHOLD_MS) {
					assignmentActiveMs += 1000;
					try {
						const k = activityKeyFor(currentUserId, sessionNumber);
						localStorage.setItem(k, String(assignmentActiveMs));
					} catch (e) {
						console.warn('Failed to save assignment activity to localStorage', e);
					}
				}
			}, 1000);
		}

		// Start sync interval
		if (!syncInterval) {
			syncInterval = setInterval(() => {
				void syncActivity();
			}, SYNC_INTERVAL_MS);
		}

		// Add activity listeners
		window.addEventListener('mousemove', markActivity);
		window.addEventListener('keydown', markActivity);
		window.addEventListener('click', markActivity);
		window.addEventListener('touchstart', markActivity);
		document.addEventListener('visibilitychange', markActivity);

		// Send final time on page unload
		window.addEventListener('beforeunload', () => {
			if (!enabled) return;
			try {
				const payload = JSON.stringify({
					user_id: currentUserId,
					session_number: sessionNumber,
					active_ms_cumulative: assignmentActiveMs,
				});
				navigator.sendBeacon(`${WEBUI_API_BASE_URL}/assignment/session-activity`, payload);
			} catch (e) {
				console.warn('Failed to send assignment activity on unload', e);
			}
		});
	}

	function stopActivityTracking() {
		// Send final time before stopping
		void syncActivity();
		
		// Clear intervals
		if (activityInterval) {
			clearInterval(activityInterval);
			activityInterval = null;
		}
		if (syncInterval) {
			clearInterval(syncInterval);
			syncInterval = null;
		}

		// Remove event listeners
		window.removeEventListener('mousemove', markActivity);
		window.removeEventListener('keydown', markActivity);
		window.removeEventListener('click', markActivity);
		window.removeEventListener('touchstart', markActivity);
		document.removeEventListener('visibilitychange', markActivity);
	}

	onMount(() => {
		if (enabled) {
			startActivityTracking();
		}
	});

	onDestroy(() => {
		stopActivityTracking();
	});

	// Restart tracking if enabled changes
	$: {
		if (enabled && !activityInterval) {
			startActivityTracking();
		} else if (!enabled && activityInterval) {
			stopActivityTracking();
		}
	}

	// Update tracking when userId or sessionNumber changes
	$: {
		if (enabled && activityInterval) {
			// If these change, we need to restart tracking with new keys
			stopActivityTracking();
			startActivityTracking();
		}
	}
</script>



