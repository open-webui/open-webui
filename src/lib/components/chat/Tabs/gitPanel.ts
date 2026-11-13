// Shared look and formatting for the Git panel's views.

export const primaryButton =
	'bg-gray-900 dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-white/90';
export const disabledButton =
	'bg-gray-100 dark:bg-white/6 text-gray-400 dark:text-gray-600 cursor-default';
export const secondaryButton =
	'bg-gray-100 dark:bg-white/6 text-gray-600 dark:text-gray-300 hover:bg-gray-200/60 dark:hover:bg-white/10 disabled:text-gray-400 dark:disabled:text-gray-600 disabled:hover:bg-gray-100 dark:disabled:hover:bg-white/6';

export const relativeTime = (date: string) => {
	const seconds = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 1000));
	return seconds < 60
		? 'now'
		: seconds < 3600
			? `${Math.floor(seconds / 60)}m`
			: seconds < 86400
				? `${Math.floor(seconds / 3600)}h`
				: `${Math.floor(seconds / 86400)}d`;
};

// Checks come from `pr/checks` (bucket, state, link) and from `pr/view` / `pr/list`
// (check runs: conclusion, status, detailsUrl; status contexts: context, state, targetUrl).
export type Check = {
	name?: string;
	context?: string;
	bucket?: string;
	status?: string;
	conclusion?: string;
	state?: string;
	link?: string;
	detailsUrl?: string;
	targetUrl?: string;
};
export type CheckOutcome = 'pass' | 'fail' | 'pending' | 'skip';

export const checkName = (check: Check) => check.name || check.context || '';
export const checkLink = (check: Check) => check.link || check.detailsUrl || check.targetUrl || '';
export const checkResult = (check: Check) =>
	(check.conclusion || check.state || check.status || check.bucket || '')
		.toLowerCase()
		.replaceAll('_', ' ');
export const checkOutcome = (check: Check): CheckOutcome => {
	const bucket = check.bucket?.toLowerCase();
	if (bucket)
		return bucket === 'pass'
			? 'pass'
			: bucket === 'fail'
				? 'fail'
				: bucket === 'pending'
					? 'pending'
					: 'skip';
	const result = (check.conclusion || check.state || check.status || '').toUpperCase();
	if (result === 'SUCCESS') return 'pass';
	if (['FAILURE', 'ERROR', 'TIMED_OUT', 'ACTION_REQUIRED', 'STARTUP_FAILURE'].includes(result))
		return 'fail';
	if (['NEUTRAL', 'SKIPPED', 'STALE', 'CANCELLED'].includes(result)) return 'skip';
	return 'pending';
};
export const outcomeTone: Record<CheckOutcome, string> = {
	pass: 'bg-green-500 dark:bg-green-400',
	fail: 'bg-red-500 dark:bg-red-400',
	pending: 'bg-yellow-500 dark:bg-yellow-400',
	skip: 'bg-gray-300 dark:bg-gray-600'
};
export const checksSummary = (checks?: Check[]) => {
	if (!checks?.length) return null;
	const outcomes = checks.map(checkOutcome);
	const failed = outcomes.filter((outcome) => outcome === 'fail').length;
	const pending = outcomes.filter((outcome) => outcome === 'pending').length;
	const passed = outcomes.filter((outcome) => outcome === 'pass').length;
	const outcome: CheckOutcome = failed ? 'fail' : pending ? 'pending' : passed ? 'pass' : 'skip';
	return { outcome, failed, pending, passed };
};

// Prompts the Git panel drafts into the chat composer. The user reviews them before sending.
type Translate = (key: string, vars?: Record<string, unknown>) => string;
type Author = { login?: string } | undefined;
type Note = { body: string; author?: Author; state?: string };

const quote = (text: string) =>
	text
		.trim()
		.split('\n')
		.map((line) => `> ${line}`)
		.join('\n');
const notes = (items: Note[]) =>
	items
		.filter((item) => item.body?.trim())
		.map((item) => `@${item.author?.login ?? 'unknown'}:\n${quote(item.body)}`);

export const issuePrompt = (
	t: Translate,
	issue: { number: number; title: string; url: string; body?: string; comments?: Note[] }
) =>
	[
		t('Work on issue #{{number}}: {{title}}', issue),
		issue.url,
		issue.body?.trim() ? quote(issue.body) : '',
		...(issue.comments?.some((item) => item.body?.trim())
			? [t('Comments on the issue:'), ...notes(issue.comments)]
			: []),
		t('Create a branch for it, make the change, and summarize what you changed.')
	]
		.filter(Boolean)
		.join('\n\n');

type PullRequestRef = { number: number; title: string; url: string; headRefName: string };

export const checkPrompt = (t: Translate, pr: PullRequestRef, check: Check) =>
	[
		t('The check "{{check}}" is failing on pull request #{{number}} ({{title}}).', {
			check: checkName(check),
			number: pr.number,
			title: pr.title
		}),
		checkLink(check),
		t(
			'Read its log, find out why it fails, and fix it on the branch {{branch}}. Then summarize the fix.',
			{ branch: pr.headRefName }
		)
	]
		.filter(Boolean)
		.join('\n\n');

export const notePrompt = (t: Translate, pr: PullRequestRef, item: Note) =>
	[
		t('Feedback from @{{author}} on pull request #{{number}} ({{title}}):', {
			author: item.author?.login ?? 'unknown',
			number: pr.number,
			title: pr.title
		}),
		quote(item.body)
	].join('\n\n');

export const feedbackPrompt = (
	t: Translate,
	pr: PullRequestRef,
	failing: Check[],
	feedback: Note[]
) =>
	[
		t(
			'Address the open feedback on pull request #{{number}} ({{title}}) on the branch {{branch}}.',
			{
				number: pr.number,
				title: pr.title,
				branch: pr.headRefName
			}
		),
		pr.url,
		...(failing.length
			? [
					t('Failing checks:'),
					failing
						.map(
							(check) => `- ${checkName(check)}${checkLink(check) ? `: ${checkLink(check)}` : ''}`
						)
						.join('\n')
				]
			: []),
		...(feedback.some((item) => item.body?.trim())
			? [t('Review comments:'), ...notes(feedback)]
			: []),
		t('Fix what is still relevant, then summarize what you changed and what you left alone.')
	].join('\n\n');

export const conflictPrompt = (t: Translate, pr: PullRequestRef & { baseRefName: string }) =>
	t(
		'Pull request #{{number}} ({{title}}) has merge conflicts with {{base}}. On the branch {{branch}}, merge {{base}} in, resolve the conflicts, run the tests, and push. Then summarize how you resolved them.',
		{ number: pr.number, title: pr.title, base: pr.baseRefName, branch: pr.headRefName }
	);
