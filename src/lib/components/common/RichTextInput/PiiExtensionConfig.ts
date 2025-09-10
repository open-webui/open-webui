/**
 * Centralized configuration for PII Detection and Modifier Extensions
 * Contains all hard-coded values, timeouts, styling, and behavioral constants
 */

export interface PiiExtensionConfig {
	/** Performance and Debugging */
	performance: {
		/** Enable performance tracking */
		enabled: boolean;
		/** Log slow operations to console */
		logSlowOperations: boolean;
		/** Thresholds for slow operation logging (ms) */
		thresholds: {
			positionMapping: number;
			decorationUpdate: number;
			apiCall: number;
			persistence: number;
		};
	};

	/** Timing and Performance */
	timing: {
		/** Default debounce delay for PII detection (ms) */
		defaultDebounceMs: number;
		/** Hover timeout before showing menu (ms) */
		hoverTimeoutMs: number;
		/** Menu close timeout after mouse leave (ms) */
		menuCloseTimeoutMs: number;
		/** Fallback timeout for menu auto-close (ms) */
		menuFallbackTimeoutMs: number;
		/** Typing pause detection threshold (ms) */
		typingPauseThresholdMs: number;
		/** Smart debounce timing adjustments */
		smartDebounce: {
			/** Minimum debounce delay (ms) */
			minDelayMs: number;
			/** Fast detection multiplier for many words */
			fastMultiplier: number;
			/** Slow detection multiplier for few words */
			slowMultiplier: number;
			/** Slow detection multiplier for short words */
			shortWordMultiplier: number;
		};
	};

	/** Text Processing */
	textProcessing: {
		/** Context expansion size for tokenization (characters) */
		contextExpansionChars: number;
		/** Minimum text length for entity matching */
		minTextLengthForMatching: number;
		/** Minimum entity length for processing */
		minEntityLength: number;
		/** Content length threshold for preview truncation */
		contentPreviewLength: number;
		/** Change ratio threshold for content detection */
		contentChangeThreshold: number;
		/** Large content threshold for smart debouncing */
		largeContentThreshold: number;
		/** Many words threshold for smart debouncing */
		manyWordsThreshold: number;
		/** Few words threshold for smart debouncing */
		fewWordsThreshold: number;
		/** Short word length threshold */
		shortWordThreshold: number;
	};

	/** PII Entity Type Priorities */
	entityTypePriorities: Record<string, number>;

	/** CSS Styling */
	styling: {
		/** Style element IDs */
		styleElementId: string;
		/** Z-index values */
		zIndex: {
			/** Modifier highlights (higher priority) */
			modifierHighlight: number;
		};
		/** Border radius for highlights */
		borderRadius: string;
		/** Padding for highlights */
		highlightPadding: string;
		/** Transition duration */
		transitionDuration: string;
		/** Modifier colors */
		modifierColors: {
			/** Text color for modifiers */
			textColor: string;
			/** Hover text color */
			textHoverColor: string;
			/** Mask background color */
			maskBackgroundColor: string;
			/** Mask background hover color */
			maskBackgroundHoverColor: string;
			/** Mask border color */
			maskBorderColor: string;
			/** Ignore opacity */
			ignoreOpacity: number;
			/** Ignore hover opacity */
			ignoreHoverOpacity: number;
		};
		/** Box shadow values */
		boxShadow: {
			/** Default hover shadow */
			hover: string;
			/** Enhanced hover shadow */
			hoverEnhanced: string;
		};
	};

	/** Regex Patterns */
	patterns: {
		/** Entity normalization - leading trim pattern */
		entityNormalizationLeading: RegExp;
		/** Entity normalization - trailing trim pattern */
		entityNormalizationTrailing: RegExp;
		/** Tokenization pattern for fallback text matching */
		tokenizationFallback: RegExp;
		/** Alpha-numeric character detection */
		alphaNumeric: RegExp;
	};
}

