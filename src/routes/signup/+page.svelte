<script lang="ts">
    import { userSignUpInitiate } from "$lib/apis/auths";
    import OTPVerification from "$lib/components/OTPVerification.svelte";
    
    let name = "";
    let email = "";
    let password = "";
    let confirmPassword = "";
    let profileImageUrl = ""; // Handle image upload logic separately
    
    let isLoading = false;
    let error = "";
    let showOTPVerification = false;
    let registrationComplete = false;
    
    async function handleSignUp() {
        if (password !== confirmPassword) {
            error = "Passwords do not match";
            return;
        }
        
        isLoading = true;
        error = "";
        
        try {
            await userSignUpInitiate(name, email, password, profileImageUrl);
            showOTPVerification = true;
        } catch (err) {
            error = err.toString() || "Failed to register";
        } finally {
            isLoading = false;
        }
    }
    
    function handleVerified(event) {
        registrationComplete = true;
        // Redirect to login page or dashboard
        setTimeout(() => {
            window.location.href = "/login";
        }, 3000);
    }
</script>

{#if registrationComplete}
    <div class="text-center p-6">
        <h2 class="text-2xl font-semibold mb-4">Registration Complete!</h2>
        <p>Your account has been successfully activated. Redirecting to login...</p>
    </div>
{:else if showOTPVerification}
    <OTPVerification {email} on:verified={handleVerified} />
{:else}
    <div class="max-w-md mx-auto p-4">
        <h2 class="text-2xl font-semibold mb-4">Create an Account</h2>
        
        {#if error}
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {error}
            </div>
        {/if}
        
        <form on:submit|preventDefault={handleSignUp}>
            <!-- Registration form fields -->
            <div class="mb-4">
                <label for="name" class="block text-sm font-medium mb-2">Name</label>
                <input
                    type="text"
                    id="name"
                    bind:value={name}
                    class="w-full p-3 border rounded focus:ring focus:ring-primary focus:outline-none"
                    required
                />
            </div>
            
            <div class="mb-4">
                <label for="email" class="block text-sm font-medium mb-2">Email</label>
                <input
                    type="email"
                    id="email"
                    bind:value={email}
                    class="w-full p-3 border rounded focus:ring focus:ring-primary focus:outline-none"
                    required
                />
            </div>
            
            <div class="mb-4">
                <label for="password" class="block text-sm font-medium mb-2">Password</label>
                <input
                    type="password"
                    id="password"
                    bind:value={password}
                    class="w-full p-3 border rounded focus:ring focus:ring-primary focus:outline-none"
                    required
                />
            </div>
            
            <div class="mb-4">
                <label for="confirmPassword" class="block text-sm font-medium mb-2">Confirm Password</label>
                <input
                    type="password"
                    id="confirmPassword"
                    bind:value={confirmPassword}
                    class="w-full p-3 border rounded focus:ring focus:ring-primary focus:outline-none"
                    required
                />
            </div>
            
            <!-- Image upload section here -->
            
            <button
                type="submit"
                class="w-full bg-primary text-white py-3 rounded font-medium"
                disabled={isLoading}
            >
                {isLoading ? 'Registering...' : 'Register'}
            </button>
        </form>
        
        <p class="mt-4 text-center">
            Already have an account? <a href="/login" class="text-primary font-medium">Sign In</a>
        </p>
    </div>
{/if}