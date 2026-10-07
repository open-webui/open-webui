import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils, type VRM } from '@pixiv/three-vrm';
import { loadBodyAnimation } from './voice-avatar-animation';
import { validateAvatar, type VoiceAvatarConfig } from './voice-avatar';

export type AvatarSignals = {
	speaking: boolean;
	listening: boolean;
	level: number;
	active: boolean;
};

export async function createAvatarRenderer(
	canvas: HTMLCanvasElement,
	data: ArrayBuffer,
	signal: AbortSignal
) {
	await validateAvatar(data);
	signal.throwIfAborted();
	const manager = new THREE.LoadingManager();
	manager.setURLModifier((url) => {
		if (!url.startsWith('blob:')) throw new Error('External avatar resources are not supported.');
		return url;
	});
	const loader = new GLTFLoader(manager);
	loader.register((parser) => new VRMLoaderPlugin(parser));
	const gltf = await loader.parseAsync(data, '');
	const vrm: VRM | undefined = gltf.userData.vrm;
	if (!vrm || signal.aborted) {
		VRMUtils.deepDispose(gltf.scene);
		signal.throwIfAborted();
		throw new Error('This VRM could not be loaded.');
	}
	VRMUtils.rotateVRM0(vrm);
	const scene = new THREE.Scene();
	scene.add(vrm.scene);
	scene.add(new THREE.HemisphereLight(0xffffff, 0x8b929f, 2));
	const light = new THREE.DirectionalLight(0xffffff, 2.2);
	light.position.set(-1, 2, 3);
	scene.add(light);
	let renderer: THREE.WebGLRenderer;
	try {
		renderer = new THREE.WebGLRenderer({
			canvas,
			alpha: true,
			antialias: true,
			powerPreference: 'low-power'
		});
	} catch (error) {
		VRMUtils.deepDispose(vrm.scene);
		throw error;
	}
	renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
	renderer.setClearColor(0x000000, 0);
	renderer.outputColorSpace = THREE.SRGBColorSpace;
	const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
	const bone = (name: Parameters<typeof vrm.humanoid.getNormalizedBoneNode>[0]) =>
		vrm.humanoid.getNormalizedBoneNode(name);
	const head = bone('head');
	const spine = bone('spine');
	const chest = bone('chest') ?? bone('upperChest');
	const leftArm = bone('leftUpperArm');
	const rightArm = bone('rightUpperArm');
	const leftElbow = bone('leftLowerArm');
	const rightElbow = bone('rightLowerArm');
	const hips = bone('hips');
	vrm.scene.updateMatrixWorld(true);
	const legs = (['left', 'right'] as const).flatMap((side) => {
		const upper = bone(`${side}UpperLeg`),
			lower = bone(`${side}LowerLeg`),
			foot = bone(`${side}Foot`);
		if (!upper || !lower || !foot) return [];
		return [
			{
				upper,
				lower,
				foot,
				target: foot.getWorldPosition(new THREE.Vector3()),
				orientation: foot.getWorldQuaternion(new THREE.Quaternion())
			}
		];
	});
	// Start all built-in states from a relaxed, slightly asymmetric stance.
	// Normalized VRM bones share T-pose axes across VRM 0 and 1.
	const restingRotations: Partial<Record<Parameters<typeof bone>[0], [number, number, number]>> = {
		hips: [0, 0, 0.025],
		spine: [0.025, 0.015, -0.035],
		chest: [-0.012, -0.008, 0.01],
		head: [0.008, -0.008, 0],
		leftShoulder: [0, 0, -0.025],
		rightShoulder: [0, 0, 0.035],
		leftUpperArm: [0.025, -0.06, -1.38],
		rightUpperArm: [-0.015, 0.035, 1.34],
		leftLowerArm: [0, -0.24, -0.035],
		rightLowerArm: [0, 0.19, 0.025],
		leftHand: [0.025, 0, -0.055],
		rightHand: [-0.015, 0, 0.035],
		leftUpperLeg: [-0.025, 0, 0.045],
		rightUpperLeg: [-0.045, 0, 0],
		leftLowerLeg: [0.05, 0, 0],
		rightLowerLeg: [0.09, 0, 0],
		leftFoot: [-0.025, 0.045, -0.02],
		rightFoot: [-0.045, -0.035, 0.025]
	};
	for (const [name, rotation] of Object.entries(restingRotations))
		bone(name as Parameters<typeof bone>[0])?.rotation.set(...rotation);
	// Resting fingers curl mainly at the first two joints, with a softer index finger.
	for (const side of ['left', 'right'] as const) {
		const sign = side === 'left' ? -1 : 1;
		for (const [i, finger] of (['Index', 'Middle', 'Ring', 'Little'] as const).entries()) {
			const curl = 0.18 + i * 0.035 + (side === 'right' ? 0.025 : 0);
			for (const [joint, amount] of [
				['Proximal', curl],
				['Intermediate', curl * 0.8],
				['Distal', 0.04]
			] as const) {
				const node = bone(`${side}${finger}${joint}`);
				if (node) node.rotation.z = sign * amount;
			}
		}
	}
	// Pose once over the supporting leg, solving the knees back to the original
	// foot contacts. Breathing never moves the pelvis or feet after this setup.
	if (hips && legs.length === 2) {
		const standingHeight =
			hips.getWorldPosition(new THREE.Vector3()).y - (legs[0].target.y + legs[1].target.y) / 2;
		if (standingHeight > 0) {
			const position = hips.getWorldPosition(new THREE.Vector3());
			position.x += standingHeight * 0.02;
			position.y -= standingHeight * 0.009;
			hips.position.copy(hips.parent ? hips.parent.worldToLocal(position) : position);
		}
	}
	vrm.scene.updateMatrixWorld(true);
	const aim = (node: THREE.Object3D, child: THREE.Object3D, target: THREE.Vector3) => {
		const origin = node.getWorldPosition(new THREE.Vector3());
		const from = child.getWorldPosition(new THREE.Vector3()).sub(origin).normalize();
		const to = target.clone().sub(origin).normalize();
		const world = new THREE.Quaternion()
			.setFromUnitVectors(from, to)
			.multiply(node.getWorldQuaternion(new THREE.Quaternion()));
		const parent =
			node.parent?.getWorldQuaternion(new THREE.Quaternion()) ?? new THREE.Quaternion();
		node.quaternion.copy(parent.invert().multiply(world));
		node.updateWorldMatrix(false, true);
	};
	for (const { upper, lower, foot, target, orientation } of legs) {
		const origin = upper.getWorldPosition(new THREE.Vector3());
		const knee = lower.getWorldPosition(new THREE.Vector3());
		const upperLength = origin.distanceTo(knee);
		const lowerLength = knee.distanceTo(foot.getWorldPosition(new THREE.Vector3()));
		if (upperLength < 0.001 || lowerLength < 0.001) continue;
		const direction = target.clone().sub(origin);
		const distance = THREE.MathUtils.clamp(
			direction.length(),
			Math.abs(upperLength - lowerLength) + 0.0001,
			upperLength + lowerLength - 0.0001
		);
		direction.normalize();
		const along = (upperLength ** 2 + distance ** 2 - lowerLength ** 2) / (2 * distance);
		const bend = new THREE.Vector3(0, 0, 1).addScaledVector(direction, -direction.z).normalize();
		knee
			.copy(origin)
			.addScaledVector(direction, along)
			.addScaledVector(bend, Math.sqrt(Math.max(0, upperLength ** 2 - along ** 2)));
		aim(upper, lower, knee);
		aim(lower, foot, target);
		const parent =
			foot.parent?.getWorldQuaternion(new THREE.Quaternion()) ?? new THREE.Quaternion();
		foot.quaternion.copy(parent.invert().multiply(orientation));
		foot.updateWorldMatrix(false, true);
	}
	vrm.update(0);
	vrm.scene.updateMatrixWorld(true);
	const bounds = new THREE.Box3().setFromObject(vrm.scene);
	const size = bounds.getSize(new THREE.Vector3());
	const center = bounds.getCenter(new THREE.Vector3());
	const headPosition = head?.getWorldPosition(new THREE.Vector3()) ?? center.clone();
	const bodyHeight = Math.max(size.y, 0.5);
	const target = new THREE.Object3D();
	scene.add(target);
	if (vrm.lookAt) vrm.lookAt.target = target;
	const expressions = vrm.expressionManager;
	const mouth = !!expressions?.getExpression('aa');
	const blink = !!expressions?.getExpression('blink');
	const separateBlink =
		!!expressions?.getExpression('blinkLeft') && !!expressions?.getExpression('blinkRight');
	let speaking = 0,
		listening = 0,
		mouthWeight = 0,
		elapsed = 0,
		nextBlink = 2.8,
		blinkStart = -10;
	let width = 0,
		height = 0;

	const mixer = new THREE.AnimationMixer(vrm.scene);
	const poses = Object.values(vrm.humanoid.normalizedHumanBones).map(({ node }) => ({
		node,
		restQ: node.quaternion.clone(),
		restP: node.position.clone(),
		q: node.quaternion.clone(),
		p: node.position.clone(),
		authoredQ: node.quaternion.clone(),
		authoredP: node.position.clone()
	}));
	const clips = new Map<string, THREE.AnimationClip>();
	let current: THREE.AnimationAction | null = null;
	let outgoing: THREE.AnimationAction | null = null;
	let fadeTime = 0,
		bodyWeight = 0,
		speechHold = 0;
	let gesture = false,
		gestureElapsed = 0;
	let enabled = true;
	let cameraDistance = 0;
	const switchClip = (clip: THREE.AnimationClip, once: boolean) => {
		if (outgoing) {
			outgoing.stop();
			mixer.uncacheAction(outgoing.getClip());
			outgoing = null;
		}
		if (current) {
			current.stop();
			// Blend from the pose actually on screen, including an interrupted crossfade.
			// A separate snapshot also lets the same clip restart without snapping.
			const pose = new THREE.AnimationClip(
				'transition',
				0.3,
				poses.flatMap(({ node, authoredQ, authoredP }) => [
					new THREE.QuaternionKeyframeTrack(`${node.name}.quaternion`, [0], authoredQ.toArray()),
					new THREE.VectorKeyframeTrack(`${node.name}.position`, [0], authoredP.toArray())
				])
			);
			outgoing = mixer.clipAction(pose).play();
		}
		current = mixer.clipAction(clip);
		current.reset().setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, once ? 1 : Infinity);
		current.clampWhenFinished = true;
		current.enabled = true;
		current.setEffectiveWeight(1).play();
		if (outgoing && outgoing !== current) current.crossFadeFrom(outgoing, 0.3, false);
		fadeTime = 0;
	};
	const cancelGesture = () => {
		gesture = false;
		gestureElapsed = 0;
		speechHold = 0;
	};

	return {
		capabilities: { mouth, blink: blink || separateBlink },
		async loadAnimation(id: string, data: ArrayBuffer) {
			const clip = await loadBodyAnimation(data, vrm);
			signal.throwIfAborted();
			// Every body clip owns the full pose, including bones omitted by its author.
			const names = new Set(clip.tracks.map((track) => track.name));
			for (const { node, restQ, restP } of poses) {
				if (!names.has(`${node.name}.quaternion`))
					clip.tracks.push(
						new THREE.QuaternionKeyframeTrack(`${node.name}.quaternion`, [0], restQ.toArray())
					);
				if (!names.has(`${node.name}.position`))
					clip.tracks.push(
						new THREE.VectorKeyframeTrack(`${node.name}.position`, [0], restP.toArray())
					);
			}
			clips.set(id, clip);
		},
		playGesture(id: string) {
			if (!enabled) return 'unavailable' as const;
			const clip = clips.get(id);
			if (!clip) return 'unavailable' as const;
			switchClip(clip, true);
			gesture = true;
			gestureElapsed = 0;
			return 'started' as const;
		},
		cancelGesture,
		render(delta: number, config: VoiceAvatarConfig, input: AvatarSignals, reducedMotion: boolean) {
			const dt = Math.min(delta, 0.05);
			elapsed += dt;
			enabled = input.active && !reducedMotion;
			if (!enabled) cancelGesture();
			if (input.speaking && input.active) speechHold = 0.2;
			else speechHold = Math.max(0, speechHold - dt);
			if (input.listening) speechHold = 0;
			const state =
				input.speaking || speechHold > 0 ? 'speaking' : input.listening ? 'listening' : 'idle';
			if (gesture) {
				gestureElapsed += dt;
				if (gestureElapsed >= current!.getClip().duration) cancelGesture();
			}
			const stateClip = enabled ? clips.get(config.states?.[state]?.file_id ?? '') : undefined;
			if (
				!gesture &&
				stateClip &&
				(current?.getClip() !== stateClip || current.loop === THREE.LoopOnce)
			)
				switchClip(stateClip, false);
			const authored = enabled && (gesture || !!stateClip);
			bodyWeight = THREE.MathUtils.clamp(bodyWeight + (authored ? dt : -dt) / 0.3, 0, 1);
			if (!enabled) bodyWeight = 0;
			// Start the procedural pose from rest, never from last frame's authored pose.
			for (const pose of poses) {
				pose.node.quaternion.copy(pose.restQ);
				pose.node.position.copy(pose.restP);
			}
			const rect = canvas.getBoundingClientRect();
			if (!rect.width || !rect.height) return;
			if (rect.width !== width || rect.height !== height) {
				width = rect.width;
				height = rect.height;
				renderer.setSize(width, height, false);
				camera.aspect = width / height;
				camera.updateProjectionMatrix();
			}

			const smooth = 1 - Math.exp(-dt * 5);
			speaking += ((input.active && input.speaking ? 1 : 0) - speaking) * smooth;
			listening +=
				((input.active && input.listening && !input.speaking ? 1 : 0) - listening) * smooth;
			// Keep the built-in body relaxed; authored clips supply intentional gestures.
			const amount = reducedMotion ? 0 : Math.sqrt(0.35);
			const breath = Math.sin(elapsed * 1.1) * 0.9 + Math.sin(elapsed * 0.47) * 0.1;
			const sway = amount * (0.01 * Math.sin(elapsed * 0.43) + 0.003 * Math.sin(elapsed * 0.71));
			if (spine) {
				spine.rotation.x += amount * (0.006 * breath + 0.015 * listening);
				spine.rotation.y += amount * speaking * 0.008 * Math.sin(elapsed * 0.6);
				spine.rotation.z += sway;
			}
			if (chest) {
				chest.rotation.x -= amount * 0.008 * breath;
				chest.rotation.z -= sway * 0.35;
			}
			if (head) {
				head.rotation.x +=
					amount *
					(0.006 * breath + speaking * 0.012 * Math.sin(elapsed * 0.85) + listening * 0.025);
				head.rotation.y +=
					amount * (0.012 * Math.sin(elapsed * 0.32) + speaking * 0.008 * Math.sin(elapsed * 0.6));
				head.rotation.z +=
					amount * (0.006 * Math.sin(elapsed * 0.27) + listening * 0.025) - sway * 0.5;
			}
			if (leftArm) leftArm.rotation.z += amount * 0.004 * breath;
			if (rightArm) rightArm.rotation.z -= amount * 0.003 * Math.sin(elapsed * 1.1 - 0.2);
			if (leftElbow) leftElbow.rotation.y -= amount * 0.006 * Math.sin(elapsed * 1.1 - 0.3);
			if (rightElbow) rightElbow.rotation.y += amount * 0.004 * Math.sin(elapsed * 1.1 - 0.5);
			if (current && (bodyWeight > 0 || authored)) {
				for (const pose of poses) {
					pose.q.copy(pose.node.quaternion);
					pose.p.copy(pose.node.position);
					// Three's mixer skips unchanged keyframes, so preserve its last output
					// independently of procedural movement and the final blended pose.
					pose.node.quaternion.copy(pose.authoredQ);
					pose.node.position.copy(pose.authoredP);
				}
				mixer.update(dt);
				fadeTime += dt;
				if (outgoing && fadeTime >= 0.3) {
					outgoing.stop();
					mixer.uncacheAction(outgoing.getClip());
					outgoing = null;
				}
				for (const pose of poses) {
					pose.authoredQ.copy(pose.node.quaternion);
					pose.authoredP.copy(pose.node.position);
					pose.node.quaternion.slerpQuaternions(pose.q, pose.authoredQ, bodyWeight);
					pose.node.position.lerpVectors(pose.p, pose.authoredP, bodyWeight);
				}
			} else if (current) {
				mixer.stopAllAction();
				if (outgoing) mixer.uncacheAction(outgoing.getClip());
				current = outgoing = null;
			}
			// Only assistant PCM drives the mouth. Silence and interruptions close it immediately.
			const desiredMouth =
				input.active && input.speaking ? Math.min(1, Math.max(0, input.level) * 7) * 0.7 : 0;
			mouthWeight =
				desiredMouth === 0
					? 0
					: mouthWeight + (desiredMouth - mouthWeight) * (1 - Math.exp(-dt * 24));
			if (mouth) expressions!.setValue('aa', mouthWeight);
			if (elapsed >= nextBlink) {
				blinkStart = elapsed;
				nextBlink = elapsed + 3.2 + Math.random() * 2.8;
			}
			const blinkPhase = (elapsed - blinkStart) / 0.17;
			const blinkWeight = blinkPhase >= 0 && blinkPhase <= 1 ? Math.sin(blinkPhase * Math.PI) : 0;
			if (blink) expressions!.setValue('blink', blinkWeight);
			else if (separateBlink) {
				expressions!.setValue('blinkLeft', blinkWeight);
				expressions!.setValue('blinkRight', blinkWeight);
			}
			if (vrm.lookAt) vrm.lookAt.autoUpdate = true;
			target.position.set(
				camera.position.x + amount * 0.1 * Math.sin(elapsed * 0.4),
				headPosition.y,
				camera.position.z
			);
			vrm.update(reducedMotion ? 0 : dt);
			vrm.scene.updateMatrixWorld(true);
			const animatedBounds = bounds.clone();
			const bonePosition = new THREE.Vector3();
			for (const { node } of poses)
				animatedBounds.expandByPoint(node.getWorldPosition(bonePosition));
			animatedBounds.expandByScalar(bodyHeight * 0.06);
			const extent = animatedBounds.getSize(new THREE.Vector3());
			const animatedCenter = animatedBounds.getCenter(new THREE.Vector3());
			const fitHeight = Math.max(bodyHeight, extent.y + 2 * Math.abs(animatedCenter.y - center.y));
			const fitWidth = Math.max(size.x, extent.x + 2 * Math.abs(animatedCenter.x - center.x));
			const distance =
				Math.max(size.z, extent.z) / 2 +
				(Math.max(fitHeight, fitWidth / camera.aspect) * 1.2) / (2 * Math.tan(Math.PI / 12));
			// Widen before a limb reaches the edge; never zoom in/out on each gesture.
			cameraDistance = Math.max(distance, cameraDistance);
			camera.position.set(center.x, center.y, center.z + cameraDistance);
			camera.lookAt(center);
			renderer.render(scene, camera);
		},
		dispose() {
			mixer.stopAllAction();
			mixer.uncacheRoot(vrm.scene);
			clips.clear();
			VRMUtils.deepDispose(vrm.scene);
			renderer.dispose();
			renderer.forceContextLoss();
		}
	};
}