/** Default configuration values */
export const DEFAULT_PII_CONFIG: PiiExtensionConfig = {
	performance: {
		enabled: true,
		logSlowOperations: true,
		thresholds: {
			positionMapping: 10,
			decorationUpdate: 20,
			apiCall: 1000,
			persistence: 100
		}
	},

	timing: {
		defaultDebounceMs: 500,
		hoverTimeoutMs: 300,
		menuCloseTimeoutMs: 500,
		menuFallbackTimeoutMs: 10000,
		typingPauseThresholdMs: 1000,
		smartDebounce: {
			minDelayMs: 400,
			fastMultiplier: 0.8,
			slowMultiplier: 2.0,
			shortWordMultiplier: 1.5
		}
	},

	textProcessing: {
		contextExpansionChars: 100,
		minTextLengthForMatching: 2,
		minEntityLength: 3,
		contentPreviewLength: 50,
		contentChangeThreshold: 0.5,
		largeContentThreshold: 200,
		manyWordsThreshold: 10,
		fewWordsThreshold: 3,
		shortWordThreshold: 4
	},

	entityTypePriorities: {
		PERSON: 5,
		ADDRESS: 4,
		DATE: 4,
		EMAIL: 4,
		PHONE_NUMBER: 4,
		ORGANISATION: 3,
		ORGANIZATION: 3,
		LOCATION: 3
	},

	styling: {
		styleElementId: 'pii-modifier-styles',
		zIndex: {
			modifierHighlight: 10
		},
		borderRadius: '3px',
		highlightPadding: '1px 2px',
		transitionDuration: '0.2s',
		modifierColors: {
			textColor: '#ca8a04',
			textHoverColor: '#a16207',
			maskBackgroundColor: 'rgba(34, 197, 94, 0.2)',
			maskBackgroundHoverColor: 'rgba(34, 197, 94, 0.3)',
			maskBorderColor: '#15803d',
			ignoreOpacity: 0.7,
			ignoreHoverOpacity: 0.9
		},
		boxShadow: {
			hover: '0 1px 3px rgba(0,0,0,0.2)',
			hoverEnhanced: '0 2px 8px rgba(0,0,0,0.1)'
		}
	},

	patterns: {
		entityNormalizationLeading: /^[\s\u00A0\t|:;.,\-_/\\]+/,
		entityNormalizationTrailing: /[\s\u00A0\t|:;.,\-_/\\]+$/,
		tokenizationFallback: /[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_-]*|[0-9]+(?:[.,][0-9]+)*/gu,
		alphaNumeric: /[A-Za-z0-9À-ÿ]/
	}
};

/**
 * Get configuration with optional overrides
 * @param overrides Partial configuration to override defaults
 * @returns Complete configuration object
 */
export function getPiiConfig(overrides?: Partial<PiiExtensionConfig>): PiiExtensionConfig {
	if (!overrides) return DEFAULT_PII_CONFIG;

	return {
		performance: {
			...DEFAULT_PII_CONFIG.performance,
			...overrides.performance,
			thresholds: {
				...DEFAULT_PII_CONFIG.performance.thresholds,
				...overrides.performance?.thresholds
			}
		},
		timing: { ...DEFAULT_PII_CONFIG.timing, ...overrides.timing },
		textProcessing: { ...DEFAULT_PII_CONFIG.textProcessing, ...overrides.textProcessing },
		entityTypePriorities: {
			...DEFAULT_PII_CONFIG.entityTypePriorities,
			...overrides.entityTypePriorities
		},
		styling: {
			...DEFAULT_PII_CONFIG.styling,
			...overrides.styling,
			modifierColors: {
				...DEFAULT_PII_CONFIG.styling.modifierColors,
				...overrides.styling?.modifierColors
			},
			boxShadow: { ...DEFAULT_PII_CONFIG.styling.boxShadow, ...overrides.styling?.boxShadow }
		},
		patterns: { ...DEFAULT_PII_CONFIG.patterns, ...overrides.patterns }
	};
}
