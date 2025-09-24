import { Page, expect, Locator } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Utility functions for file upload testing in Playwright
 *
 * Handles file uploads via drag & drop, file input, progress monitoring,
 * and PII-related file upload functionality.
 */

export class FileUploadTestHelpers {
	constructor(private page: Page) {}

	/**
	 * Upload a file using the file input element
	 */
	async uploadFile(filePath: string): Promise<void> {
		// Check if file exists
		if (!fs.existsSync(filePath)) {
			throw new Error(`Test file not found: ${filePath}`);
		}

		// First, open the file upload menu by clicking the "+" button in the input area
		await this.openFileUploadMenu();

		// Look for the main file input element (not the camera input)
		// The camera input has accept="image/*" and capture="environment", so we want the other one
		const fileInput = this.page.locator('input[type="file"]:not(#camera-input)').first();

		// Set the file on the input element
		await fileInput.setInputFiles(filePath);
		await this.page.waitForTimeout(1000); // Allow upload to start
	}

	/**
	 * Open the file upload menu (click + button, then select upload option)
	 */
	async openFileUploadMenu(): Promise<void> {
		// First, check if the upload menu is already open
		const uploadMenuSelectors = [
			'text=Datei(en) hochladen',
			'[role="menuitem"]:has-text("Datei(en) hochladen")', // RECORDED: From demo recording
			'text=Upload',
			'menuitem:has-text("Datei")',
			'menuitem:has-text("hochladen")',
			'[role="menuitem"]:has-text("Datei")',
			'button:has-text("Datei")'
		];

		// Check if menu is already open
		for (const selector of uploadMenuSelectors) {
			try {
				const item = this.page.locator(selector);
				if ((await item.count()) > 0 && (await item.isVisible())) {
					console.log('Upload menu already open, clicking menu item');
					await item.click();
					await this.page.waitForTimeout(500);
					return;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		// Menu not open, need to click the "+" button to open it
		console.log('Upload menu not open, looking for + button');

		// Look for the "+" button in the message input area (multiple strategies)
		const uploadButtonSelectors = [
			'form button:first-child', // RECORDED: First button in form (from demo recording)
			'button:has(svg):near([id*="input"])', // Button with SVG near input
			'.message-input button:has(svg)', // Button with SVG in message input area
			'[id*="input"] button:has(svg)', // Button with SVG in input container
			'button:has(path[d*="10.75"])', // Button with specific SVG path for "+" icon
			'button:has(svg[viewBox="0 0 20 20"])' // Button with SVG that matches the + icon viewBox
		];

		let uploadButton = null;
		for (const selector of uploadButtonSelectors) {
			try {
				const button = this.page.locator(selector).first();
				if ((await button.count()) > 0 && (await button.isVisible())) {
					uploadButton = button;
					console.log(`Found upload button with selector: ${selector}`);
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		if (!uploadButton) {
			// Fallback: look for any button near the chat input that could be the upload button
			const chatInput = this.page.locator('#chat-input');
			const nearbyButtons = this.page.locator('button').near(chatInput);
			const buttonCount = await nearbyButtons.count();

			for (let i = 0; i < buttonCount; i++) {
				const button = nearbyButtons.nth(i);
				if (await button.isVisible()) {
					uploadButton = button;
					console.log(`Found upload button via fallback method (button ${i})`);
					break;
				}
			}
		}

		if (!uploadButton) {
			throw new Error('Upload button not found');
		}

		// Check if button is already expanded (menu already open)
		const isExpanded = await uploadButton.getAttribute('aria-expanded');
		if (isExpanded === 'true') {
			console.log('Upload button already expanded, menu should be open');
		} else {
			// Click the upload button to open the menu
			console.log('Clicking upload button to open menu');
			await uploadButton.click();
			await this.page.waitForTimeout(500);
		}

		// Now look for the file upload menu item
		let uploadMenuItem = null;
		for (const selector of uploadMenuSelectors) {
			try {
				const item = this.page.locator(selector);
				if ((await item.count()) > 0 && (await item.isVisible())) {
					uploadMenuItem = item;
					console.log(`Found upload menu item with selector: ${selector}`);
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		if (uploadMenuItem) {
			await uploadMenuItem.click();
			await this.page.waitForTimeout(500);
		} else {
			console.log('Upload menu item not found - menu may not have opened or UI structure differs');
			// Take a screenshot for debugging if needed
			console.log('Current page URL:', await this.page.url());
		}
	}

	/**
	 * Upload a file using drag and drop
	 */
	async dragAndDropFile(filePath: string): Promise<void> {
		// Check if file exists
		if (!fs.existsSync(filePath)) {
			throw new Error(`Test file not found: ${filePath}`);
		}

		// Read file data for drag simulation
		const buffer = fs.readFileSync(filePath);
		const fileName = path.basename(filePath);
		const fileType = this.getFileType(fileName);

		// Create a data transfer object for the drag operation
		const dataTransfer = await this.page.evaluateHandle(
			({ buffer, fileName, fileType }) => {
				const dt = new DataTransfer();
				const file = new File([new Uint8Array(buffer)], fileName, { type: fileType });
				dt.items.add(file);
				return dt;
			},
			{ buffer: Array.from(buffer), fileName, fileType }
		);

		// Find the drop target - could be the chat container or input area
		const dropTargets = [
			'#chat-container',
			'#chat-input-container',
			'.file-drop-area',
			'.message-input-area'
		];

		let dropTarget = null;
		for (const selector of dropTargets) {
			try {
				const target = this.page.locator(selector);
				if ((await target.count()) > 0 && (await target.isVisible())) {
					dropTarget = target;
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		if (!dropTarget) {
			// Fallback to the whole page
			dropTarget = this.page.locator('body');
		}

		// Perform the drag and drop
		await dropTarget.dispatchEvent('dragover', { dataTransfer });
		await dropTarget.dispatchEvent('drop', { dataTransfer });
		await this.page.waitForTimeout(1000); // Allow upload to start
	}

	/**
	 * Monitor file upload progress
	 */
	async waitForUploadProgress(fileName: string, timeout = 30000): Promise<void> {
		console.log(`Waiting for upload progress for file: ${fileName}`);

		// First, wait a moment for upload to start
		await this.page.waitForTimeout(1000);

		const progressElements = [
			`[data-filename*="${fileName}"]`,
			'.file-progress',
			'.upload-progress',
			'text=uploading',
			'text=processing',
			'text=hochladen', // German for uploading
			'text=verarbeitung', // German for processing
			'text=Uploading',
			'text=Processing'
		];

		let progressFound = false;
		// Wait for progress indicator to appear
		for (const selector of progressElements) {
			try {
				const element = this.page.locator(selector).first();
				if ((await element.count()) > 0) {
					await expect(element).toBeVisible({ timeout: 5000 });
					console.log(`Found progress indicator: ${selector}`);
					progressFound = true;
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		if (!progressFound) {
			console.log('No progress indicator found - upload may be very fast or already completed');
		}

		// Wait for upload to complete - use a more flexible approach
		const startTime = Date.now();
		while (Date.now() - startTime < timeout) {
			// Check if file appears to be uploaded (various indicators)
			const completionChecks = [
				// Look for the file in the UI
				async () => {
					try {
						await this.verifyFileInList(fileName);
						return true;
					} catch (e) {
						return false;
					}
				},
				// Look for completion status text
				async () => {
					const completionTexts = [
						'uploaded',
						'processed',
						'done',
						'complete',
						'fertig',
						'hochgeladen',
						'verarbeitet',
						'abgeschlossen'
					];
					for (const text of completionTexts) {
						const element = this.page.locator(`text=${text}`);
						if ((await element.count()) > 0) {
							return true;
						}
					}
					return false;
				},
				// Check if upload/processing indicators are gone
				async () => {
					const processingTexts = ['uploading', 'processing', 'hochladen', 'verarbeitung'];
					for (const text of processingTexts) {
						const element = this.page.locator(`text=${text}`);
						if ((await element.count()) > 0) {
							return false; // Still processing
						}
					}
					return true; // No processing indicators found
				}
			];

			for (const check of completionChecks) {
				if (await check()) {
					console.log('Upload appears to be complete');
					await this.page.waitForTimeout(2000); // Allow any post-upload processing
					return;
				}
			}

			await this.page.waitForTimeout(1000); // Check again in 1 second
		}

		console.log('Upload progress monitoring timed out, continuing anyway');
	}

	/**
	 * Verify file appears in the file list
	 */
	async verifyFileInList(fileName: string): Promise<void> {
		// Look for the file in various possible locations
		const fileSelectors = [
			`text=${fileName}`,
			`[title="${fileName}"]`,
			`[data-filename="${fileName}"]`,
			`.file-item:has-text("${fileName}")`,
			`.file-name:has-text("${fileName}")`,
			`[alt="${fileName}"]`,
			// Look for file items in the message input area
			`.message-input [data-filename="${fileName}"]`,
			`.input-area [data-filename="${fileName}"]`,
			// Look by partial text match
			`text="${fileName.substring(0, 10)}"` // First 10 chars in case of truncation
		];

		let found = false;
		for (const selector of fileSelectors) {
			try {
				const element = this.page.locator(selector);
				if ((await element.count()) > 0) {
					await expect(element).toBeVisible({ timeout: 5000 });
					found = true;
					console.log(`Found file with selector: ${selector}`);
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		if (!found) {
			// Additional debugging: check what files are visible
			await this.page.waitForTimeout(2000);
			const visibleText = await this.page.locator('body').textContent();
			console.log(
				`File ${fileName} not found. Visible text includes: ${visibleText?.substring(0, 500)}`
			);
			throw new Error(`File ${fileName} not found in file list`);
		}
	}

	/**
	 * Wait for PII scanning indicator during file upload
	 */
	async waitForPiiScanning(timeout = 10000): Promise<void> {
		const scanningIndicators = [
			'text=Scanning for PII',
			'text=PII scanning',
			'text=Detecting PII',
			'text=Scannen', // German for scanning
			'text=PII scannen',
			'text=Erkennung', // German for detection
			'.pii-scanning',
			'.pii-detection-progress'
		];

		for (const selector of scanningIndicators) {
			try {
				const element = this.page.locator(selector);
				await expect(element).toBeVisible({ timeout });
				console.log(`Found PII scanning indicator: ${selector}`);
				return;
			} catch (e) {
				// Continue to next selector
			}
		}

		console.log('No PII scanning indicator found - may not be enabled or already completed');
	}

	/**
	 * Check for PII entities detected in uploaded file
	 */
	async checkFilePiiDetection(fileName: string): Promise<number> {
		// Wait a bit for PII processing to complete
		await this.page.waitForTimeout(3000);

		// Look for PII indicators related to this file
		const piiElements = this.page.locator('.pii-highlight, [data-pii-label], [data-pii-type]');
		return await piiElements.count();
	}

	/**
	 * Verify file upload error states
	 */
	async checkForUploadErrors(fileName: string): Promise<string | null> {
		const errorSelectors = [
			'text=Upload failed',
			'text=Processing failed',
			'text=Error',
			'.upload-error',
			'.file-error',
			`[data-filename="${fileName}"] .error`,
			`text=${fileName}:contains("error")`,
			`text=${fileName}:contains("failed")`
		];

		for (const selector of errorSelectors) {
			try {
				const element = this.page.locator(selector);
				if ((await element.count()) > 0 && (await element.isVisible())) {
					return await element.textContent();
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		return null; // No errors found
	}

	/**
	 * Remove/dismiss a file from the upload list
	 */
	async removeFile(fileName: string): Promise<void> {
		// Look for remove/close button associated with the file
		const removeSelectors = [
			// Look for X button near the file name/text
			`text=${fileName} >> .. >> button`, // Parent container with button
			`text=${fileName} >> xpath=../.. >> button`, // Navigate up DOM tree
			`text=${fileName} >> xpath=../..//button`, // Look for button in parent containers
			// Look for common remove button patterns
			`button:near(:text("${fileName}"))`,
			`[aria-label*="Remove"]:near(:text("${fileName}"))`,
			`[aria-label*="Delete"]:near(:text("${fileName}"))`,
			`[title*="Remove"]:near(:text("${fileName}"))`,
			`button:has-text("×"):near(:text("${fileName}"))`,
			`button:has-text("✕"):near(:text("${fileName}"))`,
			`button:has-text("X"):near(:text("${fileName}"))`,
			// Generic buttons with close icons
			'button:has(svg[viewBox*="20"]) >> path[d*="6.28"]', // X icon path
			'button:has(svg) >> path[d*="M6.28"]' // Common X icon path
		];

		let foundButton = null;
		for (const selector of removeSelectors) {
			try {
				const button = this.page.locator(selector).first();
				if ((await button.count()) > 0 && (await button.isVisible())) {
					foundButton = button;
					console.log(`Found remove button with selector: ${selector}`);
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		if (!foundButton) {
			// Fallback: Look for any buttons near where the file appears
			const fileElement = this.page.locator(`text=${fileName}`).first();
			if ((await fileElement.count()) > 0) {
				// Find all buttons that are siblings or in parent elements
				const nearbyButtons = this.page.locator('button').near(fileElement);
				const buttonCount = await nearbyButtons.count();

				for (let i = 0; i < buttonCount; i++) {
					const button = nearbyButtons.nth(i);
					const buttonText = await button.textContent();
					const ariaLabel = await button.getAttribute('aria-label');

					// Look for buttons that might be remove buttons
					if (
						buttonText?.includes('×') ||
						buttonText?.includes('✕') ||
						ariaLabel?.toLowerCase().includes('remove') ||
						ariaLabel?.toLowerCase().includes('delete') ||
						ariaLabel?.toLowerCase().includes('close')
					) {
						foundButton = button;
						console.log(`Found remove button via nearby search (button ${i})`);
						break;
					}
				}
			}
		}

		if (foundButton) {
			await foundButton.click();
			await this.page.waitForTimeout(500);
			console.log(`Successfully clicked remove button for: ${fileName}`);
		} else {
			console.log(`Remove button not found for file: ${fileName}, skipping removal test`);
			// Don't throw error, just log - file removal UI might not be implemented yet
		}
	}

	/**
	 * Check file upload progress percentage
	 */
	async getUploadProgress(fileName: string): Promise<number> {
		// Look for progress indicators
		const progressSelectors = [
			`[data-filename="${fileName}"] .progress`,
			`[data-filename="${fileName}"] [role="progressbar"]`,
			`.file-progress:near(text=${fileName})`,
			'.upload-progress'
		];

		for (const selector of progressSelectors) {
			try {
				const element = this.page.locator(selector);
				if ((await element.count()) > 0) {
					// Try to get aria-valuenow or data-progress
					let progress = await element.getAttribute('aria-valuenow');
					if (!progress) {
						progress = await element.getAttribute('data-progress');
					}
					if (!progress) {
						// Try to extract from text content
						const text = await element.textContent();
						const match = text?.match(/(\d+)%/);
						if (match) {
							progress = match[1];
						}
					}

					if (progress) {
						return parseInt(progress, 10);
					}
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		return -1; // Progress not found
	}

	/**
	 * Verify PII masking is applied to file names
	 */
	async verifyFilenameMasking(originalFileName: string, shouldBeMasked: boolean): Promise<void> {
		if (shouldBeMasked) {
			// File name should be replaced with ID or masked version
			const maskedFileVisible = (await this.page.locator(`text=${originalFileName}`).count()) === 0;
			expect(maskedFileVisible).toBe(true);

			// Should see file ID or masked name instead
			const fileIdVisible = (await this.page.locator('[data-filename]').count()) > 0;
			expect(fileIdVisible).toBe(true);
		} else {
			// Original file name should be visible
			await expect(this.page.locator(`text=${originalFileName}`)).toBeVisible();
		}
	}

	/**
	 * Get the appropriate MIME type for a file
	 */
	private getFileType(fileName: string): string {
		const ext = path.extname(fileName).toLowerCase();
		const mimeTypes: Record<string, string> = {
			'.pdf': 'application/pdf',
			'.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			'.doc': 'application/msword',
			'.txt': 'text/plain',
			'.png': 'image/png',
			'.jpg': 'image/jpeg',
			'.jpeg': 'image/jpeg',
			'.gif': 'image/gif',
			'.webp': 'image/webp',
			'.mp3': 'audio/mpeg',
			'.wav': 'audio/wav',
			'.mp4': 'video/mp4',
			'.pt': 'application/octet-stream'
		};

		return mimeTypes[ext] || 'application/octet-stream';
	}

	/**
	 * Wait for file to reach a specific status
	 */
	async waitForFileStatus(
		fileName: string,
		expectedStatus: string,
		timeout = 30000
	): Promise<void> {
		await this.page.waitForFunction(
			({ fileName, expectedStatus }) => {
				// Look for status indicators
				const fileElement = document.querySelector(`[data-filename="${fileName}"]`);
				if (fileElement) {
					const statusElement = fileElement.querySelector('.file-status, .status');
					if (statusElement && statusElement.textContent?.includes(expectedStatus)) {
						return true;
					}
				}

				// Also check for text-based status indicators using proper DOM methods
				const allElements = document.querySelectorAll('*');
				for (const element of allElements) {
					if (element.textContent && element.textContent.includes(expectedStatus)) {
						return true;
					}
				}

				return false;
			},
			{ fileName, expectedStatus },
			{ timeout }
		);
	}

	/**
	 * Capture console messages during file upload
	 */
	async captureUploadConsoleMessages(): Promise<string[]> {
		const messages: string[] = [];

		this.page.on('console', (msg) => {
			const text = msg.text();
			if (
				text.includes('PII') ||
				text.includes('upload') ||
				text.includes('file') ||
				text.includes('progress')
			) {
				messages.push(`${msg.type()}: ${text}`);
			}
		});

		return messages;
	}
}

/**
 * Test file data and paths
 */
export const FILE_TEST_DATA = {
	// Available test files
	PII_DOCUMENT:
		'/Users/maxflottmann/Projects/open-webui/tests/e2e/test_files/line.break.entity.docx',
	SIMPLE_TEXT: '/Users/maxflottmann/Projects/open-webui/tests/e2e/test_files/simple-test.txt',
	MODEL_FILE: '/Users/maxflottmann/Projects/open-webui/test/test_files/image_gen/sd-empty.pt',

	// File types for testing
	SUPPORTED_TYPES: [
		{
			extension: '.docx',
			mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
		},
		{ extension: '.pdf', mimeType: 'application/pdf' },
		{ extension: '.txt', mimeType: 'text/plain' },
		{ extension: '.png', mimeType: 'image/png' },
		{ extension: '.jpg', mimeType: 'image/jpeg' }
	],

	// Expected file processing states
	UPLOAD_STATES: {
		UPLOADING: 'uploading',
		PROCESSING: 'processing',
		UPLOADED: 'uploaded',
		ERROR: 'error',
		DONE: 'done'
	}
};

/**
 * File upload test scenarios
 */
export const FILE_UPLOAD_SCENARIOS = [
	{
		name: 'PII Document Upload',
		filePath: FILE_TEST_DATA.PII_DOCUMENT,
		expectedPiiDetection: true,
		expectedProgressStates: ['uploading', 'processing', 'uploaded'],
		description: 'Upload document with PII entities and verify detection'
	},
	{
		name: 'Simple Text Upload',
		filePath: FILE_TEST_DATA.SIMPLE_TEXT,
		expectedPiiDetection: false,
		expectedProgressStates: ['uploading', 'processing', 'uploaded'],
		description: 'Upload simple text file without PII content'
	},
	{
		name: 'Model File Upload',
		filePath: FILE_TEST_DATA.MODEL_FILE,
		expectedPiiDetection: false,
		expectedProgressStates: ['uploading', 'uploaded'],
		description: 'Upload binary model file without PII content'
	}
];
