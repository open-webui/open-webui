import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import {
	VRMAnimationLoaderPlugin,
	createVRMAnimationHumanoidTracks
} from '@pixiv/three-vrm-animation';
import type { VRM } from '@pixiv/three-vrm';

export const ANIMATION_MAX_BYTES = 10 * 1024 * 1024;

export function validateAnimation(data: ArrayBuffer) {
	if (data.byteLength > ANIMATION_MAX_BYTES) throw new Error('Animation must be at most 10 MiB.');
	if (data.byteLength < 28) throw new Error('Upload a binary VRMA file.');
	const view = new DataView(data);
	const length = view.getUint32(12, true);
	if (
		view.getUint32(0, true) !== 0x46546c67 ||
		view.getUint32(4, true) !== 2 ||
		view.getUint32(8, true) !== data.byteLength ||
		view.getUint32(16, true) !== 0x4e4f534a ||
		length > 2 * 1024 * 1024 ||
		length + 28 > data.byteLength
	)
		throw new Error('Invalid VRMA container.');
	const start = 28 + length;
	const bytes = view.getUint32(20 + length, true);
	if (view.getUint32(24 + length, true) !== 0x004e4942 || start + bytes !== data.byteLength)
		throw new Error('Invalid animation binary data.');
	const json = JSON.parse(new TextDecoder().decode(new Uint8Array(data, 20, length)));
	const ext = json.extensions?.VRMC_vrm_animation;
	const bones = Object.values(ext?.humanoid?.humanBones ?? {}) as { node: number }[];
	if (
		ext?.specVersion !== '1.0' ||
		!bones.length ||
		!json.nodes?.length ||
		json.nodes.length > 512 ||
		bones.some((b) => !Number.isInteger(b.node) || !json.nodes[b.node])
	)
		throw new Error('Use a VRMA 1.0 humanoid animation.');
	const parents = new Set<number>(),
		visiting = new Set<number>(),
		visited = new Set<number>();
	const visit = (index: number) => {
		if (!Number.isInteger(index) || !json.nodes[index] || visiting.has(index))
			throw new Error('Invalid animation node hierarchy.');
		if (visited.has(index)) return;
		visiting.add(index);
		const node = json.nodes[index];
		for (const [key, length] of Object.entries({
			translation: 3,
			rotation: 4,
			scale: 3,
			matrix: 16
		})) {
			if (
				node[key] &&
				(node[key].length !== length || node[key].some((v: number) => !Number.isFinite(v)))
			)
				throw new Error('Invalid animation transform.');
		}
		for (const child of node.children ?? []) {
			if (parents.has(child)) throw new Error('Animation nodes must have a single parent.');
			parents.add(child);
			visit(child);
		}
		visiting.delete(index);
		visited.add(index);
	};
	json.nodes.forEach((_: unknown, index: number) => visit(index));
	for (const scene of json.scenes ?? [])
		if ((scene.nodes ?? []).some((n: number) => !Number.isInteger(n) || !json.nodes[n]))
			throw new Error('Invalid animation scene.');
	if (
		json.buffers?.length !== 1 ||
		'uri' in json.buffers[0] ||
		json.buffers[0].byteLength > bytes ||
		json.buffers[0].byteLength < bytes - 3 ||
		['images', 'textures', 'meshes', 'skins'].some((k) => json[k]?.length) ||
		(json.extensionsRequired ?? []).some((e: string) => e !== 'VRMC_vrm_animation')
	)
		throw new Error('Export embedded animation only, without meshes or textures.');
	for (const buffer of json.bufferViews ?? []) {
		if (
			(buffer.buffer ?? 0) !== 0 ||
			(buffer.byteOffset ?? 0) < 0 ||
			!(buffer.byteLength > 0) ||
			(buffer.byteOffset ?? 0) + buffer.byteLength > bytes
		)
			throw new Error('Invalid animation buffer.');
	}
	let count = 0;
	const values = (json.accessors ?? []).map((a: any) => {
		count += a.count;
		const components = ({ SCALAR: 1, VEC3: 3, VEC4: 4 } as Record<string, number>)[
			a.type
		] as number;
		const buffer = json.bufferViews?.[a.bufferView];
		const stride = buffer?.byteStride ?? components * 4;
		const offset = a.byteOffset ?? 0;
		if (
			!Number.isInteger(a.count) ||
			a.count <= 0 ||
			count > 500000 ||
			a.sparse ||
			a.componentType !== 5126 ||
			!components ||
			!buffer ||
			stride < components * 4 ||
			stride % 4 ||
			offset < 0 ||
			offset + (a.count - 1) * stride + components * 4 > buffer.byteLength
		)
			throw new Error('Invalid animation keyframes.');
		return Array.from({ length: a.count }, (_, i) =>
			Array.from({ length: components }, (_, c) => {
				const value = view.getFloat32(
					start + (buffer.byteOffset ?? 0) + offset + i * stride + c * 4,
					true
				);
				if (!Number.isFinite(value)) throw new Error('Animation keyframes must be finite.');
				return value;
			})
		);
	});
	const animation = json.animations?.[0];
	if (
		json.animations?.length !== 1 ||
		!animation?.channels?.length ||
		animation.channels.length > 256
	)
		throw new Error('Export exactly one animation per VRMA file.');
	let duration = 0,
		body = false;
	for (const channel of animation.channels) {
		const target = channel.target;
		const sampler = animation.samplers?.[channel.sampler];
		const times = values[sampler?.input],
			output = values[sampler?.output];
		const interpolation = sampler?.interpolation ?? 'LINEAR';
		if (!['LINEAR', 'STEP'].includes(interpolation))
			throw new Error('Export baked animation with linear or stepped keyframes.');
		if (
			!json.nodes[target?.node] ||
			!['rotation', 'translation'].includes(target.path) ||
			!times ||
			!output ||
			json.accessors[sampler.input].type !== 'SCALAR' ||
			!['LINEAR', 'STEP'].includes(interpolation) ||
			output.length !== times.length ||
			output[0].length !== (target.path === 'rotation' ? 4 : 3) ||
			times.some((t: number[], i: number) => t[0] < 0 || (i > 0 && t[0] <= times[i - 1][0]))
		)
			throw new Error('Invalid animation channels or timing.');
		duration = Math.max(duration, times[times.length - 1][0]);
		body ||= bones.some((b) => b.node === target.node);
	}
	if (!body || duration <= 0 || duration > 60)
		throw new Error('Use a body animation between 0 and 60 seconds.');
}

