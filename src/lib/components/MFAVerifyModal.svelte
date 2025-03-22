<script>
    import { onMount } from 'svelte';
    import { mfaVerify, mfaVerifyBackupCode } from '$lib/apis/auths';
    import { toast } from 'svelte-sonner';
    
    export let visible = false;
    export let onVerified = () => {};
    
    let code = '';
    let useBackupCode = false;
    let backupCode = '';
    let loading = false;
    
    const handleVerify = async () => {
        if (loading) return;
        loading = true;
        
        try {
            let sessionUser;
            
            if (useBackupCode) {
                if (!backupCode) {
                    toast.error('Please enter a backup code');
                    loading = false;
                    return;
                }
                
                sessionUser = await mfaVerifyBackupCode(backupCode);
            } else {
                if (!code) {
                    toast.error('Please enter a verification code');
                    loading = false;
                    return;
                }
                
                sessionUser = await mfaVerify(code);
            }
            
            if (sessionUser) {
                // Ensure token is updated in localStorage for frontend authentication
                if (sessionUser.token) {
                    localStorage.token = sessionUser.token;
                }
                
                onVerified(sessionUser);
                code = '';
                backupCode = '';
                visible = false;
            }
        } catch (error) {
            toast.error(`${error}`);
        }
        
        loading = false;
    };
    
    const handleCancel = () => {
        code = '';
        backupCode = '';
        visible = false;
    };
    
    // Auto-focus the input when modal opens
    $: if (visible) {
        setTimeout(() => {
            const input = document.getElementById(useBackupCode ? 'backup-code-input' : 'code-input');
            if (input) input.focus();
        }, 100);
    }
</script>

{#if visible}
<div class="fixed inset-0 z-[9999] flex items-center justify-center bg-black bg-opacity-50">
    <div class="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 max-w-sm w-full" style="position: relative; z-index: 10000;">
        <div class="text-center mb-4">
            <h2 class="text-xl font-semibold dark:text-white">Two-Factor Authentication</h2>
            <p class="text-gray-600 dark:text-gray-400 text-sm mt-1">
                {#if useBackupCode}
                    Please enter one of your backup codes
                {:else}
                    Enter the code from your authenticator app
                {/if}
            </p>
        </div>
        
        <form on:submit|preventDefault={handleVerify} class="space-y-4">
            {#if !useBackupCode}
                <div class="relative z-[10001]">
                    <label for="code-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Verification Code
                    </label>
                    <input
                        id="code-input"
                        bind:value={code}
                        type="tel"
                        pattern="[0-9]*"
                        placeholder="Enter 6-digit code"
                        class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-600 dark:bg-gray-800 dark:text-white focus:outline-none cursor-text"
                        style="position: relative; z-index: 10001;"
                        inputmode="numeric"
                        autocomplete="one-time-code"
                        maxlength="6"
                    />
                </div>
            {:else}
                <div class="relative z-[10001]">
                    <label for="backup-code-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Backup Code
                    </label>
                    <input
                        id="backup-code-input"
                        bind:value={backupCode}
                        type="text"
                        placeholder="Enter backup code"
                        class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-600 dark:bg-gray-800 dark:text-white focus:outline-none cursor-text"
                        style="position: relative; z-index: 10001;"
                    />
                </div>
            {/if}
            
            <div class="flex justify-between relative z-[10001]">
                <button
                    type="button"
                    on:click={() => useBackupCode = !useBackupCode}
                    class="text-sm text-gray-600 dark:text-gray-400 hover:underline focus:outline-none cursor-pointer"
                    style="position: relative; z-index: 10001;">
                    {useBackupCode ? 'Use authenticator app' : 'Use backup code'}
                </button>
            </div>
            
            <div class="flex justify-end space-x-3 mt-4 relative z-[10001]">
                <button
                    type="button"
                    on:click={handleCancel}
                    class="bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-4 py-2 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none cursor-pointer"
                    style="position: relative; z-index: 10001;">
                    Cancel
                </button>
                <button
                    type="submit"
                    class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none flex items-center space-x-2 disabled:opacity-75 cursor-pointer"
                    style="position: relative; z-index: 10001;"
                    disabled={loading}>
                    {#if loading}
                        <span class="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    {/if}
                    <span>Verify</span>
                </button>
            </div>
        </form>
    </div>
</div>
{/if}