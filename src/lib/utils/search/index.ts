/**
 * This is a fork of the `quick-score` library, modified to integrate with this project.
 * Original Author: fwextensions (John Dunning)
 * Original Repository: https://github.com/fwextensions/quick-score
 * Original License: MIT
 * Original Version: 0.2.0 (1fd7fd28959ea055a317e06411ce0940ee4f5d20)
 *
 * The original library has been flattened and made typescript compatible.
 * Some features removed.
 */

export type KeyType = { name: string; scorer: ScorerFunction };
export type KeyName = string | string[];
export type ScorerFunction = (
	string: string,
	query: string,
	matches?: [number, number][]
) => number;
export type RangeTuple = [number, number];
export type TransformStringFunction = (string: string) => string;
export interface ScoredObject<T> {
	item: T;
	score: number;
	scoreKey: string;
	scoreValue: string;
	scores: { [k: string]: number };
	matches: { [k: string]: RangeTuple[] };
	_?: T;
}
export interface ScoredString<T> {
	item: T;
	score: number;
	matches: RangeTuple[];
}

export type ScoredResult<T> = T extends string ? ScoredString<T> : ScoredObject<T>;

const config = {
	wordSeparators: '-/\\:()<>%._=&[]+ \t\n\r',
	uppercaseLetters: (() => {
		const charCodeA = 'A'.charCodeAt(0);
		const uppercase = [];

		for (let i = 0; i < 26; i++) {
			uppercase.push(String.fromCharCode(charCodeA + i));
		}

		return uppercase.join('');
	})(),
	ignoredScore: 0.9,
	skippedScore: 0.15,
	emptyQueryScore: 0,
	// long, nearly-matching queries can generate up to 2^queryLength loops,
	// so support worst-case queries up to 16 characters and then give up
	// and return 0 for longer queries that may or may not actually match
	maxIterations: Math.pow(2, 16),
	longStringLength: 150,
	maxMatchStartPct: 0.15,
	minMatchDensityPct: 0.75,
	maxMatchDensityPct: 0.95,
	beginningOfStringPct: 0.1,
	useSkipReduction: (
		string: string,
		_query: string,
		_remainingScore: number,
		_searchRange: Range,
		_remainingSearchRange: Range,
		_matchedRange: Range,
		fullMatchedRange: Range
	) => {
		const len = string.length;
		const isShortString = len <= config.longStringLength;
		const matchStartPercentage = fullMatchedRange.location / len;

		return isShortString || matchStartPercentage < config.maxMatchStartPct;
	},

	adjustRemainingScore: (
		string: string,
		query: string,
		remainingScore: number,
		skippedSpecialChar: boolean,
		_searchRange: Range,
		remainingSearchRange: Range,
		_matchedRange: Range,
		fullMatchedRange: Range
	) => {
		const isShortString = string.length <= config.longStringLength;
		const matchStartPercentage = fullMatchedRange.location / string.length;
		let matchRangeDiscount = 1;
		let matchStartDiscount = 1 - matchStartPercentage;

		// discount the remainingScore based on how much larger the match is
		// than the query, unless the match is in the first 10% of the
		// string, the match range isn't too sparse and the whole string is
		// not too long.  also only discount if we didn't skip any whitespace
		// or capitals.
		if (!skippedSpecialChar) {
			matchRangeDiscount = query.length / fullMatchedRange.length;
			matchRangeDiscount =
				isShortString &&
				matchStartPercentage <= config.beginningOfStringPct &&
				matchRangeDiscount >= config.minMatchDensityPct
					? 1
					: matchRangeDiscount;
			matchStartDiscount = matchRangeDiscount >= config.maxMatchDensityPct ? 1 : matchStartDiscount;
		}

		// discount the scores of very long strings
		return (
			remainingScore *
			Math.min(remainingSearchRange.length, config.longStringLength) *
			matchRangeDiscount *
			matchStartDiscount
		);
	}
};
class Range {
	location: number;
	length: number;

	constructor(location: number = -1, length: number = 0) {
		this.location = location;
		this.length = length;
	}

	max(value?: number): number {
		if (typeof value == 'number') {
			this.length = value - this.location;
		}

		return this.location + this.length;
	}

	isValid(): boolean {
		return this.location > -1;
	}

	toArray(): RangeTuple {
		return [this.location, this.max()];
	}

	toString(): string {
		if (this.location == -1) {
			return 'invalid range';
		} else {
			return '[' + this.location + ',' + this.max() + ')';
		}
	}
}

