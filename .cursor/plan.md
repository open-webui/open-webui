# Refactoring Plan for RAUX Python Setup

## Current Structure

- `index.ts`: Main entry point that calls Python/RAUX setup and starts RAUX processes
- `forge.config.ts`: Electron Forge configuration (packaging, resources)
- `pythonExec.ts`: Handles all Python-related functionality (singleton)
- `rauxSetup.ts`: Handles all RAUX-specific installation and environment setup (singleton)

## Progress

### 1. Consolidate Python functionality in `pythonExec.ts`

- [x] Create a new `pythonExec.ts` singleton that encapsulates all Python/pip setup and execution logic
- [x] Expose public methods for Python execution, pip execution, and setup

### 2. Create a dedicated RAUX installer module

- [x] Create `rauxSetup.ts` singleton for RAUX-specific installation and environment configuration
- [x] Use `pythonExec.ts` for all Python/pip operations

### 3. Define clear interface for Python execution

- [x] Create a public interface in `pythonExec.ts`:
  ```typescript
  export interface PythonExecutor {
    runPythonCommand(command: string[], options?: ExecutionOptions): Promise<ExecutionResult>;
    runPipCommand(command: string[], options?: ExecutionOptions): Promise<ExecutionResult>;
    getPythonPath(): string;
    ensurePythonInstalled(): Promise<void>;
  }
  ```

### 4. Design module interactions

- [x] `pythonExec.ts`: Handles all Python-related functionality
  - Private: Installation and setup methods
  - Public: Execution and environment methods
- [x] `rauxSetup.ts`: Uses `pythonExec.ts` to install RAUX packages

### 5. Update imports and usage

- [x] Update `index.ts` to use the new module structure
- [x] Update any other files that directly use Python-related functionality
- [x] Remove the now obsolete RAUX install logic from `pythonSetup.ts`

### 6. Ensure thread safety and error handling

- [ ] Add proper error handling in new modules (partially done, review for completeness)
- [ ] Ensure thread-safe execution of Python commands (review if needed)
- [ ] Add initialization checks to prevent duplicate setup (review if needed)

## Implementation Approach

- [x] Create `pythonExec.ts` by migrating core functionality from `pythonSetup.ts`
- [x] Create `rauxSetup.ts` for RAUX-specific setup
- [x] Update `index.ts` to use the new modules
- [x] Remove RAUX install logic from `pythonSetup.ts` once migration is complete

## TODO
- [ ] Final review for error handling, thread safety, and initialization checks
- [ ] Remove/clean up any remaining legacy code or unused files
