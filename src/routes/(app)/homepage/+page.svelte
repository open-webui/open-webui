<script lang="ts">
    import { goto } from '$app/navigation';

    const heroCards = [
        {
            title: 'AI Chat Bot',
            subtitle: 'Conversational Assistant',
            description:
                'Ask questions, get instant policy guidance—quick answers on admissions, approvals, inmate health, or legal cases.',
            modelId: 'llama3.2:latest'
        },

        {
            title: 'Document Model',
            subtitle: 'Reports & Policy Q&A',
            description:
                'Upload and create repository look up GR & SOP sections; track changes with compliance checklists.',
            modelId: 'gpt-oss:20b'
        },
        {
            title: 'Image & Video Model',
            subtitle: 'Evidence Safeguards',
            description:
                'Auto-validate uploaded photos/videos, detect facility gaps, and complement compliance.',
            modelId: 'llama3.2-vision:latest'
        }
    ];

    const handleGetStarted = (modelId: string) => goto(`/?model=${encodeURIComponent(modelId)}`)
        .catch((err) => console.error('Navigation error:', err));
</script>

<section class="relative flex w-full justify-center overflow-hidden px-4 pb-12 pt-10 sm:px-6 lg:px-10">
    <div
        class="absolute inset-0 -z-10 bg-gradient-to-br from-blue-50 to-purple-50"
    ></div>

    <div class="relative flex w-full max-w-6xl flex-col gap-10 lg:flex-row lg:gap-12">
        <div class="flex-1 space-y-4 text-[#212969]">
            <h1 class="text-3xl font-semibold tracking-tight text-[#5E2FA0] sm:text-4xl">
                <span class="text-[#EC327D]">Smarter AI.</span> Safer Shelters.
            </h1>
            <h2 class="text-sm font-semibold uppercase tracking-[0.2em] text-[#293A98]">
                Smarter AI for Survivor-Centric Governance
            </h2>
            <p class="max-w-2xl text-sm leading-relaxed text-[#2E3576] sm:text-base">
                Empowering the Department of Women & Child Development with AI tools for survivor-centric governance.
                Enhance and improve trafficking prevention, rehabilitation, and compliance monitoring across DWCD operations.
            </p>

            <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {#each heroCards as card}
                    <article class="flex h-full flex-col rounded-[30px] border border-[#E3E5FB] bg-white/85 p-6 text-[#1F2A7A] shadow-[0_30px_70px_-40px_rgba(35,31,84,0.55)] backdrop-blur-sm">
                        <header class="space-y-1">
                            <p class="text-xs font-semibold uppercase tracking-[0.35em] text-[#E32C82]">
                                {card.subtitle}
                            </p>
                            <h3 class="text-lg font-semibold leading-tight text-[#212969]">{card.title}</h3>
                        </header>
                        <p class="mt-4 flex-1 text-sm leading-relaxed text-[#353F91]">
                            {card.description}
                        </p>
                        <button
                            class="mt-6 inline-flex min-h-[40px] w-full items-center justify-center rounded-full bg-[#2131A0] px-5 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-[#19257D] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2131A0]/60 focus-visible:ring-offset-1"
                            on:click={() => handleGetStarted(card.modelId)}
                            aria-label={`Get started with ${card.title}`}
                        >
                            Get Started
                        </button>
                    </article>
                {/each}
            </div>
        </div>
    </div>
</section>