export function quickScore(
	string: string,
	query: string,
	matches?: RangeTuple[],
	transformedString: string = string.toLocaleLowerCase(),
	transformedQuery: string = query.toLocaleLowerCase(),
	stringRange: Range = new Range(0, string.length)
) {
	let iterations = 0;

	if (query) {
		return calcScore(stringRange, new Range(0, query.length), new Range());
	} else {
		return config.emptyQueryScore;
	}

	function calcScore(searchRange: Range, queryRange: Range, fullMatchedRange: Range) {
		if (!queryRange.length) {
			// deduct some points for all remaining characters
			return config.ignoredScore;
		} else if (queryRange.length > searchRange.length) {
			return 0;
		}

		const initialMatchesLength = matches && matches.length;

		for (let i = queryRange.length; i > 0; i--) {
			if (iterations > config.maxIterations) {
				// a long query that matches the string except for the last
				// character can generate 2^queryLength iterations of this
				// loop before returning 0, so short-circuit that when we've
				// seen too many iterations (bit of an ugly kludge, but it
				// avoids locking up the UI if the user somehow types an
				// edge-case query)
				return 0;
			}

			iterations++;

			const querySubstring = transformedQuery.substring(
				queryRange.location,
				queryRange.location + i
			);
			// reduce the length of the search range by the number of chars
			// we're skipping in the query, to make sure there's enough string
			// left to possibly contain the skipped chars
			const matchedRange = getRangeOfSubstring(
				transformedString,
				querySubstring,
				new Range(searchRange.location, searchRange.length - queryRange.length + i)
			);

			if (!matchedRange.isValid()) {
				// we didn't find the query substring, so try again with a
				// shorter substring
				continue;
			}

			if (!fullMatchedRange.isValid()) {
				fullMatchedRange.location = matchedRange.location;
			} else {
				fullMatchedRange.location = Math.min(fullMatchedRange.location, matchedRange.location);
			}

			fullMatchedRange.max(matchedRange.max());

			if (matches) {
				matches.push(matchedRange.toArray());
			}

			const remainingSearchRange = new Range(
				matchedRange.max(),
				searchRange.max() - matchedRange.max()
			);
			const remainingQueryRange = new Range(queryRange.location + i, queryRange.length - i);
			const remainingScore = calcScore(remainingSearchRange, remainingQueryRange, fullMatchedRange);

			if (remainingScore) {
				let score = remainingSearchRange.location - searchRange.location;
				// default to true since we only want to apply a discount if
				// we hit the final else clause below, and we won't get to
				// any of them if the match is right at the start of the
				// searchRange
				let skippedSpecialChar = true;
				const useSkipReduction = config.useSkipReduction(
					string,
					query,
					remainingScore,
					remainingSearchRange,
					searchRange,
					remainingSearchRange,
					matchedRange
				);

				if (matchedRange.location > searchRange.location) {
					// some letters were skipped when finding this match, so
					// adjust the score based on whether spaces or capital
					// letters were skipped
					if (
						useSkipReduction &&
						config.wordSeparators.indexOf(string[matchedRange.location - 1]) > -1
					) {
						for (let j = matchedRange.location - 2; j >= searchRange.location; j--) {
							if (config.wordSeparators.indexOf(string[j]) > -1) {
								score--;
							} else {
								score -= config.skippedScore;
							}
						}
					} else if (
						useSkipReduction &&
						config.uppercaseLetters.indexOf(string[matchedRange.location]) > -1
					) {
						for (let j = matchedRange.location - 1; j >= searchRange.location; j--) {
							if (config.uppercaseLetters.indexOf(string[j]) > -1) {
								score--;
							} else {
								score -= config.skippedScore;
							}
						}
					} else {
						// reduce the score by the number of chars we've
						// skipped since the beginning of the search range
						score -= matchedRange.location - searchRange.location;
						skippedSpecialChar = false;
					}
				}

				score += config.adjustRemainingScore(
					string,
					query,
					remainingScore,
					skippedSpecialChar,
					searchRange,
					remainingSearchRange,
					matchedRange,
					fullMatchedRange
				);
				score /= searchRange.length;

				return score;
			} else if (matches) {
				// the remaining query does not appear in the remaining
				// string, so strip off any matches we've added during the
				// current call, as they'll be invalid when we start over
				// with a shorter piece of the query
				matches.length = initialMatchesLength as number;
			}
		}

		return 0;
	}
}

function getRangeOfSubstring(string: string, query: string, searchRange: Range) {
	const index = string.indexOf(query, searchRange.location);
	const result = new Range();

	if (index > -1 && index < searchRange.max()) {
		result.location = index;
		result.length = query.length;
	}

	return result;
}
/**
 * A class for scoring and sorting strings based on a query.
 * This class is responsible for transforming the data and invoking the scoring function
 */
export class QuickScore<T> {
	scorer = quickScore;
	transformStringFunc = toLocaleLowerCase;
	keys: KeyType[] = [];
	sortKey: string = '';
	minimumScore: number = 0;
	items: T[] = [];
	transformedItems: T[] = [];