export async function loadBodyAnimation(data: ArrayBuffer, vrm: VRM) {
	validateAnimation(data);
	const manager = new THREE.LoadingManager();
	manager.setURLModifier(() => {
		throw new Error('External animation resources are not supported.');
	});
	const loader = new GLTFLoader(manager);
	loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
	const gltf = await loader.parseAsync(data, '');
	const animation = gltf.userData.vrmAnimations?.[0];
	if (
		!animation ||
		!Number.isFinite(animation.restHipsPosition.y) ||
		animation.restHipsPosition.y <= 0
	)
		throw new Error('Animation needs a valid humanoid rest pose.');
	const humanoid = createVRMAnimationHumanoidTracks(animation, vrm.humanoid, vrm.meta.metaVersion);
	for (const [name, track] of humanoid.rotation)
		track.setInterpolation(animation.humanoidTracks.rotation.get(name).getInterpolation());
	const tracks: THREE.KeyframeTrack[] = [
		...humanoid.rotation.values(),
		...humanoid.translation.values()
	];
	if (!tracks.length) throw new Error('Animation has no compatible body tracks.');
	const hips = vrm.humanoid.getNormalizedBoneNode('hips')!;
	for (const track of tracks) {
		if (!track.name.endsWith('.position')) continue;
		for (let i = 0; i < track.values.length; i += 3) {
			track.values[i] = hips.position.x;
			track.values[i + 2] = hips.position.z;
		}
	}
	return new THREE.AnimationClip('body', animation.duration, tracks);
}
