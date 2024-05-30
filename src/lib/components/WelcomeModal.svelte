<script lang="ts">
  import { getContext } from 'svelte';
  import { Confetti } from 'svelte-confetti';

  import Modal from './common/Modal.svelte';
  import Logo from "$lib/components/icons/Logo.svelte";

  const i18n = getContext('i18n');

  export let show = false;
</script>

<Modal bind:show>
    <div class="flex flex-col justify-center items-center space-y-4 px-5 py-10 dark:text-gray-300 text-gray-700">
        <Logo size={100} />

        <div class="text-center">
            <p class="font-bold text-[32px]">Chào mừng bạn đến với LànhGPT V.08</p>
            <p class="text-xl font-thin mb-8">Sản phẩm của Công ty EraX (c).</p>
            <Confetti x={[-1, -0.25]} y={[0, 0.5]} />
            <Confetti x={[1, 0.25]} y={[0, 0.5]} />
        </div>

        <div class="text-center">
            <p class="text-xl">Các yêu cầu hỗ trợ vui lòng gửi đến</p>
            <p class="text-xl text-blue-500 mb-8"><a href="mailto:support@lanhgpt.ai">support@lanhgpt.ai</a></p>
        </div>

        <div>
            <button
                    on:click={() => {
					localStorage.webcome = true;
					show = false;
				}}
                    class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
            >
                <span class="relative">{$i18n.t("Okay, Let's Go!")}</span>
            </button>
        </div>
    </div>
</Modal>
