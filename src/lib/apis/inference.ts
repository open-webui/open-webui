/**
 * Inference API facade.
 *
 * This module is the single neutral seam between the UI and the inference
 * engine (Ollama / OpenAI). UI components import inference-related functions
 * exclusively from here, never from the provider-specific engine modules
 * (`$lib/inference/ollama` / `$lib/inference/openai`).
 *
 * The engine modules located under `$lib/inference/` implement the actual
 * provider calls and can be swapped or removed without touching any UI.
 *
 * Re-exports Ollama operations.
 */
export * from '$lib/inference/ollama';
export * from '$lib/inference/openai';