export function split(array) {
	const count = array.length;
	const middleIndex = Math.round(count / 2);
	return [array.slice(0, middleIndex), array.slice(middleIndex)];
}

export function shuffle(items: ScrollerItem[]): ScrollerItem[] {
	const shuffledItems = [...items];

	for (let i = shuffledItems.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[shuffledItems[i], shuffledItems[j]] = [shuffledItems[j], shuffledItems[i]];
	}

	return shuffledItems;
}
