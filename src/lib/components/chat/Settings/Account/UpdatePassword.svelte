<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { updateUserPassword } from '$lib/apis/auths';

	const i18n = getContext('i18n');

	let show = false;
	let currentPassword = '';
	let newPassword = '';
	let newPasswordConfirm = '';

	const updatePasswordHandler = async () => {
		if (newPassword === newPasswordConfirm) {
			const res = await updateUserPassword(localStorage.token, currentPassword, newPassword).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				toast.success($i18n.t('Successfully updated.'));
			}

			currentPassword = '';
			newPassword = '';
			newPasswordConfirm = '';
		} else {
			toast.error(
				`The passwords you entered don't quite match. Please double-check and try again.`
			);
			newPassword = '';
			newPasswordConfirm = '';
		}
	};
</script>

<form
	class="flex flex-col"
	on:submit|preventDefault={() => {
		updatePasswordHandler();
	}}
>
	<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
		<div class="flex justify-between items-center">
			<div class="font-semibold text-gray-800 dark:text-gray-200">
				{$i18n.t('Change Password')}
			</div>
			<button
				class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
				type="button"
				on:click={() => {
					show = !show;
				}}
			>
				{show ? $i18n.t('Hide') : $i18n.t('Show')}
			</button>
		</div>

		{#if show}
			<div class="mt-4 space-y-4">
				<!-- Current Password -->
				<div class="space-y-2">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Current Password')}
					</label>
					<input
						class="w-full px-4 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition placeholder:text-gray-400 dark:placeholder:text-gray-500"
						type="password"
						bind:value={currentPassword}
						placeholder={$i18n.t('Enter your current password')}
						autocomplete="current-password"
						required
					/>
				</div>

				<!-- New Password -->
				<div class="space-y-2">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('New Password')}
					</label>
					<input
						class="w-full px-4 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition placeholder:text-gray-400 dark:placeholder:text-gray-500"
						type="password"
						bind:value={newPassword}
						placeholder={$i18n.t('Enter your new password')}
						autocomplete="new-password"
						required
					/>
				</div>

				<!-- Confirm Password -->
				<div class="space-y-2">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Confirm Password')}
					</label>
					<input
						class="w-full px-4 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition placeholder:text-gray-400 dark:placeholder:text-gray-500"
						type="password"
						bind:value={newPasswordConfirm}
						placeholder={$i18n.t('Confirm your new password')}
						autocomplete="off"
						required
					/>
				</div>

				<!-- Submit Button -->
				<div class="flex justify-end pt-2">
					<button
						type="submit"
						class="px-6 py-2.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md"
					>
						{$i18n.t('Update password')}
					</button>
				</div>
			</div>
		{/if}
	</div>
</form>