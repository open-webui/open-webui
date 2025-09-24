# Recording Best Practices for Playwright

## 🎬 Before Recording

1. **Plan Your Test Flow**
   - Write down the exact steps you want to test
   - Identify the key assertions you need
   - Prepare test data/files in advance

2. **Clean Environment**
   - Start with a fresh browser session
   - Clear localStorage/cookies if needed
   - Ensure test files are available

## 🎯 During Recording

### What to Record:

- ✅ Main user interactions (clicks, typing, uploads)
- ✅ Navigation between pages
- ✅ Form submissions
- ✅ File uploads and selections

### What NOT to Record:

- ❌ Long waits (you'll add proper waits later)
- ❌ Mouse movements without purpose
- ❌ Multiple attempts at the same action
- ❌ Browser dev tools interactions

## 🛠️ After Recording

### 1. Clean Up Generated Code

**Before (Raw Recording):**

```typescript
await page.click('div:nth-child(3) > button:nth-child(1)');
await page.waitForTimeout(1000);
await page.click('text=Upload files');
```

**After (Cleaned Up):**

```typescript
// Click file upload button
await page.click('button:has(svg):near([id*="input"])');

// Select upload option from dropdown
await page.click('text=Upload files');

// Wait for file dialog to be ready
await page.waitForSelector('input[type="file"]:not(#camera-input)');
```

### 2. Add Proper Assertions

**Add to recorded code:**

```typescript
// Verify file appears in list
await expect(page.locator('text=filename.txt')).toBeVisible();

// Verify upload progress
await page.waitForSelector('.upload-progress', { state: 'hidden' });

// Check for PII detection if applicable
if (expectsPiiDetection) {
	await expect(page.locator('.pii-highlight')).toBeVisible();
}
```

### 3. Make Selectors More Robust

**Replace brittle selectors:**

```typescript
// ❌ Brittle (position-based)
await page.click('div:nth-child(3) > button:nth-child(1)');

// ✅ Robust (semantic)
await page.click('button[aria-label="Upload files"]');
await page.click('button:has-text("Upload")');
await page.click('[data-testid="file-upload-button"]');
```

### 4. Add Error Handling

```typescript
// Check if element exists before interacting
const uploadButton = page.locator('button:has(svg):near([id*="input"])');
await expect(uploadButton).toBeVisible({ timeout: 10000 });
await uploadButton.click();

// Handle file upload errors
try {
	await page.setInputFiles('input[type="file"]', filePath);
} catch (error) {
	console.log('File upload failed:', error);
	throw error;
}
```

## 🔄 Integration with Existing Tests

### Using Recorded Code in Helper Functions

```typescript
// Extract recorded actions into reusable helpers
class FileUploadHelpers {
	// This method contains refined recorded interactions
	async uploadFileViaUI(filePath: string) {
		// Click upload button (from recording)
		await this.page.click('button:has(svg):near([id*="input"])');

		// Select upload option (from recording)
		await this.page.click('text=Upload files');

		// Upload file (from recording, but with error handling)
		await this.page.setInputFiles('input[type="file"]:not(#camera-input)', filePath);
	}
}
```

### Combining with Existing Test Patterns

```typescript
test('file upload with recorded interactions', async ({ page }) => {
	// Use existing setup
	const helpers = new FileUploadTestHelpers(page);

	// Use recorded workflow
	await helpers.uploadFileViaUI(FILE_TEST_DATA.SIMPLE_TEXT);

	// Use existing verification methods
	await helpers.verifyFileInList('simple-test.txt');
	await helpers.waitForUploadProgress('simple-test.txt');
});
```

## 📊 Recording Different Scenarios

### 1. Happy Path Recording

```bash
npx playwright codegen -o tests/e2e/recorded-happy-path.spec.ts http://localhost:5173
# Record: Upload → Verify → Success
```

### 2. Error Path Recording

```bash
npx playwright codegen -o tests/e2e/recorded-error-path.spec.ts http://localhost:5173
# Record: Invalid file → Error message → Recovery
```

### 3. PII Workflow Recording

```bash
npx playwright codegen -o tests/e2e/recorded-pii-workflow.spec.ts http://localhost:5173
# Record: Upload PII file → Detect entities → Toggle masking → Verify
```

## 🎯 Tips for Better Recordings

1. **Slow Down**: Don't rush through interactions
2. **Be Deliberate**: Only click what you intend to test
3. **Use Inspector**: Watch the generated code as you go
4. **Test Immediately**: Run the recorded test right after recording
5. **Refactor Early**: Clean up code while interactions are fresh in memory

## 🐛 Common Recording Issues

### Issue: Flaky Selectors

```typescript
// ❌ Generated (brittle)
await page.click('div:nth-child(5)');

// ✅ Fixed (semantic)
await page.click('[data-testid="upload-button"]');
await page.click('button:has-text("Upload")');
```

### Issue: Missing Waits

```typescript
// ❌ Generated (no wait)
await page.click('button');
await page.fill('input', 'text');

// ✅ Fixed (proper waits)
await page.click('button');
await page.waitForSelector('input');
await page.fill('input', 'text');
```

### Issue: Hard-coded Paths

```typescript
// ❌ Generated (hard-coded)
await page.setInputFiles('input', '/Users/user/file.txt');

// ✅ Fixed (relative)
await page.setInputFiles('input', 'tests/e2e/test_files/file.txt');
```
