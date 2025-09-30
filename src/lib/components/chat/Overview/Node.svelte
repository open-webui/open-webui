<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	import ProfileImage from '../Messages/ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Heart from '$lib/components/icons/Heart.svelte';
	import Clip from '$lib/components/icons/Clip.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Note from '$lib/components/icons/Note.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';

	type $$Props = NodeProps;
	export let data: $$Props['data'];

	let uniqueFileTypes = [];
	if (data.message.files && data.message.files.length > 0) {
		const types = data.message.files.map((file) => {
			if (file.type === 'doc' || file.type === 'file') return 'file';
			if (file.type === 'text') return 'website';
			return file.type;
		});
		uniqueFileTypes = [...new Set(types)];
	}
</script>

<div
	class="px-4 py-3 shadow-md rounded-xl dark:bg-black bg-white border dark:border-gray-900 w-60 h-20 group"
>
	<Tooltip
		content={data?.message?.error ? data.message.error.content : data.message.content}
		class="w-full"
		allowHTML={false}
	>
		{#if data.message.role === 'user'}
			<div class="flex w-full">
				<ProfileImage
					src={data.user?.profile_image_url ?? `${WEBUI_BASE_URL}/user.png`}
					className={'size-5 -translate-y-[1px]'}
				/>
				<div class="ml-2 overflow-hidden">
					<div class="flex items-center">
						<div class="text-xs text-black dark:text-white font-medium truncate">
							{data?.user?.name ?? 'User'}
						</div>

						{#if uniqueFileTypes.length > 0}
							<div class="ml-1.5 shrink-0">
								{#if uniqueFileTypes.length > 1}
									<Clip class="size-3" />
								{:else if uniqueFileTypes[0] === 'file'}
									<Document class="size-3" />
								{:else if uniqueFileTypes[0] === 'chat'}
									<ChatBubble class="size-3" />
								{:else if uniqueFileTypes[0] === 'note'}
									<Note class="size-3" />
								{:else if uniqueFileTypes[0] === 'image'}
									<Photo class="size-3" />
								{:else if uniqueFileTypes[0] === 'website'}
									<GlobeAlt class="size-3" />
								{:else}
									<Clip class="size-3" />
								{/if}
							</div>
						{/if}
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
				<ProfileImage
					src={data?.model?.info?.meta?.profile_image_url ?? ''}
					className={'size-5 -translate-y-[1px]'}
				/>

				<div class="ml-2">
					<div class=" flex justify-between items-center">
						<div class="text-xs text-black dark:text-white font-medium line-clamp-1">
							{data?.model?.name ?? data?.message?.model ?? 'Assistant'}
						</div>

						<button
							class={data?.message?.favorite ? '' : 'invisible group-hover:visible'}
							on:click={() => {
								data.message.favorite = !(data?.message?.favorite ?? false);
							}}
						>
							<Heart
								className="size-3 {data?.message?.favorite
									? 'fill-red-500 stroke-red-500'
									: 'hover:fill-red-500 hover:stroke-red-500'} "
								strokeWidth="2.5"
							/>
						</button>
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