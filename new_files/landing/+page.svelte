<script lang="ts">
    import { goto } from '$app/navigation';
    import { WEBUI_NAME } from '$lib/stores';
    import { onMount } from 'svelte';
    import Hero from '$lib/components/landing/Hero.svelte';
    import WorkSection from '$lib/components/landing/WorkSection.svelte';
    import FaqSection from '$lib/components/landing/FaqSection.svelte';
    import NewsletterSection from '$lib/components/landing/NewsletterSection.svelte';
    import Footer from '$lib/components/landing/Footer.svelte';
    import Navbar from '$lib/components/landing/Navbar.svelte';
    import InformationSection from '$lib/components/landing/InformationSection.svelte';

    let isLoading = true;

    onMount(() => {
        // Remove splash screen immediately for landing page
        document.getElementById('splash-screen')?.remove();
        isLoading = false;
    });
</script>

{#if isLoading}
<div class="min-h-screen bg-[var(--background)] flex items-center justify-center">
    <div class="text-[var(--foreground)] text-2xl font-bold">Loading... Carregando...</div>
</div>
{:else}
<div class="min-h-screen bg-[var(--background)] flex flex-col">
    <Navbar />

    <main class="flex-grow">
        <Hero />
        <InformationSection />
        <WorkSection />
        <FaqSection />
        <NewsletterSection />
    </main>

    <Footer />
</div>
{/if}

<style>
    :global(:root) {
        --background: #ffffff;
        --foreground: #000000;
        --surface-primary: #000000;
        --text-primary: #ffffff;
    }

    :global(:root.dark) {
        --background: #000000;
        --foreground: #ffffff;
        --surface-primary: #ffffff;
        --text-primary: #000000;
    }
</style>
