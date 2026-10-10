export const AVATAR_MAX_BYTES = 25 * 1024 * 1024;

export type AvatarState = 'idle' | 'listening' | 'speaking';
export type AvatarAnimation = { file_id: string };
export type AvatarGesture = AvatarAnimation & { name: string; description: string };
export type AnimationFiles = Record<string, File>;
export function avatarAssetIds(config?: VoiceAvatarConfig | null): string[] {
	return config
		? [
				config.file_id,
				...Object.values(config.states ?? {}).map((a) => a.file_id),
				...(config.gestures ?? []).map((a) => a.file_id)
			].filter(Boolean)
		: [];
}

export type VoiceAvatarConfig = {
	file_id: string;
	states?: Partial<Record<AvatarState, AvatarAnimation>>;
	gestures?: AvatarGesture[];
};

// Validate before GLTFLoader can fetch resources or allocate GPU buffers.
export function readAvatar(data: ArrayBuffer) {
	if (data.byteLength > AVATAR_MAX_BYTES) throw new Error('Avatar must be at most 25 MiB.');
	if (data.byteLength < 20) throw new Error('Upload a VRM 0.x or VRM 1.0 file.');
	const view = new DataView(data);
	if (
		view.getUint32(0, true) !== 0x46546c67 ||
		view.getUint32(4, true) !== 2 ||
		view.getUint32(8, true) !== data.byteLength ||
		view.getUint32(16, true) !== 0x4e4f534a
	) {
		throw new Error('Upload a binary VRM file.');
	}
	const length = view.getUint32(12, true);
	if (length > 2 * 1024 * 1024 || 20 + length + 8 > data.byteLength)
		throw new Error('Invalid avatar container.');
	const json = JSON.parse(new TextDecoder().decode(new Uint8Array(data, 20, length)));
	const binaryStart = 28 + length;
	if (
		view.getUint32(24 + length, true) !== 0x004e4942 ||
		binaryStart + view.getUint32(20 + length, true) !== data.byteLength
	)
		throw new Error('Invalid avatar binary data.');
	const vrm = json.extensions?.VRMC_vrm ?? json.extensions?.VRM;
	if (!vrm?.humanoid?.humanBones)
		throw new Error('This model needs a VRM humanoid rig. A plain GLB is not enough.');
	const bones = Array.isArray(vrm.humanoid.humanBones)
		? Object.fromEntries(vrm.humanoid.humanBones.map((bone: any) => [bone.bone, bone]))
		: vrm.humanoid.humanBones;
	for (const name of [
		'hips',
		'spine',
		'head',
		'leftUpperArm',
		'rightUpperArm',
		'leftLowerArm',
		'rightLowerArm'
	]) {
		if (!Number.isInteger(bones[name]?.node) || !json.nodes?.[bones[name].node])
			throw new Error(`Avatar is missing its ${name} bone.`);
	}
	if (
		json.buffers?.length !== 1 ||
		json.buffers[0].uri ||
		json.buffers[0].byteLength > data.byteLength - binaryStart ||
		(json.images ?? []).some((image: any) => image.uri || !Number.isInteger(image.bufferView))
	) {
		throw new Error(
			'Embed all textures and buffers in the VRM file. External resources are not supported.'
		);
	}
	const vertexCount = (json.accessors ?? []).reduce(
		(sum: number, a: any) => sum + (a.count ?? 0),
		0
	);
	if (
		(json.nodes?.length ?? 0) > 512 ||
		(json.images?.length ?? 0) > 32 ||
		vertexCount > 5_000_000
	) {
		throw new Error('This avatar is too complex for a voice call. Use a lighter export.');
	}
	return { json, binaryStart };
}

export async function validateAvatar(data: ArrayBuffer) {
	const { json, binaryStart } = readAvatar(data);
	let pixels = 0;
	for (const image of json.images ?? []) {
		const buffer = json.bufferViews?.[image.bufferView];
		const start = binaryStart + (buffer?.byteOffset ?? 0);
		if (
			!buffer ||
			(buffer.buffer ?? 0) !== 0 ||
			!Number.isInteger(buffer.byteLength) ||
			start < binaryStart ||
			start + buffer.byteLength > data.byteLength ||
			!['image/png', 'image/jpeg', 'image/webp'].includes(image.mimeType)
		)
			throw new Error('Invalid embedded avatar texture.');
		const bitmap = await createImageBitmap(
			new Blob([data.slice(start, start + buffer.byteLength)], { type: image.mimeType })
		);
		const tooLarge = bitmap.width > 4096 || bitmap.height > 4096;
		pixels += bitmap.width * bitmap.height;
		bitmap.close();
		if (tooLarge || pixels > 32 * 1024 * 1024)
			throw new Error('Avatar textures are too large. Export at 2048px or below.');
	}
}
