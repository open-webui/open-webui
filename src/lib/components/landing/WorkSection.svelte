<script lang="ts">
    import { t } from '$lib/landing/translations';

    const features = [
        {
            title: 'work.features.0.title',
            description: 'work.features.0.description'
        },
        {
            title: 'work.features.1.title',
            description: 'work.features.1.description'
        },
        {
            title: 'work.features.2.title',
            description: 'work.features.2.description'
        },
        {
            title: 'work.features.3.title',
            description: 'work.features.3.description'
        }
    ];
</script>

<section class="w-full py-20 bg-[var(--background)]">
    <div class="w-full max-w-[1440px] mx-auto px-4">
        <h2 class="text-4xl font-bold text-center text-[var(--foreground)] mb-12">
            {$t('work.title')}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {#each features as feature}
                <div class="p-6 rounded-lg bg-[var(--foreground)] text-[var(--background)]">
                    <h3 class="text-xl font-bold mb-4">
                        {$t(feature.title)}
                    </h3>
                    <p class="opacity-80">
                        {$t(feature.description)}
                    </p>
                </div>
            {/each}
        </div>
    </div>
</section>
