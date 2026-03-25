<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let members: { email: string; role: string }[] = [];

	let inviteEmail = '';
	let inviting = false;

	async function handleInvite() {
		if (!inviteEmail) return;
		inviting = true;
		try {
			await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/team/invite`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email: inviteEmail })
			});
			inviteEmail = '';
		} finally {
			inviting = false;
		}
	}
</script>

<div class="p-5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Equipo</h3>

	<div class="space-y-2 mb-4 max-h-40 overflow-y-auto">
		{#each members as member}
			<div class="flex items-center justify-between py-1.5">
				<span class="text-sm text-gray-900 dark:text-white">{member.email}</span>
				<span
					class="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
				>
					{member.role}
				</span>
			</div>
		{/each}
		{#if members.length === 0}
			<p class="text-sm text-gray-400">Sin miembros aun.</p>
		{/if}
	</div>

	<form class="flex gap-2" on:submit|preventDefault={handleInvite}>
		<input
			type="email"
			bind:value={inviteEmail}
			placeholder="email@ejemplo.com"
			class="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-sm text-gray-900 dark:text-white placeholder:text-gray-400"
		/>
		<button
			type="submit"
			disabled={inviting}
			class="px-4 py-2 rounded-lg bg-claw-500 hover:bg-claw-600 disabled:opacity-50 text-white text-sm font-medium transition"
		>
			Invitar
		</button>
	</form>
</div>
