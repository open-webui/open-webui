<script context="module" lang="ts">
	import * as THREE from 'three';
	import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
	import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

	type ModelResourceLoader = (path: string, signal: AbortSignal) => Promise<Blob>;
	type PreviewModel = {
		scene: THREE.Object3D;
		scenes: THREE.Object3D[];
		animations: THREE.AnimationClip[];
	};

	export function resolveModelResourcePath(modelPath: string, uri: string) {
		if (!uri || /^[a-z][a-z\d+.-]*:/i.test(uri) || uri.startsWith('/') || /[\\\x00]/.test(uri))
			throw new Error('Only relative model resource paths are supported.');
		const base = new URL('https://terminal.invalid/');
		base.pathname = modelPath.split('/').map(encodeURIComponent).join('/');
		const resource = new URL(uri, base);
		if (resource.origin !== base.origin || resource.search || resource.hash)
			throw new Error('Only relative model resource paths are supported.');
		const path = decodeURIComponent(resource.pathname);
		if (/[\\\x00]/.test(path)) throw new Error('Invalid model resource path.');
		return modelPath.startsWith('/') ? path : path.slice(1);
	}

	export function disposeModel(model: PreviewModel) {
		const resources = new Set<{ dispose(): void }>();
		const images = new Set<ImageBitmap>();
		for (const scene of model.scenes)
			scene.traverse((node) => {
				const mesh = node as THREE.Mesh;
				if (mesh.geometry) resources.add(mesh.geometry);
				const skeleton = (node as THREE.SkinnedMesh).skeleton;
				if (skeleton) resources.add(skeleton);
				for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
					if (!material) continue;
					resources.add(material);
					for (const value of Object.values(material)) {
						if (value instanceof THREE.Texture) {
							resources.add(value);
							if (typeof ImageBitmap !== 'undefined' && value.image instanceof ImageBitmap)
								images.add(value.image);
						}
					}
				}
			});
		for (const resource of resources) resource.dispose();
		for (const image of images) image.close();
	}

	// Decode the container so GLB references use the same authenticated resource path as glTF.
	function readGltf(data: ArrayBuffer, binary: boolean) {
		if (!binary) return { json: JSON.parse(new TextDecoder().decode(data)), bin: undefined };
		const header = new DataView(data);
		if (
			data.byteLength < 20 ||
			header.getUint32(0, true) !== 0x46546c67 ||
			header.getUint32(4, true) !== 2 ||
			header.getUint32(8, true) !== data.byteLength
		)
			throw new Error('Invalid GLB file.');
		let json;
		let bin: ArrayBuffer | undefined;
		for (let offset = 12; offset < data.byteLength; ) {
			if (offset + 8 > data.byteLength) throw new Error('Invalid GLB chunk.');
			const length = header.getUint32(offset, true),
				type = header.getUint32(offset + 4, true);
			if (
				length % 4 ||
				offset + 8 + length > data.byteLength ||
				(offset === 12 && type !== 0x4e4f534a)
			)
				throw new Error('Invalid GLB chunk.');
			const chunk = data.slice(offset + 8, offset + 8 + length);
			if (type === 0x4e4f534a) json = JSON.parse(new TextDecoder().decode(chunk));
			else if (type === 0x004e4942) bin = chunk;
			offset += 8 + length;
		}
		return { json, bin };
	}

	export async function loadModel(
		data: ArrayBuffer,
		path: string,
		signal: AbortSignal,
		loadResource?: ModelResourceLoader,
		renderer?: THREE.WebGLRenderer
	): Promise<PreviewModel> {
		signal.throwIfAborted();
		const extension = path.split('.').pop()?.toLowerCase();
		const urls: string[] = [];
		const dependencies = new Map<string, string>();
		const decoders: { dispose(): void }[] = [];
		let model: PreviewModel | undefined;
		const objectUrl = (blob: Blob) => {
			const url = URL.createObjectURL(blob);
			urls.push(url);
			return url;
		};
		const readResource = async (resourcePath: string) => {
			if (!loadResource) throw new Error(`Model resource unavailable: ${resourcePath}`);
			const blob = await loadResource(resourcePath, signal);
			signal.throwIfAborted();
			return blob;
		};
		const resourceUrl = async (base: string, uri: string) => {
			if (typeof uri !== 'string') throw new Error('Invalid model resource URI.');
			if (uri.startsWith('data:')) return uri;
			const resourcePath = resolveModelResourcePath(base, uri);
			if (!dependencies.has(resourcePath))
				dependencies.set(resourcePath, objectUrl(await readResource(resourcePath)));
			return dependencies.get(resourcePath)!;
		};
		let resourceError = false;
		const manager = new THREE.LoadingManager();
		manager.setURLModifier((url) => {
			if (!url.startsWith('blob:') && !url.startsWith('data:'))
				throw new Error('Unresolved model resource.');
			return url;
		});
		manager.onError = () => {
			resourceError = true;
		};
		const loaded = new Promise<void>((resolve) => {
			manager.onLoad = resolve;
		});
		// Keep the manager open until parsing has scheduled all texture loads, including OBJ materials.
		manager.itemStart('model');
		try {
			try {
				if (extension === 'glb' || extension === 'gltf') {
					const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
					const { json, bin } = readGltf(data, extension === 'glb');
					if (json?.asset?.version !== '2.0') throw new Error('Invalid glTF file.');
					for (const resource of [...(json.buffers ?? []), ...(json.images ?? [])]) {
						if (resource.uri !== undefined) resource.uri = await resourceUrl(path, resource.uri);
					}
					if (bin && json.buffers?.[0] && !json.buffers[0].uri)
						json.buffers[0].uri = objectUrl(new Blob([bin]));
					const loader = new GLTFLoader(manager);
					const extensions = new Set([
						...(json.extensionsUsed ?? []),
						...(json.extensionsRequired ?? [])
					]);
					if (extensions.has('KHR_draco_mesh_compression')) {
						const [{ DRACOLoader }, js, wasm] = await Promise.all([
							import('three/addons/loaders/DRACOLoader.js'),
							import('three/examples/jsm/libs/draco/gltf/draco_wasm_wrapper.js?url'),
							import('three/examples/jsm/libs/draco/gltf/draco_decoder.wasm?url')
						]);
						const draco = new DRACOLoader()
							.setDecoderPath({ js: js.default, wasm: wasm.default })
							.setWorkerLimit(2);
						decoders.push(draco);
						loader.setDRACOLoader(draco);
					}
					if (
						extensions.has('EXT_meshopt_compression') ||
						extensions.has('KHR_meshopt_compression')
					) {
						const { MeshoptDecoder } = await import('three/addons/libs/meshopt_decoder.module.js');
						loader.setMeshoptDecoder(MeshoptDecoder);
					}
					if (extensions.has('KHR_texture_basisu')) {
						if (!renderer) throw new Error('KTX2 textures require a WebGL renderer.');
						const [{ KTX2Loader }, js, wasm] = await Promise.all([
							import('three/addons/loaders/KTX2Loader.js'),
							import('three/examples/jsm/libs/basis/basis_transcoder.js?url'),
							import('three/examples/jsm/libs/basis/basis_transcoder.wasm?url')
						]);
						const decoderManager = new THREE.LoadingManager();
						decoderManager.onError = () => {
							resourceError = true;
						};
						// './' keeps decoder filenames explicit instead of relying on import.meta.url in optimized dependencies.
						const ktx = new KTX2Loader(decoderManager)
							.setTranscoderPath('./')
							.setWorkerLimit(2)
							.detectSupport(renderer);
						decoderManager.setURLModifier((url) => {
							if (url === './basis_transcoder.js') return js.default;
							if (url === './basis_transcoder.wasm') return wasm.default;
							return manager.resolveURL(url);
						});
						decoders.push(ktx);
						loader.setKTX2Loader(ktx);
					}
					model = await loader.parseAsync(JSON.stringify(json), '');
				} else if (extension === 'obj') {
					const [{ OBJLoader }, { MTLLoader }] = await Promise.all([
						import('three/addons/loaders/OBJLoader.js'),
						import('three/addons/loaders/MTLLoader.js')
					]);
					const text = new TextDecoder().decode(data);
					const materials = new MTLLoader(manager).parse('', '');
					const textureKeys = new Set([
						'map_kd',
						'map_ks',
						'map_ke',
						'norm',
						'map_bump',
						'bump',
						'disp',
						'map_d'
					]);
					for (const uri of new Set(
						[...text.matchAll(/^\s*mtllib[ \t]+(.+)$/gm)].map((match) => match[1].trim())
					)) {
						const materialPath = resolveModelResourcePath(path, uri);
						const library = new MTLLoader(manager).parse(
							await (await readResource(materialPath)).text(),
							''
						);
						for (const info of Object.values(library.materialsInfo)) {
							for (const [key, value] of Object.entries(info)) {
								if (!textureKeys.has(key) || typeof value !== 'string') continue;
								const normalized = value.trim().split(/\s+/).join(' ');
								const textureUri = library.getTextureParams(normalized, {}).url;
								Object.assign(info, {
									[key]:
										normalized.slice(0, normalized.lastIndexOf(textureUri)) +
										(await resourceUrl(materialPath, textureUri))
								});
							}
						}
						Object.assign(materials.materialsInfo, library.materialsInfo);
					}
					const scene = new OBJLoader(manager).setMaterials(materials).parse(text);
					model = { scene, scenes: [scene], animations: [] };
				} else if (extension === 'stl' || extension === 'ply') {
					const geometry =
						extension === 'stl'
							? new (await import('three/addons/loaders/STLLoader.js')).STLLoader().parse(data)
							: new (await import('three/addons/loaders/PLYLoader.js')).PLYLoader().parse(data);
					const points =
						extension === 'ply' &&
						!/^element face [1-9]\d*\s*$/m.test(
							new TextDecoder().decode(data).split('end_header')[0]
						);
					const vertexColors = !!geometry.getAttribute('color');
					if (!points && !geometry.getAttribute('normal')) geometry.computeVertexNormals();
					const scene = points
						? new THREE.Points(
								geometry,
								new THREE.PointsMaterial({
									vertexColors,
									color: vertexColors ? 0xffffff : 0x657b96,
									size: 0.01
								})
							)
						: new THREE.Mesh(
								geometry,
								new THREE.MeshStandardMaterial({
									vertexColors,
									color: vertexColors ? 0xffffff : 0x9ba9bb,
									side: THREE.DoubleSide
								})
							);
					model = { scene, scenes: [scene], animations: [] };
				} else throw new Error('Unsupported 3D format.');
			} finally {
				manager.itemEnd('model');
				await loaded;
			}
			signal.throwIfAborted();
			if (resourceError) throw new Error('Could not load a model texture.');
			const bounds = new THREE.Box3().setFromObject(model.scene);
			if (
				bounds.isEmpty() ||
				![...bounds.min.toArray(), ...bounds.max.toArray()].every(Number.isFinite)
			)
				throw new Error('No renderable geometry in model.');
			return model;
		} catch (error) {
			if (model) disposeModel(model);
			throw error;
		} finally {
			for (const decoder of decoders) decoder.dispose();
			for (const url of urls) URL.revokeObjectURL(url);
		}
	}

	async function createModelPreview(
		canvas: HTMLCanvasElement,
		data: ArrayBuffer,
		path: string,
		signal: AbortSignal,
		loadResource?: ModelResourceLoader
	) {
		signal.throwIfAborted();
		const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
		let model: PreviewModel | undefined;
		let controls: OrbitControls | undefined;
		let observer: ResizeObserver | undefined;
		let environment: THREE.WebGLRenderTarget | undefined;
		let mixer: THREE.AnimationMixer | undefined;
		const dispose = () => {
			renderer.setAnimationLoop(null);
			observer?.disconnect();
			controls?.dispose();
			mixer?.stopAllAction();
			if (model) {
				mixer?.uncacheRoot(model.scene);
				disposeModel(model);
			}
			environment?.dispose();
			renderer.dispose();
			renderer.forceContextLoss();
		};

		try {
			model = await loadModel(data, path, signal, loadResource, renderer);
			signal.throwIfAborted();
			const scene = new THREE.Scene();
			scene.add(model.scene);
			const sphere = new THREE.Box3()
				.setFromObject(model.scene)
				.getBoundingSphere(new THREE.Sphere());
			const radius = Math.max(sphere.radius, 0.001);
			model.scene.traverse((node) => {
				if (node instanceof THREE.Points && node.material instanceof THREE.PointsMaterial)
					node.material.size = radius * 0.012;
			});
			const camera = new THREE.PerspectiveCamera(45, 1, radius / 100, radius * 1000);
			renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
			renderer.toneMapping = THREE.ACESFilmicToneMapping;
			const pmrem = new THREE.PMREMGenerator(renderer);
			const room = new RoomEnvironment();
			try {
				environment = pmrem.fromScene(room);
				scene.environment = environment.texture;
			} finally {
				room.dispose();
				pmrem.dispose();
			}
			scene.add(new THREE.HemisphereLight(0xffffff, 0x8b929f, 2));
			const light = new THREE.DirectionalLight(0xffffff, 2);
			light.position.set(1, 2, 3);
			scene.add(light);
			controls = new OrbitControls(camera, canvas);
			controls.minDistance = radius * 0.05;
			controls.maxDistance = radius * 100;
			controls.listenToKeyEvents(canvas);
			const render = () => renderer.render(scene, camera);
			const reset = () => {
				const halfFov = Math.atan(
					Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * Math.min(camera.aspect, 1)
				);
				const distance = (radius / Math.sin(halfFov)) * 1.15;
				controls!.target.copy(sphere.center);
				camera.position
					.copy(sphere.center)
					.addScaledVector(new THREE.Vector3(1, 0.6, 1).normalize(), distance);
				controls!.update();
				render();
			};
			const zoom = (factor: number) => {
				const offset = camera.position.clone().sub(controls!.target);
				offset.setLength(
					THREE.MathUtils.clamp(
						offset.length() * factor,
						controls!.minDistance,
						controls!.maxDistance
					)
				);
				camera.position.copy(controls!.target).add(offset);
				controls!.update();
			};
			controls.addEventListener('change', render);
			let fitted = false;
			observer = new ResizeObserver(() => {
				const { width, height } = canvas.getBoundingClientRect();
				if (!width || !height) return;
				renderer.setSize(width, height, false);
				camera.aspect = width / height;
				camera.updateProjectionMatrix();
				if (!fitted) {
					reset();
					fitted = true;
				} else render();
			});
			observer.observe(canvas);
			mixer = new THREE.AnimationMixer(model.scene);
			const selectAnimation = (index: number) => {
				mixer!.stopAllAction();
				const clip = model!.animations[index];
				if (clip) mixer!.clipAction(clip).reset().play();
				mixer!.update(0);
				render();
			};
			selectAnimation(0);
			const setPlaying = (playing: boolean) => {
				let previous: number | undefined;
				renderer.setAnimationLoop(
					playing
						? (time) => {
								if (!document.hidden && previous !== undefined)
									mixer!.update(Math.min((time - previous) / 1000, 0.1));
								previous = time;
								render();
							}
						: null
				);
			};
			return {
				reset,
				zoom,
				dispose,
				selectAnimation,
				setPlaying,
				animations: model.animations.map((clip, i) => clip.name || String(i + 1))
			};
		} catch (error) {
			dispose();
			throw error;
		}
	}
