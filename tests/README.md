# PII Testing with Playwright

This directory contains end-to-end tests for the PII (Personally Identifiable Information) functionality in Open WebUI using Playwright.

## Setup

### 1. Install Playwright

First, install Playwright as a development dependency:

```bash
npm install --save-dev @playwright/test
```

### 2. Install Playwright Browsers

Install the required browsers for testing:

```bash
npx playwright install
```

### 3. Add Scripts to package.json

Add these scripts to your `package.json` file in the scripts section:

```json
{
	"scripts": {
		"test:e2e": "playwright test",
		"test:e2e:headed": "playwright test --headed",
		"test:e2e:debug": "playwright test --debug",
		"test:e2e:pii": "playwright test tests/e2e/pii.spec.ts",
		"test:e2e:report": "playwright show-report"
	}
}
```

## Running the Tests

### Prerequisites

1. **Start the development server**:

   ```bash
   npm run dev
   ```

   The application should be running on `http://localhost:5173`

2. **Ensure PII API is configured**:
   - Make sure you have a valid PII API key configured
   - The NENNA.ai PII service should be accessible
   - Verify the PII detection is working by testing manually first

### Run All E2E Tests

```bash
npm run test:e2e
```

### Run Only PII Tests

```bash
npm run test:e2e:pii
```

### Run Tests in Headed Mode (See Browser)

```bash
npm run test:e2e:headed
```

### Debug Tests

```bash
npm run test:e2e:debug
```

### View Test Reports

```bash
npm run test:e2e:report
```

## Test Structure

### PII Test Suite (`tests/e2e/pii.spec.ts`)

The main PII test suite covers:

1. **PII Detection**: Verifies that PII is detected in user input
2. **Masking**: Tests that PII is masked before sending to AI
3. **Masking Toggle**: Tests the toggle functionality to enable/disable masking
4. **Unmasking**: Verifies PII is properly unmasked in the display
5. **State Persistence**: Tests that PII entities are maintained across the conversation
6. **Error Handling**: Verifies graceful handling of API errors
7. **UI Indicators**: Tests visual indicators for PII status

### Test Utilities (`tests/e2e/utils/pii-helpers.ts`)

Helper functions and test data for consistent PII testing:

- `PiiTestHelpers`: Class with methods for common PII testing actions
- `PII_TEST_DATA`: Predefined test messages with different types of PII
- `PII_TEST_SCENARIOS`: Test scenarios for comprehensive coverage

## Test Data

The tests use German text examples to match the application's target audience:

- `Max F aus Berlin.` - Basic person and location
- `Mein Name ist Sarah Schmidt und ich wohne in München.` - Full name and city
- `Dr. Maria Rodriguez aus Barcelona.` - Professional title and international location

## Configuration

The tests are configured through `playwright.config.ts`:

- Base URL: `http://localhost:5173`
- Browsers: Chrome, Firefox, Safari
- Retries: 2 on CI, 0 locally
- Timeout: Default Playwright timeouts
- Web Server: Automatically starts dev server if not running

## Troubleshooting

### Common Issues

1. **Tests fail with timeout errors**:
   - Ensure the development server is running on port 5173
   - Check that the PII API is responding correctly
   - Increase timeout values if PII detection is slow

2. **PII detection not working**:
   - Verify API key is properly configured
   - Check console logs for PII-related errors
   - Test PII functionality manually first

3. **Login issues**:
   - The tests assume the application handles auto-login
   - If manual login is required, update the `loginAs` method in `pii-helpers.ts`

4. **Element selectors not found**:
   - The UI selectors may need updating if the interface changes
   - Use Playwright's inspector to find correct selectors: `npx playwright codegen localhost:5173`

### Debugging Tips

1. **Use headed mode** to see what's happening:

   ```bash
   npm run test:e2e:headed
   ```

2. **Use debug mode** to step through tests:

   ```bash
   npm run test:e2e:debug
   ```

3. **Take screenshots** on failure by adding to test:

   ```typescript
   await page.screenshot({ path: 'failure.png' });
   ```

4. **Check console logs** during tests:
   ```typescript
   page.on('console', (msg) => console.log(msg.text()));
   ```

## Contributing

When adding new PII tests:

1. Add test cases to `pii.spec.ts`
2. Use the helper functions from `pii-helpers.ts`
3. Add new test data to `PII_TEST_DATA` if needed
4. Follow the existing naming conventions
5. Ensure tests are deterministic and can run in any order

## CI/CD Integration

To integrate with continuous integration:

1. Add Playwright to your CI workflow
2. Install dependencies and browsers in CI
3. Start the application server
4. Run tests with retry logic
5. Upload test reports and screenshots as artifacts

Example GitHub Actions step:

```yaml
- name: Run PII E2E tests
  run: |
    npm ci
    npx playwright install --with-deps
    npm run dev &
    npx playwright test tests/e2e/pii.spec.ts
```
