export function arraysEqual(a: any, b: any) {
	if (a.length !== b.length) return false;
	for (let i = 0; i < a.length; i++) {
		if ((a[i].id ?? a[i].content) !== (b[i].id ?? b[i].content)) {
			return false;
		}
	}
	return true;
}
