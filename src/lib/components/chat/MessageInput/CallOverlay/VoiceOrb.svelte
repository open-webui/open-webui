<script lang="ts">
	import { onMount } from 'svelte';

	let {
		level = 0,
		muted = false,
		speaking = false
	}: { level?: number; muted?: boolean; speaking?: boolean } = $props();
	let canvas: HTMLCanvasElement;
	let refresh = () => {};

	$effect(() => {
		level;
		muted;
		speaking;
		refresh();
	});

	onMount(() => {
		const gl = canvas.getContext('webgl', {
			alpha: true,
			antialias: false,
			premultipliedAlpha: false
		});
		if (!gl) return;

		const vertex = gl.createShader(gl.VERTEX_SHADER)!;
		const fragment = gl.createShader(gl.FRAGMENT_SHADER)!;
		const program = gl.createProgram()!;
		const buffer = gl.createBuffer()!;
		const dispose = () => {
			gl.deleteBuffer(buffer);
			gl.deleteProgram(program);
			gl.deleteShader(vertex);
			gl.deleteShader(fragment);
		};

		gl.shaderSource(
			vertex,
			`
			attribute vec2 position;
			varying vec2 uv;
			void main() { uv = position; gl_Position = vec4(position, 0.0, 1.0); }
		`
		);
		gl.shaderSource(
			fragment,
			`
			precision highp float;
			varying vec2 uv;
			uniform float time;
			uniform float energy;
			uniform float speech;
			uniform float dark;

			uniform float resolution;

			// Smooth, evolving material coordinates on a sphere. No image textures.
			float material(vec3 p) {
				float t = time * 0.34;
				vec3 warp = vec3(
					sin(p.y * 2.1 + p.z * 1.3 + t),
					sin(p.z * 2.3 - p.x * 1.2 - t * 0.8),
					sin(p.x * 1.8 + p.y * 1.4 + t * 0.65)
				);
				vec3 q = p + (0.38 + speech * 0.05 + energy * (0.12 + speech * 0.08)) * warp;
				return sin(q.y * 2.2 + q.x * 1.5 + t * 0.3)
					+ 0.28 * sin(q.x * 3.2 - q.z * 2.4 - t * 0.7);
			}

			void main() {
				float r = length(uv);
				float edge = 0.94;
				float alpha = 1.0 - smoothstep(edge - 2.0 / resolution, edge, r);
				if (alpha <= 0.0) { gl_FragColor = vec4(0.0); return; }

				vec2 xy = uv / edge;
				vec3 p = vec3(xy, sqrt(max(0.0, 1.0 - dot(xy, xy))));
				float field = material(p);
				float e = 0.004;
				vec3 gradient = vec3(
					material(p + vec3(e, 0.0, 0.0)),
					material(p + vec3(0.0, e, 0.0)),
					material(p + vec3(0.0, 0.0, e))
				) - field;
				gradient /= e;
				// Tangential displacement changes the lighting without distorting the silhouette.
				vec3 tangent = gradient - p * dot(gradient, p);
				float crease = exp(-field * field * 2.0);
				vec3 n = normalize(p - tangent * crease * (0.10 + energy * 0.03));
				vec3 light = normalize(vec3(0.55, 0.9, 1.4));
				float diffuse = max(dot(n, light), 0.0);
				float fill = max(dot(n, normalize(vec3(-1.0, 0.15, 0.8))), 0.0);
				float highlight = pow(max(dot(n, normalize(light + vec3(0.0, 0.0, 1.0))), 0.0), 8.0);
				float flow = smoothstep(-0.95, 0.95, field);
				vec3 low = mix(vec3(0.145, 0.15, 0.16), vec3(0.22, 0.225, 0.235), dark);
				vec3 high = mix(vec3(0.33, 0.335, 0.345), vec3(0.50, 0.505, 0.515), dark);
				float emphasis = speech * (0.35 + 0.20 * energy);
				low *= 1.0 - 0.30 * emphasis;
				high += vec3(0.10) * emphasis;
				vec3 base = mix(low, high, flow);
				vec3 color = base * (0.64 + 0.30 * diffuse + 0.06 * fill);
				color += vec3(0.04 + 0.02 * emphasis) * highlight;
				color = pow(color, vec3(1.0 / 2.2));
				gl_FragColor = vec4(color, alpha);
			}

		`
		);
		gl.compileShader(vertex);
		gl.compileShader(fragment);
		gl.attachShader(program, vertex);
		gl.attachShader(program, fragment);
		gl.linkProgram(program);
		if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
			dispose();
			return;
		}

		gl.useProgram(program);
		gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
		gl.bufferData(
			gl.ARRAY_BUFFER,
			new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
			gl.STATIC_DRAW
		);
		const position = gl.getAttribLocation(program, 'position');
		gl.enableVertexAttribArray(position);
		gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
		const timeUniform = gl.getUniformLocation(program, 'time');
		const energyUniform = gl.getUniformLocation(program, 'energy');
		const speechUniform = gl.getUniformLocation(program, 'speech');
		const darkUniform = gl.getUniformLocation(program, 'dark');
		const resolutionUniform = gl.getUniformLocation(program, 'resolution');
		const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
		let frame = 0;
		let lastTime = 0;
		let elapsed = 0;
		let amplitude = 0;
		let speech = 0;
		let disposed = false;

		const draw = (now: number) => {
			frame = 0;
			if (disposed || gl.isContextLost() || document.hidden) return;
			const delta = lastTime ? Math.min((now - lastTime) / 1000, 0.05) : 0;
			lastTime = now;
			const active = !muted && !reducedMotion.matches;
			const target = active
				? Math.min(1, Math.pow(Math.max(0, level * (speaking ? 12 : 6)), speaking ? 0.7 : 1))
				: 0;
			amplitude += (target - amplitude) * (1 - Math.exp(-delta * 6));
			speech += ((active && speaking ? 1 : 0) - speech) * (1 - Math.exp(-delta * 4));
			if (active) elapsed += delta * (0.8 + amplitude * 0.3 + speech * (0.6 + amplitude * 0.4));
			gl.uniform1f(timeUniform, reducedMotion.matches ? 0 : elapsed);
			gl.uniform1f(energyUniform, active ? amplitude : 0);
			gl.uniform1f(speechUniform, active ? speech : 0);
			gl.uniform1f(darkUniform, canvas.closest('.dark') ? 1 : 0);
			gl.uniform1f(resolutionUniform, canvas.width);
			gl.drawArrays(gl.TRIANGLES, 0, 6);
			if (!canvas.classList.contains('rendered')) canvas.classList.add('rendered');
			if (active) frame = requestAnimationFrame(draw);
		};

		refresh = () => {
			if (!frame && !disposed) {
				lastTime = 0;
				frame = requestAnimationFrame(draw);
			}
		};
		const resize = () => {
			const size = Math.max(1, Math.round(canvas.clientWidth * 2));
			canvas.width = canvas.height = size;
			gl.viewport(0, 0, size, size);
			refresh();
		};
		const onVisibility = () => {
			cancelAnimationFrame(frame);
			frame = 0;
			if (!document.hidden) refresh();
		};
		const onContextLost = () => {
			cancelAnimationFrame(frame);
			frame = 0;
			canvas.classList.remove('rendered');
		};
		const observer = new ResizeObserver(resize);
		observer.observe(canvas);
		const themeObserver = new MutationObserver(refresh);
		themeObserver.observe(document.documentElement, {
			attributes: true,
			subtree: true,
			attributeFilter: ['class']
		});
		reducedMotion.addEventListener('change', refresh);
		document.addEventListener('visibilitychange', onVisibility);
		canvas.addEventListener('webglcontextlost', onContextLost);
		resize();

		return () => {
			disposed = true;
			cancelAnimationFrame(frame);
			observer.disconnect();
			themeObserver.disconnect();
			reducedMotion.removeEventListener('change', refresh);
			refresh = () => {};
			document.removeEventListener('visibilitychange', onVisibility);
			canvas.removeEventListener('webglcontextlost', onContextLost);
			dispose();
		};
	});
</script>

<span class="voice-orb" class:muted aria-hidden="true">
	<canvas bind:this={canvas}></canvas>
</span>

<style>
	.voice-orb {
		display: block;
		position: relative;
		width: 112px;
		aspect-ratio: 1;
		transition: opacity 240ms ease;
	}
	canvas {
		display: block;
		width: 100%;
		height: 100%;
		border-radius: 50%;
		background: radial-gradient(circle at 68% 22%, #9a9ca1, #7b7d82 49%, #5d6065);
	}
	:global(.dark) canvas {
		background: radial-gradient(circle at 68% 22%, #b9bbc0, #93959a 49%, #6d7076);
	}
	canvas:global(.rendered) {
		background: transparent;
	}
	.muted {
		opacity: 0.55;
	}
	@media (prefers-reduced-motion: reduce) {
		.voice-orb {
			transition: none;
		}
	}
</style>
