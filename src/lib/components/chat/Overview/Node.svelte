<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	import ProfileImageBase from '../Messages/ProfileImageBase.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	type $$Props = NodeProps;
	export let data: $$Props['data'];
</script>

<div
	class="px-4 py-3 shadow-md rounded-xl dark:bg-black bg-white border dark:border-gray-900 w-60 h-20"
>
	<Tooltip
		content={data?.message?.error ? data.message.error.content : data.message.content}
		class="w-full"
	>
		{#if data.message.role === 'user'}
			<div class="flex w-full">
				<ProfileImageBase
					src={data.user?.profile_image_url ?? '/user.png'}
					className={'size-5 -translate-y-[1px]'}
				/>
				<div class="ml-2">
					<div class="text-xs text-black dark:text-white font-medium">
						{data?.user?.name ?? 'User'}
					</div>

					{#if data?.message?.error}
						<div class="text-red-500 line-clamp-2 text-xs mt-0.5">{data.message.error.content}</div>
					{:else}
						<div class="text-gray-500 line-clamp-2 text-xs mt-0.5">{data.message.content}</div>
					{/if}
				</div>
			</div>
		{:else}
			<div class="flex w-full">
				<ProfileImageBase
					src={data?.model?.info?.meta?.profile_image_url ?? ''}
					className={'size-5 -translate-y-[1px]'}
				/>

				<div class="ml-2">
					<div class="text-xs text-black dark:text-white font-medium">
						{data?.model?.name ?? data?.message?.model ?? 'Assistant'}
					</div>

					{#if data?.message?.error}
						<div class="text-red-500 line-clamp-2 text-xs mt-0.5">
							{data.message.error.content}
						</div>
					{:else}
						<div class="text-gray-500 line-clamp-2 text-xs mt-0.5">{data.message.content}</div>
					{/if}
				</div>
			</div>
		{/if}
	</Tooltip>
	<Handle type="target" position={Position.Top} class="w-2 rounded-full dark:bg-gray-900" />
	<Handle type="source" position={Position.Bottom} class="w-2 rounded-full dark:bg-gray-900" />
</div>
