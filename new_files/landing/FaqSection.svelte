<script lang="ts">
    import { onMount } from 'svelte';
    import gsap from 'gsap';
    import { t, currentLang } from '$lib/landing/translations';

    let openIndex = -1;
    let sectionRef: HTMLElement;
    let headingRef: HTMLElement;
    let translate: (key: string) => string;

    // Subscribe to the derived store
    $: translate = $t;

    const questions = [
        { q: 'faq.q1', a: 'faq.a1' },
        { q: 'faq.q2', a: 'faq.a2' },
        { q: 'faq.q3', a: 'faq.a3' },
        { q: 'faq.q4', a: 'faq.a4' }
    ];

    function toggleAccordion(index: number) {
        openIndex = openIndex === index ? -1 : index;
    }

    onMount(() => {
        if (!sectionRef || !headingRef) return;

        gsap.from(headingRef, {
            y: 50,
            opacity: 0,
            scrollTrigger: {
                trigger: headingRef,
                start: "top 80%",
                end: "top 60%",
                scrub: true
            }
        });

        const items = sectionRef.querySelectorAll('.faq-item');
        items.forEach((item, index) => {
            gsap.from(item, {
                x: index % 2 === 0 ? -50 : 50,
                opacity: 0,
                scrollTrigger: {
                    trigger: item,
                    start: "top 80%",
                    end: "top 60%",
                    scrub: true
                }
            });
        });
    });
</script>

<section bind:this={sectionRef} class="py-16 bg-[var(--background)]">
    <div class="container mx-auto px-4 max-w-[1440px]">
        <div bind:this={headingRef}>
            <h2 class="text-4xl md:text-5xl font-['Inter'] font-semibold text-center mb-16 text-[var(--foreground)]">
                {translate('faq.title')}
            </h2>
        </div>

        <div class="grid md:grid-cols-2 gap-8">
            {#each questions as { q, a }, index}
                <button
                    class="faq-item w-full text-left p-6 bg-[var(--surface-primary)] text-[var(--text-primary)] rounded-lg shadow-sm hover:shadow-md transition-all duration-200"
                    on:click={() => toggleAccordion(index)}
                    aria-expanded={openIndex === index}
                >
                    <div class="flex justify-between items-center">
                        <h3 class="text-xl font-semibold">
                            {translate(q)}
                        </h3>
                        <svg
                            class="w-6 h-6 transform transition-transform duration-200 {openIndex === index ? 'rotate-180' : ''}"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M19 9l-7 7-7-7"
                            />
                        </svg>
                    </div>
                    {#if openIndex === index}
                        <p class="mt-4 opacity-80">
                            {translate(a)}
                        </p>
                    {/if}
                </button>
            {/each}
        </div>
    </div>
</section>
