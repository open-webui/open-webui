export const withDownloadLock = async <T>(
	inFlight: Set<string>,
	key: string,
	onChange: () => void,
	download: () => Promise<T>
): Promise<T | undefined> => {
	if (inFlight.has(key)) {
		return undefined;
	}

	inFlight.add(key);
	onChange();
	try {
		return await download();
	} finally {
		inFlight.delete(key);
		onChange();
	}
};
