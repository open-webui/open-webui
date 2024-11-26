<script lang="ts">
    import { t } from '$lib/landing/translations';
</script>

<footer class="w-full py-12 bg-[var(--background)]">
    <div class="w-full max-w-[1440px] mx-auto px-4">
        <div class="flex flex-col items-center gap-8">
            <!-- CICERO Logo with same styling as navbar -->
            <div class="font-ClashDisplay px-6 py-2 rounded-md flex items-center justify-center bg-[var(--surface-primary)]">
                <h1 class="text-[var(--text-primary)] text-[2.7rem] font-ClashDisplay font-semibold tracking-tight">
                    CICERO
                </h1>
            </div>

            <!-- Links -->
            <div class="flex flex-col md:flex-row gap-8">
                <a href="/about" class="text-[var(--foreground)] hover:opacity-80 transition-opacity">
                    {$t('footer.aboutUs')}
                </a>
                <a href="https://blog.synthetic.lawyer" target="_blank" class="text-[var(--foreground)] hover:opacity-80 transition-opacity">
                    {$t('footer.blog')}
                </a>
                <a href="mailto:contact@cicero.chat" class="text-[var(--foreground)] hover:opacity-80 transition-opacity">
                    {$t('footer.contactUs')}
                </a>
                <a href="https://www.cicero.chat/tos.html" class="text-[var(--foreground)] hover:opacity-80 transition-opacity">
                    {$t('footer.termsPrivacy')}
                </a>
                <a href="https://www.cicero.chat/privacy-policy.html" class="text-[var(--foreground)] hover:opacity-80 transition-opacity">
                    {$t('footer.privacyPolicy')}
                </a>
            </div>

            <!-- Copyright -->
            <div class="text-[var(--foreground)] opacity-60">
                2024 Cicero. {$t('footer.rights')}
            </div>
        </div>
    </div>
</footer>

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
