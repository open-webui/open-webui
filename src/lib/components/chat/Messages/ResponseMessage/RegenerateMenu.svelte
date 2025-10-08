<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import LineSpace from '$lib/components/icons/LineSpace.svelte';
	import LineSpaceSmaller from '$lib/components/icons/LineSpaceSmaller.svelte';

	const i18n = getContext('i18n');

	export let onRegenerate: Function = (prompt = null) => {};
	export let onClose: Function = () => {};

	let show = false;
	let inputValue = '';
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
	align="end"
>
	<slot></slot>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[200px] rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-850 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<div class="py-1.5 px-2.5 flex dark:text-gray-100">
				<input
					type="text"
					id="floating-message-input"
					class="bg-transparent outline-hidden w-full flex-1 text-sm"
					placeholder={$i18n.t('Suggest a change')}
					bind:value={inputValue}
					autocomplete="off"
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							onRegenerate(inputValue);
							show = false;
						}
					}}
				/>

				<div class="ml-2 self-center flex items-center">
					<button
						class="{inputValue !== ''
							? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
							: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1 self-center"
						on:click={() => {
							onRegenerate(inputValue);
							show = false;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-3.5"
						>
							<path
								fill-rule="evenodd"
								d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</div>
			</div>
			<hr class="border-gray-50 dark:border-gray-800 my-1 mx-2" />
			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					onRegenerate();
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					aria-hidden="true"
					stroke="currentColor"
					class="w-4 h-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
					/>
				</svg>
				<div class="flex items-center">{$i18n.t('Try Again')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					onRegenerate($i18n.t('Add Details'));
				}}
			>
				<LineSpace strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Add Details')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					onRegenerate($i18n.t('More Concise'));
				}}
			>
				<LineSpaceSmaller strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('More Concise')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