	constructor(items: T[] = [], keys: string[]) {
		this.keys = keys.map((item) => ({ name: item, scorer: this.scorer }));

		this.setItems(items);

		// the scoring function needs access to this.sortKey
		this.compareScoredStrings = this.compareScoredStrings.bind(this);
	}

	search(query: string): ScoredObject<T>[] {
		const results: ScoredObject<T>[] = [];

		const sharedKeys = this.keys;
		const items = this.items;
		const transformedItems = this.transformedItems;
		const config = undefined;

		// if the query is empty, we want to return all items, so make the
		// minimum score less than 0
		const minScore = query ? this.minimumScore : -1;
		const transformedQuery = this.transformString(query);
		const itemCount = items.length;

		for (let i = 0; i < itemCount; i++) {
			const item = items[i];
			const transformedItem = transformedItems[i];
			const result: ScoredObject<T> = {
				item,
				score: 0,
				scoreKey: '',
				scoreValue: '',
				scores: {},
				matches: {},
				_: transformedItem
			};
			// if an empty keys array was passed into the constructor,
			// score all of the non-empty string keys on the object
			const keyCount = sharedKeys.length;
			let highScore = 0;
			let scoreKey = '';
			let scoreValue = '';

			// find the highest score for each keyed string on this item
			for (let j = 0; j < keyCount; j++) {
				const key = sharedKeys[j];
				// use the key as the name if it's just a string, and
				// default to the instance's scorer function
				const { name, scorer = this.scorer } = key;

				// string based key access :smile:
				const transformedString = transformedItem[name as keyof T] as string;

				// setItems() checks for non-strings and empty strings
				// when creating the transformed objects, so if the key
				// doesn't exist there, we can skip the processing
				// below for this key in this item
				if (transformedString) {
					const string = this.getItemString(item, key);
					const matches: RangeTuple[] = [];
					const newScore = scorer(
						string,
						query,
						matches,
						transformedString,
						transformedQuery,
						config
					);

					result.scores[name] = newScore;
					result.matches[name] = matches;

					if (newScore > highScore) {
						highScore = newScore;
						scoreKey = name;
						scoreValue = string;
					}
				}
			}

			if (highScore > minScore) {
				result.score = highScore;
				result.scoreKey = scoreKey;
				result.scoreValue = scoreValue;
				results.push(result);
			}
		}

		results.sort(this.compareScoredStrings);

		return results;
	}

	/**
	 * Sets the `items` array and caches a transformed copy of all the item
	 * strings specified by the `keys` parameter to the constructor, using the
	 * `transformString` option (which defaults to `toLocaleLowerCase()`).
	 */
	setItems(items: T[]) {
		// create a shallow copy of the items array so that changes to its
		// order outside of this instance won't affect searching
		const itemArray = items.slice();
		const itemCount = itemArray.length;
		const transformedItems = [];
		const sharedKeys = this.keys;

		for (let i = 0; i < itemCount; i++) {
			const item = itemArray[i];
			const transformedItem = {} as T;
			const keys = sharedKeys;
			const keyCount = keys.length;

			for (let j = 0; j < keyCount; j++) {
				const key = keys[j];
				const string = this.getItemString(item, key);

				if (string && typeof string === 'string') {
					// unsafe object mutation. Type of item.[name] should be string but the generic does not allow it
					// @ts-ignore ts 7053 unsafe mutation
					transformedItem[key.name] = this.transformString(string);
				}
			}

			transformedItems.push(transformedItem);
		}

		this.items = itemArray;
		this.transformedItems = transformedItems;
	}
	/*
	 * Gets the string value of a key on an item.
	 * key is indexed dynamically by keyname string
	 */
	getItemString(item: T, key_w: KeyType): string {
		return item[key_w.name as keyof T] as string;
	}

	/**
	 * Transforms a string into a canonical form for scoring.
	 */
	transformString(string: string): string {
		return this.transformStringFunc(string);
	}

	/**
	 * Compares two items based on their scores, or on their `sortKey` if the
	 * scores are identical.
	 */
	compareScoredStrings(a: ScoredObject<T>, b: ScoredObject<T>): number {
		// use the transformed versions of the strings for sorting
		const itemA = a._;
		const itemB = b._;
		const itemAString = itemA;
		const itemBString = itemB;

		if (a.score === b.score) {
			// sort undefineds to the end of the array, as per the ES spec
			if (itemAString === undefined || itemBString === undefined) {
				if (itemAString === undefined && itemBString === undefined) {
					return 0;
				} else if (itemAString === undefined) {
					return 1;
				} else {
					return -1;
				}
			} else if (itemAString === itemBString) {
				return 0;
			} else if ((itemAString as {}) < (itemBString as {})) {
				return -1;
			} else {
				return 1;
			}
		} else {
			return b.score - a.score;
		}
	}
}

/**
 * string preprocessor
 */
function toLocaleLowerCase(string: string): string {
	return string.toLocaleLowerCase();
}
