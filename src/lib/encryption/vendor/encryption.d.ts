/* tslint:disable */
/* eslint-disable */

export class Session {
    free(): void;
    [Symbol.dispose](): void;
    add(key_package: string, expected: string, bindings: string): string;
    commit_updates(): string;
    create(): void;
    encrypt(text: string): string;
    join(welcome: string, bindings: string): void;
    key_package(): string;
    members(): string;
    constructor(identity_json: string, host: string);
    process(packet: string, expected: string, bindings: string): string;
    public_key(): string;
    remove(participation: string, bindings: string): string;
    update(): string;
}

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly __wbg_session_free: (a: number, b: number) => void;
    readonly session_add: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => [number, number, number, number];
    readonly session_commit_updates: (a: number) => [number, number, number, number];
    readonly session_create: (a: number) => [number, number];
    readonly session_encrypt: (a: number, b: number, c: number) => [number, number, number, number];
    readonly session_join: (a: number, b: number, c: number, d: number, e: number) => [number, number];
    readonly session_key_package: (a: number) => [number, number, number, number];
    readonly session_members: (a: number) => [number, number, number, number];
    readonly session_new: (a: number, b: number, c: number, d: number) => [number, number, number];
    readonly session_process: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => [number, number, number, number];
    readonly session_public_key: (a: number) => [number, number];
    readonly session_remove: (a: number, b: number, c: number, d: number, e: number) => [number, number, number, number];
    readonly session_update: (a: number) => [number, number, number, number];
    readonly __wbindgen_exn_store: (a: number) => void;
    readonly __externref_table_alloc: () => number;
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __externref_table_dealloc: (a: number) => void;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
