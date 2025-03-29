<script>
    import { onMount } from 'svelte';
    import { mfaSetup, mfaEnable, mfaDisable, mfaGetBackupCodes, mfaRegenerateBackupCodes } from '$lib/apis/auths';
    import { toast } from 'svelte-sonner';
    
    export let token = '';
    export let visible = false;
    export let mfaEnabled = false;
    export let onUpdate = () => {};
    
    let step = mfaEnabled ? 'manage' : 'setup';
    let qrCodeUrl = '';
    let secret = '';
    let code = '';
    let backupCodes = [];
    let showBackupCodes = false;
    let loading = false;
    
    $: if (visible) {
        loadData();
    }
    
    async function loadData() {
        if (mfaEnabled) {
            step = 'manage';
        } else {
            step = 'setup';
            await loadSetupData();
        }
    }
    
    async function loadSetupData() {
        loading = true;
        try {
            const setupData = await mfaSetup(token);
            qrCodeUrl = setupData.qr_code;
            secret = setupData.secret;
        } catch (error) {
            toast.error(`Failed to load MFA setup: ${error}`);
        }
        loading = false;
    }
    
    async function getBackupCodes() {
        // Prompt for password
        const password = prompt("Enter your password to view backup codes");
        if (!password) return;
        
        loading = true;
        try {
            const response = await mfaGetBackupCodes(token, password);
            backupCodes = response.backup_codes || [];
            showBackupCodes = true;
        } catch (error) {
            toast.error(`Failed to get backup codes: ${error}`);
        }
        loading = false;
    }
    
    async function regenerateBackupCodes() {
        // Prompt for password
        const password = prompt("Enter your password to regenerate backup codes");
        if (!password) return;
        
        loading = true;
        try {
            const response = await mfaRegenerateBackupCodes(token, password);
            backupCodes = response.backup_codes || [];
            showBackupCodes = true;
            toast.success('Backup codes regenerated successfully');
        } catch (error) {
            toast.error(`Failed to regenerate backup codes: ${error}`);
        }
        loading = false;
    }
    
    async function enableMFA() {
        if (!code) {
            toast.error('Please enter the verification code');
            return;
        }
        
        loading = true;
        try {
            await mfaEnable(token, code);
            toast.success('Two-factor authentication enabled successfully');
            mfaEnabled = true;
            step = 'backup-codes';
            await getBackupCodes();
        } catch (error) {
            toast.error(`Failed to enable MFA: ${error}`);
        }
        loading = false;
    }
    
    async function disableMFA() {
        // First, validate that the user has entered a verification code
        if (!code) {
            toast.error('Please enter the verification code from your authenticator app');
            return;
        }
        
        // Then prompt for password
        const password = prompt("Enter your password to disable 2FA");
        if (!password) return;
        
        loading = true;
        try {
            await mfaDisable(token, password, code);
            toast.success('Two-factor authentication disabled successfully');
            mfaEnabled = false;
            onUpdate();
            handleClose();
        } catch (error) {
            toast.error(`Failed to disable MFA: ${error}`);
        }
        loading = false;
    }
    
    function handleClose() {
        code = '';
        showBackupCodes = false;
        step = mfaEnabled ? 'manage' : 'setup';
        visible = false;
    }
    
    function downloadBackupCodes() {
        const text = backupCodes.join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'mfa-backup-codes.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    async function copySecret() {
        try {
            await navigator.clipboard.writeText(secret);
            toast.success('Secret copied to clipboard');
        } catch (error) {
            console.error('Failed to copy secret:', error);
            
            // Fallback method if clipboard API fails
            const textArea = document.createElement('textarea');
            textArea.value = secret;
            textArea.style.position = 'fixed';  // Avoid scrolling to bottom
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    toast.success('Secret copied to clipboard');
                } else {
                    toast.error('Failed to copy secret');
                }
            } catch (err) {
                toast.error('Failed to copy secret');
            }
            
            document.body.removeChild(textArea);
        }
    }
    
    async function copyBackupCodes() {
        const text = backupCodes.join('\n');
        
        try {
            await navigator.clipboard.writeText(text);
            toast.success('Backup codes copied to clipboard');
        } catch (error) {
            console.error('Failed to copy backup codes:', error);
            
            // Fallback method if clipboard API fails
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';  // Avoid scrolling to bottom
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    toast.success('Backup codes copied to clipboard');
                } else {
                    toast.error('Failed to copy backup codes');
                }
            } catch (err) {
                toast.error('Failed to copy backup codes');
            }
            
            document.body.removeChild(textArea);
        }
    }
