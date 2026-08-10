type AudioTrack = Pick<MediaStreamTrack, 'addEventListener' | 'removeEventListener' | 'readyState'>;

type AudioStream = {
	getAudioTracks: () => AudioTrack[];
};

export const hasLiveAudioTrack = (stream: AudioStream | null) =>
	stream?.getAudioTracks().some((track) => track.readyState === 'live') ?? false;

export const watchAudioTrackEnd = (stream: AudioStream, onEnded: () => void) => {
	const tracks = stream.getAudioTracks();
	let handled = false;

	const handleEnded = () => {
		if (handled) {
			return;
		}

		handled = true;
		onEnded();
	};

	tracks.forEach((track) => track.addEventListener('ended', handleEnded));

	return () => {
		handled = true;
		tracks.forEach((track) => track.removeEventListener('ended', handleEnded));
	};
};

export const singleFlight = <T>(task: () => Promise<T>) => {
	let active: Promise<T> | null = null;

	return () => {
		if (active === null) {
			active = task().finally(() => {
				active = null;
			});
		}

		return active;
	};
};
