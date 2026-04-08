<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import VoiceRecording from './VoiceRecording.svelte';

	export let show = false;
	export let onConfirm: (data: { text: string }) => void = () => {};
	export let onCancel: () => void = () => {};

	let recording = false;

	// 모달이 열릴 때 즉시 녹음 시작
	$: if (show) {
		recording = true;
	} else {
		recording = false;
	}
</script>

<Modal
	bind:show
	size="sm"
	containerClassName="p-4 flex items-center justify-center"
	className="bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm rounded-4xl"
>
	<div class="flex flex-col gap-4 p-4 w-full">
		<div class="text-center">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">음성 입력</h2>
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
				말씀하세요. 완료되면 텍스트로 변환됩니다.
			</p>
		</div>
		<VoiceRecording
			bind:recording
			onCancel={() => {
				recording = false;
				onCancel();
				show = false;
			}}
			onConfirm={(data) => {
				recording = false;
				onConfirm(data);
				show = false;
			}}
		/>
	</div>
</Modal>
