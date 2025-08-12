<script>
    import { onMount, getContext } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { user } from '$lib/stores';
    import { 
        getTotpStatus, 
        startTotpSetup, 
        enableTotp, 
        disableTotp, 
        getTotpBackupCodes, 
        regenerateTotpBackupCodes,
    } from '$lib/apis/auths';
    import { copyToClipboard } from '$lib/utils';

    const i18n = getContext('i18n');

    const isClipboardSupported = () => {
        return navigator.clipboard && window.isSecureContext;
    };

    // State variables
    let totpEnabled = false;
    let showSetup = false;
    let showBackupCodes = false;
    let showDisableConfirm = false;
    let setupStep = 'initial'; // 'initial', 'qr', 'verify'
    
    // Setup data
    let qrCodeUrl = '';
    let secretKey = '';
    let verificationCode = '';
    
    // Backup codes
    let backupCodes = [];
    
    // Disable confirmation
    let disablePassword = '';
    
    // Loading states
    let loading = false;
    let setupLoading = false;

    // Get current user's TOTP status
    onMount(async () => {
        await checkTotpStatus();
    });

    const checkTotpStatus = async () => {
        try {
            const data = await getTotpStatus(localStorage.token);
            totpEnabled = data.enabled || false;
            console.log('TOTP Status:', { enabled: totpEnabled, data });
        } catch (error) {
            console.error('Error checking TOTP status:', error);
            // Don't show error toast for status check failures
            // toast.error('Failed to check 2FA status: ' + error.message);
        }
    };

    const startTotpSetupFlow = async () => {
        // Check if TOTP is already enabled before starting setup
        if (totpEnabled) {
            toast.error('Two-factor authentication is already enabled for this account');
            return;
        }

        setupLoading = true;
        try {
            const data = await startTotpSetup(localStorage.token);
            qrCodeUrl = data.qr_code;
            secretKey = data.secret;
            backupCodes = data.backup_codes;
            
            showSetup = true;
            setupStep = 'qr';
            
        } catch (error) {
            console.error('TOTP setup error:', error);
            if (error.message.includes('already enabled')) {
                toast.error('Two-factor authentication is already enabled for this account');
                // Refresh the status to make sure UI is correct
                await checkTotpStatus();
            } else {
                toast.error('Failed to start 2FA setup: ' + error.message);
            }
        } finally {
            setupLoading = false;
        }
    };

    const completeTotpSetup = async () => {
        if (!verificationCode || verificationCode.length !== 6) {
            toast.error('Please enter a valid 6-digit code');
            return;
        }

        setupLoading = true;
        try {
            const data = await enableTotp(localStorage.token, verificationCode);
            
            // The backend doesn't return backup_codes in enableTotp response
            // Use the ones from startTotpSetup instead (they should be in the setup data)
            // If you need to get them separately, call getTotpBackupCodes
            
            totpEnabled = true;
            setupStep = 'verify';
            toast.success('Two-factor authentication has been enabled!');
            
        } catch (error) {
            console.error('TOTP enable error:', error);
            toast.error('Failed to enable 2FA: ' + error.message);
        } finally {
            setupLoading = false;
        }
    };

    const requestDisableTotp = () => {
        showDisableConfirm = true;
        disablePassword = '';
    };

    const confirmDisableTotp = async () => {
        if (!disablePassword.trim()) {
            toast.error('Please enter your password');
            return;
        }

        loading = true;
        try {
            await disableTotp(localStorage.token, disablePassword);
            totpEnabled = false;
            showDisableConfirm = false;
            disablePassword = '';
            toast.success('Two-factor authentication has been disabled');
            
        } catch (error) {
            toast.error('Failed to disable 2FA: ' + error.message);
        } finally {
            loading = false;
        }
    };

    const cancelDisableTotp = () => {
        showDisableConfirm = false;
        disablePassword = '';
    };

    const viewBackupCodes = async () => {
        loading = true;
        try {
            const data = await getTotpBackupCodes(localStorage.token);
            backupCodes = data.backup_codes;
            showBackupCodes = true;
            
        } catch (error) {
            toast.error('Failed to load backup codes: ' + error.message);
        } finally {
            loading = false;
        }
    };

    const regenerateTotpBackupCodesFlow = async () => {
        if (!confirm('Are you sure? This will invalidate all existing backup codes.')) {
            return;
        }

        loading = true;
        try {
            const data = await regenerateTotpBackupCodes(localStorage.token);
            backupCodes = data.backup_codes;
            toast.success('New backup codes generated');
            
        } catch (error) {
            toast.error('Failed to regenerate backup codes: ' + error.message);
        } finally {
            loading = false;
        }
    };

    const closeSetup = () => {
        showSetup = false;
        setupStep = 'initial';
        qrCodeUrl = '';
        secretKey = '';
        verificationCode = '';
    };

    const closeBackupCodes = () => {
        showBackupCodes = false;
        backupCodes = [];
    };
