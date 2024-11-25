<script lang="ts">
    import { onMount } from 'svelte';
    import gsap from 'gsap';
    import { t, currentLang } from '$lib/landing/translations';

    let sectionRef: HTMLElement;
    let translate: (key: string) => string;

    // Subscribe to the derived store
    $: translate = $t;

    onMount(() => {
        if (!sectionRef) return;

        gsap.from(sectionRef, {
            y: 50,
            opacity: 0,
            scrollTrigger: {
                trigger: sectionRef,
                start: "top 80%",
                end: "top 60%",
                scrub: true
            }
        });
    });
</script>

<section bind:this={sectionRef} class="py-16 bg-[var(--background)]">
    <div class="container mx-auto px-4 max-w-[1440px]">
        <div class="text-center">
            <h2 class="text-4xl md:text-5xl font-['Inter'] font-semibold mb-8 text-[var(--foreground)]">
                {translate('newsletter.title')}
            </h2>
            <p class="text-lg md:text-xl mb-8 text-[var(--foreground)] opacity-80">
                {translate('newsletter.description')}
            </p>
            <button 
                class="bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300"
            >
                {translate('newsletter.button')}
            </button>
        </div>
    </div>
</section>