</script>

{#if visible}
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
    <div class="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div class="text-center mb-4">
            <h2 class="text-xl font-semibold dark:text-white">
                {#if step === 'setup'}
                    Set Up Two-Factor Authentication
                {:else if step === 'backup-codes'}
                    Save Your Backup Codes
                {:else if step === 'manage'}
                    Manage Two-Factor Authentication
                {:else if step === 'disable'}
                    Disable Two-Factor Authentication
                {/if}
            </h2>
        </div>
        
        {#if step === 'setup'}
            <div class="space-y-4">
                <p class="text-gray-600 dark:text-gray-400 text-sm">
                    Two-factor authentication adds an extra layer of security to your account. 
                    Scan the QR code below with an authenticator app like Google Authenticator or Authy.
                </p>
                
                {#if qrCodeUrl}
                    <div class="flex justify-center my-4">
                        <img src={qrCodeUrl} alt="QR Code" class="w-48 h-48 border dark:border-gray-700 rounded p-2 bg-white" />
                    </div>
                    
                    <div class="text-sm text-gray-600 dark:text-gray-400">
                        <p class="mb-2">If you can't scan the QR code, use this secret code in your authenticator app:</p>
                        <div class="flex items-center space-x-2 bg-gray-100 dark:bg-gray-800 p-2 rounded">
                            <code class="flex-1 font-mono text-sm">{secret}</code>
                            <button 
                                type="button" 
                                class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                                on:click={copySecret}
                            >
                                Copy
                            </button>
                        </div>
                    </div>
                    
                    <div class="mt-4">
                        <label for="verification-code" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Verification Code
                        </label>
                        <input
                            id="verification-code"
                            bind:value={code}
                            type="tel"
                            pattern="[0-9]*"
                            placeholder="Enter 6-digit code"
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-600 dark:bg-gray-800 dark:text-white focus:outline-none"
                            inputmode="numeric"
                            autocomplete="one-time-code"
                            maxlength="6"
                        />
                    </div>
                {:else}
                    <div class="flex justify-center my-4">
                        <span class="inline-block h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></span>
                    </div>
                {/if}
                
                <div class="flex justify-end space-x-3 mt-4">
                    <button
                        type="button"
                        on:click={handleClose}
                        class="bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-4 py-2 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none">
                        Cancel
                    </button>
                    <button
                        type="button"
                        on:click={enableMFA}
                        class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none flex items-center space-x-2 disabled:opacity-75"
                        disabled={loading || !qrCodeUrl}>
                        {#if loading}
                            <span class="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                        {/if}
                        <span>Enable</span>
                    </button>
                </div>
            </div>
        {:else if step === 'backup-codes'}
            <div class="space-y-4">
                <p class="text-gray-600 dark:text-gray-400 text-sm">
                    Save these backup codes in a secure place. If you lose access to your authenticator app, 
                    you can use one of these codes to sign in. Each code can only be used once.
                </p>
                
                <div class="bg-gray-100 dark:bg-gray-800 p-3 rounded">
                    <div class="grid grid-cols-2 gap-2">
                        {#each backupCodes as code}
                            <div class="font-mono text-sm">{code}</div>
                        {/each}
                    </div>
                </div>
                
                <div class="flex space-x-2">
                    <button 
                        type="button" 
                        class="flex-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm border border-blue-600 dark:border-blue-400 rounded px-3 py-1"
                        on:click={downloadBackupCodes}
                    >
                        Download
                    </button>
                    <button 
                        type="button" 
                        class="flex-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm border border-blue-600 dark:border-blue-400 rounded px-3 py-1"
                        on:click={copyBackupCodes}
                    >
                        Copy
                    </button>
                </div>
                
                <div class="flex justify-end mt-4">
                    <button
                        type="button"
                        on:click={() => { onUpdate(); handleClose(); }}
                        class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none">
                        Done
                    </button>
                </div>
            </div>
        {:else if step === 'manage'}
            <div class="space-y-4">
                <p class="text-gray-600 dark:text-gray-400 text-sm">
                    Two-factor authentication is currently enabled for your account.
                </p>
                
                <div class="flex flex-col space-y-3">
                    <button
                        type="button"
                        on:click={getBackupCodes}
                        class="text-left border border-gray-300 dark:border-gray-700 rounded-md p-3 hover:bg-gray-50 dark:hover:bg-gray-800">
                        <div class="font-medium">View backup codes</div>
                        <div class="text-sm text-gray-600 dark:text-gray-400">See your backup codes for account recovery</div>
                    </button>
                    
                    <button
                        type="button"
                        on:click={regenerateBackupCodes}
                        class="text-left border border-gray-300 dark:border-gray-700 rounded-md p-3 hover:bg-gray-50 dark:hover:bg-gray-800">
                        <div class="font-medium">Generate new backup codes</div>
                        <div class="text-sm text-gray-600 dark:text-gray-400">Creates new backup codes and invalidates old ones</div>
                    </button>
                    
                    <button
                        type="button"
                        on:click={() => step = 'disable'}
                        class="text-left border border-red-200 dark:border-red-900 rounded-md p-3 hover:bg-red-50 dark:hover:bg-red-900/20">
                        <div class="font-medium text-red-600 dark:text-red-400">Disable two-factor authentication</div>
                        <div class="text-sm text-red-500 dark:text-red-400">Removes the additional security layer from your account</div>
                    </button>
                </div>
                
                {#if showBackupCodes}
                    <div class="mt-4 p-3 border rounded border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                        <h3 class="font-medium mb-2">Your backup codes</h3>
                        <div class="bg-white dark:bg-gray-900 p-3 rounded">
                            <div class="grid grid-cols-2 gap-2">
                                {#each backupCodes as code}
                                    <div class="font-mono text-sm">{code}</div>
                                {/each}
                            </div>
                        </div>
                        
                        <div class="flex space-x-2 mt-3">
                            <button 
                                type="button" 
                                class="flex-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm border border-blue-600 dark:border-blue-400 rounded px-3 py-1"
                                on:click={downloadBackupCodes}
                            >
                                Download
                            </button>
                            <button 
                                type="button" 
                                class="flex-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm border border-blue-600 dark:border-blue-400 rounded px-3 py-1"
                                on:click={copyBackupCodes}
                            >
                                Copy
                            </button>
                        </div>
                    </div>
                {/if}
                
                <div class="flex justify-end mt-4">
                    <button
                        type="button"
                        on:click={handleClose}
                        class="bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-4 py-2 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none">
                        Close
                    </button>
                </div>
            </div>
        {:else if step === 'disable'}
            <div class="space-y-4">
                <p class="text-gray-600 dark:text-gray-400 text-sm">
                    To disable two-factor authentication, enter the verification code from your authenticator app.
                </p>
                
                <div>
                    <label for="disable-code" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Verification Code
                    </label>
                    <input
                        id="disable-code"
                        bind:value={code}
                        type="tel"
                        pattern="[0-9]*"
                        placeholder="Enter 6-digit code"
                        class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-600 dark:bg-gray-800 dark:text-white focus:outline-none"
                        inputmode="numeric"
                        autocomplete="one-time-code"
                        maxlength="6"
                        on:focus={(e) => e.target.select()}
                    />
                </div>
                
                <div class="flex justify-end space-x-3 mt-4">
                    <button
                        type="button"
                        on:click={() => step = 'manage'}
                        class="bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-4 py-2 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none">
                        Cancel
                    </button>
                    <button
                        type="button"
                        on:click={disableMFA}
                        class="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none flex items-center space-x-2 disabled:opacity-75"
                        disabled={loading}>
                        {#if loading}
                            <span class="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                        {/if}
                        <span>Disable</span>
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>
{/if}