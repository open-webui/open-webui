export class AudioQueue {
	constructor(audioElement) {
		this.audio = audioElement;
		this.queue = [];
		this.current = null;
		this.id = null;

		this._onEnded = () => this.next();
		this.audio.addEventListener('ended', this._onEnded);

		this.onStopped = null; // optional callback
	}

	setId(newId) {
		console.log('Setting audio queue ID to:', newId);
		if (this.id !== newId) {
			this.stop();
			this.id = newId;
			if (this.onStopped) this.onStopped({ event: 'id-change', id: newId });
		}
	}

	setPlaybackRate(rate) {
		console.log('Setting audio playback rate to:', rate);
		this.audio.playbackRate = rate;
	}

	enqueue(url) {
		console.log('Enqueuing audio URL:', url);
		this.queue.push(url);

		// Auto-play if nothing is currently playing or loaded
		if (this.audio.paused && !this.current) {
			this.next();
		}
	}

	play() {
		if (!this.current && this.queue.length > 0) {
			this.next();
		} else {
			this.audio.play();
		}
	}

	next() {
		this.current = this.queue.shift();
		if (this.current) {
			this.audio.src = this.current;
			this.audio.play();
			console.log('Playing audio URL:', this.current);
		} else {
			this.stop();
			if (this.onStopped) this.onStopped({ event: 'empty-queue', id: this.id });
		}
	}

	stop() {
		this.audio.pause();
		this.audio.currentTime = 0;
		this.audio.src = '';
		this.queue = [];
		this.current = null;
		if (this.onStopped) this.onStopped({ event: 'stop', id: this.id });
	}

	destroy() {
		this.audio.removeEventListener('ended', this._onEnded);
		this.stop();
		this.onStopped = null;
		this.audio = null;
	}
}
