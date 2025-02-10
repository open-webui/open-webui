import WorkerInstance from '$lib/workers/kokoro.worker?worker';

export class KokoroWorker {
	private worker: Worker | null = null;
	private initialized: boolean = false;
	private dtype: string;

	constructor(dtype: string = 'fp32') {
		this.dtype = dtype;
	}

	public async init() {
		if (this.worker) {
			console.warn('KokoroWorker is already initialized.');
			return;
		}

		this.worker = new WorkerInstance();

		return new Promise<void>((resolve, reject) => {
			this.worker!.onmessage = (event) => {
				const { status, error } = event.data;

				if (status === 'init:complete') {
					this.initialized = true;
					resolve();
				} else if (status === 'init:error') {
					console.error(error);
					this.initialized = false;
					reject(new Error(error));
				}
			};

			this.worker!.postMessage({
				type: 'init',
				payload: { dtype: this.dtype }
			});
		});
	}

	public async generate({ text, voice }: { text: string; voice: string }): Promise<string> {
		if (!this.initialized || !this.worker) {
			throw new Error('KokoroTTS Worker is not initialized yet.');
		}

		return new Promise<string>((resolve, reject) => {
			this.worker.postMessage({ type: 'generate', payload: { text, voice } });

			const handleMessage = (event: MessageEvent) => {
				if (event.data.status === 'generate:complete') {
					this.worker!.removeEventListener('message', handleMessage);
					resolve(event.data.audioUrl);
				} else if (event.data.status === 'generate:error') {
					this.worker!.removeEventListener('message', handleMessage);
					reject(new Error(event.data.error));
				}
			};

			this.worker.addEventListener('message', handleMessage);
		});
	}

	public terminate() {
		if (this.worker) {
			this.worker.terminate();
			this.worker = null;
			this.initialized = false;
		}
	}
}