</script>

<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Spinner from './Spinner.svelte';

	const i18n: any = getContext('i18n');
	export let data: ArrayBuffer;
	export let path = '';
	export let loadResource: ((path: string, signal: AbortSignal) => Promise<Blob>) | undefined =
		undefined;
	let canvas: HTMLCanvasElement;
	let loading = true;
	let error = '';
	let playing = false;
	let animation = 0;
	let preview: Awaited<ReturnType<typeof createModelPreview>>;

	onMount(() => {
		const abort = new AbortController();
		void (async () => {
			try {
				if (abort.signal.aborted) return;
				const result = await createModelPreview(canvas, data, path, abort.signal, loadResource);
				if (abort.signal.aborted) result.dispose();
				else preview = result;
			} catch (e) {
				if (!abort.signal.aborted) {
					console.error('Error rendering model preview:', e);
					error = e instanceof Error ? e.message : $i18n.t('Preview failed');
				}
			} finally {
				if (!abort.signal.aborted) loading = false;
			}
		})();
		return () => {
			abort.abort();
			preview?.dispose();
		};
	});
</script>

<div class="relative h-full w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
	<canvas
		bind:this={canvas}
		class="block h-full w-full touch-none"
		class:invisible={loading || error}
		tabindex="0"
		aria-label={$i18n.t('3D model preview')}
	></canvas>
	{#if loading}
		<div class="absolute inset-0 flex items-center justify-center">
			<Spinner className="size-4" />
		</div>
	{:else if error}
		<div
			role="alert"
			class="absolute inset-0 flex items-center justify-center p-4 text-sm text-red-500"
		>
			{$i18n.t('Error previewing file: {{error}}', { error })}
		</div>
	{:else}
		<div
			class="absolute bottom-3 left-1/2 flex max-w-[calc(100%-1.5rem)] -translate-x-1/2 flex-wrap items-center justify-center gap-1 rounded-lg border border-gray-200/60 bg-white/90 p-1 text-xs text-gray-500 shadow-lg dark:border-gray-700/60 dark:bg-gray-850/90 dark:text-gray-400"
		>
			<button
				type="button"
				class="rounded px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800"
				aria-label={$i18n.t('Zoom out')}
				on:click={() => preview?.zoom(1.25)}>−</button
			>
			<button
				type="button"
				class="whitespace-nowrap rounded px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800"
				on:click={() => preview?.reset()}>{$i18n.t('Reset view')}</button
			>
			<button
				type="button"
				class="rounded px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800"
				aria-label={$i18n.t('Zoom in')}
				on:click={() => preview?.zoom(0.8)}>+</button
			>
			{#if preview?.animations.length}
				<select
					class="min-w-0 max-w-36 rounded bg-transparent p-1"
					aria-label={$i18n.t('Animation')}
					bind:value={animation}
					on:change={() => preview?.selectAnimation(animation)}
				>
					{#each preview.animations as name, index}<option value={index}>{name}</option>{/each}
				</select>
				<button
					type="button"
					class="rounded px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800"
					on:click={() => {
						playing = !playing;
						preview?.setPlaying(playing);
					}}>{playing ? $i18n.t('Pause') : $i18n.t('Play')}</button
				>
			{/if}
		</div>
	{/if}
</div>
