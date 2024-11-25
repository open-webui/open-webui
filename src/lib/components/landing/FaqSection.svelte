<script lang="ts">
    import { t } from '$lib/landing/translations';

    const faqs = [
        {
            question: 'faq.q1',
            answer: 'faq.a1'
        },
        {
            question: 'faq.q2',
            answer: 'faq.a2'
        },
        {
            question: 'faq.q3',
            answer: 'faq.a3'
        },
        {
            question: 'faq.q4',
            answer: 'faq.a4'
        }
    ];
</script>

<section class="w-full py-20 bg-[var(--background)]">
    <div class="w-full max-w-[1440px] mx-auto px-4">
        <h2 class="text-4xl font-bold text-center text-[var(--foreground)] mb-12">
            {$t('faq.title')}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            {#each faqs as faq}
                <div class="p-6 rounded-lg bg-[var(--foreground)] text-[var(--background)]">
                    <h3 class="text-xl font-bold mb-4">
                        {$t(faq.question)}
                    </h3>
                    <p class="opacity-80">
                        {$t(faq.answer)}
                    </p>
                </div>
            {/each}
        </div>
    </div>
</section>
