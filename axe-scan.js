import playwright from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { promises as fs } from 'fs';

(async () => {
  const browser = await playwright.chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });

  // Wait a bit more for any dynamic content to load
  await page.waitForTimeout(5000);

  // Take a screenshot to see what we're scanning
  await page.screenshot({ path: 'axe-scan-page.png', fullPage: true });
  console.log('Screenshot saved to axe-scan-page.png');

  console.log('Running axe-core WCAG 2.1 AA scan (all rules)...');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2aa'])
    .analyze();

  console.log('\n=== SCAN RESULTS ===');
  console.log(`Violations found: ${results.violations.length}`);
  console.log(`Passes: ${results.passes.length}`);
  console.log(`Incomplete: ${results.incomplete.length}`);
  console.log(`Inapplicable: ${results.inapplicable.length}`);

  if (results.violations.length > 0) {
    console.log('\n=== VIOLATIONS BY SEVERITY ===');
    const bySeverity = {};
    results.violations.forEach(v => {
      bySeverity[v.impact] = (bySeverity[v.impact] || 0) + v.nodes.length;
    });
    console.log(JSON.stringify(bySeverity, null, 2));

    console.log('\n=== VIOLATION DETAILS ===');
    results.violations.forEach(v => {
      console.log(`\n${v.id} (${v.impact}): ${v.nodes.length} occurrences`);
      console.log(`  Help: ${v.help}`);
      console.log(`  URL: ${v.helpUrl}`);
    });
  }

  // Save results
  await fs.writeFile(
    'axe-playwright-results.json',
    JSON.stringify(results, null, 2)
  );
  console.log('\n✅ Full results saved to axe-playwright-results.json');

  await browser.close();
})();
