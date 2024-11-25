<script lang="ts">
    import { goto } from '$app/navigation';
    import { WEBUI_NAME } from '$lib/stores';
    import { onMount } from 'svelte';
    import { currentLang, t } from '$lib/landing/translations';
    import Hero from '$lib/components/landing/Hero.svelte';
    import WorkSection from '$lib/components/landing/WorkSection.svelte';
    import FaqSection from '$lib/components/landing/FaqSection.svelte';
    import NewsletterSection from '$lib/components/landing/NewsletterSection.svelte';
    import Footer from '$lib/components/landing/Footer.svelte';
    import Navbar from '$lib/components/landing/Navbar.svelte';
    import InformationSection from '$lib/components/landing/InformationSection.svelte';
    import '$lib/styles/fonts.css';
    import '$lib/styles/style.css';
    import '../../tailwind.css';

    let isLoading = true;
    let mainContainer: HTMLElement;

    onMount(() => {
        // Set Cicero as the name
        WEBUI_NAME.set('Cicero');

        // Remove splash screen immediately for landing page
        document.getElementById('splash-screen')?.remove();
        isLoading = false;

        // Force scrollable container
        if (mainContainer) {
            mainContainer.style.height = '100vh';
            mainContainer.style.overflowY = 'auto';
        }

        // Force body to be non-scrollable
        document.body.style.overflow = 'hidden';
        document.body.style.height = '100vh';
        document.documentElement.style.overflow = 'hidden';
        document.documentElement.style.height = '100vh';
    });
</script>

<div class="landing-page">
    <div class="sticky top-0 z-50 bg-[var(--background)]">
        <Navbar />
    </div>
    <div bind:this={mainContainer} class="main-content">
        <div class="h-[calc(100vh-64px)] flex items-center justify-center">
            <Hero />
        </div>
        <div class="py-20">
            <InformationSection />
        </div>
        <div class="py-20">
            <WorkSection />
        </div>
        <div class="py-20">
            <FaqSection />
        </div>
        <div class="py-20">
            <NewsletterSection />
        </div>
        <Footer />
    </div>
</div>

<style>
    .landing-page {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: var(--background);
        display: flex;
        flex-direction: column;
    }

    .main-content {
        flex: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    :global(html), :global(body) {
        margin: 0;
        padding: 0;
        height: 100vh;
        overflow: hidden;
        overscroll-behavior: none;
    }
</style>
