/**
 * API Key Selection Utility
 *
 * This utility provides functions for selecting API keys based on different strategies.
 * It supports random, round-robin, least-recently-used, and weighted selection methods.
 */

// Key selection strategies
export enum KeySelectionStrategy {
  /** Select a random key each time */
  RANDOM = 'random',
  /** Select keys in sequence, cycling through all available keys */
  ROUND_ROBIN = 'round-robin',
  /** Select the least recently used key */
  LEAST_RECENTLY_USED = 'least-recently-used',
  /** Select keys based on weighted distribution (if weights are provided) */
  WEIGHTED = 'weighted',
}

// Options for API key selection
export interface ApiKeyOptions {
  /** Strategy to use for selecting API keys */
  strategy?: KeySelectionStrategy;
  /** Enable caching of API keys to reduce lookups */
  enableCache?: boolean;
  /** Cache TTL in milliseconds (default: 5 minutes) */
  cacheTTL?: number;
  /** Custom validation function for API keys */
  validateKey?: (key: string) => boolean;
  /** Enable debug logging */
  debug?: boolean;
  /** Key weights for weighted distribution (only used with WEIGHTED strategy) */
  weights?: Record<string, number>;
}

// In-memory cache for API keys
const apiKeyCache: Record<
  string,
  {
    keys: string[];
    timestamp: number;
    lastUsedIndex?: number;
    lastUsed?: Record<string, number>;
  }
> = {};

/**
 * Select an API key from a list of keys based on the specified strategy
 *
 * @param connectionId - Unique identifier for the connection (used for caching)
 * @param keys - Array of API keys to select from
 * @param options - Options for key selection
 * @returns The selected API key
 */
export function selectApiKey(
  connectionId: string,
  keys: string[],
  options: ApiKeyOptions = {}
): string {
  // Validate inputs
  if (!connectionId || typeof connectionId !== 'string') {
    throw new Error('Connection ID must be a non-empty string');
  }

  if (!keys || !Array.isArray(keys) || keys.length === 0) {
    throw new Error('No API keys available');
  }

  // If there's only one key, return it directly without further processing
  if (keys.length === 1) {
    return keys[0];
  }

  // Default options
  const {
    strategy = KeySelectionStrategy.RANDOM,
    enableCache = true,
    cacheTTL = 5 * 60 * 1000, // 5 minutes
    validateKey,
    debug = false,
    weights = {},
  } = options;

  // Check cache first if enabled
  const now = Date.now();
  if (
    enableCache &&
    apiKeyCache[connectionId] &&
    now - apiKeyCache[connectionId].timestamp < cacheTTL
  ) {
    if (debug) console.log(`[selectApiKey] Cache hit for connection: ${connectionId}`);
    return selectKeyFromCache(connectionId, keys, strategy, weights, validateKey, debug);
  }

  // Update cache
  apiKeyCache[connectionId] = {
    keys,
    timestamp: now,
    lastUsedIndex: apiKeyCache[connectionId]?.lastUsedIndex,
    lastUsed: apiKeyCache[connectionId]?.lastUsed || {},
  };

  return selectKeyFromCache(connectionId, keys, strategy, weights, validateKey, debug);
}

/**
 * Helper function to select a key from the cache based on the specified strategy
 * @private
 */
function selectKeyFromCache(
  connectionId: string,
  keys: string[],
  strategy: KeySelectionStrategy,
  weights: Record<string, number>,
  validateKey?: (key: string) => boolean,
  debug = false,
): string {
  const cache = apiKeyCache[connectionId];
  let selectedKey: string | undefined;

  switch (strategy) {
    case KeySelectionStrategy.ROUND_ROBIN:
      // Initialize or increment the last used index
      cache.lastUsedIndex =
        cache.lastUsedIndex === undefined ? 0 : (cache.lastUsedIndex + 1) % keys.length;
      selectedKey = keys[cache.lastUsedIndex];
      if (debug) console.log(`[selectApiKey] Round-robin selected key index: ${cache.lastUsedIndex}`);
      break;

    case KeySelectionStrategy.LEAST_RECENTLY_USED:
      // Initialize lastUsed if needed
      if (!cache.lastUsed) {
        cache.lastUsed = {};
        keys.forEach((key) => {
          cache.lastUsed![key] = 0;
        });
      }

      // Find the least recently used key
      selectedKey = keys.reduce((leastUsed, current) => {
        const leastUsedTime = cache.lastUsed![leastUsed] || 0;
        const currentTime = cache.lastUsed![current] || 0;

        return currentTime < leastUsedTime ? current : leastUsed;
      }, keys[0]);

      // Update the last used timestamp
      cache.lastUsed[selectedKey] = Date.now();
      if (debug)
        console.log(`[selectApiKey] Least-recently-used selected key`);
      break;

    case KeySelectionStrategy.WEIGHTED: {
      // Check if weights are provided
      const hasWeights = Object.keys(weights).length > 0;

      if (hasWeights) {
        // Calculate total weight
        let totalWeight = 0;
        const keyWeights: number[] = [];

        keys.forEach((key, index) => {
          const weight = weights[key] || 1;
          keyWeights[index] = weight;
          totalWeight += weight;
        });

        // Select a random point in the total weight
        const random = Math.random() * totalWeight;
        let weightSum = 0;
        let keySelected = false;

        // Find the key at the random point
        for (let i = 0; i < keys.length; i++) {
          weightSum += keyWeights[i];
          if (random <= weightSum) {
            selectedKey = keys[i];
            keySelected = true;
            if (debug) console.log(`[selectApiKey] Weighted selection chose key index: ${i}`);
            break;
          }
        }

        // Fallback to first key if something went wrong
        if (!keySelected) {
          selectedKey = keys[0];
          if (debug) console.log(`[selectApiKey] Weighted selection fallback to first key`);
        }
      } else {
        // If no weights provided, fall back to random selection
        const randomIndex = Math.floor(Math.random() * keys.length);
        selectedKey = keys[randomIndex];
        if (debug)
          console.log(`[selectApiKey] No weights provided, using random selection: ${randomIndex}`);
      }
      break;
    }

    case KeySelectionStrategy.RANDOM:
    default: {
      // Select a random key
      const randomIndex = Math.floor(Math.random() * keys.length);
      selectedKey = keys[randomIndex];
      if (debug) console.log(`[selectApiKey] Random selection chose key index: ${randomIndex}`);
      break;
    }
  }

  // Validate the selected key if a validation function is provided
  if (selectedKey && validateKey && !validateKey(selectedKey)) {
    // Try to find a valid key
    const validKey = keys.find((key) => validateKey(key));
    if (validKey) {
      if (debug)
        console.log(`[selectApiKey] Selected key failed validation, found alternative valid key`);

      return validKey;
    }
    throw new Error(`No valid API keys available for connection: ${connectionId}`);
  }

  return selectedKey || keys[0];
}

/**
 * Clear the API key cache for a specific connection or all connections
 *
 * @param connectionId - Optional connection ID to clear cache for. If not provided, clears all caches.
 */
export function clearApiKeyCache(connectionId?: string): void {
  if (connectionId) {
    delete apiKeyCache[connectionId];
  } else {
    Object.keys(apiKeyCache).forEach(key => {
      delete apiKeyCache[key];
    });
  }
}
