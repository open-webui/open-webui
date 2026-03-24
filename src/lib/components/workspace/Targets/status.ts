import type { TargetStatus } from './types';

export const getTargetStatusClass = (status: TargetStatus) => {
	if (status === 'Active') {
		return 'text-emerald-700 dark:text-emerald-300 bg-emerald-100/80 dark:bg-emerald-900/45';
	}

	if (status === 'Pending') {
		return 'text-amber-700 dark:text-amber-300 bg-amber-100/80 dark:bg-amber-900/45';
	}

	if (status === 'Paused') {
		return 'text-slate-700 dark:text-slate-300 bg-slate-100/80 dark:bg-slate-800/80';
	}

	if (status === 'Complete') {
		return 'text-cyan-700 dark:text-cyan-300 bg-cyan-100/80 dark:bg-cyan-900/45';
	}

	return 'text-rose-700 dark:text-rose-300 bg-rose-100/80 dark:bg-rose-900/45';
};
