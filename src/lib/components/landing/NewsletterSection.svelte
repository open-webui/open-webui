<script lang="ts">
    import { t } from '$lib/landing/translations';
</script>

<section class="w-full py-20 bg-[var(--background)]">
    <div class="w-full max-w-[1440px] mx-auto px-4">
        <h2 class="text-4xl font-bold text-center text-[var(--foreground)] mb-8">
            {$t('newsletter.title')}
        </h2>
        <p class="text-xl text-center text-[var(--foreground)] mb-8">
            {$t('newsletter.description')}
        </p>
        <div class="flex justify-center">
            <button class="bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-gradient-to-r hover:from-[var(--red-light)] hover:to-[var(--red-dark)] hover:text-white px-[25px] py-[15px] font-medium leading-[20px] rounded-full uppercase transition-all duration-300">
                {$t('newsletter.button')}
            </button>
        </div>
    </div>
</section>

<style>
    button:hover {
        color: white !important;
    }
</style>
