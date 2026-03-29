/**
 * P0-2 Color Contrast Validation Script
 * Standalone script using Playwright + axe-core
 */

import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function validateP02() {
  console.log('🔍 Starting P0-2 Color Contrast Validation...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  const page = await context.newPage();

  try {
    // Navigate to Open-WebUI
    console.log('📍 Navigating to http://localhost:5173...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000); // Extra time for dynamic content

    console.log('✓ Page loaded\n');

    // Run axe-core scan
    console.log('🔬 Running axe-core accessibility scan...');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    // Filter for color-contrast violations
    const contrastViolations = results.violations.filter(
      v => v.id === 'color-contrast'
    );

    const contrastNodes = contrastViolations.reduce(
      (sum, v) => sum + v.nodes.length,
      0
    );

    // Generate report
    const report = {
      timestamp: new Date().toISOString(),
      url: page.url(),
      branch: 'feat/wcag-phase1-accessibility',
      summary: {
        totalViolations: results.violations.length,
        contrastViolations: contrastViolations.length,
        contrastNodes: contrastNodes,
        wcagLevel: 'AA',
        requiredRatio: '4.5:1',
      },
      violations: results.violations.map(violation => ({
        id: violation.id,
        impact: violation.impact,
        description: violation.description,
        help: violation.help,
        helpUrl: violation.helpUrl,
        nodes: violation.nodes.map(node => ({
          html: node.html.substring(0, 200),
          target: node.target,
          failureSummary: node.failureSummary,
        })),
      })),
      passes: results.passes
        .filter(pass => pass.id === 'color-contrast')
        .map(pass => ({
          id: pass.id,
          description: pass.description,
          totalNodes: pass.nodes.length,
        })),
    };

    // Save report
    const reportPath = join(__dirname, 'p0-2-validation-report.json');
    writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`✓ Report saved: ${reportPath}\n`);

    // Take screenshot
    const screenshotPath = join(__dirname, 'p0-2-validation-screenshot.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`✓ Screenshot saved: ${screenshotPath}\n`);

    // Print summary
    console.log('═══════════════════════════════════════════');
    console.log('  P0-2 Color Contrast Validation Summary');
    console.log('═══════════════════════════════════════════\n');
    console.log(`Total violations: ${report.summary.totalViolations}`);
    console.log(`Color contrast violations: ${report.summary.contrastViolations}`);
    console.log(`Affected nodes: ${report.summary.contrastNodes}\n`);

    if (contrastViolations.length > 0) {
      console.log('❌ COLOR CONTRAST VIOLATIONS FOUND:\n');
      contrastViolations.forEach(violation => {
        console.log(`  ${violation.id} (${violation.impact})`);
        console.log(`  ${violation.description}`);
        console.log(`  Affected nodes: ${violation.nodes.length}\n`);
        violation.nodes.slice(0, 3).forEach(node => {
          console.log(`    HTML: ${node.html.substring(0, 100)}...`);
          console.log(`    Target: ${node.target.join(' ')}`);
          if (node.failureSummary) {
            console.log(`    Failure: ${node.failureSummary.split('\n')[0]}`);
          }
          console.log();
        });
        if (violation.nodes.length > 3) {
          console.log(`    ... and ${violation.nodes.length - 3} more nodes\n`);
        }
      });

      console.log(`\n⚠️  VALIDATION FAILED: ${contrastViolations.length} color contrast violations found`);
      console.log(`    Check ${reportPath} for full details\n`);
      process.exit(1);
    } else {
      console.log('✅ NO COLOR CONTRAST VIOLATIONS FOUND!\n');
      console.log('🎉 P0-2 color contrast fixes are working correctly!\n');
      console.log(`WCAG 2.1 AA compliance achieved for color contrast (4.5:1 ratio)\n`);
      process.exit(0);
    }
  } catch (error) {
    console.error('❌ Validation failed with error:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

validateP02();
