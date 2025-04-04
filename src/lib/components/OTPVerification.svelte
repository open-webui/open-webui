<script lang="ts">
    import { verifyUserSignUp } from "$lib/apis/auths";
    import { createEventDispatcher } from "svelte";
    
    export let email: string;
    
    let otpCode = "";
    let isLoading = false;
    let error = "";
    
    const dispatch = createEventDispatcher();
    
    async function handleSubmit() {
        isLoading = true;
        error = "";
        
        try {
            const result = await verifyUserSignUp(email, otpCode);
            dispatch("verified", result);
        } catch (err) {
            error = err.toString() || "Failed to verify OTP code";
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="flex flex-col items-center justify-center max-w-md mx-auto p-4">
    <h2 class="text-2xl font-semibold mb-4">Account Activation Pending</h2>
    <p class="text-center mb-6">
        We've sent a verification code to <strong>{email}</strong>. 
        Please enter the code below to activate your account.
    </p>
    
    {#if error}
        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 w-full">
            {error}
        </div>
    {/if}
    
    <form on:submit|preventDefault={handleSubmit} class="w-full">
        <div class="mb-4">
            <label for="otp" class="block text-sm font-medium mb-2">Verification Code</label>
            <input
                type="text"
                id="otp"
                bind:value={otpCode}
                class="w-full p-3 border rounded focus:ring focus:ring-primary focus:outline-none"
                placeholder="Enter OTP code"
                required
            />
        </div>
        
        <button
            type="submit"
            class="w-full bg-primary text-white py-3 rounded font-medium"
            disabled={isLoading}
        >
            {isLoading ? 'Verifying...' : 'Verify Account'}
        </button>
    </form>
</div>