</script>

<div class="my-2">
    <div class="flex justify-between items-center text-sm mb-2">
        <div class="font-medium">{$i18n.t('Two-Factor Authentication')}</div>
        <div class="flex items-center">
            {#if totpEnabled}
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    {$i18n.t('Enabled')}
                </span>
            {:else}
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                    {$i18n.t('Disabled')}
                </span>
            {/if}
        </div>
    </div>

    <div class="text-xs text-gray-600 dark:text-gray-400 mb-3">
        Add an extra layer of security to your account with TOTP-based two-factor authentication.
    </div>

    <div class="flex gap-2">
        {#if !totpEnabled}
            <button
                class="text-xs font-medium text-gray-800 dark:text-gray-400 rounded-full px-4 py-1.5 bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 disabled:opacity-50 transition"
                on:click={startTotpSetupFlow}
                disabled={setupLoading}
            >
                {setupLoading ? 'Setting up...' : $i18n.t('Enable 2FA')}
            </button>
        {:else}
            <button
                class="text-xs font-medium text-gray-800 dark:text-gray-400 rounded-full px-4 py-1.5 bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 disabled:opacity-50 transition"
                on:click={viewBackupCodes}
                disabled={loading}
            >
                {$i18n.t('Backup Codes')}
            </button>
            <button
                class="text-xs font-medium text-white rounded-full px-4 py-1.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 transition"
                on:click={requestDisableTotp}
                disabled={loading}
            >
                {loading ? 'Disabling...' : $i18n.t('Disable 2FA')}
            </button>
        {/if}
    </div>
</div>

<!-- TOTP Setup Modal -->
{#if showSetup}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold dark:text-white">{$i18n.t('Set Up Two-Factor Authentication')}</h3>
                <button
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    on:click={closeSetup}
                >
                    ✕
                </button>
            </div>

            {#if setupStep === 'qr'}
                <div class="text-center">
                    <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                    </p>
                    
                    <div class="flex justify-center mb-4">
                        <img src={qrCodeUrl} alt="TOTP QR Code" class="border border-gray-300 dark:border-gray-600 rounded" />
                    </div>

                    <div class="mb-4">
                        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">Or enter this key manually:</p>
                        <div class="bg-gray-100 dark:bg-gray-700 p-2 rounded text-sm font-mono break-all">
                            {secretKey}
                        </div>
                        <button
                            class="text-xs text-blue-600 hover:text-blue-700 mt-1"
                            on:click={() => copyToClipboard(secretKey)}
                        >
                            Copy key
                        </button>
                    </div>

                    <div class="mb-4">
                        <label for="verificationCode" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Enter verification code
                        </label>
                        <input
                            id="verificationCode"
                            bind:value={verificationCode}
                            type="text"
                            placeholder="000000"
                            maxlength="6"
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-center text-lg tracking-widest bg-transparent dark:text-white"
                        />
                    </div>

                    <button
                        class="w-full bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 py-2 rounded-full font-medium disabled:opacity-50 transition"
                        on:click={completeTotpSetup}
                        disabled={setupLoading || verificationCode.length !== 6}
                    >
                        {setupLoading ? 'Verifying...' : $i18n.t('Enable 2FA')}
                    </button>
                </div>
            {:else if setupStep === 'verify'}
                <div class="text-center">
                    <div class="mb-4">
                        <div class="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg class="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h4 class="text-lg font-semibold text-green-800 dark:text-green-200 mb-2">{$i18n.t('2FA Enabled Successfully!')}</h4>
                        <p class="text-sm text-gray-600 dark:text-gray-400">
                            Save these backup codes in a safe place. You can use them to access your account if you lose your authenticator device.
                        </p>
                    </div>

                    <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
                        <h5 class="font-medium text-yellow-800 dark:text-yellow-200 mb-2">{$i18n.t('Backup Codes')}</h5>
                        <div class="grid grid-cols-2 gap-2 text-sm font-mono">
                            {#each backupCodes as code}
                                <div class="bg-white dark:bg-gray-700 px-2 py-1 rounded border text-center">
                                    {code}
                                </div>
                            {/each}
                        </div>
                        {#if isClipboardSupported()}
                            <button
                                class="mt-2 text-xs text-blue-600 hover:text-blue-700"
                                on:click={() => copyToClipboard(backupCodes.join('\n'))}
                            >
                                Copy all codes
                            </button>
                        {/if}
                    </div>

                    <button
                        class="w-full bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 py-2 rounded-full font-medium transition"
                        on:click={closeSetup}
                    >
                        {$i18n.t('Done')}
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}

<!-- Backup Codes Modal -->
{#if showBackupCodes}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold dark:text-white">{$i18n.t('Backup Codes')}</h3>
                <button
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    on:click={closeBackupCodes}
                >
                    ✕
                </button>
            </div>

            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
                These codes can be used to access your account if you lose your authenticator device. Each code can only be used once.
            </p>

            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
                <div class="grid grid-cols-2 gap-2 text-sm font-mono">
                    {#each backupCodes as code}
                        <div class="bg-white dark:bg-gray-600 px-2 py-1 rounded border text-center">
                            {code}
                        </div>
                    {/each}
                </div>
            </div>

            <div class="flex space-x-3">
                {#if isClipboardSupported()}
                    <button
                        class="flex-1 text-xs font-medium text-gray-800 dark:text-gray-400 rounded-full px-4 py-2 bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
                        on:click={() => copyToClipboard(backupCodes.join('\n'))}
                    >
                        {$i18n.t('Copy All')}
                    </button>
                {/if}
                <button
                    class="flex-1 text-xs font-medium text-white rounded-full px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 transition"
                    on:click={regenerateTotpBackupCodesFlow}
                    disabled={loading}
                >
                    {loading ? 'Generating...' : $i18n.t('Regenerate')}
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Password Confirmation Modal for Disable -->
{#if showDisableConfirm}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold dark:text-white">{$i18n.t('Disable Two-Factor Authentication')}</h3>
                <button
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    on:click={cancelDisableTotp}
                >
                    ✕
                </button>
            </div>

            <div class="mb-4">
                <div class="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                            </svg>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-red-800 dark:text-red-200">
                                <strong>Warning:</strong> Disabling 2FA will make your account less secure. Please enter your password to confirm.
                            </p>
                        </div>
                    </div>
                </div>

                <label for="disablePassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {$i18n.t('Current Password')}
                </label>
                <input
                    id="disablePassword"
                    bind:value={disablePassword}
                    type="password"
                    placeholder={$i18n.t('Enter your password')}
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-transparent dark:text-white"
                    autofocus
                />
            </div>

            <div class="flex space-x-3">
                <button
                    class="flex-1 text-xs font-medium text-gray-800 dark:text-gray-400 rounded-full px-4 py-2 bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
                    on:click={cancelDisableTotp}
                >
                    {$i18n.t('Cancel')}
                </button>
                <button
                    class="flex-1 text-xs font-medium text-white rounded-full px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 transition"
                    on:click={confirmDisableTotp}
                    disabled={loading || !disablePassword.trim()}
                >
                    {loading ? 'Disabling...' : $i18n.t('Disable 2FA')}
                </button>
            </div>
        </div>
    </div>
{/if}