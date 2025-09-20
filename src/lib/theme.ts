/**
 * @file This file serves as the main entry point for the theming system.
 * It re-exports all the necessary functions and stores from the deconstructed
 * theme modules. This allows other parts of the application to have a single,
 * consistent import path for all theme-related functionalities, and avoids the
 * need to refactor all imports at once.
 */

export * from '$lib/stores/theme';
export * from '$lib/themes/apply';
export * from '$lib/themes/community';
