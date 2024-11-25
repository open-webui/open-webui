<script lang="ts">
    import { t } from '$lib/landing/translations';
</script>

<section class="w-full py-20 bg-[var(--background)]">
    <div class="w-full max-w-[1440px] mx-auto px-4">
        <h2 class="text-4xl font-bold text-center text-[var(--foreground)] mb-8">
            {$t('information.title')}
        </h2>
        <p class="text-xl text-center text-[var(--foreground)]">
            {$t('information.description')}
            <span class="font-bold">{$t('information.descriptionBold')}</span>
        </p>
    </div>
</section>
