<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import gsap from 'gsap';
    import { t, currentLang } from '$lib/landing/translations';

    const features = [0, 1, 2, 3];
    let translate: (key: string) => string;

    // Subscribe to the derived store
    $: translate = $t;

    onMount(() => {
        const cards = document.querySelectorAll('.work-card');
        cards.forEach((card, index) => {
            gsap.from(card, {
                y: 50,
                opacity: 0,
                scrollTrigger: {
                    trigger: card,
                    start: "top 80%",
                    end: "top 60%",
                    scrub: true
                }
            });
        });
    });
</script>

<section class="py-16 md:py-24 bg-[var(--background)]">
    <div class="container mx-auto px-4 md:px-6 lg:px-8 max-w-[1440px]">
        <h2 class="text-4xl md:text-5xl font-['Inter'] font-semibold text-center mb-16 text-[var(--foreground)]">
            {translate('work.title')}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 mb-16">
            {#each features as index}
                <div 
                    class="work-card p-8 rounded-lg bg-[var(--surface-primary)] text-[var(--text-primary)] border border-[var(--border-light)] hover:border-[var(--border-medium)] transition-all duration-300"
                >
                    <h3 class="text-2xl font-['Inter'] font-semibold mb-4">
                        {translate(`work.features.${index}.title`)}
                    </h3>
                    <p class="text-lg font-['Inter'] opacity-80">
                        {translate(`work.features.${index}.description`)}
                    </p>
                </div>
            {/each}
        </div>
        <div class="flex justify-center">
            <button 
                class="bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300"
                on:click={() => goto('/auth')}
            >
                {translate('hero.cta')}
            </button>
        </div>
    </div>
</section>

<style>
    :global(:root) {
        --border-light: rgba(255, 255, 255, 0.1);
        --border-medium: rgba(255, 255, 255, 0.2);
    }

    :global(:root.dark) {
        --border-light: rgba(0, 0, 0, 0.1);
        --border-medium: rgba(0, 0, 0, 0.2);
    }
</style>
