<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import gsap from 'gsap';
    import { t, currentLang } from '$lib/landing/translations';

    let animatedText: HTMLElement;
    let heroButton: HTMLElement;
    let heroText: HTMLElement;
    let timeline: gsap.core.Timeline;
    let translate: (key: string) => string;

    // Subscribe to the derived store
    $: translate = $t;

    function initializeAnimation() {
        if (!animatedText) return;
        
        // Kill existing animation if it exists
        if (timeline) {
            timeline.kill();
        }
        
        // Create new timeline
        timeline = gsap.timeline();
        
        // Get the current translation first
        const currentText = translate('hero.subtitle');
        
        // Set initial state with dot
        animatedText.innerHTML = `[ <span class="pulsating-dot"></span> ]`;
        gsap.set(animatedText, { opacity: 0 });
        
        // Fade in with dot
        timeline.to(animatedText, { 
            opacity: 1,
            duration: 0.3
        });
        
        // Wait for 1.5 seconds while dot pulsates
        timeline.to({}, { duration: 1.5 });
        
        // Text appears from left to right
        const words = currentText.split(' ');
        const steps = words.length;
        
        for (let i = 0; i <= steps; i++) {
            const visibleWords = words.slice(0, i);
            const remainingSpace = " ".repeat(Math.max(1, 3));
            
            timeline.to(animatedText, {
                innerHTML: `[${remainingSpace}${visibleWords.join(' ')}${remainingSpace}]`,
                duration: 0.2,
                ease: "none"
            });
        }
    }

    // Subscribe to language changes and translation updates
    $: if (animatedText) {
        initializeAnimation();
    }

    onMount(() => {
        try {
            // Create scroll animations
            const scrollTl = gsap.timeline({
                scrollTrigger: {
                    trigger: ".heroSection",
                    start: "top top",
                    end: "bottom top",
                    pin: true,
                    scrub: 1
                }
            });

            if (heroText && heroButton) {
                scrollTl.to([heroText, heroButton], {
                    y: "-100%",
                    opacity: 0,
                    duration: 1,
                    ease: "power1.inOut"
                });
            }

            return () => {
                if (timeline) {
                    timeline.kill();
                }
                // Kill all ScrollTrigger instances for this component
                ScrollTrigger.getAll().forEach(trigger => {
                    trigger.kill();
                });
            };
        } catch (error) {
            console.error('Error initializing animations:', error);
        }
    });
</script>

<section class="heroSection w-full h-screen flex items-center justify-center relative bg-[var(--background)]">
    <div
        bind:this={heroText}
        class="w-full max-w-[1440px] mx-auto text-center"
    >
        <div class="w-full text-5xl md:text-6xl lg:text-[80px] leading-tight lg:leading-[80px] font-Inter font-bold uppercase text-[var(--foreground)]">
            {translate('hero.title')}
        </div>
        <div class="mt-2 text-[1.5rem] md:text-[1.875rem] font-Inter font-normal leading-[30px] bg-[#FFFF05]/70 inline-block px-4 py-2 rounded-lg">
            <span bind:this={animatedText}></span>
        </div>
    </div>

    <button
        bind:this={heroButton}
        class="try-it-now-btn absolute bottom-20 left-1/2 -translate-x-1/2 bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300"
        on:click={() => {
            if (localStorage.token) {
                window.location.href = '/workspace';
            } else {
                window.location.href = '/auth';
            }
        }}
    >
        {translate('hero.cta')}
    </button>
</section>

<style>
    :global(:root) {
        --background: #ffffff;
        --foreground: #0a0a0a;
        --surface-primary: #0a0a0a;
        --text-primary: #ffffff;
        --red-light: #FF4D4D;
        --red-dark: #CD0003;
    }

    :global(:root.dark) {
        --background: #0a0a0a;
        --foreground: #ededed;
        --surface-primary: #ffffff;
        --text-primary: #0a0a0a;
    }

    .pulsating-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        background-color: currentColor;
        border-radius: 50%;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% {
            transform: scale(0.8);
            opacity: 0.5;
        }
        50% {
            transform: scale(1.2);
            opacity: 1;
        }
        100% {
            transform: scale(0.8);
            opacity: 0.5;
        }
    }

    :global(.try-it-now-btn:hover) {
        color: white !important;
    }
</style>
