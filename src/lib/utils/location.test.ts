import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getUserPosition } from './location';

const mockGetCurrentPosition = vi.fn();

beforeEach(() => {
	vi.stubGlobal('navigator', {
		geolocation: { getCurrentPosition: mockGetCurrentPosition }
	});
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('getUserPosition', () => {
	it('passes timeout options to getCurrentPosition', async () => {
		mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
			success({ coords: { latitude: 48.123, longitude: 37.456 } } as GeolocationPosition);
		});

		await getUserPosition();

		expect(mockGetCurrentPosition).toHaveBeenCalledWith(
			expect.any(Function),
			expect.any(Function),
			{ timeout: 5000, maximumAge: 60_000, enableHighAccuracy: false }
		);
	});

	it('returns formatted coordinates by default', async () => {
		mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
			success({ coords: { latitude: 48.1234, longitude: 37.4567 } } as GeolocationPosition);
		});

		const result = await getUserPosition();
		expect(result).toBe('48.123, 37.457 (lat, long)');
	});

	it('returns raw coordinates when raw=true', async () => {
		mockGetCurrentPosition.mockImplementation((success: PositionCallback) => {
			success({ coords: { latitude: 48.123, longitude: 37.456 } } as GeolocationPosition);
		});

		const result = await getUserPosition(true);
		expect(result).toEqual({ latitude: 48.123, longitude: 37.456 });
	});

	it('throws when geolocation permission is denied', async () => {
		const error = { code: 1, message: 'User denied geolocation' } as GeolocationPositionError;
		mockGetCurrentPosition.mockImplementation((_: PositionCallback, reject: PositionErrorCallback) => {
			reject(error);
		});

		await expect(getUserPosition()).rejects.toMatchObject({ message: 'User denied geolocation' });
	});

	it('throws when geolocation times out', async () => {
		const error = { code: 3, message: 'Timeout expired' } as GeolocationPositionError;
		mockGetCurrentPosition.mockImplementation((_: PositionCallback, reject: PositionErrorCallback) => {
			reject(error);
		});

		await expect(getUserPosition()).rejects.toMatchObject({ message: 'Timeout expired' });
	});

	it('throws when geolocation API is unavailable', async () => {
		vi.stubGlobal('navigator', {});

		await expect(getUserPosition()).rejects.toThrow(
			'Geolocation is not supported by this browser'
		);
	});
});
