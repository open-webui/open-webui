<script lang="ts">
    import { t } from '$lib/landing/translations';
</script>

<section class="w-full h-screen flex flex-col justify-center bg-[var(--background)] relative">
    <div class="w-full max-w-[1440px] mx-auto text-center px-4">
        <div class="w-full text-5xl md:text-6xl lg:text-[80px] leading-tight lg:leading-[80px] font-Inter font-bold uppercase text-[var(--foreground)]">
            {$t('hero.title')}
        </div>
        <div class="mt-2 text-[1.5rem] md:text-[1.875rem] font-Inter font-normal leading-[30px] bg-[#FFFF05]/70 inline-block px-4 py-2 rounded-lg">
            [ {$t('hero.subtitle')} ]
        </div>
    </div>

    <!-- Try it now button near bottom with slightly more padding -->
    <div class="absolute bottom-28 left-1/2 transform -translate-x-1/2">
        <button
            class="try-it-now-btn bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-sans text-[1rem] font-medium leading-[20px] rounded-full uppercase transition-all duration-300"
            on:click={() => {
                if (localStorage.token) {
                    window.location.href = '/workspace';
                } else {
                    window.location.href = '/auth';
                }
            }}
        >
            {$t('hero.cta')}
        </button>
    </div>
</section>

<style>
    :global(:root) {
        --background: #ffffff;
        --foreground: #000000;
        --surface-primary: #000000;
        --text-primary: #ffffff;
        --red-light: #FF4D4D;
        --red-dark: #CD0003;
    }

    :global(:root.dark) {
        --background: #000000;
        --foreground: #ffffff;
        --surface-primary: #ffffff;
        --text-primary: #000000;
    }

    :global(.try-it-now-btn:hover) {
        color: white !important;
    }
</style>
