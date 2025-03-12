<script>
    import { page } from '$app/stores';
</script>

<div class="relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out md:max-w-[calc(100%-260px)] max-w-full">
<nav class="px-2.5 pt-1 backdrop-blur-xl drag-region">
    <div class="">
        <div
            class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
        >
            <a
                class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes(
                    '/character/create'
                )
                    ? ''
                    : 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
                href="/character/create">{'Create'}</a
            >

            <a
                class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes(
                    '/character/browse'
                )
                    ? ''
                    : 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
                href="/character/browse"
            >
                {'Browse'}
            </a>
        </div>
    </div>
</nav>
<div class="pb-1 px-[18px] flex-1 max-h-full overflow-y-auto">
    <slot/>
</div>
</div>