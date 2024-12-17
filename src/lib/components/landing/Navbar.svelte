<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { t, toggleLanguage, currentLang } from '$lib/landing/translations';

    let isScrolled = false;
    let isDark = false;

    onMount(() => {
        const savedTheme = localStorage.getItem('theme');
        isDark = savedTheme
            ? savedTheme === 'dark'
            : window.matchMedia('(prefers-color-scheme: dark)').matches;
        updateTheme();

        const handleScroll = () => {
            isScrolled = window.scrollY > 50;
        };

        window.addEventListener('scroll', handleScroll);

        return () => {
            window.removeEventListener('scroll', handleScroll);
        };
    });

    function updateTheme() {
        if (isDark) {
            document.documentElement.classList.add('dark');
            document.documentElement.style.setProperty('--background', '#000000');
            document.documentElement.style.setProperty('--foreground', '#FFFFFF');
            document.documentElement.style.setProperty('--surface-primary', '#FFFFFF');
            document.documentElement.style.setProperty('--text-primary', '#000000');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.style.setProperty('--background', '#FFFFFF');
            document.documentElement.style.setProperty('--foreground', '#000000');
            document.documentElement.style.setProperty('--surface-primary', '#000000');
            document.documentElement.style.setProperty('--text-primary', '#FFFFFF');
        }
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }

    function toggleTheme() {
        isDark = !isDark;
        updateTheme();
    }
</script>

<div class="fixed w-full z-50">
    <div class="container mx-auto px-4 max-w-[1440px]">
        <nav
            class="flex items-center transition-all duration-500 justify-between py-2 {isScrolled
                ? 'md:py-2'
                : 'md:py-4'}"
        >
            <a
                href="/"
                class="logo font-ClashDisplay hover:scale-110 transition-all px-6 py-2 rounded-md flex items-center justify-center mt-6 bg-[var(--surface-primary)]"
            >
                <h1
                    class="text-[var(--text-primary)] text-[2.7rem] font-ClashDisplay font-semibold tracking-tight"
                >
                    CICERO
                </h1>
            </a>

            <div class="flex items-center gap-[30px]">
                <div class="social flex items-center gap-5">
                    <a
                        href="/about"
                        class="text-[var(--foreground)] hover:opacity-80 transition-all"
                    >
                        About
                    </a>
                    <a
                        href="https://blog.synthetic.lawyer"
                        target="_blank"
                        class="hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center bg-[var(--surface-primary)]"
                        style="width: 32px; height: 32px"
                    >
                        <img
                            src="/assets/icons/medium.svg"
                            height={16}
                            width={16}
                            alt="Medium"
                            class="w-4 h-4 {isDark ? '' : 'invert'}"
                        />
                    </a>
                    <button
                        on:click={toggleLanguage}
                        class="hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center text-xs font-ClashDisplay bg-[var(--surface-primary)] text-[var(--text-primary)]"
                        aria-label="Toggle language"
                        style="width: 32px; height: 32px; padding: 0 6px;"
                    >
                        <span class="font-bold tracking-normal text-[14px]">{$currentLang === 'en-US' ? 'PT' : 'EN'}</span>
                    </button>
                    <button
                        on:click={toggleTheme}
                        class="hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center bg-[var(--surface-primary)]"
                        aria-label="Toggle theme"
                        style="width: 32px; height: 32px"
                    >
                        {#if isDark}
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                class="text-[var(--text-primary)]"
                            >
                                <circle cx="12" cy="12" r="5" />
                                <line x1="12" y1="1" x2="12" y2="3" />
                                <line x1="12" y1="21" x2="12" y2="23" />
                                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                                <line x1="1" y1="12" x2="3" y2="12" />
                                <line x1="21" y1="12" x2="23" y2="12" />
                                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                            </svg>
                        {:else}
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                class="text-[var(--text-primary)]"
                            >
                                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                            </svg>
                        {/if}
                    </button>
                    <a
                        href="https://www.linkedin.com/company/cicero-contracts"
                        target="_blank"
                        class="hover:scale-110 transition-all p-2 rounded-full flex items-center justify-center bg-[var(--surface-primary)]"
                        style="width: 32px; height: 32px"
                    >
                        <img
                            src="/assets/icons/linkedin.svg"
                            height={16}
                            width={16}
                            alt="LinkedIn"
                            class="w-4 h-4 {isDark ? 'invert' : ''}"
                        />
                    </a>
                </div>
            </div>
        </nav>
    </div>
</div>

<style>
    @font-face {
        font-family: 'ClashDisplay';
        src: url('/assets/fonts/Inter-SemiBold.woff2') format('woff2');
        font-weight: 400;
        font-style: normal;
        font-display: swap;
    }

    @font-face {
        font-family: 'ClashDisplay';
        src: url('/assets/fonts/Inter-SemiBold.woff2') format('woff2');
        font-weight: 600;
        font-style: normal;
        font-display: swap;
    }
</style>
