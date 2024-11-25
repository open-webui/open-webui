<script lang="ts">
    import { t, currentLang } from '$lib/landing/translations';
    
    let translate: (key: string) => string;

    // Subscribe to the derived store
    $: translate = $t;
</script>

<footer class="py-8 bg-[var(--background)]">
    <div class="container mx-auto px-4 max-w-[1440px]">
        <div class="flex flex-wrap justify-center gap-6 text-sm text-[var(--foreground)] opacity-80">
            <a href="#" class="hover:opacity-100 transition-opacity">
                {translate('footer.aboutUs')}
            </a>
            <a href="#" class="hover:opacity-100 transition-opacity">
                {translate('footer.blog')}
            </a>
            <a href="#" class="hover:opacity-100 transition-opacity">
                {translate('footer.contactUs')}
            </a>
            <a href="#" class="hover:opacity-100 transition-opacity">
                {translate('footer.termsPrivacy')}
            </a>
            <a href="#" class="hover:opacity-100 transition-opacity">
                {translate('footer.cookieSettings')}
            </a>
        </div>
        <div class="mt-4 text-center text-sm text-[var(--foreground)] opacity-60">
            © 2024 Cicero. {translate('footer.rights')}
        </div>
    </div>
</footer>
