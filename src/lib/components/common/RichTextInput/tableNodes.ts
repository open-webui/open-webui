type ElementLike = {
	children: ArrayLike<ElementLike>;
	matches: (selector: string) => boolean;
};

const childrenOf = <T extends ElementLike>(node: T): T[] => Array.from(node.children) as T[];

export const getDirectTableRows = <T extends ElementLike>(table: T): T[] => {
	return childrenOf(table).flatMap((child) => {
		if (child.matches('tr')) {
			return [child];
		}

		if (child.matches('thead, tbody, tfoot')) {
			return childrenOf(child).filter((row) => row.matches('tr'));
		}

		return [];
	});
};

export const getDirectTableCells = <T extends ElementLike>(row: T): T[] => {
	return childrenOf(row).filter((child) => child.matches('th, td'));
};
