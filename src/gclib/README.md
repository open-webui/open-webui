# GCLib - Custom Code Contribution Pattern

This directory (`src/gclib`) contains our custom modifications to the Open WebUI codebase. The pattern described below allows us to maintain our custom changes while minimizing conflicts when merging updates from the original repository.

## Pattern for Custom Contributions

1. We've created an alias `$gclib` which points to the `src/gclib` folder.

2. When modifying code within the `$lib` alias (which points to `src/lib`):

- Make a copy of the file and place it under the `src/gclib` folder using the same path structure
- For example, if modifying `src/lib/components/common/Example.svelte`, create `src/gclib/components/common/Example.svelte`

3. Replace imports used within the original `$lib` files to instead use the `$gclib` versions:

- Example: Change `import Example from '$lib/components/common/Example.svelte'` to `import Example from '$gclib/components/common/Example.svelte'`

4. In your custom `$gclib` files, continue to use `$gclib` imports for custom components and `$lib` imports for unmodified components.

## Contributing Changes Back to Open WebUI

When developing features that we want to contribute back to the open source project:

1. Changes should be made directly under the `$lib` path, not in `$gclib`

2. Follow the guidelines in the Open WebUI [CONTRIBUTING.md](../../docs/CONTRIBUTING.md) document:

- Open a discussion about your ideas first
- Follow the project's coding standards
- Include tests for new features
- Update documentation as necessary
- Write clear, descriptive commit messages
- Complete pull requests in a timely manner

3. Before submitting a pull request to the Open WebUI repository:

- Ensure the code works with the original imports (not using `$gclib`)
- Test thoroughly to verify functionality
- Remove any company-specific code or references

## Benefits

This approach:

- Isolates all custom code to the `$gclib` directory
- Requires minimal changes to the original `$lib` folder (only import statements)
- Makes it easier to identify and maintain our custom modifications
- Reduces merge conflicts when pulling updates from the original repository
- Provides a clear path for contributing improvements back to the open source project
