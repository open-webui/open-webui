/* PCM capture and playback share the browser's 24 kHz audio clock. */
class RealtimeAudioProcessor extends AudioWorkletProcessor {
	constructor() {
		super();
		this.capture = new Float32Array(960);
		this.captureLength = 0;
		this.enabled = false;
		/** @type {{ samples: Float32Array, offset: number, response_id: string, item_id: string, content_index: number }[]} */
		this.queue = [];
		this.queued = 0;
		this.received = 0;
		this.playing = false;
		this.rendered = new Map();
		this.ended = new Set();
		this.ticks = 0;
		this.inputEnergy = 0;
		this.outputEnergy = 0;
		this.levelSamples = 0;
		this.port.onmessage = ({ data }) => {
			if (data.type === 'capture') {
				this.enabled = data.enabled;
				this.captureLength = 0;
			} else if (data.type === 'audio') {
				if (this.queued + data.samples.length > 24000 * 120) {
					this.port.postMessage({ type: 'overflow' });
					return;
				}
				this.received += data.samples.length;
				this.queue.push({ ...data, offset: 0 });
				this.queued += data.samples.length;
			} else if (data.type === 'done') {
				this.ended.add(data.response_id);
			} else if (data.type === 'clear') {
				this.port.postMessage({
					type: 'cleared',
					id: data.id,
					rendered: [...this.rendered.values()]
				});
				this.queue = [];
				this.queued = 0;
				this.playing = false;
				this.rendered.clear();
				this.ended.clear();
			}
		};
	}

	/** @param {Float32Array[][]} inputs @param {Float32Array[][]} outputs */
	process(inputs, outputs) {
		const input = inputs[0]?.[0];
		if (this.enabled && input) {
			for (const sample of input) {
				this.capture[this.captureLength++] = sample;
				if (this.captureLength === 960) {
					const pcm = new ArrayBuffer(1920);
					const view = new DataView(pcm);
					for (let i = 0; i < 960; i++) {
						const value = Math.max(-1, Math.min(1, this.capture[i]));
						view.setInt16(i * 2, value * (value < 0 ? 32768 : 32767), true);
					}
					this.port.postMessage({ type: 'input', pcm }, [pcm]);
					this.captureLength = 0;
				}
			}
		}
		const output = outputs[0][0];
		if (!this.playing && (this.queued >= 1920 || this.ended.has(this.queue[0]?.response_id))) {
			this.playing = true;
		}
		if (this.playing) {
			let offset = 0;
			while (offset < output.length && this.queue.length) {
				const chunk = this.queue[0];
				const count = Math.min(output.length - offset, chunk.samples.length - chunk.offset);
				output.set(chunk.samples.subarray(chunk.offset, chunk.offset + count), offset);
				offset += count;
				chunk.offset += count;
				this.queued -= count;
				const key = `${chunk.item_id}:${chunk.content_index}`;
				const position = this.rendered.get(key) ?? {
					response_id: chunk.response_id,
					item_id: chunk.item_id,
					content_index: chunk.content_index,
					samples: 0
				};
				position.samples += count;
				this.rendered.set(key, position);
				if (chunk.offset === chunk.samples.length) this.queue.shift();
			}
			if (!this.queued) this.playing = false;
		}
		for (let i = 0; i < output.length; i++) {
			const sample = this.enabled ? (input?.[i] ?? 0) : 0;
			this.inputEnergy += sample * sample;
			this.outputEnergy += output[i] * output[i];
		}
		this.levelSamples += output.length;
		if (++this.ticks % 8 === 0) {
			this.port.postMessage({
				type: 'playback',
				queued: this.queued,
				received: this.received,
				inputLevel: Math.sqrt(this.inputEnergy / this.levelSamples),
				outputLevel: Math.sqrt(this.outputEnergy / this.levelSamples)
			});
			this.inputEnergy = this.outputEnergy = this.levelSamples = 0;
		}
		return true;
	}
}
registerProcessor('realtime-audio', RealtimeAudioProcessor);
