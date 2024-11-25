<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import gsap from 'gsap';
    import { t, currentLang } from '$lib/landing/translations';

    let infoText: HTMLElement;
    let infoImage: HTMLElement;
    let translate: (key: string) => string;

    // Subscribe to the derived store
    $: translate = $t;

    onMount(() => {
        if (!infoText || !infoImage) return;

        gsap.from(infoText, {
            x: "-100%",
            opacity: 0,
            scrollTrigger: {
                trigger: infoText,
                start: "top 80%",
                end: "top 50%",
                scrub: true
            }
        });

        gsap.from(infoImage, {
            scale: 0.5,
            opacity: 0,
            scrollTrigger: {
                trigger: infoImage,
                start: "top 80%",
                end: "top 50%",
                scrub: true
            }
        });
    });
</script>

<section class="py-16 md:py-24 bg-[var(--background)]">
    <div class="container mx-auto px-4 md:px-6 lg:px-8 max-w-[1440px]">
        <div class="grid md:grid-cols-2 items-center gap-8 md:gap-12">
            <div bind:this={infoText} class="text-center md:text-left">
                <h2 class="text-3xl md:text-4xl lg:text-[40px] font-bold mb-4 text-[var(--foreground)]">
                    {translate('information.title')}
                </h2>
                <p class="text-lg md:text-xl leading-relaxed opacity-80 text-[var(--foreground)]">
                    {translate('information.description')}
                    <span class="font-bold">{translate('information.descriptionBold')}</span>
                </p>
                
                <button 
                    class="mt-8 bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300"
                    on:click={() => goto('/auth')}
                >
                    {translate('hero.cta')}
                </button>
            </div>

            <div
                bind:this={infoImage}
                class="p-12 border border-[#B10508] rounded-[30px] bg-[rgba(255,255,255,0.10)] backdrop-blur-lg"
            >
                <div class="text-center">
                    <h3 class="text-2xl md:text-3xl font-bold mb-4 text-[var(--foreground)]">
                        {translate('information.title')}
                    </h3>
                </div>
            </div>
        </div>
    </div>
</section>
