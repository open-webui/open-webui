<script>
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let loaded = false;
	let email = '';
	let verificationType = '';

	onMount(async () => {
		// 从URL参数获取验证类型
		const urlParams = new URLSearchParams($page.url.search);
		verificationType = urlParams.get('type') || 'signup';
		
		// 从URL参数获取邮箱（如果有的话）
		email = urlParams.get('email') || '';
		
		loaded = true;
	});

	const handleResendEmail = () => {
		// TODO: 这里应该调用重发邮件的API
		console.log('Resending verification email to:', email);
		// 现在只是显示一个提示
		alert('Verification email has been resent!');
	};

	const getTitle = () => {
		if (verificationType === 'reset') {
			return 'Check your email';
		}
		return 'Verify your email';
	};

	const getMessage = () => {
		if (verificationType === 'reset') {
			return 'We\'ve sent a password reset link to your email address. Please check your inbox and click the link to reset your password.';
		}
		return 'We\'ve sent a verification link to your email address. Please check your inbox and click the link to verify your account.';
	};
</script>

<svelte:head>
	<title>{getTitle()}</title>
</svelte:head>

<div class="w-full h-screen max-h-[100dvh] bg-white dark:bg-black">
	<div class="w-full h-full flex items-center justify-center">
		<div class="w-full max-w-md px-8 text-center">
			{#if loaded}
				<!-- Email Icon -->
				<div class="flex justify-center mb-8">
					<div class="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
						<svg class="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
						</svg>
					</div>
				</div>

				<!-- Title -->
				<div class="mb-6">
					<h1 class="text-2xl font-bold text-black dark:text-white mb-4">
						{getTitle()}
					</h1>
					<p class="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
						{getMessage()}
					</p>
				</div>

				<!-- Email Display -->
				{#if email}
					<div class="mb-8">
						<p class="text-sm text-gray-500 dark:text-gray-500">
							Email sent to: <span class="font-medium text-gray-700 dark:text-gray-300">{email}</span>
						</p>
					</div>
				{/if}

				<!-- Resend Button -->
				<div class="mb-8">
					<button
						type="button"
						class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
						on:click={handleResendEmail}
					>
						Resend email
					</button>
				</div>

				<!-- Back to Login -->
				<div class="border-t border-gray-200 dark:border-gray-700 pt-6">
					<p class="text-sm text-gray-500 dark:text-gray-500 mb-4">
						Didn't receive the email? Check your spam folder or try again.
					</p>
					<button
						type="button"
						class="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
						on:click={() => goto('/auth/login')}
					>
						Back to Sign In
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>

