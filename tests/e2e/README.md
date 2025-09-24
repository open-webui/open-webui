# End-to-End Test Suite

This directory contains comprehensive end-to-end tests for Open WebUI functionality using Playwright.

## Test Organization

Tests are organized by feature area following the established patterns:

### Test Files

- **`pii.spec.ts`** - PII (Personally Identifiable Information) detection and masking tests
- **`file-upload.spec.ts`** - File upload functionality including progress bars and PII detection

### Helper Utilities

- **`utils/pii-helpers.ts`** - Helper functions for PII-related testing
- **`utils/file-upload-helpers.ts`** - Helper functions for file upload testing

### Test Files

- **`test_files/`** - Test files used during e2e testing
  - `line.break.entity.docx` - Document with PII entities for testing PII detection
  - `simple-test.txt` - Simple text file for basic upload testing

## Running Tests

### All E2E Tests

```bash
npm run test:e2e
```

### With Browser UI (Headed Mode)

```bash
npm run test:e2e:headed
```

### Debug Mode

```bash
npm run test:e2e:debug
```

### Specific Feature Tests

#### PII Functionality Tests

```bash
npm run test:e2e:pii
```

#### File Upload Tests

```bash
npm run test:e2e:file-upload
```

### View Test Reports

```bash
npm run test:e2e:report
```

## File Upload Test Coverage

The file upload tests cover:

### Core Upload Functionality

- Drag and drop file uploads
- File input dialog uploads
- Multiple file uploads
- File removal from upload list

### Progress Bar and Status Monitoring

- Upload progress indicators
- File processing status transitions
- Error handling and graceful failures
- Performance monitoring

### PII Integration

- PII detection in uploaded files
- Filename masking when PII detection is enabled
- PII entity persistence across sessions
- Integration with chat PII functionality

### Edge Cases

- Large file uploads
- Concurrent file uploads
- State persistence across UI interactions
- Error recovery

## Prerequisites

1. **Development Server**: Application must be running on `localhost:5173`
2. **Authentication**: Tests assume user authentication with `max@nenna.ai` / `test`
3. **Test Files**: Required test files must be present in `test_files/` directory
4. **PII Service**: For PII-related tests, NENNA.ai PII detection service should be configured

## Configuration

Tests automatically handle:

- Login flow if authentication is required
- Application initialization and loading
- PII service availability detection
- File upload capability verification

## Test Data

### Available Test Files

- **PII Document** (`line.break.entity.docx`): ~13KB document with PII entities
- **Simple Text** (`simple-test.txt`): Basic text file without PII
- **Model File** (`sd-empty.pt`): Binary model file for large upload testing

### Test Scenarios

Each test file supports different scenarios:

- Basic upload mechanics
- Progress monitoring
- PII detection validation
- Performance benchmarking

## Debugging

### Console Logging

Tests capture and log relevant console messages during:

- File upload operations
- PII detection processes
- Progress status changes
- Error conditions

### Browser Developer Tools

When running in headed mode (`--headed`) or debug mode (`--debug`):

- Use browser developer tools to inspect application state
- Monitor network requests for file uploads
- Check console for detailed error messages

### Playwright Inspector

Debug mode provides:

- Step-by-step test execution
- Element inspection capabilities
- Screenshot capture on failures
- Trace recording for analysis

## Extending Tests

### Adding New Test Files

1. Place test files in `tests/e2e/test_files/`
2. Update `FILE_TEST_DATA` in `file-upload-helpers.ts`
3. Add scenarios to `FILE_UPLOAD_SCENARIOS` if needed

### Adding New Test Cases

1. Follow the established pattern in existing spec files
2. Use helper classes for common operations
3. Include proper error handling and timeout management
4. Add console logging for debugging support

### Helper Function Guidelines

- Create reusable functions in helper classes
- Include robust selector strategies (multiple fallbacks)
- Handle timing issues with appropriate waits
- Provide meaningful error messages

## Troubleshooting

### Common Issues

#### File Not Found Errors

- Verify test files exist in `test_files/` directory
- Check file paths in `FILE_TEST_DATA` configuration
- Ensure file permissions allow reading

#### Upload Timeout Issues

- Increase timeout values for large files
- Check network connectivity and server responsiveness
- Verify file size limits in application configuration

#### PII Detection Not Working

- Confirm PII service is configured and accessible
- Check API key configuration in application settings
- Verify PII detection is enabled in user interface

#### Authentication Failures

- Verify test credentials are correct
- Check if application requires different login flow
- Ensure development environment matches production authentication

### Performance Considerations

- File upload tests may take longer than standard UI tests
- Large files (>10MB) may require extended timeouts
- Concurrent upload tests may stress development server

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on state from previous tests
2. **Resource Cleanup**: Remove uploaded files after tests complete
3. **Timeout Management**: Use appropriate timeouts for file operations
4. **Error Handling**: Include graceful handling of missing features or services
5. **Documentation**: Keep test documentation updated with new features

## Integration with CI/CD

When running in automated environments:

- Use headless mode for performance
- Configure appropriate timeouts for slower environments
- Ensure test files are included in CI artifacts
- Set up proper credentials management for authentication
